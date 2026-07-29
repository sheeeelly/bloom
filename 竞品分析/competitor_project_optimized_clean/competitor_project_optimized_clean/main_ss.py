"""Six Stories 自动监控引擎 - 页面白名单 + 详情补充版

目标页面：
https://www.sixstories.com/collections/bridesmaid-dresses?sort_by=manual

核心逻辑：
1. 只读取目标 collection 页面 products.json(sort_by=manual) 的商品，作为页面商品白名单和排序来源。
2. 不再通过 extra collections、PDP Colour、Similar Products、HTML 正则等方式扩充商品池。
3. collection HTML 只用于补款式名，不新增商品。
4. products.json 里的商品 JSON 负责补商品详情、价格、主图、variants、尺码和可售状态。
5. 最终输出严格按页面白名单顺序，接口/HTML 只能补详情，不能新增页面外商品。
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

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
    COLUMNS_L2_SS,
    HEADER_L1_CONFIG_SS,
    SSProductRecord,
)

try:
    from utils.gsheet_sync import GSheetSync
except ImportError:
    GSheetSync = None  # type: ignore


logger = logging.getLogger(__name__)

SS_SOURCE_PAGE_URL = "https://www.sixstories.com/collections/bridesmaid-dresses?sort_by=manual"

try:
    from utils.attribute_extractor import (
        extract_attributes as _common_extract_attributes,
    )
except Exception:  # 兼容未新增公共解析器的旧项目
    _common_extract_attributes = None  # type: ignore

SS_BRAND_NAME = "Six Stories"


# =========================
# Six Stories 配置
# =========================

SS_BASE_URL = "https://www.sixstories.com"
SS_FALLBACK_BASE_URL = "https://www.sixstories.co.uk"
SS_COLLECTION_HANDLE = "bridesmaid-dresses"
# SS 主列表页外，Clearance / Last Chance 里也会出现伴娘服颜色，
# 例如 JANE / Cowl Back Satin Bridesmaid Dress - Fuchsia Pink。
SS_EXTRA_COLLECTION_HANDLES: list[str] = []


HEADERS_JSON = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

HEADERS_HTML = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# =========================
# 关键词配置
# =========================

FABRIC_KEYWORDS = [
    "Hammered Satin",
    "Luxury Satin",
    "Smooth Satin",
    "Satin",
    "Chiffon",
    "Crepe",
    "Sculpt",
    "Mesh",
    "Velvet",
    "Tulle",
    "Lace",
    "Organza",
]

STYLE_KEYWORDS = [
    "Bias Cut",
    "Neck Drape",
    "Drape Detail",
    "Multi-Wear",
    "Neck Scarf",
    "With Neck Scarf",
    "Bow Tie",
    "Bow-Tie",
    "Cinched Waist",
    "Sculptural Neckline",
    "Bardot Neck Strap",
    "Cowl Wrap Neck",
    "Cowl Wrap",
    "Twist Asymmetrical",
    "Twist Bust",
    "Neck Tie",
    "Statement Shoulder",
    "One Shoulder",
    "Cowl Asymmetrical",
    "Asymmetric Neck",
    "Asymmetrical Neck",
    "Cowl Front",
    "Cowl Back",
    "Cami Cowl",
    "Cami",
    "Spaghetti Strap",
    "Spaghetti Straps",
    "Halter Neck",
    "High Neck",
    "Strapless",
    "Wrap Tie",
    "V Neck",
    "V-Neck",
    "Plunge",
    "Bardot",
    "Bandeau",
    "Racer Neck",
    "Flutter Sleeve",
    "Long Sleeve",
    "Short Sleeve",
    "Balloon Sleeve",
    "Bow Tie Shoulder",
    "Bow One Shoulder",
    "Square Neck",
    "Twist Back",
    "Cross Neck",
    "Drape Detail",
    "Knot Front",
    "Gathered Bust",
    "Batwing",
    "Tie Back",
    "Self Tie",
]

LENGTH_KEYWORDS = [
    "Maxi",
    "Midi",
    "Mini",
    "Floor Length",
    "Floor-Length",
    "Short",
    "Long",
]

NECKLINE_KEYWORDS = [
    "Bardot Neck Strap",
    "Bardot Neck",
    "Sculptural Neckline",
    "Neck Drape",
    "Cowl Wrap Neck",
    "Cowl Wrap",
    "Twist Bust",
    "Twist Asymmetrical",
    "Neck Tie",
    "Statement Shoulder",
    "Cowl Front",
    "Cowl Back",
    "Cowl Neck",
    "Cowl",
    "One Shoulder",
    "Asymmetric Neck",
    "Asymmetrical Neck",
    "Halter Neck",
    "High Neck",
    "Strapless",
    "Bandeau",
    "Bardot",
    "Plunge",
    "V Neck",
    "V-Neck",
    "Square Neck",
    "Racer Neck",
    "Cross Neck",
    "Scoop Neck",
]

STYLE_LABEL_BLACKLIST = {
    "NEW IN",
    "BESTSELLERS",
    "BRIDESMAID DRESSES",
    "BRIDAL",
    "WIFEY",
    "ACCESSORIES",
    "BUNDLES",
    "WINTER SALE",
    "SHOP BY COLOUR",
    "SHOP BY COLOR",
    "SHOP BY STYLE",
    "SHOP BY NEED",
    "DRESSES",
    "COLOUR",
    "COLOR",
    "STYLE",
    "MATERIAL",
    "SIZE",
    "PRICE",
    "PRODUCT TYPE",
    "LOVED FOR",
    "GBP",
    "USD",
    "EUR",
    "FILTER",
    "SORT",
}

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


def _make_ss_record(**kwargs: Any) -> SSProductRecord:
    """兼容新版/旧版 SSProductRecord。

    新版 product_record.py 已增加 brand 字段；旧版没有。
    这里优先传 brand，遇到旧版不支持时自动移除，避免和前面补丁冲突。
    """
    try:
        return SSProductRecord(**kwargs)
    except TypeError as exc:
        if "brand" in str(exc):
            kwargs = dict(kwargs)
            kwargs.pop("brand", None)
            return SSProductRecord(**kwargs)
        raise


def _clean_text(value: Any) -> str:
    text = unescape(_safe_str(value))
    # Shopify body_html / description 里会带 HTML 标签；
    # 属性识别必须先去标签，否则 "Maxi length" 等详情文案可能无法稳定命中。
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_price(value: Any) -> float:
    if value is None:
        return 0.0

    if isinstance(value, list):
        value = value[0] if value else 0

    raw_text = str(value).strip()
    if not raw_text:
        return 0.0

    clean_text = re.sub(r"[^0-9.\-]", "", raw_text)

    try:
        price = float(clean_text) if clean_text else 0.0

        # Shopify /products/{handle}.js 有时返回的是 cents，例如 12999
        if "." not in clean_text and price >= 1000:
            price = price / 100

        return price
    except ValueError:
        logger.warning("无法解析价格: %r，按 0 处理", value)
        return 0.0


def _currency_symbol(base_url: str) -> str:
    if "sixstories.co.uk" in base_url:
        return "£"
    return "$"


def _format_price(value: float, base_url: str) -> str:
    symbol = _currency_symbol(base_url)
    return f"{symbol}{value:.2f}"


def _normalize_image_url(url: Any) -> str:
    text = _safe_str(url)

    if not text:
        return ""

    if text.startswith("//"):
        return "https:" + text

    return text


def _find_keyword(text: str, keywords: list[str]) -> str:
    text_lower = _clean_text(text).lower()
    normalized_text = text_lower.replace("-", " ")

    for keyword in keywords:
        keyword_lower = keyword.lower()
        normalized_keyword = keyword_lower.replace("-", " ")

        if keyword_lower in text_lower or normalized_keyword in normalized_text:
            return keyword.replace("-", " ")

    return ""


def _normalize_product_display_name(product_name: str) -> str:
    """
    统一官网展示名。

    Six Stories 个别 DASSI 商品的 /products/{handle}.js title 会返回：
    Cami Cowl Front Satin Bridesmaid Dress - Navy

    但前台 PDP/系列名展示为：
    Cami Cowl Satin Bridesmaid Dress

    因此导出时按前台展示名去掉多余的 Front，避免同一款 DASSI 被拆成两个商品名。
    """
    name = _clean_text(product_name)

    replacements = {
        "Cami Cowl Front Satin Bridesmaid Dress": "Cami Cowl Satin Bridesmaid Dress",
        "Cami Cowl Front Bridesmaid Dress": "Cami Cowl Satin Bridesmaid Dress",
    }

    for source, target in replacements.items():
        if name.lower() == source.lower():
            return target

    return name


def _split_title_color(title: str) -> tuple[str, str]:
    """
    Six Stories 标题常见格式：
    Cowl Back Satin Bridesmaid Dress - Rose
    Cami Cowl Satin Bridesmaid Dress  - Rust
    """
    title = _safe_str(title)

    match = re.match(r"^(.*?)\s+-\s+(.*?)$", title)
    if match:
        product_name = _normalize_product_display_name(match.group(1).strip())
        color_name = match.group(2).strip()
        return product_name, color_name

    return _normalize_product_display_name(title), "Default"


def _normalize_base_product_name(title: str) -> str:
    """
    Cami Cowl Satin Bridesmaid Dress - Rust -> cami cowl satin bridesmaid dress
    """
    base_name, _ = _split_title_color(title)
    base_name = re.sub(r"\s+", " ", base_name).strip().lower()
    return base_name


def _get_tags(product: dict[str, Any]) -> list[str]:
    tags = product.get("tags", []) or []

    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]

    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]

    return []


def _normalize_ss_attr_value(value: str) -> str:
    """统一 Six Stories 导出字段格式，避免 hammered satin / floor length 等原始写法混乱。"""
    raw = _safe_str(value)
    if not raw:
        return ""
    key = raw.strip().lower().replace("-", " ")
    mapping = {
        "hammered satin": "Hammered Satin",
        "luxury satin": "Satin",
        "smooth satin": "Satin",
        "satin": "Satin",
        "chiffon": "Chiffon",
        "maxi": "Maxi",
        "maxi length": "Maxi",
        "floor length": "Maxi",
        "floor length": "Maxi",
        "long": "Maxi",
        "midi": "Midi",
        "mini": "Mini",
        "bardot neck strap": "Bardot Neck Strap",
        "bardot neck": "Bardot Neck",
        "neck drape": "Neck Drape",
        "drape detail": "Drape Detail",
        "bias cut": "Bias Cut",
        "cinched waist": "Cinched Waist",
        "multi wear": "Multi-Wear",
        "neck tie": "Neck Tie",
    }
    return mapping.get(key, raw.replace("-", " "))


def _extract_attrs(
    product_name: str,
    tags: list[str],
    product: dict[str, Any] | None = None,
) -> dict[str, str]:
    """
    从商品名 + tags + 商品详情文案中提取面料/风格/长度/上半身款式。

    Six Stories 的 PRODUCT DETAILS 经常是自然语言：
    - "Bestselling hammered luxury satin"
    - "Bias cut shape for the perfect drape"
    - "Multi-wear neck drape detail"
    - "Concealed side zip & maxi length"

    因此不能只靠产品名 / tag，需要把 body_html / description 里的详情文案一起解析。
    """
    product = product or {}

    detail_text = " ".join(
        [
            product_name,
            _safe_str(product.get("title")),
            _safe_str(product.get("handle")),
            _safe_str(product.get("product_type")),
            _clean_text(product.get("body_html")),
            _clean_text(product.get("description")),
            _clean_text(product.get("product_details")),
            _clean_text(product.get("fabric_details")),
            " ".join(tags),
        ]
    )

    lower_text = detail_text.lower().replace("-", " ").replace("&", " and ")

    fabric = _find_keyword(detail_text, FABRIC_KEYWORDS)
    style = _find_keyword(detail_text, STYLE_KEYWORDS)
    length = _find_keyword(detail_text, LENGTH_KEYWORDS)
    neckline = _find_keyword(detail_text, NECKLINE_KEYWORDS)

    # 面料兜底：Six Stories 会写 "hammered luxury satin"，原关键词容易只命中 Satin。
    if "hammered" in lower_text and "satin" in lower_text:
        fabric = "Hammered Satin"
    elif "luxurious smooth satin" in lower_text or "smooth satin feel" in lower_text or "luxury satin" in lower_text:
        fabric = fabric or "Satin"
    elif "satin" in lower_text:
        fabric = fabric or "Satin"

    # 组合式风格解析，避免只返回单个粗关键词。
    style_parts: list[str] = []

    def add_style(label: str, *patterns: str) -> None:
        if label in style_parts:
            return
        if any(pattern and pattern in lower_text for pattern in patterns):
            style_parts.append(label)

    add_style("Bias Cut", "bias cut shape", "bias cut")
    add_style("Drape Detail", "dramatic neck drape", "neck drape detail", "drape detail", "perfect drape", "elegantly draped")
    add_style("Neck Drape", "neck drape")
    add_style("Multi-Wear", "multi wear", "multiwear", "can be worn loose", "can be worn loose or as a neck tie")
    add_style("Neck Tie", "neck tie")
    add_style("Neck Scarf", "with neck scarf", "chiffon neck scarf", "neck scarf")
    add_style("Bow Tie", "bow tie chiffon bridesmaid dress", "bow tie bridesmaid dress", "bow tie", "bow-tie")
    add_style("Cinched Waist", "cinched at the waist", "cinched waist")
    add_style("Sculptural Neckline", "sculptural neckline")
    add_style("Twist Open Back", "twist open back", "twist back")
    add_style("Open Back", "open back")
    add_style("Concealed Side Zip", "concealed side zip")
    add_style("Self Tie Belt", "self tie fabric belt", "self tie belt")
    add_style("Side Zip", "side zip")
    add_style("A-Line", "a line", "a-line")
    add_style("Cowl Front", "cowl front")
    add_style("Cowl Back", "cowl back")
    add_style("Wrap Tie", "wrap tie")
    add_style("Drape Detail", "drape detail")

    if style_parts:
        # 限制长度，避免一个字段过长；但保留比单个关键词更完整的结构信息。
        style = " / ".join(style_parts[:5])

    if not style:
        if "cowl wrap" in lower_text:
            style = "Cowl Wrap Neck"
        elif "twist asymmetrical" in lower_text:
            style = "Twist Asymmetrical"
        elif "twist bust" in lower_text:
            style = "Twist Bust"
        elif "cowl front" in lower_text:
            style = "Cowl Front"
        elif "cowl back" in lower_text:
            style = "Cowl Back"
        elif "spaghetti" in lower_text or "cami strap" in lower_text:
            style = "Cami"
        elif "maxi gown" in lower_text:
            style = _find_keyword(product_name, STYLE_KEYWORDS)

    # 上半身款式/领型兜底。
    neckline_parts: list[str] = []

    def add_neckline(label: str, *patterns: str) -> None:
        if label in neckline_parts:
            return
        if any(pattern and pattern in lower_text for pattern in patterns):
            neckline_parts.append(label)

    add_neckline("Bardot Neck Strap", "bardot neck strap")
    add_neckline("Bardot Neck", "bardot neck", "bardot")
    add_neckline("Neck Drape", "neck drape")
    add_neckline("One Shoulder", "one shoulder", "one shoulder moment")
    add_neckline("Sculptural Neckline", "sculptural neckline")
    add_neckline("Plunge", "plunge neckline", "plunging neckline", "deep plunge")
    add_neckline("Cowl Front", "cowl front")
    add_neckline("Cowl Back", "cowl back")
    add_neckline("Spaghetti Strap", "spaghetti style adjustable strap", "spaghetti strap", "spaghetti straps")
    add_neckline("Adjustable Strap", "adjustable strap", "adjustable straps")
    add_neckline("High Neck", "high neck")
    add_neckline("Halter Neck", "halter neck")
    add_neckline("Square Neck", "square neck")
    add_neckline("Strapless", "strapless")
    add_neckline("Bow Tie Shoulder", "bow tie shoulder", "bow tie straps", "bow tie")

    if neckline_parts:
        neckline = " / ".join(neckline_parts[:4])

    if not neckline:
        if "cowl wrap" in lower_text:
            neckline = "Cowl Wrap Neck"
        elif "twist bust" in lower_text:
            neckline = "Twist Bust"
        elif "twist asymmetrical" in lower_text:
            neckline = "Twist Asymmetrical"
        elif "cowl front" in lower_text:
            neckline = "Cowl Front"
        elif "cowl back" in lower_text:
            neckline = "Cowl Back"
        elif "cowl neckline" in lower_text or "cowl neck" in lower_text:
            neckline = "Cowl"
        else:
            neckline = style

    # 长度兜底：如果详情明确写了 maxi length 优先解析；如果没写但产品属于 Six Stories Bridesmaid Dress，
    # 且没有 midi/mini/short 等反例，则默认补 Maxi，避免 BELLA/ROMY 这类标准伴娘裙长度空缺。
    if not length:
        if "maxi length" in lower_text or "maxi gown" in lower_text or "maxi dress" in lower_text:
            length = "Maxi"
        elif "floor length" in lower_text or "floor length" in lower_text:
            length = "Maxi"
        elif "midi length" in lower_text or "midi dress" in lower_text:
            length = "Midi"
        elif "mini length" in lower_text or "mini dress" in lower_text:
            length = "Mini"
        elif "short dress" in lower_text:
            length = "Short"
        else:
            title_handle_text = " ".join([
                _safe_str(product.get("title")),
                product_name,
                _safe_str(product.get("handle")),
                _safe_str(product.get("product_type")),
            ]).lower().replace("-", " ")
            # 注意：不要把 scarf 作为长度兜底的反例。
            # Six Stories 有很多真实裙款标题是 "... Bridesmaid Dress With Neck Scarf"，
            # 例如 Plunge Cowl Chiffon Bridesmaid Dress With Neck Scarf / Bandeau Satin Bridesmaid Dress With Chiffon Neck Scarf。
            # 旧逻辑因为 blocked 里包含 scarf，导致这些标准伴娘裙长度为空。
            blocked = ["midi", "mini", "short", "jumpsuit", "bag", "swatch"]
            if "bridesmaid dress" in title_handle_text and not any(word in title_handle_text for word in blocked):
                length = "Maxi"

    result = {
        "fabric_name": _normalize_ss_attr_value(fabric),
        "aesthetic_tag": _normalize_ss_attr_value(style),
        "length": _normalize_ss_attr_value(length),
        "neckline": _normalize_ss_attr_value(neckline),
    }

    # 公共属性解析器只做兜底，不覆盖 Six Stories 本地更精细的规则。
    if _common_extract_attributes is not None:
        try:
            common_attrs = _common_extract_attributes(
                {
                    "title": _safe_str(product.get("title")) or product_name,
                    "product_name": product_name,
                    "handle": product.get("handle"),
                    "body_html": product.get("body_html"),
                    "description": product.get("description"),
                    "product_details": product.get("product_details"),
                    "fabric_details": product.get("fabric_details"),
                    "tags": tags,
                    "product_type": product.get("product_type"),
                    "vendor": product.get("vendor"),
                    "_site": "Six Stories",
                },
                default_floor_length=False,
            )
            for key, value in common_attrs.items():
                if not result.get(key) and value:
                    result[key] = _normalize_ss_attr_value(value)
        except Exception as exc:
            logger.debug("公共属性解析器兜底失败: %s", exc)

    return result

def _extract_handle_from_product_url(href: str) -> str:
    """
    从商品 URL 中提取真实 handle。
    过滤：
    /products/xxx.oembed
    /products/xxx.oembed.js
    /products/xxx.js
    /products/xxx.json
    """
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

    return f"{base_url}/products/{handle}"


def _is_non_dress_product(product: dict[str, Any]) -> bool:
    title = _safe_str(product.get("title")).lower()
    handle = _safe_str(product.get("handle")).lower()
    product_type = _safe_str(product.get("product_type")).lower()
    tags = " ".join(_get_tags(product)).lower()

    text = f"{title} {handle} {product_type} {tags}"

    exclude_keywords = [
        # 非伴娘服/配件商品：collection 页面目前会混入 1 个 Bags 商品，
        # 如果不排除，会进入 Excel 成为 “Six Stories Garment Bag / Default”。
        "garment bag",
        "bag",
        "bags",
        "pouch",
        "pouches",
        "veil",
        "sweatshirt",
        "sweatpants",
        "accessory",
        "accessories",
        "swatch",
        "swatch card",
        "fabric card",
        "satin swatch",
        "chiffon swatch",
        "crepe swatch",
        "colour swatch",
        "color swatch",
    ]

    return any(keyword in text for keyword in exclude_keywords)


def _is_pdp_enrich_enabled(config: Config) -> bool:
    """Six Stories 最终口径：PDP 颜色/相似商品不再扩充商品池。

    商品池和排序必须只来自：
    https://www.sixstories.com/collections/bridesmaid-dresses?sort_by=manual

    PDP / HTML / GraphQL / products.json 只能补白名单商品详情，不能新增页面外商品。
    因此这里强制关闭旧的 PDP Colour / Similar Products 扩色逻辑，忽略 .env 旧开关。
    """
    return False


def _split_csv_env(value: Any) -> list[str]:
    """把环境变量/配置中的逗号分隔集合 handle 拆成列表。"""
    raw = _safe_str(value)
    if not raw:
        return []

    return [
        item.strip().strip("/")
        for item in raw.split(",")
        if item.strip().strip("/")
    ]


def _get_ss_collection_handles(config: Config) -> list[str]:
    """只返回 Six Stories 目标页面对应的主 collection。

    旧逻辑支持 SS_EXTRA_COLLECTION_HANDLES，会把 Clearance / Last Chance 等页面外商品
    合并进商品池。当前需求是“只爬目标网址页面展示的商品”，所以这里忽略
    SS_EXTRA_COLLECTION_HANDLES，只允许主 collection 参与商品池和排序。
    """
    main_handle = (
        os.getenv(
            "SS_COLLECTION_HANDLE",
            str(getattr(config, "ss_collection_handle", SS_COLLECTION_HANDLE)),
        )
        .strip()
        .strip("/")
    ) or SS_COLLECTION_HANDLE

    return [main_handle]


# =========================
# HTML Parser
# =========================

class SixStoriesCollectionHTMLParser(HTMLParser):
    """
    解析 collection 商品卡片里的款式名：
    TILLY / BELLA / ROMY / MYAH 等。
    """

    def __init__(self) -> None:
        super().__init__()
        self.tokens: list[dict[str, str]] = []
        self.current_product_handle: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return

        attrs_dict = {k: v for k, v in attrs}
        href = attrs_dict.get("href") or ""
        handle = _extract_handle_from_product_url(href)

        if handle:
            self.current_product_handle = handle

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a":
            self.current_product_handle = ""

    def handle_data(self, data: str) -> None:
        text = _clean_text(data)

        if not text:
            return

        if self.current_product_handle:
            self.tokens.append(
                {
                    "type": "product_link",
                    "text": text,
                    "handle": self.current_product_handle,
                }
            )
        else:
            self.tokens.append(
                {
                    "type": "text",
                    "text": text,
                    "handle": "",
                }
            )


class ProductLinkHTMLParser(HTMLParser):
    """
    从 PDP 详情页中提取 ProductItem 卡片。
    重点解析：
    - ProductItem__CustomTitle：TILLY / DASSI / BELLA / ROMY
    - ProductItem__Title：Cowl Back Satin Bridesmaid Dress - Rose
    - href：/products/xxx
    """

    def __init__(self) -> None:
        super().__init__()

        self.handles: set[str] = set()
        self.cards: list[dict[str, str]] = []

        self._current_href_handle: str = ""
        self._current_custom_title: str = ""
        self._current_product_title: str = ""

        self._in_custom_title: bool = False
        self._in_product_title: bool = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k: v for k, v in attrs}
        class_name = attrs_dict.get("class") or ""

        if tag.lower() == "h3" and "ProductItem__CustomTitle" in class_name:
            self._in_custom_title = True

        if tag.lower() == "h2" and "ProductItem__Title" in class_name:
            self._in_product_title = True

        if tag.lower() == "a":
            href = attrs_dict.get("href") or ""
            handle = _extract_handle_from_product_url(href)

            if handle:
                self.handles.add(handle)
                self._current_href_handle = handle

        for key in ["data-url", "data-product-url", "data-href"]:
            value = attrs_dict.get(key) or ""
            handle = _extract_handle_from_product_url(value)
            if handle:
                self.handles.add(handle)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag == "h3":
            self._in_custom_title = False

        if tag == "h2":
            self._in_product_title = False

        if tag == "a":
            if self._current_href_handle and self._current_product_title:
                self.cards.append(
                    {
                        "handle": self._current_href_handle,
                        "style_label": self._current_custom_title,
                        "title": self._current_product_title,
                    }
                )

            self._current_href_handle = ""
            self._current_product_title = ""

    def handle_data(self, data: str) -> None:
        text = _clean_text(data)

        if not text:
            return

        if self._in_custom_title:
            self._current_custom_title = text

        if self._in_product_title:
            self._current_product_title = text



class PDPColourLinkHTMLParser(HTMLParser):
    """
    从 PDP 顶部 Colour 色块区域提取同款颜色链接。

    Six Stories 的 Colour 色块是普通 a 标签，链接文本为空；
    旧逻辑只解析 ProductItem__Title 卡片，因此会漏掉这种纯色块链接。
    例如 DASSI / Cami Cowl Satin Bridesmaid Dress 在 PDP 色块区域有 10 个链接，
    但 collection/相似商品卡片可能只展示 9 个。
    """

    SIZE_STOP_PATTERNS = (
        "size",
        "uk size",
        "us size",
        "eu size",
        "add to cart",
        "add to basket",
        "notify me",
        "product details",
        "delivery",
        "returns",
    )

    def __init__(self) -> None:
        super().__init__()
        self.handles: list[str] = []
        self._seen: set[str] = set()
        self._collecting: bool = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self._collecting:
            return

        attrs_dict = {k: v for k, v in attrs}

        values = []
        if tag.lower() == "a":
            values.append(attrs_dict.get("href") or "")

        for key in ["data-url", "data-product-url", "data-href"]:
            values.append(attrs_dict.get(key) or "")

        for value in values:
            handle = _extract_handle_from_product_url(value)
            if not handle:
                continue
            if handle in self._seen:
                continue

            self._seen.add(handle)
            self.handles.append(handle)

    def handle_data(self, data: str) -> None:
        text = _clean_text(data)
        if not text:
            return

        lower_text = text.lower().replace("\xa0", " ").strip()

        # 遇到 Colour: / Color: 后，开始收集后续色块链接。
        if "colour:" in lower_text or "color:" in lower_text:
            self._collecting = True
            return

        # 遇到尺码/加购/详情区，说明顶部色块区结束。
        if self._collecting and any(pattern in lower_text for pattern in self.SIZE_STOP_PATTERNS):
            self._collecting = False


def _extract_pdp_colour_handles_from_html(html: str) -> list[str]:
    """
    只提取 PDP 顶部 Colour 色块区域里的商品 handle。
    这部分链接通常没有标题文本，不能依赖 ProductItem 卡片解析。
    """
    parser = PDPColourLinkHTMLParser()
    parser.feed(html)

    result: list[str] = []
    seen: set[str] = set()

    for handle in parser.handles:
        clean_handle = _extract_handle_from_product_url(f"/products/{handle}")
        if not clean_handle:
            continue
        if "." in clean_handle:
            continue
        if clean_handle in seen:
            continue

        seen.add(clean_handle)
        result.append(clean_handle)

    return result

def _is_style_label(text: str) -> bool:
    text = _clean_text(text)

    if not text:
        return False

    upper_text = text.upper()

    blacklist = {
        "NEW IN",
        "BESTSELLERS",
        "BRIDESMAID DRESSES",
        "BRIDAL",
        "WIFEY",
        "ACCESSORIES",
        "BUNDLES",
        "WINTER SALE",
        "SHOP BY COLOUR",
        "SHOP BY COLOR",
        "SHOP BY STYLE",
        "SHOP BY NEED",
        "DRESSES",
        "COLOUR",
        "COLOR",
        "STYLE",
        "MATERIAL",
        "SIZE",
        "PRICE",
        "PRODUCT TYPE",
        "LOVED FOR",
        "GBP",
        "USD",
        "EUR",
        "FILTER",
        "SORT",
    }

    if upper_text in blacklist:
        return False

    if len(text) < 2 or len(text) > 30:
        return False

    if "DRESS" in upper_text or "DRESSES" in upper_text:
        return False

    if "£" in text or "$" in text or "€" in text:
        return False

    if any(char.isdigit() for char in text):
        return False

    if text != upper_text:
        return False

    if not re.fullmatch(r"[A-Z &'’-]+", text):
        return False

    return True


def _extract_style_label_map_from_html(html: str) -> dict[str, str]:
    parser = SixStoriesCollectionHTMLParser()
    parser.feed(html)

    handle_to_label: dict[str, str] = {}
    tokens = parser.tokens

    for idx, token in enumerate(tokens):
        if token.get("type") != "product_link":
            continue

        handle = token.get("handle", "")
        link_text = token.get("text", "")

        if not handle:
            continue

        if "dress" not in link_text.lower() and "bridesmaid" not in link_text.lower():
            continue

        for lookback_idx in range(idx - 1, max(idx - 12, -1), -1):
            candidate = tokens[lookback_idx].get("text", "")

            if _is_style_label(candidate):
                handle_to_label.setdefault(handle, candidate)
                break

    return handle_to_label


def _extract_product_cards_from_html(html: str) -> list[dict[str, str]]:
    parser = ProductLinkHTMLParser()
    parser.feed(html)

    result: list[dict[str, str]] = []
    seen: set[str] = set()

    for card in parser.cards:
        handle = _safe_str(card.get("handle"))
        title = _safe_str(card.get("title"))
        style_label = _safe_str(card.get("style_label"))

        if not handle or not title:
            continue

        if handle in seen:
            continue

        seen.add(handle)

        result.append(
            {
                "handle": handle,
                "title": title,
                "style_label": style_label,
                "base_product_name": _normalize_base_product_name(title),
            }
        )

    return result


def _extract_product_handles_from_html(html: str) -> set[str]:
    handles: set[str] = set()

    for card in _extract_product_cards_from_html(html):
        handle = _safe_str(card.get("handle"))
        if handle:
            handles.add(handle)

    parser = ProductLinkHTMLParser()
    parser.feed(html)

    for handle in parser.handles:
        clean_handle = _extract_handle_from_product_url(f"/products/{handle}")
        if clean_handle:
            handles.add(clean_handle)

    for match in re.finditer(r"/products/([a-zA-Z0-9_\-]+)(?:[/?#\"'])", html):
        handle = match.group(1).strip()
        clean_handle = _extract_handle_from_product_url(f"/products/{handle}")
        if clean_handle:
            handles.add(clean_handle)

    return handles


def _same_style_family(handle_a: str, handle_b: str) -> bool:
    a = _safe_str(handle_a).lower()
    b = _safe_str(handle_b).lower()

    if not a or not b:
        return False

    if a == b:
        return True

    a_parts = a.split("-")
    b_parts = b.split("-")

    min_len = min(len(a_parts), len(b_parts))
    common = 0

    for idx in range(min_len):
        if a_parts[idx] == b_parts[idx]:
            common += 1
        else:
            break

    return common >= 5


# =========================
# 请求函数
# =========================

def _fetch_html(base_url: str, path_or_url: str, timeout: int, *, raise_retryable: bool = False) -> str:
    if path_or_url.startswith("http"):
        url = path_or_url
    else:
        url = urljoin(base_url, path_or_url)

    try:
        resp = requests.get(url, headers=HEADERS_HTML, timeout=timeout)

        if resp.status_code != 200:
            logger.warning("HTML 请求失败: %s status=%s", url, resp.status_code)
            if resp.status_code in {403, 404, 410}:
                return ""
            if raise_retryable:
                classify_http_status(resp.status_code, url)
            return ""

        return resp.text

    except Exception as exc:
        if raise_retryable and is_retryable_exception(exc):
            raise RetryableTaskError(f"Six Stories HTML retryable error url={url}: {exc}") from exc
        logger.warning("HTML 请求异常: %s | %s", url, exc)
        return ""


def _fetch_product_by_handle(base_url: str, handle: str, timeout: int, *, raise_retryable: bool = False) -> dict[str, Any] | None:
    handle = _safe_str(handle)

    if not handle:
        return None

    if "." in handle:
        return None

    url = f"{base_url}/products/{handle}.js"

    try:
        logger.info("请求 Six Stories 商品 JSON: %s", url)

        resp = requests.get(
            url,
            headers=HEADERS_JSON,
            timeout=timeout,
        )

        if resp.status_code != 200:
            logger.warning(
                "Six Stories 商品 JSON 请求失败: handle=%s status=%s text=%s",
                handle,
                resp.status_code,
                resp.text[:200],
            )
            if resp.status_code in {403, 404, 410}:
                return None
            if raise_retryable:
                classify_http_status(resp.status_code, url)
            return None

        product = resp.json()

        if not isinstance(product, dict):
            return None

        product["_source_base_url"] = base_url
        return product

    except Exception as exc:
        if raise_retryable and is_retryable_exception(exc):
            raise RetryableTaskError(f"Six Stories product.js retryable error handle={handle}: {exc}") from exc
        logger.warning("请求商品 JSON 异常: handle=%s | %s", handle, exc)
        return None


def _fetch_products_page(
    base_url: str,
    collection_handle: str,
    page: int,
    timeout: int,
) -> list[dict[str, Any]] | None:
    url = f"{base_url}/collections/{collection_handle}/products.json"

    params = {
        "limit": 250,
        "page": page,
        "sort_by": "manual",
    }

    try:
        logger.info("请求 Six Stories JSON 集合=%s 第 %s 页: %s", collection_handle, page, url)

        resp = requests.get(
            url,
            params=params,
            headers=HEADERS_JSON,
            timeout=timeout,
        )

        if resp.status_code != 200:
            logger.warning(
                "Six Stories JSON 请求失败：base=%s collection=%s page=%s status=%s text=%s",
                base_url,
                collection_handle,
                page,
                resp.status_code,
                resp.text[:300],
            )
            return None

        data = resp.json()
        products = data.get("products", [])

        if not isinstance(products, list):
            logger.warning("Six Stories JSON 响应 products 不是列表，已忽略")
            return []

        return products

    except Exception as exc:
        logger.error("请求 Six Stories JSON 异常: %s", exc, exc_info=True)
        return None


# =========================
# Collection 抓取
# =========================

def fetch_all_sixstories_products(config: Config) -> tuple[list[dict[str, Any]], str]:
    timeout = int(getattr(config, "request_timeout", 30) or 30)
    collection_handles = _get_ss_collection_handles(config)

    for base_url in [SS_BASE_URL, SS_FALLBACK_BASE_URL]:
        product_by_handle: dict[str, dict[str, Any]] = {}

        for collection_handle in collection_handles:
            page = 1
            empty_or_failed = False

            while True:
                products = _fetch_products_page(base_url, collection_handle, page, timeout)

                if products is None:
                    empty_or_failed = True
                    break

                if not products:
                    logger.info(
                        "Six Stories JSON base=%s collection=%s 第 %s 页为空，停止",
                        base_url,
                        collection_handle,
                        page,
                    )
                    break

                new_count = 0
                updated_count = 0

                for product in products:
                    if not isinstance(product, dict):
                        continue

                    if _is_non_dress_product(product):
                        logger.info("跳过非衣服商品: %s", _safe_str(product.get("title")))
                        continue

                    handle = _safe_str(product.get("handle"))

                    if not handle:
                        continue

                    product["_source_base_url"] = base_url
                    product.setdefault("_ss_collection_handles", [])
                    if collection_handle not in product["_ss_collection_handles"]:
                        product["_ss_collection_handles"].append(collection_handle)

                    if handle not in product_by_handle:
                        product["_collection_order"] = len(product_by_handle) + 1
                        product_by_handle[handle] = product
                        new_count += 1
                    else:
                        existing = product_by_handle[handle]
                        existing_handles = existing.setdefault("_ss_collection_handles", [])
                        if collection_handle not in existing_handles:
                            existing_handles.append(collection_handle)
                        updated_count += 1

                logger.info(
                    "Six Stories JSON base=%s collection=%s 第 %s 页返回=%s 新增=%s 更新=%s 累计=%s",
                    base_url,
                    collection_handle,
                    page,
                    len(products),
                    new_count,
                    updated_count,
                    len(product_by_handle),
                )

                page += 1
                time.sleep(1)

            # 如果主集合都失败了，继续尝试 fallback base_url；如果只是 extra 集合失败，不影响主集合结果。
            if empty_or_failed and not product_by_handle and collection_handle == collection_handles[0]:
                break

        if product_by_handle:
            return sorted(
                product_by_handle.values(),
                key=lambda item: int(item.get("_collection_order", 999999)),
            ), base_url

    return [], ""


def fetch_sixstories_style_label_map(base_url: str, config: Config) -> dict[str, str]:
    timeout = int(getattr(config, "request_timeout", 30) or 30)
    sleep_seconds = 0.8

    handle_to_label: dict[str, str] = {}
    collection_handles = _get_ss_collection_handles(config)
    max_pages = 50

    for collection_handle in collection_handles:
        empty_pages = 0

        for page in range(1, max_pages + 1):
            url = f"{base_url}/collections/{collection_handle}"

            params = {}
            if page > 1:
                params["page"] = page

            try:
                logger.info("请求 Six Stories HTML 集合=%s 第 %s 页: %s", collection_handle, page, url)

                resp = requests.get(
                    url,
                    params=params,
                    headers=HEADERS_HTML,
                    timeout=timeout,
                )

                if resp.status_code != 200:
                    logger.warning(
                        "Six Stories HTML 请求失败：base=%s collection=%s page=%s status=%s",
                        base_url,
                        collection_handle,
                        page,
                        resp.status_code,
                    )
                    break

                page_map = _extract_style_label_map_from_html(resp.text)
                new_count = 0

                for handle, label in page_map.items():
                    if handle not in handle_to_label:
                        handle_to_label[handle] = label
                        new_count += 1

                logger.info(
                    "Six Stories HTML 集合=%s 第 %s 页解析款式名=%s，新增=%s，累计=%s",
                    collection_handle,
                    page,
                    len(page_map),
                    new_count,
                    len(handle_to_label),
                )

                if not page_map:
                    empty_pages += 1
                else:
                    empty_pages = 0

                if empty_pages >= 2:
                    break

                time.sleep(sleep_seconds)

            except Exception as exc:
                logger.error("请求 Six Stories HTML 异常: %s", exc, exc_info=True)
                break

    return handle_to_label


# =========================
# PDP 颜色补抓
# =========================

def _family_key(product: dict[str, Any], style_label_map: dict[str, str]) -> str:
    handle = _safe_str(product.get("handle"))
    title = _safe_str(product.get("title"))
    base_product_name, _ = _split_title_color(title)
    style_label = _safe_str(product.get("_ss_style_label_override")) or style_label_map.get(handle, "")

    if style_label:
        return f"{style_label}::{base_product_name}".lower()

    return base_product_name.lower()


def _title_case_color_slug(value: str) -> str:
    value = _safe_str(value).replace("-", " ")
    return " ".join(part.capitalize() for part in value.split() if part)


def _infer_color_from_title_or_handle(product: dict[str, Any], handle: str) -> str:
    """
    PDP 顶部 Colour 色块有时链接到一个商品 handle，但该商品 title/款式名
    不一定和当前 PDP 完全一致。这里先从商品标题里取颜色，取不到时再从 handle 末尾兜底。
    """
    _, title_color = _split_title_color(_safe_str(product.get("title")))
    if title_color and title_color != "Default":
        return title_color

    handle = _safe_str(handle).lower()
    match = re.search(r"bridesmaid-dress-([a-z0-9-]+)$", handle)
    if match:
        return _title_case_color_slug(match.group(1))

    return ""


def _apply_pdp_family_context(
    product: dict[str, Any],
    *,
    rep_style_label: str,
    rep_display_product_name: str,
    found_handle: str,
) -> dict[str, Any]:
    """
    对 PDP Colour 色块补到的商品，强制继承当前 PDP 的款式上下文。

    例：DASSI / Cami Cowl Satin Bridesmaid Dress 的 Colour 里有 Navy，
    但 Navy 对应 handle/title 可能是 cami-cowl-front-bridesmaid-dress-navy。
    如果不继承 PDP 上下文，Excel 会误出成 TILLY / Cami Cowl Front...。
    """
    if rep_style_label:
        product["_ss_style_label_override"] = rep_style_label

    if rep_display_product_name:
        product["_ss_base_product_name_override"] = _normalize_product_display_name(rep_display_product_name)

    color_name = _infer_color_from_title_or_handle(product, found_handle)
    if color_name:
        product["_ss_color_name_override"] = color_name

    return product


def enrich_products_with_pdp_color_links_by_family(
    products: list[dict[str, Any]],
    base_url: str,
    style_label_map: dict[str, str],
    config: Config,
) -> list[dict[str, Any]]:
    """
    通用版 PDP 颜色补抓：

    旧逻辑只按每个款式取少量代表 PDP，所以会漏掉这类情况：
    - JANE 普通颜色页只展示 14 个色块；
    - Fuchsia Pink / Last Chance 页里又展示更多隐藏色；
    - 某些色块展示名和落地商品 title 不完全一致。

    新逻辑：
    1. 先按款式组选初始 PDP 队列；
    2. 每个 PDP 同时解析：顶部 Colour 色块、页面所有同款 product links、ProductItem 卡片；
    3. 新发现同款 handle 后立即加入产品池，并继续把它的 PDP 加入队列；
    4. 直到该款式没有新颜色为止。

    这样不是只修一个 Fuchsia Pink，而是能覆盖其他款式隐藏在
    Clearance / Last Chance / 异常色块链接里的同类漏色问题。
    """
    timeout = int(getattr(config, "request_timeout", 30) or 30)
    sleep_seconds = float(os.getenv("SS_PDP_SLEEP_SECONDS", "1.5"))
    recursive_enabled = os.getenv("SS_PDP_RECURSIVE_COLOR_ENRICH", "true").strip().lower() in {"1", "true", "yes", "y"}
    max_reps_per_family = int(os.getenv("SS_PDP_MAX_REPS_PER_FAMILY", "3"))
    max_clearance_reps_per_family = int(os.getenv("SS_PDP_MAX_CLEARANCE_REPS_PER_FAMILY", "999"))
    max_pdp_pages_total = int(os.getenv("SS_PDP_MAX_TOTAL_PAGES", "1200"))
    max_pdp_pages_per_family = int(os.getenv("SS_PDP_MAX_PAGES_PER_FAMILY", "80"))

    product_by_handle: dict[str, dict[str, Any]] = {
        _safe_str(product.get("handle")): product
        for product in products
        if _safe_str(product.get("handle"))
    }

    family_to_rep_handles: dict[str, list[str]] = {}

    for product in products:
        handle = _safe_str(product.get("handle"))
        if not handle:
            continue

        family_key = _family_key(product, style_label_map)
        family_to_rep_handles.setdefault(family_key, [])

        collection_handles_for_product = product.get("_ss_collection_handles", []) or []
        is_clearance_product = any(
            "clearance" in _safe_str(item).lower() or "last-chance" in _safe_str(item).lower()
            for item in collection_handles_for_product
        )

        reps = family_to_rep_handles[family_key]
        if handle in reps:
            continue

        clearance_reps = [
            rep for rep in reps
            if any(
                "clearance" in _safe_str(item).lower() or "last-chance" in _safe_str(item).lower()
                for item in (product_by_handle.get(rep, {}).get("_ss_collection_handles", []) or [])
            )
        ]

        if is_clearance_product:
            if len(clearance_reps) < max_clearance_reps_per_family:
                reps.append(handle)
            continue

        if len([rep for rep in reps if rep not in clearance_reps]) < max_reps_per_family:
            reps.append(handle)

    total_seed_count = sum(len(v) for v in family_to_rep_handles.values())

    logger.info(
        "Six Stories PDP 递归颜色补抓启动：商品=%s，款式组=%s，初始PDP=%s，recursive=%s",
        len(product_by_handle),
        len(family_to_rep_handles),
        total_seed_count,
        recursive_enabled,
    )

    processed_pdp_handles: set[str] = set()
    total_pdp_count = 0
    retry_queue_mgr = RetryQueue(site_key="sixstories")
    pdp_html_retry_cache: dict[str, tuple[str, str]] = {}

    def queue_pdp_html_retry(
        *,
        rep_handle: str,
        pdp_base_url: str,
        first_error: str,
    ) -> None:
        def handler() -> str:
            return _fetch_html(
                pdp_base_url,
                f"/products/{rep_handle}",
                timeout,
                raise_retryable=True,
            )

        def on_success(html: str) -> None:
            if html:
                pdp_html_retry_cache[rep_handle] = (html, pdp_base_url)

        retry_queue_mgr.submit(
            task_type="ss_pdp_html",
            identity_key=f"{pdp_base_url}|{rep_handle}",
            payload={
                "handle": rep_handle,
                "base_url": pdp_base_url,
                "url": f"{pdp_base_url}/products/{rep_handle}",
                "first_error": first_error,
            },
            handler=handler,
            on_success=on_success,
            accept_result=lambda html: isinstance(html, str) and bool(html.strip()),
        )

    def queue_product_retry(
        *,
        found_handle: str,
        used_pdp_base_url: str,
        rep_style_label: str,
        rep_display_product_name: str,
        recursive_enabled: bool,
        processed_pdp_handles_ref: set[str],
        queued_ref: set[str],
        queue_ref: list[str],
        first_error: str,
    ) -> None:
        def handler() -> dict[str, Any] | None:
            return _fetch_product_by_handle(used_pdp_base_url, found_handle, timeout, raise_retryable=True)

        def on_success(product: dict[str, Any] | None) -> None:
            if not product or _is_non_dress_product(product):
                return
            patched = _apply_pdp_family_context(
                product,
                rep_style_label=rep_style_label,
                rep_display_product_name=rep_display_product_name,
                found_handle=found_handle,
            )
            product_by_handle[found_handle] = patched
            if recursive_enabled and found_handle not in processed_pdp_handles_ref and found_handle not in queued_ref:
                queue_ref.append(found_handle)
                queued_ref.add(found_handle)

        retry_queue_mgr.submit(
            task_type="ss_product_js",
            identity_key=found_handle,
            payload={"handle": found_handle, "base_url": used_pdp_base_url, "first_error": first_error},
            handler=handler,
            on_success=on_success,
        )


    for family_key, seed_handles in family_to_rep_handles.items():
        queue: list[str] = []
        queued: set[str] = set()

        for handle in seed_handles:
            if handle and handle not in queued:
                queue.append(handle)
                queued.add(handle)

        family_processed_count = 0

        while queue:
            if total_pdp_count >= max_pdp_pages_total:
                logger.warning(
                    "Six Stories PDP 递归颜色补抓达到全局上限：%s，停止后续 PDP 扫描",
                    max_pdp_pages_total,
                )
                return list(product_by_handle.values())

            if family_processed_count >= max_pdp_pages_per_family:
                logger.warning(
                    "Six Stories PDP 递归颜色补抓达到单款式上限：family=%s limit=%s，跳过剩余队列=%s",
                    family_key,
                    max_pdp_pages_per_family,
                    len(queue),
                )
                break

            rep_handle = queue.pop(0)
            if not rep_handle or rep_handle in processed_pdp_handles:
                continue

            rep_product = product_by_handle.get(rep_handle, {})
            if not rep_product:
                continue

            processed_pdp_handles.add(rep_handle)
            total_pdp_count += 1
            family_processed_count += 1

            rep_title = _safe_str(rep_product.get("title"))
            rep_display_product_name, _ = _split_title_color(rep_title)
            rep_display_product_name = _safe_str(rep_product.get("_ss_base_product_name_override")) or rep_display_product_name
            rep_base_product_name = _normalize_base_product_name(rep_title)
            rep_style_label = _safe_str(rep_product.get("_ss_style_label_override")) or style_label_map.get(rep_handle, "")

            logger.info(
                "Six Stories PDP 颜色补抓: total=%s family=%s/%s | 款式组=%s | PDP=%s",
                total_pdp_count,
                family_processed_count,
                max_pdp_pages_per_family,
                family_key,
                rep_handle,
            )

            pdp_base_urls = [
                "https://www.sixstories.com",
                "https://www.sixstories.co.uk",
            ]

            html = ""
            used_pdp_base_url = base_url

            for pdp_base_url in pdp_base_urls:
                try:
                    html = _fetch_html(
                        pdp_base_url,
                        f"/products/{rep_handle}",
                        timeout,
                        raise_retryable=True,
                    )
                except Exception as exc:
                    if is_retryable_exception(exc):
                        logger.warning(
                            "Six Stories PDP HTML 异常，已进入 retry queue: handle=%s base=%s | %s",
                            rep_handle,
                            pdp_base_url,
                            exc,
                        )
                        queue_pdp_html_retry(
                            rep_handle=rep_handle,
                            pdp_base_url=pdp_base_url,
                            first_error=str(exc),
                        )
                    else:
                        logger.warning(
                            "Six Stories PDP HTML 非重试异常，跳过: handle=%s base=%s | %s",
                            rep_handle,
                            pdp_base_url,
                            exc,
                        )
                    html = ""

                if html:
                    used_pdp_base_url = pdp_base_url
                    break

            if not html:
                retry_queue_mgr.drain()

                cached_html = pdp_html_retry_cache.pop(rep_handle, None)
                if cached_html:
                    html, used_pdp_base_url = cached_html
                    logger.info(
                        "Six Stories PDP HTML retry 成功回填: handle=%s base=%s",
                        rep_handle,
                        used_pdp_base_url,
                    )
                else:
                    time.sleep(sleep_seconds)
                    continue

            # 1）PDP 顶部 Colour 色块。链接文本可能为空，必须单独解析。
            colour_handles = _extract_pdp_colour_handles_from_html(html)

            # 2）PDP 源码里所有 product links。用于兜底异常色块：
            # 比如页面展示 Mint Green，但 href/title 实际落到 Fuchsia Pink。
            all_same_family_handles: list[str] = []
            for found_handle in _extract_product_handles_from_html(html):
                if not found_handle or found_handle == rep_handle:
                    continue
                if "." in found_handle:
                    continue
                if _same_style_family(rep_handle, found_handle):
                    all_same_family_handles.append(found_handle)

            # 3）页面下方 ProductItem 卡片。可补 Similar Products / More in this colour。
            product_cards = _extract_product_cards_from_html(html)

            candidate_handles: list[str] = []
            candidate_context: dict[str, str] = {}

            for handle in colour_handles:
                if handle and handle not in candidate_handles:
                    candidate_handles.append(handle)
                    candidate_context[handle] = "colour"

            for handle in all_same_family_handles:
                if handle and handle not in candidate_handles:
                    candidate_handles.append(handle)
                    candidate_context[handle] = "same_family_link"

            logger.info(
                "Six Stories PDP 解析: rep=%s colour=%s same_family_links=%s product_cards=%s candidates=%s",
                rep_handle,
                len(colour_handles),
                len(all_same_family_handles),
                len(product_cards),
                len(candidate_handles),
            )

            added = 0

            for found_handle in candidate_handles:
                if not found_handle or "." in found_handle:
                    continue

                if rep_style_label:
                    # Colour/同款链接来自当前 PDP，优先继承当前 PDP 的款式名。
                    style_label_map[found_handle] = rep_style_label

                if found_handle in product_by_handle:
                    product_by_handle[found_handle] = _apply_pdp_family_context(
                        product_by_handle[found_handle],
                        rep_style_label=rep_style_label,
                        rep_display_product_name=rep_display_product_name,
                        found_handle=found_handle,
                    )

                    if recursive_enabled and found_handle not in processed_pdp_handles and found_handle not in queued:
                        queue.append(found_handle)
                        queued.add(found_handle)
                    continue

                try:
                    product = _fetch_product_by_handle(used_pdp_base_url, found_handle, timeout, raise_retryable=True)
                except Exception as exc:
                    logger.warning("Six Stories 商品 JSON 异常，已进入 retry queue: handle=%s | %s", found_handle, exc)
                    queue_product_retry(
                        found_handle=found_handle,
                        used_pdp_base_url=used_pdp_base_url,
                        rep_style_label=rep_style_label,
                        rep_display_product_name=rep_display_product_name,
                        recursive_enabled=recursive_enabled,
                        processed_pdp_handles_ref=processed_pdp_handles,
                        queued_ref=queued,
                        queue_ref=queue,
                        first_error=str(exc),
                    )
                    continue
                if not product:
                    continue

                if _is_non_dress_product(product):
                    continue

                product = _apply_pdp_family_context(
                    product,
                    rep_style_label=rep_style_label,
                    rep_display_product_name=rep_display_product_name,
                    found_handle=found_handle,
                )

                product_by_handle[found_handle] = product
                added += 1

                logger.info(
                    "PDP 同款颜色补到商品: source=%s | 款式=%s | 商品=%s | handle=%s | title=%s",
                    candidate_context.get(found_handle, "unknown"),
                    rep_style_label,
                    rep_display_product_name,
                    found_handle,
                    _safe_str(product.get("title")),
                )

                if recursive_enabled and found_handle not in processed_pdp_handles and found_handle not in queued:
                    queue.append(found_handle)
                    queued.add(found_handle)

            # 4）ProductItem 卡片兜底。这里有标题和款式名，可用更宽松规则判断。
            for card in product_cards:
                found_handle = _safe_str(card.get("handle"))
                found_title = _safe_str(card.get("title"))
                found_style_label = _safe_str(card.get("style_label"))
                found_base_product_name = _safe_str(card.get("base_product_name"))

                if not found_handle or "." in found_handle:
                    continue

                same_style_label = bool(
                    rep_style_label
                    and found_style_label
                    and rep_style_label.lower() == found_style_label.lower()
                )

                same_base_name = bool(
                    rep_base_product_name
                    and found_base_product_name
                    and rep_base_product_name == found_base_product_name
                )

                same_handle_family = _same_style_family(rep_handle, found_handle)

                if not (same_style_label or same_base_name or same_handle_family):
                    continue

                if found_style_label:
                    style_label_map.setdefault(found_handle, found_style_label)
                elif rep_style_label:
                    style_label_map.setdefault(found_handle, rep_style_label)

                if found_handle in product_by_handle:
                    if recursive_enabled and found_handle not in processed_pdp_handles and found_handle not in queued:
                        queue.append(found_handle)
                        queued.add(found_handle)
                    continue

                try:
                    product = _fetch_product_by_handle(used_pdp_base_url, found_handle, timeout, raise_retryable=True)
                except Exception as exc:
                    logger.warning("Six Stories 商品 JSON 异常，已进入 retry queue: handle=%s | %s", found_handle, exc)
                    queue_product_retry(
                        found_handle=found_handle,
                        used_pdp_base_url=used_pdp_base_url,
                        rep_style_label=rep_style_label,
                        rep_display_product_name=rep_display_product_name,
                        recursive_enabled=recursive_enabled,
                        processed_pdp_handles_ref=processed_pdp_handles,
                        queued_ref=queued,
                        queue_ref=queue,
                        first_error=str(exc),
                    )
                    continue
                if not product:
                    continue

                if _is_non_dress_product(product):
                    continue

                if rep_style_label and same_handle_family:
                    product = _apply_pdp_family_context(
                        product,
                        rep_style_label=rep_style_label,
                        rep_display_product_name=rep_display_product_name,
                        found_handle=found_handle,
                    )

                product_by_handle[found_handle] = product
                added += 1

                logger.info(
                    "PDP ProductItem 补到同款颜色: 款式=%s | 商品=%s | handle=%s",
                    found_style_label or rep_style_label,
                    found_title,
                    found_handle,
                )

                if recursive_enabled and found_handle not in processed_pdp_handles and found_handle not in queued:
                    queue.append(found_handle)
                    queued.add(found_handle)

            if added:
                logger.info(
                    "PDP 颜色补全: rep=%s 新增=%s 当前总商品=%s 队列剩余=%s",
                    rep_handle,
                    added,
                    len(product_by_handle),
                    len(queue),
                )

            time.sleep(sleep_seconds)

    retry_queue_mgr.drain()

    logger.info(
        "Six Stories PDP 递归颜色补抓完成：最终商品=%s，扫描PDP=%s retry_summary=%s",
        len(product_by_handle),
        total_pdp_count,
        retry_queue_mgr.summary(),
    )

    return list(product_by_handle.values())


# =========================
# 商品记录构建
# =========================

def _extract_variant_color(variant: dict[str, Any]) -> str:
    for key in ["option1", "option2", "option3", "title"]:
        value = _safe_str(variant.get(key))

        if not value:
            continue

        lower_value = value.lower().strip()

        if lower_value in SIZE_VALUES:
            continue

        if lower_value.isdigit():
            continue

        if re.fullmatch(r"(uk|us)?\s*\d+", lower_value):
            continue

        return value

    return ""




def _extract_variant_size(variant: dict[str, Any]) -> str:
    """从 Shopify variant 中提取尺码。"""
    for key in ["option1", "option2", "option3", "title"]:
        value = _safe_str(variant.get(key))
        if not value:
            continue
        lower_value = value.lower().strip()
        if lower_value in SIZE_VALUES or re.fullmatch(r"(uk|us)?\s*\d+(?:/\d+)?", lower_value):
            return value
    return ""


def _variant_available(variant: dict[str, Any]) -> bool:
    if "available" in variant:
        return bool(variant.get("available"))
    if "availableForSale" in variant:
        return bool(variant.get("availableForSale"))
    # Shopify products.json variants 通常有 available；没有可靠字段时不误判为缺货。
    return True


def _format_sizes_for_product(product: dict[str, Any]) -> tuple[str, str]:
    """返回（尺码, 库存状态）。

    - 只输出可售尺码；
    - 有 variants 但全部不可售：尺码=无码，库存=缺货；
    - 没有拿到 variants：尺码=未获取，库存=未知。
    """
    variants = product.get("variants", []) or []
    if not isinstance(variants, list) or not variants:
        return "未获取", "未知"

    all_sizes: list[str] = []
    available_sizes: list[str] = []
    has_available = False

    for variant in variants:
        if not isinstance(variant, dict):
            continue
        size = _extract_variant_size(variant)
        if size and size not in all_sizes:
            all_sizes.append(size)
        if _variant_available(variant):
            has_available = True
            if size and size not in available_sizes:
                available_sizes.append(size)

    if available_sizes:
        return " / ".join(available_sizes), "现货"
    if all_sizes and not has_available:
        return "无码", "缺货"
    if all_sizes:
        # 有尺码但没有明确 available 字段时，保留尺码，库存未知。
        return " / ".join(all_sizes), "未知"
    return "未获取", "未知"


def _get_variant_image(product: dict[str, Any], variant: dict[str, Any]) -> str:
    featured_image = variant.get("featured_image")
    if isinstance(featured_image, dict):
        src = featured_image.get("src")
        if src:
            return _normalize_image_url(src)

    images = product.get("images", []) or []
    variant_id = variant.get("id")

    if variant_id:
        for image in images:
            if not isinstance(image, dict):
                continue

            variant_ids = image.get("variant_ids", []) or []
            if variant_id in variant_ids:
                return _normalize_image_url(image.get("src"))

    if images:
        first_image = images[0]
        if isinstance(first_image, dict):
            return _normalize_image_url(first_image.get("src"))
        if isinstance(first_image, str):
            return _normalize_image_url(first_image)

    image = product.get("image")
    if isinstance(image, dict):
        return _normalize_image_url(image.get("src"))
    if isinstance(image, str):
        return _normalize_image_url(image)

    return ""


def _build_delisted_record(
    baseline_mgr: BaselineManager,
    key: str,
    info: dict[str, Any],
    scrape_time: str,
) -> SSProductRecord:
    metadata = info.get("metadata", {}) if isinstance(info.get("metadata"), dict) else {}
    fallback_product_name, fallback_color_name = baseline_mgr.split_key(key)

    return _make_ss_record(
        site_name=metadata.get("site_name", "Six Stories"),
        brand=metadata.get("brand", SS_BRAND_NAME),
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



def _ss_family_export_key(product: dict[str, Any], style_label_map: dict[str, str]) -> tuple[str, str]:
    """用于同款属性回填的导出维度 key：款式名 + 规范商品名。"""
    raw_title = _safe_str(product.get("title"))
    base_product_name, _ = _split_title_color(raw_title)
    base_product_name = _normalize_product_display_name(base_product_name)

    base_product_name_override = _safe_str(product.get("_ss_base_product_name_override"))
    if base_product_name_override:
        base_product_name = _normalize_product_display_name(base_product_name_override)

    handle = _safe_str(product.get("handle"))
    style_label = _safe_str(product.get("_ss_style_label_override")) or style_label_map.get(handle, "")
    return style_label.lower().strip(), base_product_name.lower().strip()


def _pick_best_ss_length(length_values: list[str]) -> str:
    """同款多色长度回填时，按更明确的长度优先。"""
    priority = ["Maxi", "Floor Length", "Floor-Length", "Midi", "Mini", "Short", "Long"]
    normalized: list[str] = []
    seen: set[str] = set()
    for value in length_values:
        norm = _normalize_ss_attr_value(value)
        if norm and norm not in seen:
            seen.add(norm)
            normalized.append(norm)
    for target in priority:
        target_norm = _normalize_ss_attr_value(target)
        if target_norm in normalized:
            return target_norm
    return normalized[0] if normalized else ""


def _backfill_same_product_length(
    products: list[dict[str, Any]],
    style_label_map: dict[str, str],
) -> None:
    """
    同一款 Six Stories 商品不同颜色之间回填长度。

    例如同款 Rust PDP 详情写了 "Concealed side zip & maxi length"，
    但 Champagne / Moss Green 颜色页没写长度时，导出前把 Rust 的 Maxi
    回填给同款其他颜色，避免同产品不同颜色长度为空。
    """
    family_lengths: dict[tuple[str, str], list[str]] = {}

    for product in products:
        if not isinstance(product, dict):
            continue
        raw_title = _safe_str(product.get("title"))
        base_product_name, _ = _split_title_color(raw_title)
        base_product_name = _normalize_product_display_name(base_product_name)
        base_product_name_override = _safe_str(product.get("_ss_base_product_name_override"))
        if base_product_name_override:
            base_product_name = _normalize_product_display_name(base_product_name_override)

        tags = _get_tags(product)
        attrs = _extract_attrs(base_product_name, tags, product)
        length = _safe_str(attrs.get("length"))
        if not length:
            continue
        key = _ss_family_export_key(product, style_label_map)
        if key[1]:
            family_lengths.setdefault(key, []).append(length)

    family_best_length: dict[tuple[str, str], str] = {
        key: _pick_best_ss_length(values)
        for key, values in family_lengths.items()
        if _pick_best_ss_length(values)
    }

    backfilled = 0
    for product in products:
        if not isinstance(product, dict):
            continue
        key = _ss_family_export_key(product, style_label_map)
        best_length = family_best_length.get(key, "")
        if not best_length:
            continue

        raw_title = _safe_str(product.get("title"))
        base_product_name, _ = _split_title_color(raw_title)
        base_product_name = _normalize_product_display_name(base_product_name)
        base_product_name_override = _safe_str(product.get("_ss_base_product_name_override"))
        if base_product_name_override:
            base_product_name = _normalize_product_display_name(base_product_name_override)
        current_attrs = _extract_attrs(base_product_name, _get_tags(product), product)
        if not _safe_str(current_attrs.get("length")):
            product["_ss_length_backfill"] = best_length
            backfilled += 1

    logger.info(
        "Six Stories 同款长度回填完成：款式组=%s 回填商品=%s",
        len(family_best_length),
        backfilled,
    )


def _build_records(
    products: list[dict[str, Any]],
    style_label_map: dict[str, str],
    baseline_mgr: BaselineManager,
    is_initialization_phase: bool,
    current_date: str,
    current_time_full: str,
) -> tuple[list[SSProductRecord], set[str]]:
    records: list[SSProductRecord] = []
    active_keys: set[str] = set()

    _backfill_same_product_length(products, style_label_map)

    sorted_products = sorted(products, key=lambda item: int(item.get("_collection_order", 999999)))

    for current_rank, product in enumerate(sorted_products, start=1):
        product["_collection_order"] = product.get("_collection_order") or current_rank
        raw_title = _safe_str(product.get("title"))
        base_product_name, title_color = _split_title_color(raw_title)
        base_product_name = _normalize_product_display_name(base_product_name)

        handle = _safe_str(product.get("handle"))
        style_label = _safe_str(product.get("_ss_style_label_override")) or style_label_map.get(handle, "")

        base_product_name_override = _safe_str(product.get("_ss_base_product_name_override"))
        if base_product_name_override:
            base_product_name = _normalize_product_display_name(base_product_name_override)

        title_color_override = _safe_str(product.get("_ss_color_name_override"))
        if title_color_override:
            title_color = title_color_override

        source_base_url = _safe_str(product.get("_source_base_url")) or SS_BASE_URL
        product_url = _build_product_url(source_base_url, handle)

        tags = _get_tags(product)
        variants = product.get("variants", []) or []
        if not isinstance(variants, list):
            variants = []

        # Six Stories 的列表页商品本身通常已经是 SKC（一个颜色一个商品），
        # variants 主要表示尺码。因此导出一行商品，用 variants 聚合尺码和库存。
        representative_variant = variants[0] if variants and isinstance(variants[0], dict) else {}

        if title_color and title_color != "Default":
            color_name = title_color
        else:
            color_name = _extract_variant_color(representative_variant) or "Default"

        attrs = _extract_attrs(base_product_name, tags, product)
        if not _safe_str(attrs.get("length")) and _safe_str(product.get("_ss_length_backfill")):
            attrs["length"] = _normalize_ss_attr_value(_safe_str(product.get("_ss_length_backfill")))

        price = _parse_price(
            representative_variant.get("price")
            or product.get("price")
            or product.get("price_min")
        )

        compare_price = _parse_price(
            representative_variant.get("compare_at_price")
            or product.get("compare_at_price")
            or product.get("compare_at_price_max")
        )

        original_price = compare_price if compare_price > price else price
        discount_type = "打折" if original_price > price else "无折扣"
        size_text, stock_type = _format_sizes_for_product(product)

        record = _make_ss_record(
            site_name="Six Stories",
            brand=SS_BRAND_NAME,
            category="Bridesmaid Dresses",
            style_label=style_label,
            product_url=product_url,
            product_name=base_product_name,
            color_name=color_name,
            size=size_text,
            main_image_url=_get_variant_image(product, representative_variant),
            original_price=_format_price(original_price, source_base_url),
            sale_price=_format_price(price, source_base_url),
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
            is_official_new="否",
            status="Active",
        )

        product_key = handle or f"{style_label}::{base_product_name}"

        baseline_key = baseline_mgr.make_key(product_key, color_name)
        report_metadata = apply_ranking_context(
            record,
            baseline_mgr,
            baseline_key,
            product_key=product_key,
            current_rank=product.get("_collection_order") or current_rank,
            source_page_url=SS_SOURCE_PAGE_URL,
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
# 颜色完整性检查 Sheet
# =========================

HEADER_L1_CONFIG_SS_COLOR_AUDIT = [
    ("颜色完整性检查", 10),
]

COLUMNS_L2_SS_COLOR_AUDIT = [
    "网站名", "品牌", "类目", "款式名", "商品名称",
    "颜色数量", "颜色列表", "是否疑似异常", "异常原因", "样例商品链接",
]


class SSColorAuditRecord:
    def __init__(self, row: list[str]) -> None:
        self._row = row

    def to_row(self) -> list[str]:
        return self._row


def _build_ss_color_audit_records(records: list[SSProductRecord]) -> list[SSColorAuditRecord]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}

    for record in records:
        if getattr(record, "status", "") != "Active":
            continue

        style_label = _safe_str(getattr(record, "style_label", ""))
        product_name = _safe_str(getattr(record, "product_name", ""))
        color_name = _safe_str(getattr(record, "color_name", ""))
        key = (style_label, product_name)

        if key not in groups:
            groups[key] = {
                "site_name": _safe_str(getattr(record, "site_name", "Six Stories")) or "Six Stories",
                "brand": _safe_str(getattr(record, "brand", SS_BRAND_NAME)) or SS_BRAND_NAME,
                "category": _safe_str(getattr(record, "category", "Bridesmaid Dresses")) or "Bridesmaid Dresses",
                "style_label": style_label,
                "product_name": product_name,
                "colors": set(),
                "urls": [],
                "missing_color": 0,
                "missing_image": 0,
                "missing_price": 0,
                "missing_style": 0,
                "missing_length": 0,
                "missing_neckline": 0,
            }

        group = groups[key]
        if color_name:
            group["colors"].add(color_name)
        else:
            group["missing_color"] += 1

        url = _safe_str(getattr(record, "product_url", ""))
        if url:
            group["urls"].append(url)
        if not _safe_str(getattr(record, "main_image_url", "")):
            group["missing_image"] += 1
        if not _safe_str(getattr(record, "sale_price", "")):
            group["missing_price"] += 1
        if not _safe_str(getattr(record, "aesthetic_tag", "")):
            group["missing_style"] += 1
        if not _safe_str(getattr(record, "length", "")):
            group["missing_length"] += 1
        if not _safe_str(getattr(record, "neckline", "")):
            group["missing_neckline"] += 1

    rows: list[SSColorAuditRecord] = []
    for group in sorted(groups.values(), key=lambda item: (item["style_label"], item["product_name"])):
        colors = sorted(group["colors"], key=lambda x: x.lower())
        issues: list[str] = []
        if len(colors) <= 1:
            issues.append("颜色数<=1，需确认是否单色款或漏色")
        if group["missing_color"]:
            issues.append(f"颜色为空 {group['missing_color']} 行")
        if group["missing_image"]:
            issues.append(f"主图为空 {group['missing_image']} 行")
        if group["missing_price"]:
            issues.append(f"售价为空 {group['missing_price']} 行")
        if group["missing_style"]:
            issues.append(f"风格为空 {group['missing_style']} 行")
        if group["missing_length"]:
            issues.append(f"长度为空 {group['missing_length']} 行")
        if group["missing_neckline"]:
            issues.append(f"上半身款式为空 {group['missing_neckline']} 行")

        rows.append(
            SSColorAuditRecord(
                [
                    group["site_name"],
                    group["brand"],
                    group["category"],
                    group["style_label"],
                    group["product_name"],
                    str(len(colors)),
                    " | ".join(colors),
                    "是" if issues else "否",
                    "；".join(issues),
                    group["urls"][0] if group["urls"] else "",
                ]
            )
        )

    return rows


def _is_ss_color_audit_enabled(config: Config) -> bool:
    value = os.getenv(
        "SS_ENABLE_COLOR_AUDIT_SHEET",
        str(getattr(config, "ss_enable_color_audit_sheet", "true")),
    ).strip().lower()
    return value in {"1", "true", "yes", "y"}







# =========================
# 主流程
# =========================

def main() -> None:
    config = Config.load()

    logging.basicConfig(
        level=getattr(logging, getattr(config, "log_level", "INFO"), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    logger.info("========== Six Stories 自动监控引擎启动 ==========")

    baseline_path = getattr(config, "ss_baseline_path", "sixstories_baseline.json")
    baseline_mgr = BaselineManager(baseline_path)
    output_dir = getattr(config, "output_dir", "output")
    report_prefix = "sixstories_report_"
    is_initialization_phase = is_first_site_crawl(output_dir, report_prefix, baseline_mgr)

    current_dt = resolve_current_datetime()
    current_date = current_dt.strftime("%Y-%m-%d")
    current_time_full = current_dt.strftime("%Y-%m-%d %H:%M:%S")

    products, base_url = fetch_all_sixstories_products(config)

    if not products or not base_url:
        logger.error("Six Stories 没有抓取到商品，流程结束")
        return

    style_label_map = fetch_sixstories_style_label_map(base_url, config)

    logger.info(
        "Six Stories 页面白名单商品数=%s；商品池和排序只来自 %s，已关闭 extra collections / PDP Colour / Similar Products 扩商品池。",
        len(products),
        SS_SOURCE_PAGE_URL,
    )

    records, active_keys = _build_records(
        products=products,
        style_label_map=style_label_map,
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

    sheet_name = getattr(config, "ss_sheet_name", "SS_伴娘服总表")
    output_dir = getattr(config, "output_dir", "output")

    report_sheets = build_report_sheets(
        full_sheet_name=sheet_name,
        records=records,
        delisted_records=delisted_records,
        is_initialization_phase=is_initialization_phase,
        columns_l2=COLUMNS_L2_SS,
    )

    filepath = DataExporter().export_multiple_sheets(
        report_sheets,
        output_dir,
        prefix=report_prefix,
        header_l1=HEADER_L1_CONFIG_SS,
        columns_l2=COLUMNS_L2_SS,
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
                if _is_ss_color_audit_enabled(config):
                    color_audit_records = _build_ss_color_audit_records(records)
                    try:
                        gsync.sync_data(
                            "颜色完整性检查",
                            color_audit_records,
                            headers=COLUMNS_L2_SS_COLOR_AUDIT,
                        )
                    except Exception as exc:
                        logger.warning("同步颜色完整性检查到 Google Sheets 失败，已跳过: %s", exc)
            except Exception as exc:
                logger.error("同步 Google Sheets 失败: %s", exc, exc_info=True)
        else:
            logger.info("未配置 Google Sheets，跳过同步")

    logger.info(
        "✅ Six Stories 处理完成：款式数=%s，颜色行数=%s，HTML款式名=%s，下架=%s",
        len(products),
        len(records),
        len(style_label_map),
        delisted_count,
    )


def run_ss() -> None:
    main()


if __name__ == "__main__":
    main()
