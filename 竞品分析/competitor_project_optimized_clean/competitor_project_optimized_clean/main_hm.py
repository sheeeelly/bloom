"""Hello Molly 自动监控引擎 - 页面白名单排序 + Next Data 批量补详情版

目标页面：
https://www.hellomolly.com/collections/wedding-edit/bridesmaid

当前最终口径：
1. Nosto 前台分页只负责确认该页面真实商品池和页面排序。
2. 不再通过 siblings / HTML fallback / extra handles 扩充商品池。
3. Next Data 只负责补页面白名单商品的详情、价格、variants、尺码和库存。
4. 最终输出严格按页面白名单顺序，不允许接口新增页面外商品。
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any

import requests

from utils.baseline_manager import BaselineManager
from utils.report_history import cleanup_previous_site_reports, is_first_site_crawl, resolve_current_datetime
from utils.config import Config
from utils.data_exporter import DataExporter
from utils.product_details import collect_product_detail_text, collect_hellomolly_product_detail_text
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

try:
    from utils.attribute_extractor import extract_attributes as common_extract_attributes
except ImportError:
    common_extract_attributes = None  # type: ignore

try:
    from utils.gsheet_sync import GSheetSync
except ImportError:
    GSheetSync = None  # type: ignore


logger = logging.getLogger(__name__)

HM_SOURCE_PAGE_URL = "https://www.hellomolly.com/collections/wedding-edit/bridesmaid"


# =========================
# Hello Molly 配置
# =========================

HM_BASE_URL = "https://www.hellomolly.com"
HM_COLLECTION_PATH = "collections/wedding-edit/bridesmaid"
NOSTO_GRAPHQL_URL = "https://search.nosto.com/v1/graphql"

DEFAULT_NOSTO_ACCOUNT_ID = "shopify-28120711254"
DEFAULT_NOSTO_CATEGORY_PATH = "Bridesmaid"

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
    "Referer": "https://www.hellomolly.com/collections/wedding-edit/bridesmaid",
}


# =========================
# Excel 表结构
# =========================

HEADER_L1_CONFIG_HM = [("原始排序表", 20)]

COLUMNS_L2_HM = [
    "排序", "排名涨跌",
    "网站名", "品牌", "类目",
    "商品唯一键 / SKC Key", "款式 ID / SPU Key", "款式名",
    "商品链接", "商品名称", "颜色名称", "尺码", "主图",
    "标价", "售价", "折扣类型", "定制/现货",
    "商品详情描述", "爬取时间", "数据周次",
]


@dataclass
class HMProductRecord:
    site_name: str = "Hello Molly"
    brand: str = "Hello Molly"
    category: str = "Bridesmaid Dresses"

    source_page_url: str = ""
    current_rank: int | str = ""
    previous_rank: int | str = ""
    rank_change: int | str = ""
    rank_trend: str = ""
    product_skc_key: str = ""
    style_spu_key: str = ""
    data_week: str = ""
    new_type: str = ""

    style_label: str = ""
    product_url: str = ""
    product_name: str = ""
    color_name: str = ""
    main_image_url: str = ""
    size: str = ""

    original_price: str = ""
    sale_price: str = ""
    discount_type: str = "无折扣"

    stock_type: str = "现货"
    detail_text: str = ""

    fabric_name: str = ""
    aesthetic_tag: str = ""
    length: str = ""
    neckline: str = ""

    scrape_time: str = ""
    release_date: str = ""
    is_new_color: str = "否"
    relisted_after_delisted: str = "否"
    last_delisted_at: str = ""
    is_official_new: str = "否"
    status: str = "Active"

    def to_row(self) -> list:
        return [
            self.current_rank, self.rank_change,
            self.site_name, self.brand, self.category,
            self.product_skc_key, self.style_spu_key, self.style_label,
            self.product_url, self.product_name, self.color_name, self.size, self.main_image_url,
            self.original_price, self.sale_price, self.discount_type, self.stock_type,
            self.detail_text, self.scrape_time, self.data_week,
        ]

    def to_metadata(self) -> dict:
        return {
            "site_name": self.site_name,
            "brand": self.brand,
            "category": self.category,
            "source_page_url": self.source_page_url,
            "current_rank": self.current_rank,
            "previous_rank": self.previous_rank,
            "rank_change": self.rank_change,
            "rank_trend": self.rank_trend,
            "product_skc_key": self.product_skc_key,
            "style_spu_key": self.style_spu_key,
            "data_week": self.data_week,
            "new_type": self.new_type,
            "style_label": self.style_label,
            "product_url": self.product_url,
            "product_name": self.product_name,
            "color_name": self.color_name,
            "size": self.size,
            "main_image_url": self.main_image_url,
            "original_price": self.original_price,
            "sale_price": self.sale_price,
            "discount_type": self.discount_type,
            "stock_type": self.stock_type,
            "detail_text": self.detail_text,
            "fabric_name": self.fabric_name,
            "aesthetic_tag": self.aesthetic_tag,
            "length": self.length,
            "neckline": self.neckline,
            "scrape_time": self.scrape_time,
            "release_date": self.release_date,
            "is_new_color": self.is_new_color,
            "relisted_after_delisted": self.relisted_after_delisted,
            "last_delisted_at": self.last_delisted_at,
            "is_official_new": self.is_official_new,
            "status": self.status,
        }


# =========================
# 关键词
# =========================

FABRIC_KEYWORDS = [
    "Luxurious Satin", "Silky Satin", "Hammered Satin", "Bias Cut Satin",
    "Matte Satin", "Stretch Satin", "Satin", "Chiffon", "Crepe", "Mesh",
    "Lace", "Velvet", "Tulle", "Sequin", "Sequinned", "Jersey",
    "Organza", "Luxe", "Slinky", "Scuba", "Georgette", "Knit",
    "Ribbed", "Sheer", "Viscose", "Rayon", "Polyester", "Spandex",
]

STYLE_KEYWORDS = [
    "Straight Flowy Silhouette", "Straight Silhouette", "Flowy Silhouette", "Bias Cut",
    "Bodycon", "Fishtail", "Mermaid", "A-Line", "Column", "Slip",
    "Wrap", "Ruched", "Ruching", "Draped", "Drape", "Corset",
    "Backless", "Elastic Back", "Cape", "With Scarf", "Scarf", "Jumpsuit", "Multiway",
    "Asymmetric", "Asymmetrical", "Pleated", "Twist", "Tie", "Cut Out",
    "Cut-Out", "Embellished", "Feather", "Ruffle", "Ruffled", "Bow",
    "Split", "Thigh Split", "Side Split", "Front Split", "Gathered", "Flowy", "Strapless", "Halter",
    "Cowl", "Off Shoulder", "One Shoulder",
]

LENGTH_KEYWORDS = ["Maxi", "Midi", "Mini", "Long", "Short"]

NECKLINE_KEYWORDS = [
    "Bandeau", "One Shoulder", "One-Shoulder", "Asymmetric",
    "Asymmetrical", "Asymmetric-Neck", "Off Shoulder", "Off The Shoulder",
    "Off-the-Shoulder", "Bardot", "Plunge", "Cowl", "Halter",
    "High Neck", "V Neck", "V-Neck", "V Neckline", "V-Neckline", "Soft V Neckline", "Soft V-Neckline",
    "Square Neck", "Sweetheart", "Strapless", "Scoop Neck", "Crew Neck", "Cami", "Bustier",
    "Elastic Back", "Sleeveless",
]

COLOR_KEYWORDS = [
    "Chocolate Brown", "Sage Green", "Olive Green", "Dusty Pink",
    "Candy Pink", "Light Blue", "Light Pink", "Powder Blue", "Baby Blue",
    "Dusty Blue", "Sky Blue", "Ice Blue", "Steel Blue", "Slate Blue",
    "Butter Yellow", "Blue", "Black", "White", "Ivory", "Cream", "Pearl",
    "Champagne", "Oyster", "Stone", "Taupe", "Mocha", "Chocolate",
    "Brown", "Dark Brown", "Nude", "Beige", "Mushroom", "Blush",
    "Blush Pink", "Pink", "Rose", "Dusty Rose", "Baby Pink", "Hot Pink",
    "Fuchsia", "Red", "Burgundy", "Wine", "Deep Wine", "Berry",
    "Orange", "Coral", "Yellow", "Lemon", "Butter", "Green", "Sage",
    "Olive", "Khaki", "Emerald", "Mint", "Pistachio", "Navy", "Teal",
    "Aqua", "Purple", "Lilac", "Lavender", "Orchid", "Plum", "Silver",
    "Gold", "Grey", "Gray", "Multi", "Floral", "Bronze",
]

SIZE_VALUES = {
    "default title", "default", "one size", "os",
    "xxs", "xs", "s", "m", "l", "xl", "xxl", "2xl", "3xl", "4xl",
    "us 0", "us 2", "us 4", "us 6", "us 8", "us 10", "us 12",
    "us 14", "us 16", "us 18",
    "au 4", "au 6", "au 8", "au 10", "au 12", "au 14", "au 16", "au 18",
    "uk 4", "uk 6", "uk 8", "uk 10", "uk 12", "uk 14", "uk 16", "uk 18",
    "0", "2", "4", "6", "8", "10", "12", "14", "16", "18", "20", "22",
    "24", "26",
}


# =========================
# 基础工具函数
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
        if "." not in clean_text and price >= 1000:
            price = price / 100
        return price
    except ValueError:
        return 0.0


def _format_price(value: float) -> str:
    if not value:
        return ""
    return f"${value:.2f}"


def _json_loads_safe(value: Any, default: Any = None) -> Any:
    if default is None:
        default = []

    if value is None:
        return default

    if isinstance(value, (list, dict)):
        return value

    text = str(value).strip()
    if not text:
        return default

    try:
        return json.loads(text)
    except Exception:
        return default


def _list_first(value: Any) -> str:
    if isinstance(value, list):
        return _safe_str(value[0]) if value else ""
    return _safe_str(value)


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
    tags = product.get("tags", []) or product.get("tags1", []) or []

    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]

    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]

    return []


def _extract_brand(product: dict[str, Any]) -> str:
    nosto_fields = product.get("_nosto_custom_fields", {})
    if not isinstance(nosto_fields, dict):
        nosto_fields = {}

    brand = (
        _safe_str(product.get("vendor"))
        or _safe_str(product.get("brand"))
        or _safe_str(product.get("product_brand"))
        or _safe_str(nosto_fields.get("attributes-brand"))
        or "Hello Molly"
    )

    if brand.lower() in {"hello-molly", "hellomolly"}:
        return "Hello Molly"
    return brand




def _tags_to_text(tags: list[str]) -> str:
    return " ".join(t.replace("_", " ").replace("-", " ") for t in tags)


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

    if lower_handle.endswith(".js") or lower_handle.endswith(".json"):
        return ""

    if "." in handle:
        return ""

    return handle


def _build_product_url(base_url: str, handle: str) -> str:
    handle = _safe_str(handle)
    if not handle:
        return ""
    return f"{base_url}/products/{handle}"


def _is_non_dress_product(product: dict[str, Any]) -> bool:
    title = _safe_str(product.get("title") or product.get("name")).lower()
    handle = _safe_str(product.get("handle")).lower()
    product_type = _safe_str(product.get("product_type") or product.get("productType")).lower()
    tags = " ".join(_get_tags(product)).lower()

    text = f"{title} {handle} {product_type} {tags}"

    if "swatch" in text or "swatch card" in text:
        return True

    if "neck scarf" in text:
        return True

    if "scarf" in text and not any(word in text for word in ["dress", "gown", "jumpsuit"]):
        return True

    exclude_keywords = [
        "gift card", "sample", "shoe", "heels", "bag", "clutch",
        "earring", "necklace", "bracelet", "accessory", "accessories",
        "lingerie", "shapewear", "bikini", "swimsuit",
    ]

    return any(keyword in text for keyword in exclude_keywords)


def _strip_color_from_title(title: str) -> tuple[str, str]:
    title = _clean_text(title)

    if not title:
        return "", "Default"

    match = re.match(r"^(.*?)\s+-\s+(.*?)$", title)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    for color in sorted(COLOR_KEYWORDS, key=len, reverse=True):
        pattern = rf"^(.*?)\s+in\s+{re.escape(color)}$"
        match = re.match(pattern, title, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(), color

    for color in sorted(COLOR_KEYWORDS, key=len, reverse=True):
        if title.lower().endswith(" " + color.lower()):
            base_title = title[: -len(color)].strip()
            return base_title, color

    return title, "Default"


def _split_style_color_name(title: str, handle: str) -> tuple[str, str, str]:
    title = _clean_text(title)
    handle = _safe_str(handle)

    if not title:
        return "", "", "Default"

    base_title, color_name = _strip_color_from_title(title)

    if color_name == "Default":
        handle_slug = handle.lower()
        for color in sorted(COLOR_KEYWORDS, key=len, reverse=True):
            color_slug = _slugify(color)
            if handle_slug.endswith(f"-{color_slug}"):
                color_name = color
                break

    style_label = ""
    product_name = base_title

    words = base_title.split()

    if len(words) >= 3 and words[0].lower() == "the":
        style_label = f"{words[0]} {words[1]}"
        product_name = " ".join(words[2:]).strip()
    elif len(words) >= 2:
        handle_first = handle.split("-", 1)[0].lower() if handle else ""
        if handle_first and words[0].lower() == handle_first:
            style_label = words[0]
            product_name = " ".join(words[1:]).strip()

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

        if re.fullmatch(r"(au|us|uk)?\s*\d+", lower_value):
            continue

        return value

    return ""



def _extract_variant_size(variant: dict[str, Any]) -> str:
    candidates: list[str] = []

    selected_options = variant.get("selectedOptions") or variant.get("selected_options") or []
    if isinstance(selected_options, list):
        for option in selected_options:
            if not isinstance(option, dict):
                continue
            name = _safe_str(option.get("name")).lower()
            value = _clean_text(option.get("value"))
            if value and any(token in name for token in ["size", "尺寸"]):
                candidates.append(value)

    for key in ["size", "option1", "option2", "option3", "title", "name"]:
        value = _clean_text(variant.get(key))
        if not value:
            continue
        for part in re.split(r"\s*/\s*|\s+-\s+|\s*,\s*", value):
            part = _clean_text(part)
            if part:
                candidates.append(part)

    for value in candidates:
        lower = value.lower().strip()
        if not lower or lower in {"default", "default title", "one size", "os"}:
            if lower in {"one size", "os"}:
                return "One Size"
            continue
        if lower in SIZE_VALUES or re.fullmatch(r"(au|us|uk)?\s*\d+", lower):
            return value.upper() if lower in {"xs", "s", "m", "l", "xl", "xxl"} else value
    return ""


def _format_sizes_for_variants(color_variants: list[dict[str, Any]], has_variant_data: bool) -> str:
    if not has_variant_data:
        return "未获取"

    available_sizes: list[str] = []
    all_sizes: list[str] = []

    for variant in color_variants or []:
        if not isinstance(variant, dict):
            continue
        size = _extract_variant_size(variant)
        if size and size not in all_sizes:
            all_sizes.append(size)
        if bool(variant.get("available", False)) and size and size not in available_sizes:
            available_sizes.append(size)

    if available_sizes:
        return " / ".join(available_sizes)
    if all_sizes:
        return "无码"
    return "未获取"


def _stock_type_for_variants(color_variants: list[dict[str, Any]], has_variant_data: bool) -> str:
    if not has_variant_data:
        return "未知"
    return "现货" if any(bool(variant.get("available", False)) for variant in color_variants or []) else "缺货"


def _normalize_hm_attr_value(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""

    normalized = text.strip().lower().replace("_", " ").replace("-", " ")
    normalized = re.sub(r"\s+", " ", normalized)

    mapping = {
        "luxurious satin": "Satin",
        "silky satin": "Satin",
        "satin": "Satin",
        "matte satin": "Matte Satin",
        "stretch satin": "Stretch Satin",
        "chiffon": "Chiffon",
        "mesh": "Mesh",
        "lace": "Lace",
        "velvet": "Velvet",
        "tulle": "Tulle",
        "sequin": "Sequin",
        "sequinned": "Sequin",
        "jersey": "Jersey",
        "crepe": "Crepe",
        "knit": "Knit",
        "maxi": "Maxi",
        "midi": "Midi",
        "mini": "Mini",
        "long": "Long",
        "short": "Short",
        "v neckline": "V Neck",
        "v neck": "V Neck",
        "v neck line": "V Neck",
        "v-neckline": "V Neck",
        "v-neck": "V Neck",
        "soft v neckline": "V Neck",
        "soft v neck": "V Neck",
        "elastic back": "Elastic Back",
        "straight flowy silhouette": "Straight / Flowy Silhouette",
        "flowy silhouette": "Flowy Silhouette",
        "straight silhouette": "Straight Silhouette",
        "flowy": "Flowy",
        "slip": "Slip",
    }
    return mapping.get(normalized, text.replace("-", " ").title())


def _hm_join_parts(parts: list[str], limit: int = 4) -> str:
    result: list[str] = []
    seen: set[str] = set()
    for part in parts:
        value = _normalize_hm_attr_value(part)
        if not value:
            continue
        key = value.lower().replace("-", " ")
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= limit:
            break
    return " / ".join(result)


def _extract_hm_detail_attrs(text: str) -> dict[str, str]:
    """从 Hello Molly PDP Details / description 文案中提取属性，优先级高于 Nosto 粗标签。"""
    clean = _clean_text(text)
    normalized = clean.lower()
    normalized = normalized.replace("–", "-").replace("—", "-").replace("&", " and ")
    normalized = re.sub(r"[\-_/]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    fabric = ""
    fabric_patterns = [
        ("Satin", ["luxurious satin", "silky satin", "satin maxi", "satin dress", "crafted in a silky satin", " satin.", " satin "]),
        ("Chiffon", ["chiffon"]),
        ("Mesh", ["mesh"]),
        ("Lace", ["lace"]),
        ("Velvet", ["velvet"]),
        ("Tulle", ["tulle"]),
        ("Sequin", ["sequin", "sequinned"]),
        ("Jersey", ["jersey"]),
        ("Crepe", ["crepe"]),
        ("Knit", ["knit"]),
        ("Viscose / Rayon", ["viscose", "rayon"]),
    ]
    for label, patterns in fabric_patterns:
        if any(pattern in normalized for pattern in patterns):
            fabric = label
            break

    length = ""
    if "maxi dress" in normalized or "maxi length" in normalized or "maxi gown" in normalized:
        length = "Maxi"
    elif "midi dress" in normalized or "midi length" in normalized:
        length = "Midi"
    elif "mini dress" in normalized or "mini length" in normalized:
        length = "Mini"
    elif "length from shoulder to hem" in normalized and re.search(r"1[34]\d\s*cm", normalized):
        length = "Maxi"

    neckline_parts: list[str] = []
    neckline_patterns = [
        ("V Neck", ["soft v neckline", "v neckline", "v neck", "v-neckline", "v-neck"]),
        ("Elastic Back", ["elastic back"]),
        ("Strapless", ["strapless"]),
        ("Halter", ["halter neck", "halterneck", "halter"]),
        ("Cowl Neck", ["cowl neckline", "cowl neck", "cowl"]),
        ("Square Neck", ["square neckline", "square neck"]),
        ("Sweetheart", ["sweetheart neckline", "sweetheart"]),
        ("One Shoulder", ["one shoulder", "one-shoulder"]),
        ("Off Shoulder", ["off shoulder", "off the shoulder", "off-the-shoulder"]),
        ("Scoop Neck", ["scoop neckline", "scoop neck"]),
        ("High Neck", ["high neckline", "high neck"]),
        ("Plunge Neck", ["plunge neckline", "plunging neckline", "deep plunge"]),
        ("Cupped Bust", ["cupped bust", "bust cups", "cupped cups"]),
        ("Sleeveless", ["sleeveless"]),
    ]
    for label, patterns in neckline_patterns:
        if any(pattern in normalized for pattern in patterns):
            neckline_parts.append(label)

    style_parts: list[str] = []
    style_patterns = [
        ("Straight", ["straight, flowy silhouette", "straight silhouette"]),
        ("Flowy Silhouette", ["straight, flowy silhouette", "flowy silhouette", "flowy"]),
        ("Bias Cut", ["bias cut"]),
        ("Slip", ["slip dress", "slip silhouette"]),
        ("Ruched", ["ruched", "ruching"]),
        ("Draped", ["draped", "drape"]),
        ("Gathered", ["gathered"]),
        ("A-Line", ["a line", "a-line"]),
        ("Column", ["column silhouette", "column dress"]),
        ("Bodycon", ["bodycon"]),
        ("Ruffle", ["ruffle", "ruffled"]),
        ("Frilled", ["frilled"]),
        ("High-Low Hem", ["high low", "high-low"]),
        ("Thigh High Split", ["thigh high split", "thigh-high split"]),
        ("Side Split", ["side split", "side-split"]),
        ("Front Split", ["front split", "front slit"]),
        ("Cut-Out", ["cut out", "cut-out"]),
        ("Backless", ["backless", "open back", "low v shaped back", "low v-shaped back"]),
        ("Elastic Back", ["elastic back"]),
        ("Second Skin Fit", ["second skin fit"]),
        ("Floral Applique", ["flower applique", "flower appliques", "floral applique"]),
    ]
    for label, patterns in style_patterns:
        if any(pattern in normalized for pattern in patterns):
            style_parts.append(label)

    return {
        "fabric_name": fabric,
        "aesthetic_tag": _hm_join_parts(style_parts),
        "length": length,
        "neckline": _hm_join_parts(neckline_parts),
    }


def _hm_attr_score(attrs: dict[str, str]) -> int:
    score = 0
    for key in ["fabric_name", "aesthetic_tag", "length", "neckline"]:
        value = _safe_str(attrs.get(key))
        if not value:
            continue
        score += 1
        if "/" in value:
            score += 1
    return score


def _hm_merge_attrs(primary: dict[str, str], fallback: dict[str, str]) -> dict[str, str]:
    merged = dict(primary)
    low_quality_style = {"slip", "flowy"}
    low_quality_neckline = {"sleeveless"}
    for key, value in fallback.items():
        value = _safe_str(value)
        if not value:
            continue
        current = _safe_str(merged.get(key))
        if not current:
            merged[key] = value
            continue
        if key == "aesthetic_tag" and current.lower() in low_quality_style and value.lower() != current.lower():
            merged[key] = value
        elif key == "neckline" and current.lower() in low_quality_neckline and value.lower() != current.lower():
            merged[key] = value
    return merged


def _hm_style_group_key(style_label: str, product_name: str, product: dict[str, Any]) -> str:
    base = " ".join([_safe_str(style_label), _safe_str(product_name)]) or _safe_str(product.get("title")) or _safe_str(product.get("handle"))
    base = re.sub(r"(black|white|ivory|cream|champagne|sage|green|blue|light blue|pink|blush|chocolate|brown|burgundy|red|lemon|yellow|lilac|lavender|purple|navy|floral|multi)", " ", base, flags=re.I)
    return _slugify(base)


def _extract_attrs(product_name: str, tags: list[str], product: dict[str, Any] | None = None) -> dict[str, str]:
    product = product or {}

    nosto_fields = product.get("_nosto_custom_fields", {})
    if not isinstance(nosto_fields, dict):
        nosto_fields = {}

    fabric_from_nosto = _normalize_hm_attr_value(_list_first(_json_loads_safe(nosto_fields.get("attributes-fabric"), [])))
    style_from_nosto = _normalize_hm_attr_value(_list_first(_json_loads_safe(nosto_fields.get("attributes-style"), [])))
    length_from_nosto = _normalize_hm_attr_value(_list_first(_json_loads_safe(nosto_fields.get("attributes-length"), [])))
    neckline_from_nosto = _normalize_hm_attr_value(_list_first(_json_loads_safe(nosto_fields.get("attributes-sleeves"), [])))

    tag_text = _tags_to_text(tags)

    extra_text = " ".join(
        [
            _safe_str(product.get("title")),
            _safe_str(product.get("handle")),
            _safe_str(product.get("product_type")),
            _safe_str(product.get("productType")),
            _clean_text(product.get("body_html")),
            _clean_text(product.get("description")),
            _clean_text(product.get("descriptionHtml")),
            _safe_str(product.get("vendor")),
            tag_text,
            " ".join(str(v) for v in nosto_fields.values()),
        ]
    )

    text = f"{product_name} {extra_text}"

    detail_attrs = _extract_hm_detail_attrs(text)

    common_attrs = {}
    if common_extract_attributes:
        try:
            common_attrs = common_extract_attributes(
                {
                    **product,
                    "product_name": product_name,
                    "tags": tags,
                    "_nosto_custom_fields": nosto_fields,
                },
                default_floor_length=False,
            ) or {}
        except Exception as exc:
            logger.debug("Hello Molly 公共属性解析兜底失败: %s", exc)

    keyword_attrs = {
        "fabric_name": _normalize_hm_attr_value(_find_keyword(text, FABRIC_KEYWORDS)),
        "aesthetic_tag": _normalize_hm_attr_value(_find_keyword(text, STYLE_KEYWORDS)),
        "length": _normalize_hm_attr_value(_find_keyword(text, LENGTH_KEYWORDS)),
        "neckline": _normalize_hm_attr_value(_find_keyword(text, NECKLINE_KEYWORDS)),
    }

    nosto_attrs = {
        "fabric_name": fabric_from_nosto,
        "aesthetic_tag": style_from_nosto,
        "length": length_from_nosto,
        "neckline": neckline_from_nosto,
    }

    attrs = dict(detail_attrs)
    attrs = _hm_merge_attrs(attrs, common_attrs)
    attrs = _hm_merge_attrs(attrs, nosto_attrs)
    attrs = _hm_merge_attrs(attrs, keyword_attrs)

    return attrs


def _is_official_new(product: dict[str, Any]) -> str:
    """
    判断 Hello Molly 商品是否为官网 New。

    优先从：
    1. Nosto tags1
    2. Next Data tags
    3. Nosto customFields
    4. 商品标题
    中识别 New / New In / category_new 等标识。
    """
    tags = _get_tags(product)
    tags_text = " ".join(tags).lower()

    title = _safe_str(product.get("title") or product.get("name")).lower()
    handle = _safe_str(product.get("handle")).lower()

    nosto_fields = product.get("_nosto_custom_fields", {})
    if isinstance(nosto_fields, dict):
        nosto_text = " ".join(str(v) for v in nosto_fields.values()).lower()
    else:
        nosto_text = ""

    combined_text = f"{title} {handle} {tags_text} {nosto_text}"

    new_keywords = [
        "category_new",
        "new in",
        "new-in",
        "new arrival",
        "new arrivals",
        "just added",
    ]

    for keyword in new_keywords:
        if keyword in combined_text:
            return "是"

    return "否"
# =========================
# HTTP
# =========================

def _make_session(config: Config) -> requests.Session:
    session = requests.Session()

    proxy_url = getattr(config, "proxy_url", None)
    if proxy_url:
        session.proxies = {"http": proxy_url, "https": proxy_url}
        logger.info("已配置 HTTP 代理: %s", proxy_url)

    return session


def _fetch_text(
    session: requests.Session,
    url: str,
    *,
    headers: dict[str, str],
    timeout: int,
    retries: int = 2,
    raise_retryable: bool = False,
) -> str:
    for attempt in range(retries + 1):
        try:
            response = session.get(url, headers=headers, timeout=timeout)

            if response.status_code == 200:
                return response.text

            logger.warning("请求失败: status=%s url=%s", response.status_code, response.url)

            if response.status_code in {403, 404, 410}:
                return ""

            if raise_retryable:
                classify_http_status(response.status_code, response.url)

        except requests.RequestException as exc:
            if raise_retryable and is_retryable_exception(exc):
                raise RetryableTaskError(f"Hello Molly HTML retryable error url={url}: {exc}") from exc

            logger.warning("请求异常: %s | url=%s", exc, url)

        if attempt < retries:
            time.sleep(0.4 * (attempt + 1))

    return ""


def _fetch_json_get(
    session: requests.Session,
    url: str,
    *,
    headers: dict[str, str],
    timeout: int,
    params: dict[str, Any] | None = None,
    retries: int = 2,
    raise_retryable: bool = False,
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

            logger.warning("JSON GET 失败: status=%s url=%s", response.status_code, response.url)

            if response.status_code in {403, 404, 410}:
                return None

            if raise_retryable:
                classify_http_status(response.status_code, response.url)

        except requests.RequestException as exc:
            if raise_retryable and is_retryable_exception(exc):
                raise RetryableTaskError(f"Hello Molly JSON GET retryable error url={url}: {exc}") from exc
            logger.warning("JSON GET 异常: %s | url=%s", exc, url)

        if attempt < retries:
            time.sleep(0.4 * (attempt + 1))

    return None


def _fetch_json_post(
    session: requests.Session,
    url: str,
    *,
    headers: dict[str, str],
    timeout: int,
    payload: dict[str, Any],
    retries: int = 2,
) -> dict[str, Any] | None:
    for attempt in range(retries + 1):
        try:
            response = session.post(url, headers=headers, timeout=timeout, json=payload)

            if response.status_code == 200:
                try:
                    data = response.json()
                    return data if isinstance(data, dict) else None
                except ValueError:
                    logger.warning("JSON POST 解析失败: %s", response.url)
                    return None

            logger.warning("JSON POST 失败: status=%s text=%s", response.status_code, response.text[:300])

            if response.status_code in {403, 404}:
                return None

        except requests.RequestException as exc:
            logger.warning("JSON POST 异常: %s | url=%s", exc, url)

        if attempt < retries:
            time.sleep(0.4 * (attempt + 1))

    return None


# =========================
# HTML / Next buildId
# =========================

class HelloMollyHTMLParser(HTMLParser):
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


def _extract_next_data_json_from_html(html: str) -> dict[str, Any] | None:
    match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return None

    raw_json = unescape(match.group(1)).strip()

    if not raw_json:
        return None

    try:
        data = json.loads(raw_json)
        return data if isinstance(data, dict) else None
    except ValueError:
        return None


def _extract_build_id_from_html(html: str) -> str:
    next_data = _extract_next_data_json_from_html(html)
    if isinstance(next_data, dict):
        build_id = _safe_str(next_data.get("buildId"))
        if build_id:
            return build_id

    for pattern in [r"/_next/data/([^/]+)/", r"/_next/static/([^/]+)/"]:
        match = re.search(pattern, html)
        if match:
            return match.group(1).strip()

    return ""


def _discover_build_id(session: requests.Session, base_url: str, collection_path: str, timeout: int) -> str:
    env_build_id = os.getenv("HM_NEXT_BUILD_ID", "").strip()
    if env_build_id:
        logger.info("使用 .env 中 HM_NEXT_BUILD_ID=%s", env_build_id)
        return env_build_id

    url = f"{base_url}/{collection_path.strip('/')}"
    html = ""
    retry_queue = RetryQueue(site_key="hellomolly")

    def queue_build_id_retry(first_error: str) -> None:
        def handler() -> str:
            local_session = requests.Session()
            return _fetch_text(
                local_session,
                url,
                headers=HEADERS_HTML,
                timeout=timeout,
                raise_retryable=True,
            )

        def on_success(text: str) -> None:
            nonlocal html
            html = text or ""

        retry_queue.submit(
            task_type="hm_build_id_html",
            identity_key=url,
            payload={"url": url, "first_error": first_error},
            handler=handler,
            on_success=on_success,
            accept_result=lambda text: isinstance(text, str) and bool(text.strip()),
        )

    try:
        html = _fetch_text(
            session,
            url,
            headers=HEADERS_HTML,
            timeout=timeout,
            raise_retryable=True,
        )
    except Exception as exc:
        if is_retryable_exception(exc):
            logger.warning("Hello Molly build_id 页面请求异常，已进入 retry queue: %s", exc)
            queue_build_id_retry(str(exc))
        else:
            logger.warning("Hello Molly build_id 页面请求非重试异常: %s", exc)

    if not html:
        retry_queue.drain()

    build_id = _extract_build_id_from_html(html)

    if build_id:
        logger.info("发现 Hello Molly Next build_id=%s", build_id)
    else:
        logger.warning("未发现 Hello Molly Next build_id，Next Data 详情可能失败")

    return build_id




# =========================
# Nosto GraphQL
# =========================

NOSTO_REAL_COLLECTION_QUERY = """
query (
  $abTests: [InputSearchABTest!],
  $accountId: String,
  $query: String,
  $segments: [String!],
  $rules: [String!],
  $products: InputSearchProducts,
  $categories: InputSearchCategories,
  $popularSearches: InputSearchPopularSearches,
  $keywords: InputSearchKeywords,
  $sessionParams: InputSearchQuery
) {
  search(
    accountId: $accountId
    query: $query
    segments: $segments
    rules: $rules
    products: $products
    categories: $categories
    popularSearches: $popularSearches
    keywords: $keywords
    sessionParams: $sessionParams
    abTests: $abTests
  ) {
    query
    redirect
    products {
      hits {
        productId
        name
        url
        imageUrl
        price
        listPrice
        priceCurrencyCode
        customFields {
          key
          value
        }
        tags1
        alternateImageUrls
        skus {
          id
          name
          price
          listPrice
          inventoryLevel
          customFields {
            key
            value
          }
        }
        inventoryLevel
      }
      total
      size
      from
      facets {
        ... on SearchTermsFacet {
          id
          field
          type
          name
          data {
            value
            count
            selected
            visual {
              type
              value
            }
          }
        }
        ... on SearchStatsFacet {
          id
          field
          type
          name
          min
          max
        }
      }
      collapse
      fuzzy
      categoryId
      categoryPath
      searchType
    }
    abTests {
      id
      activeVariation {
        id
      }
    }
  }
}
"""


def _custom_fields_to_dict(custom_fields: Any) -> dict[str, str]:
    result: dict[str, str] = {}

    if not isinstance(custom_fields, list):
        return result

    for item in custom_fields:
        if not isinstance(item, dict):
            continue

        key = _safe_str(item.get("key"))
        value = _safe_str(item.get("value"))

        if key:
            result[key] = value

    return result


def _extract_sibling_handles_from_nosto_fields(fields: dict[str, str]) -> list[str]:
    siblings = _json_loads_safe(fields.get("categorisation-siblings"), [])

    handles: list[str] = []
    seen: set[str] = set()

    if isinstance(siblings, list):
        for item in siblings:
            if not isinstance(item, dict):
                continue

            handle = _safe_str(item.get("handle"))

            if handle and handle not in seen:
                seen.add(handle)
                handles.append(handle)

    return handles


def _normalize_nosto_hit(hit: dict[str, Any], base_url: str) -> dict[str, Any] | None:
    name = _safe_str(hit.get("name"))
    url = _safe_str(hit.get("url"))
    handle = _extract_handle_from_product_url(url)

    if not handle and url:
        handle = url.rstrip("/").split("/")[-1].split("?")[0].split("#")[0]

    if not handle or not name:
        return None

    fields = _custom_fields_to_dict(hit.get("customFields"))

    color = _list_first(_json_loads_safe(fields.get("attributes-color"), []))
    brand = _safe_str(fields.get("attributes-brand")) or "Hello Molly"
    product_type = _safe_str(fields.get("producttype")) or "Clothes"

    tags = hit.get("tags1") if isinstance(hit.get("tags1"), list) else []

    for key in [
        "attributes-fabric",
        "attributes-style",
        "attributes-length",
        "attributes-color",
        "attributes-sleeves",
        "attributes-trend",
        "attributes-occasion",
        "attributes-brand",
    ]:
        parsed_value = _json_loads_safe(fields.get(key), [])
        if isinstance(parsed_value, list):
            tags.extend([f"{key}_{v}" for v in parsed_value if v])
        elif parsed_value:
            tags.append(f"{key}_{parsed_value}")

    price = _parse_price(hit.get("price"))
    list_price = _parse_price(hit.get("listPrice")) or price
    image_url = _normalize_image_url(hit.get("imageUrl"))

    skus = hit.get("skus") if isinstance(hit.get("skus"), list) else []
    variants: list[dict[str, Any]] = []

    for sku in skus:
        if not isinstance(sku, dict):
            continue

        sku_custom = _custom_fields_to_dict(sku.get("customFields"))
        size_value = _safe_str(sku_custom.get("size") or sku.get("name"))
        inventory = int(_parse_price(sku.get("inventoryLevel")))

        variants.append(
            {
                "id": sku.get("id") or "",
                "title": size_value or "Default Title",
                "price": _parse_price(sku.get("price")) or price,
                "compare_at_price": _parse_price(sku.get("listPrice")),
                "available": inventory > 0,
                "inventoryLevel": inventory,
                "featured_image": {"src": image_url} if image_url else None,
                "selectedOptions": [
                    {"name": "Color", "value": color},
                    {"name": "Size", "value": size_value},
                ],
            }
        )

    if not variants:
        inventory = int(_parse_price(hit.get("inventoryLevel")))
        variants.append(
            {
                "id": hit.get("productId") or "",
                "title": color or "Default Title",
                "price": price,
                "compare_at_price": list_price if list_price > price else "",
                "available": inventory > 0,
                "inventoryLevel": inventory,
                "featured_image": {"src": image_url} if image_url else None,
                "selectedOptions": [{"name": "Color", "value": color}] if color else [],
            }
        )

    product = {
        "id": hit.get("productId") or "",
        "title": name,
        "handle": handle,
        "vendor": brand,
        "product_type": product_type,
        "productType": product_type,
        "tags": tags,
        "body_html": "",
        "description": "",
        "descriptionHtml": "",
        "availableForSale": int(_parse_price(hit.get("inventoryLevel"))) > 0,
        "variants": variants,
        "images": [{"src": image_url}] if image_url else [],
        "image": {"src": image_url} if image_url else None,
        "price": price,
        "compare_at_price": list_price if list_price > price else "",
        "original_price": list_price,
        "sale_price": price,
        "siblings": [],
        "_source_base_url": base_url,
        "_nosto_custom_fields": fields,
        "_nosto_attrs": {
            "color": color,
            "fabric": _list_first(_json_loads_safe(fields.get("attributes-fabric"), [])),
            "style": _list_first(_json_loads_safe(fields.get("attributes-style"), [])),
            "length": _list_first(_json_loads_safe(fields.get("attributes-length"), [])),
            "neckline": _list_first(_json_loads_safe(fields.get("attributes-sleeves"), [])),
        },
    }

    if _is_non_dress_product(product):
        return None

    return product


def _build_nosto_payload(account_id: str, category_path: str, size: int, from_offset: int) -> dict[str, Any]:
    segments_env = os.getenv(
        "HM_NOSTO_SEGMENTS",
        "613aa0000000000000000002,61c26a800000000000000002,5a497a000000000000000002",
    ).strip()

    segments = [s.strip() for s in segments_env.split(",") if s.strip()]

    return {
        "query": NOSTO_REAL_COLLECTION_QUERY,
        "variables": {
            "abTests": [],
            "accountId": account_id,
            "query": None,
            "segments": None,
            "rules": None,
            "products": {
                "categoryPath": category_path,
                "size": size,
                "from": from_offset,
                "facets": ["*"],
            },
            "categories": None,
            "popularSearches": None,
            "keywords": None,
            "sessionParams": {
                "segments": segments,
            },
        },
    }


def _fetch_nosto_category_products(
    session: requests.Session,
    base_url: str,
    account_id: str,
    category_path: str,
    timeout: int,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    page_size = int(os.getenv("HM_NOSTO_PAGE_SIZE", "96"))
    max_pages = int(os.getenv("HM_NOSTO_MAX_PAGES", "30"))

    products_by_handle: dict[str, dict[str, Any]] = {}
    seed_handles: list[str] = []
    seen_seed_handles: set[str] = set()

    for page_index in range(max_pages):
        from_offset = page_index * page_size

        payload = _build_nosto_payload(
            account_id=account_id,
            category_path=category_path,
            size=page_size,
            from_offset=from_offset,
        )

        logger.info(
            "请求 Nosto Bridesmaid 分页: categoryPath=%s size=%s from=%s",
            category_path,
            page_size,
            from_offset,
        )

        data = _fetch_json_post(
            session=session,
            url=NOSTO_GRAPHQL_URL,
            headers=HEADERS_JSON,
            timeout=timeout,
            payload=payload,
            retries=2,
        )

        if not data:
            logger.warning("Nosto categoryPath=%s from=%s 无响应，停止", category_path, from_offset)
            break

        if data.get("errors"):
            logger.warning("Nosto errors: %s", data.get("errors"))

        products_block = (
            data.get("data", {})
            .get("search", {})
            .get("products", {})
        )

        hits = products_block.get("hits", [])
        total = int(products_block.get("total") or 0)

        if not isinstance(hits, list) or not hits:
            logger.info("Nosto categoryPath=%s from=%s hits=0，停止", category_path, from_offset)
            break

        new_count = 0

        for hit in hits:
            if not isinstance(hit, dict):
                continue

            product = _normalize_nosto_hit(hit, base_url)

            if not product:
                continue

            handle = _safe_str(product.get("handle"))

            if not handle:
                continue

            if handle not in products_by_handle:
                products_by_handle[handle] = product

            if handle not in seen_seed_handles:
                seen_seed_handles.add(handle)
                seed_handles.append(handle)
                new_count += 1

            # 当前最终口径：Nosto 页面分页只确认当前 collection 页面真实商品池和排序。
            # 不再读取 categorisation-siblings 扩充同款颜色，避免页面外颜色/商品进入表格。

        logger.info(
            "Nosto Bridesmaid page=%s from=%s hits=%s 新增seed=%s 累计seed=%s total=%s",
            page_index + 1,
            from_offset,
            len(hits),
            new_count,
            len(seed_handles),
            total,
        )

        if from_offset + page_size >= total:
            break

        time.sleep(0.05)

    logger.info(
        "Nosto Bridesmaid 完成：skeleton_products=%s seed_handles=%s",
        len(products_by_handle),
        len(seed_handles),
    )

    return products_by_handle, seed_handles


# =========================
# HTML 兜底
# =========================

def _get_extra_seed_handles() -> list[str]:
    env_value = os.getenv("HM_EXTRA_PRODUCT_HANDLES", "").strip()
    handles: list[str] = []
    seen: set[str] = set()

    if env_value:
        for raw_handle in env_value.split(","):
            handle = raw_handle.strip().strip("/")
            handle = handle.split("/products/")[-1]
            handle = handle.split("?")[0].split("#")[0]

            if handle and handle not in seen:
                seen.add(handle)
                handles.append(handle)

    return handles


def _fetch_html_seed_handles(
    session: requests.Session,
    base_url: str,
    collection_path: str,
    timeout: int,
) -> list[str]:
    max_pages = int(os.getenv("HM_COLLECTION_MAX_PAGES", "5"))
    handles: list[str] = []
    seen: set[str] = set()
    retry_queue = RetryQueue(site_key="hellomolly")

    def apply_html_page(html: str) -> int:
        if not html:
            return 0

        parser = HelloMollyHTMLParser()
        parser.feed(html)

        new_count = 0

        for handle in parser.handles:
            if handle in seen:
                continue
            seen.add(handle)
            handles.append(handle)
            new_count += 1

        for match in re.finditer(r"/products/([a-zA-Z0-9_\-]+)(?:[/?#\"'])", html):
            handle = _extract_handle_from_product_url(f"/products/{match.group(1).strip()}")
            if handle and handle not in seen:
                seen.add(handle)
                handles.append(handle)
                new_count += 1

        return new_count

    def queue_html_page_retry(page: int, url: str, first_error: str) -> None:
        def handler() -> str:
            local_session = requests.Session()
            return _fetch_text(
                local_session,
                url,
                headers=HEADERS_HTML,
                timeout=timeout,
                raise_retryable=True,
            )

        retry_queue.submit(
            task_type="hm_collection_html",
            identity_key=f"page={page}|{url}",
            payload={"page": page, "url": url, "first_error": first_error},
            handler=handler,
            on_success=lambda html: apply_html_page(html),
            accept_result=lambda html: isinstance(html, str) and bool(html.strip()),
        )

    for page in range(1, max_pages + 1):
        url = f"{base_url}/{collection_path.strip('/')}"
        if page > 1:
            url = f"{url}?page={page}"

        logger.info("请求 Hello Molly HTML 兜底列表页: page=%s", page)

        html = ""
        try:
            html = _fetch_text(
                session,
                url,
                headers=HEADERS_HTML,
                timeout=timeout,
                raise_retryable=True,
            )
        except Exception as exc:
            if is_retryable_exception(exc):
                logger.warning(
                    "Hello Molly HTML 兜底列表页异常，已进入 retry queue: page=%s | %s",
                    page,
                    exc,
                )
                queue_html_page_retry(page, url, str(exc))
            else:
                logger.warning("Hello Molly HTML 兜底列表页非重试异常: page=%s | %s", page, exc)

        if not html:
            break

        new_count = apply_html_page(html)

        logger.info(
            "HTML 兜底 page=%s 新增=%s 累计=%s",
            page,
            new_count,
            len(handles),
        )

        if new_count == 0:
            break

        time.sleep(0.08)

    retry_queue.drain()
    return handles


# =========================
# Next Data 商品详情
# =========================

def _get_product_from_next_data(data: dict[str, Any]) -> dict[str, Any] | None:
    page_props = data.get("pageProps")
    if not isinstance(page_props, dict):
        return None

    product = page_props.get("product")
    if isinstance(product, dict):
        return product

    return None


def _nodes(value: Any) -> list[Any]:
    if isinstance(value, dict):
        if isinstance(value.get("nodes"), list):
            return value["nodes"]
        if isinstance(value.get("edges"), list):
            return [edge.get("node") for edge in value["edges"] if isinstance(edge, dict)]
    if isinstance(value, list):
        return value
    return []


def _money_amount(value: Any) -> float:
    if value is None:
        return 0.0

    if isinstance(value, dict):
        return _parse_price(value.get("amount") or value.get("value") or value.get("price"))

    return _parse_price(value)


def _extract_price_info(product: dict[str, Any]) -> tuple[float, float]:
    variants = _nodes(product.get("variants"))

    for variant in variants:
        if not isinstance(variant, dict):
            continue

        price = _money_amount(variant.get("price") or variant.get("priceV2"))
        compare_price = _money_amount(
            variant.get("compareAtPrice")
            or variant.get("compareAtPriceV2")
            or variant.get("compare_at_price")
        )

        if price:
            original_price = compare_price if compare_price and compare_price > price else price
            return original_price, price

    selected_variant = product.get("selectedOrFirstAvailableVariant") or product.get("variant")
    if isinstance(selected_variant, dict):
        price = _money_amount(selected_variant.get("price") or selected_variant.get("priceV2"))
        compare_price = _money_amount(
            selected_variant.get("compareAtPrice")
            or selected_variant.get("compareAtPriceV2")
            or selected_variant.get("compare_at_price")
        )
        if price:
            original_price = compare_price if compare_price and compare_price > price else price
            return original_price, price

    return 0.0, 0.0


def _extract_image_url(product: dict[str, Any]) -> str:
    for image in [product.get("featuredImage"), product.get("featured_image"), product.get("image")]:
        if isinstance(image, dict):
            url = image.get("url") or image.get("src") or image.get("originalSrc") or image.get("transformedSrc")
            if url:
                return _normalize_image_url(url)
        elif isinstance(image, str):
            return _normalize_image_url(image)

    for image in _nodes(product.get("images")):
        if isinstance(image, dict):
            url = image.get("url") or image.get("src") or image.get("originalSrc") or image.get("transformedSrc")
            if url:
                return _normalize_image_url(url)
        elif isinstance(image, str):
            return _normalize_image_url(image)

    return ""


def _extract_variants(product: dict[str, Any], price: float, image_url: str) -> list[dict[str, Any]]:
    variants_raw = _nodes(product.get("variants"))
    variants: list[dict[str, Any]] = []

    for variant in variants_raw:
        if not isinstance(variant, dict):
            continue

        variant_price = _money_amount(variant.get("price") or variant.get("priceV2")) or price
        compare_price = _money_amount(
            variant.get("compareAtPrice")
            or variant.get("compareAtPriceV2")
            or variant.get("compare_at_price")
        )

        available = bool(
            variant.get("availableForSale")
            if "availableForSale" in variant
            else variant.get("available", True)
        )

        variant_image = ""
        image = variant.get("image") or variant.get("featuredImage") or variant.get("featured_image")
        if isinstance(image, dict):
            variant_image = _normalize_image_url(
                image.get("url") or image.get("src") or image.get("originalSrc")
            )

        variants.append(
            {
                "id": variant.get("id") or "",
                "title": variant.get("title") or variant.get("size") or "Default Title",
                "price": variant_price,
                "compare_at_price": compare_price,
                "available": available,
                "featured_image": {"src": variant_image or image_url} if (variant_image or image_url) else None,
                "selectedOptions": variant.get("selectedOptions") or [],
            }
        )

    if variants:
        return variants

    available = bool(product.get("availableForSale", True))
    return [
        {
            "id": product.get("id") or "",
            "title": "Default Title",
            "price": price,
            "compare_at_price": "",
            "available": available,
            "featured_image": {"src": image_url} if image_url else None,
            "selectedOptions": [],
        }
    ]


def _extract_sibling_handles_from_next_product(product: dict[str, Any]) -> list[str]:
    siblings = product.get("siblings") or []
    handles: list[str] = []
    seen: set[str] = set()

    if isinstance(siblings, list):
        for sibling in siblings:
            if not isinstance(sibling, dict):
                continue

            handle = _safe_str(sibling.get("handle"))
            title = _safe_str(sibling.get("title"))

            if not handle or handle in seen:
                continue

            if _is_non_dress_product({"title": title, "handle": handle, "tags": []}):
                continue

            seen.add(handle)
            handles.append(handle)

    return handles


def _merge_skeleton(product: dict[str, Any], skeleton: dict[str, Any] | None) -> dict[str, Any]:
    if not skeleton:
        return product

    product["_nosto_custom_fields"] = skeleton.get("_nosto_custom_fields", {})
    product["_nosto_attrs"] = skeleton.get("_nosto_attrs", {})

    if not product.get("images") and skeleton.get("images"):
        product["images"] = skeleton.get("images")

    if not product.get("image") and skeleton.get("image"):
        product["image"] = skeleton.get("image")

    if not product.get("price") and skeleton.get("price"):
        product["price"] = skeleton.get("price")

    if not product.get("compare_at_price") and skeleton.get("compare_at_price"):
        product["compare_at_price"] = skeleton.get("compare_at_price")

    return product


def _normalize_next_product(product: dict[str, Any], base_url: str, skeleton: dict[str, Any] | None = None) -> dict[str, Any]:
    handle = _safe_str(product.get("handle"))
    title = _safe_str(product.get("title"))
    tags = _get_tags(product)

    original_price, sale_price = _extract_price_info(product)

    if not sale_price and skeleton:
        sale_price = _parse_price(skeleton.get("sale_price") or skeleton.get("price"))

    if not original_price and skeleton:
        original_price = _parse_price(skeleton.get("original_price") or skeleton.get("compare_at_price")) or sale_price

    image_url = _extract_image_url(product)
    if not image_url and skeleton:
        image_url = _extract_image_url(skeleton)

    variants = _extract_variants(product, sale_price, image_url)

    normalized = {
        "id": product.get("id") or "",
        "title": title,
        "handle": handle,
        "vendor": product.get("vendor") or "Hello Molly",
        "product_type": product.get("productType") or product.get("product_type") or "",
        "productType": product.get("productType") or product.get("product_type") or "",
        "tags": tags,
        "body_html": product.get("descriptionHtml") or product.get("body_html") or "",
        "description": product.get("description") or "",
        "descriptionHtml": product.get("descriptionHtml") or "",
        "availableForSale": bool(product.get("availableForSale", True)),
        "variants": variants,
        "images": [{"src": image_url}] if image_url else [],
        "image": {"src": image_url} if image_url else None,
        "price": sale_price,
        "compare_at_price": original_price if original_price > sale_price else "",
        "original_price": original_price,
        "sale_price": sale_price,
        "siblings": product.get("siblings") or [],
        "_source_base_url": base_url,
    }

    return _merge_skeleton(normalized, skeleton)


def _fetch_product_next_data(
    session: requests.Session,
    base_url: str,
    build_id: str,
    handle: str,
    timeout: int,
    skeleton: dict[str, Any] | None = None,
    *,
    raise_retryable: bool = False,
) -> dict[str, Any] | None:
    if not build_id:
        return skeleton

    url = f"{base_url}/_next/data/{build_id}/products/{handle}.json"
    headers = {
        **HEADERS_JSON,
        "Referer": f"{base_url}/products/{handle}",
    }

    data = _fetch_json_get(
        session,
        url,
        headers=headers,
        timeout=timeout,
        params={"product": handle},
        retries=1,
        raise_retryable=raise_retryable,
    )

    if not data:
        return skeleton

    product = _get_product_from_next_data(data)
    if not product:
        return skeleton

    return _normalize_next_product(product, base_url, skeleton=skeleton)


def _fetch_products_for_whitelist_order(
    session: requests.Session,
    base_url: str,
    build_id: str,
    seed_handles: list[str],
    skeleton_products: dict[str, dict[str, Any]],
    timeout: int,
) -> list[dict[str, Any]]:
    """只补页面白名单商品详情，并严格按页面顺序返回。

    Hello Molly 的商品池和排序来自 Nosto 前台分页 seed_handles。
    Next Data 只用于补这些 handle 的详情/variants/尺码，不允许 siblings 或其他接口新增商品。
    """
    configured_workers = int(os.getenv("HM_DETAIL_WORKERS", "8"))
    max_workers = max(1, min(configured_workers, 12))

    ordered_handles: list[str] = []
    seen: set[str] = set()
    for handle in seed_handles:
        handle = _safe_str(handle)
        if handle and handle not in seen:
            seen.add(handle)
            ordered_handles.append(handle)

    products_by_handle: dict[str, dict[str, Any]] = {}
    retry_queue = RetryQueue(site_key="hellomolly")

    def accept_product(handle: str, product: dict[str, Any] | None) -> None:
        if not product:
            product = skeleton_products.get(handle)
        if not product or _is_non_dress_product(product):
            return
        product_handle = _safe_str(product.get("handle")) or handle
        if product_handle not in seen:
            # Next Data / fallback 只能补页面白名单商品，不能新增页面外商品。
            return
        products_by_handle[product_handle] = product

    def queue_retry(handle: str, error: str) -> None:
        def handler() -> dict[str, Any] | None:
            local_session = requests.Session()
            return _fetch_product_next_data(
                local_session,
                base_url,
                build_id,
                handle,
                timeout,
                skeleton_products.get(handle),
                raise_retryable=True,
            )

        retry_queue.submit(
            task_type="hm_next_data_whitelist",
            identity_key=handle,
            payload={"handle": handle, "base_url": base_url, "build_id": build_id, "first_error": error},
            handler=handler,
            on_success=lambda product, h=handle: accept_product(h, product),
        )

    logger.info(
        "开始 Hello Molly Next Data 按页面白名单补详情：handles=%s workers=%s",
        len(ordered_handles),
        max_workers,
    )

    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="HMDetail") as executor:
        future_map = {
            executor.submit(
                _fetch_product_next_data,
                session,
                base_url,
                build_id,
                handle,
                timeout,
                skeleton_products.get(handle),
                raise_retryable=True,
            ): handle
            for handle in ordered_handles
        }

        for future in as_completed(future_map):
            handle = future_map[future]
            completed += 1
            try:
                product = future.result()
            except Exception as exc:
                logger.warning("Hello Molly 商品详情异常，已进入 retry queue: handle=%s | %s", handle, exc)
                queue_retry(handle, str(exc))
                continue

            accept_product(handle, product)
            if completed % 25 == 0 or completed == len(ordered_handles):
                with_detail = sum(1 for p in products_by_handle.values() if collect_hellomolly_product_detail_text(p))
                with_variants = sum(1 for p in products_by_handle.values() if isinstance(p.get("variants"), list) and p.get("variants"))
                logger.info(
                    "Hello Molly Next Data 进度: %s/%s 成功=%s 有详情=%s 有尺码数据=%s",
                    completed,
                    len(ordered_handles),
                    len(products_by_handle),
                    with_detail,
                    with_variants,
                )

    retry_queue.drain()

    ordered_products: list[dict[str, Any]] = []
    missing_detail = 0
    missing_variants = 0
    for index, handle in enumerate(ordered_handles, start=1):
        product = products_by_handle.get(handle) or skeleton_products.get(handle)
        if not product or _is_non_dress_product(product):
            continue
        product["_source_base_url"] = base_url
        product["_collection_order"] = index
        if not collect_hellomolly_product_detail_text(product):
            missing_detail += 1
        if not (isinstance(product.get("variants"), list) and product.get("variants")):
            missing_variants += 1
        ordered_products.append(product)

    logger.info(
        "Hello Molly 白名单详情补充完成：页面商品=%s 输出=%s next_data=%s missing_detail=%s missing_variants=%s retry_summary=%s",
        len(ordered_handles),
        len(ordered_products),
        len(products_by_handle),
        missing_detail,
        missing_variants,
        retry_queue.summary(),
    )

    return ordered_products


# =========================
# 主抓取
# =========================

def fetch_all_hellomolly_products(config: Config) -> tuple[list[dict[str, Any]], str]:
    base_url = getattr(config, "hm_base_url", HM_BASE_URL) or HM_BASE_URL
    collection_path = getattr(config, "hm_collection_path", HM_COLLECTION_PATH) or HM_COLLECTION_PATH
    timeout = int(getattr(config, "request_timeout", 30) or 30)

    session = _make_session(config)

    build_id = _discover_build_id(
        session=session,
        base_url=base_url,
        collection_path=collection_path,
        timeout=timeout,
    )

    account_id = os.getenv("HM_NOSTO_ACCOUNT_ID", DEFAULT_NOSTO_ACCOUNT_ID).strip()
    category_path = os.getenv("HM_NOSTO_CATEGORY_PATH", DEFAULT_NOSTO_CATEGORY_PATH).strip()

    skeleton_products, seed_handles_from_nosto = _fetch_nosto_category_products(
        session=session,
        base_url=base_url,
        account_id=account_id,
        category_path=category_path,
        timeout=timeout,
    )

    seed_handles: list[str] = []
    seen_handles: set[str] = set()

    for handle in seed_handles_from_nosto:
        if handle and handle not in seen_handles:
            seen_handles.add(handle)
            seed_handles.append(handle)

    logger.info(
        "Hello Molly 页面白名单 handle 数量=%s | nosto=%s | skeleton=%s。已关闭 siblings / HTML fallback / extra handles 扩商品池。",
        len(seed_handles),
        len(seed_handles_from_nosto),
        len(skeleton_products),
    )

    products = _fetch_products_for_whitelist_order(
        session=session,
        base_url=base_url,
        build_id=build_id,
        seed_handles=seed_handles,
        skeleton_products=skeleton_products,
        timeout=timeout,
    )

    products.sort(key=lambda item: int(item.get("_collection_order", 999999)))

    return products, base_url


# =========================
# 记录构建
# =========================

def _build_delisted_record(
    baseline_mgr: BaselineManager,
    key: str,
    info: dict[str, Any],
    scrape_time: str,
) -> HMProductRecord:
    metadata = info.get("metadata", {}) if isinstance(info.get("metadata"), dict) else {}
    fallback_product_name, fallback_color_name = baseline_mgr.split_key(key)

    return HMProductRecord(
        site_name=metadata.get("site_name", "Hello Molly"),
        brand=metadata.get("brand", "Hello Molly"),
        category=metadata.get("category", "Bridesmaid Dresses"),
        style_label=metadata.get("style_label", ""),
        product_url=metadata.get("product_url", ""),
        product_name=metadata.get("product_name", fallback_product_name),
        color_name=metadata.get("color_name", fallback_color_name),
        main_image_url=metadata.get("main_image_url", ""),
        size=metadata.get("size", ""),
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
        relisted_after_delisted=metadata.get("relisted_after_delisted", "否"),
        last_delisted_at=info.get("delisted_at", "") or metadata.get("last_delisted_at", ""),
        is_official_new=metadata.get("is_official_new", "否"),
        status="Delisted",
    )


def _build_records(
    products: list[dict[str, Any]],
    baseline_mgr: BaselineManager,
    is_initialization_phase: bool,
    current_date: str,
    current_time_full: str,
) -> tuple[list[HMProductRecord], set[str]]:
    records: list[HMProductRecord] = []
    active_keys: set[str] = set()

    sorted_products = sorted(
        products,
        key=lambda item: int(item.get("_collection_order", 999999)),
    )

    prepared: list[dict[str, Any]] = []
    best_attrs_by_group: dict[str, dict[str, str]] = {}

    for product in sorted_products:
        raw_title = _safe_str(product.get("title"))
        handle = _safe_str(product.get("handle"))
        source_base_url = _safe_str(product.get("_source_base_url")) or HM_BASE_URL

        if not handle:
            continue

        if _is_non_dress_product(product):
            continue

        style_label, product_name_from_title, title_color = _split_style_color_name(raw_title, handle)
        product_url = _build_product_url(source_base_url, handle)
        tags = _get_tags(product)
        attrs = _extract_attrs(product_name_from_title, tags, product)
        group_key = _hm_style_group_key(style_label, product_name_from_title, product)

        prepared.append(
            {
                "product": product,
                "handle": handle,
                "style_label": style_label,
                "product_name": product_name_from_title,
                "title_color": title_color,
                "product_url": product_url,
                "attrs": attrs,
                "group_key": group_key,
            }
        )

        existing = best_attrs_by_group.get(group_key)
        if not existing or _hm_attr_score(attrs) > _hm_attr_score(existing):
            best_attrs_by_group[group_key] = attrs

    for current_rank, info in enumerate(prepared, start=1):
        product = info["product"]
        product["_collection_order"] = product.get("_collection_order") or current_rank
        handle = info["handle"]
        style_label = info["style_label"]
        product_name_from_title = info["product_name"]
        title_color = info["title_color"]
        product_url = info["product_url"]
        attrs = _hm_merge_attrs(info["attrs"], best_attrs_by_group.get(info["group_key"], {}))

        raw_variants = product.get("variants", []) or []
        has_variant_data = isinstance(raw_variants, list) and any(isinstance(v, dict) for v in raw_variants)
        variants = raw_variants if has_variant_data else [{}]

        color_groups: dict[str, list[dict[str, Any]]] = {}

        nosto_attrs = product.get("_nosto_attrs", {})
        nosto_color = nosto_attrs.get("color") if isinstance(nosto_attrs, dict) else ""

        for variant in variants:
            if not isinstance(variant, dict):
                continue

            if title_color and title_color != "Default":
                color_name = title_color
            else:
                variant_color = _extract_variant_color(variant)
                color_name = nosto_color or variant_color or "Default"

            color_groups.setdefault(color_name, []).append(variant)

        if not color_groups:
            color_groups[title_color or nosto_color or "Default"] = [{}]

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

            size_text = _format_sizes_for_variants(color_variants, has_variant_data)
            stock_type = _stock_type_for_variants(color_variants, has_variant_data)

            image_url = ""
            featured_image = chosen_variant.get("featured_image")
            if isinstance(featured_image, dict):
                image_url = _normalize_image_url(featured_image.get("src") or featured_image.get("url"))

            if not image_url:
                images = product.get("images", []) or []
                if images:
                    first_image = images[0]
                    if isinstance(first_image, dict):
                        image_url = _normalize_image_url(first_image.get("src") or first_image.get("url"))
                    elif isinstance(first_image, str):
                        image_url = _normalize_image_url(first_image)

            record = HMProductRecord(
                site_name="Hello Molly",
                brand=_extract_brand(product),
                category="Bridesmaid Dresses",
                style_label=style_label,
                product_url=product_url,
                product_name=product_name_from_title,
                color_name=color_name,
                size=size_text,
                main_image_url=image_url,
                original_price=_format_price(original_price),
                sale_price=_format_price(price),
                discount_type=discount_type,
                stock_type=stock_type,
                detail_text=collect_hellomolly_product_detail_text(product),
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

            product_key = handle

            baseline_key = baseline_mgr.make_key(product_key, color_name)
            report_metadata = apply_ranking_context(
                record,
                baseline_mgr,
                baseline_key,
                product_key=product_key,
                current_rank=product.get("_collection_order") or current_rank,
                source_page_url=HM_SOURCE_PAGE_URL,
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

    logger.info("========== Hello Molly 自动监控引擎启动 ==========")

    baseline_path = getattr(config, "hm_baseline_path", "hellomolly_baseline.json")
    baseline_mgr = BaselineManager(baseline_path)
    output_dir = getattr(config, "output_dir", "output")
    report_prefix = "hellomolly_report_"
    is_initialization_phase = is_first_site_crawl(output_dir, report_prefix, baseline_mgr)

    current_dt = resolve_current_datetime()
    current_date = current_dt.strftime("%Y-%m-%d")
    current_time_full = current_dt.strftime("%Y-%m-%d %H:%M:%S")

    products, base_url = fetch_all_hellomolly_products(config)

    if not products or not base_url:
        logger.error("Hello Molly 没有抓取到商品，流程结束")
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

    sheet_name = getattr(config, "hm_sheet_name", "HM_伴娘服总表")
    output_dir = getattr(config, "output_dir", "output")

    report_sheets = build_report_sheets(
        full_sheet_name=sheet_name,
        records=records,
        delisted_records=delisted_records,
        is_initialization_phase=is_initialization_phase,
        columns_l2=COLUMNS_L2_HM,
    )

    filepath = DataExporter().export_multiple_sheets(
        report_sheets,
        output_dir,
        prefix=report_prefix,
        header_l1=HEADER_L1_CONFIG_HM,
        columns_l2=COLUMNS_L2_HM,
    )

    cleanup_previous_site_reports(output_dir, report_prefix, filepath)

    logger.info("Excel 已导出: %s", filepath)

    if GSheetSync:
        sheet_id = (
            getattr(config, "gsheet_spreadsheet_id", "")
            or os.getenv("GSHEET_SPREADSHEET_ID", "")
        )
        cred_json = (
            getattr(config, "gsheet_credentials_json", "")
            or os.getenv("GSHEET_CREDENTIALS_JSON", "credentials.json")
        )

        if sheet_id and cred_json and os.path.exists(cred_json):
            try:
                gsync = GSheetSync(sheet_id, cred_json)
                gsync.sync_competitor_report(sheet_name, report_sheets)
            except Exception as exc:
                logger.error("同步 Google Sheets 失败: %s", exc, exc_info=True)
        else:
            logger.info("未配置 Google Sheets，跳过同步")

    logger.info(
        "✅ Hello Molly 处理完成：商品数=%s，颜色行数=%s，下架=%s",
        len(products),
        len(records),
        delisted_count,
    )


def run_hm() -> None:
    main()


if __name__ == "__main__":
    main()
