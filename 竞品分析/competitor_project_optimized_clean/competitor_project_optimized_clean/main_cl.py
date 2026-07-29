"""Club L London 自动监控引擎 - 前台页面白名单排序 + GraphQL 批量补详情版。

最终口径：
- 前台页面只负责确认商品池和排序；
- GraphQL 只负责补白名单商品的详情、价格、variants/尺码；
- HTML PDP 只作为缺失兜底；
- 不再通过 GraphQL collection、product.js、products.json、SWYM、同款颜色扩展新增页面外商品。
"""

from __future__ import annotations

import json
import logging
import os
import re
import random
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import fields, is_dataclass
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from utils.baseline_manager import BaselineManager
from utils.report_history import cleanup_previous_site_reports, is_first_site_crawl, resolve_current_datetime
from utils.config import Config
from utils.data_exporter import DataExporter
from utils.product_details import collect_clublondon_product_detail_text
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
    from utils.gsheet_sync import GSheetSync
except ImportError:
    GSheetSync = None  # type: ignore


logger = logging.getLogger(__name__)

CL_SOURCE_PAGE_URL = "https://clubllondon.com/collections/bridesmaids"

# Club L HTML 软失败缓存：避免同一个 handle 在颜色扩展阶段 404/503 失败后，
# 又在商品详情兜底阶段重复请求同一个 URL，导致“看起来爬完了还在爬”。
_CL_HTML_SOFT_FAILED_HANDLES: set[str] = set()
_CL_HTML_SOFT_FAILED_LOCK = threading.Lock()


def _remember_cl_html_soft_failed_handle(url: str, status_code: int) -> None:
    """记录 HTML 多次重试仍失败的商品 handle，用于后续兜底阶段去重跳过。"""
    try:
        parsed = urlparse(url)
        path = parsed.path or url
    except Exception:
        path = url

    if "/products/" not in path:
        return

    handle = path.split("/products/", 1)[1].split("/", 1)[0]
    handle = handle.split("?", 1)[0].split("#", 1)[0].strip().lower()
    for suffix in (".js", ".json", ".oembed"):
        if handle.endswith(suffix):
            handle = handle[: -len(suffix)]
            break

    if not handle:
        return

    with _CL_HTML_SOFT_FAILED_LOCK:
        _CL_HTML_SOFT_FAILED_HANDLES.add(handle)

    logger.info(
        "Club L HTML 软失败已记录，后续 HTML 详情兜底跳过: handle=%s status=%s",
        handle,
        status_code,
    )


def _get_cl_html_soft_failed_handles() -> set[str]:
    with _CL_HTML_SOFT_FAILED_LOCK:
        return set(_CL_HTML_SOFT_FAILED_HANDLES)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, str(default))).strip())
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name, str(default))).strip())
    except Exception:
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    """Safely convert loose frontend state values to int.

    CL 前台页面状态中的 productCount 可能是字符串、数字或 None。
    这里本地定义转换函数，避免读取前台排序时因为 helper 缺失直接失败。
    """
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value).strip()
        if not text:
            return default
        # 支持 "296 products" / "296" / "296.0" 这类格式。
        match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
        if not match:
            return default
        return int(float(match.group(0)))
    except Exception:
        return default


CL_BASE_URL = "https://clubllondon.com"
CL_COLLECTION_HANDLE = "bridesmaids"
CL_GRAPHQL_URL = "https://club-l-london.myshopify.com/api/2026-01/graphql.json"
CL_BRAND_NAME = "Club L London"

HEADERS_HTML = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
}


_CL_HTML_REQUEST_LOCK = threading.Lock()
_CL_HTML_LAST_REQUEST_AT = 0.0


def _throttle_cl_html_request() -> None:
    """Club L HTML 全局限速。

    同款颜色扩展必须访问商品 HTML 页，但 Club L 对短时间大量 HTML 请求容易返回 503。
    这里对所有 Club L HTML 请求做进程内全局限速，即使后面误开多线程，也不会瞬时打爆。
    """
    global _CL_HTML_LAST_REQUEST_AT

    min_interval = max(0.0, _env_float("CL_HTML_MIN_INTERVAL_SECONDS", 6.0))
    jitter = max(0.0, _env_float("CL_HTML_MIN_INTERVAL_JITTER_SECONDS", 1.5))

    if min_interval <= 0:
        return

    with _CL_HTML_REQUEST_LOCK:
        now = time.monotonic()
        elapsed = now - _CL_HTML_LAST_REQUEST_AT
        wait_seconds = max(0.0, min_interval - elapsed)
        if jitter > 0:
            wait_seconds += random.uniform(0, jitter)

        if wait_seconds > 0:
            time.sleep(wait_seconds)

        _CL_HTML_LAST_REQUEST_AT = time.monotonic()

HEADERS_JSON = {
    "User-Agent": HEADERS_HTML["User-Agent"],
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://clubllondon.com/collections/bridesmaids",
}

HEADERS_GRAPHQL = {
    "User-Agent": HEADERS_HTML["User-Agent"],
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://clubllondon.com",
    "Referer": "https://clubllondon.com/collections/bridesmaids",
}


FABRIC_KEYWORDS = [
    "Matte Satin", "Stretch Satin", "Duchess Satin", "Lightweight Woven", "Woven",
    "Broderie Anglaise", "Solton", "Satin", "Chiffon", "Crepe Jersey",
    "Scuba Crepe", "Crepe", "Mesh", "Lace", "Velvet", "Tulle", "Sequin", "Sequinned",
    "Jersey", "Organza", "Luxe", "Slinky", "Scuba", "Georgette",
]

STYLE_KEYWORDS = [
    "Bodycon", "Fishtail", "Mermaid", "A-Line", "Column", "Column Silhouette",
    "Structured", "Soft Volume", "Clean Lines", "Straight Skirt", "Centre Back Split", "Center Back Split",
    "Slip",
    "Wrap", "Ruched", "Ruching", "Draped Detail", "Draped", "Drape", "Sash Detail", "Sash", "Side Split", "Side-Split", "Front High Split", "High Split", "Corset",
    "Backless", "Open Back", "Back Cowl Drape", "Cold Shoulder", "Belt Feature", "Pleated Detailing", "Pleated",
    "Cape", "With Scarf", "Scarf", "Jumpsuit", "Multiway",
    "Asymmetric", "Asymmetrical", "Twist", "Tie",
    "Cut Out", "Cut-Out", "Embellished", "Embellished Back Detail", "Feather", "Ruffle", "Ruffled",
    "Bow", "Split", "Thigh Split", "Gathered", "Drop-Waist", "Drop Waist",
]

LENGTH_KEYWORDS = ["Maxi", "Midi", "Mini", "Long", "Short"]

NECKLINE_KEYWORDS = [
    "Bandeau", "One Shoulder", "One-Shoulder", "Asymmetric",
    "Asymmetrical", "Asymmetric-Neck", "Off Shoulder", "Off The Shoulder",
    "Bardot", "Plunge", "Cowl", "Halter", "Halter Neck",
    "High Neck", "High-Neck", "Round Neck", "Round-Neck",
    "Round Neckline", "Round-Neckline", "Round",
    "Wide Neckline", "Wide-Neckline", "Wide Neck", "Wide-Neck",
    "Cut-Out Neckline", "Cut Out Neckline", "Cut-Out Neck", "Cut Out Neck",
    "Slashed Neckline", "Slashed Neck", "Crew Neckline", "Crew-Neckline",
    "Short Sleeve", "Short Sleeves", "Sleeveless", "Fine Shoulder Straps", "Shoulder Straps",
    "Underwired Cups", "Underwire Cups",
    "V Neck", "V-Neck", "Square Neck", "Square-Neck", "Sweetheart",
    "Strapless", "Scoop Neck", "Scoop-Neck", "Crew Neck", "Crew-Neck",
    "Cami",
]

COLOR_KEYWORDS = [
    "White And Black",
    "Black And White",
    "Pale Pink",
    "Light Pink",
    "Blush Pink",
    "Baby Pink",
    "Hot Pink",
    "Dusty Rose",
    "Powder Blue",
    "Light Blue",
    "Baby Blue",
    "Dusty Blue",
    "Sky Blue",
    "Cobalt Blue",
    "Royal Blue",
    "Steel Blue",
    "Ice Blue",
    "Navy",
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
    "Dark Brown",
    "Brown",
    "Nude",
    "Beige",
    "Blush",
    "Pink",
    "Rose",
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
    "Lime",
    "Sage",
    "Olive",
    "Khaki",
    "Emerald",
    "Forest Green",
    "Mint",
    "Green",
    "Teal",
    "Aqua",
    "Purple",
    "Lilac",
    "Lavender",
    "Orchid",
    "Plum",
    "Aubergine",
    "Silver",
    "Gold",
    "Grey",
    "Gray",
    "Multi",
    "Floral",
]

SIZE_VALUES = {
    "default title", "default", "one size", "os",
    "xxs", "xs", "s", "m", "l", "xl", "xxl", "2xl", "3xl", "4xl",
    "uk 4", "uk 6", "uk 8", "uk 10", "uk 12", "uk 14", "uk 16", "uk 18",
    "uk 20", "uk 22", "uk 24", "uk 26",
    "us 0", "us 2", "us 4", "us 6", "us 8", "us 10", "us 12", "us 14",
    "us 16", "us 18", "us 20", "us 22", "us 24", "us 26",
    "4", "6", "8", "10", "12", "14", "16", "18", "20", "22", "24", "26",
}


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
    return match.group(1) if match else ""


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
    return f"£{value:.2f}"


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


def _get_color_slugs() -> list[str]:
    return sorted(
        {_slugify(color) for color in COLOR_KEYWORDS if color},
        key=len,
        reverse=True,
    )


def _find_keyword(text: str, keywords: list[str]) -> str:
    original_lower = text.lower()
    normalized_lower = original_lower.replace("-", " ")

    for keyword in keywords:
        keyword_lower = keyword.lower()
        keyword_normalized = keyword_lower.replace("-", " ")
        if keyword_lower in original_lower or keyword_normalized in normalized_lower:
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
    for key, value in incoming.items():
        if value in [None, "", [], {}]:
            continue
        existing[key] = value
    return existing


def _merge_product_js(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    protected_keys = {
        "price",
        "price_min",
        "compare_at_price",
        "compare_at_price_max",
        "variants",
    }

    for key, value in incoming.items():
        if value in [None, "", [], {}]:
            continue

        if key in protected_keys and existing.get(key) not in [None, "", [], {}, 0]:
            continue

        existing[key] = value

    return existing


def _extract_attrs(
    product_name: str,
    tags: list[str],
    product: dict[str, Any] | None = None,
) -> dict[str, str]:
    """
    Club L 属性解析。

    兼容前面新增的 utils.attribute_extractor：
    - 如果公共解析器存在，优先用公共解析器，保证全站字段口径统一；
    - 如果公共解析器不存在或返回为空，则回退到本文件原有关键词逻辑；
    - 返回字段保持 main_cl 原格式，不影响后续 ProductRecord 构建。
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
            _safe_str(product.get("vendor")),
            " ".join(tags),
        ]
    )

    lower_text = detail_text.lower().replace("-", " ")

    fabric = _find_keyword(detail_text, FABRIC_KEYWORDS)
    if "scuba crepe" in lower_text:
        fabric = "Scuba Crepe"
    length = _find_keyword(detail_text, LENGTH_KEYWORDS)
    neckline = _find_keyword(detail_text, NECKLINE_KEYWORDS)
    style = _find_keyword(detail_text, STYLE_KEYWORDS)

    # Club L 的 Features 文案经常把风格点拆成多行：
    # - Draped detail
    # - Sash detail
    # - Side-split
    # 单个关键词命中只会返回一个值，容易丢掉其它风格点；这里组合输出，
    # 但只收集明确出现在标题/Description/Features 中的词，不做臆测。
    style_parts: list[str] = []
    style_patterns = [
        ("Column Silhouette", ["column silhouette"]),
        ("Straight Skirt", ["straight skirt"]),
        ("Centre Back Split", ["centre back split", "center back split", "centre-back split", "center-back split"]),
        ("Front High Split", ["front high split", "front-high split"]),
        ("Side Split", ["side split", "side-split", "side split detail", "side split for"]),
        ("Draped", ["draped detail", "drape detail", "draped", "drape"]),
        ("Gathered", ["gathered detailing", "gathered detail", "gathered"]),
        ("Ruched", ["ruched", "ruching"]),
        ("Pleated", ["pleated detailing", "pleating", "pleated"]),
        ("Belt Feature", ["belt feature", "belt detail", "belt to cinch", "belt"]),
        ("Sash Detail", ["sash detail", "sash"]),
        ("Cold Shoulder", ["cold shoulder detail", "cold shoulder"]),
        ("Open Back", ["open back", "open-back"]),
        ("Back Cowl Drape", ["back cowl-drape", "back cowl drape", "soft back-cowl drape", "back-cowl drape"]),
        ("Embellished Back Detail", ["embellished back detail", "embellished detailing", "embellished detail"]),
        ("Cut-Out", ["cut out neckline", "cut-out neckline", "cut out", "cut-out"]),
        ("Structured", ["structured midi", "structured silhouette", "beautifully structured", "structured"]),
        ("Soft Volume", ["soft volume"]),
        ("Clean Lines", ["clean lines"]),
        ("Corset", ["corset"]),
        ("Lace-Up Back", ["lace up back", "lace-up back"]),
        ("Bodycon", ["bodycon"]),
        ("Drop Waist", ["drop waist", "drop-waist"]),
        ("Bow", ["bow detail", "bow"]),
    ]
    for label, patterns in style_patterns:
        if any(pattern in lower_text for pattern in patterns) and label not in style_parts:
            style_parts.append(label)

    if style_parts:
        style = " / ".join(style_parts[:4])

    if not style:
        if "with scarf" in lower_text or "scarf detail" in lower_text:
            style = "With Scarf"
        elif "scarf" in lower_text:
            style = "Scarf"
        elif "ruched" in lower_text:
            style = "Ruched"
        elif "ruching" in lower_text:
            style = "Ruching"
        elif "gathered detailing" in lower_text or "gathered detail" in lower_text:
            style = "Gathered"
        elif "draped" in lower_text:
            style = "Draped"
        elif "drape" in lower_text:
            style = "Drape"
        elif "corset" in lower_text:
            style = "Corset"
        elif "bodycon" in lower_text:
            style = "Bodycon"
        elif "cut out neckline" in lower_text or "cut-out neckline" in lower_text or "cut out" in lower_text or "cut-out" in lower_text:
            style = "Cut-Out"
        elif "column silhouette" in lower_text:
            style = "Column Silhouette"
        elif "structured" in lower_text:
            style = "Structured"
        elif "soft volume" in lower_text:
            style = "Soft Volume"
        elif "centre back split" in lower_text or "center back split" in lower_text or "centre-back split" in lower_text or "center-back split" in lower_text:
            style = "Centre Back Split"
        elif "drop waist" in lower_text:
            style = "Drop Waist"
        elif "bow detail" in lower_text:
            style = "Bow"

    if not neckline:
        if (
            "round neckline" in lower_text
            or "round neck" in lower_text
            or "round neck maxi" in lower_text
            or "round-neck" in lower_text
        ):
            neckline = "Round Neck"
        elif (
            "wide neckline" in lower_text
            or "wide neck" in lower_text
            or "wide-neck" in lower_text
        ):
            neckline = "Wide Neck"
        elif "cut out neckline" in lower_text or "cut-out neckline" in lower_text or "cut out neck" in lower_text or "cut-out neck" in lower_text:
            neckline = "Cut-Out Neckline"
        elif "sweetheart neckline" in lower_text or "sweetheart neck" in lower_text:
            neckline = "Sweetheart"
        elif "short sleeves" in lower_text or "short sleeve" in lower_text:
            neckline = "Short Sleeve"
        elif "sleeveless" in lower_text:
            neckline = "Sleeveless"
        elif "fine shoulder straps" in lower_text or "shoulder straps" in lower_text:
            neckline = "Fine Shoulder Straps"
        elif "underwired cups" in lower_text or "underwire cups" in lower_text:
            neckline = "Underwired Cups"
        elif "halter neckline" in lower_text or "halter neck" in lower_text:
            neckline = "Halter Neck"
        elif "square neckline" in lower_text or "square neck" in lower_text:
            neckline = "Square Neck"
        elif "scoop neckline" in lower_text or "scoop neck" in lower_text:
            neckline = "Scoop Neck"
        elif "crew neckline" in lower_text or "crew neck" in lower_text:
            neckline = "Crew Neck"
        elif "slashed neckline" in lower_text or "slashed neck" in lower_text:
            neckline = "Slashed Neckline"

    local_attrs = {
        "fabric_name": fabric,
        "aesthetic_tag": style,
        "length": length,
        "neckline": neckline,
    }

    try:
        from utils.attribute_extractor import extract_attributes

        source = dict(product)
        source.update(
            {
                "product_name": product_name,
                "tags": tags,
                "_site": "Club L London",
            }
        )
        common_attrs = extract_attributes(source, default_floor_length=False)
        if isinstance(common_attrs, dict):
            # Club L 本地规则更贴合商品详情文案，优先保留本地解析结果；
            # 公共解析器只做兜底，避免把 Wide Neck / Cut-Out Neckline / Sash Detail 等细粒度信息覆盖掉。
            return {
                "fabric_name": local_attrs["fabric_name"] or common_attrs.get("fabric_name", ""),
                "aesthetic_tag": local_attrs["aesthetic_tag"] or common_attrs.get("aesthetic_tag", ""),
                "length": local_attrs["length"] or common_attrs.get("length", ""),
                "neckline": local_attrs["neckline"] or common_attrs.get("neckline", ""),
            }
    except Exception:
        # 公共解析器是增强项，不允许影响 Club L 主流程。
        pass

    return local_attrs


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


def _is_non_dress_product(product: dict[str, Any]) -> bool:
    title = _safe_str(product.get("title")).lower()
    handle = _safe_str(product.get("handle")).lower()
    product_type = _safe_str(product.get("product_type")).lower()
    tags = " ".join(_get_tags(product)).lower()

    text = f"{title} {handle} {product_type} {tags}"

    exclude_keywords = [
        "gift card", "swatch", "sample", "shoe", "heels", "bag", "clutch",
        "earring", "necklace", "bracelet", "accessory", "accessories",
        "lingerie", "shapewear", "bikini", "swimsuit",
    ]

    return any(keyword in text for keyword in exclude_keywords)


def _looks_like_foreign_localized_handle(handle: str) -> bool:
    """
    排除多语言本地化 URL。
    例如：
    - robe-longue / decollete / fronces：法语
    - vestido-largo / asimetrico：西语
    - maxikleid / blassrosa：德语
    """
    handle = _safe_str(handle).lower()

    foreign_keywords = [
        "robe-", "jupe-", "haut-", "longue", "decollete", "fronces",
        "asymetrique", "citron", "marron", "rose-pale", "dos-nu",
        "vestido", "largo", "entallado", "asim-trico", "asimetrico",
        "color-", "azul", "cielo",
        "maxikleid", "kleid", "blassrosa", "hohem-ausschnitt", "raffung",
        "ausschnitt", "mit-",
    ]

    return any(word in handle for word in foreign_keywords)


def _style_prefix_from_handle(handle: str) -> str:
    handle = _safe_str(handle).lower()
    if not handle:
        return ""
    return handle.split("-", 1)[0]


def _strip_style_and_color_from_handle(handle: str) -> tuple[str, str, str]:
    """
    将 handle 拆成：款式前缀、颜色 slug、颜色后的商品描述尾巴。

    例：
    luscious-light-pink-high-neck-maxi-dress-with-drop-waist-and-bow-detail-cl136467081
    -> (luscious, light-pink, high-neck-maxi-dress-with-drop-waist-and-bow-detail-cl136467081)
    """
    handle = _safe_str(handle).lower().strip("/")
    prefix = _style_prefix_from_handle(handle)

    if not prefix:
        return "", "", ""

    rest = handle[len(prefix):].lstrip("-")
    if not rest:
        return prefix, "", ""

    for color_slug in _get_color_slugs():
        if rest == color_slug:
            return prefix, color_slug, ""
        if rest.startswith(color_slug + "-"):
            return prefix, color_slug, rest[len(color_slug):].lstrip("-")

    return prefix, "", rest


def _normalize_handle_tail_for_style_match(tail: str) -> str:
    tail = _safe_str(tail).lower().strip("-")
    # 同款不同颜色通常只有末尾商品编码不同，例如 cl136467081 / cl136467013。
    # 比较版型主体时需要去掉这个尾码。
    tail = re.sub(r"-cl\d+$", "", tail)
    tail = re.sub(r"-\d{6,}$", "", tail)
    return tail.strip("-")




def _split_style_color_name(title: str, handle: str) -> tuple[str, str, str]:
    title = _clean_text(title)
    handle = _safe_str(handle)

    if not title:
        return "", "", "Default"

    style_label = ""
    rest = title

    if "|" in title:
        left, right = [part.strip() for part in title.split("|", 1)]
        style_label = left
        rest = right
    else:
        handle_first = handle.split("-", 1)[0].strip().lower() if handle else ""
        first_word = title.split(" ", 1)[0].strip()

        if handle_first and first_word.lower() == handle_first:
            style_label = first_word
            rest = title.split(" ", 1)[1].strip() if " " in title else ""

    color_name = "Default"
    product_name = rest

    for color in sorted(COLOR_KEYWORDS, key=len, reverse=True):
        if rest.lower().startswith(color.lower() + " "):
            color_name = color
            product_name = rest[len(color):].strip()
            break

    if color_name == "Default":
        match = re.match(r"^(.*?)\s+-\s+(.*?)$", rest)
        if match:
            product_name = match.group(1).strip()
            color_name = match.group(2).strip()

    if color_name == "Default":
        for color in sorted(COLOR_KEYWORDS, key=len, reverse=True):
            pattern = rf"^(.*?)\s+in\s+{re.escape(color)}$"
            match = re.match(pattern, rest, flags=re.IGNORECASE)
            if match:
                product_name = match.group(1).strip()
                color_name = color
                break

    if color_name == "Default":
        handle_slug = handle.lower()
        for color in sorted(COLOR_KEYWORDS, key=len, reverse=True):
            color_slug = _slugify(color)
            if handle_slug.endswith(f"-{color_slug}"):
                color_name = color
                break

    return style_label, product_name, color_name


def _extract_variant_color(variant: dict[str, Any]) -> str:
    candidates: list[str] = []

    selected_options = variant.get("selectedOptions") or variant.get("selected_options") or []
    if isinstance(selected_options, list):
        for option in selected_options:
            if not isinstance(option, dict):
                continue

            name = _safe_str(option.get("name")).lower()
            value = _safe_str(option.get("value"))

            if name in {"color", "colour"} and value:
                candidates.append(value)

    for key in ["option1", "option2", "option3", "title", "name"]:
        value = _safe_str(variant.get(key))
        if value:
            candidates.extend(re.split(r"\s*/\s*|\s+-\s+", value))

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




def _extract_variant_size(variant: dict[str, Any]) -> str:
    """Extract size from Shopify variant data.

    CL 的每个 handle 基本已经是一个颜色 SKC，variants 主要代表尺码。
    这里只从 selectedOptions / option 字段里识别尺码，不从商品标题或颜色里猜。
    """
    selected_options = variant.get("selectedOptions") or variant.get("selected_options") or []
    if isinstance(selected_options, list):
        for option in selected_options:
            if not isinstance(option, dict):
                continue
            name = _safe_str(option.get("name")).lower()
            value = _clean_text(option.get("value"))
            if value and name in {"size", "sizes", "uk size", "us size"}:
                return value

    candidates: list[str] = []
    for key in ["option1", "option2", "option3", "title", "name"]:
        value = _safe_str(variant.get(key))
        if value:
            candidates.extend(re.split(r"\s*/\s*|\s+-\s+", value))

    for value in candidates:
        value = _clean_text(value)
        lower_value = value.lower()
        if not value:
            continue
        if lower_value in SIZE_VALUES:
            return value
        if re.fullmatch(r"(?:uk|us)?\s*\d+", lower_value):
            return value

    return ""


def _variant_has_reliable_size_data(variants: list[dict[str, Any]]) -> bool:
    for variant in variants or []:
        if not isinstance(variant, dict):
            continue
        if _extract_variant_size(variant):
            return True
    return False


def _variant_has_reliable_availability_data(variants: list[dict[str, Any]]) -> bool:
    for variant in variants or []:
        if not isinstance(variant, dict):
            continue
        if "available" in variant or "availableForSale" in variant:
            return True
    return False


def _format_sizes_for_variants(variants: list[dict[str, Any]]) -> str:
    """Return available sizes for current SKC.

    - 有可售尺码：输出 "UK 6 / UK 8 / ..."；
    - 明确拿到尺码/可售状态但全部不可售：输出 "无码"；
    - 没拿到可靠 variants/尺码数据：输出 "未获取"。
    """
    if not isinstance(variants, list) or not variants:
        return "未获取"

    has_size_data = _variant_has_reliable_size_data(variants)
    has_availability_data = _variant_has_reliable_availability_data(variants)

    if not has_size_data:
        return "未获取"

    available_sizes: list[str] = []
    all_sizes: list[str] = []
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        size = _extract_variant_size(variant)
        if not size:
            continue
        if size not in all_sizes:
            all_sizes.append(size)
        if bool(variant.get("available", variant.get("availableForSale", False))) and size not in available_sizes:
            available_sizes.append(size)

    if available_sizes:
        return " / ".join(available_sizes)

    if all_sizes and has_availability_data:
        return "无码"

    return "未获取"


def _stock_type_from_variants(variants: list[dict[str, Any]]) -> str:
    if not isinstance(variants, list) or not variants:
        return "未知"
    if not _variant_has_reliable_availability_data(variants):
        return "未知"
    return "现货" if any(bool(v.get("available", v.get("availableForSale", False))) for v in variants if isinstance(v, dict)) else "缺货"


def _get_variant_image(product: dict[str, Any], variant: dict[str, Any]) -> str:
    featured_image = variant.get("featured_image")
    if isinstance(featured_image, dict):
        src = featured_image.get("src") or featured_image.get("url")
        if src:
            return _normalize_image_url(src)

    image = variant.get("image")
    if isinstance(image, dict):
        src = image.get("src") or image.get("url")
        if src:
            return _normalize_image_url(src)

    images = product.get("images", []) or []
    variant_id = variant.get("id")
    image_id = variant.get("image_id") or variant.get("featured_image_id")

    if image_id:
        for image_item in images:
            if isinstance(image_item, dict) and image_item.get("id") == image_id:
                return _normalize_image_url(image_item.get("src") or image_item.get("url"))

    if variant_id:
        for image_item in images:
            if not isinstance(image_item, dict):
                continue
            variant_ids = image_item.get("variant_ids", []) or []
            if variant_id in variant_ids:
                return _normalize_image_url(image_item.get("src") or image_item.get("url"))

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


def _make_session(config: Config) -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS_HTML)

    proxy_url = getattr(config, "proxy_url", None)
    if proxy_url:
        session.proxies = {"http": proxy_url, "https": proxy_url}
        logger.info("已配置 HTTP 代理: %s", proxy_url)

    token = os.getenv("CL_STOREFRONT_TOKEN", "").strip()
    if token:
        session.headers.update({"X-Shopify-Storefront-Access-Token": token})

    return session


def _post_graphql_raw(
    session: requests.Session,
    graphql_url: str,
    payload: dict[str, Any],
    timeout: int,
    retries: int = 2,
    *,
    raise_retryable: bool = False,
) -> tuple[int, dict[str, Any] | None, str]:
    headers = dict(HEADERS_GRAPHQL)

    token = os.getenv("CL_STOREFRONT_TOKEN", "").strip()
    if token:
        headers["X-Shopify-Storefront-Access-Token"] = token

    last_status = 0
    last_text = ""

    for attempt in range(retries + 1):
        try:
            response = session.post(
                graphql_url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )

            last_status = response.status_code
            last_text = response.text[:1200]

            if response.status_code == 200:
                try:
                    data = response.json()
                except ValueError:
                    logger.warning("Club L GraphQL JSON 解析失败: %s", response.text[:300])
                    return response.status_code, None, response.text

                return response.status_code, data if isinstance(data, dict) else None, response.text

            if response.status_code == 429:
                sleep_seconds = int(
                    response.headers.get("Retry-After")
                    or os.getenv("CL_GRAPHQL_429_SLEEP_SECONDS", "8")
                )
                logger.warning("Club L GraphQL 429，等待 %s 秒后重试", sleep_seconds)

                if attempt < retries:
                    time.sleep(sleep_seconds)
                    continue

                return response.status_code, None, response.text

            logger.warning(
                "Club L GraphQL 请求失败: status=%s text=%s",
                response.status_code,
                response.text[:500],
            )
            if response.status_code in {403, 404, 410}:
                return response.status_code, None, response.text
            if raise_retryable:
                classify_http_status(response.status_code, graphql_url)
            return response.status_code, None, response.text

        except requests.RequestException as exc:
            if raise_retryable and is_retryable_exception(exc):
                raise RetryableTaskError(f"Club L GraphQL retryable error url={graphql_url}: {exc}") from exc
            logger.warning("Club L GraphQL 请求异常: %s", exc)
            last_text = str(exc)

        if attempt < retries:
            time.sleep(0.8 * (attempt + 1))

    return last_status, None, last_text


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

            if response.status_code == 429:
                sleep_seconds = int(
                    response.headers.get("Retry-After")
                    or os.getenv("CL_429_SLEEP_SECONDS", "8")
                )
                logger.warning("JSON GET 触发 429，等待 %s 秒后重试: %s", sleep_seconds, response.url)

                if attempt < retries:
                    time.sleep(sleep_seconds)
                    continue

                return None

            # product.js 在 Club L 上不是稳定接口：很多正常商品页的 .js 会返回 404。
            # 这里把 404/410 作为“该辅助接口不可用”处理，避免刷 warning 和误进重试队列。
            if response.status_code in {404, 410}:
                logger.info("JSON GET 辅助接口不可用: status=%s url=%s", response.status_code, response.url)
                return None

            logger.warning("JSON GET 失败: status=%s url=%s", response.status_code, response.url)

            if response.status_code in {403}:
                return None

            if raise_retryable:
                classify_http_status(response.status_code, response.url)

        except requests.RequestException as exc:
            if raise_retryable and is_retryable_exception(exc):
                raise RetryableTaskError(f"Club L JSON GET retryable error url={url}: {exc}") from exc
            logger.warning("JSON GET 异常: %s | url=%s", exc, url)

        if attempt < retries:
            time.sleep(0.8 * (attempt + 1))

    return None


def _fetch_html(
    session: requests.Session,
    base_url: str,
    path_or_url: str,
    timeout: int,
    *,
    raise_retryable: bool = False,
) -> str:
    if path_or_url.startswith("http"):
        url = path_or_url
    else:
        url = urljoin(base_url, path_or_url)

    retries = max(0, _env_int("CL_HTML_RETRIES", 3))
    # 404 在 Club L 上经常是“假 404”，但如果每个 404 都重试 7-8 次，会导致后续兜底阶段非常慢。
    # 因此单独控制 404 重试次数，默认最多重试 2 次；503/429 仍按 CL_HTML_RETRIES 处理。
    html_404_retries = max(0, _env_int("CL_HTML_404_RETRIES", 2))
    base_sleep = max(0.0, _env_float("CL_HTML_RETRY_BASE_SLEEP_SECONDS", 2.5))
    jitter = max(0.0, _env_float("CL_HTML_RETRY_JITTER_SECONDS", 1.0))
    # Club L 商品 HTML 偶发 503 通常是服务端限流/风控，不要立刻丢进 retry queue 形成二次冲击。
    raise_after_exhausted = _env_bool("CL_HTML_RAISE_RETRYABLE_AFTER_EXHAUSTED", False)

    for attempt in range(retries + 1):
        try:
            _throttle_cl_html_request()
            html_headers = dict(HEADERS_HTML)
            html_headers["Referer"] = base_url.rstrip("/") + "/collections/bridesmaids"
            response = session.get(url, headers=html_headers, timeout=timeout)
            status_code = response.status_code

            if status_code == 200:
                return response.text

            if status_code == 429:
                sleep_seconds = float(
                    response.headers.get("Retry-After")
                    or os.getenv("CL_HTML_429_SLEEP_SECONDS", "20")
                )
                logger.warning("Club L HTML 触发 429，等待 %.1f 秒后重试: %s", sleep_seconds, url)
                if attempt < retries:
                    time.sleep(sleep_seconds + random.uniform(0, jitter))
                    continue
                if raise_retryable and raise_after_exhausted:
                    classify_http_status(status_code, url)
                return ""

            if status_code in {403, 404, 408, 500, 502, 503, 504, 520, 521, 522, 523, 524}:
                effective_retries = html_404_retries if status_code == 404 else retries
                if status_code == 404:
                    # Club L 会对脚本请求返回“假 404”：浏览器可打开，但 requests 暂时拿到 404。
                    # 但 404 重试成本不能太高，否则颜色扩展完成后还会被 HTML 兜底拖住。
                    sleep_seconds = max(0.0, _env_float("CL_HTML_404_SLEEP_SECONDS", 8.0))
                elif status_code == 403:
                    sleep_seconds = max(base_sleep * (2 ** attempt), 15.0)
                elif status_code == 503:
                    sleep_seconds = max(
                        base_sleep * (2 ** attempt),
                        max(0.0, _env_float("CL_HTML_503_SLEEP_SECONDS", 30.0)),
                    )
                else:
                    sleep_seconds = base_sleep * (2 ** attempt)

                logger.warning(
                    "Club L HTML 临时不可用: %s status=%s attempt=%s/%s wait=%.1fs",
                    url,
                    status_code,
                    attempt + 1,
                    effective_retries + 1,
                    sleep_seconds,
                )
                if attempt < effective_retries:
                    time.sleep(sleep_seconds + random.uniform(0, jitter))
                    continue
                if raise_retryable and raise_after_exhausted and status_code != 404:
                    classify_http_status(status_code, url)
                logger.warning("Club L HTML 多次重试仍失败，按软失败处理，不作为下架依据: %s status=%s", url, status_code)
                _remember_cl_html_soft_failed_handle(url, status_code)
                return ""

            logger.warning("Club L HTML 请求失败: %s status=%s", url, status_code)
            if status_code == 410:
                return ""
            if raise_retryable and raise_after_exhausted:
                classify_http_status(status_code, url)
            return ""

        except Exception as exc:
            logger.warning("Club L HTML 请求异常: %s | %s", url, exc)
            if attempt < retries and is_retryable_exception(exc):
                sleep_seconds = base_sleep * (2 ** attempt)
                time.sleep(sleep_seconds + random.uniform(0, jitter))
                continue
            if raise_retryable and raise_after_exhausted and is_retryable_exception(exc):
                raise RetryableTaskError(f"Club L HTML retryable error url={url}: {exc}") from exc
            return ""

    return ""


def _money_amount(value: Any) -> float:
    if value is None:
        return 0.0

    if isinstance(value, dict):
        return _parse_price(value.get("amount") or value.get("value") or value.get("price"))

    return _parse_price(value)


CL_COLLECTION_LIST_QUERY = """
query getCollectionByHandle($handle: String!, $first: Int = 250, $after: String) {
  collectionByHandle(handle: $handle) {
    id
    title
    description
    products(first: $first, after: $after) {
      edges {
        cursor
        node {
          id
          title
          handle
        }
      }
      pageInfo {
        endCursor
        hasNextPage
      }
    }
  }
}
"""




def _build_product_details_query(product_ids: list[str], country: str) -> str:
    fragment = """
fragment ProductData on Product {
  id
  title
  handle
  vendor
  productType
  description
  descriptionHtml
  tags
  availableForSale
  featuredImage {
    url
  }
  priceRange {
    maxVariantPrice {
      amount
      currencyCode
    }
    minVariantPrice {
      amount
      currencyCode
    }
  }
  compareAtPriceRange {
    maxVariantPrice {
      amount
      currencyCode
    }
    minVariantPrice {
      amount
      currencyCode
    }
  }
  variants(first: 50) {
    nodes {
      id
      title
      availableForSale
      price {
        amount
        currencyCode
      }
      compareAtPrice {
        amount
        currencyCode
      }
      image {
        url
      }
      selectedOptions {
        name
        value
      }
    }
  }
}
"""

    query_parts: list[str] = [fragment]
    query_parts.append(f"query products @inContext(country: {country}) {{")

    for product_id in product_ids:
        clean_id = _extract_numeric_id(product_id)
        if not clean_id:
            continue

        query_parts.append(
            f'''
  result_{clean_id}: product(id: "gid://shopify/Product/{clean_id}") {{
    ...ProductData
  }}
'''
        )

    query_parts.append("}")
    return "\n".join(query_parts)


def _graphql_product_to_dict(product: dict[str, Any], base_url: str) -> dict[str, Any]:
    product_id = _extract_numeric_id(product.get("id"))
    title = _safe_str(product.get("title"))
    handle = _safe_str(product.get("handle"))

    price_range = product.get("priceRange", {})
    compare_range = product.get("compareAtPriceRange", {})

    price = 0.0
    compare_price = 0.0

    if isinstance(price_range, dict):
        price = (
            _money_amount(price_range.get("minVariantPrice"))
            or _money_amount(price_range.get("maxVariantPrice"))
        )

    if isinstance(compare_range, dict):
        compare_price = (
            _money_amount(compare_range.get("maxVariantPrice"))
            or _money_amount(compare_range.get("minVariantPrice"))
        )

    image_url = ""
    featured_image = product.get("featuredImage")
    if isinstance(featured_image, dict):
        image_url = _normalize_image_url(featured_image.get("url"))

    images: list[dict[str, str]] = []
    images_block = product.get("images", {})
    if isinstance(images_block, dict):
        image_nodes = images_block.get("nodes", []) or []
        if isinstance(image_nodes, list):
            for image in image_nodes:
                if not isinstance(image, dict):
                    continue
                url = _normalize_image_url(image.get("url"))
                if url:
                    images.append({"src": url, "url": url})

    if not image_url and images:
        image_url = images[0]["src"]

    variants: list[dict[str, Any]] = []
    variants_block = product.get("variants", {})
    variant_nodes = []
    if isinstance(variants_block, dict):
        variant_nodes = variants_block.get("nodes", []) or []

    if isinstance(variant_nodes, list):
        for variant in variant_nodes:
            if not isinstance(variant, dict):
                continue

            variant_price = _money_amount(variant.get("price")) or price
            variant_compare = _money_amount(variant.get("compareAtPrice"))

            variant_image_url = ""
            variant_image = variant.get("image")
            if isinstance(variant_image, dict):
                variant_image_url = _normalize_image_url(variant_image.get("url"))

            selected_options = variant.get("selectedOptions") or []

            variants.append(
                {
                    "id": variant.get("id") or "",
                    "title": variant.get("title") or "Default Title",
                    "price": variant_price,
                    "compare_at_price": variant_compare if variant_compare > variant_price else "",
                    "available": bool(variant.get("availableForSale", True)),
                    "featured_image": {"src": variant_image_url or image_url} if (variant_image_url or image_url) else None,
                    "selectedOptions": selected_options,
                }
            )

    if not variants:
        variants = [
            {
                "id": product.get("id") or "",
                "title": "Default Title",
                "price": price,
                "compare_at_price": compare_price if compare_price > price else "",
                "available": bool(product.get("availableForSale", True)),
                "featured_image": {"src": image_url} if image_url else None,
                "selectedOptions": [],
            }
        ]

    return {
        "id": int(product_id) if product_id else "",
        "title": title,
        "handle": handle,
        "vendor": product.get("vendor") or "Club L London",
        "product_type": product.get("productType") or "",
        "tags": product.get("tags") or [],
        "body_html": product.get("descriptionHtml") or "",
        "description": product.get("description") or "",
        "variants": variants,
        "images": images,
        "image": {"src": image_url, "url": image_url} if image_url else None,
        "price": price,
        "price_min": price,
        "compare_at_price": compare_price if compare_price > price else "",
        "compare_at_price_max": compare_price if compare_price > price else "",
        "available": bool(product.get("availableForSale", True)),
        "_source_base_url": base_url,
    }


def _fetch_product_details_graphql_batch(
    session: requests.Session,
    graphql_url: str,
    product_ids: list[str],
    base_url: str,
    timeout: int,
    *,
    raise_retryable: bool = False,
) -> dict[str, dict[str, Any]] | None:
    clean_ids: list[str] = []
    seen: set[str] = set()

    for product_id in product_ids:
        clean_id = _extract_numeric_id(product_id)
        if clean_id and clean_id not in seen:
            seen.add(clean_id)
            clean_ids.append(clean_id)

    if not clean_ids:
        return {}

    country = os.getenv("CL_GRAPHQL_COUNTRY", "GB").strip().upper() or "GB"
    query = _build_product_details_query(clean_ids, country)
    payload = {"query": query}

    status, data, text = _post_graphql_raw(
        session=session,
        graphql_url=graphql_url,
        payload=payload,
        timeout=timeout,
        retries=1,
        raise_retryable=raise_retryable,
    )

    if status == 429 and ("MAX_COMPLEXITY_EXCEEDED" in text or "Complexity exceeded" in text):
        return None

    if data and data.get("errors"):
        errors_text = json.dumps(data.get("errors"), ensure_ascii=False)
        if "MAX_COMPLEXITY_EXCEEDED" in errors_text or "Complexity exceeded" in errors_text:
            return None
        logger.warning("Club L GraphQL 商品详情 errors: %s", data.get("errors"))

    if not data:
        return {}

    data_block = data.get("data", {})
    if not isinstance(data_block, dict):
        return {}

    result: dict[str, dict[str, Any]] = {}

    for product_id in clean_ids:
        product = data_block.get(f"result_{product_id}")
        if isinstance(product, dict):
            normalized = _graphql_product_to_dict(product, base_url)
            handle = _safe_str(normalized.get("handle"))
            if handle:
                result[handle] = normalized

    return result


def _fetch_product_details_graphql_all(
    session: requests.Session,
    graphql_url: str,
    product_refs: list[dict[str, str]],
    base_url: str,
    timeout: int,
) -> dict[str, dict[str, Any]]:
    product_ids = [
        _extract_numeric_id(ref.get("id"))
        for ref in product_refs
        if _extract_numeric_id(ref.get("id"))
    ]

    batch_size = int(os.getenv("CL_GRAPHQL_PRODUCT_BATCH_SIZE", "15"))
    min_batch_size = int(os.getenv("CL_GRAPHQL_MIN_BATCH_SIZE", "5"))

    result: dict[str, dict[str, Any]] = {}

    logger.info(
        "开始 Club L GraphQL 批量补商品详情：product_ids=%s batch_size=%s",
        len(product_ids),
        batch_size,
    )

    def fetch_range(ids: list[str]) -> dict[str, dict[str, Any]]:
        if not ids:
            return {}

        batch_result = _fetch_product_details_graphql_batch(
            session=session,
            graphql_url=graphql_url,
            product_ids=ids,
            base_url=base_url,
            timeout=timeout,
        )

        if batch_result is not None:
            return batch_result

        if len(ids) <= min_batch_size:
            logger.warning("Club L GraphQL batch 已降到最小仍超复杂度，跳过 ids=%s", ids)
            return {}

        mid = len(ids) // 2
        logger.warning(
            "Club L GraphQL batch complexity exceeded，自动拆分：%s -> %s + %s",
            len(ids),
            mid,
            len(ids) - mid,
        )

        left = fetch_range(ids[:mid])
        time.sleep(float(os.getenv("CL_GRAPHQL_BATCH_SLEEP_SECONDS", "0.5")))
        right = fetch_range(ids[mid:])

        merged: dict[str, dict[str, Any]] = {}
        merged.update(left)
        merged.update(right)
        return merged

    for i in range(0, len(product_ids), batch_size):
        batch = product_ids[i:i + batch_size]
        batch_result = fetch_range(batch)

        result.update(batch_result)

        logger.info(
            "Club L GraphQL 商品详情 batch %s-%s 返回=%s 累计=%s",
            i + 1,
            i + len(batch),
            len(batch_result),
            len(result),
        )

        time.sleep(float(os.getenv("CL_GRAPHQL_BATCH_SLEEP_SECONDS", "0.5")))

    return result



def _normalize_handle(value: Any) -> str:
    """统一清洗 Club L / Shopify product handle。

    兼容以下输入：
    - 纯 handle: abc-def-cl123
    - 商品 URL: https://clubllondon.com/products/abc-def-cl123?variant=xxx
    - 路径: /products/abc-def-cl123
    - 误带后缀: abc-def-cl123.js / abc-def-cl123.json

    返回空字符串表示不是有效 product handle。
    """
    raw = unescape(_safe_str(value)).strip()
    if not raw:
        return ""

    # 如果是完整 URL，优先从 path 中取 /products/{handle}
    if raw.startswith("http://") or raw.startswith("https://"):
        try:
            parsed = urlparse(raw)
            raw = parsed.path or ""
        except Exception:
            return ""

    # 支持传入 /products/{handle} 或 products/{handle}
    if "/products/" in raw:
        raw = raw.split("/products/", 1)[1]
    elif raw.startswith("products/"):
        raw = raw.split("products/", 1)[1]

    raw = raw.split("?", 1)[0].split("#", 1)[0].strip().strip("/")
    if not raw:
        return ""

    lower = raw.lower()

    # 过滤非商品 handle 或接口后缀
    for suffix in (".js", ".json", ".oembed"):
        if lower.endswith(suffix):
            lower = lower[: -len(suffix)]
            break

    lower = lower.strip().strip("/")
    if not lower:
        return ""

    # 过滤明显不是 handle 的内容
    if lower.startswith("gid://") or lower.startswith("shopify/"):
        return ""
    if "/" in lower or "?" in lower or "#" in lower:
        return ""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*[a-z0-9]", lower):
        return ""

    return lower

def _graphql_string(value: str) -> str:
    """生成安全的 GraphQL 字符串字面量。"""
    return json.dumps(_safe_str(value), ensure_ascii=False)


def _build_product_details_by_handle_query(handles: list[str], country: str) -> tuple[str, dict[str, str]]:
    fragment = """
fragment ProductData on Product {
  id
  title
  handle
  vendor
  productType
  description
  descriptionHtml
  tags
  availableForSale
  featuredImage {
    url
  }
  priceRange {
    maxVariantPrice {
      amount
      currencyCode
    }
    minVariantPrice {
      amount
      currencyCode
    }
  }
  compareAtPriceRange {
    maxVariantPrice {
      amount
      currencyCode
    }
    minVariantPrice {
      amount
      currencyCode
    }
  }
  variants(first: 50) {
    nodes {
      id
      title
      availableForSale
      price {
        amount
        currencyCode
      }
      compareAtPrice {
        amount
        currencyCode
      }
      image {
        url
      }
      selectedOptions {
        name
        value
      }
    }
  }
}
"""

    alias_to_handle: dict[str, str] = {}
    query_parts: list[str] = [fragment, f"query productsByHandle @inContext(country: {country}) {{"]

    for idx, handle in enumerate(handles):
        clean_handle = _normalize_handle(handle)
        if not clean_handle:
            continue
        alias = f"result_{idx}"
        alias_to_handle[alias] = clean_handle
        query_parts.append(f"  {alias}: productByHandle(handle: {_graphql_string(clean_handle)}) {{ ...ProductData }}")

    query_parts.append("}")
    return "\n".join(query_parts), alias_to_handle


def _fetch_product_details_graphql_by_handles_batch(
    session: requests.Session,
    graphql_url: str,
    handles: list[str],
    base_url: str,
    timeout: int,
    *,
    raise_retryable: bool = False,
) -> dict[str, dict[str, Any]] | None:
    clean_handles: list[str] = []
    seen: set[str] = set()

    for handle in handles:
        clean_handle = _normalize_handle(handle)
        if not clean_handle or _looks_like_foreign_localized_handle(clean_handle):
            continue
        if clean_handle in seen:
            continue
        seen.add(clean_handle)
        clean_handles.append(clean_handle)

    if not clean_handles:
        return {}

    country = os.getenv("CL_GRAPHQL_COUNTRY", "GB").strip().upper() or "GB"
    query, alias_to_handle = _build_product_details_by_handle_query(clean_handles, country)
    payload = {"query": query}

    status, data, text = _post_graphql_raw(
        session=session,
        graphql_url=graphql_url,
        payload=payload,
        timeout=timeout,
        retries=1,
        raise_retryable=raise_retryable,
    )

    if status == 429 and ("MAX_COMPLEXITY_EXCEEDED" in text or "Complexity exceeded" in text):
        return None

    if data and data.get("errors"):
        errors_text = json.dumps(data.get("errors"), ensure_ascii=False)
        if "MAX_COMPLEXITY_EXCEEDED" in errors_text or "Complexity exceeded" in errors_text:
            return None
        logger.warning("Club L GraphQL handle详情 errors: %s", data.get("errors"))

    if not data:
        return {}

    data_block = data.get("data", {})
    if not isinstance(data_block, dict):
        return {}

    result: dict[str, dict[str, Any]] = {}
    for alias, original_handle in alias_to_handle.items():
        product = data_block.get(alias)
        if isinstance(product, dict):
            normalized = _graphql_product_to_dict(product, base_url)
            handle = _safe_str(normalized.get("handle")) or original_handle
            if handle:
                result[handle] = normalized

    return result


def _fetch_product_details_graphql_by_handles(
    session: requests.Session,
    graphql_url: str,
    handles: list[str],
    base_url: str,
    timeout: int,
) -> dict[str, dict[str, Any]]:
    clean_handles: list[str] = []
    seen: set[str] = set()
    for handle in handles:
        clean_handle = _normalize_handle(handle)
        if not clean_handle or _looks_like_foreign_localized_handle(clean_handle):
            continue
        if clean_handle in seen:
            continue
        seen.add(clean_handle)
        clean_handles.append(clean_handle)

    # 只按页面白名单 handle 批量补详情。控制单批大小，避免 Shopify Storefront GraphQL complexity exceeded。
    configured_batch_size = _env_int("CL_GRAPHQL_HANDLE_BATCH_SIZE", 12)
    batch_size = max(1, min(configured_batch_size, 15))
    configured_min_batch_size = _env_int("CL_GRAPHQL_HANDLE_MIN_BATCH_SIZE", 1)
    min_batch_size = max(1, min(configured_min_batch_size, batch_size))
    sleep_seconds = max(0.0, min(_env_float("CL_GRAPHQL_HANDLE_BATCH_SLEEP_SECONDS", 0.2), 1.0))

    result: dict[str, dict[str, Any]] = {}
    logger.info("开始 Club L GraphQL 按 handle 补详情：handles=%s batch_size=%s", len(clean_handles), batch_size)

    def fetch_range(batch_handles: list[str]) -> dict[str, dict[str, Any]]:
        if not batch_handles:
            return {}

        batch_result = _fetch_product_details_graphql_by_handles_batch(
            session=session,
            graphql_url=graphql_url,
            handles=batch_handles,
            base_url=base_url,
            timeout=timeout,
        )

        if batch_result is not None:
            return batch_result

        if len(batch_handles) <= min_batch_size:
            logger.warning("Club L GraphQL handle batch 已降到最小仍超复杂度，跳过 handles=%s", batch_handles)
            return {}

        mid = len(batch_handles) // 2
        logger.warning(
            "Club L GraphQL handle batch complexity exceeded，自动拆分：%s -> %s + %s",
            len(batch_handles),
            mid,
            len(batch_handles) - mid,
        )
        left = fetch_range(batch_handles[:mid])
        time.sleep(sleep_seconds)
        right = fetch_range(batch_handles[mid:])
        merged: dict[str, dict[str, Any]] = {}
        merged.update(left)
        merged.update(right)
        return merged

    for i in range(0, len(clean_handles), batch_size):
        batch = clean_handles[i:i + batch_size]
        batch_result = fetch_range(batch)
        result.update(batch_result)
        logger.info(
            "Club L GraphQL handle详情 batch %s-%s 返回=%s 累计=%s",
            i + 1,
            i + len(batch),
            len(batch_result),
            len(result),
        )
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    return result


def _normalize_host(host: str) -> str:
    host = _safe_str(host).lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _extract_same_origin_product_handle(href: str, base_url: str) -> str:
    """
    从 href 中提取当前站点同域名的 product handle。

    重要：商品页会同时出现 .fr / .ie / .us 等 alternate 链接。
    这些链接的 handle 不能拿到 .com 域名下请求 product.js，否则会产生大量 404。
    """
    href = unescape(_safe_str(href))
    if not href or "/products/" not in href:
        return ""

    lower_href = href.lower().strip()
    if lower_href.startswith(("javascript:", "mailto:", "tel:", "#")):
        return ""

    base_parsed = urlparse(base_url)
    parsed = urlparse(urljoin(base_url.rstrip("/") + "/", href))

    if parsed.scheme not in {"http", "https"}:
        return ""

    base_host = _normalize_host(base_parsed.netloc)
    parsed_host = _normalize_host(parsed.netloc)

    if base_host and parsed_host and parsed_host != base_host:
        return ""

    path_and_query = parsed.path
    if parsed.query:
        path_and_query = f"{path_and_query}?{parsed.query}"

    handle = _extract_handle_from_product_url(path_and_query)
    if not handle:
        return ""

    if _looks_like_foreign_localized_handle(handle):
        return ""

    return handle


class ClubLCollectionHTMLParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.handles: list[str] = []
        self._seen_handles: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k: v for k, v in attrs}

        for key in ["href", "data-url", "data-product-url", "data-href"]:
            href = attrs_dict.get(key) or ""
            handle = _extract_same_origin_product_handle(href, self.base_url)

            if not handle:
                continue

            if handle in self._seen_handles:
                continue

            self._seen_handles.add(handle)
            self.handles.append(handle)


def _extract_cl_handles_from_any_payload(payload: Any, base_url: str) -> list[str]:
    """从 CL 前台接口响应里递归提取 product handle。

    用途：CL 列表页经常只在 DOM 中保留首批/可见商品，导致只抓到约 60 个。
    前台接口响应才是页面实际加载商品的完整来源之一。这里只提取站内 /products/{handle}
    或 product-like 对象中的 handle，不决定商品详情，只用于还原列表页商品池/顺序。
    """
    handles: list[str] = []
    seen: set[str] = set()

    def add_handle(value: Any) -> None:
        text = _safe_str(value).strip()
        if not text:
            return
        handle = ""
        if "/products/" in text or text.startswith("http"):
            handle = _extract_same_origin_product_handle(text, base_url)
        else:
            maybe = _normalize_handle(text.lower())
            # 只接受看起来像 CL 商品 handle 的字符串，避免 collection/tag 等普通文本混入。
            if maybe and ("-cl" in maybe or re.search(r"cl\d{6,}", maybe, re.I)):
                handle = maybe
        if not handle or handle in seen or _looks_like_foreign_localized_handle(handle):
            return
        seen.add(handle)
        handles.append(handle)

    def walk(obj: Any, parent_key: str = "") -> None:
        if obj is None:
            return
        if isinstance(obj, dict):
            # product-like object: 优先读 handle/url 字段。
            lower_keys = {str(k).lower() for k in obj.keys()}
            looks_product = bool(
                {"handle", "producthandle", "product_handle", "onlineStoreUrl", "url", "href", "productUrl"} & lower_keys
            ) or bool({"variants", "price", "title", "featuredImage", "images"} & lower_keys and "handle" in lower_keys)

            if looks_product:
                for key in ("handle", "productHandle", "product_handle", "onlineStoreUrl", "url", "href", "productUrl", "link"):
                    if key in obj:
                        add_handle(obj.get(key))

            # Shopify GraphQL edge/node 结构。
            node = obj.get("node")
            if isinstance(node, dict):
                walk(node, "node")

            for key, value in obj.items():
                # 避免递归大段 description/html 文本，减少误提取。
                lk = str(key).lower()
                if lk in {"description", "descriptionhtml", "body_html", "bodyhtml", "html"}:
                    continue
                walk(value, lk)
        elif isinstance(obj, list):
            for item in obj:
                walk(item, parent_key)
        elif isinstance(obj, str):
            if "/products/" in obj:
                for m in re.finditer(r"/products/([a-z0-9][a-z0-9-]*[a-z0-9])", obj, re.I):
                    add_handle(m.group(1))

    walk(payload)
    return handles

def _fetch_collection_product_refs_graphql_collection(
    session: requests.Session,
    graphql_url: str,
    collection_handle: str,
    timeout: int,
) -> list[dict[str, str]]:
    """使用 Shopify collection GraphQL 读取完整 collection 商品列表。

    只在前台渲染/接口监听拿到的数量明显不完整时兜底，解决 CL DOM 虚拟列表只保留
    首批约 60 个商品的问题。该函数只返回 collection 内商品，不参与详情扩展。
    """
    refs: list[dict[str, str]] = []
    seen: set[str] = set()
    after: str | None = None

    while True:
        variables = {"handle": collection_handle, "first": 250, "after": after}
        data = _graphql_post(session, graphql_url, CL_COLLECTION_LIST_QUERY, variables, timeout=timeout)
        collection = (data or {}).get("data", {}).get("collectionByHandle") or {}
        products = collection.get("products") or {}
        edges = products.get("edges") or []
        for edge in edges:
            node = (edge or {}).get("node") or {}
            handle = _normalize_handle(node.get("handle"))
            if not handle or handle in seen or _looks_like_foreign_localized_handle(handle):
                continue
            seen.add(handle)
            refs.append({
                "id": _extract_numeric_id(node.get("id")) or "",
                "gid": _safe_str(node.get("id")),
                "title": _safe_str(node.get("title")),
                "handle": handle,
                "_collection_page": "graphql_collection_fallback",
            })

        page_info = products.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        after = page_info.get("endCursor")
        if not after:
            break

    logger.info("Club L collection GraphQL 完整商品列表读取完成：refs=%s", len(refs))
    return refs




def _fetch_collection_product_refs_rendered_page(
    base_url: str,
    collection_handle: str,
    timeout: int,
) -> list[dict[str, str]]:
    """按 Club L 前台分页真实顺序读取商品池。

    最终口径与 Babyboo 一致：
    - 页面只负责确认商品池和排序；
    - 这里不使用 Shopify collection GraphQL 补商品池；
    - 逐页读取当前页面商品卡片，点击 View Next / Next 后继续读取下一页；
    - GraphQL 只在后续按白名单 handle 补详情、价格、variants/尺码。
    """
    if os.getenv("CL_DISABLE_RENDERED_PAGE_ORDER", "false").strip().lower() in {"1", "true", "yes", "y"}:
        logger.error("CL_DISABLE_RENDERED_PAGE_ORDER 已开启；为避免错误排序，不再降级使用 GraphQL 排序。")
        return []

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        logger.error("未安装 playwright，无法读取 CL 前台分页真实排序: %s", exc)
        return []

    page_url = f"{base_url.rstrip('/')}/collections/{collection_handle}"
    wait_ms = max(1000, _env_int("CL_RENDER_WAIT_MS", 4000))
    page_wait_ms = max(800, _env_int("CL_PAGE_CHANGE_WAIT_MS", 2500))
    max_pages = max(1, _env_int("CL_MAX_FRONTEND_PAGES", 20))
    expected_count = max(0, _env_int("CL_EXPECTED_PRODUCT_COUNT", 0))
    expected_last_handle = _normalize_handle(os.getenv("CL_EXPECTED_LAST_HANDLE", ""))
    no_new_page_limit = max(1, _env_int("CL_NO_NEW_PAGE_LIMIT", 2))

    js_extract_current_page = r"""
() => {
  const normalize = (href) => {
    try {
      const url = new URL(href, window.location.origin);
      if (url.origin !== window.location.origin) return '';
      const marker = '/products/';
      if (!url.pathname.includes(marker)) return '';
      let handle = url.pathname.split(marker)[1] || '';
      handle = handle.split('/')[0].split('?')[0].split('#')[0].trim().toLowerCase();
      if (!handle || handle.endsWith('.js') || handle.endsWith('.json') || handle.endsWith('.oembed')) return '';
      if (!/^[a-z0-9][a-z0-9-]*[a-z0-9]$/.test(handle)) return '';
      return handle;
    } catch (e) {
      return '';
    }
  };

  const isVisible = (el) => {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
  };

  const isBadArea = (el) => !!el.closest(
    'header, footer, nav, aside, [role="dialog"], [aria-modal="true"], [class*="drawer" i], [class*="modal" i], [class*="menu" i], [class*="cart" i], [class*="recent" i], [class*="recommend" i], [class*="related" i], [class*="upsell" i]'
  );

  const gridSelectors = [
    '[data-product-grid]',
    '[data-products-grid]',
    '[data-collection-products]',
    '[data-collection-product-grid]',
    '[data-testid*="product-grid" i]',
    '[class*="product-grid" i]',
    '[class*="products-grid" i]',
    '[class*="collection-products" i]',
    '[class*="ProductGrid" i]',
    '[class*="CollectionProduct" i]',
    'main'
  ];

  const roots = [];
  for (const selector of gridSelectors) {
    for (const root of Array.from(document.querySelectorAll(selector))) {
      if (!root || isBadArea(root)) continue;
      const count = Array.from(root.querySelectorAll('a[href*="/products/"]')).filter(a => isVisible(a) && !isBadArea(a)).length;
      if (count >= 3) roots.push({root, count});
    }
  }
  roots.sort((a, b) => b.count - a.count);
  const root = roots.length ? roots[0].root : (document.querySelector('main') || document.body);

  const anchors = Array.from(root.querySelectorAll('a[href*="/products/"]'));
  const rows = [];
  const seen = new Set();

  for (const a of anchors) {
    if (!isVisible(a) || isBadArea(a)) continue;
    const handle = normalize(a.getAttribute('href') || a.href || '');
    if (!handle || seen.has(handle)) continue;

    const card = a.closest('[data-product-card], [data-testid*="product" i], [class*="product-card" i], [class*="ProductCard" i], [class*="product-item" i], [class*="grid-item" i], li, article, div');
    if (!card || isBadArea(card) || !isVisible(card)) continue;

    const hasImg = !!card.querySelector('img, picture, source');
    const cardText = (card.innerText || card.textContent || '').replace(/\s+/g, ' ').trim();
    const looksProduct = hasImg || /£\s*\d+|\$\s*\d+|size|quick add|add to bag/i.test(cardText);
    if (!looksProduct) continue;

    const rect = card.getBoundingClientRect();
    rows.push({
      handle,
      top: Math.round(rect.top + (window.scrollY || window.pageYOffset || 0)),
      left: Math.round(rect.left + (window.scrollX || window.pageXOffset || 0)),
      title: cardText.slice(0, 200)
    });
    seen.add(handle);
  }

  rows.sort((a, b) => (a.top - b.top) || (a.left - b.left));

  const bodyText = (document.body.innerText || '').replace(/\s+/g, ' ');
  let productCount = 0;
  const patterns = [
    /(\d+)\s*(?:products|items|styles|results)/i,
    /showing\s+\d+\s*-\s*\d+\s+of\s+(\d+)/i
  ];
  for (const re of patterns) {
    const m = bodyText.match(re);
    if (m && m[1]) {
      productCount = parseInt(m[1], 10) || 0;
      break;
    }
  }

  return {
    handles: rows.map(r => r.handle),
    productCount,
    rootCount: rows.length,
    url: window.location.href
  };
}
"""

    js_click_next = r"""
() => {
  const isVisible = (el) => {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
  };
  const isDisabled = (el) => {
    const aria = (el.getAttribute('aria-disabled') || '').toLowerCase();
    const cls = (el.getAttribute('class') || '').toLowerCase();
    return el.disabled || aria === 'true' || cls.includes('disabled') || cls.includes('is-disabled');
  };
  const textOf = (el) => ((el.innerText || el.textContent || '') + ' ' + (el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '') + ' ' + (el.getAttribute('rel') || '')).replace(/\s+/g, ' ').trim().toLowerCase();

  const candidates = Array.from(document.querySelectorAll('a, button, [role="button"]'));
  const scored = [];
  for (const el of candidates) {
    if (!isVisible(el) || isDisabled(el)) continue;
    const href = (el.getAttribute('href') || '').toLowerCase();
    if (href.includes('/products/')) continue;
    const text = textOf(el);
    if (!text) continue;
    if (text.includes('previous') || text.includes('prev') || text.includes('back')) continue;

    let score = 0;
    if (text.includes('view next')) score += 100;
    if (text === 'next' || text.includes(' next ') || text.endsWith(' next') || text.startsWith('next ')) score += 80;
    if (text.includes('next page')) score += 80;
    if (text.includes('load more') || text.includes('view more') || text.includes('show more')) score += 40;
    if ((el.getAttribute('rel') || '').toLowerCase() === 'next') score += 100;
    if (/page=\d+/.test(href)) score += 20;
    if (score <= 0) continue;

    const rect = el.getBoundingClientRect();
    scored.push({el, score, top: rect.top, left: rect.left, text, href});
  }
  scored.sort((a, b) => (b.score - a.score) || (b.top - a.top) || (b.left - a.left));
  if (!scored.length) return {clicked: false, reason: 'no_next'};

  const target = scored[0].el;
  try {
    target.scrollIntoView({block: 'center', inline: 'center'});
    target.click();
    return {clicked: true, text: scored[0].text, href: scored[0].href};
  } catch (e) {
    return {clicked: false, reason: String(e)};
  }
}
"""

    all_handles: list[str] = []
    seen_handles: set[str] = set()
    detected_count = 0

    def merge_current_page(state: Any) -> int:
        nonlocal detected_count
        if isinstance(state, dict) and not detected_count:
            detected_count = _safe_int(state.get("productCount"), 0) or 0
        items = state.get("handles") if isinstance(state, dict) else state
        if not isinstance(items, list):
            return 0
        added = 0
        for raw in items:
            handle = _normalize_handle(str(raw)) or str(raw).strip().lower()
            if not handle or handle in seen_handles:
                continue
            if _looks_like_foreign_localized_handle(handle):
                continue
            seen_handles.add(handle)
            all_handles.append(handle)
            added += 1
        return added

    def chromium_launch_kwargs() -> dict[str, Any]:
        configured = os.getenv("CL_CHROMIUM_EXECUTABLE_PATH", "").strip()
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
                viewport={"width": 1440, "height": 1800},
                locale="en-GB",
            )
            page = context.new_page()
            page.goto(page_url, wait_until="domcontentloaded", timeout=timeout * 1000)
            page.wait_for_timeout(wait_ms)

            for selector in (
                'button:has-text("Accept")',
                'button:has-text("YES")',
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

            no_new_pages = 0
            for page_no in range(1, max_pages + 1):
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                page.wait_for_timeout(page_wait_ms)
                state = page.evaluate(js_extract_current_page) or {}
                before_total = len(all_handles)
                added = merge_current_page(state)
                current_handles = state.get("handles") if isinstance(state, dict) else []
                current_count = len(current_handles) if isinstance(current_handles, list) else 0
                logger.info(
                    "Club L 前台分页读取: page=%s current=%s added=%s total=%s detected_count=%s url=%s",
                    page_no,
                    current_count,
                    added,
                    len(all_handles),
                    detected_count or "",
                    (state.get("url") if isinstance(state, dict) else "") or page.url,
                )

                if expected_count and len(all_handles) >= expected_count:
                    break
                if expected_last_handle and expected_last_handle in seen_handles:
                    break

                if added == 0 and page_no > 1:
                    no_new_pages += 1
                else:
                    no_new_pages = 0
                if no_new_pages >= no_new_page_limit:
                    logger.info("Club L 连续 %s 页没有新增商品，停止分页读取。", no_new_pages)
                    break

                before_url = page.url
                before_snapshot = "|".join(list(all_handles[-5:]))
                try:
                    clicked_info = page.evaluate(js_click_next) or {}
                except Exception as exc:
                    logger.info("Club L 未能点击 View Next，停止分页读取: %s", exc)
                    break

                if not isinstance(clicked_info, dict) or not clicked_info.get("clicked"):
                    logger.info("Club L 未找到可点击 View Next / Next，停止分页读取。reason=%s", clicked_info)
                    break

                try:
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
                try:
                    page.wait_for_load_state("networkidle", timeout=7000)
                except Exception:
                    pass
                page.wait_for_timeout(page_wait_ms)

                # 若点击后没有导航且页面商品也未变化，下一轮会因为 added=0 停止。
                logger.debug(
                    "Club L 已点击 View Next: text=%s href=%s before_url=%s after_url=%s before_tail=%s",
                    clicked_info.get("text"),
                    clicked_info.get("href"),
                    before_url,
                    page.url,
                    before_snapshot,
                )

            context.close()
            browser.close()
    except Exception as exc:
        logger.error("读取 CL 前台分页真实排序失败；为避免错误排序，不再降级使用 GraphQL: %s", exc)
        return []

    if expected_last_handle and expected_last_handle in all_handles:
        all_handles = all_handles[: all_handles.index(expected_last_handle) + 1]
        logger.info("Club L 已按 CL_EXPECTED_LAST_HANDLE 截断到最后商品: %s，共 %s 个", expected_last_handle, len(all_handles))

    trim_count = expected_count or detected_count
    if trim_count and len(all_handles) > trim_count:
        logger.warning("Club L 前台分页商品数 %s 超过页面显示总数 %s，已按页面总数截断", len(all_handles), trim_count)
        all_handles = all_handles[:trim_count]

    refs: list[dict[str, str]] = []
    for idx, handle in enumerate(all_handles, start=1):
        clean_handle = _normalize_handle(handle)
        if not clean_handle:
            continue
        refs.append({
            "id": "",
            "gid": "",
            "title": "",
            "handle": clean_handle,
            "_collection_page": f"frontend_page_order_{idx}",
        })

    logger.info("Club L 前台分页真实页面顺序 handles=%s detected_count=%s last=%s", len(refs), detected_count or "", refs[-1].get("handle") if refs else "")
    return refs


def _fetch_product_by_handle(
    session: requests.Session,
    base_url: str,
    handle: str,
    timeout: int,
    *,
    raise_retryable: bool = False,
) -> dict[str, Any] | None:
    handle = _safe_str(handle)

    if not handle or "." in handle:
        return None

    if _looks_like_foreign_localized_handle(handle):
        logger.info("跳过多语言本地化 product.js handle: %s", handle)
        return None

    url = f"{base_url.rstrip('/')}/products/{handle}.js"

    data = _fetch_json_get(
        session=session,
        url=url,
        headers=HEADERS_JSON,
        timeout=timeout,
        retries=1,
    )

    if not data or not isinstance(data, dict):
        return None

    data["_source_base_url"] = base_url
    return data




def _strip_json_ld_comments(raw: str) -> str:
    raw = _safe_str(raw).strip()
    # 个别站点会在 JSON-LD 前后包 HTML 注释，先清理掉。
    raw = re.sub(r"^\s*<!--", "", raw)
    raw = re.sub(r"-->\s*$", "", raw)
    return raw.strip()


def _iter_json_ld_objects(html: str) -> list[Any]:
    """提取页面中的 JSON-LD 对象，用于 HTML 详情页兜底。"""
    objects: list[Any] = []
    if not html:
        return objects

    pattern = re.compile(
        r"(?is)<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>"
    )

    for match in pattern.finditer(html):
        raw = _strip_json_ld_comments(unescape(match.group(1)))
        if not raw:
            continue
        try:
            objects.append(json.loads(raw))
        except Exception:
            # 有些 JSON-LD 里会混入无法解析的片段，兜底链路不影响主流程。
            logger.debug("Club L JSON-LD 解析失败，已跳过: %.200s", raw)
            continue

    return objects


def _flatten_json_ld(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    if isinstance(value, dict):
        result.append(value)
        graph = value.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                result.extend(_flatten_json_ld(item))
    elif isinstance(value, list):
        for item in value:
            result.extend(_flatten_json_ld(item))

    return result


def _jsonld_type_contains(item: dict[str, Any], target: str) -> bool:
    raw_type = item.get("@type") or item.get("type")
    target = target.lower()

    if isinstance(raw_type, str):
        return raw_type.lower() == target
    if isinstance(raw_type, list):
        return any(_safe_str(t).lower() == target for t in raw_type)
    return False


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in [None, "", [], {}]:
            return value
    return ""


def _extract_meta_content(html: str, *keys: str) -> str:
    """按 property/name/itemprop 提取 meta content。"""
    if not html:
        return ""

    for key in keys:
        # property/name/itemprop 在 content 前
        pattern1 = re.compile(
            r'''(?is)<meta\b(?=[^>]*(?:property|name|itemprop)=["']''' + re.escape(key) + r'''["'])(?=[^>]*content=["']([^"']*)["'])[^>]*>'''
        )
        match = pattern1.search(html)
        if match:
            return _clean_text(match.group(1))

        # content 在 property/name/itemprop 前
        pattern2 = re.compile(
            r'''(?is)<meta\b(?=[^>]*content=["']([^"']*)["'])(?=[^>]*(?:property|name|itemprop)=["']''' + re.escape(key) + r'''["'])[^>]*>'''
        )
        match = pattern2.search(html)
        if match:
            return _clean_text(match.group(1))

    return ""


def _extract_tag_text(html: str, tag: str) -> str:
    pattern = re.compile(rf"(?is)<{tag}\b[^>]*>(.*?)</{tag}>")
    match = pattern.search(html or "")
    return _clean_text(match.group(1)) if match else ""


def _normalize_jsonld_image(value: Any) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []

    def add(url: Any) -> None:
        clean = _normalize_image_url(url)
        if clean and clean not in {img["src"] for img in images}:
            images.append({"src": clean, "url": clean})

    if isinstance(value, str):
        add(value)
    elif isinstance(value, dict):
        add(value.get("url") or value.get("contentUrl") or value.get("src"))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                add(item)
            elif isinstance(item, dict):
                add(item.get("url") or item.get("contentUrl") or item.get("src"))

    return images


def _normalize_jsonld_offers(offers: Any, fallback_price: float, image_url: str) -> list[dict[str, Any]]:
    """把 JSON-LD offers 转成项目内通用 variants。"""
    offer_items: list[Any] = []

    if isinstance(offers, dict):
        if isinstance(offers.get("offers"), list):
            offer_items.extend(offers.get("offers") or [])
        else:
            offer_items.append(offers)
    elif isinstance(offers, list):
        offer_items.extend(offers)

    variants: list[dict[str, Any]] = []

    for offer in offer_items:
        if not isinstance(offer, dict):
            continue

        price = _parse_price(
            _first_non_empty(
                offer.get("price"),
                offer.get("lowPrice"),
                offer.get("highPrice"),
                fallback_price,
            )
        )
        availability = _safe_str(offer.get("availability")).lower()
        available = not any(word in availability for word in ["outofstock", "soldout", "discontinued"])
        sku = _safe_str(offer.get("sku"))

        variants.append(
            {
                "id": sku,
                "title": _safe_str(offer.get("name")) or "Default Title",
                "price": price,
                "compare_at_price": "",
                "available": available,
                "featured_image": {"src": image_url} if image_url else None,
                "selectedOptions": [],
            }
        )

    if not variants and fallback_price:
        variants.append(
            {
                "id": "",
                "title": "Default Title",
                "price": fallback_price,
                "compare_at_price": "",
                "available": True,
                "featured_image": {"src": image_url} if image_url else None,
                "selectedOptions": [],
            }
        )

    return variants


def _product_from_html_detail(html: str, base_url: str, handle: str) -> dict[str, Any] | None:
    """从 Club L 商品 HTML 详情页提取基础商品信息。

    背景：Club L 部分正常商品页不再稳定提供 /products/{handle}.js，
    所以这里使用 JSON-LD/meta 作为兜底，保证周报至少能拿到名称、价格、图片、描述、URL 等核心字段。
    """
    if not html or not handle:
        return None

    product_jsonld: dict[str, Any] | None = None
    for obj in _iter_json_ld_objects(html):
        for item in _flatten_json_ld(obj):
            if _jsonld_type_contains(item, "Product"):
                product_jsonld = item
                break
        if product_jsonld:
            break

    title = ""
    description = ""
    images: list[dict[str, str]] = []
    offers: Any = None
    sku = ""

    if product_jsonld:
        title = _clean_text(product_jsonld.get("name"))
        description = _clean_text(product_jsonld.get("description"))
        images = _normalize_jsonld_image(product_jsonld.get("image"))
        offers = product_jsonld.get("offers")
        sku = _safe_str(product_jsonld.get("sku") or product_jsonld.get("mpn"))

    # meta / title 兜底
    title = title or _extract_meta_content(html, "og:title", "twitter:title") or _extract_tag_text(html, "title")
    title = re.sub(r"\s*[|–-]\s*Club L London.*$", "", title, flags=re.IGNORECASE).strip()

    description = description or _extract_meta_content(html, "description", "og:description", "twitter:description")

    if not images:
        og_image = _extract_meta_content(html, "og:image", "twitter:image", "image")
        if og_image:
            img = _normalize_image_url(og_image)
            images = [{"src": img, "url": img}]

    image_url = images[0]["src"] if images else ""

    meta_price = _parse_price(
        _first_non_empty(
            _extract_meta_content(html, "product:price:amount", "og:price:amount"),
            _extract_meta_content(html, "price"),
        )
    )

    variants = _normalize_jsonld_offers(offers, meta_price, image_url)
    price = 0.0
    for variant in variants:
        price = _parse_price(variant.get("price"))
        if price:
            break
    price = price or meta_price

    # 商品 id：优先用 JSON-LD sku/mpn，否则用 handle 末尾的 cl 编码兜底，保证 baseline key 稳定。
    product_id = _extract_numeric_id(sku) or _extract_numeric_id(handle)

    if not title and not description and not image_url and not price:
        return None

    return {
        "id": int(product_id) if product_id else "",
        "title": title,
        "handle": handle,
        "vendor": "Club L London",
        "product_type": "",
        "tags": [],
        "body_html": description,
        "description": description,
        "variants": variants or [
            {
                "id": "",
                "title": "Default Title",
                "price": price,
                "compare_at_price": "",
                "available": True,
                "featured_image": {"src": image_url} if image_url else None,
                "selectedOptions": [],
            }
        ],
        "images": images,
        "image": {"src": image_url, "url": image_url} if image_url else None,
        "price": price,
        "price_min": price,
        "compare_at_price": "",
        "compare_at_price_max": "",
        "available": True,
        "_source_base_url": base_url,
        "_html_detail_fallback": True,
    }


def _fetch_product_html_detail(
    session: requests.Session,
    base_url: str,
    handle: str,
    timeout: int,
    *,
    raise_retryable: bool = False,
) -> dict[str, Any] | None:
    handle = _safe_str(handle)
    if not handle or "." in handle or _looks_like_foreign_localized_handle(handle):
        return None

    product_url = _build_product_url(base_url, handle)
    html = _fetch_html(
        session=session,
        base_url=base_url,
        path_or_url=product_url,
        timeout=timeout,
        raise_retryable=raise_retryable,
    )

    if not html:
        return None

    return _product_from_html_detail(html, base_url, handle)


def _product_needs_html_detail(product: dict[str, Any]) -> bool:
    has_title = bool(_safe_str(product.get("title")))
    has_price = bool(_parse_price(product.get("price") or product.get("price_min")))
    has_desc = bool(_clean_text(product.get("body_html")) or _clean_text(product.get("description")))
    has_images = bool(product.get("images") or product.get("image"))
    has_variants = bool(product.get("variants"))

    return not (has_title and has_price and has_desc and has_images and has_variants)


def _fetch_product_html_details_batch(
    session: requests.Session,
    base_url: str,
    handles: list[str],
    timeout: int,
) -> dict[str, dict[str, Any]]:
    if os.getenv("CL_ENABLE_PRODUCT_HTML_DETAIL_FALLBACK", "true").strip().lower() not in {"1", "true", "yes", "y"}:
        logger.info("已关闭 Club L 商品 HTML 详情兜底，跳过 handles=%s", len(handles))
        return {}

    max_workers = max(1, _env_int("CL_PRODUCT_HTML_DETAIL_WORKERS", 1))
    sleep_seconds = max(0.0, _env_float("CL_PRODUCT_HTML_DETAIL_SLEEP_SECONDS", 3.0))
    enable_retry_queue = _env_bool("CL_PRODUCT_HTML_DETAIL_RETRY_QUEUE", False)

    soft_failed_handles = _get_cl_html_soft_failed_handles()
    deduped_handles = list(dict.fromkeys(_normalize_handle(h) or _safe_str(h).strip().lower() for h in handles if h))
    clean_handles = [
        h for h in deduped_handles
        if h
        and not _looks_like_foreign_localized_handle(h)
        and h not in soft_failed_handles
    ]

    skipped_soft_failed = len([h for h in deduped_handles if h in soft_failed_handles])
    if skipped_soft_failed:
        logger.info(
            "Club L 商品 HTML 详情兜底跳过已软失败 handles=%s，避免重复 404/503 慢爬",
            skipped_soft_failed,
        )

    result: dict[str, dict[str, Any]] = {}
    retry_queue = RetryQueue(site_key="clubllondon")

    logger.info(
        "开始 Club L 商品 HTML 详情兜底：handles=%s workers=%s sleep=%s",
        len(clean_handles),
        max_workers,
        sleep_seconds,
    )

    def fetch_with_delay(handle: str) -> dict[str, Any] | None:
        time.sleep(sleep_seconds)
        return _fetch_product_html_detail(
            session=session,
            base_url=base_url,
            handle=handle,
            timeout=timeout,
            raise_retryable=enable_retry_queue,
        )

    def apply_product(handle: str, product: dict[str, Any] | None) -> None:
        if not product or _is_non_dress_product(product):
            return
        product_handle = _safe_str(product.get("handle")) or handle
        result[product_handle] = product

    def queue_retry(handle: str, error: str) -> None:
        def handler() -> dict[str, Any] | None:
            local_session = requests.Session()
            time.sleep(sleep_seconds)
            return _fetch_product_html_detail(
                session=local_session,
                base_url=base_url,
                handle=handle,
                timeout=timeout,
                raise_retryable=enable_retry_queue,
            )

        retry_queue.submit(
            task_type="cl_product_html_detail",
            identity_key=handle,
            payload={"handle": handle, "url": _build_product_url(base_url, handle), "first_error": error},
            handler=handler,
            on_success=lambda product, h=handle: apply_product(h, product),
        )

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="CLProductHTML") as executor:
        future_map = {
            executor.submit(fetch_with_delay, handle): handle
            for handle in clean_handles
        }

        for future in as_completed(future_map):
            handle = future_map[future]
            try:
                product = future.result()
            except Exception as exc:
                if enable_retry_queue and is_retryable_exception(exc):
                    logger.warning("Club L 商品 HTML 详情异常，已进入 retry queue: handle=%s | %s", handle, exc)
                    queue_retry(handle, str(exc))
                else:
                    logger.warning("Club L 商品 HTML 详情异常，已跳过: handle=%s | %s", handle, exc)
                continue

            apply_product(handle, product)

    if enable_retry_queue:
        retry_queue.drain()
    logger.info("Club L 商品 HTML 详情兜底完成：成功=%s retry_summary=%s", len(result), retry_queue.summary())
    return result











def _product_needs_js(product: dict[str, Any]) -> bool:
    has_price = bool(_parse_price(product.get("price") or product.get("price_min")))
    has_desc = bool(_clean_text(product.get("body_html")) or _clean_text(product.get("description")))
    has_images = bool(product.get("images") or product.get("image"))
    has_variants = bool(product.get("variants"))

    return not (has_price and has_desc and has_images and has_variants)




def _fetch_product_js_batch(
    session: requests.Session,
    base_url: str,
    handles: list[str],
    timeout: int,
) -> dict[str, dict[str, Any]]:
    if os.getenv("CL_ENABLE_PRODUCT_JS_FALLBACK", "true").strip().lower() not in {"1", "true", "yes", "y"}:
        logger.info("已关闭 Club L product.js 兜底，跳过 handles=%s", len(handles))
        return {}

    max_workers = int(os.getenv("CL_PRODUCT_JS_WORKERS", "2"))
    sleep_seconds = float(os.getenv("CL_PRODUCT_JS_SLEEP_SECONDS", "0.8"))

    result: dict[str, dict[str, Any]] = {}
    clean_handles = [
        h for h in handles
        if h and not _looks_like_foreign_localized_handle(h)
    ]

    logger.info(
        "开始 Club L product.js 兜底：handles=%s workers=%s sleep=%s",
        len(clean_handles),
        max_workers,
        sleep_seconds,
    )

    retry_queue = RetryQueue(site_key="clubllondon")

    def fetch_with_delay(handle: str) -> dict[str, Any] | None:
        time.sleep(sleep_seconds)
        return _fetch_product_by_handle(session, base_url, handle, timeout, raise_retryable=True)

    def apply_product(handle: str, product: dict[str, Any] | None) -> None:
        if not product or _is_non_dress_product(product):
            return
        product_handle = _safe_str(product.get("handle")) or handle
        result[product_handle] = product

    def queue_retry(handle: str, error: str) -> None:
        def handler() -> dict[str, Any] | None:
            local_session = requests.Session()
            return _fetch_product_by_handle(local_session, base_url, handle, timeout, raise_retryable=True)

        retry_queue.submit(
            task_type="cl_product_js",
            identity_key=handle,
            payload={"handle": handle, "base_url": base_url, "first_error": error},
            handler=handler,
            on_success=lambda product, h=handle: apply_product(h, product),
        )

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="CLProductJS") as executor:
        future_map = {
            executor.submit(fetch_with_delay, handle): handle
            for handle in clean_handles
        }

        for future in as_completed(future_map):
            handle = future_map[future]

            try:
                product = future.result()
            except Exception as exc:
                logger.warning("Club L product.js 异常，已进入 retry queue: handle=%s | %s", handle, exc)
                queue_retry(handle, str(exc))
                continue

            apply_product(handle, product)

    retry_queue.drain()
    logger.info("Club L product.js 兜底完成：成功=%s retry_summary=%s", len(result), retry_queue.summary())
    return result










def fetch_all_clubllondon_products(config: Config) -> tuple[list[dict[str, Any]], str]:
    """只抓取 Club L 前台页面真实展示商品，并用 GraphQL 批量补详情。

    与 Babyboo 最终口径一致：
    1. 前台页面决定商品池和排序；
    2. GraphQL 只能按页面白名单 handle 补详情、价格、variants/尺码；
    3. HTML PDP 只补 GraphQL 后仍缺失的页面白名单商品；
    4. 不再使用 GraphQL collection、product.js、products.json、SWYM、同款颜色扩展来新增页面外商品。
    """
    base_url = getattr(config, "cl_base_url", CL_BASE_URL) or CL_BASE_URL
    collection_handle = getattr(config, "cl_collection_handle", CL_COLLECTION_HANDLE) or CL_COLLECTION_HANDLE
    graphql_url = getattr(config, "cl_graphql_url", CL_GRAPHQL_URL) or CL_GRAPHQL_URL
    timeout = int(getattr(config, "request_timeout", 30) or 30)

    session = _make_session(config)

    # 1) 前台页面真实展示顺序 = 唯一商品池和排序源。
    product_refs = _fetch_collection_product_refs_rendered_page(
        base_url=base_url,
        collection_handle=collection_handle,
        timeout=timeout,
    )

    if not product_refs:
        logger.error(
            "Club L 未能读取前台真实商品顺序，已停止导出。请确认 Playwright/Chromium 可用。"
        )
        return [], base_url

    page_refs: list[dict[str, str]] = []
    seen_handles: set[str] = set()
    for ref in product_refs:
        handle = _normalize_handle(ref.get("handle")) or _safe_str(ref.get("handle")).strip().lower()
        if not handle or handle in seen_handles:
            continue
        if _looks_like_foreign_localized_handle(handle):
            continue
        seen_handles.add(handle)
        clean_ref = dict(ref)
        clean_ref["handle"] = handle
        page_refs.append(clean_ref)

    page_handles = [ref["handle"] for ref in page_refs if ref.get("handle")]
    page_handle_set = set(page_handles)

    logger.info(
        "Club L 页面展示商品白名单=%s，后续 GraphQL/HTML 详情补充不允许新增页面外商品",
        len(page_handles),
    )

    # 2) GraphQL 按 handle 批量补详情/价格/variants/尺码。
    graphql_products = _fetch_product_details_graphql_by_handles(
        session=session,
        graphql_url=graphql_url,
        handles=page_handles,
        base_url=base_url,
        timeout=timeout,
    )

    products_by_handle: dict[str, dict[str, Any]] = {}
    for ref in page_refs:
        handle = ref.get("handle") or ""
        if not handle or handle not in page_handle_set:
            continue

        gql_product = graphql_products.get(handle) or {}
        if gql_product:
            product = dict(gql_product)
            product["_graphql_whitelist_detail_ok"] = True
        else:
            # 页面上已经展示该商品时，不因为详情接口缺失就把它从排序表删除。
            product = {
                "id": _extract_numeric_id(ref.get("id")) or "",
                "title": _safe_str(ref.get("title")),
                "handle": handle,
                "vendor": "Club L London",
                "product_type": "",
                "tags": [],
                "body_html": "",
                "description": "",
                "variants": [],
                "images": [],
                "_page_visible_skeleton": True,
            }

        product["handle"] = _safe_str(product.get("handle")) or handle
        product["_source_base_url"] = base_url
        products_by_handle[handle] = product

    # 3) HTML PDP 只作为缺失兜底，且只能补页面白名单商品。
    html_candidates = [
        handle for handle, product in products_by_handle.items()
        if handle in page_handle_set and _product_needs_html_detail(product)
    ]

    html_detail_products = _fetch_product_html_details_batch(
        session=session,
        base_url=base_url,
        handles=html_candidates,
        timeout=timeout,
    )

    for handle, html_product in html_detail_products.items():
        handle = _normalize_handle(handle) or handle
        if handle not in page_handle_set:
            logger.info("跳过 Club L 页面外 HTML 详情: %s", handle)
            continue
        existing = products_by_handle.get(handle, {})
        products_by_handle[handle] = _merge_non_empty(existing, html_product)

    # 4) 严格按页面顺序输出。GraphQL/HTML 返回顺序不参与最终排序。
    products: list[dict[str, Any]] = []
    for ref in page_refs:
        handle = ref.get("handle") or ""
        if not handle:
            continue
        product = products_by_handle.get(handle)
        if not product:
            product = {
                "id": _extract_numeric_id(ref.get("id")) or "",
                "title": _safe_str(ref.get("title")),
                "handle": handle,
                "vendor": "Club L London",
                "product_type": "",
                "tags": [],
                "body_html": "",
                "description": "",
                "variants": [],
                "images": [],
                "_page_visible_skeleton": True,
            }

        product["handle"] = _safe_str(product.get("handle")) or handle
        product["_source_base_url"] = base_url
        product["_collection_order"] = len(products) + 1
        products.append(product)

    missing_detail = sum(
        1 for product in products
        if not (_clean_text(product.get("body_html")) or _clean_text(product.get("description")))
    )
    missing_variants = sum(1 for product in products if not product.get("variants"))

    logger.info(
        "Club L 最终页面展示商品数=%s | page_refs=%s | graphql_detail=%s | html_detail=%s | missing_detail=%s | missing_variants=%s | 已关闭页面外扩展(graphql_collection/product_js/products_json/color/swym)",
        len(products),
        len(page_refs),
        len(graphql_products),
        len(html_detail_products),
        missing_detail,
        missing_variants,
    )

    return products, base_url



def _record_field_names(record_cls: type) -> set[str]:
    try:
        if is_dataclass(record_cls):
            return {field.name for field in fields(record_cls)}
    except Exception:
        pass
    return set(getattr(record_cls, "__annotations__", {}).keys())


_CL_RECORD_FIELDS = _record_field_names(CLProductRecord)


def _make_cl_product_record(**kwargs: Any) -> CLProductRecord:
    """
    兼容新版/旧版 CLProductRecord。

    新版 product_record.py 增加了 brand 字段；旧版没有。
    这里按 dataclass 字段自动过滤，避免 TypeError。
    """
    filtered = {key: value for key, value in kwargs.items() if key in _CL_RECORD_FIELDS}
    return CLProductRecord(**filtered)





def _build_delisted_record(
    baseline_mgr: BaselineManager,
    key: str,
    info: dict[str, Any],
    scrape_time: str,
) -> CLProductRecord:
    metadata = info.get("metadata", {}) if isinstance(info.get("metadata"), dict) else {}
    fallback_product_name, fallback_color_name = baseline_mgr.split_key(key)

    return _make_cl_product_record(
        site_name=metadata.get("site_name", CL_BRAND_NAME),
        brand=metadata.get("brand", CL_BRAND_NAME),
        category=metadata.get("category", "Bridesmaids"),
        style_label=metadata.get("style_label", ""),
        product_url=metadata.get("product_url", ""),
        product_name=metadata.get("product_name", fallback_product_name),
        color_name=metadata.get("color_name", fallback_color_name),
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

    sorted_products = sorted(
        products,
        key=lambda item: int(item.get("_collection_order", 999999)),
    )

    for current_rank, product in enumerate(sorted_products, start=1):
        # Excel 里的“排序”必须连续，且与最终输出行顺序一致。
        # 不再保留页面 refs 去重/过滤前的原始 idx，避免 103 后跳到 106 这类断号。
        product["_collection_order"] = current_rank
        raw_title = _safe_str(product.get("title"))
        handle = _safe_str(product.get("handle"))
        source_base_url = _safe_str(product.get("_source_base_url")) or CL_BASE_URL

        style_label, product_name_from_title, title_color = _split_style_color_name(raw_title, handle)
        product_url = _build_product_url(source_base_url, handle)

        tags = _get_tags(product)
        variants = product.get("variants", []) or []

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
                or product.get("price_min")
            )

            compare_price = _parse_price(
                chosen_variant.get("compare_at_price")
                or product.get("compare_at_price")
                or product.get("compare_at_price_max")
            )

            original_price = compare_price if compare_price > price else price
            discount_type = "打折" if original_price > price else "无折扣"

            stock_type = _stock_type_from_variants(color_variants)
            size_text = _format_sizes_for_variants(color_variants)

            record = _make_cl_product_record(
                site_name=CL_BRAND_NAME,
                brand=CL_BRAND_NAME,
                category="Bridesmaids",
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
                detail_text=collect_clublondon_product_detail_text(product),
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
                source_page_url=CL_SOURCE_PAGE_URL,
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


def main() -> None:
    config = Config.load()

    logging.basicConfig(
        level=getattr(logging, getattr(config, "log_level", "INFO"), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    logger.info("========== Club L London 自动监控引擎启动 ==========")

    baseline_path = getattr(config, "cl_baseline_path", "clubllondon_baseline.json")
    baseline_mgr = BaselineManager(baseline_path)
    output_dir = getattr(config, "output_dir", "output")
    report_prefix = "clubllondon_report_"
    is_initialization_phase = is_first_site_crawl(output_dir, report_prefix, baseline_mgr)

    current_dt = resolve_current_datetime()
    current_date = current_dt.strftime("%Y-%m-%d")
    current_time_full = current_dt.strftime("%Y-%m-%d %H:%M:%S")

    products, base_url = fetch_all_clubllondon_products(config)

    if not products or not base_url:
        logger.error("Club L London 没有抓取到商品，流程结束")
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

    sheet_name = getattr(config, "cl_sheet_name", "CL_伴娘服总表")
    output_dir = getattr(config, "output_dir", "output")

    report_sheets = build_report_sheets(
        full_sheet_name=sheet_name,
        records=records,
        delisted_records=delisted_records,
        is_initialization_phase=is_initialization_phase,
        columns_l2=COLUMNS_L2_CL,
    )

    filepath = DataExporter().export_multiple_sheets(
        report_sheets,
        output_dir,
        prefix=report_prefix,
        header_l1=HEADER_L1_CONFIG_CL,
        columns_l2=COLUMNS_L2_CL,
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
        "✅ Club L London 处理完成：商品数=%s，颜色行数=%s，下架=%s",
        len(products),
        len(records),
        delisted_count,
    )


def run_cl() -> None:
    main()


if __name__ == "__main__":
    main()
