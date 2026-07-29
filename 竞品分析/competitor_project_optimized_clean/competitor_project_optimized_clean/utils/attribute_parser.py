"""商品属性解析兼容模块。 

用途：
1. 保留旧代码的 AttributeParser.parse(product_data) 调用方式。
2. 优先复用新的公共解析器 utils.attribute_extractor.extract_attributes，避免多套关键词逻辑冲突。
3. 如果公共解析器不存在，也提供本地兜底关键词解析。

返回字段保持旧版兼容：
- fabric
- style
- length
- neckline
- aesthetic
- silhouette
"""

from __future__ import annotations

import logging
import re
from html import unescape
from typing import Any

logger = logging.getLogger(__name__)

try:
    # 新公共模块：建议后续所有站点统一走这里
    from utils.attribute_extractor import extract_attributes as _common_extract_attributes
except Exception:  # pragma: no cover - 兼容老项目未新增 attribute_extractor.py 的情况
    _common_extract_attributes = None  # type: ignore[assignment]


# 兜底关键词：公共解析器不可用时使用；顺序从更具体到更通用
FABRIC_KEYWORDS = [
    "Stretch Charmeuse", "Charmeuse", "Crepe Back Satin", "Stretch Crepe",
    "Sculpting Satin", "Matte Satin", "Stretch Satin", "Cotton Sateen",
    "Mikado", "Satin", "Chiffon", "Velvet", "Tulle", "Crepe", "Mesh",
    "Lace", "Organza", "Sequin", "Sequins", "Jersey", "Georgette",
    "Jacquard", "Taffeta", "Twill", "Crepon", "Luxe", "Slinky", "Scuba",
    "Knit", "Ribbed", "Sheer",
]

STYLE_KEYWORDS = [
    "Fit and Flare", "Fit-and-Flare", "A-Line", "A Line", "Ball Gown",
    "Ballgown", "Full Skirt", "Mermaid", "Trumpet", "Sheath", "Empire",
    "Column", "Wrap", "Slip", "Jumpsuit", "Pantsuit", "Corset", "Bustier",
    "Pleated", "Ruched", "Ruching", "Ruffle", "Ruffled", "Draped", "Drape",
    "Bodycon", "Fishtail", "Backless", "Cape", "Multiway", "Asymmetric",
    "Asymmetrical", "Twist", "Tie", "Cut Out", "Cut-Out", "Embellished",
    "Feather", "Bow", "Split", "Thigh Split", "Gathered", "Drop Waist",
    "Drop-Waist", "Basque Waist", "Flowy",
]

LENGTH_KEYWORDS = [
    "Floor-Length", "Floor Length", "Floorlength", "Floor", "Maxi", "Long",
    "Ankle-Length", "Ankle Length", "Midi", "Mini", "Short", "Knee-Length",
    "Knee Length", "Tea-Length", "Tea Length", "High-Low", "High Low",
]

NECKLINE_KEYWORDS = [
    "Inverted Sweetheart Neckline", "Inverted Sweetheart", "Inverted Neckline",
    "Sweetheart Neckline", "Sweetheart", "Off-the-Shoulder", "Off the Shoulder",
    "Off-Shoulder", "Off Shoulder", "One-Shoulder", "One Shoulder",
    "High-Neck", "High Neck", "Square Neckline", "Square Neck", "Cowl Neck",
    "Cowl Front", "Cowl Back", "Cowl", "Scoop Neck", "Scoop", "Boat Neck",
    "Bateau", "V-Neck", "V Neck", "Deep V", "Plunge", "Strapless",
    "Halter Neck", "Halter", "Spaghetti Strap", "Spaghetti Straps",
    "Adjustable Straps", "Cami Strap", "Cami", "Tank", "Sleeveless",
    "Flutter Sleeve", "Long Sleeve", "Short Sleeve", "Cap Sleeve", "Cold Shoulder",
    "Illusion", "Straight Neckline", "Straight Neck", "Surplice", "Bustier Top",
    "Corset Bodice", "Bow Shoulder", "Crisscross Back", "Tie Back", "Back Tie",
    "Strappy",
]

AESTHETIC_KEYWORDS = [
    "Classic", "Modern", "Romantic", "Bohemian", "Boho", "Vintage", "Minimalist",
    "Elegant", "Rustic", "Glamorous", "Sophisticated", "Timeless", "Statement",
]

SILHOUETTE_KEYWORDS = [
    "Fit and Flare", "Fit-and-Flare", "A-Line", "A Line", "Ball Gown", "Ballgown",
    "Sheath", "Mermaid", "Trumpet", "Empire", "Column", "Fitted", "Flowy",
    "Structured", "Relaxed", "Tailored", "Draped", "Slip", "Wrap", "Jumpsuit",
]

NORMALIZE_MAP = {
    "Fit-and-Flare": "Fit and Flare",
    "A Line": "A-Line",
    "Ballgown": "Ball Gown",
    "Floor Length": "Floor-Length",
    "Floorlength": "Floor-Length",
    "Floor": "Floor-Length",
    "Maxi": "Floor-Length",
    "Ankle Length": "Ankle-Length",
    "Knee Length": "Knee-Length",
    "Tea Length": "Tea-Length",
    "High Low": "High-Low",
    "Off the Shoulder": "Off-the-Shoulder",
    "Off Shoulder": "Off-the-Shoulder",
    "Off-Shoulder": "Off-the-Shoulder",
    "One Shoulder": "One-Shoulder",
    "High Neck": "High-Neck",
    "V Neck": "V-Neck",
    "Cowl": "Cowl Neck",
    "Scoop": "Scoop Neck",
    "Halter Neck": "Halter",
    "Spaghetti Straps": "Spaghetti Strap",
    "Adjustable Straps": "Spaghetti Strap",
    "Sequins": "Sequin",
    "Boho": "Bohemian",
}

TEXT_KEYS = [
    "title", "product_name", "name", "handle", "body_html", "description",
    "descriptionHtml", "product_description", "short_description", "long_description",
    "product_details", "details", "features", "fabric_details", "tags", "product_type",
    "productType", "vendor", "style", "silhouette", "length", "neckline", "material",
    "fabric", "_pdp_detail_text", "_pdp_jsonld_text",
]

BLOCK_KEY_PARTS = {"image", "img", "thumb", "url", "href", "price", "sku", "id", "pid"}


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _clean_text(value: Any) -> str:
    text = unescape(_safe_str(value))
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_text(value: Any) -> str:
    text = _clean_text(value).lower()
    text = text.replace("–", "-").replace("—", "-").replace("&", " and ")
    text = re.sub(r"[\-_/]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_value(value: str) -> str:
    return NORMALIZE_MAP.get(value, value)


def _value_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(_value_to_text(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_value_to_text(item) for item in value)
    return _clean_text(value)


def _collect_text(product_data: dict[str, Any]) -> str:
    chunks: list[str] = []

    for key in TEXT_KEYS:
        if key in product_data:
            text = _value_to_text(product_data.get(key))
            if text:
                chunks.append(text)

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, sub_value in value.items():
                key_text = _safe_str(key).lower()
                if any(block in key_text for block in BLOCK_KEY_PARTS):
                    continue

                if any(
                    token in key_text
                    for token in [
                        "facet", "attribute", "detail", "description", "feature",
                        "fabric", "material", "length", "silhouette", "neckline",
                        "sleeve", "style", "tag", "product_type", "type",
                    ]
                ):
                    text = _value_to_text(sub_value)
                    if text:
                        chunks.append(text)

                walk(sub_value)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(product_data)
    return " ".join(chunks)


def _find_keyword(text: str, keywords: list[str]) -> str:
    normalized_text = f" {_normalize_text(text)} "
    for keyword in sorted(keywords, key=len, reverse=True):
        nk = _normalize_text(keyword)
        if not nk:
            continue
        if f" {nk} " in normalized_text:
            return _normalize_value(keyword)
    return ""


def _should_default_floor_length(product_data: dict[str, Any], text: str) -> bool:
    title = _normalize_text(
        product_data.get("title") or product_data.get("product_name") or product_data.get("name")
    )
    if not any(word in title for word in ["dress", "gown"]):
        return False

    normalized_text = _normalize_text(text)
    blocked_terms = [
        "mini", "midi", "short", "knee length", "tea length", "high low",
        "ankle length", "jumpsuit", "pantsuit", "separates",
    ]
    return not any(term in normalized_text for term in blocked_terms)


class AttributeParser:
    """从商品名称、描述、标签、PDP 文案中解析结构化属性。"""

    def __init__(self, *, default_floor_length: bool = False) -> None:
        # 默认不强制 Floor-Length，避免 BG/SS 等站点误填。
        # DB 需要默认 Floor-Length 时，建议直接用 utils.attribute_extractor.extract_attributes(default_floor_length=True)。
        self.default_floor_length = default_floor_length

    def parse(self, product_data: dict[str, Any]) -> dict[str, str]:
        """兼容旧版返回字段，不破坏现有 main_bg.py 调用。"""
        if not isinstance(product_data, dict):
            product_data = {"title": _safe_str(product_data)}

        if _common_extract_attributes is not None:
            try:
                common = _common_extract_attributes(
                    product_data,
                    default_floor_length=self.default_floor_length,
                )
                style = _safe_str(common.get("aesthetic_tag"))
                return {
                    "fabric": _safe_str(common.get("fabric_name")),
                    "style": style,
                    "length": _safe_str(common.get("length")),
                    "neckline": _safe_str(common.get("neckline")),
                    # 旧字段保留；公共解析器没有单独 aesthetic 时保持空，不用 style 冒充美学标签。
                    "aesthetic": self._parse_aesthetic(product_data),
                    "silhouette": self._parse_silhouette(product_data) or style,
                }
            except Exception as exc:
                logger.debug("公共属性解析器调用失败，使用 attribute_parser 本地兜底: %s", exc)

        text = _collect_text(product_data)
        fabric = _find_keyword(text, FABRIC_KEYWORDS)
        style = _find_keyword(text, STYLE_KEYWORDS)
        length = _find_keyword(text, LENGTH_KEYWORDS)
        neckline = _find_keyword(text, NECKLINE_KEYWORDS)

        if not length and self.default_floor_length and _should_default_floor_length(product_data, text):
            length = "Floor-Length"

        aesthetic = _find_keyword(text, AESTHETIC_KEYWORDS)
        silhouette = _find_keyword(text, SILHOUETTE_KEYWORDS) or style

        return {
            "fabric": fabric,
            "style": style,
            "length": length,
            "neckline": neckline,
            "aesthetic": aesthetic,
            "silhouette": silhouette,
        }

    def _parse_aesthetic(self, product_data: dict[str, Any]) -> str:
        return _find_keyword(_collect_text(product_data), AESTHETIC_KEYWORDS)

    def _parse_silhouette(self, product_data: dict[str, Any]) -> str:
        return _find_keyword(_collect_text(product_data), SILHOUETTE_KEYWORDS)

    # 下面这些方法保留给旧代码/测试直接调用，避免破坏兼容性。
    def _normalize_tags(self, tags: Any) -> list[str]:
        if isinstance(tags, str):
            return [t.strip() for t in tags.split(",") if t.strip()]
        if isinstance(tags, list):
            return [str(t).strip() for t in tags if str(t).strip()]
        return [str(tags).strip()] if str(tags).strip() else []

    def _normalize_value(self, value: str) -> str:
        return _normalize_value(value)

    def _find_keyword(self, keywords: list[str], *texts: str) -> str:
        return _find_keyword(" ".join(texts), keywords)

    def _tags_text(self, tags: list[str]) -> str:
        return " ".join(tags)

    def _parse_fabric(self, title: str, description: str, tags: list[str]) -> str:
        return self._find_keyword(FABRIC_KEYWORDS, title, description, self._tags_text(tags))

    def _parse_style(self, title: str, description: str, tags: list[str]) -> str:
        return self._find_keyword(STYLE_KEYWORDS, title, description, self._tags_text(tags))

    def _parse_length(self, title: str, description: str, tags: list[str]) -> str:
        return self._find_keyword(LENGTH_KEYWORDS, title, description, self._tags_text(tags))

    def _parse_neckline(self, title: str, description: str, tags: list[str]) -> str:
        return self._find_keyword(NECKLINE_KEYWORDS, title, description, self._tags_text(tags))
