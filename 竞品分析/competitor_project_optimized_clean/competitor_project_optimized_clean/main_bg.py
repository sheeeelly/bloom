"""Birdy Grey 自动基线感知爬虫引擎。"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import fields
from datetime import datetime
from html import unescape
from typing import Any

import requests

from apis.collection_api import CollectionAPI
from utils.attribute_parser import AttributeParser
from utils.baseline_manager import BaselineManager
from utils.report_history import cleanup_previous_site_reports, is_first_site_crawl, resolve_current_datetime
from utils.config import Config
from utils.data_exporter import DataExporter
from utils.product_details import collect_product_detail_text, extract_frontend_detail_sections, extract_frontend_detail_sections_from_html, extract_description_from_json_like, is_incomplete_detail_text
from utils.report_builder import (
    apply_ranking_context,
    build_report_sheets,
    make_full_columns,
    mark_and_build_delisted_records,
    mark_relisted_after_delisted,
    sync_change_context_from_metadata,
)
from utils.product_record import COLUMNS_L2, HEADER_L1_CONFIG, ProductRecord
from utils.request_handler import RequestHandler
from utils.retry_errors import RetryableTaskError, classify_http_status, is_retryable_exception
from utils.retry_queue import RetryQueue

try:
    from utils.gsheet_sync import GSheetSync
except ImportError:
    GSheetSync = None  # type: ignore

try:
    from utils.attribute_extractor import extract_attributes as common_extract_attributes
except Exception:  # 兼容未替换公共解析器的旧项目
    common_extract_attributes = None  # type: ignore


logger = logging.getLogger(__name__)

BG_SOURCE_PAGE_URL = "https://www.birdygrey.com/collections/bridesmaid-dresses?sort.ga_unique_purchases=desc"


# SearchSpring / tag 里的 aesthetic 字段有些只是氛围词，不能当成最终「风格」。
# 遇到这些值时，即使字段不为空，也继续进入 PDP Product Details 补抓。
LOW_QUALITY_STYLE_VALUES = {
    "sophisticated", "glam", "romantic", "modernminimal", "modern minimal",
    "classic", "timeless", "elegant", "minimal", "modern", "boho",
    "garden", "whimsical", "chic", "formal", "bridesmaid",
}

STRUCTURAL_STYLE_KEYWORDS = [
    "a-line", "aline", "tiered", "fluted", "wrap", "ruffle", "ruffled",
    "pleated", "draped", "ruched", "cowl", "slip", "column", "sheath",
    "mermaid", "trumpet", "empire", "empire waist", "bow", "split",
    "front slit", "side slit", "high slit", "fully lined", "flared",
    "streamer", "streamers", "front streamers", "multiway", "convertible",
    "built-in boning", "boning", "sweeping skirt", "hidden pockets", "side pockets",
    "diagonal seam", "fitted waist", "detachable sleeves", "cut-out back",
    "open back", "pockets", "maternity", "bra-friendly", "off-the-shoulder",
    "strapless", "halter", "v-neck", "square neck", "boat neck", "long sleeve",
    "spaghetti strap", "adjustable strap", "wide shoulder strap", "floral", "jacquard",
]


def _style_quality_key(value: Any) -> str:
    return re.sub(r"[\s_\-/]+", " ", str(value or "").strip().lower()).strip()


def _is_low_quality_style_value(value: Any) -> bool:
    key = _style_quality_key(value)
    if not key:
        return True
    parts = [part.strip() for part in re.split(r"/|,|;", key) if part.strip()] or [key]
    # 如果全部都是氛围词，就认为低质量；只要含结构词，就保留。
    if all(part in LOW_QUALITY_STYLE_VALUES for part in parts):
        return True
    compact = re.sub(r"[^a-z0-9]+", "", key)
    if compact in {re.sub(r"[^a-z0-9]+", "", item) for item in LOW_QUALITY_STYLE_VALUES}:
        return True
    return not any(token in key for token in STRUCTURAL_STYLE_KEYWORDS)


def _pick_structural_style(*values: Any) -> str:
    """优先返回 Product Details 解析出的结构化风格；跳过 Sophisticated/glam 这类氛围词。"""
    fallback = ""
    for value in values:
        normalized = _normalize_bg_attr_display(value, "style")
        if not normalized:
            continue
        if _is_low_quality_style_value(normalized):
            if not fallback:
                fallback = normalized
            continue
        return normalized
    # 如果确实没有结构化信息，默认不把氛围词写进「风格」列，避免误以为字段已完整。
    return ""


def _pick_first_display(field: str, *values: Any) -> str:
    for value in values:
        normalized = _normalize_bg_attr_display(value, field)
        if normalized:
            return normalized
    return ""


def _setup_logging(config: Config) -> None:
    level = getattr(logging, getattr(config, "log_level", "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


def _parse_price(value: Any) -> float:
    """兼容 99、99.00、$99.00、['99.00'] 等格式。"""
    if value is None:
        return 0.0

    if isinstance(value, list):
        value = value[0] if value else 0

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return 0.0

    text = re.sub(r"[^0-9.\-]", "", text)

    try:
        return float(text) if text else 0.0
    except ValueError:
        logger.warning("无法解析价格: %r，按 0 处理", value)
        return 0.0


def _format_price(value: float) -> str:
    return f"${value:.2f}"


def _get_tag_val(tags: list[Any], prefix: str) -> str:
    prefix_lower = prefix.lower()

    for tag in tags:
        if not isinstance(tag, str):
            continue

        if tag.lower().startswith(prefix_lower):
            return tag.split(":", 1)[1].strip() if ":" in tag else ""

    return ""


def _title_case_words(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""

    mapping = {
        "mattesatin": "Matte Satin",
        "matte satin": "Matte Satin",
        "shinysatin": "Shiny Satin",
        "shiny satin": "Shiny Satin",
        "stretchsatin": "Stretch Satin",
        "stretch satin": "Stretch Satin",
        "luxestretchknit": "Luxe Stretch Knit",
        "luxe stretch knit": "Luxe Stretch Knit",
        "plisse": "Plissé",
        "plissé": "Plissé",
        "chiffon": "Chiffon",
        "satin": "Satin",
        "crepe": "Crepe",
        "mesh": "Mesh",
        "velvet": "Velvet",
        "tulle": "Tulle",
        "lace": "Lace",
        "organza": "Organza",
    }
    key = re.sub(r"[\s_-]+", " ", text.lower()).strip()
    return mapping.get(key, " ".join(part.capitalize() for part in text.split()))


def _normalize_color_name(raw_color: str, fabric_name: str) -> str:
    color = _title_case_words(raw_color)
    fabric = _title_case_words(fabric_name)

    if not color:
        return "Default"

    include_fabric = os.getenv("BG_COLOR_INCLUDE_FABRIC", "true").strip().lower() in {
        "1", "true", "yes", "y"
    }
    if not include_fabric or not fabric:
        return color

    color_key = re.sub(r"[\s_-]+", " ", color.lower()).strip()
    fabric_key = re.sub(r"[\s_-]+", " ", fabric.lower()).strip()
    if color_key == fabric_key or color_key.startswith(fabric_key + " "):
        return color

    return f"{fabric} {color}".strip()


def _normalize_bg_attr_display(value: Any, field: str = "") -> str:
    """统一 BG 输出字段展示，避免 mattesatin / floorlength 这种原始 tag 直接进表。"""
    text = str(value or "").strip()
    if not text:
        return ""

    key = re.sub(r"[\s_\-/]+", "", text.lower())
    spaced_key = re.sub(r"[\s_\-/]+", " ", text.lower()).strip()

    mapping = {
        "mattesatin": "Matte Satin",
        "stretchsatin": "Stretch Satin",
        "shinysatin": "Shiny Satin",
        "luxestretchknit": "Luxe Stretch Knit",
        "luxeknit": "Luxe Knit",
        "stretchknit": "Stretch Knit",
        "satin": "Satin",
        "chiffon": "Chiffon",
        "crepe": "Crepe",
        "mesh": "Mesh",
        "velvet": "Velvet",
        "tulle": "Tulle",
        "lace": "Lace",
        "organza": "Organza",
        "plisse": "Plissé",
        "plissé": "Plissé",
        "plissefabric": "Plissé",
        "plisséfabric": "Plissé",
        "floorlength": "Floor-Length",
        "floor": "Floor-Length",
        "maxilength": "Floor-Length",
        "maxi": "Floor-Length",
        "anklelength": "Ankle-Length",
        "midi": "Midi",
        "midilength": "Midi",
        "mini": "Mini",
        "minilength": "Mini",
        "boatneckline": "Boat Neck",
        "boatneck": "Boat Neck",
        "plungingvneckline": "Plunging V-Neck",
        "deepplungingvneckline": "Plunging V-Neck",
        "vneckline": "V-Neck",
        "vneck": "V-Neck",
        "shouldertiestraps": "Shoulder Tie Straps",
        "tiestraps": "Shoulder Tie Straps",
        "shoulderstraps": "Shoulder Straps",
        "thinstraps": "Thin Straps",
        "finestraps": "Thin Straps",
        "oneshoulder": "One-Shoulder",
        "oneshoulderneckline": "One-Shoulder",
        "longsleeves": "Long Sleeve",
        "longsleeve": "Long Sleeve",
        "modernminimal": "Modern Minimal",
        "deepvneck": "Deep V-Neck",
        "deepvneckline": "Deep V-Neck",
        "halterneck": "Halter Neck",
        "halterneckline": "Halter Neck",
        "squareneck": "Square Neck",
        "square neckline": "Square Neck",
        "scoopneck": "Scoop Neck",
        "scoopneckline": "Scoop Neck",
        "sweetheartneck": "Sweetheart Neck",
        "sweetheartneckline": "Sweetheart Neck",
    }

    if key in mapping:
        return mapping[key]

    if "/" in text:
        return " / ".join(_normalize_bg_attr_display(part, field) for part in text.split("/") if str(part).strip())

    if field == "style":
        style_map = {
            "aline": "A-Line",
            "a line": "A-Line",
            "tiered": "Tiered",
            "flutedskirt": "Fluted Skirt",
            "fullylined": "Fully Lined",
            "frontslit": "Front Slit",
            "sideslit": "Side Slit",
            "wrap": "Wrap",
            "ruffle": "Ruffle",
            "ruffled": "Ruffle",
            "pleated": "Pleated",
            "draped": "Draped",
            "ruched": "Ruched",
            "column": "Column",
            "columnskirt": "Column",
            "sweepingcolumnskirt": "Column",
            "sheath": "Sheath",
            "fittedwaist": "Fitted Waist",
            "hiddenpockets": "Hidden Pockets",
            "sidepockets": "Hidden Pockets",
            "detachablesleeves": "Detachable Sleeves",
            "cutoutback": "Cut-Out Back",
            "openback": "Open Back",
            "sophisticated": "Sophisticated",
        }
        if key in style_map:
            return style_map[key]

    return " ".join(part.capitalize() for part in re.split(r"\s+", text.replace("-", " ")) if part)


def _extract_bg_attrs_from_detail_text(text: str) -> dict[str, str]:
    """从 BG PDP Product Details / Fabric Details 文案中补属性。只基于明确出现的词，不臆测。"""
    raw = unescape(str(text or ""))
    raw = re.sub(r"<[^>]+>", " ", raw)
    lower = re.sub(r"[\s\u00a0]+", " ", raw.lower().replace("–", "-").replace("—", "-")).strip()

    fabric = ""
    fabric_patterns = [
        ("Matte Satin", ["matte satin fabric", "fabric details matte satin", "elegant matte satin", "matte satin boasts", "matte satin"]),
        ("Shiny Satin", ["shiny satin"]),
        ("Stretch Satin", ["stretch satin"]),
        ("Luxe Stretch Knit", ["luxe stretch knit"]),
        ("Plissé", ["plissé fabric", "plisse fabric", "lightweight plissé", "lightweight plisse", "plissé"]),
        ("Woven", ["woven fabric", "premium woven", "this woven fabric"]),
        ("Chiffon", ["chiffon"]),
        ("Crepe", ["crepe"]),
        ("Satin", ["satin"]),
        ("Tulle", ["tulle"]),
        ("Velvet", ["velvet"]),
        ("Mesh", ["mesh"]),
        ("Lace", ["lace"]),
    ]
    for label, patterns in fabric_patterns:
        if any(pattern in lower for pattern in patterns):
            fabric = label
            break

    length = ""
    if "ankle-length" in lower or "ankle length" in lower:
        length = "Ankle-Length"
    elif (
        "floor-length" in lower
        or "floor length" in lower
        or "floorlength" in lower
        or "floor sweeping" in lower
        or "floor-sweeping" in lower
        or "sweeps the floor" in lower
        or "sits on the floor" in lower
        or "grazes the floor" in lower
    ):
        length = "Floor-Length"
    elif "maxi length" in lower or "maxi dress" in lower or "maxi gown" in lower:
        length = "Floor-Length"
    elif "tea-length" in lower or "tea length" in lower:
        length = "Tea-Length"
    elif "midi length" in lower or "midi dress" in lower:
        length = "Midi"
    elif "mini length" in lower or "mini dress" in lower:
        length = "Mini"
    elif re.search(r"\bgown\b", lower) and not any(term in lower for term in ["mini", "midi", "short", "knee length", "tea length", "ankle length", "high-low"]):
        length = "Floor-Length"

    neckline_parts: list[str] = []
    neckline_patterns = [
        ("Plunging V-Neck", ["deep plunging v-neckline", "deep plunging v neckline", "plunging v-neckline", "plunging v neckline"]),
        ("Deep V-Neck", ["deep v-neck", "deep v neck"]),
        ("V-Neck", ["v-neckline", "v neckline", "v-neck", "v neck", "v front & back", "v front and back", "v front back", "v front"]),
        ("Boat Neck", ["boat neckline", "boat neck", "bateau neckline", "bateau neck"]),
        ("Shoulder Tie Straps", ["shoulder tie straps", "tie straps"]),
        ("Spaghetti Straps", ["spaghetti straps", "spaghetti strap"]),
        ("Adjustable Straps", ["adjustable straps", "adjustable strap"]),
        ("Thin Straps", ["modern, thin straps", "thin straps", "fine straps"]),
        ("Long Sleeve", ["long sleeves", "long sleeve"]),
        ("Short Sleeve", ["short sleeves", "short sleeve"]),
        ("Flutter Sleeve", ["sheer flutter sleeves", "flutter sleeves", "flutter sleeve"]),
        ("Sleeveless", ["sleeveless"]),
        ("Strapless", ["strapless neckline", "strapless dress"]),
        ("Halter Neck", ["halter neckline", "halter neck"]),
        ("Square Neck", ["square neckline", "square neck"]),
        ("Scoop Neck", ["scoop neckline", "scoop neck"]),
        ("Cowl Neck", ["cowl neckline", "cowl neck"]),
        ("Sweetheart Neck", ["sweetheart neckline", "sweetheart neck"]),
        ("One Shoulder", ["one shoulder", "one-shoulder", "one-shoulder neckline"]),
        ("Off Shoulder", ["off shoulder", "off-the-shoulder", "off the shoulder"]),
        ("Bow Shoulder", ["bows on the shoulders", "shoulder bows", "bow shoulder"]),
    ]
    for label, patterns in neckline_patterns:
        if any(pattern in lower for pattern in patterns) and label not in neckline_parts:
            neckline_parts.append(label)
    if "Plunging V-Neck" in neckline_parts and "V-Neck" in neckline_parts:
        neckline_parts.remove("V-Neck")
    if "Deep V-Neck" in neckline_parts and "V-Neck" in neckline_parts:
        neckline_parts.remove("V-Neck")

    style_parts: list[str] = []
    style_patterns = [
        ("A-Line", ["a-line", "a line", "a line dress", "a line skirt", "a line silhouette"]),
        ("Tiered", ["tiered silhouette", "tiered skirt", "tiered"]),
        ("Fluted Skirt", ["fluted skirt"]),
        ("Bow Shoulder", ["bows on the shoulders", "shoulder bows", "bow shoulder"]),
        ("Wrap", ["wrap dress", "wrap skirt", "wrap silhouette"]),
        ("Ruffle", ["ruffle", "ruffled"]),
        ("Pleated", ["pleated", "pleating"]),
        ("Draped", ["draped", "drape"]),
        ("Ruched", ["ruched", "ruching"]),
        ("Asymmetric", ["asymmetric silhouette", "asymmetrical silhouette", "asymmetric", "asymmetrical"]),
        ("Column", ["column silhouette", "column dress", "column skirt", "sweeping column skirt"]),
        ("Sheath", ["sheath silhouette", "sheath dress"]),
        ("Lace-Up Back", ["lace-up corset back", "lace up corset back", "lace-up back", "lace up back", "lace-up", "lace up"]),
        ("Corset", ["corset back", "corset bodice", "corset", "snatched-waist", "snatched waist"]),
        ("Scarf-Detail", ["style it with a scarf", "with a scarf", "scarf-detail", "scarf detail"]),
        ("Empire Waist", ["raised empire waist", "empire waist"]),
        ("Maternity", ["maternity dress", "expecting moms", "baby-bump friendly", "baby bump friendly", "all trimesters"]),
        ("Fitted Waist", ["fitted waist", "cinched waist", "snatched-waist", "snatched waist"]),
        ("Hidden Pockets", ["hidden side pockets", "side pockets", "hidden pockets"]),
        ("Detachable Sleeves", ["detachable sleeves", "sleeves that button on and off", "button on and off"]),
        ("Front Streamers", ["extra long front streamers", "front streamers", "2 extra long front streamers", "streamers attached"]),
        ("Convertible", ["convertible bows", "bows on the shoulders are convertible", "convertible shoulder bows"]),
        ("Multiway", ["different looks", "creates different looks", "hidden loops at the neck and back", "hidden loops", "multiway"]),
        ("Built-In Boning", ["built-in boning", "built in boning", "boning"]),
        ("Diagonal Seam", ["diagonal seam"]),
        ("Cut-Out Back", ["cut-out in back", "cut out in back", "cut-out back", "cut out back", "surprise cut-out"]),
        ("Open Back", ["open back", "open-back"]),
        ("Jacquard Floral", ["jacquard floral fabric", "jacquard floral", "floral jacquard"]),
        ("Floral", ["floral fabric", "floral print"]),
        ("Front Slit", ["front slit", "front split", "with slit", "seam with slit"]),
        ("Side Slit", ["side slit", "side split"]),
        ("Fully Lined", ["fully-lined", "fully lined"]),
        ("Flowy", ["flowing", "movement", "light and airy"]),
    ]
    for label, patterns in style_patterns:
        if any(pattern in lower for pattern in patterns) and label not in style_parts:
            style_parts.append(label)

    return {
        "fabric_name": fabric,
        "aesthetic_tag": " / ".join(style_parts[:4]),
        "length": length,
        "neckline": " / ".join(neckline_parts[:4]),
    }


def _bg_known_style_fallback(product_name: str, handle: str, detail_text: str, neckline: str = "", length: str = "", fabric: str = "") -> str:
    """
    BG 款式级风格兜底。

    用于解决 Product Details 已经抓到，但仍然因为自然语言表达或历史款式命名导致
    「风格」为空的问题。优先基于详情文案，其次基于已知款式名/handle 做保守兜底。
    """
    source = " ".join([product_name or "", handle or "", detail_text or "", neckline or "", length or "", fabric or ""])
    normalized = re.sub(r"[^a-z0-9]+", " ", source.lower()).strip()

    parts: list[str] = []

    def add(label: str, *patterns: str) -> None:
        if label in parts:
            return
        if any(pattern and pattern in normalized for pattern in patterns):
            parts.append(label)

    # 明确来自 Product Details 的结构化风格
    add("A-Line", "a line", "a line skirt", "a line dress", "a line silhouette")
    add("Tiered", "tiered", "tiered silhouette", "tiered skirt")
    add("Jacquard Floral", "jacquard floral", "floral jacquard")
    add("Floral", "floral fabric", "floral print")
    add("Front Streamers", "front streamers", "extra long front streamers", "streamers attached")
    add("Multiway", "different looks", "hidden loops", "convertible")
    add("Built-In Boning", "built in boning", "built in", "boning")
    add("Fitted Waist", "fitted waist", "cinched waist")
    add("Sweeping Skirt", "sweeping skirt", "sweeping column skirt")
    add("Hidden Pockets", "hidden side pockets", "side pockets", "hidden pockets")
    add("Detachable Sleeves", "detachable sleeves", "button on and off")
    add("Diagonal Seam", "diagonal seam")
    add("Front Slit", "front slit", "front split", "with slit", "seam with slit")
    add("Side Slit", "side slit", "side split")
    add("Cut-Out Back", "cut out in back", "cut out back", "surprise cut out", "cutout back")
    add("Open Back", "open back")
    add("Column", "column skirt", "column silhouette")
    add("Fully Lined", "fully lined")
    add("Empire Waist", "raised empire waist", "empire waist")
    add("Maternity", "maternity dress", "expecting moms", "baby bump friendly", "all trimesters")
    add("Fluted Skirt", "fluted skirt")
    add("Pleated", "pleated", "pleating")
    add("Ruffle", "ruffle", "ruffled")
    add("Ruched", "ruched", "ruching")
    add("Draped", "draped", "drape")
    add("Asymmetric", "asymmetric silhouette", "asymmetrical silhouette", "asymmetric", "asymmetrical")
    add("Lace-Up Back", "lace up corset back", "lace up back", "lace up", "laceup")
    add("Corset", "corset back", "corset bodice", "corset", "snatched waist")
    add("Convertible", "convertible bows", "bows on the shoulders are convertible", "convertible shoulder bows")
    add("Scarf-Detail", "style it with a scarf", "with a scarf", "scarf detail")

    if parts:
        return " / ".join(parts[:4])

    # 款式名兜底：只在风格仍为空时使用，用于 BG 常见基础款多色变体。
    name_key = re.sub(r"[^a-z0-9]+", " ", (product_name or handle or "").lower()).strip()
    known_map = [
        (("grace dress with slit", "grace chiffon dress with slit"), "Front Streamers / Multiway / Front Slit / Hidden Pockets"),
        (("grace dress slit",), "Front Streamers / Multiway / Front Slit / Hidden Pockets"),
        (("grace dress", "grace chiffon dress"), "Front Streamers / Multiway / Hidden Pockets"),
        (("stephanie dress", "stephanie chiffon dress"), "A-Line / Diagonal Seam / Front Slit"),
        (("gwennie dress with slit", "gwennie chiffon dress with slit"), "A-Line / Front Slit"),
        (("gwennie dress", "gwennie chiffon dress"), "A-Line"),
        (("kaia dress", "kaia chiffon dress"), "A-Line"),
        (("kayla dress", "kayla chiffon dress"), "A-Line"),
        # Hannah: PDP 明确写到 V front & back、raised empire waist、sheer flutter sleeves、pockets。
        (("hannah dress", "hannah chiffon dress"), "Empire Waist / Maternity / Hidden Pockets"),
        (("mischa dress", "mischa chiffon dress"), "Off-the-Shoulder"),
        (("kensie dress",), "A-Line"),
        (("destiny dress",), "A-Line"),
        (("daphne dress",), "A-Line"),
        (("ivy dress",), "Sheath"),
        (("arbor dress",), "A-Line / Jacquard Floral"),
        # Gwen: Product Details 明确写到 midi length、fluted skirt、convertible shoulder bows。
        # 该款有大量颜色级 handle，若某些颜色未命中 PDP 回填，也不能让风格为空。
        (("gwen dress", "gwen matte satin dress"), "Fluted Skirt / Bow Shoulder / Convertible"),
    ]
    for keys, value in known_map:
        if any(key in name_key for key in keys):
            return value

    # 最后兜底：如果 title/handle 明确写了 with slit，不让风格空。
    if "with slit" in normalized or " dress with slit" in normalized:
        return "Front Slit"

    return ""



def _bg_known_length_fallback(product_name: str, handle: str, detail_text: str, fabric: str = "", style: str = "") -> str:
    """BG 长度兜底：用于 PDP 没有明确 length 字段但文案/款式可稳定判断的场景。"""
    source = " ".join([product_name or "", handle or "", detail_text or "", fabric or "", style or ""])
    normalized = re.sub(r"[^a-z0-9]+", " ", source.lower()).strip()

    # 明确非及地长度优先。
    if "tea length" in normalized or "tea length dress" in normalized:
        return "Tea-Length"
    if "ankle length" in normalized or "ankle length dress" in normalized:
        return "Ankle-Length"
    if "midi" in normalized:
        return "Midi"
    if "mini" in normalized or "short dress" in normalized:
        return "Mini"
    if "knee length" in normalized:
        return "Knee-Length"

    # BG Gwen: Product Details 明确为 midi length dress。
    # 有些颜色级 handle 如果没有成功回填 PDP 详情，仍应按款式级规则兜底。
    if "gwen dress" in normalized or "gwen matte satin dress" in normalized:
        return "Midi"

    # 明确及地/长礼服。
    if any(pattern in normalized for pattern in [
        "floor length", "floorlength", "floor sweeping", "sweeps the floor",
        "sits on the floor", "grazes the floor", "maxi length", "maxi dress", "maxi gown",
    ]):
        return "Floor-Length"

    # BG Freida / Stephanie 这类详情只写 gown / column，不直接写 length。
    if re.search(r"\bgown\b", normalized) and not any(term in normalized for term in ["mini", "midi", "short", "knee length", "tea length", "ankle length", "high low"]):
        return "Floor-Length"
    if "luxe stretch knit dress" in normalized and "column" in normalized:
        return "Floor-Length"
    if "stephanie dress" in normalized and ("halter gown" in normalized or "classic halter gown" in normalized or "cross front halter" in normalized):
        return "Floor-Length"

    return ""


def _bg_known_neckline_fallback(product_name: str, handle: str, detail_text: str) -> str:
    """BG 上半身款式兜底：只处理 Product Details 或已知款式中非常明确的表达。"""
    source = " ".join([product_name or "", handle or "", detail_text or ""])
    normalized = re.sub(r"[^a-z0-9]+", " ", source.lower()).strip()

    if any(pattern in normalized for pattern in ["bows on the shoulders", "shoulder bows", "bow shoulder"]):
        return "Bow Shoulder"

    # Gwen: Product Details 明确写到 bows on the shoulders，颜色级 handle 没有命中 PDP 时兜底。
    if "gwen dress" in normalized or "gwen matte satin dress" in normalized:
        return "Bow Shoulder"

    hannah_neckline_parts: list[str] = []
    if any(pattern in normalized for pattern in ["v front back", "v front and back", "v front", "v neckline", "v neck"]):
        hannah_neckline_parts.append("V-Neck")
    if any(pattern in normalized for pattern in ["sheer flutter sleeves", "flutter sleeves", "flutter sleeve"]):
        hannah_neckline_parts.append("Flutter Sleeve")
    if hannah_neckline_parts:
        return " / ".join(hannah_neckline_parts[:2])

    # Hannah: 颜色级 handle 未成功回填 PDP 时，按款式级描述兜底。
    if "hannah dress" in normalized or "hannah chiffon dress" in normalized:
        return "V-Neck / Flutter Sleeve"

    if any(pattern in normalized for pattern in ["cowl neckline", "cowl neck"]):
        return "Cowl Neck"
    if any(pattern in normalized for pattern in ["halter neckline", "halter neck"]):
        return "Halter Neck"
    if any(pattern in normalized for pattern in ["square neckline", "square neck"]):
        return "Square Neck"
    if any(pattern in normalized for pattern in ["v neckline", "v neck", "v neck line"]):
        return "V-Neck"
    if any(pattern in normalized for pattern in ["strapless neckline", "strapless dress"]):
        return "Strapless"

    return ""

def _smart_title(raw_title: str, handle: str, fabric_name: str) -> str:
    title = (raw_title or "").strip()

    # 之前版本会把 fabric 拼进商品名，例如 "Chris Dress in chiffon"。
    # 为了和前面统一字段逻辑一致，默认不再拼 fabric；面料单独放到「面料名称」，
    # 颜色可通过 BG_COLOR_INCLUDE_FABRIC=true 输出为 "Chiffon Sage"。
    keep_fabric_in_name = os.getenv("BG_KEEP_FABRIC_IN_PRODUCT_NAME", "false").strip().lower() in {
        "1", "true", "yes", "y"
    }
    if keep_fabric_in_name and fabric_name and " in " not in title.lower():
        title = f"{title} in {fabric_name}"

    if "slit" in (handle or "").lower() and "slit" not in title.lower():
        title = f"{title} With Slit"

    return title


def _bg_stable_product_key(handle: str, product_name: str) -> str:
    """
    Birdy Grey 基线/周度新增颜色使用的稳定商品 key。

    优先使用 handle，避免商品标题文案变化时，同一个商品颜色被误判为新商品/新颜色；
    handle 为空时再用 product_name 兜底。
    """
    handle = str(handle or "").strip().strip("/")
    if handle and "." not in handle:
        return handle
    return str(product_name or "").strip() or "UNKNOWN"


def _record_kwargs(record_cls: type, **kwargs: Any) -> dict[str, Any]:
    """兼容新版/旧版 ProductRecord：新版有 brand，旧版没有。"""
    try:
        allowed = {field.name for field in fields(record_cls)}
    except TypeError:
        return kwargs
    return {key: value for key, value in kwargs.items() if key in allowed}


def _make_product_record(**kwargs: Any) -> ProductRecord:
    return ProductRecord(**_record_kwargs(ProductRecord, **kwargs))




def _merge_common_attrs(item: dict[str, Any], attrs: dict[str, str], tags: list[Any]) -> dict[str, str]:
    """公共属性解析器只做兜底，不覆盖 Birdy Grey 标签里已经解析出的值。"""
    if common_extract_attributes is None:
        return attrs

    try:
        common_attrs = common_extract_attributes({
            "title": item.get("title"),
            "handle": item.get("handle"),
            "tags": tags,
            "body_html": item.get("body_html"),
            "description": item.get("description"),
            "product_type": item.get("product_type"),
            "vendor": item.get("vendor"),
            "product_details": item.get("product_details"),
            "fabric_details": item.get("fabric_details"),
            "_pdp_detail_text": item.get("_pdp_detail_text"),
            "_pdp_jsonld_text": item.get("_pdp_jsonld_text"),
        }, default_floor_length=True)
    except Exception:
        return attrs

    merged = dict(attrs)
    if not merged.get("fabric") and common_attrs.get("fabric_name"):
        merged["fabric"] = common_attrs.get("fabric_name", "")
    if not merged.get("aesthetic") and common_attrs.get("aesthetic_tag"):
        merged["aesthetic"] = common_attrs.get("aesthetic_tag", "")
    if not merged.get("length") and common_attrs.get("length"):
        merged["length"] = common_attrs.get("length", "")
    if not merged.get("neckline") and common_attrs.get("neckline"):
        merged["neckline"] = common_attrs.get("neckline", "")
    return merged




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


def _html_to_visible_text(html: str) -> str:
    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<noscript\b[^>]*>.*?</noscript>", " ", html, flags=re.I | re.S)
    text = unescape(html)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()




def _extract_focused_pdp_text(visible_text: str, raw_html: str = "") -> str:
    """只提取前台 Product Details / Fabric Details 等详情区块。

    优先使用可见文本；如果页面把 Product Details/Fabric Details 放在内嵌 JS/JSON，
    再从原始 HTML 反解。找不到明确详情标题时返回空。
    """
    focused = extract_frontend_detail_sections(visible_text or "")
    if focused:
        return focused
    if raw_html:
        focused = extract_frontend_detail_sections_from_html(raw_html)
        if focused:
            return focused
    return ""

def _extract_jsonld_text_from_html(html: str) -> str:
    chunks: list[str] = []
    for match in re.finditer(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html,
        flags=re.I | re.S,
    ):
        raw = unescape(match.group(1)).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            data = raw
        chunks.append(_value_to_text_for_pdp(data))
    return re.sub(r"\s+", " ", " ".join(chunks)).strip()


def _value_to_text_for_pdp(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(_value_to_text_for_pdp(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_value_to_text_for_pdp(v) for v in value)
    return _html_to_visible_text(str(value))



def clean_bg_product_json_text(text: str) -> str:
    """JSON 兜底只保留 body_html/description 的自然描述，不接受 tags/schema。"""
    cleaned = extract_description_from_json_like({"body_html": text})
    lower = cleaned.lower()
    if not cleaned:
        return ""
    if "schema.org" in lower or "productgroup" in lower or "offer" in lower:
        return ""
    return cleaned

def _fetch_bg_pdp_attr_text(
    session: requests.Session,
    handle: str,
    timeout: int,
    *,
    raise_retryable: bool = False,
) -> tuple[str, str]:
    """抓取 Birdy Grey PDP / product JSON 中的详情文案，用于补属性。"""
    handle = (handle or "").strip().strip("/")
    if not handle or "." in handle:
        return "", ""

    headers_html = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.birdygrey.com/collections/bridesmaid-dresses",
    }
    headers_json = {
        "User-Agent": headers_html["User-Agent"],
        "Accept": "application/json, text/plain, */*",
        "Referer": f"https://www.birdygrey.com/products/{handle}",
    }

    # 1）优先抓 PDP HTML，因为 Product Details / Fabric Details 往往在页面中。
    page_url = f"https://www.birdygrey.com/products/{handle}"
    try:
        resp = session.get(page_url, headers=headers_html, timeout=timeout)
        if resp.status_code == 200:
            visible = _html_to_visible_text(resp.text)
            focused = _extract_focused_pdp_text(visible, resp.text)
            jsonld_text = _extract_jsonld_text_from_html(resp.text)
            if focused or jsonld_text:
                return focused, jsonld_text
        elif resp.status_code not in {404, 410}:
            if raise_retryable:
                classify_http_status(resp.status_code, page_url)
            logger.debug("Birdy Grey PDP HTML 请求失败: status=%s url=%s", resp.status_code, page_url)
    except Exception as exc:
        if raise_retryable and is_retryable_exception(exc):
            raise RetryableTaskError(f"Birdy Grey PDP retryable error handle={handle}: {exc}") from exc
        logger.debug("Birdy Grey PDP HTML 请求异常: handle=%s | %s", handle, exc)

    # 2）兜底抓 Shopify JSON / JS。部分商品 HTML 不含详情时，body_html 可能在这里。
    for suffix in [".js", ".json"]:
        url = f"https://www.birdygrey.com/products/{handle}{suffix}"
        try:
            resp = session.get(url, headers=headers_json, timeout=timeout)
            if resp.status_code != 200:
                if raise_retryable and resp.status_code not in {404, 410}:
                    classify_http_status(resp.status_code, url)
                continue
            data = resp.json()
            if suffix == ".json" and isinstance(data, dict) and isinstance(data.get("product"), dict):
                data = data["product"]
            if not isinstance(data, dict):
                continue
            text = "\n".join(
                str(data.get(k) or "")
                for k in ["body_html", "description", "product_details", "fabric_details"]
                if data.get(k)
            )
            focused = extract_frontend_detail_sections(text) or clean_bg_product_json_text(text)
            if focused:
                return focused, ""
        except Exception as exc:
            if raise_retryable and is_retryable_exception(exc):
                raise RetryableTaskError(f"Birdy Grey product JSON retryable error handle={handle}: {exc}") from exc
            logger.debug("Birdy Grey product detail JSON 请求异常: handle=%s url=%s | %s", handle, url, exc)

    return "", ""


# ==========================================
# Birdy Grey 尺码补充（按页面 SKC / color handle 维度）
# ==========================================

_BG_SIZE_ORDER = [
    "XXS", "XS", "S", "M", "L", "XL", "XXL",
    "0", "2", "4", "6", "8", "10", "12", "14", "16", "18", "20", "22", "24", "26", "28", "30", "32",
    "1X", "2X", "3X", "4X", "5X",
]
_BG_SIZE_ORDER_INDEX = {value: idx for idx, value in enumerate(_BG_SIZE_ORDER)}
_BG_SIZE_PATTERN = re.compile(
    r"^(?:XXS|XS|S|M|L|XL|XXL|[1-5]X|[0-9]{1,2}|US\s*[0-9]{1,2}|A[0-9]{1,2})$",
    flags=re.I,
)


def _normalize_bg_size_label(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(?:size|choose size|select size)\s*[:：-]?\s*", "", text, flags=re.I).strip()
    # 页面按钮常见文案："XS Sold Out" / "US 6 - Unavailable"。
    # 尺码归一化时先移除库存状态词，再判断真实尺码。
    text = re.sub(r"\b(?:sold out|out of stock|unavailable|notify me|coming soon)\b", "", text, flags=re.I).strip()
    text = re.sub(r"[-–—]+$", "", text).strip()
    text = text.replace("US ", "").replace("us ", "")
    if not text or text.lower() in {"default title", "one size", "os", "n/a", "none", "sold out"}:
        return ""
    upper = text.upper().replace(" ", "")
    # 兼容 x-small / small 等文本写法。
    word_map = {
        "XX-SMALL": "XXS", "EXTRAEXTRASMALL": "XXS", "2XS": "XXS",
        "X-SMALL": "XS", "EXTRASMALL": "XS",
        "SMALL": "S", "MEDIUM": "M", "LARGE": "L",
        "X-LARGE": "XL", "EXTRALARGE": "XL",
        "XX-LARGE": "XXL", "EXTRAEXTRALARGE": "XXL", "2XL": "XXL",
    }
    upper = word_map.get(upper, upper)
    if _BG_SIZE_PATTERN.match(upper):
        return upper
    return ""


def _bg_size_sort_key(value: str) -> tuple[int, str]:
    label = _normalize_bg_size_label(value) or str(value or "").strip().upper()
    return (_BG_SIZE_ORDER_INDEX.get(label, 999), label)


def _extract_bg_variant_size(variant: dict[str, Any]) -> str:
    """从 Shopify variant 中提取尺码。

    BG 的商品详情按颜色/SKC 维度展示，尺码必须按每个 color handle 的 variants 读取，
    不能用款式组代表 PDP 的尺码套所有颜色。
    """
    if not isinstance(variant, dict):
        return ""

    selected_options = variant.get("selectedOptions") or variant.get("selected_options") or []
    if isinstance(selected_options, list):
        for option in selected_options:
            if not isinstance(option, dict):
                continue
            name = str(option.get("name") or "").strip().lower()
            value = option.get("value")
            if "size" in name:
                label = _normalize_bg_size_label(value)
                if label:
                    return label

    # Shopify /products/{handle}.js 常见字段：option1 / option2 / option3。
    for key in ["option1", "option2", "option3"]:
        label = _normalize_bg_size_label(variant.get(key))
        if label:
            return label

    # 兜底从 title/public_title 中找尺码。例如 "XS" 或 "Black / XS"。
    for key in ["public_title", "title", "name"]:
        text = str(variant.get(key) or "").strip()
        if not text:
            continue
        for part in re.split(r"\s*/\s*|\s+-\s+|,", text):
            label = _normalize_bg_size_label(part)
            if label:
                return label
    return ""


def _bg_variant_is_available(variant: dict[str, Any]) -> bool:
    if not isinstance(variant, dict):
        return False
    for key in ["available", "availableForSale", "available_for_sale"]:
        if key in variant:
            return bool(variant.get(key))
    # 某些 Shopify JSON 只有库存数量字段。
    for key in ["inventory_quantity", "quantity", "inventoryQuantity"]:
        if key in variant:
            try:
                return int(float(str(variant.get(key) or 0))) > 0
            except Exception:
                pass
    # 没有可靠可售字段时，不把它当作可售，避免把全尺码误写出来。
    return False


def _format_bg_sizes_from_variants(variants: Any) -> tuple[str, str]:
    """返回：(尺码文本, 库存状态)。

    - 有可售尺码：输出可售尺码，库存状态=现货；
    - variants 存在但全部不可售：输出 无码，库存状态=缺货；
    - variants 缺失或没有尺码字段：输出 未获取，库存状态=未知。
    """
    if not isinstance(variants, list) or not variants:
        return "未获取", "未知"

    all_sizes: list[str] = []
    available_sizes: list[str] = []
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        size = _extract_bg_variant_size(variant)
        if not size:
            continue
        if size not in all_sizes:
            all_sizes.append(size)
        if _bg_variant_is_available(variant) and size not in available_sizes:
            available_sizes.append(size)

    if available_sizes:
        available_sizes = sorted(available_sizes, key=_bg_size_sort_key)
        return " / ".join(available_sizes), "现货"
    if all_sizes:
        return "无码", "缺货"
    return "未获取", "未知"


def _fetch_bg_product_json_for_size(
    session: requests.Session,
    handle: str,
    timeout: int,
) -> tuple[str, str, str]:
    """按 BG 页面 color handle 精确读取尺码。

    注意：这里仅用于页面白名单 handle 的尺码补充，不允许新增商品。
    """
    handle = str(handle or "").strip().strip("/")
    if not handle or "." in handle:
        return handle, "未获取", "未知"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": f"https://www.birdygrey.com/products/{handle}",
    }

    for suffix in [".js", ".json"]:
        url = f"https://www.birdygrey.com/products/{handle}{suffix}"
        try:
            resp = session.get(url, headers=headers, timeout=timeout)
            if resp.status_code != 200:
                logger.debug("Birdy Grey 尺码 JSON 请求失败: status=%s url=%s", resp.status_code, url)
                continue
            data = resp.json()
            if suffix == ".json" and isinstance(data, dict) and isinstance(data.get("product"), dict):
                data = data["product"]
            if not isinstance(data, dict):
                continue
            size_text, stock_status = _format_bg_sizes_from_variants(data.get("variants"))
            if size_text != "未获取":
                return handle, size_text, stock_status
        except Exception as exc:
            logger.debug("Birdy Grey 尺码 JSON 请求异常: handle=%s suffix=%s | %s", handle, suffix, exc)

    return handle, "未获取", "未知"





def _extract_bg_size_labels_from_page_text(page_text: str) -> list[str]:
    """从 BG 渲染后页面的可见文本中兜底提取尺码。

    Birdy Grey 部分 PDP 的尺码区域不是普通 button / radio selector，
    而是以文本形式出现：
        Size:
        Size Chart Icon Size Chart
        Size values
        XS
        S
        M
        ...

    之前 parser 只抓按钮/选项节点，会把这类商品写成“未获取”。
    这里在 selector 解析失败时，从 "Size values" 后面的文本块兜底提取尺码。
    """
    if not page_text:
        return []

    lines = [line.strip() for line in re.split(r"[\r\n]+", str(page_text)) if line and line.strip()]
    if not lines:
        return []

    lower_lines = [line.lower() for line in lines]
    start_indexes: list[int] = []

    for idx, lower in enumerate(lower_lines):
        normalized = re.sub(r"\s+", " ", lower).strip()
        if normalized in {"size values", "size value", "sizes"}:
            start_indexes.append(idx + 1)
        elif normalized.startswith("size values "):
            start_indexes.append(idx)

    stop_patterns = [
        "estimated arrival",
        "add to bag",
        "add to cart",
        "product details",
        "fabric details",
        "complete the look",
        "customers also",
        "you may also",
        "reviews",
        "shipping",
        "returns",
        "color:",
        "color values",
        "quantity",
    ]

    skip_patterns = [
        "size:",
        "size chart",
        "size chart icon",
        "choose size",
        "select size",
        "selected size",
    ]

    collected: list[str] = []

    for start_idx in start_indexes:
        # 最多向后读 40 行，避免把整页其他文案误识别为尺码。
        for line in lines[start_idx:start_idx + 40]:
            lower = line.lower()
            normalized_line = re.sub(r"\s+", " ", lower).strip()

            if any(pattern in normalized_line for pattern in stop_patterns):
                if collected:
                    return sorted(collected, key=_bg_size_sort_key)
                continue

            if any(pattern == normalized_line or normalized_line.startswith(pattern) for pattern in skip_patterns):
                continue

            # 兼容一行一个尺码，或一行多个尺码：XS S M L XL XXL 0X 1X...
            parts = re.split(r"\s*/\s*|\s+\|\s+|,|;|\s{2,}|\s+", line)
            line_found = False

            for part in parts:
                label = _normalize_bg_size_label(part)
                if not label:
                    continue
                if label not in collected:
                    collected.append(label)
                line_found = True

            # 如果已经开始收集，连续遇到明显非尺码文本时可以停止，避免误抓。
            if collected and not line_found:
                # 一些页面尺码之间可能夹杂空白或无效辅助文本；这里只在明显长文本时停止。
                if len(line) > 25:
                    break

        if collected:
            return sorted(collected, key=_bg_size_sort_key)

    return []


def _extract_bg_sizes_from_rendered_page(page: Any) -> tuple[str, str]:
    """从真实渲染后的 BG PDP 页面读取当前颜色/SKC 的尺码。

    优先读取真实尺码按钮/选项；如果按钮 selector 没命中，则从页面文本中的
    "Size values" 区块兜底提取尺码。这样可以覆盖 Brielle 这类页面。
    """
    try:
        raw_items = page.evaluate(
            r"""
            () => {
              const visible = (el) => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style && style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
              };
              const disabledLike = (el) => {
                const cls = ((el.className || '') + ' ' + ((el.parentElement && el.parentElement.className) || '')).toLowerCase();
                const aria = String(el.getAttribute('aria-disabled') || '').toLowerCase();
                const disabled = !!el.disabled || aria === 'true';
                const text = ((el.innerText || el.textContent || '') + ' ' + (el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '')).toLowerCase();
                return disabled || /disabled|unavailable|sold[-_\s]?out|out[-_\s]?of[-_\s]?stock|not-available/.test(cls) || /sold out|unavailable|out of stock/.test(text);
              };
              const readText = (el) => {
                const attrs = ['data-size','data-value','data-option-value','data-option','value','aria-label','title'];
                const parts = [];
                for (const a of attrs) {
                  const v = el.getAttribute && el.getAttribute(a);
                  if (v) parts.push(v);
                }
                const t = (el.innerText || el.textContent || '').trim();
                if (t) parts.push(t);
                return parts.join(' ').replace(/\s+/g, ' ').trim();
              };
              const containers = Array.from(document.querySelectorAll('main, form[action*="/cart/add"], [data-product-form], [class*="product"], body'));
              const nodes = [];
              for (const root of containers) {
                for (const el of root.querySelectorAll('button, [role="button"], label, input[type="radio"], input[type="button"], option, select option, [data-size], [data-option-value], [data-value]')) {
                  if (!visible(el)) continue;
                  const raw = readText(el);
                  if (!raw) continue;
                  nodes.push({raw, disabled: disabledLike(el)});
                }
              }
              return nodes;
            }
            """
        )
    except Exception:
        raw_items = []

    all_sizes: list[str] = []
    available_sizes: list[str] = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            raw = str(item.get("raw") or "")
            disabled = bool(item.get("disabled"))
            # 同一个节点可能包含多个文本片段，只从常见分隔中取可能的尺码 token。
            parts = re.split(r"\s*/\s*|\s+\|\s+|,|\n|\r|\t|•|\s{2,}", raw)
            for part in parts:
                label = _normalize_bg_size_label(part)
                if not label:
                    continue
                if label not in all_sizes:
                    all_sizes.append(label)
                if not disabled and label not in available_sizes:
                    available_sizes.append(label)

    if available_sizes:
        available_sizes = sorted(available_sizes, key=_bg_size_sort_key)
        return " / ".join(available_sizes), "现货"
    if all_sizes:
        return "无码", "缺货"

    # 兜底：BG 部分 PDP 将尺码以 "Size values" 文本块渲染，不一定有可识别按钮。
    try:
        page_text = page.inner_text("body", timeout=5000)
    except Exception:
        page_text = ""

    fallback_sizes = _extract_bg_size_labels_from_page_text(page_text)
    if fallback_sizes:
        return " / ".join(fallback_sizes), "现货"

    return "未获取", "未知"

def _fetch_bg_rendered_size_worker(
    handles: list[str],
    timeout: int,
    sleep_seconds: float,
    browser_executable_path: str,
    worker_idx: int,
) -> dict[str, tuple[str, str]]:
    """单个 Playwright worker：复用一个浏览器顺序打开一组 BG PDP 读取尺码。"""
    results: dict[str, tuple[str, str]] = {}
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        logger.warning("Playwright 不可用，无法读取 Birdy Grey 渲染后尺码：%s", exc)
        return results

    with sync_playwright() as p:
        launch_kwargs: dict[str, Any] = {
            "headless": True,
            "args": ["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
        }
        if browser_executable_path:
            launch_kwargs["executable_path"] = browser_executable_path
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 1200},
            locale="en-US",
        )
        page = context.new_page()
        page.set_default_timeout(max(5000, timeout * 1000))
        for idx, handle in enumerate(handles, start=1):
            handle = str(handle or "").strip().strip("/")
            if not handle:
                continue
            url = f"https://www.birdygrey.com/products/{handle}"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=max(8000, timeout * 1000))
                try:
                    page.wait_for_load_state("networkidle", timeout=6000)
                except Exception:
                    pass
                page.wait_for_timeout(800)
                size_text, stock_status = _extract_bg_sizes_from_rendered_page(page)
                results[handle] = (size_text, stock_status)
            except Exception as exc:
                logger.debug("Birdy Grey 渲染 PDP 尺码读取失败: worker=%s handle=%s | %s", worker_idx, handle, exc)
                results[handle] = ("未获取", "未知")
            if sleep_seconds:
                time.sleep(sleep_seconds)
        try:
            page.close()
        except Exception:
            pass
        context.close()
        browser.close()
    return results


def _prefetch_bg_rendered_size_info_by_handle(
    config: Config,
    handles: list[str],
    existing: dict[str, tuple[str, str]] | None = None,
) -> dict[str, tuple[str, str]]:
    """对 JSON 未命中的 BG color handle，用真实 PDP 渲染页面补尺码。

    这是 BG 获取尺码的有效兜底：不能因为 .js/.json 无 variants 就停止。
    商品池仍由 SearchSpring 页面白名单决定；这里只补白名单 handle 的尺码。
    """
    if not _env_bool("BG_ENABLE_RENDERED_SIZE_ENRICH", True):
        return existing or {}

    existing = dict(existing or {})
    missing_handles = [h for h in handles if existing.get(h, ("未获取", "未知"))[0] == "未获取"]
    if not missing_handles:
        return existing

    max_handles = _env_int("BG_RENDERED_SIZE_MAX_HANDLES", 0)
    if max_handles > 0 and len(missing_handles) > max_handles:
        logger.warning(
            "Birdy Grey 渲染尺码补抓 handle 数=%s 超过限制=%s，本次仅补前 %s 个；如需全量请调大/置空 BG_RENDERED_SIZE_MAX_HANDLES",
            len(missing_handles), max_handles, max_handles,
        )
        missing_handles = missing_handles[:max_handles]

    workers = max(1, min(_env_int("BG_RENDERED_SIZE_WORKERS", 4), 8))
    sleep_seconds = max(0.0, min(_env_float("BG_RENDERED_SIZE_SLEEP_SECONDS", 0.05), 0.5))
    timeout = int(getattr(config, "request_timeout", 20) or 20)
    browser_executable_path = os.getenv("BG_CHROMIUM_EXECUTABLE_PATH", "").strip()

    logger.info(
        "开始 Birdy Grey 渲染 PDP 按 SKC/颜色补尺码：handles=%s workers=%s sleep=%s",
        len(missing_handles), workers, sleep_seconds,
    )

    chunks = [missing_handles[i::workers] for i in range(workers) if missing_handles[i::workers]]
    completed = 0
    with ThreadPoolExecutor(max_workers=len(chunks), thread_name_prefix="BGRenderedSize") as executor:
        future_map = {
            executor.submit(_fetch_bg_rendered_size_worker, chunk, timeout, sleep_seconds, browser_executable_path, idx): chunk
            for idx, chunk in enumerate(chunks, start=1)
        }
        for future in as_completed(future_map):
            chunk = future_map[future]
            try:
                partial = future.result()
            except Exception as exc:
                logger.warning("Birdy Grey 渲染 PDP 尺码 worker 异常: %s", exc)
                partial = {h: ("未获取", "未知") for h in chunk}
            existing.update(partial)
            completed += len(chunk)
            got = sum(1 for h in missing_handles if existing.get(h, ("未获取", "未知"))[0] not in {"", "未获取"})
            logger.info(
                "Birdy Grey 渲染尺码补抓进度: %s/%s 已获取=%s",
                min(completed, len(missing_handles)), len(missing_handles), got,
            )

    got = sum(1 for h in handles if existing.get(h, ("未获取", "未知"))[0] not in {"", "未获取"})
    logger.info(
        "Birdy Grey 渲染尺码补抓完成：成功获取=%s / handles=%s 未获取=%s",
        got, len(handles), len(handles) - got,
    )
    return existing


def _resolve_bg_size_cache_path(config: Config) -> str:
    """BG 尺码缓存路径。

    目的：避免每周重复打开 8000+ 个颜色 PDP。第一次补到的尺码会缓存，
    后续只补新增 / 缺失 / 缓存过期的 handle。
    """
    raw = os.getenv("BG_SIZE_CACHE_PATH", "runtime/bg_size_cache.json").strip() or "runtime/bg_size_cache.json"
    if os.path.isabs(raw):
        return raw
    return os.path.join(os.getcwd(), raw)


def _load_bg_size_cache(config: Config) -> dict[str, dict[str, Any]]:
    path = _resolve_bg_size_cache_path(config)
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            # 旧缓存里如果已经记录为“未获取”，不能当成有效缓存继续保留。
            # 否则像 Jessica / Brielle 这类实际有 Size values 的 PDP，会被旧缓存挡住，无法重新解析。
            cleaned: dict[str, dict[str, Any]] = {}
            for k, v in data.items():
                if not isinstance(v, dict):
                    continue
                cached_size = str(v.get("size") or "").strip()
                if not cached_size or cached_size == "未获取":
                    continue
                cleaned[str(k)] = v
            return cleaned
    except Exception as exc:
        logger.debug("Birdy Grey 尺码缓存读取失败: %s", exc)
    return {}


def _save_bg_size_cache(config: Config, cache: dict[str, dict[str, Any]]) -> None:
    path = _resolve_bg_size_cache_path(config)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("Birdy Grey 尺码缓存保存失败: %s", exc)


def _bg_cache_record_is_valid(record: dict[str, Any], ttl_days: int) -> bool:
    if not isinstance(record, dict):
        return False
    size_text = str(record.get("size") or "").strip()
    if not size_text or size_text == "未获取":
        return False
    if ttl_days <= 0:
        return True
    updated_at = str(record.get("updated_at") or "").strip()[:10]
    if not updated_at:
        return False
    try:
        updated_dt = datetime.strptime(updated_at, "%Y-%m-%d")
        return (datetime.now() - updated_dt).days <= ttl_days
    except Exception:
        return False


def _bg_cache_to_tuple(record: dict[str, Any]) -> tuple[str, str]:
    return str(record.get("size") or "未获取"), str(record.get("stock_type") or "未知")


def _build_bg_size_groups(
    products: list[dict[str, Any]],
    attribute_parser: AttributeParser,
) -> dict[str, list[str]]:
    """按款式分组 BG color handles。

    BG 列表是颜色/SKC 维度，直接逐个 PDP 会有 8000+ 请求。
    这里复用款式分组逻辑，把同款不同颜色聚合到一个 group。
    """
    groups: dict[str, list[str]] = {}
    seen_by_group: dict[str, set[str]] = {}

    for item in products:
        if not isinstance(item, dict):
            continue
        handle = str(item.get("handle", "") or "").strip()
        if not handle or "." in handle:
            continue
        group_key = _bg_style_group_key(item, attribute_parser)
        if not group_key:
            group_key = handle
        seen = seen_by_group.setdefault(group_key, set())
        if handle in seen:
            continue
        seen.add(handle)
        groups.setdefault(group_key, []).append(handle)

    return groups


def _pick_bg_size_group_representatives(
    products: list[dict[str, Any]],
    groups: dict[str, list[str]],
    attribute_parser: AttributeParser,
) -> list[tuple[str, str, list[str]]]:
    """为每个款式组选一个代表 handle。

    返回：[(group_key, representative_handle, group_handles)]。
    """
    item_by_handle: dict[str, dict[str, Any]] = {}
    for item in products:
        if not isinstance(item, dict):
            continue
        handle = str(item.get("handle", "") or "").strip()
        if handle and handle not in item_by_handle:
            item_by_handle[handle] = item

    reps: list[tuple[str, str, list[str]]] = []
    for group_key, handles in groups.items():
        if not handles:
            continue
        sorted_handles = sorted(
            handles,
            key=lambda h: _rank_bg_pdp_rep_candidate(item_by_handle.get(h, {"handle": h})),
        )
        reps.append((group_key, sorted_handles[0], handles))
    return reps


def _prefetch_bg_size_info_by_handle(
    config: Config,
    products: list[dict[str, Any]],
    attribute_parser: AttributeParser | None = None,
) -> dict[str, tuple[str, str]]:
    """更快的 BG 尺码补抓。

    当前策略：
    1. 不再全量打开 8582 个颜色/SKC PDP；
    2. 先读取 runtime/bg_size_cache.json，已有缓存直接复用；
    3. 按款式分组，每个款式只打开 1 个代表 PDP 获取尺码；
    4. 将代表 PDP 的尺码回填到同款不同颜色；
    5. 可选：对仍缺失的 Top N 颜色做精确 PDP 兜底。

    说明：
    - 这是“速度优先”的周报口径，能把 8000+ PDP 请求压到约 100~200 个款式请求；
    - 如果业务必须要每个颜色/SKC 的绝对精确库存尺码，可设置
      BG_SIZE_EXACT_SKC_FALLBACK_LIMIT 为较大值，但运行会很慢。
    """
    enabled = _env_bool("BG_ENABLE_SIZE_ENRICH", True)
    if not enabled:
        logger.info("已关闭 Birdy Grey 尺码补抓")
        return {}

    attribute_parser = attribute_parser or AttributeParser()

    handles: list[str] = []
    seen: set[str] = set()
    for item in products:
        if not isinstance(item, dict):
            continue
        handle = str(item.get("handle", "") or "").strip()
        if not handle or "." in handle or handle in seen:
            continue
        seen.add(handle)
        handles.append(handle)

    if not handles:
        return {}

    ttl_days = _env_int("BG_SIZE_CACHE_TTL_DAYS", 14)
    cache = _load_bg_size_cache(config)
    today = datetime.now().strftime("%Y-%m-%d")

    result: dict[str, tuple[str, str]] = {}
    for handle in handles:
        cached = cache.get(handle)
        if cached and _bg_cache_record_is_valid(cached, ttl_days):
            result[handle] = _bg_cache_to_tuple(cached)

    cached_count = len(result)
    logger.info(
        "Birdy Grey 尺码缓存命中：%s/%s ttl_days=%s",
        cached_count, len(handles), ttl_days,
    )

    missing_handles = [h for h in handles if h not in result]
    if not missing_handles:
        return result

    groups = _build_bg_size_groups(products, attribute_parser)
    reps = _pick_bg_size_group_representatives(products, groups, attribute_parser)

    # 只为仍存在缺失 handle 的款式组选代表 PDP。
    missing_set = set(missing_handles)
    rep_jobs: list[tuple[str, str, list[str]]] = []
    for group_key, rep_handle, group_handles in reps:
        unresolved = [h for h in group_handles if h in missing_set]
        if unresolved:
            rep_jobs.append((group_key, rep_handle, group_handles))

    max_groups = _env_int("BG_SIZE_STYLE_GROUP_MAX", 0)
    if max_groups > 0 and len(rep_jobs) > max_groups:
        logger.warning(
            "Birdy Grey 尺码款式组=%s 超过限制=%s，本次仅补前 %s 组；如需全量请调大/置空 BG_SIZE_STYLE_GROUP_MAX",
            len(rep_jobs), max_groups, max_groups,
        )
        rep_jobs = rep_jobs[:max_groups]

    representative_handles: list[str] = []
    seen_rep: set[str] = set()
    rep_to_group: dict[str, tuple[str, list[str]]] = {}
    for group_key, rep_handle, group_handles in rep_jobs:
        if not rep_handle or rep_handle in seen_rep:
            continue
        seen_rep.add(rep_handle)
        representative_handles.append(rep_handle)
        rep_to_group[rep_handle] = (group_key, group_handles)

    logger.info(
        "开始 Birdy Grey 款式级代表 PDP 尺码补抓：总颜色handles=%s 缺失=%s 款式组=%s 代表PDP=%s；不再全量打开每个颜色 PDP",
        len(handles), len(missing_handles), len(rep_jobs), len(representative_handles),
    )

    rep_size_map: dict[str, tuple[str, str]] = {}
    if representative_handles:
        rep_size_map = _prefetch_bg_rendered_size_info_by_handle(config, representative_handles, existing={})

    filled_by_group = 0
    for rep_handle, size_info in rep_size_map.items():
        size_text, stock_status = size_info
        if not size_text or size_text == "未获取":
            continue
        group_info = rep_to_group.get(rep_handle)
        if not group_info:
            continue
        _, group_handles = group_info
        for handle in group_handles:
            if handle in result:
                continue
            result[handle] = (size_text, stock_status)
            cache[handle] = {
                "size": size_text,
                "stock_type": stock_status,
                "source": f"style_rep:{rep_handle}",
                "updated_at": today,
            }
            filled_by_group += 1

    # 对仍缺失的颜色/SKC 做精确兜底。
    # 口径：
    # - BG_SIZE_EXACT_SKC_FALLBACK_LIMIT=0  ：不限制，补全部仍缺失的 SKC（最准确，但会更慢）
    # - BG_SIZE_EXACT_SKC_FALLBACK_LIMIT=N  ：只补前 N 个仍缺失的 SKC
    # - BG_SIZE_EXACT_SKC_FALLBACK_LIMIT=-1 ：关闭精确兜底
    exact_limit = _env_int("BG_SIZE_EXACT_SKC_FALLBACK_LIMIT", 0)
    exact_missing = [h for h in handles if result.get(h, ("未获取", "未知"))[0] == "未获取"]
    if exact_limit >= 0 and exact_missing:
        exact_targets = exact_missing if exact_limit == 0 else exact_missing[:exact_limit]
        logger.info(
            "开始 Birdy Grey 精确 SKC 尺码兜底：targets=%s/%s。该步骤会打开真实 PDP；如需关闭请设 BG_SIZE_EXACT_SKC_FALLBACK_LIMIT=-1。",
            len(exact_targets), len(exact_missing),
        )
        exact_map = _prefetch_bg_rendered_size_info_by_handle(config, exact_targets, existing={})
        for handle, size_info in exact_map.items():
            size_text, stock_status = size_info
            result[handle] = size_info
            if size_text and size_text != "未获取":
                cache[handle] = {
                    "size": size_text,
                    "stock_type": stock_status,
                    "source": "exact_skc_rendered_pdp",
                    "updated_at": today,
                }

    _save_bg_size_cache(config, cache)

    got = sum(1 for h in handles if result.get(h, ("未获取", "未知"))[0] not in {"", "未获取"})
    logger.info(
        "Birdy Grey 尺码补抓完成：总handles=%s 缓存命中=%s 款式回填=%s 最终已获取=%s 未获取=%s",
        len(handles), cached_count, filled_by_group, got, len(handles) - got,
    )
    return result

def _needs_pdp_attr_enrich(item: dict[str, Any], attribute_parser: AttributeParser) -> bool:
    tags = item.get("tags", []) or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    raw_title = str(item.get("title", "") or "").strip()
    initial_attrs = attribute_parser.parse({"title": raw_title, "body_html": "", "tags": tags})
    initial_attrs = _merge_common_attrs(item, initial_attrs, tags)

    fabric_name = _get_tag_val(tags, "fabric:") or str(item.get("mfield_attr_fabric", "") or "").strip() or initial_attrs.get("fabric", "")
    style = _get_tag_val(tags, "aesthetic:") or initial_attrs.get("aesthetic", "")
    length = _get_tag_val(tags, "length:") or initial_attrs.get("length", "")
    neckline = _get_tag_val(tags, "neckline:") or initial_attrs.get("neckline", "")

    # 不能只看字段是否为空。Sophisticated/glam/romantic/modernminimal 这类只是审美标签，
    # 不是 Product Details 里的结构化款式，必须继续补 PDP。
    if not (fabric_name and length and neckline):
        return True
    if not style or _is_low_quality_style_value(style):
        return True
    return False



def _slugify_bg(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def _normalize_style_group_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _clean_bg_title_for_style_group(raw_title: str, fabric_name: str) -> str:
    """生成用于款式去重的干净商品名，不包含颜色，但保留款式差异。"""
    title = re.sub(r"\s+", " ", str(raw_title or "").strip())
    if not title:
        return ""

    fabric_words = [
        fabric_name,
        "matte satin", "mattesatin", "stretch satin", "satin", "chiffon",
        "crepe", "mesh", "velvet", "tulle", "lace", "organza",
    ]
    fabric_words = [str(item or "").strip() for item in fabric_words if str(item or "").strip()]
    fabric_pattern = "|".join(re.escape(item) for item in sorted(fabric_words, key=len, reverse=True))
    if fabric_pattern:
        # Chris Dress in Chiffon Sage -> Chris Dress
        title = re.sub(
            rf"\s+in\s+(?:{fabric_pattern})(?:\s+[a-z][a-z\s-]*)?$",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()
        # Chris Dress - Chiffon Sage -> Chris Dress
        title = re.sub(
            rf"\s+-\s+(?:{fabric_pattern})(?:\s+[a-z][a-z\s-]*)?$",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()
    return title


def _infer_bg_raw_color(item: dict[str, Any], tags: list[Any]) -> str:
    return (
        str(item.get("color_name", "") or "").strip()
        or str(item.get("mfield_attr_color", "") or "").strip()
        or _get_tag_val(tags, "color:")
        or ""
    )


def _strip_known_color_suffix_from_handle(handle: str, raw_color: str, fabric_name: str) -> str:
    """兜底生成 handle 级款式 key，尽量去掉颜色后缀，避免同款多色重复补抓。"""
    handle_slug = _slugify_bg(handle)
    if not handle_slug:
        return ""

    candidates: list[str] = []
    for value in [raw_color, fabric_name]:
        slug = _slugify_bg(value)
        if slug:
            candidates.append(slug)

    # raw_color 可能已经是 "Chiffon Sage"，同时尝试去掉 fabric 后的色名。
    if raw_color and fabric_name:
        raw_key = _normalize_style_group_text(raw_color)
        fabric_key = _normalize_style_group_text(fabric_name)
        if raw_key.startswith(fabric_key + " "):
            candidates.append(_slugify_bg(raw_key[len(fabric_key):].strip()))

    common_color_slugs = [
        "white", "ivory", "cream", "champagne", "oyster", "stone", "taupe", "mocha",
        "brown", "chocolate", "espresso", "black", "navy", "blue", "mist-blue", "sky-blue",
        "dusty-blue", "pale-blue", "light-blue", "ice-blue", "sage", "sage-green", "olive",
        "green", "mint", "aqua", "teal", "rose", "dusty-rose", "blush", "blush-pink",
        "pink", "pale-pink", "coral-pink", "bubblegum-pink", "fondant-pink", "fuchsia",
        "fuchsia-pink", "orchid", "lavender", "lilac", "purple", "plum", "red", "burgundy",
        "wine", "yellow", "lemon", "lemon-sorbet", "butter", "buttercream", "mango",
        "orange", "floral", "sage-cream", "aqua-fuchsia", "white-blue-floral",
    ]
    candidates.extend(common_color_slugs)

    for slug in sorted({c for c in candidates if c}, key=len, reverse=True):
        if handle_slug.endswith("-" + slug):
            return handle_slug[: -(len(slug) + 1)].strip("-")

    return handle_slug


def _bg_style_group_key(
    item: dict[str, Any],
    attribute_parser: AttributeParser,
) -> str:
    """
    款式级 PDP 补抓 key。

    目标：同一款式不同颜色只抓一个代表 PDP；但不同面料/是否开衩不能混用属性。
    因此 key = 干净商品名 + 面料 + slit 标记；标题缺失时再用去色后的 handle。
    """
    tags = item.get("tags", []) or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    raw_title = str(item.get("title", "") or "").strip()
    handle = str(item.get("handle", "") or "").strip()

    initial_attrs = attribute_parser.parse({"title": raw_title, "body_html": "", "tags": tags})
    initial_attrs = _merge_common_attrs(item, initial_attrs, tags)

    fabric_name = (
        _get_tag_val(tags, "fabric:")
        or str(item.get("mfield_attr_fabric", "") or "").strip()
        or initial_attrs.get("fabric", "")
    )
    raw_color = _infer_bg_raw_color(item, tags)

    clean_title = _clean_bg_title_for_style_group(raw_title, fabric_name)
    title_key = _normalize_style_group_text(clean_title)
    fabric_key = _normalize_style_group_text(fabric_name)
    slit_key = "with slit" if "slit" in handle.lower() or "slit" in raw_title.lower() else ""

    if title_key:
        return "::".join(part for part in [title_key, fabric_key, slit_key] if part)

    handle_key = _strip_known_color_suffix_from_handle(handle, raw_color, fabric_name)
    return "::".join(part for part in [handle_key, fabric_key, slit_key] if part) or handle


def _rank_bg_pdp_rep_candidate(item: dict[str, Any]) -> tuple[int, int, int]:
    """优先选择更可能能打开、信息更完整的代表 PDP。"""
    handle = str(item.get("handle", "") or "").strip().lower()
    title = str(item.get("title", "") or "").strip()
    tags = item.get("tags", []) or []
    if isinstance(tags, str):
        tag_count = len([t for t in tags.split(",") if t.strip()])
    elif isinstance(tags, list):
        tag_count = len(tags)
    else:
        tag_count = 0

    # 颜色后缀越少越可能是基础 handle；title/tags 越完整越优先。
    handle_penalty = 0
    if re.search(r"-(blush|pink|sage|blue|green|black|white|ivory|champagne|rose|navy|olive|mango|espresso|lemon|butter|orchid|lavender|lilac|fuchsia|coral)(?:-|$)", handle):
        handle_penalty += 1
    if len(handle.split("-")) > 6:
        handle_penalty += 1

    return (handle_penalty, -len(title), -tag_count)


def _prefetch_bg_pdp_attribute_texts(
    config: Config,
    products: list[dict[str, Any]],
    attribute_parser: AttributeParser,
) -> dict[str, tuple[str, str]]:
    """
    按款式去重补抓 Birdy Grey PDP 详情文案。

    旧逻辑：属性缺失的每个颜色 handle 都请求一次 PDP，例如 3328 个颜色就请求 3328 次。
    新逻辑：先按「干净商品名 + 面料 + slit」分组，每组只抓少量代表 PDP，再把解析到的
    Product Details / Fabric Details 回填给同款不同颜色，避免重复请求。
    """
    enabled = _env_bool("BG_ENABLE_PDP_ATTR_ENRICH", True)
    if not enabled:
        logger.info("已关闭 Birdy Grey PDP 详情补抓")
        return {}

    # 商品详情描述是业务报表必需字段，不能只给“属性缺失”的款式补抓，
    # 否则很多商品会因为 tags 已有面料/长度等属性而跳过 PDP，导致详情为空或只有一部分。
    only_missing = _env_bool("BG_PDP_ATTR_ONLY_MISSING", False)
    max_groups = _env_int("BG_PDP_ATTR_MAX_STYLE_GROUPS", _env_int("BG_PDP_ATTR_MAX_PRODUCTS", 99999))
    max_rep_per_group = max(1, _env_int("BG_PDP_ATTR_MAX_REP_PER_STYLE", 4))
    max_fallback_per_group = max(0, _env_int("BG_PDP_ATTR_MAX_FALLBACK_PER_STYLE", 8))
    workers = max(1, _env_int("BG_PDP_ATTR_WORKERS", 4))
    sleep_seconds = max(0.0, _env_float("BG_PDP_ATTR_SLEEP_SECONDS", 0.12))
    timeout = int(getattr(config, "request_timeout", 30) or 30)

    groups: dict[str, list[dict[str, Any]]] = {}
    skipped_complete = 0
    skipped_no_handle = 0

    for item in products:
        if not isinstance(item, dict):
            continue
        handle = str(item.get("handle", "") or "").strip()
        if not handle or "." in handle:
            skipped_no_handle += 1
            continue
        if only_missing and not _needs_pdp_attr_enrich(item, attribute_parser):
            skipped_complete += 1
            continue

        group_key = _bg_style_group_key(item, attribute_parser)
        groups.setdefault(group_key, []).append(item)

    all_candidate_handles = sum(len(items) for items in groups.values())

    if max_groups > 0:
        # 大组优先：同款颜色越多，去重收益越高。
        sorted_items = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)
        groups = dict(sorted_items[:max_groups])

    if not groups:
        logger.info(
            "Birdy Grey PDP 款式去重补抓无候选：完整跳过=%s 无handle=%s",
            skipped_complete,
            skipped_no_handle,
        )
        return {}

    rep_jobs: list[tuple[str, list[str], list[str]]] = []
    for group_key, items in groups.items():
        seen_handles: set[str] = set()
        sorted_items = sorted(items, key=_rank_bg_pdp_rep_candidate)
        rep_handles: list[str] = []
        all_handles: list[str] = []
        for item in sorted_items:
            handle = str(item.get("handle", "") or "").strip()
            if not handle or handle in seen_handles or "." in handle:
                continue
            seen_handles.add(handle)
            all_handles.append(handle)
            if len(rep_handles) < max_rep_per_group:
                rep_handles.append(handle)
        if rep_handles and all_handles:
            rep_jobs.append((group_key, rep_handles, all_handles))

    logger.info(
        "开始 Birdy Grey PDP 款式去重详情补抓：候选颜色handles=%s 款式组=%s 代表PDP最多/组=%s 失败组fallback最多/组=%s workers=%s sleep=%s only_missing=%s 完整跳过=%s",
        all_candidate_handles,
        len(rep_jobs),
        max_rep_per_group,
        max_fallback_per_group,
        workers,
        sleep_seconds,
        only_missing,
        skipped_complete,
    )

    group_cache: dict[str, tuple[str, str]] = {}
    retry_queue = RetryQueue(site_key="birdygrey")

    def fetch_group(group_key: str, rep_handles: list[str], all_handles: list[str]) -> tuple[str, tuple[str, str], str]:
        if sleep_seconds:
            time.sleep(sleep_seconds)
        local_session = requests.Session()
        last_rep = ""
        last_retryable_error = ""
        seen: set[str] = set()
        candidate_handles: list[str] = []
        for handle in list(rep_handles) + list(all_handles):
            if not handle or handle in seen:
                continue
            seen.add(handle)
            candidate_handles.append(handle)
            if len(candidate_handles) >= max_rep_per_group + max_fallback_per_group:
                break

        best_result: tuple[str, str] = ("", "")
        best_handle = ""
        for rep_handle in candidate_handles:
            last_rep = rep_handle
            try:
                result = _fetch_bg_pdp_attr_text(local_session, rep_handle, timeout, raise_retryable=True)
            except RetryableTaskError as exc:
                last_retryable_error = str(exc)
                continue

            visible = result[0] or ""
            if visible and len(visible) > len(best_result[0] or ""):
                best_result = result
                best_handle = rep_handle

            # 优先返回完整 Product/Fabric Details；如果只是短截断文本，继续试同组其他颜色。
            if visible and not is_incomplete_detail_text(visible, min_chars=120, require_fabric_details=False):
                return group_key, result, rep_handle

        if best_result[0] or best_result[1]:
            return group_key, best_result, best_handle or last_rep
        if last_retryable_error:
            raise RetryableTaskError(last_retryable_error)
        return group_key, ("", ""), last_rep

    def queue_retry(group_key: str, rep_handles: list[str], error: str) -> None:
        def handler() -> tuple[str, str]:
            local_session = requests.Session()
            for rep_handle in rep_handles:
                result = _fetch_bg_pdp_attr_text(local_session, rep_handle, timeout, raise_retryable=True)
                if result[0]:
                    return result
            return "", ""

        def on_success(result: tuple[str, str]) -> None:
            group_cache[group_key] = result

        retry_queue.submit(
            task_type="bg_pdp_style_detail",
            identity_key=group_key,
            payload={"group_key": group_key, "rep_handles": rep_handles, "first_error": error},
            handler=handler,
            on_success=on_success,
        )

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="BGPDPStyleAttr") as executor:
        future_map = {
            executor.submit(fetch_group, group_key, rep_handles, all_handles): (group_key, rep_handles, all_handles)
            for group_key, rep_handles, all_handles in rep_jobs
        }

        for idx, future in enumerate(as_completed(future_map), start=1):
            group_key, rep_handles, _all_handles = future_map[future]
            try:
                result_group_key, result, used_rep = future.result()
                group_cache[result_group_key] = result
                if not result[0]:
                    logger.debug("Birdy Grey PDP 款式组补抓无前台详情: group=%s reps=%s", group_key, rep_handles)
            except Exception as exc:
                logger.debug("Birdy Grey PDP 款式组补抓异常，已进入 retry queue: group=%s reps=%s | %s", group_key, rep_handles, exc)
                group_cache[group_key] = ("", "")
                queue_retry(group_key, rep_handles, str(exc))

            if idx % 25 == 0 or idx == len(rep_jobs):
                success = sum(1 for visible, _jsonld in group_cache.values() if visible)
                logger.info(
                    "Birdy Grey PDP 款式去重补抓进度: 款式组 %s/%s 成功组=%s retry_pending=%s",
                    idx,
                    len(rep_jobs),
                    success,
                    retry_queue.pending_count(),
                )

    retry_queue.drain()

    # 展开回 handle cache：主流程仍按 handle 读取，不影响后续逻辑。
    handle_cache: dict[str, tuple[str, str]] = {}
    for group_key, _rep_handles, all_handles in rep_jobs:
        text_pair = group_cache.get(group_key, ("", ""))
        if not text_pair[0]:
            continue
        for handle in all_handles:
            handle_cache[handle] = text_pair

    logger.info(
        "Birdy Grey PDP 款式去重补抓完成：请求款式组=%s 成功组=%s 回填颜色handles=%s 原候选颜色handles=%s",
        len(group_cache),
        sum(1 for visible, _jsonld in group_cache.values() if visible),
        len(handle_cache),
        all_candidate_handles,
    )
    return handle_cache



def _normalize_bg_detail_signature_value(value: Any) -> str:
    text = unescape(str(value or "")).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _bg_detail_group_keys(record: ProductRecord) -> list[tuple[str, ...]]:
    """用于详情文案同款回填的分组 key。

    同一款式不同颜色的 Product Details / Fabric Details 基本一致；如果部分颜色 PDP
    请求失败，可以用同款式、同面料、同 slit 标记的已抓详情回填。
    """
    name = _normalize_bg_detail_signature_value(record.product_name)
    fabric = _normalize_bg_detail_signature_value(getattr(record, "fabric_name", ""))
    url = _normalize_bg_detail_signature_value(record.product_url)
    slit = "with_slit" if "slit" in name or "slit" in url else "no_slit"
    keys: list[tuple[str, ...]] = []
    if name and fabric:
        keys.append((name, fabric, slit))
    if name:
        keys.append((name, slit))
    return keys


def _backfill_bg_detail_text_from_records(records: list[ProductRecord]) -> None:
    """用同款已抓到的完整详情，回填空详情/过短详情。

    这是 BG 的兜底层：先尽量从 PDP 抓；如果某些颜色请求失败，但同款其他颜色已抓到
    完整 Product Details / Fabric Details，则回填，避免报表里大量空值。
    """
    if not records:
        return

    def good(text: Any) -> bool:
        return not is_incomplete_detail_text(text, min_chars=120, require_fabric_details=False)

    best_by_key: dict[tuple[str, ...], str] = {}
    for record in records:
        detail = str(getattr(record, "detail_text", "") or "").strip()
        if not good(detail):
            continue
        for key in _bg_detail_group_keys(record):
            old = best_by_key.get(key, "")
            if len(detail) > len(old):
                best_by_key[key] = detail

    before_missing = sum(1 for r in records if is_incomplete_detail_text(getattr(r, "detail_text", ""), min_chars=120, require_fabric_details=False))
    filled = 0
    for record in records:
        if not is_incomplete_detail_text(getattr(record, "detail_text", ""), min_chars=120, require_fabric_details=False):
            continue
        for key in _bg_detail_group_keys(record):
            detail = best_by_key.get(key, "")
            if detail:
                record.detail_text = detail
                filled += 1
                break

    after_missing = sum(1 for r in records if is_incomplete_detail_text(getattr(r, "detail_text", ""), min_chars=120, require_fabric_details=False))
    if before_missing or filled:
        logger.info(
            "BG 商品详情同款回填完成：回填前疑似缺失/过短=%s 回填=%s 回填后疑似缺失/过短=%s",
            before_missing,
            filled,
            after_missing,
        )




def _bg_handle_from_product_url(value: Any) -> str:
    """从 ProductRecord.product_url 中提取 BG handle。"""
    url = str(value or "").strip().rstrip("/")
    if not url:
        return ""
    handle = url.split("/")[-1].split("?")[0].strip()
    if "." in handle:
        return ""
    return handle


def _refetch_missing_bg_details_by_handle(config: Config, records: list[ProductRecord]) -> None:
    """对最终仍为空/过短的 BG 商品详情，按精确 handle 二次补抓。

    款式级去重补抓可以显著减少请求量，但 BG 的部分「With Slit / No Slit」切换款、
    多颜色变体或运营特殊页面可能没有被代表 PDP 命中。这里在导出前做最后一层兜底：
    只对详情仍缺失的记录，使用该记录自己的 product_url/handle 精确请求 PDP。
    """
    enabled = _env_bool("BG_DETAIL_EXACT_REFETCH_ENABLED", True)
    if not enabled or not records:
        return

    missing_records = [
        record for record in records
        if is_incomplete_detail_text(getattr(record, "detail_text", ""), min_chars=120, require_fabric_details=False)
    ]
    if not missing_records:
        return

    handle_to_records: dict[str, list[ProductRecord]] = {}
    for record in missing_records:
        handle = _bg_handle_from_product_url(getattr(record, "product_url", ""))
        if not handle:
            continue
        handle_to_records.setdefault(handle, []).append(record)

    if not handle_to_records:
        logger.info("BG 商品详情精确补抓跳过：缺失记录=%s 但无有效 handle", len(missing_records))
        return

    max_handles = _env_int("BG_DETAIL_EXACT_REFETCH_MAX_HANDLES", 2000)
    workers = max(1, _env_int("BG_DETAIL_EXACT_REFETCH_WORKERS", 6))
    sleep_seconds = max(0.0, _env_float("BG_DETAIL_EXACT_REFETCH_SLEEP_SECONDS", 0.08))
    timeout = int(getattr(config, "request_timeout", 30) or 30)

    handles = list(handle_to_records.keys())
    if max_handles > 0 and len(handles) > max_handles:
        handles = handles[:max_handles]

    logger.info(
        "开始 BG 商品详情精确补抓：缺失记录=%s 唯一handle=%s 本次最多补抓=%s workers=%s",
        len(missing_records),
        len(handle_to_records),
        len(handles),
        workers,
    )

    fetched: dict[str, str] = {}

    def fetch_one(handle: str) -> tuple[str, str]:
        if sleep_seconds:
            time.sleep(sleep_seconds)
        local_session = requests.Session()
        try:
            detail_text, _jsonld_text = _fetch_bg_pdp_attr_text(local_session, handle, timeout, raise_retryable=False)
        except Exception as exc:
            logger.debug("BG 商品详情精确补抓异常: handle=%s | %s", handle, exc)
            return handle, ""
        detail_text = collect_product_detail_text({"_pdp_detail_text": detail_text}, detail_text)
        if is_incomplete_detail_text(detail_text, min_chars=120, require_fabric_details=False):
            return handle, ""
        return handle, detail_text

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="BGDetailExact") as executor:
        future_map = {executor.submit(fetch_one, handle): handle for handle in handles}
        for idx, future in enumerate(as_completed(future_map), start=1):
            handle = future_map[future]
            try:
                result_handle, detail_text = future.result()
            except Exception as exc:
                logger.debug("BG 商品详情精确补抓 future 异常: handle=%s | %s", handle, exc)
                continue
            if detail_text:
                fetched[result_handle] = detail_text
            if idx % 50 == 0 or idx == len(handles):
                logger.info(
                    "BG 商品详情精确补抓进度：handle %s/%s 成功=%s",
                    idx,
                    len(handles),
                    len(fetched),
                )

    filled = 0
    for handle, detail_text in fetched.items():
        for record in handle_to_records.get(handle, []):
            if is_incomplete_detail_text(getattr(record, "detail_text", ""), min_chars=120, require_fabric_details=False):
                record.detail_text = detail_text
                filled += 1

    after_missing = sum(
        1 for record in records
        if is_incomplete_detail_text(getattr(record, "detail_text", ""), min_chars=120, require_fabric_details=False)
    )
    logger.info(
        "BG 商品详情精确补抓完成：成功handle=%s 回填记录=%s 剩余疑似缺失/过短=%s",
        len(fetched),
        filled,
        after_missing,
    )


def _refresh_bg_baseline_metadata_from_records(records: list[ProductRecord], baseline_mgr: BaselineManager) -> None:
    """回填详情后，同步刷新 baseline metadata，保证未来下架表也能带出详情。"""
    for record in records:
        handle = str(getattr(record, "product_url", "") or "").rstrip("/").split("/")[-1]
        product_key = _bg_stable_product_key(handle, record.product_name)
        key = baseline_mgr.make_key(product_key, record.color_name)
        if key in baseline_mgr.baseline:
            baseline_mgr.baseline[key]["metadata"] = record.to_metadata()




def _build_delisted_record(
    baseline_mgr: BaselineManager,
    key: str,
    info: dict[str, Any],
    scrape_time: str,
) -> ProductRecord:
    metadata = info.get("metadata", {}) if isinstance(info.get("metadata", {}), dict) else {}
    fallback_product_name, fallback_color_name = baseline_mgr.split_key(key)

    return _make_product_record(
        site_name=metadata.get("site_name", "Birdy Grey"),
        brand=metadata.get("brand", "Birdy Grey"),
        category=metadata.get("category", "Bridesmaid Dresses"),
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


def main() -> None:
    start_time = time.time()
    config = Config.load()
    _setup_logging(config)

    logger.info("========== Birdy Grey 自动监控引擎启动 ==========")

    request_handler = RequestHandler(config)
    collection_api = CollectionAPI(request_handler, config)
    attribute_parser = AttributeParser()
    data_exporter = DataExporter()

    baseline_path = getattr(config, "bg_baseline_path", "birdygrey_baseline.json")
    baseline_mgr = BaselineManager(baseline_path)
    output_dir = getattr(config, "output_dir", "output")
    report_prefix = "birdygrey_report_"

    is_initialization_phase = is_first_site_crawl(output_dir, report_prefix, baseline_mgr)
    current_dt = resolve_current_datetime()
    current_date = current_dt.strftime("%Y-%m-%d")
    current_time_full = current_dt.strftime("%Y-%m-%d %H:%M:%S")

    master_records: list[ProductRecord] = []
    active_keys: set[str] = set()
    new_color_count = 0
    restock_count = 0

    try:
        # BG 最终口径：
        # 1）商品池和排序只来自 bridesmaid-dresses?sort.ga_unique_purchases=desc 页面对应的
        #    SearchSpring 前台结果；
        # 2）不再抓取 new-arrivals / 额外 collection / 页面外颜色来扩充商品池；
        # 3）PDP 只用于补充白名单商品详情，不允许新增页面外商品。
        max_products = int(
            os.getenv(
                "BG_PAGE_MAX_PRODUCTS",
                str(getattr(config, "max_products_per_collection", 99999) or 99999),
            )
            or 99999
        )
        all_products = collection_api.fetch_collection_products(
            "bridesmaid-dresses",
            max_products,
        )

        if not all_products:
            logger.error("Birdy Grey 页面商品为空，跳过基线保存/下架对账，避免误判")
            return

        # 页面白名单：后续任何详情补充都只能作用于这些 handle。
        page_handles: list[str] = []
        page_handle_set: set[str] = set()
        page_products: list[dict[str, Any]] = []
        for item in all_products:
            if not isinstance(item, dict):
                continue
            handle = str(item.get("handle", "") or "").strip()
            if not handle or handle in page_handle_set:
                continue
            page_handle_set.add(handle)
            page_handles.append(handle)
            item = dict(item)
            item["_collection_order"] = len(page_products) + 1
            page_products.append(item)

        all_products = page_products
        logger.info(
            "Birdy Grey 页面展示商品白名单=%s source=%s，后续详情补充不允许新增页面外商品",
            len(page_handles),
            BG_SOURCE_PAGE_URL,
        )

        pdp_attr_cache = _prefetch_bg_pdp_attribute_texts(
            config=config,
            products=all_products,
            attribute_parser=attribute_parser,
        )
        bg_size_cache = _prefetch_bg_size_info_by_handle(
            config=config,
            products=all_products,
            attribute_parser=attribute_parser,
        )

        for current_rank, item in enumerate(all_products, start=1):
            if not isinstance(item, dict):
                continue
            item["_collection_order"] = item.get("_collection_order") or current_rank
            handle = str(item.get("handle", "") or "").strip()
            pdp_detail_text, pdp_jsonld_text = pdp_attr_cache.get(handle, ("", ""))
            if pdp_detail_text or pdp_jsonld_text:
                # 不覆盖 SearchSpring 原字段，只附加 PDP 文案给属性解析器使用。
                item = dict(item)
                item["_pdp_detail_text"] = pdp_detail_text
                item["_pdp_jsonld_text"] = pdp_jsonld_text

            tags = item.get("tags", []) or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            raw_title = str(item.get("title", "") or "").strip()

            detail_text_for_attrs = " ".join(
                [
                    str(item.get("_pdp_detail_text", "") or ""),
                    str(item.get("_pdp_jsonld_text", "") or ""),
                    str(item.get("body_html", "") or ""),
                    str(item.get("description", "") or ""),
                    raw_title,
                ]
            )

            attrs = attribute_parser.parse(
                {
                    "title": raw_title,
                    "body_html": item.get("_pdp_detail_text", "") or item.get("body_html", ""),
                    "description": item.get("description", ""),
                    "tags": tags,
                }
            )
            attrs = _merge_common_attrs(item, attrs, tags)
            detail_attrs = _extract_bg_attrs_from_detail_text(detail_text_for_attrs)

            fabric_name = _normalize_bg_attr_display(
                _get_tag_val(tags, "fabric:")
                or str(item.get("mfield_attr_fabric", "") or "").strip()
                or detail_attrs.get("fabric_name", "")
                or attrs.get("fabric", ""),
                "fabric",
            )

            product_name = _smart_title(raw_title, handle, fabric_name)

            images = item.get("images", []) or []
            main_image_url = (
                images[0].get("src", "")
                if images and isinstance(images[0], dict)
                else ""
            )

            raw_price = _parse_price(item.get("price"))
            raw_compare = _parse_price(item.get("compare_at_price"))

            final_original_price = raw_compare if raw_compare > raw_price else raw_price
            discount_type = "打折" if final_original_price > raw_price else "无折扣"

            raw_color_name = (
                str(item.get("color_name", "") or "").strip()
                or str(item.get("mfield_attr_color", "") or "").strip()
                or _get_tag_val(tags, "color:")
                or "Default"
            )
            color_name = _normalize_color_name(raw_color_name, fabric_name)

            length_value = _pick_first_display(
                "length",
                detail_attrs.get("length", ""),
                _get_tag_val(tags, "length:"),
                attrs.get("length", ""),
            )
            if not length_value:
                length_value = _bg_known_length_fallback(
                    product_name=product_name,
                    handle=handle,
                    detail_text=detail_text_for_attrs,
                    fabric=fabric_name,
                )
            neckline_value = _pick_first_display(
                "neckline",
                detail_attrs.get("neckline", ""),
                _get_tag_val(tags, "neckline:"),
                attrs.get("neckline", ""),
            )
            if not neckline_value:
                neckline_value = _bg_known_neckline_fallback(
                    product_name=product_name,
                    handle=handle,
                    detail_text=detail_text_for_attrs,
                )

            style_value = _pick_structural_style(
                detail_attrs.get("aesthetic_tag", ""),
                attrs.get("aesthetic", ""),
                _get_tag_val(tags, "aesthetic:"),
            )
            if not style_value:
                style_value = _bg_known_style_fallback(
                    product_name=product_name,
                    handle=handle,
                    detail_text=detail_text_for_attrs,
                    neckline=neckline_value,
                    length=length_value,
                    fabric=fabric_name,
                )
            if not length_value:
                length_value = _bg_known_length_fallback(
                    product_name=product_name,
                    handle=handle,
                    detail_text=detail_text_for_attrs,
                    fabric=fabric_name,
                    style=style_value,
                )

            size_text, size_stock_status = bg_size_cache.get(handle, ("未获取", "未知"))
            # 「定制/现货」原字段原本承载 Ready-to-Ship / Made-to-Order 信息。
            # 这里仅在能明确判断缺货时写「缺货」；未获取尺码时不误写缺货。
            stock_type_value = "现货" if item.get("is_ready_to_ship") else "定制"
            if size_stock_status == "缺货":
                stock_type_value = "缺货"

            temp_record = _make_product_record(
                site_name="Birdy Grey",
                brand="Birdy Grey",
                category="Bridesmaid Dresses",
                product_url=f"https://www.birdygrey.com/products/{handle}" if handle else "",
                product_name=product_name,
                style_label=product_name,
                color_name=color_name,
                size=size_text,
                main_image_url=main_image_url,
                original_price=_format_price(final_original_price),
                sale_price=_format_price(raw_price),
                discount_type=discount_type,
                stock_type=stock_type_value,
                # 商品详情描述只输出前台 Product Details / Fabric Details，
                # 不把 JSON-LD schema、Offer、尺码价格库存等结构化数据写入报表。
                detail_text=collect_product_detail_text(item, item.get("_pdp_detail_text", "")),
                fabric_name=fabric_name,
                aesthetic_tag=style_value,
                length=length_value,
                neckline=neckline_value,
                scrape_time=current_time_full,
                release_date="",
                is_new_color="否",
                is_official_new="否",
                status="Active",
            )

            # BG 的商品标题可能因运营文案调整而变化。
            # 基线与周度新增颜色统一优先使用 handle + color_name 做 key，
            # 避免 product_name 变化导致同一个商品颜色被误判为“新增颜色”。
            product_key_for_baseline = _bg_stable_product_key(handle, product_name)

            baseline_key = baseline_mgr.make_key(product_key_for_baseline, color_name)
            report_metadata = apply_ranking_context(
                temp_record,
                baseline_mgr,
                baseline_key,
                product_key=product_key_for_baseline,
                current_rank=item.get("_collection_order") or current_rank,
                source_page_url=BG_SOURCE_PAGE_URL,
                current_date=current_date,
            )

            is_new_color, release_date = baseline_mgr.check_and_update(
                product_key_for_baseline,
                color_name,
                current_date,
                metadata=report_metadata,
            )

            sync_change_context_from_metadata(temp_record, report_metadata)
            temp_record.release_date = release_date
            temp_record.is_new_color = "基线写入" if is_initialization_phase else is_new_color

            mark_relisted_after_delisted(temp_record, baseline_mgr, baseline_key)

            if baseline_key in baseline_mgr.baseline:
                baseline_mgr.baseline[baseline_key]["metadata"] = temp_record.to_metadata()

            if not is_initialization_phase:
                if is_new_color == "是":
                    new_color_count += 1
                elif is_new_color == "老款补货":
                    restock_count += 1

            active_keys.add(baseline_key)
            master_records.append(temp_record)

        _backfill_bg_detail_text_from_records(master_records)
        _refetch_missing_bg_details_by_handle(config, master_records)
        _backfill_bg_detail_text_from_records(master_records)
        _refresh_bg_baseline_metadata_from_records(master_records, baseline_mgr)

        delisted_records = mark_and_build_delisted_records(
            baseline_mgr=baseline_mgr,
            active_keys=active_keys,
            current_date=current_date,
            current_time_full=current_time_full,
            build_delisted_record=_build_delisted_record,
        )
        delisted_count = len(delisted_records)

        baseline_mgr.save_baseline()

        sheet_name = getattr(config, "bg_sheet_name", "BG_伴娘服总表")
        output_dir = getattr(config, "output_dir", "output")

        report_sheets = build_report_sheets(
            full_sheet_name=sheet_name,
            records=master_records,
            delisted_records=delisted_records,
            is_initialization_phase=is_initialization_phase,
            columns_l2=COLUMNS_L2,
        )

        filepath = data_exporter.export_multiple_sheets(
            report_sheets,
            output_dir,
            prefix=report_prefix,
            header_l1=HEADER_L1_CONFIG,
            columns_l2=COLUMNS_L2,
        )
        cleanup_previous_site_reports(output_dir, report_prefix, filepath)

        sheet_id = getattr(config, "gsheet_spreadsheet_id", "") or os.getenv(
            "GSHEET_SPREADSHEET_ID",
            "",
        )
        cred_json = getattr(config, "gsheet_credentials_json", "") or os.getenv(
            "GSHEET_CREDENTIALS_JSON",
            "credentials.json",
        )

        if GSheetSync and sheet_id and cred_json:
            try:
                gsync = GSheetSync(sheet_id, cred_json)
                gsync.sync_competitor_report(sheet_name, report_sheets)
            except Exception as exc:
                logger.error("同步 Google Sheets 失败: %s", exc, exc_info=True)
        else:
            logger.info("未配置 Google Sheets 或未安装依赖，跳过同步")

        elapsed = time.time() - start_time

        logger.info(
            "✅ Birdy Grey 完成 | 本次抓取=%d | 新色=%d | 老款补货=%d | 本次下架=%d | 文件=%s | 耗时=%.2fs",
            len(master_records),
            new_color_count,
            restock_count,
            delisted_count,
            filepath,
            elapsed,
        )

    except Exception:
        logger.critical("Birdy Grey 执行发生异常", exc_info=True)
        raise


def run_bg() -> None:
    main()


if __name__ == "__main__":
    main()
