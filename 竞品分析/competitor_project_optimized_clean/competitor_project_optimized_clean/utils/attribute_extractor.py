"""公共商品属性解析模块。 

统一从 title / handle / tags / description / body_html / PDP detail text 等内容中解析：
- fabric_name: 面料
- aesthetic_tag: 风格/廓形/设计特征
- length: 长度
- neckline: 上半身款式/领型/肩带/袖型

各站点可直接调用 extract_attributes(source)。source 可以是 dict 或字符串。
"""

from __future__ import annotations

import logging
import re
from html import unescape
from typing import Any

logger = logging.getLogger(__name__)

FABRIC_KEYWORDS = [
    "Luxurious Smooth Satin", "Smooth Satin", "Soft Sheen Satin",
    "Luxurious Satin", "Silky Satin", "Hammered Satin", "Bias Cut Satin", "Viscose Rayon", "Viscose", "Rayon",
    "Stretch Charmeuse", "Charmeuse", "Crepe Back Satin", "Stretch Crepe",
    "Sculpting Satin", "Matte Satin", "Shiny Satin", "Stretch Satin", "Cotton Sateen",
    "Luxe Stretch Knit", "Luxe Knit", "Stretch Knit", "Mikado",
    "Plissé Fabric", "Plisse Fabric", "Plissé", "Plisse", "Satin", "Chiffon", "Velvet", "Tulle", "Crepe", "Mesh",
    "Lace", "Organza", "Sequin", "Sequins", "Jersey", "Georgette",
    "Jacquard", "Taffeta", "Twill", "Crepon", "Woven Fabric", "Woven", "Luxe", "Slinky", "Scuba",
    "Knit", "Ribbed", "Sheer",
]

STYLE_KEYWORDS = [
    "Twist Open Back", "Open Back", "Plunge Neckline", "Concealed Side Zip",
    "Cowl Wrap Neck", "Cowl Front", "Cowl Back", "Wrap Tie", "Self Tie",
    "Drape Detail", "Knot Front", "Gathered Bust", "Twist Bust", "Statement Shoulder",
    "Straight Flowy Silhouette", "Flowy Silhouette", "Straight Silhouette", "Bias Cut", "Elastic Back",
    "Bows on the Shoulders", "Convertible Bows", "Bow Shoulder", "Shoulder Bows",
    "Fluted Skirt", "Fluted",
    "Bustier Top Ruffle Tiered Dress", "Bustier Top Ruffle Tiered",
    "Bustier Ruffle Tiered Dress", "Bustier Ruffle Tiered",
    "Ruffle Tiered Dress", "Ruffle Tiered", "Tiered Dress", "Tiered",
    "Ankle-Length A-Line Tiered Silhouette", "Tea-Length A-Line Dress", "A-Line Dress", "A-Line Tiered Silhouette", "A-Line Tiered", "Tiered Silhouette", "Fully-Lined A-Line Skirt",
    "Jacquard Floral Fabric", "Jacquard Floral", "Floral Jacquard", "Floral Fabric", "Floral",
    "Fit and Flare", "Fit-and-Flare", "A-Line", "A Line", "Ball Gown",
    "Ballgown", "Full Skirt", "Mermaid", "Trumpet", "Sheath", "Empire",
    "Column", "Column Silhouette", "Column Skirt", "Sweeping Column Skirt", "Sweeping Skirt",
    "Wrap", "Slip", "Jumpsuit", "Pantsuit", "Corset", "Built-In Boning", "Boning",
    "Front Streamers", "Extra Long Front Streamers", "Multiway", "Convertible", "Diagonal Seam",
    "Bustier", "Pleated", "Ruched", "Ruching", "Ruffle", "Ruffled",
    "Draped", "Drape", "Bodycon", "Fishtail", "Backless", "Open Back", "Cut-Out Back", "Cape",
    "Multiway", "Asymmetric", "Asymmetrical", "Twist", "Tie", "Cut Out",
    "Cut-Out", "Detachable Sleeves", "Hidden Pockets", "Side Pockets", "Fitted Waist", "Loops", "Waist Loops",
    "Embellished", "Feather", "Bow", "Split", "Front Slit", "Side Slit", "Thigh Split",
    "Gathered", "Drop Waist", "Drop-Waist", "Basque Waist", "Flowy", "Fully Lined",
]

LENGTH_KEYWORDS = [
    "Floor-Length", "Floor Length", "Floorlength", "Floor", "Floor-Sweeping", "Floor Sweeping",
    "Full-Length", "Full Length", "Gown", "Maxi", "Long",
    "Ankle-Length", "Ankle Length", "Midi", "Mini", "Short", "Knee-Length",
    "Knee Length", "Tea-Length", "Tea Length", "High-Low", "High Low",
]

NECKLINE_KEYWORDS = [
    "Plunge Neckline", "Plunging Neckline", "Deep Plunge Neckline",
    "Cowl Wrap Neck", "Cowl Front Neck", "Cowl Back Neck",
    "Spaghetti Style Adjustable Strap", "Adjustable Strap",
    "Soft V-Neckline", "Soft V Neckline", "Elastic Back", "Cupped Bust",
    "Bows on the Shoulders", "Bow Shoulder", "Shoulder Bows",
    "Inverted Sweetheart Neckline", "Inverted Sweetheart", "Inverted Neckline",
    "Sweetheart Neckline", "Sweetheart", "Off-the-Shoulder", "Off the Shoulder",
    "Off-Shoulder", "Off Shoulder", "One-Shoulder", "One Shoulder",
    "High-Neck", "High Neck", "Boat Neckline", "Boat Neck", "Bateau", "Square Neckline", "Square Neck", "Cowl Neck",
    "Cowl Front", "Cowl Back", "Cowl", "Scoop Neck", "Boat Neck", "Bateau",
    "Deep Plunging V-Neckline", "Deep Plunging V Neckline", "Plunging V-Neckline", "Plunging V Neckline", "V-Neckline", "V Neckline", "V-Neck", "V Neck", "Deep V", "Plunge", "Strapless", "Halter Neck",
    "Cross Front Halter", "Halter", "Spaghetti Strap", "Spaghetti Straps", "Thin Straps", "Fine Straps", "Adjustable Straps",
    "Shoulder Tie Straps", "Tie Straps", "Wide Shoulder Straps", "Shoulder Straps", "Cami Strap", "Cami", "Tank", "Sleeveless", "Flutter Sleeve", "Long Sleeve",
    "Short Sleeve", "Long Sleeves", "Long Sleeve", "Cap Sleeve", "Cold Shoulder", "Illusion", "Straight Neckline",
    "Straight Neck", "Surplice", "Bustier Top", "Corset Bodice", "Bow Shoulder",
    "Crisscross Back", "Tie Back", "Back Tie", "Strappy",
]

NORMALIZE_MAP = {
    "Luxurious Smooth Satin": "Satin",
    "Smooth Satin": "Satin",
    "Soft Sheen Satin": "Satin",
    "Twist Open Back": "Twist Open Back",
    "Plunge Neckline": "Plunge",
    "Plunging Neckline": "Plunge",
    "Deep Plunge Neckline": "Plunge",
    "Cowl Front Neck": "Cowl Front",
    "Cowl Back Neck": "Cowl Back",
    "Spaghetti Style Adjustable Strap": "Spaghetti Strap",
    "Adjustable Strap": "Adjustable Strap",
    "Concealed Side Zip": "Concealed Side Zip",
    "Bows on the Shoulders": "Bow Shoulder",
    "Convertible Bows": "Bow Shoulder",
    "Shoulder Bows": "Bow Shoulder",
    "Fluted": "Fluted Skirt",
    "Bustier Top Ruffle Tiered Dress": "Bustier Ruffle Tiered",
    "Bustier Top Ruffle Tiered": "Bustier Ruffle Tiered",
    "Bustier Ruffle Tiered Dress": "Bustier Ruffle Tiered",
    "Ruffle Tiered Dress": "Ruffle Tiered",
    "Ankle-Length A-Line Tiered Silhouette": "A-Line / Tiered",
    "A-Line Tiered Silhouette": "A-Line / Tiered",
    "A-Line Tiered": "A-Line / Tiered",
    "Tiered Silhouette": "Tiered",
    "Fully-Lined A-Line Skirt": "A-Line",
    "Tea-Length A-Line Dress": "A-Line",
    "A-Line Dress": "A-Line",
    "Jacquard Floral Fabric": "Jacquard Floral",
    "Floral Jacquard": "Jacquard Floral",
    "Floral Fabric": "Floral",
    "Tiered Dress": "Tiered",
    "Ruffled": "Ruffle",
    "Fit-and-Flare": "Fit and Flare",
    "A Line": "A-Line",
    "Ballgown": "Ball Gown",
    "Floor Length": "Floor-Length",
    "Floorlength": "Floor-Length",
    "floorlength": "Floor-Length",
    "Floor": "Floor-Length",
    "Floor-Sweeping": "Floor-Length",
    "Floor Sweeping": "Floor-Length",
    "Full-Length": "Floor-Length",
    "Full Length": "Floor-Length",
    "Gown": "Floor-Length",
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
    "Boat Neckline": "Boat Neck",
    "Plunging V-Neckline": "Plunging V-Neck",
    "Plunging V Neckline": "Plunging V-Neck",
    "Deep Plunging V-Neckline": "Plunging V-Neck",
    "Deep Plunging V Neckline": "Plunging V-Neck",
    "V-Neckline": "V-Neck",
    "V Neckline": "V-Neck",
    "Shoulder Tie Straps": "Shoulder Tie Straps",
    "Wide Shoulder Straps": "Wide Shoulder Straps",
    "Tie Straps": "Shoulder Tie Straps",
    "Deep V": "Deep V-Neck",
    "V Neck": "V-Neck",
    "Shoulder Straps": "Shoulder Straps",
    "Tie Straps": "Shoulder Tie Straps",
    "Cowl": "Cowl Neck",
    "Scoop": "Scoop Neck",
    "Halter Neck": "Halter",
    "Spaghetti Straps": "Spaghetti Strap",
    "Adjustable Straps": "Spaghetti Strap",
    "Extra Long Front Streamers": "Front Streamers",
    "2 Extra Long Front Streamers": "Front Streamers",
    "Different Looks": "Multiway",
    "Built In Boning": "Built-In Boning",
    "Built-In Boning": "Built-In Boning",
    "Diagonal Seam With Slit": "Diagonal Seam / Front Slit",
    "Diagonal Seam": "Diagonal Seam",
    "Sweeping Skirt": "Sweeping Skirt",
    "Sweeping Column Skirt": "Column",
    "Hidden Side Pockets": "Hidden Pockets",
    "Shiny Satin": "Shiny Satin",
    "Woven Fabric": "Woven",
    "Stretch Satin": "Stretch Satin",
    "Luxe Stretch Knit": "Luxe Stretch Knit",
    "Luxe Knit": "Luxe Knit",
    "Stretch Knit": "Stretch Knit",
    "Plisse": "Plissé",
    "Plisse Fabric": "Plissé",
    "Plissé Fabric": "Plissé",
    "Sequins": "Sequin",
}

TEXT_KEYS = [
    "title", "product_name", "handle", "body_html", "description", "descriptionHtml",
    "product_description", "short_description", "long_description", "product_details",
    "details", "features", "fabric_details", "tags", "product_type", "productType",
    "vendor", "style", "silhouette", "length", "neckline", "material", "fabric",
    "_pdp_detail_text", "_pdp_jsonld_text",
]

BLOCK_KEY_PARTS = ["image", "img", "thumb", "url", "href", "price", "sku", "id", "pid"]


def clean_text(value: Any) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_text(value: Any) -> str:
    text = clean_text(value).lower()
    text = text.replace("–", "-").replace("—", "-").replace("&", " and ")
    text = re.sub(r"[\-_/]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(_to_text(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_to_text(v) for v in value)
    return clean_text(value)


def _collect_source_text(source: Any) -> str:
    if isinstance(source, str):
        return clean_text(source)

    if not isinstance(source, dict):
        return clean_text(source)

    chunks: list[str] = []
    for key in TEXT_KEYS:
        if key in source:
            text = _to_text(source.get(key))
            if text:
                chunks.append(text)

    def walk(value: Any, key_path: str = "") -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                key = str(k or "").lower()
                if any(block in key for block in BLOCK_KEY_PARTS):
                    continue
                if any(token in key for token in [
                    "facet", "attribute", "detail", "description", "feature", "fabric",
                    "material", "length", "silhouette", "neckline", "sleeve", "style",
                    "tag", "product_type", "type",
                ]):
                    text = _to_text(v)
                    if text:
                        chunks.append(text)
                walk(v, f"{key_path}.{key}" if key_path else key)
        elif isinstance(value, list):
            for item in value:
                walk(item, key_path)

    walk(source)
    return " ".join(chunks)


def _find_keyword(text: str, keywords: list[str]) -> str:
    normalized_text = f" {_normalize_text(text)} "
    for keyword in sorted(keywords, key=len, reverse=True):
        nk = _normalize_text(keyword)
        if not nk:
            continue

        # 避免把 "strapless bra-friendly" 误判为商品本身是 Strapless 款式。
        if nk == "strapless":
            if " strapless bra " in normalized_text or " strapless bra friendly " in normalized_text:
                positive_patterns = [
                    " strapless neckline ", " strapless bodice ", " strapless dress ",
                    " strapless gown ", " strapless top ", " strapless silhouette ",
                ]
                if not any(pattern in normalized_text for pattern in positive_patterns):
                    continue

        if f" {nk} " in normalized_text:
            return NORMALIZE_MAP.get(keyword, keyword)
    return ""


def should_default_floor_length(source: Any, text: str) -> bool:
    if not isinstance(source, dict):
        return False
    normalized_text = _normalize_text(text)
    title = _normalize_text(source.get("title") or source.get("product_name"))
    if not any(word in title for word in ["dress", "gown"]):
        return False
    blocked = ["mini", "midi", "short", "knee length", "tea length", "high low", "jumpsuit", "pantsuit", "separates"]
    return not any(term in normalized_text for term in blocked)


def _extract_detail_patterns(text: str) -> dict[str, str]:
    normalized = _normalize_text(text)

    fabric = ""
    fabric_patterns = [
        ("Satin", ["luxurious smooth satin feel", "smooth satin feel", "soft sheen finish", "luxurious satin", "silky satin", "satin maxi", "satin dress", "crafted in a silky satin"]),
        ("Viscose / Rayon", ["viscose", "rayon"]),
        ("Matte Satin", ["matte satin fabric", "fabric details matte satin", "matte satin boasts", "matte satin"]),
        ("Shiny Satin", ["shiny satin"]),
        ("Stretch Satin", ["stretch satin"]),
        ("Jacquard", ["jacquard floral fabric", "jacquard fabric", "jacquard"]),
        ("Luxe Stretch Knit", ["luxe stretch knit"]),
        ("Plissé", ["plisse fabric", "plisse", "plissé fabric", "plissé"]),
        ("Chiffon", ["chiffon"]),
        ("Crepe", ["crepe"]),
        ("Satin", ["satin"]),
        ("Tulle", ["tulle"]),
        ("Velvet", ["velvet"]),
        ("Mesh", ["mesh"]),
        ("Lace", ["lace"]),
    ]
    for label, patterns in fabric_patterns:
        if any(pattern in normalized for pattern in patterns):
            fabric = label
            break

    length = ""
    if any(p in normalized for p in ["ankle length", "ankle length dress"]):
        length = "Ankle-Length"
    elif any(p in normalized for p in ["floor length", "floor length fully lined", "floorlength", "floor sweeping", "floor-sweeping", "sweeps the floor", "sits on the floor", "grazes the floor"]):
        length = "Floor-Length"
    elif "maxi length" in normalized or "maxi dress" in normalized or "maxi gown" in normalized:
        length = "Floor-Length"
    elif "tea length" in normalized or "tea length dress" in normalized:
        length = "Tea-Length"
    elif "midi length" in normalized or "midi dress" in normalized:
        length = "Midi"
    elif "mini length" in normalized or "mini dress" in normalized:
        length = "Mini"
    elif re.search(r"\bgown\b", normalized) and not any(term in normalized for term in ["mini", "midi", "short", "knee length", "tea length", "ankle length", "high low"]):
        # BG 文案中 gown 通常指及地/长礼服，例如 Luxe Stretch Knit gown、classic halter gown。
        length = "Floor-Length"

    neckline_parts: list[str] = []
    neckline_patterns = [
        ("Plunge", ["plunge neckline", "plunging neckline", "deep plunge", "deep plunging"]),
        ("Cowl Wrap Neck", ["cowl wrap neck", "cowl wrap"]),
        ("Cowl Front", ["cowl front neck", "cowl front"]),
        ("Cowl Back", ["cowl back neck", "cowl back"]),
        ("Spaghetti Strap", ["spaghetti style adjustable strap", "spaghetti strap", "spaghetti straps"]),
        ("Adjustable Strap", ["adjustable strap", "adjustable straps"]),
        ("V-Neck", ["soft v neckline", "soft v neck", "v neckline", "v neck"]),
        ("Elastic Back", ["elastic back"]),
        ("Cupped Bust", ["cupped bust", "bust cups", "cupped cups"]),
        ("Plunging V-Neck", ["deep plunging v neckline", "plunging v neckline"]),
        ("Deep V-Neck", ["deep v neck"]),
        ("V-Neck", ["v neckline", "v neck"]),
        ("Boat Neck", ["boat neckline", "boat neck", "bateau neckline", "bateau neck"]),
        ("Shoulder Tie Straps", ["shoulder tie straps", "tie straps"]),
        ("Wide Shoulder Straps", ["wide shoulder straps", "wide shoulder strap"]),
        ("Spaghetti Strap", ["spaghetti straps", "spaghetti strap"]),
        ("Adjustable Straps", ["adjustable straps", "adjustable strap"]),
        ("Long Sleeve", ["long sleeves", "long sleeve"]),
        ("Short Sleeve", ["short sleeves", "short sleeve"]),
        ("Sleeveless", ["sleeveless"]),
        ("Strapless", ["strapless neckline", "strapless dress"]),
        ("Cross Front Halter", ["cross front halter dress", "cross front halter"]),
        ("Halter", ["halter neckline", "halter neck", "halter dress", "halter gown"]),
        ("Square Neck", ["square neckline", "square neck"]),
        ("Scoop Neck", ["scoop neckline", "scoop neck"]),
        ("Cowl Neck", ["cowl neckline", "cowl neck"]),
        ("Sweetheart", ["sweetheart neckline", "sweetheart neck"]),
        ("One-Shoulder", ["one shoulder", "one shoulder neckline", "one-shoulder neckline"]),
        ("Thin Straps", ["modern, thin straps", "thin straps", "fine straps"]),
        ("Off-the-Shoulder", ["off shoulder", "off the shoulder"]),
        ("Bow Shoulder", ["bows on the shoulders", "shoulder bows"]),
    ]
    for label, patterns in neckline_patterns:
        if any(pattern in normalized for pattern in patterns) and label not in neckline_parts:
            neckline_parts.append(label)
    if "Plunging V-Neck" in neckline_parts and "V-Neck" in neckline_parts:
        neckline_parts.remove("V-Neck")
    if "Deep V-Neck" in neckline_parts and "V-Neck" in neckline_parts:
        neckline_parts.remove("V-Neck")

    style_parts: list[str] = []
    style_patterns = [
        ("Twist Open Back", ["twist open back", "twist back"]),
        ("Open Back", ["open back"]),
        ("Plunge", ["plunge neckline", "plunging neckline", "deep plunge", "deep plunging"]),
        ("Cowl Wrap", ["cowl wrap"]),
        ("Cowl Front", ["cowl front"]),
        ("Cowl Back", ["cowl back"]),
        ("Wrap Tie", ["wrap tie"]),
        ("Self Tie", ["self tie"]),
        ("Drape Detail", ["drape detail", "draped detail", "drape"]),
        ("Knot Front", ["knot front"]),
        ("Gathered Bust", ["gathered bust"]),
        ("Twist Bust", ["twist bust"]),
        ("Statement Shoulder", ["statement shoulder"]),
        ("Concealed Side Zip", ["concealed side zip"]),
        ("Straight / Flowy Silhouette", ["straight, flowy silhouette", "straight flowy silhouette"]),
        ("Straight", ["straight silhouette"]),
        ("Flowy Silhouette", ["flowy silhouette"]),
        ("Bias Cut", ["bias cut"]),
        ("Elastic Back", ["elastic back"]),
        ("A-Line", ["tea length a line dress", "tea length a line", "a line dress", "a line skirt", "a line tiered", "a line", "a-line dress", "a-line skirt"]),
        ("Front Streamers", ["extra long front streamers", "front streamers", "2 extra long front streamers", "streamers attached"]),
        ("Multiway", ["different looks", "creates different looks", "hidden loops at the neck and back", "hidden loops", "convertible"]),
        ("Built-In Boning", ["built in boning", "built-in boning", "boning"]),
        ("Diagonal Seam", ["diagonal seam"]),
        ("Jacquard Floral", ["jacquard floral fabric", "jacquard floral", "floral jacquard"]),
        ("Floral", ["floral fabric", "floral print", "floral"]),
        ("Tiered", ["tiered silhouette", "tiered skirt", "tiered"]),
        ("Fluted Skirt", ["fluted skirt"]),
        ("Bow Shoulder", ["bows on the shoulders", "shoulder bows"]),
        ("Wrap", ["wrap dress", "wrap skirt", "wrap silhouette"]),
        ("Ruffle", ["ruffle", "ruffled"]),
        ("Pleated", ["pleated", "pleating"]),
        ("Draped", ["draped", "drape"]),
        ("Ruched", ["ruched", "ruching"]),
        ("Column", ["column silhouette", "column dress", "column skirt", "sweeping column skirt"]),
        ("Sweeping Skirt", ["floor length sweeping skirt", "floor length sweeping", "sweeping skirt"]),
        ("Sheath", ["sheath silhouette", "sheath dress"]),
        ("Fitted Waist", ["fitted waist", "cinched waist"]),
        ("Hidden Pockets", ["hidden side pockets", "side pockets", "hidden pockets"]),
        ("Detachable Sleeves", ["detachable sleeves", "sleeves that button on and off", "button on and off"]),
        ("Cut-Out Back", ["cut-out in back", "cut out in back", "cut-out back", "cut out back", "surprise cut-out"]),
        ("Open Back", ["open back", "open-back"]),
        ("Front Slit", ["front slit", "front split", "with slit", "seam with slit"]),
        ("Side Slit", ["side slit", "side split"]),
        ("Fully Lined", ["fully lined"]),
        ("Flowy", ["flowing", "movement", "light and airy"]),
    ]
    for label, patterns in style_patterns:
        if any(pattern in normalized for pattern in patterns) and label not in style_parts:
            style_parts.append(label)

    return {
        "fabric_name": fabric,
        "aesthetic_tag": " / ".join(style_parts[:4]),
        "length": length,
        "neckline": " / ".join(neckline_parts[:4]),
    }


def _source_hint(source: Any, *keys: str) -> str:
    if not isinstance(source, dict):
        return ""
    return " ".join(clean_text(source.get(key)) for key in keys if source.get(key))


def _known_bg_style_fallback(source: Any, text: str, current_style: str = "") -> str:
    if current_style:
        return current_style

    hint = _source_hint(source, "title", "product_name", "handle") if isinstance(source, dict) else clean_text(text)
    source_text = " ".join([hint, clean_text(text)])
    normalized = _normalize_text(source_text)

    parts: list[str] = []

    def add(label: str, *patterns: str) -> None:
        if label in parts:
            return
        if any(pattern and pattern in normalized for pattern in patterns):
            parts.append(label)

    add("A-Line", "a line", "a-line", "a line skirt", "a line dress")
    add("Front Streamers", "front streamers", "extra long front streamers", "streamers attached")
    add("Multiway", "different looks", "hidden loops", "convertible")
    add("Built-In Boning", "built in boning", "built-in boning", "boning")
    add("Fitted Waist", "fitted waist", "cinched waist")
    add("Sweeping Skirt", "sweeping skirt", "sweeping column skirt")
    add("Hidden Pockets", "hidden side pockets", "side pockets", "hidden pockets")
    add("Detachable Sleeves", "detachable sleeves", "button on and off")
    add("Diagonal Seam", "diagonal seam")
    add("Front Slit", "front slit", "front split", "with slit", "seam with slit")
    add("Side Slit", "side slit", "side split")
    add("Cut-Out Back", "cut out in back", "cut-out in back", "surprise cut out", "cut out back")
    add("Open Back", "open back")
    add("Column", "column skirt", "column silhouette")
    add("Jacquard Floral", "jacquard floral", "floral jacquard")
    add("Floral", "floral fabric", "floral print")
    add("Fully Lined", "fully lined")
    add("Fluted Skirt", "fluted skirt")
    add("Ruffle", "ruffle", "ruffled")
    add("Pleated", "pleated", "pleating")
    add("Ruched", "ruched", "ruching")
    add("Draped", "draped", "drape")

    if parts:
        return " / ".join(parts[:4])

    name_key = _normalize_text(hint)
    known_map = [
        (("grace dress with slit", "grace chiffon dress with slit"), "Front Streamers / Multiway / Front Slit / Hidden Pockets"),
        (("grace dress slit",), "Front Streamers / Multiway / Front Slit / Hidden Pockets"),
        (("grace dress", "grace chiffon dress"), "Front Streamers / Multiway / Hidden Pockets"),
        (("stephanie dress", "stephanie chiffon dress"), "A-Line / Diagonal Seam / Front Slit"),
        (("gwennie dress with slit", "gwennie chiffon dress with slit"), "A-Line / Front Slit"),
        (("gwennie dress", "gwennie chiffon dress"), "A-Line"),
        (("kaia dress", "kaia chiffon dress"), "A-Line"),
        (("kayla dress", "kayla chiffon dress"), "A-Line"),
        (("hannah dress", "hannah chiffon dress"), "A-Line"),
        (("mischa dress", "mischa chiffon dress"), "Off-the-Shoulder"),
        (("kensie dress",), "A-Line"),
        (("destiny dress",), "A-Line"),
        (("daphne dress",), "A-Line"),
        (("ivy dress",), "Sheath"),
        (("arbor dress",), "A-Line / Jacquard Floral"),
    ]
    for keys, value in known_map:
        if any(key in name_key for key in keys):
            return value

    if "with slit" in normalized or " dress with slit" in normalized:
        return "Front Slit"
    return ""



def _known_bg_length_fallback(source: Any, text: str, current_length: str = "") -> str:
    """BG 长度兜底：只在已有规则没有输出长度时使用。"""
    if current_length:
        return current_length

    source_text = " ".join([
        _source_hint(source, "title", "product_name", "handle") if isinstance(source, dict) else "",
        clean_text(text),
    ])
    normalized = _normalize_text(source_text)

    # 明确的短/中长优先，避免 gown 兜底误覆盖。
    if "tea length" in normalized or "tea-length" in normalized:
        return "Tea-Length"
    if "ankle length" in normalized or "ankle-length" in normalized:
        return "Ankle-Length"
    if "midi" in normalized:
        return "Midi"
    if "mini" in normalized or "short dress" in normalized:
        return "Mini"
    if "knee length" in normalized or "knee-length" in normalized:
        return "Knee-Length"

    # 明确长礼服/及地描述。
    if any(pattern in normalized for pattern in [
        "floor length", "floorlength", "floor sweeping", "floor-sweeping",
        "sweeps the floor", "sits on the floor", "grazes the floor",
        "maxi length", "maxi dress", "maxi gown",
    ]):
        return "Floor-Length"

    # Freida / Stephanie 这类 BG 商品详情没有直接写 length，但以 gown / maxi 语境出现。
    if re.search(r"\bgown\b", normalized) and not any(term in normalized for term in ["mini", "midi", "short", "knee length", "tea length", "ankle length", "high low"]):
        return "Floor-Length"
    if "luxe stretch knit dress" in normalized and "column" in normalized:
        return "Floor-Length"
    if "stephanie dress" in normalized and ("halter gown" in normalized or "classic halter gown" in normalized):
        return "Floor-Length"

    return ""

def extract_attributes(source: Any, *, default_floor_length: bool = False) -> dict[str, str]:
    text = _collect_source_text(source)
    detail_attrs = _extract_detail_patterns(text)
    fabric = detail_attrs.get("fabric_name") or _find_keyword(text, FABRIC_KEYWORDS)
    style = detail_attrs.get("aesthetic_tag") or _find_keyword(text, STYLE_KEYWORDS)
    style = _known_bg_style_fallback(source, text, style)
    length = detail_attrs.get("length") or _find_keyword(text, LENGTH_KEYWORDS)
    length = _known_bg_length_fallback(source, text, length)
    neckline = detail_attrs.get("neckline") or _find_keyword(text, NECKLINE_KEYWORDS)
    if not length and default_floor_length and should_default_floor_length(source, text):
        length = "Floor-Length"
    return {
        "fabric_name": fabric,
        "aesthetic_tag": style,
        "length": length,
        "neckline": neckline,
    }


