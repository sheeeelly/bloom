"""Babyboo Fashion 自动监控引擎 - 页面展示商品白名单版

目标页面：
https://www.babyboofashion.com/collections/bridesmaid#/sort:ga_unique_purchases:desc

核心逻辑：
1. 只以前台渲染后的 Babyboo 指定 Bridesmaid 列表页真实展示商品为准。
2. 不再用 SearchSpring、products.json、collection HTML、extra handles、Webyze ProductColors、GraphQL 兜底扩充商品池。
3. product.js / product.json / PDP 仅允许给上述页面展示商品补详情、价格和尺码，不允许新增商品。
4. 最终输出顺序严格使用页面接口返回顺序，避免把同款其他颜色或非页面商品额外加入报表。
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any

import requests

from utils.baseline_manager import BaselineManager
from utils.report_history import cleanup_previous_site_reports, is_first_site_crawl, resolve_current_datetime
from utils.config import Config
from utils.data_exporter import DataExporter
from utils.product_details import collect_product_detail_text
from utils.report_builder import (
    apply_ranking_context,
    build_report_sheets,
    make_full_columns,
    mark_and_build_delisted_records,
    mark_relisted_after_delisted,
    sync_change_context_from_metadata,
)
from utils.retry_errors import RetryableTaskError, classify_http_status, is_retryable_exception
from utils.retry_queue import RetryQueue
from utils.product_record import (
    CLProductRecord,
    COLUMNS_L2_CL,
    HEADER_L1_CONFIG_CL,
)

try:
    from utils.product_record import COLUMNS_L2_BB, HEADER_L1_CONFIG_BB
except ImportError:  # 兼容尚未替换新版 product_record.py 的项目
    COLUMNS_L2_BB = COLUMNS_L2_CL
    HEADER_L1_CONFIG_BB = HEADER_L1_CONFIG_CL

try:
    from utils.attribute_extractor import extract_attributes
except ImportError:  # 兼容尚未新增公共属性解析模块的项目
    extract_attributes = None  # type: ignore

try:
    from utils.gsheet_sync import GSheetSync
except ImportError:
    GSheetSync = None  # type: ignore


logger = logging.getLogger(__name__)

BB_SOURCE_PAGE_URL = "https://www.babyboofashion.com/collections/bridesmaid#/sort:ga_unique_purchases:desc"


# =========================
# Babyboo Fashion 配置
# =========================

BB_BASE_URL = "https://www.babyboofashion.com"
BB_COLLECTION_HANDLE = "bridesmaid"

BB_SHOP_DOMAIN = "babyboofashion-com-au.myshopify.com"
BB_GRAPHQL_URL = "https://babyboofashion-com-au.myshopify.com/api/2024-04/graphql.json"
BB_SEARCHSPRING_CATEGORY_URL = "https://z2b4sf.a.searchspring.io/api/search/category.json"
BB_SEARCHSPRING_SITE_ID = "z2b4sf"
BB_SEARCHSPRING_MARKET = "AUD"
BB_WEBYZE_GROUP_URL = "https://s-pc.webyze.com/ProductColors/product-group.json"

HEADERS_HTML = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

HEADERS_JSON = {
    "User-Agent": HEADERS_HTML["User-Agent"],
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.babyboofashion.com",
    "Referer": "https://www.babyboofashion.com/collections/bridesmaid",
}


# =========================
# 属性关键词
# =========================

FABRIC_KEYWORDS = [
    "Non-Stretch Cotton Blend",
    "Cotton Blend",
    "Textured Cut & Sew",
    "Cut & Sew",
    "Cut-and-Sew",
    "Cut and Sew",
    "Duchess Satin",
    "Matte Satin",
    "Stretch Satin",
    "Stretch Mesh",
    "Power Mesh",
    "Soft Mesh",
    "Crepe Satin",
    "Luxe Stretch Knit",
    "Stretch Knit",
    "Satin",
    "Chiffon",
    "Crepe Jersey",
    "Scuba Crepe",
    "Crepe",
    "Mesh",
    "Lace",
    "Velvet",
    "Tulle",
    "Sequin",
    "Sequinned",
    "Jersey",
    "Organza",
    "Jacquard",
    "Broderie Anglaise",
    "Plisse",
    "Plissé",
    "Cotton",
    "Linen",
    "Woven",
    "Charmeuse",
    "Ponte",
    "Twill",
    "Luxe",
    "Slinky",
    "Scuba",
    "Georgette",
    "Knit",
    "Ribbed",
    "Sheer",
    "Polyester",
    "Viscose",
    "Rayon",
    "Nylon",
    "Elastane",
    "Spandex",
]

STYLE_KEYWORDS = [
    "Bodycon",
    "Fishtail",
    "Mermaid",
    "A-Line",
    "Column Silhouette",
    "Column",
    "Straight Skirt",
    "Centre Back Split",
    "Center Back Split",
    "Lace-Up Back",
    "Lace Up Back",
    "Fluted Skirt",
    "Convertible Bow",
    "Slip",
    "Wrap",
    "Ruched",
    "Ruching",
    "Draped",
    "Drape",
    "Corset",
    "Backless",
    "Cape",
    "With Scarf",
    "Scarf",
    "Jumpsuit",
    "Multiway",
    "Asymmetric",
    "Asymmetrical",
    "Pleated",
    "Twist",
    "Tie",
    "Cut Out",
    "Cut-Out",
    "Embellished",
    "Feather",
    "Ruffle",
    "Ruffled",
    "Bow",
    "Split",
    "Front Split",
    "Thigh High Split",
    "Ruched Hips",
    "Full Gathered Skirt",
    "Second Skin Fit",
    "Back Split",
    "Side Split",
    "Thigh Split",
    "Gathered",
    "Tiered",
    "Ruffle Hem",
    "Frill",
    "Rosette",
    "Flower Applique",
    "Floral Applique",
    "Floral Print",
    "Polka Dot Print",
    "Gown",
    "Halter",
    "Cowl",
    "Strapless",
    "Off Shoulder",
    "One Shoulder",
]

LENGTH_KEYWORDS = [
    "Maxi",
    "Midi",
    "Mini",
    "Long",
    "Short",
]

NECKLINE_KEYWORDS = [
    "Bandeau",
    "One Shoulder",
    "One-Shoulder",
    "Asymmetric",
    "Asymmetrical",
    "Asymmetric-Neck",
    "Off Shoulder",
    "Off The Shoulder",
    "Bardot",
    "Plunge",
    "Cowl",
    "Halter",
    "High Neck",
    "V Neck",
    "V-Neck",
    "Square Neck",
    "Sweetheart",
    "Strapless",
    "Scoop Neck",
    "Scooped Neckline",
    "Crew Neck",
    "Cami",
    "Bustier",
    "Fine Shoulder Straps",
    "Shoulder Straps",
    "Thin Straps",
    "Cupped Bust",
    "Plunging Neckline",
    "Deep Plunge Neckline",
    "Halterneck Straps",
    "Halter Neck Straps",
    "Low V-Shaped Back",
    "Adjustable Straps",
    "Spaghetti Straps",
    "Tie Straps",
    "Halter Tie",
    "Cross Back Straps",
    "Ruffle Straps",
    "Underwired Cups",
    "Underwire Cups",
    "Corset Bodice",
]

COLOR_KEYWORDS = [
    "Glacier Blue",
    "Plum Brown",
    "Light Blue",
    "Powder Blue",
    "Baby Blue",
    "Dusty Blue",
    "Sky Blue",
    "Blue",
    "Black",
    "White",
    "Ivory",
    "Cream",
    "Champagne",
    "Oyster",
    "Stone",
    "Taupe",
    "Mocha",
    "Chocolate",
    "Brown",
    "Dark Brown",
    "Nude",
    "Beige",
    "Blush",
    "Blush Pink",
    "Pink",
    "Rose",
    "Dusty Rose",
    "Baby Pink",
    "Hot Pink",
    "Fuchsia",
    "Red",
    "Burgundy",
    "Wine",
    "Deep Wine",
    "Berry",
    "Orange",
    "Coral",
    "Yellow",
    "Lemon",
    "Butter",
    "Green",
    "Sage",
    "Olive",
    "Khaki",
    "Emerald",
    "Mint",
    "Navy",
    "Teal",
    "Aqua",
    "Purple",
    "Lilac",
    "Lavender",
    "Orchid",
    "Plum",
    "Silver",
    "Gold",
    "Grey",
    "Gray",
    "Multi",
    "Floral",
]

SIZE_VALUES = {
    "default title",
    "default",
    "one size",
    "os",
    "xxs",
    "xs",
    "s",
    "m",
    "l",
    "xl",
    "xxl",
    "2xl",
    "3xl",
    "4xl",
    "uk 4",
    "uk 6",
    "uk 8",
    "uk 10",
    "uk 12",
    "uk 14",
    "uk 16",
    "uk 18",
    "uk 20",
    "uk 22",
    "uk 24",
    "uk 26",
    "us 0",
    "us 2",
    "us 4",
    "us 6",
    "us 8",
    "us 10",
    "us 12",
    "us 14",
    "us 16",
    "us 18",
    "us 20",
    "us 22",
    "us 24",
    "us 26",
    "4",
    "6",
    "8",
    "10",
    "12",
    "14",
    "16",
    "18",
    "20",
    "22",
    "24",
    "26",
}


# =========================
# 通用工具函数
# =========================

def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_text(value: Any) -> str:
    text = unescape(_safe_str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_numeric_id(value: Any) -> str:
    text = _safe_str(value)
    if not text:
        return ""

    match = re.search(r"(\d{6,})", text)
    if match:
        return match.group(1)

    return ""


def _parse_price(value: Any) -> float:
    if value is None:
        return 0.0

    if isinstance(value, dict):
        value = value.get("amount") or value.get("price") or value.get("value")

    if isinstance(value, list):
        value = value[0] if value else 0

    raw_text = str(value).strip()
    if not raw_text:
        return 0.0

    clean_text = re.sub(r"[^0-9.\-]", "", raw_text)

    try:
        price = float(clean_text) if clean_text else 0.0

        # Shopify product.js 有时返回 cents，例如 8500
        if "." not in clean_text and price >= 1000:
            price = price / 100

        return price
    except ValueError:
        return 0.0


def _format_price(value: float) -> str:
    """统一输出 Babyboo AU 站价格，避免出现 CA$360.00 AUD 这类混合币种。

    本爬虫只抓取 https://www.babyboofashion.com/collections/bridesmaid 对应页面，
    价格口径固定为 AU / AUD，不再读取 BB_PRICE_PREFIX、BB_PRICE_SUFFIX 等
    可能残留 CA 配置的环境变量。
    """
    if not value:
        return ""
    return f"${value:.2f} AUD"


def _normalize_image_url(url: Any) -> str:
    text = _safe_str(url)
    if not text:
        return ""
    if text.startswith("//"):
        return "https:" + text
    return text


def _slugify(text: str) -> str:
    text = _safe_str(text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def _find_keyword(text: str, keywords: list[str]) -> str:
    text_lower = text.lower()
    text_normalized = text_lower.replace("_", " ").replace("-", " ")

    for keyword in keywords:
        keyword_lower = keyword.lower()
        keyword_normalized = keyword_lower.replace("-", " ")
        if keyword_lower in text_lower or keyword_normalized in text_normalized:
            return keyword.replace("-", " ")

    return ""


def _get_tags(product: dict[str, Any]) -> list[str]:
    tags = product.get("tags", []) or []

    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]

    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]

    return []


def _merge_non_empty(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """只用非空值覆盖，避免 Webyze / skeleton 空字段覆盖 GraphQL 完整字段。"""
    for key, value in incoming.items():
        if value in [None, "", [], {}]:
            continue
        existing[key] = value
    return existing




def _extract_handle_from_product_url(href: str) -> str:
    href = _safe_str(href)

    if "/products/" not in href:
        return ""

    handle = href.split("/products/", 1)[1]
    handle = handle.split("?", 1)[0]
    handle = handle.split("#", 1)[0]
    handle = handle.strip("/")

    if not handle:
        return ""

    lower_handle = handle.lower()

    if ".oembed" in lower_handle:
        return ""
    if lower_handle.endswith(".js"):
        return ""
    if lower_handle.endswith(".json"):
        return ""
    if "." in handle:
        return ""

    return handle


def _build_product_url(base_url: str, handle: str) -> str:
    handle = _safe_str(handle)
    if not handle:
        return ""
    return f"{base_url.rstrip('/')}/products/{handle}"




def _split_style_color_name(title: str, handle: str) -> tuple[str, str, str]:
    """
    示例：
    Vessa Maxi Dress - Black -> Vessa / Maxi Dress / Black
    Cyra Maxi Dress - Glacier Blue -> Cyra / Maxi Dress / Glacier Blue
    """
    title = _clean_text(title)
    handle = _safe_str(handle)

    if not title:
        return "", "", "Default"

    color_name = "Default"
    base_title = title

    match = re.match(r"^(.*?)\s+-\s+(.*?)$", title)
    if match:
        base_title = match.group(1).strip()
        color_name = match.group(2).strip()

    if color_name == "Default":
        for color in sorted(COLOR_KEYWORDS, key=len, reverse=True):
            pattern = rf"^(.*?)\s+in\s+{re.escape(color)}$"
            match = re.match(pattern, title, flags=re.IGNORECASE)
            if match:
                base_title = match.group(1).strip()
                color_name = color
                break

    if color_name == "Default":
        handle_slug = handle.lower()
        for color in sorted(COLOR_KEYWORDS, key=len, reverse=True):
            color_slug = _slugify(color)
            if handle_slug.endswith(f"-{color_slug}"):
                color_name = color
                break

    style_label = ""
    product_name = base_title

    if " " in base_title:
        first_word, rest = base_title.split(" ", 1)
        first_word_clean = first_word.strip()

        blocked_first_words = {
            *(c.lower() for c in COLOR_KEYWORDS),
            *(f.lower() for f in FABRIC_KEYWORDS),
            *(l.lower() for l in LENGTH_KEYWORDS),
            "the",
            "a",
            "an",
        }

        if first_word_clean.lower() not in blocked_first_words:
            style_label = first_word_clean
            product_name = rest.strip()

    return style_label, product_name, color_name


def _extract_variant_color(variant: dict[str, Any]) -> str:
    candidates: list[str] = []

    for key in ["option1", "option2", "option3", "title", "name"]:
        value = _safe_str(variant.get(key))
        if value:
            candidates.extend(re.split(r"\s*/\s*|\s+-\s+", value))

    selected_options = variant.get("selectedOptions") or variant.get("selected_options") or []
    if isinstance(selected_options, list):
        for option in selected_options:
            if not isinstance(option, dict):
                continue
            name = _safe_str(option.get("name")).lower()
            value = _safe_str(option.get("value"))
            if name == "color" and value:
                candidates.append(value)

    for value in candidates:
        value = _clean_text(value)
        lower_value = value.lower()

        if not value:
            continue
        if lower_value in SIZE_VALUES:
            continue
        if lower_value.isdigit():
            continue
        if re.fullmatch(r"(uk|us)?\s*\d+", lower_value):
            continue

        return value

    return ""



def _is_size_candidate(value: Any) -> bool:
    """判断一个 option/title 片段是否像尺码。"""
    text = _clean_text(value)
    if not text:
        return False

    lower = text.lower()
    if lower in SIZE_VALUES:
        return True

    normalized = lower.replace(".", "").replace(" ", "")
    if normalized in SIZE_VALUES:
        return True

    # Babyboo 常见尺码：XXS/XS/S/M/L/XL/XXL，或 AU/US/UK 数字尺码。
    if re.fullmatch(r"(xxs|xs|s|m|l|xl|xxl|2xl|3xl|4xl)", lower):
        return True
    if re.fullmatch(r"(?:au|us|uk)?\s*\d{1,2}", lower):
        return True
    if re.fullmatch(r"\d{1,2}\s*-\s*\d{1,2}", lower):
        return True

    return False


def _extract_variant_size(variant: dict[str, Any]) -> str:
    """从 Shopify/SearchSpring/product.js variant 中提取尺码。"""
    if not isinstance(variant, dict):
        return ""

    selected_options = variant.get("selectedOptions") or variant.get("selected_options") or []
    if isinstance(selected_options, list):
        for option in selected_options:
            if not isinstance(option, dict):
                continue
            name = _safe_str(option.get("name")).lower()
            value = _clean_text(option.get("value"))
            if value and ("size" in name or _is_size_candidate(value)):
                return value

    # SearchSpring / product.js 常见 option 字段。
    for key in ["size", "ss_size", "ss_size_filter_ac", "option1", "option2", "option3"]:
        value = _clean_text(variant.get(key))
        if value and _is_size_candidate(value):
            return value

    # variant title 常见格式：Black / XS、XS、Default Title。
    title = _clean_text(variant.get("title") or variant.get("name"))
    if title and title.lower() not in {"default title", "default"}:
        for part in re.split(r"\s*/\s*|\s+-\s*|,", title):
            part = _clean_text(part)
            if _is_size_candidate(part):
                return part

    sku = _clean_text(variant.get("sku"))
    if sku:
        for part in re.split(r"[-_/\s]+", sku):
            if _is_size_candidate(part):
                return part.upper() if len(part) <= 4 else part

    return ""


def _extract_sizes_from_searchspring_item(item: dict[str, Any]) -> list[str]:
    """从 SearchSpring 原始 result 中尽可能提取尺码列表。"""
    size_keys = [
        "sizes", "size", "ss_size", "ss_size_filter_ac", "ss_size_filter",
        "available_sizes", "availableSizes", "variant_sizes", "variantSizes",
        "option_size", "filter_size",
    ]
    sizes: list[str] = []

    for key in size_keys:
        raw = item.get(key)
        values = _as_text_list(raw)
        if not values and raw not in [None, "", [], {}]:
            values = [str(raw)]
        for value in values:
            # SearchSpring 可能用逗号、管道、分号、斜杠拼接尺码。
            for part in re.split(r",|\||;|/", str(value)):
                part = _clean_text(part)
                if part and _is_size_candidate(part) and part not in sizes:
                    sizes.append(part)

    return sizes


def _format_sizes_for_variants(color_variants: list[dict[str, Any]], product: dict[str, Any]) -> str:
    """输出 PDP 页面中明确可售的尺码。

    口径：
    - 没有拿到任何 variants/尺码数据：写“未获取”，不能误判为无码；
    - 拿到了 variants，但所有尺码都不可售：写“无码”；
    - 只有 available=True 的尺码才写进表格。
    """
    if not color_variants:
        return "未获取"

    available_sizes: list[str] = []
    has_any_size = False

    for variant in color_variants or []:
        if not isinstance(variant, dict):
            continue

        size = _extract_variant_size(variant)
        if size:
            has_any_size = True

        if not bool(variant.get("available", False)):
            continue

        if size and size not in available_sizes:
            available_sizes.append(size)

    if available_sizes:
        return " / ".join(available_sizes)

    return "无码" if has_any_size else "未获取"


def _get_variant_image(product: dict[str, Any], variant: dict[str, Any]) -> str:
    featured_image = variant.get("featured_image")
    if isinstance(featured_image, dict):
        src = featured_image.get("src") or featured_image.get("url")
        if src:
            return _normalize_image_url(src)

    images = product.get("images", []) or []
    variant_id = variant.get("id")
    image_id = variant.get("image_id") or variant.get("featured_image_id")

    if image_id:
        for image in images:
            if isinstance(image, dict) and image.get("id") == image_id:
                return _normalize_image_url(image.get("src") or image.get("url"))

    if variant_id:
        for image in images:
            if not isinstance(image, dict):
                continue
            variant_ids = image.get("variant_ids", []) or []
            if variant_id in variant_ids:
                return _normalize_image_url(image.get("src") or image.get("url"))

    if images:
        first_image = images[0]
        if isinstance(first_image, dict):
            return _normalize_image_url(first_image.get("src") or first_image.get("url"))
        if isinstance(first_image, str):
            return _normalize_image_url(first_image)

    image = product.get("image")
    if isinstance(image, dict):
        return _normalize_image_url(image.get("src") or image.get("url"))
    if isinstance(image, str):
        return _normalize_image_url(image)

    return ""


def _is_official_new(product: dict[str, Any]) -> str:
    tags_text = " ".join(_get_tags(product)).lower()
    title = _safe_str(product.get("title")).lower()

    if "new in" in tags_text or "new-in" in tags_text or "new arrival" in tags_text:
        return "是"
    if "new in" in title:
        return "是"

    return "否"


def _normalize_attr_label(value: str) -> str:
    value = re.sub(r"\s+", " ", _safe_str(value)).strip()
    mapping = {
        "Duchess satin": "Duchess Satin",
        "matte satin": "Matte Satin",
        "centre back split": "Centre Back Split",
        "center back split": "Center Back Split",
        "lace up back": "Lace-Up Back",
        "fine shoulder straps": "Fine Shoulder Straps",
        "shoulder straps": "Shoulder Straps",
        "underwired cups": "Underwired Cups",
        "underwire cups": "Underwired Cups",
        "maxi length": "Maxi",
        "midi length": "Midi",
        "mini length": "Mini",
        "non stretch cotton blend": "Non-Stretch Cotton Blend",
        "non-stretch cotton blend": "Non-Stretch Cotton Blend",
        "cotton blend": "Cotton Blend",
        "textured cut & sew": "Textured Cut & Sew",
        "textured cut and sew": "Textured Cut & Sew",
        "textured cut-and-sew": "Textured Cut & Sew",
        "cut & sew": "Cut & Sew",
        "cut and sew": "Cut & Sew",
        "cut-and-sew": "Cut & Sew",
        "premium non stretch cotton blend": "Non-Stretch Cotton Blend",
        "premium non-stretch cotton blend": "Non-Stretch Cotton Blend",
        "luxury non stretch cotton blend": "Non-Stretch Cotton Blend",
        "luxury non-stretch cotton blend": "Non-Stretch Cotton Blend",
        "luxe stretch knit": "Luxe Stretch Knit",
        "stretch knit": "Stretch Knit",
        "scuba crepe": "Scuba Crepe",
        "broderie anglaise": "Broderie Anglaise",
        "plisse": "Plissé",
        "plissé": "Plissé",
        "high low hem": "High-Low Hem",
        "high-low hem": "High-Low Hem",
        "voluminous skirt": "Voluminous Skirt",
        "frilled high low hem skirt": "Frilled High-Low Skirt",
        "frilled high-low hem skirt": "Frilled High-Low Skirt",
    }
    return mapping.get(value, value[:1].upper() + value[1:] if value else "")


def _append_unique(values: list[str], value: str) -> None:
    value = _normalize_attr_label(value)
    if value and value not in values:
        values.append(value)


def _local_extract_attrs_from_text(detail_text: str) -> dict[str, str]:
    """
    Babyboo 本地细粒度规则。

    重点覆盖 PDP Product Details 中常见表达，例如：
    - Duchess satin / Matte satin fabric
    - Column silhouette / Straight skirt with centre back split / Lace-up back
    - Maxi length / Midi length
    - Fine shoulder straps / Underwired cups
    """
    clean_text = _clean_text(detail_text)
    normalized_text = clean_text.lower().replace("-", " ")

    fabric = _find_keyword(clean_text, FABRIC_KEYWORDS)
    if not fabric:
        fabric_patterns = [
            ("Non-Stretch Cotton Blend", r"\b(?:premium\s+|luxury\s+|signature\s+)?non[-\s]?stretch\s+cotton\s+blend(?:\s+fabric)?\b"),
            ("Cotton Blend", r"\b(?:premium\s+|luxury\s+|signature\s+)?cotton\s+blend(?:\s+fabric)?\b"),
            ("Luxe Stretch Knit", r"\bluxe\s+stretch\s+knit(?:\s+fabric)?\b"),
            ("Stretch Knit", r"\bstretch\s+knit(?:\s+fabric)?\b"),
            ("Duchess Satin", r"\bduchess\s+satin\b"),
            ("Matte Satin", r"\bmatte\s+satin\b"),
            ("Stretch Satin", r"\bstretch\s+satin\b"),
            ("Crepe Satin", r"\bcrepe\s+satin\b"),
            ("Scuba Crepe", r"\bscuba\s+crepe\b"),
            ("Power Mesh", r"\bpower\s+mesh\b"),
            ("Stretch Mesh", r"\bstretch\s+mesh\b"),
            ("Soft Mesh", r"\bsoft\s+mesh\b"),
            ("Broderie Anglaise", r"\bbroderie\s+anglaise\b"),
            ("Jacquard", r"\bjacquard(?:\s+floral)?(?:\s+fabric)?\b"),
            ("Plissé", r"\bpliss[eé](?:\s+fabric)?\b"),
            ("Charmeuse", r"\bcharmeuse\b"),
            ("Ponte", r"\bponte\b"),
            ("Twill", r"\btwill\b"),
            ("Linen", r"\blinen(?:\s+blend)?\b"),
            ("Woven", r"\bwoven(?:\s+fabric)?\b"),
            ("Satin", r"\bsatin\b"),
            ("Chiffon", r"\bchiffon\b"),
            ("Crepe Jersey", r"\bcrepe\s+jersey\b"),
            ("Crepe", r"\bcrepe\b"),
            ("Mesh", r"\bmesh\b"),
            ("Velvet", r"\bvelvet\b"),
            ("Tulle", r"\btulle\b"),
            ("Lace", r"\blace\b"),
            ("Jersey", r"\bjersey\b"),
            ("Organza", r"\borganza\b"),
            ("Cotton", r"\bcotton\b"),
            ("Polyester", r"\bpolyester\b"),
            ("Viscose", r"\bviscose\b"),
            ("Rayon", r"\brayon\b"),
            ("Nylon", r"\bnylon\b"),
        ]
        for label, pattern in fabric_patterns:
            if re.search(pattern, normalized_text, flags=re.IGNORECASE):
                fabric = label
                break

    length_match = re.search(
        r"\b(maxi|midi|mini|long|short)\s+(?:length|dress|gown)\b",
        clean_text,
        flags=re.IGNORECASE,
    )
    if length_match:
        length = length_match.group(1).title()
    else:
        length = _find_keyword(clean_text, LENGTH_KEYWORDS)
        if not length and re.search(r"\bgown\b", normalized_text):
            # Babyboo 的 Gown 通常是长款；只作为长度兜底，不影响上半身款式。
            length = "Maxi"

    neckline_parts: list[str] = []
    neckline_patterns = [
        ("Strapless Scooped Neckline", r"\bstrapless\s+scooped\s+neckline\b"),
        ("Strapless Neckline", r"\bstrapless\s+neckline\b"),
        ("Scooped Neckline", r"\bscooped\s+neckline\b"),
        ("Sweetheart Neckline", r"\bsweetheart\s+neckline\b"),
        ("Cowl Neckline", r"\bcowl\s+neckline\b"),
        ("Halter Neckline", r"\bhalter\s+neckline\b"),
        ("One Shoulder", r"\bone\s+shoulder\b"),
        ("Off Shoulder", r"\boff\s+(?:the\s+)?shoulder\b"),
        ("Square Neckline", r"\bsquare\s+neckline\b"),
        ("Plunge Neckline", r"\bplunge\s+neckline\b"),
        ("V-Neckline", r"\bv\s*neckline\b"),
        ("High Neck", r"\bhigh\s+neck\b"),
        ("Fine Shoulder Straps", r"\bfine\s+shoulder\s+straps\b"),
        ("Shoulder Straps", r"\bshoulder\s+straps\b"),
        ("Thin Straps", r"\bthin\s+straps?\b"),
        ("Adjustable Straps", r"\badjustable\s+straps\b"),
        ("Spaghetti Straps", r"\bspaghetti\s+straps?\b"),
        ("Tie Straps", r"\btie\s+straps?\b|\bshoulder\s+tie\s+straps?\b"),
        ("Halter Tie", r"\bhalter\s+tie\b|\btie\s+halter\b"),
        ("Cross Back Straps", r"\bcross[-\s]?back\s+straps?\b"),
        ("Ruffle Straps", r"\bruffle\s+straps?\b|\bruffled\s+straps?\b"),
        ("Underwired Cups", r"\bunderwired\s+cups?\b|\bunderwire\s+cups?\b"),
        ("Corset Bodice", r"\bcorset\s+bodice\b|\binternal\s+corset\s+construction\b"),
        ("Bustier", r"\bbustier\b"),
        ("Bandeau", r"\bbandeau\b"),
    ]

    for label, pattern in neckline_patterns:
        if re.search(pattern, clean_text, flags=re.IGNORECASE):
            _append_unique(neckline_parts, label)

    neckline = " / ".join(neckline_parts[:4]) if neckline_parts else _find_keyword(clean_text, NECKLINE_KEYWORDS)

    style_parts: list[str] = []
    style_patterns = [
        ("A-Line", r"\ba[-\s]?line\b"),
        ("Column Silhouette", r"\bcolumn\s+silhouette\b"),
        ("Straight Skirt", r"\bstraight\s+skirt\b"),
        ("Centre Back Split", r"\bcentre\s+back\s+split\b|\bcenter\s+back\s+split\b"),
        ("Lace-Up Back", r"\blace[-\s]?up\s+back\b"),
        ("Fluted Skirt", r"\bfluted\s+skirt\b"),
        ("Convertible Bow", r"\bconvertible\b[^.]{0,80}\bbows?\b|\bbows?\b[^.]{0,80}\bconvertible\b"),
        ("Corset", r"\b(corset|internal corset construction|corset bodice)\b"),
        ("Cowl Overlay", r"\bcowl\s+overlay\b"),
        ("Asymmetric Pleating", r"\b(asymmetric pleating|asymmetrical pleating)\b"),
        ("Pleated", r"\b(pleated|pleating)\b"),
        ("Tiered", r"\btiered\b"),
        ("Ruffle Hem", r"\bruffle\s+hem\b|\bruffled\s+hem\b"),
        ("Ruffle", r"\bruffle\b|\bruffled\b"),
        ("Frilled High-Low Skirt", r"\bfrilled\s+high[-\s]?low\s+(?:hem\s+)?skirt\b"),
        ("High-Low Hem", r"\bhigh[-\s]?low\s+(?:hem|skirt)\b"),
        ("Voluminous Skirt", r"\bvoluminous\s+skirt\b"),
        ("Frill", r"\bfrill\b|\bfrilled\b"),
        ("Flared Skirt", r"\b(flare to the hem|flared skirt|flared hem)\b"),
        ("Ruched", r"\b(ruched|ruching)\b"),
        ("Draped", r"\b(draped|drape)\b"),
        ("Cut-Out", r"\b(cut out|cut-out)\b"),
        ("Bodycon", r"\bbodycon\b"),
        ("Backless", r"\bbackless\b"),
        ("Side Split", r"\bside\s+split\b"),
        ("Front Split", r"\bfront\s+split\b"),
        ("Back Split", r"\bback\s+split\b"),
        ("Split", r"\b(thigh split|split)\b"),
        ("Rosette", r"\brosette\b"),
        ("Flower Applique", r"\bflower\s+appliqu[eé]\b|\bfloral\s+appliqu[eé]\b"),
        ("Floral Print", r"\bfloral\s+print\b"),
        ("Polka Dot Print", r"\bpolka\s+dot\s+print\b"),
    ]

    for label, pattern in style_patterns:
        if re.search(pattern, clean_text, flags=re.IGNORECASE):
            _append_unique(style_parts, label)

    style = " / ".join(style_parts[:5]) if style_parts else _find_keyword(clean_text, STYLE_KEYWORDS)

    return {
        "fabric_name": fabric,
        "aesthetic_tag": style,
        "length": length,
        "neckline": neckline,
    }


def _merge_attr_dicts(primary: dict[str, str], fallback: dict[str, str]) -> dict[str, str]:
    """primary 优先，fallback 只补空字段。"""
    merged = dict(primary or {})
    for key, value in (fallback or {}).items():
        if not merged.get(key) and value:
            merged[key] = value
    return merged


def _extract_attrs(
    product_name: str,
    tags: list[str],
    product: dict[str, Any] | None = None,
) -> dict[str, str]:
    """
    统一属性解析入口。

    这版不再“公共解析器一返回就直接结束”，而是：
    1. 先跑 Babyboo 本地细粒度规则，覆盖 Product Details / Fabric Details；
    2. 再用公共解析器补空字段；
    3. 确保像 Duchess satin / Column silhouette / Maxi length / Fine shoulder straps
       这类 PDP 明确写出的信息不会在表里空缺。
    """
    product = product or {}
    detail_text = " ".join(
        [
            product_name,
            _safe_str(product.get("title")),
            _safe_str(product.get("handle")),
            _safe_str(product.get("product_type") or product.get("productType")),
            _clean_text(product.get("body_html") or product.get("descriptionHtml")),
            _clean_text(product.get("description")),
            _clean_text(product.get("_pdp_detail_text")),
            _clean_text(product.get("_pdp_jsonld_text")),
            _safe_str(product.get("vendor")),
            " ".join(tags),
        ]
    )

    local_attrs = _local_extract_attrs_from_text(detail_text)

    # 标题/handle 兜底：有些 Webyze/GraphQL 商品详情较少，但标题本身带有明确结构。
    title_fallback_text = " ".join([
        _safe_str(product.get("title")),
        _safe_str(product.get("handle")),
        product_name,
    ])
    title_fallback_attrs = _local_extract_attrs_from_text(title_fallback_text)
    local_attrs = _merge_attr_dicts(local_attrs, title_fallback_attrs)

    # 保守长度兜底：商品名明确是 Maxi/Midi/Mini Dress 时补长度。
    lower_title = title_fallback_text.lower().replace("-", " ")
    if not local_attrs.get("length"):
        if "maxi dress" in lower_title or "maxi gown" in lower_title:
            local_attrs["length"] = "Maxi"
        elif "midi dress" in lower_title:
            local_attrs["length"] = "Midi"
        elif "mini dress" in lower_title:
            local_attrs["length"] = "Mini"

    # 款式级保守兜底：少数 Babyboo 商品 GraphQL/HTML 详情不完整，但款式名长期稳定。
    style_name_key = (str(product.get("title") or "") + " " + str(product.get("handle") or "") + " " + product_name).lower().replace("-", " ")
    if not local_attrs.get("fabric_name"):
        if "angelina" in style_name_key:
            local_attrs["fabric_name"] = "Cotton Blend"
        elif "mariella" in style_name_key:
            local_attrs["fabric_name"] = "Cotton Blend"
    if not local_attrs.get("aesthetic_tag"):
        fallback_style_parts = []
        if "angelina" in style_name_key:
            fallback_style_parts.extend(["High-Low Hem", "Voluminous Skirt"])
        if "maxi dress" in style_name_key and "high low" in style_name_key:
            fallback_style_parts.append("High-Low Hem")
        if fallback_style_parts:
            local_attrs["aesthetic_tag"] = " / ".join(dict.fromkeys(fallback_style_parts))

    if extract_attributes is None:
        return local_attrs

    try:
        source = dict(product)
        source.update(
            {
                "product_name": product_name,
                "title": _safe_str(product.get("title")) or product_name,
                "tags": tags,
                "descriptionHtml": product.get("descriptionHtml") or product.get("body_html") or "",
                "description": product.get("description") or "",
                "body_html": product.get("body_html") or product.get("descriptionHtml") or "",
                "product_type": product.get("product_type") or product.get("productType") or "",
                "vendor": product.get("vendor") or "Babyboo Fashion",
                "_pdp_detail_text": product.get("_pdp_detail_text") or "",
                "_pdp_jsonld_text": product.get("_pdp_jsonld_text") or "",
            }
        )
        common_attrs = extract_attributes(source, default_floor_length=False) or {}
        common_attrs = {
            "fabric_name": common_attrs.get("fabric_name", ""),
            "aesthetic_tag": common_attrs.get("aesthetic_tag", ""),
            "length": common_attrs.get("length", ""),
            "neckline": common_attrs.get("neckline", ""),
        }
        return _merge_attr_dicts(local_attrs, common_attrs)
    except Exception as exc:
        logger.debug("公共属性解析失败，仅使用 Babyboo 本地规则: %s", exc)
        return local_attrs


# =========================
# HTTP
# =========================

def _make_session(config: Config) -> requests.Session:
    session = requests.Session()

    proxy_url = getattr(config, "proxy_url", None)
    if proxy_url:
        session.proxies = {"http": proxy_url, "https": proxy_url}
        logger.info("已配置 HTTP 代理: %s", proxy_url)

    token = os.getenv("BB_STOREFRONT_TOKEN", "").strip()
    if token:
        session.headers.update({"X-Shopify-Storefront-Access-Token": token})

    return session


def _fetch_json_get(
    session: requests.Session,
    url: str,
    *,
    headers: dict[str, str],
    timeout: int,
    params: dict[str, Any] | None = None,
    retries: int = 2,
) -> dict[str, Any] | None:
    for attempt in range(retries + 1):
        try:
            response = session.get(url, headers=headers, timeout=timeout, params=params)

            if response.status_code == 200:
                try:
                    data = response.json()
                    return data if isinstance(data, dict) else None
                except ValueError:
                    logger.warning("JSON GET 解析失败: %s", response.url)
                    return None

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    sleep_seconds = int(retry_after)
                else:
                    sleep_seconds = int(os.getenv("BB_429_SLEEP_SECONDS", "8"))

                logger.warning("JSON GET 触发 429，等待 %s 秒后重试: %s", sleep_seconds, response.url)

                if attempt < retries:
                    time.sleep(sleep_seconds)
                    continue

                return None

            logger.warning("JSON GET 失败: status=%s url=%s", response.status_code, response.url)

            if response.status_code in {403, 404}:
                return None

        except requests.RequestException as exc:
            logger.warning("JSON GET 异常: %s | url=%s", exc, url)

        if attempt < retries:
            time.sleep(0.8 * (attempt + 1))

    return None








# =========================
# 前台页面真实展示商品发现
# =========================

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except Exception:
        return default


def _normalize_page_handle(handle: str) -> str:
    text = _safe_str(handle).strip().lower()
    if not text:
        return ""
    if "/products/" in text:
        text = text.split("/products/", 1)[1]
    text = text.split("?", 1)[0].split("#", 1)[0].strip("/")
    if not text or "." in text:
        return ""
    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", text):
        return ""
    return text


def _fetch_babyboo_rendered_page_refs(
    base_url: str,
    collection_handle: str,
    timeout: int,
) -> list[dict[str, Any]]:
    """只从 Babyboo 前台 collection 页面真实展示链路中提取商品顺序。

    重要：这一步是唯一商品发现来源。
    优先监听前台页面自己触发的 SearchSpring 响应，并按响应中的商品顺序累计。
    这和代码私下调用 SearchSpring 不同：它只使用当前页面真实请求返回的商品池/排序。
    DOM 只作为兜底，但不会从 script/body 隐藏链接中提取，避免顺序污染。
    """
    if os.getenv("BB_DISABLE_RENDERED_PAGE_ORDER", "false").strip().lower() in {"1", "true", "yes", "y"}:
        logger.error("BB_DISABLE_RENDERED_PAGE_ORDER 已开启；为避免错误商品池，不再降级使用 SearchSpring。")
        return []

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        logger.error("未安装 playwright，无法读取 Babyboo 前台真实商品顺序: %s", exc)
        return []

    page_url = BB_SOURCE_PAGE_URL or f"{base_url.rstrip()}/collections/{collection_handle}"
    wait_ms = max(1000, _env_int("BB_RENDER_WAIT_MS", 5000))
    scroll_rounds = max(1, _env_int("BB_RENDER_SCROLL_ROUNDS", 160))
    scroll_pause_ms = max(200, _env_int("BB_RENDER_SCROLL_PAUSE_MS", 700))
    # BB 前台接口的 total/detected_count 偶尔会比唯一商品 handle 数多 1 个，
    # 可能来自隐藏/重复商品或非列表实际渲染项。这里允许 1 个容差，
    # 避免已经抓到最后一页后为了补齐 detected_count 继续空转十几轮。
    stable_rounds_required = max(1, _env_int("BB_RENDER_STABLE_ROUNDS", 3))
    detected_count_tolerance = max(0, _env_int("BB_DETECTED_COUNT_TOLERANCE", 1))
    scroll_step_px = max(500, _env_int("BB_RENDER_SCROLL_STEP_PX", 900))
    expected_count = max(0, _env_int("BB_EXPECTED_PRODUCT_COUNT", 0))
    expected_last_handle = _normalize_page_handle(os.getenv("BB_EXPECTED_LAST_HANDLE", ""))

    def detect_total_count(data: dict[str, Any] | None) -> int:
        if not isinstance(data, dict):
            return 0
        candidates: list[Any] = []
        for block_key in ("pagination", "meta", "response", "merchandising"):
            block = data.get(block_key)
            if isinstance(block, dict):
                for key in (
                    "totalResults", "total_results", "total", "count", "productCount",
                    "numFound", "totalItems", "resultsCount", "resultCount",
                ):
                    candidates.append(block.get(key))
        for key in (
            "totalResults", "total_results", "total", "count", "productCount",
            "numFound", "totalItems", "resultsCount", "resultCount",
        ):
            candidates.append(data.get(key))
        for value in candidates:
            try:
                total = int(float(str(value).replace(",", "")))
                if total > 0:
                    return total
            except Exception:
                continue
        return 0

    def detect_page_no(url: str, data: dict[str, Any] | None) -> int:
        candidates: list[Any] = []
        if isinstance(data, dict):
            pagination = data.get("pagination")
            if isinstance(pagination, dict):
                candidates.extend([
                    pagination.get("currentPage"), pagination.get("current_page"),
                    pagination.get("page"), pagination.get("pageNum"), pagination.get("page_number"),
                ])
            meta = data.get("meta")
            if isinstance(meta, dict):
                candidates.extend([meta.get("page"), meta.get("currentPage"), meta.get("current_page")])
        for value in candidates:
            try:
                page_no = int(float(str(value)))
                if page_no > 0:
                    return page_no
            except Exception:
                pass
        for pattern in (r"[?&](?:page|p|currentPage|pageNum)=([0-9]+)", r"[?&]q\.page=([0-9]+)"):
            m = re.search(pattern, url)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    pass
        return 1

    def make_ref_from_searchspring_item(item: dict[str, Any], order: int) -> dict[str, Any] | None:
        product = _normalize_babyboo_searchspring_result(item, base_url, order)
        if not product:
            return None
        handle = _normalize_page_handle(str(product.get("handle") or ""))
        if not handle:
            return None
        image_url = ""
        image = product.get("image")
        if isinstance(image, dict):
            image_url = _normalize_image_url(image.get("src") or image.get("url"))
        if not image_url:
            images = product.get("images")
            if isinstance(images, list) and images:
                first = images[0]
                if isinstance(first, dict):
                    image_url = _normalize_image_url(first.get("src") or first.get("url"))
                else:
                    image_url = _normalize_image_url(first)
        price = _format_price(_parse_price(product.get("sale_price") or product.get("price") or product.get("original_price")))
        return {
            "handle": handle,
            "id": product.get("id") or "",
            "title": _clean_text(product.get("title")),
            "image": image_url,
            "price": price,
            "_searchspring_raw": product.get("_searchspring_raw") or item,
            "_collection_order": order,
            "_source": "frontend_searchspring_response",
        }

    # DOM 兜底：只看 main 区域中真实可见商品链接，避免 body/script 隐藏链接污染顺序。
    js_extract_dom_state = r"""
() => {
  const normalize = (href) => {
    try {
      if (!href) return '';
      const url = String(href).startsWith('http') ? new URL(String(href)) : new URL(String(href), window.location.origin);
      if (url.hostname && url.hostname !== window.location.hostname) return '';
      if (!url.pathname.includes('/products/')) return '';
      let handle = url.pathname.split('/products/')[1] || '';
      handle = handle.split('/')[0].split('?')[0].split('#')[0].trim().toLowerCase();
      if (!handle || handle.endsWith('.js') || handle.endsWith('.json') || handle.endsWith('.oembed')) return '';
      if (!/^[a-z0-9][a-z0-9-]*[a-z0-9]$/.test(handle)) return '';
      return handle;
    } catch (e) { return ''; }
  };

  const isVisible = (el) => {
    try {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 8 && rect.height > 8 && style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    } catch (e) { return false; }
  };

  const badArea = (el) => !!el.closest(
    'header, footer, nav, aside, [role="dialog"], [aria-modal="true"], '
    + '[class*="drawer" i], [class*="modal" i], [class*="menu" i], [class*="cart" i], '
    + '[class*="recent" i], [class*="recommend" i], [class*="related" i], '
    + '[class*="upsell" i], [class*="wishlist" i], [class*="predictive" i]'
  );

  const anchors = Array.from(document.querySelectorAll('main a[href*="/products/"], [role="main"] a[href*="/products/"]'));
  const byHandle = new Map();
  for (const a of anchors) {
    if (badArea(a) || !isVisible(a)) continue;
    const handle = normalize(a.getAttribute('href') || a.href || '');
    if (!handle) continue;
    const card = a.closest('[data-product-card], [data-product-id], [data-product-handle], [class*="product" i], li, article, div') || a;
    if (!card || badArea(card) || !isVisible(card)) continue;
    const rect = card.getBoundingClientRect();
    if (rect.width < 80 || rect.height < 80) continue;
    // 只累计当前页面流中的卡片；不从隐藏模板取链接。
    if (rect.bottom < -300 || rect.top > window.innerHeight + 3200) continue;
    const img = card.querySelector('img');
    const image = img ? (img.currentSrc || img.src || img.getAttribute('data-src') || '') : '';
    const title = ((a.getAttribute('title') || a.getAttribute('aria-label') || a.textContent || card.innerText || '') + '').replace(/\s+/g, ' ').trim();
    const item = {handle, title, image, price: '', top: Math.round(rect.top + window.scrollY), left: Math.round(rect.left + window.scrollX)};
    const old = byHandle.get(handle);
    if (!old || item.top < old.top || (item.top === old.top && item.left < old.left)) byHandle.set(handle, item);
  }

  const bodyText = (document.body.innerText || '').replace(/\s+/g, ' ');
  let productCount = 0;
  const patterns = [/(\d+)\s*(?:products|items|styles|results)/i, /showing\s+\d+\s*-\s*\d+\s+of\s+(\d+)/i];
  for (const re of patterns) {
    const m = bodyText.match(re);
    if (m && m[1]) { productCount = parseInt(m[1], 10) || 0; break; }
  }
  return {items: Array.from(byHandle.values()).sort((a,b) => Math.abs(a.top-b.top)>8 ? a.top-b.top : a.left-b.left), productCount};
}
"""

    js_click_more = r"""
() => {
  const isVisible = (el) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  const textOf = (el) => ((el.innerText || el.textContent || '') + ' ' + (el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '')).trim();
  const candidates = Array.from(document.querySelectorAll('button, a, [role="button"]'));
  for (const el of candidates) {
    if (!isVisible(el)) continue;
    const href = (el.getAttribute('href') || '').toLowerCase();
    if (href.includes('/products/')) continue;
    const text = textOf(el).replace(/\s+/g, ' ').toLowerCase();
    if (!text) continue;
    const looksMore = text.includes('load more') || text.includes('show more') || text.includes('view more') || text.includes('see more') || text.includes('more products') || text.includes('next page') || /^more$/.test(text);
    if (!looksMore) continue;
    try { el.scrollIntoView({block: 'center', inline: 'center'}); el.click(); return true; } catch (e) {}
  }
  return false;
}
"""

    js_scroll_step = r"""
(step) => {
  window.scrollBy(0, step);
  const scrollables = Array.from(document.querySelectorAll('main, [role="main"], [data-product-grid], [data-products-grid], [data-collection-products], [class*="product-grid" i], [class*="collection-products" i], .boost-pfs-filter-products'));
  for (const el of scrollables) {
    try { if (el.scrollHeight > el.clientHeight + 100) el.scrollTop = Math.min(el.scrollTop + step, el.scrollHeight); } catch (e) {}
  }
  return true;
}
"""

    api_refs: list[dict[str, Any]] = []
    api_seen_handles: set[str] = set()
    dom_refs: list[dict[str, Any]] = []
    dom_seen_handles: set[str] = set()
    detected_count = 0
    api_response_count = 0

    def merge_api_response(data: Any, url: str) -> int:
        nonlocal detected_count, api_response_count
        if not isinstance(data, dict):
            return 0
        results = _searchspring_results_from_response(data)
        if not results:
            return 0
        # 只接受当前页面真实触发的 SearchSpring 商品响应，不接受推荐/弹窗等非 PLP 响应。
        lower_url = (url or "").lower()
        if "searchspring" not in lower_url and "ss-" not in lower_url:
            return 0
        total = detect_total_count(data)
        if total > detected_count:
            detected_count = total
        page_no = detect_page_no(url, data)
        added = 0
        for idx, item in enumerate(results, start=1):
            ref = make_ref_from_searchspring_item(item, len(api_refs) + 1)
            if not ref:
                continue
            handle = _normalize_page_handle(str(ref.get("handle") or ""))
            if not handle or handle in api_seen_handles:
                continue
            api_seen_handles.add(handle)
            ref["_frontend_page"] = page_no
            ref["_frontend_index"] = idx
            ref["_collection_order"] = len(api_refs) + 1
            api_refs.append(ref)
            added += 1
        if added:
            api_response_count += 1
            logger.info(
                "Babyboo 前台接口排序响应: page=%s results=%s 新增=%s 累计=%s detected_count=%s url=%s",
                page_no,
                len(results),
                added,
                len(api_refs),
                detected_count or "",
                url.split("?", 1)[0],
            )
        return added

    def merge_dom_state(state: Any) -> int:
        nonlocal detected_count
        if isinstance(state, dict):
            try:
                total = int(state.get("productCount") or 0)
                if total > detected_count:
                    detected_count = total
            except Exception:
                pass
            items = state.get("items")
        else:
            items = state
        if not isinstance(items, list):
            return 0
        added = 0
        for item in items:
            if isinstance(item, dict):
                handle = _normalize_page_handle(str(item.get("handle") or ""))
                title = _clean_text(item.get("title"))
                image = _normalize_image_url(item.get("image"))
                price = _safe_str(item.get("price"))
            else:
                handle = _normalize_page_handle(str(item))
                title = image = price = ""
            if not handle or handle in dom_seen_handles:
                continue
            dom_seen_handles.add(handle)
            dom_refs.append({
                "handle": handle,
                "title": title,
                "image": image,
                "price": price,
                "_collection_order": len(dom_refs) + 1,
                "_source": "rendered_dom_visible_cards",
            })
            added += 1
        return added

    def current_count() -> int:
        return len(api_refs) if api_refs else len(dom_refs)

    def chromium_launch_kwargs() -> dict[str, Any]:
        configured = os.getenv("BB_CHROMIUM_EXECUTABLE_PATH", "").strip()
        candidates = [configured] if configured else []
        candidates.extend([
            shutil.which("chromium") or "",
            shutil.which("chromium-browser") or "",
            shutil.which("google-chrome") or "",
            shutil.which("google-chrome-stable") or "",
        ])
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return {"headless": True, "executable_path": candidate}
        return {"headless": True}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**chromium_launch_kwargs())
            context = browser.new_context(
                user_agent=HEADERS_HTML.get("User-Agent") or "Mozilla/5.0",
                viewport={"width": 1440, "height": 2200},
                locale="en-AU",
            )
            page = context.new_page()

            def on_response(response: Any) -> None:
                try:
                    url = getattr(response, "url", "") or ""
                    lower_url = url.lower()
                    if "searchspring" not in lower_url and "ss-" not in lower_url:
                        return
                    try:
                        data = response.json()
                    except Exception:
                        try:
                            body = response.body()
                            data = json.loads(body.decode("utf-8", errors="ignore"))
                        except Exception:
                            return
                    merge_api_response(data, url)
                except Exception as resp_exc:
                    logger.debug("Babyboo 前台接口响应解析失败: %s", resp_exc)

            page.on("response", on_response)
            page.goto(page_url, wait_until="domcontentloaded", timeout=timeout * 1000)
            page.wait_for_timeout(wait_ms)

            for selector in (
                'button:has-text("Accept")',
                'button:has-text("No thanks")',
                '[aria-label*="close" i]',
                'button[aria-label*="close" i]',
            ):
                try:
                    loc = page.locator(selector).first
                    if loc.is_visible(timeout=500):
                        loc.click(timeout=1000)
                        page.wait_for_timeout(300)
                except Exception:
                    continue
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass

            stable_rounds = 0
            try:
                merge_dom_state(page.evaluate(js_extract_dom_state) or {})
            except Exception:
                pass

            for idx in range(scroll_rounds):
                before_count = current_count()
                clicked_more = False
                try:
                    clicked_more = bool(page.evaluate(js_click_more))
                except Exception:
                    clicked_more = False
                if clicked_more:
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass
                    try:
                        page.wait_for_timeout(scroll_pause_ms)
                    except Exception:
                        pass
                    try:
                        merge_dom_state(page.evaluate(js_extract_dom_state) or {})
                    except Exception:
                        pass

                for _ in range(3):
                    try:
                        page.evaluate(js_scroll_step, scroll_step_px)
                    except Exception:
                        try:
                            page.mouse.wheel(0, scroll_step_px)
                        except Exception:
                            pass
                    try:
                        page.wait_for_timeout(scroll_pause_ms)
                    except Exception:
                        raise
                    try:
                        merge_dom_state(page.evaluate(js_extract_dom_state) or {})
                    except Exception:
                        pass

                after_count = current_count()
                logger.info(
                    "Babyboo 前台真实排序抓取进度: round=%s api_handles=%s dom_handles=%s added=%s clicked_more=%s detected_count=%s",
                    idx + 1,
                    len(api_refs),
                    len(dom_refs),
                    after_count - before_count,
                    clicked_more,
                    detected_count or "",
                )

                target_count = expected_count or detected_count
                if target_count and current_count() >= target_count:
                    break
                if expected_last_handle and (expected_last_handle in api_seen_handles or expected_last_handle in dom_seen_handles):
                    break

                no_new_items = after_count == before_count
                if no_new_items and not clicked_more:
                    stable_rounds += 1
                else:
                    stable_rounds = 0

                # 页面 total 可能比唯一 handle 多 1 个；如果已经接近页面显示总数，
                # 且连续多轮没有新增商品，就以已捕获的前台顺序为准停止。
                if (
                    target_count
                    and detected_count_tolerance
                    and current_count() >= max(0, target_count - detected_count_tolerance)
                    and stable_rounds >= stable_rounds_required
                ):
                    logger.warning(
                        "Babyboo 前台唯一商品数接近页面显示总数，已停止等待缺口：handles=%s detected_count=%s tolerance=%s stable_rounds=%s",
                        current_count(),
                        target_count,
                        detected_count_tolerance,
                        stable_rounds,
                    )
                    break

                if stable_rounds >= stable_rounds_required:
                    break

            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass
    except Exception as exc:
        if api_refs or dom_refs:
            logger.warning(
                "读取 Babyboo 前台真实排序时页面中断，但已累计商品，继续使用已捕获的前台顺序: api=%s dom=%s error=%s",
                len(api_refs),
                len(dom_refs),
                exc,
            )
        else:
            logger.error("读取 Babyboo 前台真实排序失败；为避免错误商品池，不再降级使用 SearchSpring: %s", exc)
            return []

    refs = api_refs if api_refs else dom_refs
    if api_refs:
        logger.info("Babyboo 使用前台 SearchSpring 响应顺序作为最终排序源：responses=%s handles=%s", api_response_count, len(api_refs))
    else:
        logger.info("Babyboo 未捕获前台 SearchSpring 响应，使用可见 DOM 商品卡顺序：handles=%s", len(dom_refs))

    if expected_last_handle and expected_last_handle in {str(item.get("handle") or "") for item in refs}:
        idx = next((i for i, item in enumerate(refs) if item.get("handle") == expected_last_handle), -1)
        if idx >= 0:
            refs = refs[:idx + 1]
            logger.info("Babyboo 已按 BB_EXPECTED_LAST_HANDLE 截断到最后商品: %s，共 %s 个", expected_last_handle, len(refs))

    trim_count = expected_count or detected_count
    if trim_count and len(refs) > trim_count:
        logger.warning("Babyboo 渲染商品数 %s 超过页面显示总数 %s，已按页面总数截断", len(refs), trim_count)
        refs = refs[:trim_count]

    for idx, ref in enumerate(refs, start=1):
        ref["_collection_order"] = idx

    if detected_count and len(refs) != detected_count:
        logger.warning(
            "Babyboo 前台唯一商品数与页面显示总数不完全一致：handles=%s detected_count=%s diff=%s。以页面实际返回的唯一商品顺序为准。",
            len(refs),
            detected_count,
            detected_count - len(refs),
        )
    logger.info(
        "Babyboo 前台真实页面顺序 handles=%s detected_count=%s last=%s",
        len(refs),
        detected_count or "",
        refs[-1].get("handle") if refs else "",
    )
    return refs


def _build_babyboo_skeleton_from_ref(ref: dict[str, Any], base_url: str) -> dict[str, Any]:
    handle = _normalize_page_handle(str(ref.get("handle") or ""))
    price = _parse_price(ref.get("price"))
    image_url = _normalize_image_url(ref.get("image"))
    title = _clean_text(ref.get("title"))
    return {
        "id": ref.get("id") or "",
        "title": title or handle.replace("-", " ").title(),
        "handle": handle,
        "vendor": "Babyboo Fashion",
        "product_type": "",
        "tags": [],
        "body_html": "",
        "description": "",
        "variants": [],
        "images": [{"src": image_url}] if image_url else [],
        "image": {"src": image_url} if image_url else None,
        "price": price,
        "sale_price": price,
        "compare_at_price": "",
        "original_price": price,
        "totalInventory": None,
        "_source_base_url": base_url,
        "_source": "rendered_page",
        "_collection_order": int(ref.get("_collection_order") or 0),
    }

# =========================
# SearchSpring category.json 商品发现
# =========================

def _first_non_empty(*values: Any) -> Any:
    """返回第一个非空值；兼容 SearchSpring 字段多版本命名。"""
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        return value
    return ""


def _as_text_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(_as_text_list(item))
        return result

    text = str(value).strip()
    if not text:
        return []

    # SearchSpring tags / collection_handle 有时是逗号分隔或管道分隔。
    parts = re.split(r",|\|", text)
    return [part.strip() for part in parts if part.strip()]


def _searchspring_results_from_response(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    """兼容 SearchSpring category/search/native 不同返回结构。"""
    if not isinstance(data, dict):
        return []

    candidates = [
        data.get("results"),
        data.get("products"),
        data.get("items"),
        data.get("data", {}).get("results") if isinstance(data.get("data"), dict) else None,
        data.get("response", {}).get("docs") if isinstance(data.get("response"), dict) else None,
    ]

    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]

    return []




def _normalize_babyboo_searchspring_result(item: dict[str, Any], base_url: str, order: int) -> dict[str, Any] | None:
    """把 SearchSpring category.json result 规范成当前 Babyboo 后续流程可复用的 Shopify-like product。"""
    if not isinstance(item, dict):
        return None

    product_url = _safe_str(
        _first_non_empty(
            item.get("url"),
            item.get("product_url"),
            item.get("productUrl"),
            item.get("link"),
            item.get("permalink"),
        )
    )

    handle = _safe_str(
        _first_non_empty(
            item.get("handle"),
            item.get("product_handle"),
            item.get("productHandle"),
            item.get("ss_handle"),
            item.get("url_handle"),
            item.get("slug"),
        )
    )

    if not handle and product_url:
        handle = _extract_handle_from_product_url(product_url)

    if handle:
        handle = handle.split("/products/")[-1].split("?")[0].split("#")[0].strip("/")

    title = _clean_text(
        _first_non_empty(
            item.get("title"),
            item.get("name"),
            item.get("product_name"),
            item.get("productName"),
            item.get("ss_name"),
        )
    )

    if not handle and title:
        handle = _slugify(title)

    if not handle:
        return None

    product_id = _extract_numeric_id(
        _first_non_empty(
            item.get("product_id"),
            item.get("productId"),
            item.get("shopify_product_id"),
            item.get("shopifyProductId"),
            item.get("uid"),
            item.get("id"),
        )
    )

    image_url = _normalize_image_url(
        _first_non_empty(
            item.get("imageUrl"),
            item.get("image_url"),
            item.get("thumbnailImageUrl"),
            item.get("thumbnail_image_url"),
            item.get("thumbnail"),
            item.get("image"),
            item.get("image_url_1"),
        )
    )

    price = _parse_price(
        _first_non_empty(
            item.get("price"),
            item.get("sale_price"),
            item.get("salePrice"),
            item.get("price_min"),
            item.get("min_price"),
        )
    )

    compare_price = _parse_price(
        _first_non_empty(
            item.get("compare_at_price"),
            item.get("compareAtPrice"),
            item.get("msrp"),
            item.get("list_price"),
            item.get("retail_price"),
            item.get("original_price"),
        )
    )

    if compare_price and price and compare_price < price:
        compare_price = 0.0

    tags: list[str] = []
    for key in ("tags", "tag", "ss_tags", "collections", "collection_handle", "category", "categories"):
        tags.extend(_as_text_list(item.get(key)))

    sku = _safe_str(_first_non_empty(item.get("sku"), item.get("ss_sku"), item.get("variant_sku")))
    variant_title = _safe_str(_first_non_empty(item.get("variant_title"), item.get("variantTitle"))) or "Default Title"

    available_value = _first_non_empty(
        item.get("available"),
        item.get("availableForSale"),
        item.get("in_stock"),
        item.get("stock"),
    )
    available = True
    if isinstance(available_value, str):
        available = available_value.strip().lower() not in {"0", "false", "no", "n", "out of stock", "sold out"}
    elif available_value not in [None, ""]:
        available = bool(available_value)

    searchspring_sizes = _extract_sizes_from_searchspring_item(item)
    selected_options = []
    if searchspring_sizes:
        # SearchSpring 单条 result 通常是商品级；这里仅作为 GraphQL 失败时的尺码兜底。
        selected_options = [{"name": "Size", "value": searchspring_sizes[0]}]

    variants = [
        {
            "id": _safe_str(_first_non_empty(item.get("variant_id"), item.get("variantId"), sku)),
            "title": variant_title,
            "sku": sku,
            "price": price,
            "compare_at_price": compare_price if compare_price > price else "",
            "available": available,
            "featured_image": {"src": image_url} if image_url else None,
            "selectedOptions": selected_options,
        }
    ]

    description = _clean_text(
        _first_non_empty(
            item.get("description"),
            item.get("body_html"),
            item.get("bodyHtml"),
            item.get("short_description"),
        )
    )

    return {
        "id": int(product_id) if product_id else "",
        "title": title,
        "handle": handle,
        "vendor": _safe_str(item.get("vendor")) or "Babyboo Fashion",
        "product_type": _safe_str(_first_non_empty(item.get("product_type"), item.get("productType"))) or "",
        "tags": list(dict.fromkeys(tags)),
        "body_html": description,
        "description": description,
        "variants": variants,
        "images": [{"src": image_url}] if image_url else [],
        "image": {"src": image_url} if image_url else None,
        "price": price,
        "sale_price": price,
        "compare_at_price": compare_price if compare_price > price else "",
        "original_price": compare_price if compare_price > price else price,
        "totalInventory": None,
        "_searchspring_sizes": searchspring_sizes,
        "_source_base_url": base_url,
        "_source": "searchspring_category",
        "_searchspring_raw": item,
        "_collection_order": order,
    }



# =========================
# Playwright View More GraphQL 监听
# =========================







# =========================
# HTML / products.json / product.js 兜底
# =========================

class BabybooCollectionHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.handles: list[str] = []
        self._seen_handles: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k: v for k, v in attrs}

        for key in ["href", "data-url", "data-product-url", "data-href"]:
            href = attrs_dict.get(key) or ""
            handle = _extract_handle_from_product_url(href)

            if handle and handle not in self._seen_handles:
                self._seen_handles.add(handle)
                self.handles.append(handle)






def _clone_session_for_worker(session: requests.Session) -> requests.Session:
    """为并发 worker 创建独立 session，同时保留代理和公共 headers。"""
    local_session = requests.Session()
    try:
        local_session.headers.update(session.headers)
    except Exception:
        pass
    try:
        local_session.proxies.update(session.proxies)
    except Exception:
        pass
    return local_session


def _fetch_product_json(
    session: requests.Session,
    base_url: str,
    handle: str,
    timeout: int,
) -> dict[str, Any] | None:
    """读取 Shopify /products/{handle}.json，作为 .js 失败时的快速兜底。"""
    clean_handle = _normalize_page_handle(handle)
    if not clean_handle:
        return None

    url = f"{base_url.rstrip('/')}/products/{clean_handle}.json"
    data = _fetch_json_get(
        session,
        url,
        headers=HEADERS_JSON,
        timeout=timeout,
        retries=1,
    )
    if not isinstance(data, dict):
        return None

    product = data.get("product") if isinstance(data.get("product"), dict) else data
    if not isinstance(product, dict):
        return None

    product["handle"] = _normalize_page_handle(product.get("handle") or clean_handle) or clean_handle
    product["_source_base_url"] = base_url
    product["_source"] = "product_json"
    return product


def _fetch_product_js(
    session: requests.Session,
    base_url: str,
    handle: str,
    timeout: int,
) -> dict[str, Any] | None:
    """快速读取 Shopify /products/{handle}.js。

    注意：这个函数只负责给页面白名单内商品补详情、价格和 variants；
    调用方必须按页面白名单过滤结果，不能用这里返回的数据扩商品池。
    """
    clean_handle = _normalize_page_handle(handle)
    if not clean_handle:
        return None

    url = f"{base_url.rstrip('/')}/products/{clean_handle}.js"
    data = _fetch_json_get(
        session,
        url,
        headers=HEADERS_JSON,
        timeout=timeout,
        retries=1,
    )

    if not isinstance(data, dict):
        return _fetch_product_json(session, base_url, clean_handle, timeout)

    data["handle"] = _normalize_page_handle(data.get("handle") or clean_handle) or clean_handle
    data["_source_base_url"] = base_url
    data["_source"] = "product_js"
    return data


def _fetch_product_js_batch(
    session: requests.Session,
    base_url: str,
    handles: list[str],
    timeout: int,
) -> dict[str, dict[str, Any]]:
    """并发补页面白名单商品的 product.js/json 详情。

    这是当前 BB 的主要快速补详情链路：
    - 商品池和排序仍然只来自前台列表页 page_handles；
    - product.js/json 只能补这些 handle 的详情、价格、variants、尺码；
    - 任何返回 handle 不在白名单里的数据都会在主流程被丢弃。
    """
    # 当前 BB 最终口径：product.js/json 是页面白名单商品的主详情/尺码补充链路，
    # 不允许再被 .env 中旧开关关闭。
    # 之前如果本地残留 BB_ENABLE_PRODUCT_JS_MISSING=false，
    # 会直接跳过快速补详情，导致所有商品进入慢速 PDP 兜底。

    clean_handles: list[str] = []
    seen: set[str] = set()
    for handle in handles:
        clean = _normalize_page_handle(handle)
        if clean and clean not in seen:
            seen.add(clean)
            clean_handles.append(clean)

    workers = max(2, min(_env_int("BB_PRODUCT_JS_WORKERS", 8), 12))
    sleep_seconds = max(0.0, min(_env_float("BB_PRODUCT_JS_SLEEP_SECONDS", 0.05), 0.2))
    request_timeout = max(5, min(int(timeout or 12), 15))

    logger.info(
        "开始并发请求 Babyboo product.js/json：handles=%s workers=%s sleep=%s timeout=%s",
        len(clean_handles), workers, sleep_seconds, request_timeout,
    )

    result: dict[str, dict[str, Any]] = {}

    def fetch_with_delay(handle: str) -> tuple[str, dict[str, Any] | None]:
        if sleep_seconds:
            time.sleep(sleep_seconds)
        local_session = _clone_session_for_worker(session)
        return handle, _fetch_product_js(local_session, base_url, handle, request_timeout)

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="BBProductJS") as executor:
        future_map = {executor.submit(fetch_with_delay, handle): handle for handle in clean_handles}

        for idx, future in enumerate(as_completed(future_map), start=1):
            handle = future_map[future]
            try:
                requested_handle, product = future.result()
            except Exception as exc:
                logger.warning("product.js/json 异常: handle=%s | %s", handle, exc)
                continue

            if not product:
                continue

            clean_returned = _normalize_page_handle(product.get("handle") or requested_handle)
            if not clean_returned:
                continue
            result[clean_returned] = product

            if idx % 25 == 0 or idx == len(clean_handles):
                detail_count = sum(1 for p in result.values() if _pdp_has_detail(p))
                variant_count = sum(1 for p in result.values() if _pdp_has_variant_data(p))
                logger.info(
                    "Babyboo product.js/json 进度: %s/%s 成功=%s 有详情=%s 有尺码数据=%s",
                    idx, len(clean_handles), len(result), detail_count, variant_count,
                )

    logger.info("Babyboo product.js/json 快速补详情完成：成功=%s / handles=%s", len(result), len(clean_handles))
    return result


# =========================
# Webyze ProductColors
# =========================







# =========================
# Shopify Storefront GraphQL
# =========================















def _money_amount(value: Any) -> float:
    """Parse Shopify Storefront MoneyV2 / loose price values."""
    if value is None:
        return 0.0
    if isinstance(value, dict):
        return _parse_price(value.get("amount") or value.get("value") or value.get("price"))
    return _parse_price(value)


def _graphql_str(value: str) -> str:
    """Safely quote a string for inline GraphQL query fields."""
    return json.dumps(str(value or ""))


def _post_graphql_raw(
    session: requests.Session,
    graphql_url: str,
    *,
    payload: dict[str, Any],
    timeout: int,
) -> tuple[int, dict[str, Any] | None, str]:
    """POST Storefront GraphQL with simple retry for transient errors.

    返回 (status_code, json_data, raw_text)。403/401 直接返回，避免误重试刷请求。
    """
    headers = dict(HEADERS_JSON)
    headers.setdefault("Accept", "application/json")
    for attempt in range(2):
        try:
            response = session.post(graphql_url, headers=headers, json=payload, timeout=timeout)
            text = response.text or ""
            if response.status_code == 200:
                try:
                    data = response.json()
                except ValueError:
                    logger.warning("Babyboo GraphQL JSON 解析失败: %s", text[:300])
                    return response.status_code, None, text
                return response.status_code, data if isinstance(data, dict) else None, text
            if response.status_code in {401, 403}:
                logger.warning("Babyboo GraphQL 访问被拒绝: status=%s text=%s", response.status_code, text[:200])
                return response.status_code, None, text
            if response.status_code == 429 and attempt == 0:
                time.sleep(float(os.getenv("BB_GRAPHQL_429_SLEEP_SECONDS", "2")))
                continue
            logger.warning("Babyboo GraphQL 请求失败: status=%s text=%s", response.status_code, text[:300])
            return response.status_code, None, text
        except requests.RequestException as exc:
            if attempt == 0:
                time.sleep(0.5)
                continue
            logger.warning("Babyboo GraphQL 请求异常: %s", exc)
            return 0, None, str(exc)
    return 0, None, ""


def _build_graphql_query_by_handles(handles: list[str], country: str, variants_first: int) -> str:
    """Build a lightweight Storefront query by handle.

    只查补表必需字段：详情、价格、主图、variants 尺码/available。
    不查 images(first:10)、metafields、inventory 等高复杂度字段。
    """
    fragment = f"""
fragment Data on Product {{
  id
  title
  handle
  vendor
  productType
  description
  descriptionHtml
  tags
  featuredImage {{ url }}
  priceRange {{
    minVariantPrice {{ amount }}
    maxVariantPrice {{ amount }}
  }}
  compareAtPriceRange {{
    minVariantPrice {{ amount }}
    maxVariantPrice {{ amount }}
  }}
  variants(first: {variants_first}) {{
    nodes {{
      id
      title
      sku
      availableForSale
      price {{ amount }}
      compareAtPrice {{ amount }}
      selectedOptions {{ name value }}
      image {{ url }}
    }}
  }}
}}
"""
    parts: list[str] = [fragment, f"query products @inContext(country: {country}) {{"]
    for idx, handle in enumerate(handles):
        clean_handle = _normalize_page_handle(handle)
        if not clean_handle:
            continue
        parts.append(f'  p{idx}: productByHandle(handle: {_graphql_str(clean_handle)}) {{ ...Data }}')
    parts.append("}")
    return "\n".join(parts)


def _normalize_graphql_product_by_handle(gql_product: dict[str, Any], base_url: str) -> dict[str, Any]:
    """Normalize Storefront productByHandle response to Shopify-like product dict used downstream."""
    product_id = _extract_numeric_id(gql_product.get("id"))
    title = _safe_str(gql_product.get("title"))
    handle = _normalize_page_handle(_safe_str(gql_product.get("handle")))

    price_range = gql_product.get("priceRange") if isinstance(gql_product.get("priceRange"), dict) else {}
    compare_range = gql_product.get("compareAtPriceRange") if isinstance(gql_product.get("compareAtPriceRange"), dict) else {}

    min_price = _money_amount(price_range.get("minVariantPrice")) or _money_amount(price_range.get("maxVariantPrice"))
    compare_price = _money_amount(compare_range.get("maxVariantPrice")) or _money_amount(compare_range.get("minVariantPrice"))
    if compare_price and min_price and compare_price < min_price:
        compare_price = 0.0

    image_url = ""
    featured = gql_product.get("featuredImage")
    if isinstance(featured, dict):
        image_url = _normalize_image_url(featured.get("url"))

    variants: list[dict[str, Any]] = []
    variant_nodes = []
    variants_block = gql_product.get("variants")
    if isinstance(variants_block, dict):
        variant_nodes = variants_block.get("nodes") or []

    for node in variant_nodes:
        if not isinstance(node, dict):
            continue
        variant_price = _money_amount(node.get("price")) or min_price
        variant_compare = _money_amount(node.get("compareAtPrice")) or compare_price
        variant_image = ""
        image = node.get("image")
        if isinstance(image, dict):
            variant_image = _normalize_image_url(image.get("url"))
        variants.append({
            "id": node.get("id") or "",
            "title": node.get("title") or "Default Title",
            "sku": node.get("sku") or "",
            "price": variant_price,
            "compare_at_price": variant_compare if variant_compare and variant_compare > variant_price else "",
            "available": bool(node.get("availableForSale", False)),
            "availableForSale": bool(node.get("availableForSale", False)),
            "featured_image": {"src": variant_image or image_url} if (variant_image or image_url) else None,
            "selectedOptions": node.get("selectedOptions") or [],
        })

    return {
        "id": int(product_id) if product_id else "",
        "title": title,
        "handle": handle,
        "vendor": gql_product.get("vendor") or "Babyboo Fashion",
        "product_type": gql_product.get("productType") or "",
        "tags": gql_product.get("tags") or [],
        "body_html": gql_product.get("descriptionHtml") or "",
        "description": gql_product.get("description") or "",
        "variants": variants,
        "images": [{"src": image_url}] if image_url else [],
        "image": {"src": image_url} if image_url else None,
        "price": min_price,
        "sale_price": min_price,
        "compare_at_price": compare_price if compare_price and compare_price > min_price else "",
        "original_price": compare_price if compare_price and compare_price > min_price else min_price,
        "_source_base_url": base_url,
        "_source": "graphql_product_by_handle",
    }


def _fetch_graphql_products_by_handles_batch(
    session: requests.Session,
    graphql_url: str,
    handles: list[str],
    base_url: str,
    timeout: int,
) -> dict[str, dict[str, Any]] | None:
    """Fetch one GraphQL batch. 返回 None 表示 complexity exceeded，需要上层拆分 batch。"""
    clean_handles: list[str] = []
    seen: set[str] = set()
    for handle in handles:
        clean = _normalize_page_handle(handle)
        if clean and clean not in seen:
            seen.add(clean)
            clean_handles.append(clean)
    if not clean_handles:
        return {}

    country = "AU"  # 当前 BB 抓取主站 /collections/bridesmaid，价格口径固定 AUD。
    variants_first = max(1, min(_env_int("BB_GRAPHQL_VARIANTS_FIRST", 50), 50))
    query = _build_graphql_query_by_handles(clean_handles, country, variants_first)
    status, data, text = _post_graphql_raw(session, graphql_url, payload={"query": query}, timeout=timeout)

    if status == 429 and ("MAX_COMPLEXITY_EXCEEDED" in text or "Complexity exceeded" in text):
        return None
    if data and data.get("errors"):
        errors_text = json.dumps(data.get("errors"), ensure_ascii=False)
        if "MAX_COMPLEXITY_EXCEEDED" in errors_text or "Complexity exceeded" in errors_text:
            logger.warning("GraphQL Complexity exceeded: %s", errors_text[:300])
            return None
        logger.warning("Babyboo GraphQL errors: %s", data.get("errors"))
    if not data or not isinstance(data.get("data"), dict):
        return {}

    data_block = data.get("data") or {}
    result: dict[str, dict[str, Any]] = {}
    for idx, handle in enumerate(clean_handles):
        product = data_block.get(f"p{idx}")
        if isinstance(product, dict):
            normalized = _normalize_graphql_product_by_handle(product, base_url)
            clean_handle = _normalize_page_handle(normalized.get("handle") or handle)
            if clean_handle:
                result[clean_handle] = normalized
    return result


def _fetch_graphql_products_by_handles_all(
    session: requests.Session,
    base_url: str,
    handles: list[str],
    timeout: int,
) -> dict[str, dict[str, Any]]:
    """Batch fetch details for page whitelist handles using Storefront GraphQL.

    只按 handle 查询页面白名单内商品；不决定商品池、不决定排序。
    """
    graphql_url = BB_GRAPHQL_URL
    clean_handles: list[str] = []
    seen: set[str] = set()
    for handle in handles:
        clean = _normalize_page_handle(handle)
        if clean and clean not in seen:
            seen.add(clean)
            clean_handles.append(clean)

    configured_batch = _env_int("BB_GRAPHQL_BATCH_SIZE", 12)
    default_batch_size = max(1, min(configured_batch, 15))
    configured_min = _env_int("BB_GRAPHQL_MIN_BATCH_SIZE", 1)
    min_batch_size = max(1, min(configured_min, default_batch_size))

    logger.info(
        "开始 Babyboo GraphQL 批量补详情/价格/尺码：handles=%s batch_size=%s variants_first<=50",
        len(clean_handles),
        default_batch_size,
    )

    result: dict[str, dict[str, Any]] = {}

    def fetch_range(batch_handles: list[str]) -> dict[str, dict[str, Any]]:
        if not batch_handles:
            return {}
        batch_result = _fetch_graphql_products_by_handles_batch(
            session=session,
            graphql_url=graphql_url,
            handles=batch_handles,
            base_url=base_url,
            timeout=timeout,
        )
        if batch_result is not None:
            return batch_result
        if len(batch_handles) <= min_batch_size:
            logger.warning("GraphQL batch 已降到最小仍超复杂度，跳过 handles=%s", batch_handles)
            return {}
        mid = len(batch_handles) // 2
        logger.warning("GraphQL batch complexity exceeded，自动拆分：%s -> %s + %s", len(batch_handles), mid, len(batch_handles) - mid)
        left = fetch_range(batch_handles[:mid])
        time.sleep(0.05)
        right = fetch_range(batch_handles[mid:])
        merged: dict[str, dict[str, Any]] = {}
        merged.update(left)
        merged.update(right)
        return merged

    for i in range(0, len(clean_handles), default_batch_size):
        batch = clean_handles[i:i + default_batch_size]
        batch_result = fetch_range(batch)
        result.update(batch_result)
        logger.info(
            "Babyboo GraphQL batch %s-%s 返回=%s 累计=%s",
            i + 1,
            i + len(batch),
            len(batch_result),
            len(result),
        )
        time.sleep(0.05)

    logger.info("Babyboo GraphQL 白名单详情补充完成：成功=%s / handles=%s", len(result), len(clean_handles))
    return result


def _is_unresolved_webyze_only_product(product: dict[str, Any]) -> bool:
    """
    判断是否为 Webyze-only 且详情不可访问的商品。

    这类商品通常满足：
    1. 来源于 Webyze 颜色组；
    2. 没有 GraphQL 价格；
    3. 没有 GraphQL / product.js 详情文案；
    4. 没有 tags；
    5. 只剩 title / handle / image 这类基础信息。

    这种商品大概率是旧颜色、下架颜色、未发布颜色或当前 CA 站不可访问颜色，
    不写入 Excel，避免污染报表。
    """
    has_webyze_group = bool(product.get("_webyze_group_id"))

    has_price = bool(
        _parse_price(
            product.get("price")
            or product.get("sale_price")
            or product.get("price_min")
        )
    )

    has_description = bool(
        _clean_text(product.get("body_html"))
        or _clean_text(product.get("description"))
    )

    has_tags = bool(_get_tags(product))

    return has_webyze_group and not has_price and not has_description and not has_tags




def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip() or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)).strip() or default)
    except ValueError:
        return default


def _html_to_visible_text_for_bb(html: str) -> str:
    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<noscript\b[^>]*>.*?</noscript>", " ", html, flags=re.I | re.S)
    text = unescape(html)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_focused_bb_pdp_text(visible_text: str) -> str:
    """优先抽取 Product Details / Size + Fit 周边文案。"""
    text = re.sub(r"\s+", " ", visible_text or "").strip()
    if not text:
        return ""

    lower = text.lower()
    starts = ["product details", "details"]
    stop_words = [
        "size + fit", "size & fit", "shipping", "returns", "reviews",
        "you may also", "complete the look", "recently viewed", "recommended",
        "shop similar", "customers also", "faq",
    ]

    chunks: list[str] = []
    for start_word in starts:
        start = lower.find(start_word)
        if start < 0:
            continue
        end_candidates = [lower.find(stop, start + len(start_word)) for stop in stop_words]
        end_candidates = [idx for idx in end_candidates if idx > start]
        end = min(end_candidates) if end_candidates else min(len(text), start + 3000)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

    if chunks:
        return " ".join(chunks)

    # Next/Shopify 页面结构变化时兜底前半段，避免整页导航污染太重。
    return text[:16000]


def _fetch_bb_pdp_attr_text(
    session: requests.Session,
    base_url: str,
    handle: str,
    timeout: int,
    *,
    raise_retryable: bool = False,
) -> tuple[str, str]:
    handle = _safe_str(handle).strip("/")
    if not handle or "." in handle:
        return "", ""

    url = f"{base_url.rstrip('/')}/products/{handle}"
    headers = {
        **HEADERS_HTML,
        "Referer": f"{base_url.rstrip('/')}/collections/{BB_COLLECTION_HANDLE}",
    }

    try:
        response = session.get(url, headers=headers, timeout=timeout)
        if response.status_code != 200:
            if raise_retryable:
                classify_http_status(response.status_code, url)
            if response.status_code not in {403, 404, 410}:
                logger.debug("Babyboo PDP 属性补抓失败: status=%s url=%s", response.status_code, url)
            return "", ""

        visible = _html_to_visible_text_for_bb(response.text)
        focused = _extract_focused_bb_pdp_text(visible)

        jsonld_chunks: list[str] = []
        for match in re.finditer(
            r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
            response.text,
            flags=re.I | re.S,
        ):
            raw = unescape(match.group(1)).strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                data = raw
            jsonld_chunks.append(_clean_text(json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data))

        return focused, " ".join(jsonld_chunks).strip()

    except Exception as exc:
        if raise_retryable and is_retryable_exception(exc):
            raise RetryableTaskError(f"Babyboo PDP retryable error handle={handle}: {exc}") from exc
        logger.debug("Babyboo PDP 属性补抓异常: handle=%s | %s", handle, exc)
        return "", ""



def _iter_nested_json_objects(value: Any):
    """深度遍历 JSON 对象，用于从 PDP HTML 内嵌数据里找 product/variant。"""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_nested_json_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_nested_json_objects(child)


def _load_json_fragment(raw: str) -> Any | None:
    text = unescape(raw or "").strip()
    if not text:
        return None
    for old, new in {
        r"\u003c": "<",
        r"\u003e": ">",
        r"\u0026": "&",
        r"\u002F": "/",
        r"\/": "/",
    }.items():
        text = text.replace(old, new)
    try:
        return json.loads(text)
    except Exception:
        return None


def _extract_json_script_objects(html: str) -> list[Any]:
    """读取 PDP 页面中真实渲染用的 JSON/script 数据。"""
    objects: list[Any] = []
    for match in re.finditer(r"<script[^>]*>(.*?)</script>", html or "", flags=re.I | re.S):
        raw = match.group(1).strip()
        if not raw:
            continue
        attrs_start = (html or "").rfind("<script", 0, match.start(1))
        attrs_end = (html or "").find(">", attrs_start)
        attrs = (html or "")[attrs_start:attrs_end + 1].lower() if attrs_start >= 0 and attrs_end >= attrs_start else ""
        # 优先解析 script type=json / ld+json；这些通常包含 product 和 variants。
        if "application/json" in attrs or "application/ld+json" in attrs:
            data = _load_json_fragment(raw)
            if data is not None:
                objects.append(data)
            continue
        # 某些 Hydrogen/Shopify 页面会在普通 script 中内嵌 variants/product JSON。
        if '"variants"' not in raw and "'variants'" not in raw and '"Product"' not in raw:
            continue
        decoder = json.JSONDecoder()
        for brace_match in re.finditer(r"[\{\[]", raw):
            fragment = raw[brace_match.start():]
            try:
                data, _idx = decoder.raw_decode(fragment)
            except Exception:
                continue
            if isinstance(data, (dict, list)):
                objects.append(data)
                break
    return objects


def _json_product_score(obj: dict[str, Any], handle: str) -> int:
    score = 0
    lower_handle = _normalize_page_handle(handle)
    obj_handle = _normalize_page_handle(obj.get("handle") or obj.get("productHandle") or obj.get("slug") or "")
    if lower_handle and obj_handle == lower_handle:
        score += 80
    if isinstance(obj.get("variants"), list) and obj.get("variants"):
        score += 40
    if obj.get("title") or obj.get("name"):
        score += 15
    if obj.get("description") or obj.get("body_html") or obj.get("descriptionHtml"):
        score += 15
    if obj.get("price") or obj.get("price_min") or obj.get("offers"):
        score += 10
    return score


def _find_best_pdp_product_json(html: str, handle: str) -> dict[str, Any]:
    """从 PDP HTML 内嵌 JSON 中找到最像当前商品的 product 对象。"""
    best: dict[str, Any] = {}
    best_score = 0
    for data in _extract_json_script_objects(html):
        for obj in _iter_nested_json_objects(data):
            if not isinstance(obj, dict):
                continue
            # product 容器常见结构：{"product": {...}}
            product_obj = obj.get("product") if isinstance(obj.get("product"), dict) else obj
            if not isinstance(product_obj, dict):
                continue
            if not (
                product_obj.get("title")
                or product_obj.get("name")
                or product_obj.get("handle")
                or product_obj.get("variants")
                or product_obj.get("offers")
            ):
                continue
            score = _json_product_score(product_obj, handle)
            if score > best_score:
                best_score = score
                best = product_obj
    return best


def _normalize_pdp_variant(variant: dict[str, Any], option_names: list[str] | None = None) -> dict[str, Any]:
    if not isinstance(variant, dict):
        return {}
    normalized = dict(variant)

    options = variant.get("options")
    if isinstance(options, list):
        for idx, value in enumerate(options[:3], start=1):
            normalized.setdefault(f"option{idx}", value)
            if option_names and idx - 1 < len(option_names):
                selected = normalized.setdefault("selectedOptions", [])
                if isinstance(selected, list):
                    selected.append({"name": option_names[idx - 1], "value": value})

    selected = normalized.get("selectedOptions") or normalized.get("selected_options")
    if not selected and isinstance(variant.get("selected_options"), list):
        normalized["selectedOptions"] = variant.get("selected_options")

    if "available" not in normalized:
        for key in ["availableForSale", "available_for_sale", "isAvailable", "inStock", "inventoryAvailable"]:
            if key in variant:
                normalized["available"] = bool(variant.get(key))
                break
    if "available" not in normalized:
        for key in ["quantityAvailable", "inventory_quantity", "inventoryQuantity"]:
            if key in variant:
                try:
                    normalized["available"] = int(float(str(variant.get(key)))) > 0
                    break
                except Exception:
                    pass

    # Shopify product JSON 里的 price 常见为 cents。
    if "price" not in normalized:
        for key in ["priceV2", "priceAmount", "amount"]:
            value = variant.get(key)
            if isinstance(value, dict):
                value = value.get("amount")
            if value not in [None, ""]:
                normalized["price"] = value
                break
    return normalized


def _normalize_variants_from_pdp_json(product_json: dict[str, Any]) -> list[dict[str, Any]]:
    variants = product_json.get("variants") if isinstance(product_json, dict) else []
    if isinstance(variants, dict):
        # GraphQL edges/nodes 结构。
        if isinstance(variants.get("nodes"), list):
            variants = variants.get("nodes")
        elif isinstance(variants.get("edges"), list):
            variants = [edge.get("node") for edge in variants.get("edges") if isinstance(edge, dict)]
    if not isinstance(variants, list):
        return []

    option_names: list[str] = []
    options = product_json.get("options") if isinstance(product_json, dict) else []
    if isinstance(options, list):
        for option in options:
            if isinstance(option, dict):
                name = _clean_text(option.get("name"))
            else:
                name = _clean_text(option)
            if name:
                option_names.append(name)

    result: list[dict[str, Any]] = []
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        item = _normalize_pdp_variant(variant, option_names)
        if item:
            result.append(item)
    return result


def _variants_from_size_controls(html: str) -> list[dict[str, Any]]:
    """从 PDP 可见尺码按钮/option 中兜底解析尺码。只在内嵌 variant JSON 缺失时使用。"""
    if not html:
        return []
    # 限定在 size 周边窗口，避免误读 footer / size guide 中的数字。
    decoded = unescape(html)
    lower = decoded.lower()
    starts = [idx for marker in ["size", "select size", "choose size"] for idx in [lower.find(marker)] if idx >= 0]
    if not starts:
        return []
    start = min(starts)
    window = decoded[start:start + 20000]

    variants: list[dict[str, Any]] = []
    seen: set[str] = set()
    tag_re = re.compile(r"<(button|option|label|input|span|div)\b([^>]*)>(.*?)</\1>|<(input)\b([^>]*)/?>", flags=re.I | re.S)
    for match in tag_re.finditer(window):
        attrs = (match.group(2) or match.group(5) or "")
        body = match.group(3) or ""
        candidates = []
        for attr_name in ["value", "data-value", "data-option-value", "aria-label", "title"]:
            attr_match = re.search(rf"{attr_name}\s*=\s*['\"]([^'\"]+)['\"]", attrs, flags=re.I)
            if attr_match:
                candidates.append(attr_match.group(1))
        candidates.append(_clean_text(body))
        size = ""
        for candidate in candidates:
            candidate = _clean_text(candidate)
            if _is_size_candidate(candidate):
                size = candidate
                break
        if not size or size in seen:
            continue
        seen.add(size)
        unavailable = bool(re.search(r"disabled|sold[-_ ]?out|unavailable|oos|is-disabled", attrs + " " + body, flags=re.I))
        variants.append({"title": size, "option1": size, "available": not unavailable})
    return variants


def _extract_jsonld_product_summary(html: str) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for match in re.finditer(r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", html or "", flags=re.I | re.S):
        data = _load_json_fragment(match.group(1))
        for obj in _iter_nested_json_objects(data):
            if not isinstance(obj, dict):
                continue
            typ = obj.get("@type") or obj.get("type")
            if isinstance(typ, list):
                is_product = any(str(t).lower() == "product" for t in typ)
            else:
                is_product = str(typ).lower() == "product"
            if not is_product:
                continue
            summary.setdefault("title", obj.get("name") or obj.get("title"))
            summary.setdefault("description", obj.get("description"))
            image = obj.get("image")
            if isinstance(image, list):
                image = image[0] if image else ""
            summary.setdefault("image", image)
            offers = obj.get("offers")
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if isinstance(offers, dict):
                summary.setdefault("price", offers.get("price") or offers.get("lowPrice"))
            return summary
    return summary


def _extract_pdp_price_from_html(html: str) -> float:
    candidates = re.findall(r"\$\s*([0-9]{2,4}(?:\.[0-9]{1,2})?)", html or "")
    for value in candidates[:20]:
        price = _parse_price(value)
        if price > 0:
            return price
    return 0.0


def _fetch_bb_pdp_product_info(
    session: requests.Session,
    base_url: str,
    handle: str,
    timeout: int,
    *,
    raise_retryable: bool = False,
) -> dict[str, Any]:
    """读取商品 PDP 实际页面，补充详情、尺码、价格、主图和库存。"""
    clean_handle = _normalize_page_handle(handle)
    if not clean_handle:
        return {}

    url = f"{base_url.rstrip('/')}/products/{clean_handle}"
    headers = {
        **HEADERS_HTML,
        "Referer": BB_SOURCE_PAGE_URL,
    }

    try:
        response = session.get(url, headers=headers, timeout=timeout)
        if response.status_code != 200:
            if raise_retryable:
                classify_http_status(response.status_code, url)
            logger.debug("Babyboo PDP 页面读取失败: status=%s url=%s", response.status_code, url)
            return {}

        html = response.text or ""
        product_json = _find_best_pdp_product_json(html, clean_handle)
        jsonld = _extract_jsonld_product_summary(html)
        variants = _normalize_variants_from_pdp_json(product_json)
        if not variants:
            variants = _variants_from_size_controls(html)

        detail_text = _extract_focused_bb_pdp_text(_html_to_visible_text_for_bb(html))
        if not detail_text:
            detail_text = _clean_text(jsonld.get("description") or product_json.get("description") or product_json.get("body_html") or "")

        title = _clean_text(
            product_json.get("title")
            or product_json.get("name")
            or jsonld.get("title")
            or ""
        )

        image = ""
        raw_image = product_json.get("featured_image") or product_json.get("featuredImage") or product_json.get("image") or jsonld.get("image")
        if isinstance(raw_image, dict):
            raw_image = raw_image.get("src") or raw_image.get("url")
        if isinstance(raw_image, list):
            raw_image = raw_image[0] if raw_image else ""
        image = _normalize_image_url(raw_image)

        images: list[dict[str, str]] = []
        if image:
            images.append({"src": image})

        price = _parse_price(product_json.get("price") or product_json.get("price_min") or product_json.get("priceMin") or jsonld.get("price"))
        if not price:
            price = _extract_pdp_price_from_html(html)
        compare_price = _parse_price(product_json.get("compare_at_price") or product_json.get("compareAtPrice") or product_json.get("compare_at_price_max"))

        product: dict[str, Any] = {
            "handle": clean_handle,
            "title": title,
            "body_html": detail_text,
            "description": detail_text,
            "_pdp_detail_text": detail_text,
            "variants": variants,
            "images": images,
            "image": {"src": image} if image else {},
            "price": price,
            "sale_price": price,
            "original_price": compare_price or price,
            "_source": "pdp_page",
        }
        return {k: v for k, v in product.items() if v not in [None, "", [], {}]}
    except Exception as exc:
        if raise_retryable and is_retryable_exception(exc):
            raise RetryableTaskError(f"Babyboo PDP page retryable error handle={clean_handle}: {exc}") from exc
        logger.debug("Babyboo PDP 页面读取异常: handle=%s | %s", clean_handle, exc)
        return {}



def _pdp_has_detail(product: dict[str, Any] | None) -> bool:
    if not isinstance(product, dict):
        return False
    return bool(_clean_text(product.get("body_html") or product.get("description") or product.get("_pdp_detail_text")))


def _pdp_has_variant_data(product: dict[str, Any] | None) -> bool:
    if not isinstance(product, dict):
        return False
    variants = product.get("variants")
    return isinstance(variants, list) and bool(variants)


def _babyboo_chromium_launch_kwargs() -> dict[str, Any]:
    """统一寻找本地 Chromium/Chrome，用于 BB 前台列表页和 PDP 渲染兜底。"""
    configured = os.getenv("BB_CHROMIUM_EXECUTABLE_PATH", "").strip()
    candidates = [configured] if configured else []
    candidates.extend([
        shutil.which("chromium") or "",
        shutil.which("chromium-browser") or "",
        shutil.which("google-chrome") or "",
        shutil.which("google-chrome-stable") or "",
    ])
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return {"headless": True, "executable_path": candidate}
    return {"headless": True}


JS_BB_PDP_RENDERED_STATE = r"""
() => {
  const clean = (value) => String(value || '').replace(/\s+/g, ' ').trim();
  const visible = (el) => {
    try {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    } catch (e) { return false; }
  };
  const sizeRe = /^(XXS|XS|S|M|L|XL|XXL|XXXL|2XL|3XL|4XL|5XL|AU\s*\d{1,2}|US\s*\d{1,2}|UK\s*\d{1,2}|\d{1,2})$/i;
  const badText = /size guide|sizing|measurements|model|height|bust|waist|hips/i;
  const sizes = [];
  const seen = new Set();
  const addSize = (raw, el) => {
    let value = clean(raw).replace(/^size\s*[:：-]?\s*/i, '');
    if (!value || !sizeRe.test(value) || badText.test(value)) return;
    const key = value.toUpperCase().replace(/\s+/g, '');
    if (seen.has(key)) return;
    seen.add(key);
    let attrs = '';
    try {
      attrs = Array.from(el.attributes || []).map(a => `${a.name}=${a.value}`).join(' ');
    } catch(e) {}
    const text = clean((el.innerText || el.textContent || '') + ' ' + attrs);
    const unavailable = !!(
      el.disabled ||
      el.getAttribute('aria-disabled') === 'true' ||
      el.getAttribute('disabled') !== null ||
      /disabled|sold[-_ ]?out|unavailable|out[-_ ]?of[-_ ]?stock|oos|is-disabled/i.test(text)
    );
    sizes.push({title: value.toUpperCase().replace(/^AU\s*/i, ''), option1: value.toUpperCase().replace(/^AU\s*/i, ''), available: !unavailable});
  };

  const candidates = Array.from(document.querySelectorAll(
    'button, [role="button"], label, input, option, select option, [data-option-value], [data-value], [data-size], span, div'
  ));
  for (const el of candidates) {
    if (!visible(el) && el.tagName !== 'OPTION' && el.tagName !== 'INPUT') continue;
    const container = el.closest('fieldset, form, section, [class*="size" i], [data-option-name*="Size" i], [data-option-name*="size" i], [class*="variant" i], [class*="option" i], div') || el;
    const containerText = clean(container.innerText || container.textContent || '');
    const contextLooksLikeSize = /size|select size|choose size|xs|xxs|xxl/i.test(containerText) || /size/i.test((container.className || '') + ' ' + Array.from(container.attributes || []).map(a => `${a.name}=${a.value}`).join(' '));
    if (!contextLooksLikeSize) continue;
    const values = [];
    values.push(el.getAttribute('value'));
    values.push(el.getAttribute('data-value'));
    values.push(el.getAttribute('data-option-value'));
    values.push(el.getAttribute('data-size'));
    values.push(el.getAttribute('aria-label'));
    values.push(el.getAttribute('title'));
    values.push(el.innerText || el.textContent || '');
    for (const value of values) addSize(value, el);
  }

  const bodyText = clean(document.body ? document.body.innerText : '');
  const title = clean((document.querySelector('h1') || {}).innerText || document.title || '');
  const imageEl = document.querySelector('main img[src*="cdn"], main img[src*="shopify"], img[src*="cdn.shopify"], img[src*="babyboofashion"]');
  const image = imageEl ? (imageEl.currentSrc || imageEl.src || imageEl.getAttribute('data-src') || '') : '';
  const priceEl = document.querySelector('[class*="price" i], [data-price], [data-product-price], meta[property="product:price:amount"]');
  const price = priceEl ? clean(priceEl.getAttribute('content') || priceEl.getAttribute('data-price') || priceEl.innerText || priceEl.textContent || '') : '';
  return {bodyText, title, image, price, sizes};
}
"""


def _fetch_bb_pdp_product_info_rendered_page(
    context: Any,
    base_url: str,
    handle: str,
    timeout: int,
) -> dict[str, Any]:
    """用 Playwright 打开真实 PDP 页面，兜底获取 requests HTML 中缺失的详情和尺码。"""
    clean_handle = _normalize_page_handle(handle)
    if not clean_handle:
        return {}

    url = f"{base_url.rstrip('/')}/products/{clean_handle}"
    page = None
    try:
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=max(8000, timeout * 1000))
        page.wait_for_timeout(max(500, _env_int("BB_PDP_RENDER_WAIT_MS", 1200)))
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        state = page.evaluate(JS_BB_PDP_RENDERED_STATE) or {}
        try:
            html = page.content()
        except Exception:
            html = ""

        visible_text = _clean_text(state.get("bodyText"))
        detail_text = _extract_focused_bb_pdp_text(visible_text)
        if not detail_text and html:
            detail_text = _extract_focused_bb_pdp_text(_html_to_visible_text_for_bb(html))
        if not detail_text and html:
            product_json = _find_best_pdp_product_json(html, clean_handle)
            jsonld = _extract_jsonld_product_summary(html)
            detail_text = _clean_text(jsonld.get("description") or product_json.get("description") or product_json.get("body_html") or "")

        variants: list[dict[str, Any]] = []
        for item in state.get("sizes") or []:
            if not isinstance(item, dict):
                continue
            size = _clean_text(item.get("option1") or item.get("title"))
            if not _is_size_candidate(size):
                continue
            variants.append({
                "title": size,
                "option1": size,
                "selectedOptions": [{"name": "Size", "value": size}],
                "available": bool(item.get("available", True)),
            })
        if not variants and html:
            product_json = _find_best_pdp_product_json(html, clean_handle)
            variants = _normalize_variants_from_pdp_json(product_json)
        if not variants and html:
            variants = _variants_from_size_controls(html)

        price = _parse_price(state.get("price"))
        if not price and html:
            price = _extract_pdp_price_from_html(html)
        image = _normalize_image_url(state.get("image"))
        title = _clean_text(state.get("title"))

        product: dict[str, Any] = {
            "handle": clean_handle,
            "title": title,
            "body_html": detail_text,
            "description": detail_text,
            "_pdp_detail_text": detail_text,
            "variants": variants,
            "images": [{"src": image}] if image else [],
            "image": {"src": image} if image else {},
            "price": price,
            "sale_price": price,
            "original_price": price,
            "_source": "pdp_rendered_page",
        }
        return {k: v for k, v in product.items() if v not in [None, "", [], {}]}
    except Exception as exc:
        logger.debug("Babyboo rendered PDP 兜底读取异常: handle=%s | %s", clean_handle, exc)
        return {}
    finally:
        if page is not None:
            try:
                page.close()
            except Exception:
                pass


def _fetch_bb_pdp_products_rendered_fallback(
    base_url: str,
    handles: list[str],
    timeout: int,
) -> dict[str, dict[str, Any]]:
    """对 requests PDP 仍缺详情/尺码的商品，用浏览器打开实际 PDP 页面补齐。"""
    if not handles or not _env_bool("BB_ENABLE_PDP_RENDERED_FALLBACK", True):
        return {}
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        logger.warning("未安装 playwright，无法执行 Babyboo rendered PDP 兜底: %s", exc)
        return {}

    max_products = max(0, _env_int("BB_PDP_RENDERED_FALLBACK_MAX_PRODUCTS", 99999))
    clean_handles: list[str] = []
    seen: set[str] = set()
    for handle in handles:
        clean = _normalize_page_handle(handle)
        if clean and clean not in seen:
            seen.add(clean)
            clean_handles.append(clean)
    if max_products:
        clean_handles = clean_handles[:max_products]
    if not clean_handles:
        return {}

    result: dict[str, dict[str, Any]] = {}
    logger.info("开始 Babyboo rendered PDP 兜底补详情/尺码：handles=%s", len(clean_handles))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**_babyboo_chromium_launch_kwargs())
            context = browser.new_context(
                user_agent=HEADERS_HTML.get("User-Agent") or "Mozilla/5.0",
                viewport={"width": 1440, "height": 1800},
                locale="en-AU",
            )
            for idx, handle in enumerate(clean_handles, start=1):
                product = _fetch_bb_pdp_product_info_rendered_page(context, base_url, handle, timeout)
                if product:
                    result[handle] = product
                if idx % 10 == 0 or idx == len(clean_handles):
                    detail_count = sum(1 for p in result.values() if _pdp_has_detail(p))
                    variant_count = sum(1 for p in result.values() if _pdp_has_variant_data(p))
                    logger.info(
                        "Babyboo rendered PDP 兜底进度: %s/%s 成功=%s 有详情=%s 有尺码数据=%s",
                        idx, len(clean_handles), len(result), detail_count, variant_count,
                    )
            context.close()
            browser.close()
    except Exception as exc:
        logger.warning("Babyboo rendered PDP 兜底整体失败: %s", exc)
    logger.info("Babyboo rendered PDP 兜底完成：成功=%s / handles=%s", len(result), len(clean_handles))
    return result


def _fetch_bb_pdp_products_batch(
    session: requests.Session,
    base_url: str,
    handles: list[str],
    timeout: int,
) -> dict[str, dict[str, Any]]:
    """读取页面白名单内商品 PDP。

    先用 requests 并发读取 PDP HTML；如果仍缺商品详情描述或尺码数据，再用
    Playwright 打开真实商品详情页兜底。这样保留“商品池只来自列表页”的前提，
    同时避免详情/尺码大面积缺失。
    """
    clean_handles: list[str] = []
    seen: set[str] = set()
    for handle in handles:
        clean = _normalize_page_handle(handle)
        if clean and clean not in seen:
            seen.add(clean)
            clean_handles.append(clean)

    workers = max(1, min(_env_int("BB_PDP_PAGE_WORKERS", 8), 12))
    sleep_seconds = max(0.0, min(_env_float("BB_PDP_PAGE_SLEEP_SECONDS", 0.05), 0.3))
    request_timeout = max(6, min(int(timeout or 15), 20))

    logger.info(
        "开始读取 Babyboo PDP HTML详情/尺码：handles=%s workers=%s sleep=%s timeout=%s",
        len(clean_handles), workers, sleep_seconds, request_timeout,
    )

    result: dict[str, dict[str, Any]] = {}

    def fetch_one(handle: str) -> tuple[str, dict[str, Any]]:
        if sleep_seconds:
            time.sleep(sleep_seconds)
        local_session = requests.Session()
        return handle, _fetch_bb_pdp_product_info(local_session, base_url, handle, request_timeout, raise_retryable=False)

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="BBPDPHTML") as executor:
        future_map = {executor.submit(fetch_one, handle): handle for handle in clean_handles}
        for idx, future in enumerate(as_completed(future_map), start=1):
            handle = future_map[future]
            try:
                result_handle, product = future.result()
            except Exception as exc:
                logger.warning("Babyboo PDP HTML详情异常: handle=%s | %s", handle, exc)
                continue
            if product:
                result[result_handle] = product
            if idx % 25 == 0 or idx == len(clean_handles):
                detail_count = sum(1 for p in result.values() if _pdp_has_detail(p))
                variant_count = sum(1 for p in result.values() if _pdp_has_variant_data(p))
                logger.info(
                    "Babyboo PDP HTML详情进度: %s/%s 成功=%s 有详情=%s 有尺码数据=%s",
                    idx, len(clean_handles), len(result), detail_count, variant_count,
                )

    missing_for_rendered = [
        handle for handle in clean_handles
        if not _pdp_has_detail(result.get(handle)) or not _pdp_has_variant_data(result.get(handle))
    ]
    if missing_for_rendered:
        logger.info(
            "Babyboo PDP HTML后仍缺详情/尺码：%s / %s，开始 rendered PDP 兜底",
            len(missing_for_rendered), len(clean_handles),
        )
        rendered_result = _fetch_bb_pdp_products_rendered_fallback(base_url, missing_for_rendered, request_timeout)
        for handle, product in rendered_result.items():
            clean = _normalize_page_handle(handle)
            if not clean:
                continue
            existing = result.get(clean, {})
            result[clean] = _merge_non_empty(existing, product)

    final_detail_count = sum(1 for p in result.values() if _pdp_has_detail(p))
    final_variant_count = sum(1 for p in result.values() if _pdp_has_variant_data(p))
    logger.info(
        "Babyboo PDP 详情/尺码读取完成：成功=%s / handles=%s | 有详情=%s | 有尺码数据=%s",
        len(result), len(clean_handles), final_detail_count, final_variant_count,
    )
    return result


def _needs_bb_pdp_attr_enrich(product: dict[str, Any]) -> bool:
    if not _env_bool("BB_PDP_ATTR_ONLY_MISSING", True):
        return True
    if not product.get("handle"):
        return False
    if _is_unresolved_webyze_only_product(product):
        return False

    style_label, product_name, _color = _split_style_color_name(
        _safe_str(product.get("title")),
        _safe_str(product.get("handle")),
    )
    tags = _get_tags(product)
    attrs = _extract_attrs(product_name or style_label or _safe_str(product.get("title")), tags, product)
    return not (
        attrs.get("fabric_name")
        and attrs.get("aesthetic_tag")
        and attrs.get("length")
        and attrs.get("neckline")
    )


def enrich_babyboo_products_with_pdp_attributes(
    config: Config,
    session: requests.Session,
    base_url: str,
    products_by_handle: dict[str, dict[str, Any]],
    timeout: int,
) -> dict[str, dict[str, Any]]:
    """
    对 GraphQL / Webyze / product.js 仍缺属性的 Babyboo 商品，补抓 PDP 文案。
    只附加 _pdp_detail_text / _pdp_jsonld_text，不覆盖已有价格、图片、库存等结构化字段。
    """
    if not _env_bool("BB_ENABLE_PDP_ATTR_ENRICH", True):
        logger.info("已关闭 Babyboo PDP 属性补抓")
        return products_by_handle

    candidates = [
        handle for handle, product in products_by_handle.items()
        if handle and _needs_bb_pdp_attr_enrich(product)
    ]

    max_products = _env_int("BB_PDP_ATTR_MAX_PRODUCTS", 99999)
    if max_products > 0:
        candidates = candidates[:max_products]

    if not candidates:
        logger.info("Babyboo PDP 属性补抓无候选")
        return products_by_handle

    workers = max(1, _env_int("BB_PDP_ATTR_WORKERS", 6))
    sleep_seconds = max(0.0, _env_float("BB_PDP_ATTR_SLEEP_SECONDS", 0.08))

    logger.info(
        "开始 Babyboo PDP 属性补抓：候选handles=%s workers=%s sleep=%s only_missing=%s",
        len(candidates),
        workers,
        sleep_seconds,
        _env_bool("BB_PDP_ATTR_ONLY_MISSING", True),
    )

    cache: dict[str, tuple[str, str]] = {}
    retry_queue = RetryQueue(site_key="babyboo")

    def fetch_one(handle: str) -> tuple[str, tuple[str, str]]:
        if sleep_seconds:
            time.sleep(sleep_seconds)
        local_session = requests.Session()
        return handle, _fetch_bb_pdp_attr_text(local_session, base_url, handle, timeout, raise_retryable=True)

    def queue_retry(handle: str, error: str) -> None:
        def handler() -> tuple[str, str]:
            local_session = requests.Session()
            return _fetch_bb_pdp_attr_text(local_session, base_url, handle, timeout, raise_retryable=True)

        def on_success(result: tuple[str, str]) -> None:
            cache[handle] = result

        retry_queue.submit(
            task_type="bb_pdp_attr",
            identity_key=handle,
            payload={"handle": handle, "base_url": base_url, "first_error": error},
            handler=handler,
            on_success=on_success,
        )

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="BBPDPAttr") as executor:
        future_map = {executor.submit(fetch_one, handle): handle for handle in candidates}
        for idx, future in enumerate(as_completed(future_map), start=1):
            handle = future_map[future]
            try:
                result_handle, result = future.result()
                cache[result_handle] = result
            except Exception as exc:
                logger.debug("Babyboo PDP 属性补抓并发异常，已进入 retry queue: handle=%s | %s", handle, exc)
                cache[handle] = ("", "")
                queue_retry(handle, str(exc))

            if idx % 50 == 0 or idx == len(candidates):
                success = sum(1 for visible, jsonld in cache.values() if visible or jsonld)
                logger.info("Babyboo PDP 属性补抓进度: %s/%s 成功=%s retry_pending=%s", idx, len(candidates), success, retry_queue.pending_count())

    retry_queue.drain()

    enriched = 0
    for handle, (detail_text, jsonld_text) in cache.items():
        if not (detail_text or jsonld_text):
            continue
        product = products_by_handle.get(handle)
        if not isinstance(product, dict):
            continue
        product["_pdp_detail_text"] = detail_text
        product["_pdp_jsonld_text"] = jsonld_text
        enriched += 1

    logger.info("Babyboo PDP 属性补抓完成：成功补充=%s / 候选=%s", enriched, len(candidates))
    return products_by_handle

# =========================
# 商品抓取主逻辑
# =========================

def fetch_all_babyboo_products(config: Config) -> tuple[list[dict[str, Any]], str]:
    """抓取 Babyboo 指定列表页当前真实展示商品。

    重要：商品池只来自 BB_SOURCE_PAGE_URL 前台渲染后的商品卡片顺序。
    SearchSpring / GraphQL / products.json / Webyze 不再作为商品发现来源，避免官网没有展示的商品进入表格。
    product.js / PDP 只能补这些页面 handle 的详情、价格、尺码。
    """
    base_url = BB_BASE_URL
    collection_handle = BB_COLLECTION_HANDLE
    timeout = int(getattr(config, "request_timeout", 30) or 30)

    session = _make_session(config)

    # 1. 唯一商品发现链路：前台渲染页面真实商品卡片顺序。
    page_refs = _fetch_babyboo_rendered_page_refs(
        base_url=base_url,
        collection_handle=collection_handle,
        timeout=timeout,
    )

    if not page_refs:
        logger.error(
            "Babyboo 未能读取前台真实商品顺序，已停止导出。"
            "请确认 Playwright/Chromium 可用；不要降级使用 SearchSpring，否则会把页面外商品写进表。"
        )
        return [], base_url

    page_handles: list[str] = []
    seen_handles: set[str] = set()
    normalized_refs: list[dict[str, Any]] = []
    for ref in page_refs:
        handle = _normalize_page_handle(str(ref.get("handle") or ""))
        if not handle or handle in seen_handles:
            continue
        seen_handles.add(handle)
        page_handles.append(handle)
        ref = dict(ref)
        ref["handle"] = handle
        ref["_collection_order"] = len(normalized_refs) + 1
        normalized_refs.append(ref)

    page_handle_set = set(page_handles)
    logger.info(
        "Babyboo 页面展示商品白名单=%s，后续详情补充不允许新增页面外商品",
        len(page_handles),
    )

    # 2. 先用页面 DOM 信息建骨架，保证即使详情接口失败，也不会丢失页面真实展示商品。
    products_by_handle: dict[str, dict[str, Any]] = {
        ref["handle"]: _build_babyboo_skeleton_from_ref(ref, base_url)
        for ref in normalized_refs
        if ref.get("handle")
    }

    # 3. 批量补详情/价格/variants/尺码：使用 Storefront GraphQL 按页面白名单 handle 查询。
    #    GraphQL 只补充已在页面中出现的商品，不决定商品池、不改变排序。
    graphql_products = _fetch_graphql_products_by_handles_all(
        session=session,
        base_url=base_url,
        handles=page_handles,
        timeout=timeout,
    )
    for handle, gql_product in graphql_products.items():
        clean_handle = _normalize_page_handle(handle or _safe_str(gql_product.get("handle")))
        if clean_handle not in page_handle_set:
            continue
        existing = products_by_handle.get(clean_handle, {})
        merged = _merge_non_empty(existing, gql_product)
        merged["_source_base_url"] = base_url
        merged["_source"] = "rendered_page_graphql"
        merged["_collection_order"] = existing.get("_collection_order") or (page_handles.index(clean_handle) + 1)
        products_by_handle[clean_handle] = merged

    # 4. 只对 GraphQL 后仍缺详情或尺码的商品读取 PDP。
    #    PDP 仍然只作为补缺链路，不决定商品池、不改变排序。
    missing_for_pdp = [
        handle for handle in page_handles
        if not _pdp_has_detail(products_by_handle.get(handle))
        or not _pdp_has_variant_data(products_by_handle.get(handle))
    ]
    if missing_for_pdp:
        logger.info(
            "Babyboo GraphQL 后仍缺详情/尺码：%s / %s，开始 PDP 兜底",
            len(missing_for_pdp), len(page_handles),
        )
        pdp_products = _fetch_bb_pdp_products_batch(
            session=session,
            base_url=base_url,
            handles=missing_for_pdp,
            timeout=timeout,
        )

        for handle, pdp_product in pdp_products.items():
            clean_handle = _normalize_page_handle(handle or _safe_str(pdp_product.get("handle")))
            if clean_handle not in page_handle_set:
                continue
            existing = products_by_handle.get(clean_handle, {})
            merged = _merge_non_empty(existing, pdp_product)
            merged["_source_base_url"] = base_url
            merged["_source"] = "rendered_page_graphql_pdp"
            merged["_collection_order"] = existing.get("_collection_order") or (page_handles.index(clean_handle) + 1)
            products_by_handle[clean_handle] = merged
    else:
        logger.info("Babyboo GraphQL 已覆盖全部页面商品详情和尺码，无需 PDP 兜底")

    # 4. 最终输出严格按前台页面顺序连续编号；不再用任何接口补齐页面外商品。
    products: list[dict[str, Any]] = []
    for idx, handle in enumerate(page_handles, start=1):
        product = products_by_handle.get(handle)
        if not product:
            continue
        product["_source_base_url"] = base_url
        product["_collection_order"] = idx
        products.append(product)

    logger.info(
        "Babyboo 最终页面展示商品数=%s | page_last=%s | GraphQL 仅补白名单详情，未扩商品池",
        len(products),
        page_handles[-1] if page_handles else "",
    )
    return products, base_url


# =========================
# 记录构建
# =========================

def _make_bb_record(**kwargs: Any) -> CLProductRecord:
    """
    Babyboo 当前复用 CLProductRecord。

    为了避免和不同版本 product_record.py 冲突：
    - 新版 CLProductRecord 支持 brand 字段；
    - 旧版 CLProductRecord 不支持 brand 字段。

    这里会自动按 dataclass 字段过滤 kwargs，保证两种版本都能跑。
    """
    fields = getattr(CLProductRecord, "__dataclass_fields__", {}) or {}
    if fields:
        kwargs = {k: v for k, v in kwargs.items() if k in fields}
    return CLProductRecord(**kwargs)




def _build_delisted_record(
    baseline_mgr: BaselineManager,
    key: str,
    info: dict[str, Any],
    scrape_time: str,
) -> CLProductRecord:
    metadata = info.get("metadata", {}) if isinstance(info.get("metadata"), dict) else {}
    fallback_product_name, fallback_color_name = baseline_mgr.split_key(key)

    return _make_bb_record(
        site_name=metadata.get("site_name", "Babyboo Fashion"),
        brand=metadata.get("brand", "Babyboo Fashion"),
        category=metadata.get("category", "Bridesmaid Dresses"),
        style_label=metadata.get("style_label", ""),
        product_url=metadata.get("product_url", ""),
        product_name=metadata.get("product_name", fallback_product_name),
        color_name=metadata.get("color_name", fallback_color_name),
        size=metadata.get("size", ""),
        main_image_url=metadata.get("main_image_url", ""),
        original_price=metadata.get("original_price", ""),
        sale_price=metadata.get("sale_price", ""),
        discount_type=metadata.get("discount_type", ""),
        stock_type=metadata.get("stock_type", ""),
        detail_text=metadata.get("detail_text", ""),
        fabric_name=metadata.get("fabric_name", ""),
        aesthetic_tag=metadata.get("aesthetic_tag", ""),
        length=metadata.get("length", ""),
        neckline=metadata.get("neckline", ""),
        scrape_time=scrape_time,
        release_date=info.get("first_seen", ""),
        is_new_color="否",
        is_official_new=metadata.get("is_official_new", "否"),
        status="Delisted",
    )


def _build_records(
    products: list[dict[str, Any]],
    baseline_mgr: BaselineManager,
    is_initialization_phase: bool,
    current_date: str,
    current_time_full: str,
) -> tuple[list[CLProductRecord], set[str]]:
    records: list[CLProductRecord] = []
    active_keys: set[str] = set()

    sorted_products = sorted(products, key=lambda item: int(item.get("_collection_order", 999999)))

    for current_rank, product in enumerate(sorted_products, start=1):
        product["_collection_order"] = product.get("_collection_order") or current_rank
        raw_title = _safe_str(product.get("title"))
        handle = _safe_str(product.get("handle"))
        source_base_url = _safe_str(product.get("_source_base_url")) or BB_BASE_URL

        style_label, product_name_from_title, title_color = _split_style_color_name(raw_title, handle)
        product_url = _build_product_url(source_base_url, handle)

        tags = _get_tags(product)
        variants = product.get("variants", []) or []
        has_variant_data = isinstance(variants, list) and bool(variants)
        if not isinstance(variants, list):
            variants = []

        color_groups: dict[str, list[dict[str, Any]]] = {}

        for variant in variants:
            if not isinstance(variant, dict):
                continue

            if title_color and title_color != "Default":
                color_name = title_color
            else:
                variant_color = _extract_variant_color(variant)
                color_name = variant_color or "Default"

            color_groups.setdefault(color_name, []).append(variant)

        if not color_groups:
            color_groups[title_color or "Default"] = []

        attrs = _extract_attrs(product_name_from_title, tags, product)

        for color_name, color_variants in color_groups.items():
            chosen_variant = next(
                (variant for variant in color_variants if variant.get("available", False)),
                color_variants[0] if color_variants else {},
            )

            price = _parse_price(
                chosen_variant.get("price")
                or product.get("price")
                or product.get("sale_price")
                or product.get("price_min")
            )

            compare_price = _parse_price(
                chosen_variant.get("compare_at_price")
                or product.get("compare_at_price")
                or product.get("original_price")
                or product.get("compare_at_price_max")
            )

            original_price = compare_price if compare_price > price else price
            discount_type = "打折" if original_price > price else "无折扣"

            any_available = any(bool(variant.get("available", False)) for variant in color_variants)
            size_text = _format_sizes_for_variants(color_variants, product)
            stock_type = "未知" if not has_variant_data else ("现货" if any_available else "缺货")

            record = _make_bb_record(
                site_name="Babyboo Fashion",
                brand="Babyboo Fashion",
                category="Bridesmaid Dresses",
                style_label=style_label,
                product_url=product_url,
                product_name=product_name_from_title,
                color_name=color_name,
                size=size_text,
                main_image_url=_get_variant_image(product, chosen_variant),
                original_price=_format_price(original_price),
                sale_price=_format_price(price),
                discount_type=discount_type,
                stock_type=stock_type,
                detail_text=collect_product_detail_text(product),
                fabric_name=attrs["fabric_name"],
                aesthetic_tag=attrs["aesthetic_tag"],
                length=attrs["length"],
                neckline=attrs["neckline"],
                scrape_time=current_time_full,
                release_date="",
                is_new_color="否",
                is_official_new=_is_official_new(product),
                status="Active",
            )

            product_key = handle or f"{style_label}::{product_name_from_title}"

            baseline_key = baseline_mgr.make_key(product_key, color_name)
            report_metadata = apply_ranking_context(
                record,
                baseline_mgr,
                baseline_key,
                product_key=product_key,
                current_rank=product.get("_collection_order") or current_rank,
                source_page_url=BB_SOURCE_PAGE_URL,
                current_date=current_date,
            )

            is_new_color, release_date = baseline_mgr.check_and_update(
                product_key,
                color_name,
                current_date,
                metadata=report_metadata,
            )

            sync_change_context_from_metadata(record, report_metadata)
            record.release_date = release_date
            record.is_new_color = "基线写入" if is_initialization_phase else is_new_color

            mark_relisted_after_delisted(record, baseline_mgr, baseline_key)
            if baseline_key in baseline_mgr.baseline:
                baseline_mgr.baseline[baseline_key]["metadata"] = record.to_metadata()
            active_keys.add(baseline_key)

            records.append(record)

    return records, active_keys


# =========================
# 主流程
# =========================

def main() -> None:
    config = Config.load()

    logging.basicConfig(
        level=getattr(logging, getattr(config, "log_level", "INFO"), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    logger.info("========== Babyboo Fashion 自动监控引擎启动 ==========")

    baseline_path = getattr(config, "bb_baseline_path", "babyboo_baseline.json")
    baseline_mgr = BaselineManager(baseline_path)
    output_dir = getattr(config, "output_dir", "output")
    report_prefix = "babyboo_report_"
    is_initialization_phase = is_first_site_crawl(output_dir, report_prefix, baseline_mgr)

    current_dt = resolve_current_datetime()
    current_date = current_dt.strftime("%Y-%m-%d")
    current_time_full = current_dt.strftime("%Y-%m-%d %H:%M:%S")

    products, base_url = fetch_all_babyboo_products(config)

    if not products or not base_url:
        logger.error("Babyboo Fashion 没有抓取到商品，流程结束")
        return

    records, active_keys = _build_records(
        products=products,
        baseline_mgr=baseline_mgr,
        is_initialization_phase=is_initialization_phase,
        current_date=current_date,
        current_time_full=current_time_full,
    )

    delisted_records = mark_and_build_delisted_records(
        baseline_mgr=baseline_mgr,
        active_keys=active_keys,
        current_date=current_date,
        current_time_full=current_time_full,
        build_delisted_record=_build_delisted_record,
    )
    delisted_count = len(delisted_records)


    baseline_mgr.save_baseline()

    sheet_name = getattr(config, "bb_sheet_name", "BB_伴娘服总表")
    output_dir = getattr(config, "output_dir", "output")

    report_sheets = build_report_sheets(
        full_sheet_name=sheet_name,
        records=records,
        delisted_records=delisted_records,
        is_initialization_phase=is_initialization_phase,
        columns_l2=COLUMNS_L2_BB,
    )

    filepath = DataExporter().export_multiple_sheets(
        report_sheets,
        output_dir,
        prefix=report_prefix,
        header_l1=HEADER_L1_CONFIG_BB,
        columns_l2=COLUMNS_L2_BB,
    )

    cleanup_previous_site_reports(output_dir, report_prefix, filepath)

    logger.info("Excel 已导出: %s", filepath)

    if GSheetSync:
        sheet_id = getattr(config, "gsheet_spreadsheet_id", "") or os.getenv("GSHEET_SPREADSHEET_ID", "")
        cred_json = getattr(config, "gsheet_credentials_json", "") or os.getenv("GSHEET_CREDENTIALS_JSON", "credentials.json")

        if sheet_id and cred_json and os.path.exists(cred_json):
            try:
                gsync = GSheetSync(sheet_id, cred_json)
                gsync.sync_competitor_report(sheet_name, report_sheets)
            except Exception as exc:
                logger.error("同步 Google Sheets 失败: %s", exc, exc_info=True)
        else:
            logger.info("未配置 Google Sheets，跳过同步")

    logger.info(
        "✅ Babyboo Fashion 处理完成：商品数=%s，颜色行数=%s，下架=%s",
        len(products),
        len(records),
        delisted_count,
    )


def run_bb() -> None:
    main()


if __name__ == "__main__":
    main()
