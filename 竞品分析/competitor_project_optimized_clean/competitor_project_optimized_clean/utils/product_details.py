"""商品详情描述提取工具。

用于把 Product Details / Fabric Details / Size + Fit / Description 等前台详情文字
统一沉淀到一列。注意：商品详情描述只放客户能在 PDP 前台看到的详情区块，
不能把 Shopify/SearchSpring tags、JSON-LD schema、Offer、尺码库存价格等后台/结构化数据写入。
"""

from __future__ import annotations

import html
import json
import re
from typing import Any


BACKEND_TAG_KEYWORDS = (
    "category:",
    "collection:",
    "colour:",
    "color:",
    "length:",
    "occasion:",
    "style:",
    "subcat:",
    "status:",
    "security-ribbon",
)

SCHEMA_STOP_PATTERNS = (
    "https://schema.org",
    "http://schema.org",
    "ProductGroup",
    "BreadcrumbList",
    "PostalAddress",
    "NewCondition",
    "InStock",
    "#shipping_policy",
    "#return_policy",
)

DETAIL_SECTION_STARTS = (
    "product details",
    "fabric details",
    "size + fit",
    "size & fit",
    "description",
)

# 详情区块结束标记。这里不要用过于泛化的 shipping/returns 单词，避免 Product Details
# 文案里出现 shipping/return 时过早截断；使用 PDP 常见标题更稳。
DETAIL_SECTION_STOPS = (
    "shipping & returns",
    "shipping + returns",
    "shipping and returns",
    "shipping policy",
    "returns and exchanges",
    "complete the look",
    "you may also",
    "recently viewed",
    "customers also",
    "shop the look",
    "suggested products",
    "footer",
    "your bag",
    "reviews",
    "faq",
    "https://schema.org",
    "http://schema.org",
    "ProductGroup",
    "BreadcrumbList",
    "PostalAddress",
    "NewCondition",
    "InStock",
    "#shipping_policy",
    "#return_policy",
)


def _fix_mojibake(text: str) -> str:
    """修复日志/网页文本中常见的 UTF-8 mojibake。"""
    text = str(text or "")
    replacements = {
        "â¢": "•",
        "â€“": "–",
        "â€”": "—",
        "â": "’",
        "â": "‘",
        "â": "“",
        "â": "”",
        "Â": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _html_to_text_preserve_blocks(value: Any, *, keep_scripts: bool = False) -> str:
    text = str(value or "")
    if not text:
        return ""
    if not keep_scripts:
        text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    else:
        text = re.sub(r"</?script[^>]*>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(?:p|li|div|tr|h\d|section|button|summary|details)>\s*", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = _fix_mojibake(text)
    # 保留 bullet 前换行，避免全部挤成一段。
    text = re.sub(r"\s*•\s*", "\n• ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def _truncate_schema_noise(text: str) -> str:
    normalized = str(text or "")
    lower = normalized.lower()
    cut_positions = []
    for marker in SCHEMA_STOP_PATTERNS:
        idx = lower.find(marker.lower())
        if idx >= 0:
            cut_positions.append(idx)
    if cut_positions:
        normalized = normalized[: min(cut_positions)]
    return normalized.strip()


def _looks_like_backend_tag_line(line: str) -> bool:
    normalized = re.sub(r"\s+", " ", line or "").strip()
    if not normalized:
        return False
    lower = normalized.lower()
    segments = [seg.strip() for seg in normalized.split(";") if seg.strip()]
    colon_tag_count = sum(
        1
        for seg in segments
        if re.match(r"^(category|collection|colo[u]?r|length|occasion|style|subcat|status)\s*:", seg, flags=re.I)
    )
    if len(segments) >= 3 and colon_tag_count >= 2:
        return True
    keyword_hits = sum(1 for kw in BACKEND_TAG_KEYWORDS if kw in lower)
    if keyword_hits >= 3 and ";" in normalized:
        return True
    return False


def _remove_backend_tag_lines(text: str) -> str:
    lines = []
    for line in str(text or "").splitlines():
        if _looks_like_backend_tag_line(line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _dedupe_lines_keep_order(text: str) -> str:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        # 去掉无意义展开符，但保留标题。
        if line in {"+", "–", "-"}:
            continue
        if re.fullmatch(r"learn more about this fabric selection", line, flags=re.I):
            continue
        key = re.sub(r"\s+", " ", line).strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(line)
    return "\n".join(result).strip()


def _normalize_detail_headings(text: str) -> str:
    text = str(text or "")
    # 把标题前后统一成换行，解决 Product Details + • xxx 挤在一行导致分段失败。
    for heading in ["Product Details", "Fabric Details", "Size + Fit", "Size & Fit", "Description"]:
        pattern = re.compile(rf"\b{re.escape(heading)}\b\s*[+–-]?\s*", flags=re.I)
        text = pattern.sub(lambda m, h=heading: f"\n{h}\n", text)
    text = re.sub(r"\s*•\s*", "\n• ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def clean_detail_text(value: Any) -> str:
    """通用详情清洗。用于已经确认是详情候选的文本。"""
    text = _html_to_text_preserve_blocks(value)
    if not text:
        return ""
    text = _truncate_schema_noise(text)
    text = _normalize_detail_headings(text)
    text = _remove_backend_tag_lines(text)
    text = _dedupe_lines_keep_order(text)
    return text.strip()




def is_incomplete_detail_text(value: Any, *, min_chars: int = 120, require_fabric_details: bool = False) -> bool:
    """判断商品详情是否明显不完整。

    BG 详情应该至少包含 Product Details 中的多条要点；多数商品还包含 Fabric Details。
    这里不要过严，否则少数真实短详情会被误判；主要用于补抓/回填兜底。
    """
    text = clean_detail_text(value)
    if not text:
        return True
    body_lines = [
        line.strip() for line in text.splitlines()
        if line.strip()
        and not re.fullmatch(r"Product Details|Fabric Details|Size \+ Fit|Size & Fit|Description", line.strip(), flags=re.I)
    ]
    if len(" ".join(body_lines)) < min_chars:
        return True
    lower = text.lower()
    if require_fabric_details and "fabric details" not in lower:
        return True
    # 如果只有 Product Details 的第一个短句，通常是被 stop marker 误截断或 JSON 字段不完整。
    bullet_count = len(re.findall(r"(?:^|\n)\s*•\s+", text))
    if "product details" in lower and bullet_count <= 1 and len(" ".join(body_lines)) < 220:
        return True
    return False

def extract_frontend_detail_sections(text: Any, *, max_chars: int = 7000) -> str:
    """只抽取前台商品详情区块。

    优先从 Product Details 开始，连续保留 Fabric Details；若无 Product Details，才使用
    Fabric Details / Size + Fit / Description。结束于 Shipping & Returns 等明显后续模块。
    找不到这些标题时返回空，避免把整页 schema/SEO 数据当详情。
    """
    raw = _html_to_text_preserve_blocks(text, keep_scripts=False)
    if not raw:
        return ""
    raw = _fix_mojibake(raw)
    raw = _normalize_detail_headings(raw)

    lower = raw.lower()
    starts: list[int] = []
    # Product Details 是最准确入口；不要被上方 meta description 或菜单文案干扰。
    product_idx = lower.find("product details")
    if product_idx >= 0:
        starts.append(product_idx)
    else:
        for marker in ["fabric details", "size + fit", "size & fit", "description"]:
            idx = lower.find(marker)
            if idx >= 0:
                starts.append(idx)
    if not starts:
        return ""

    start = min(starts)
    stop_candidates: list[int] = []
    for marker in DETAIL_SECTION_STOPS:
        idx = lower.find(marker.lower(), start + 15)
        if idx > start:
            stop_candidates.append(idx)
    end = min(stop_candidates) if stop_candidates else min(len(raw), start + max_chars)
    section = raw[start:end].strip()
    if len(section) > max_chars:
        section = section[:max_chars].strip()

    section = clean_detail_text(section)
    if not section:
        return ""

    # 如果只有标题没有有效正文，不返回。
    body_lines = [
        line for line in section.splitlines()
        if line.strip() and not re.fullmatch(r"Product Details|Fabric Details|Size \+ Fit|Size & Fit|Description", line.strip(), flags=re.I)
    ]
    if not body_lines:
        return ""
    return section


def extract_frontend_detail_sections_from_html(raw_html: Any, *, max_chars: int = 7000) -> str:
    """从原始 HTML/内嵌 JS 中提取前台详情。

    第一优先级：去掉 script/style 后的可见文本。
    第二优先级：保留 script 内容并反转义，适配 Hydrogen/Remix 把 PDP 文案塞在内嵌 JSON 的情况。
    """
    html_text = str(raw_html or "")
    if not html_text:
        return ""

    visible = extract_frontend_detail_sections(html_text, max_chars=max_chars)
    if visible:
        return visible

    decoded = html.unescape(html_text)
    replacements = {
        r"\u003c": "<",
        r"\u003e": ">",
        r"\u0026": "&",
        r"\u002F": "/",
        r"\/": "/",
        r"\n": "\n",
        r"\t": " ",
        r"\r": " ",
        r'\"': '"',
    }
    for old, new in replacements.items():
        decoded = decoded.replace(old, new)

    # 部分 JSON 字符串还会整体转义，尝试抽取包含详情标题的短窗口，避免把整页 schema 带进去。
    lower = decoded.lower()
    positions = [idx for marker in DETAIL_SECTION_STARTS for idx in [lower.find(marker)] if idx >= 0]
    if positions:
        start = min(positions)
        window = decoded[max(0, start - 300): start + max_chars]
        focused = extract_frontend_detail_sections(window, max_chars=max_chars)
        if focused:
            return focused

    return ""


def extract_description_from_json_like(value: Any) -> str:
    """从 Shopify .js/.json 等结构中提取自然描述。

    只读取 body_html/description 这类字段，不读取 tags/schema/variants/offers。
    """
    if not value:
        return ""
    if isinstance(value, str):
        # 字符串有可能是 JSON，也有可能是 HTML 描述。
        s = value.strip()
        if s.startswith("{") or s.startswith("["):
            try:
                return extract_description_from_json_like(json.loads(s))
            except Exception:
                pass
        return clean_detail_text(s)

    if isinstance(value, dict):
        product = value.get("product") if isinstance(value.get("product"), dict) else value
        parts: list[str] = []
        for key in [
            "product_details",
            "productDetails",
            "details",
            "detail",
            "fabric_details",
            "fabricDetails",
            "size_fit",
            "sizeFit",
            "size_and_fit",
            "sizeAndFit",
            "description",
            "descriptionHtml",
            "body_html",
            "short_description",
        ]:
            text = clean_detail_text(product.get(key))
            if text:
                parts.append(text)
        return _dedupe_lines_keep_order("\n".join(parts))

    return ""



def _clean_hellomolly_detail_text(value: Any) -> str:
    """Hello Molly 商品详情清洗。

    HM 的商品对象经常同时提供 description 和 descriptionHtml/body_html，内容相同但一个是
    整段文本、一个是分行详情。如果把多个来源拼接，会出现“整段 + 分行”的重复。
    因此 HM 侧先只选一个来源，再做最后的轻量去重。
    """
    text = clean_detail_text(value)
    if not text:
        return ""

    # 让 Please Note 独立成行，便于识别 HM PDP 的真正详情正文起点。
    text = re.sub(r"\s*(Please Note\s*:)", r"\n\1", text, flags=re.I).strip()

    # 如果同一份文本前半段是纯文本摘要，后半段从 Please Note 开始是 PDP 详情正文，
    # 优先保留后半段，避免同一批 details 以段落和列表两种格式重复出现。
    m = re.search(r"(?i)(?:^|\n)\s*Please Note\s*:", text)
    if m and m.start() > 80:
        text = text[m.start():].strip()

    # 句子/条目级去重：适配同一条详情既以句子形式出现，又以单独换行出现的情况。
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line in {"+", "–", "-"}:
            continue
        key = re.sub(r"^[•\-\*]\s*", "", line)
        key = re.sub(r"[\s\.。;；:：,，]+", " ", key).strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        lines.append(line)

    return "\n".join(lines).strip()


def collect_hellomolly_product_detail_text(product: dict[str, Any] | None, *extra_values: Any) -> str:
    """Hello Molly 专用详情提取。

    关键原则：只取一个最干净的详情来源，不把 description、descriptionHtml、body_html
    全部拼接到一起，避免重复。优先取前台 HTML/descriptionHtml/body_html；如果没有，
    再取纯文本 description。
    """
    product = product or {}

    # extra_values 通常是额外传入的 PDP HTML；优先尝试前台详情区块，但命中后即返回。
    for value in extra_values:
        focused = extract_frontend_detail_sections(value)
        cleaned = _clean_hellomolly_detail_text(focused or value)
        if cleaned:
            return cleaned

    # HM 优先使用一个最完整、最接近前台 PDP 的字段；找到就直接返回，不继续拼其它字段。
    candidate_keys = [
        "_pdp_detail_text",
        "body_html",
        "descriptionHtml",
        "product_details",
        "productDetails",
        "details",
        "detail",
        "description",
        "short_description",
        "subtitle",
    ]

    for key in candidate_keys:
        value = product.get(key)
        if not value:
            continue
        focused = extract_frontend_detail_sections(value)
        cleaned = _clean_hellomolly_detail_text(focused or value)
        if cleaned:
            return cleaned

    return ""


def _clean_clublondon_detail_text(value: Any) -> str:
    """Club L London 商品详情清洗。

    CL 的商品对象经常同时带 description 与 body_html/descriptionHtml。如果多个字段拼接，
    会出现“完整详情 + 同一段详情再次重复”的问题。CL 侧应只选择一个最完整来源，
    并在 SKU 后截断异常重复内容。
    """
    text = clean_detail_text(value)
    if not text:
        return ""

    # CL 详情通常是：自然语言描述 + Features + Sizing & Fit + Product Information + SKU。
    # 统一切分这些标题，提升可读性，也让后续截断/去重更稳定。
    # Features 标题在 CL 里通常是大写；不要用忽略大小写，否则会误切正文里的
    # "features a refined..."。
    text = re.sub(r"(?<![A-Za-z])Features\s*[-–]?\s*", "\nFeatures\n", text)
    text = re.sub(r"Sizing\s*&\s*Fit\s*", "\nSizing & Fit\n", text, flags=re.I)
    text = re.sub(r"Product\s+Information\s*", "\nProduct Information\n", text, flags=re.I)
    text = re.sub(r"SKU\s*:\s*", "\nSKU: ", text, flags=re.I)

    # Features 里的 - xxx 经常连在一行，拆成条目。只处理短横线后有空格的情况，
    # 避免影响 floor-sweeping / maxi-length 这类连字符单词。
    text = re.sub(r"\s*-\s+", "\n- ", text)

    # CL 的纯文本有时会把若干信息黏在一起，例如
    # "Club L LondonLined" / "153cmThis style"。做轻量切分，提升可读性。
    text = re.sub(r"(Club L London)(?=(Lined|Double|Premium|Worn|This style))", r"\1\n", text)
    text = re.sub(r"(cm)(?=This style)", r"\1\n", text)
    text = re.sub(r"(stretch)(?=Premium)", r"\1\n", text, flags=re.I)
    text = re.sub(r"(Elastane|Polyester|Polyamide|Cotton|Viscose)(?=Worn length)", r"\1\n", text, flags=re.I)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()

    # 如果因为历史拼接出现“... SKU: CLxxxx \n 又从商品描述开头重复一遍”，保留 SKU 前后的第一份完整详情。
    sku_match = re.search(r"(?i)SKU\s*:\s*[A-Z0-9-]+", text)
    if sku_match:
        text = text[: sku_match.end()].strip()

    return _dedupe_lines_keep_order(text).strip()


def _score_clublondon_detail_text(text: str) -> tuple[int, int]:
    """给 CL 候选详情打分，优先选包含详情结构的完整来源。"""
    cleaned = _clean_clublondon_detail_text(text)
    if not cleaned:
        return (0, 0)
    lower = cleaned.lower()
    score = 0
    for marker, weight in [
        ("features", 20),
        ("sizing & fit", 18),
        ("product information", 18),
        ("sku:", 14),
        ("designed exclusively by club l london", 8),
        ("model is", 6),
        ("worn length", 6),
    ]:
        if marker in lower:
            score += weight
    # 过短文本通常只是标题/摘要，完整程度较低。
    score += min(len(cleaned) // 80, 12)
    return (score, len(cleaned))


def collect_clublondon_product_detail_text(product: dict[str, Any] | None, *extra_values: Any) -> str:
    """Club L London 专用详情提取。

    核心原则：只选择一个最完整、最干净的详情来源，不把 description 与 body_html
    叠加拼接，避免同一份 Features/Sizing/Product Information 重复出现。
    """
    product = product or {}

    candidates: list[Any] = []
    candidates.extend(extra_values)

    # CL GraphQL 返回 body_html=descriptionHtml，description 是纯文本；product.js 通常为 body_html。
    # 只选择一个最佳来源。
    candidate_keys = [
        "_pdp_detail_text",
        "body_html",
        "descriptionHtml",
        "product_details",
        "productDetails",
        "details",
        "detail",
        "description",
        "short_description",
        "subtitle",
    ]
    for key in candidate_keys:
        value = product.get(key)
        if value:
            candidates.append(value)

    best_text = ""
    best_score = (0, 0)
    for value in candidates:
        # CL 详情一般没有 Product Details 标题，因此不能只依赖 extract_frontend_detail_sections。
        focused = extract_frontend_detail_sections(value)
        cleaned = _clean_clublondon_detail_text(focused or value)
        score = _score_clublondon_detail_text(cleaned)
        if score > best_score:
            best_score = score
            best_text = cleaned

    return best_text.strip()

def collect_product_detail_text(product: dict[str, Any] | None, *extra_values: Any) -> str:
    """从商品对象中收集前台商品详情文案，返回去重后的单列文本。"""
    product = product or {}
    candidate_keys = [
        "_pdp_detail_text",
        "product_details",
        "productDetails",
        "details",
        "detail",
        "size_fit",
        "sizeFit",
        "size_and_fit",
        "sizeAndFit",
        "fit_details",
        "fabric_details",
        "fabricDetails",
        "description",
        "descriptionHtml",
        "body_html",
        "short_description",
        "subtitle",
    ]

    parts: list[str] = []
    for value in extra_values:
        focused = extract_frontend_detail_sections(value)
        cleaned = focused or clean_detail_text(value)
        if cleaned:
            parts.append(cleaned)

    for key in candidate_keys:
        value = product.get(key)
        if not value:
            continue
        focused = extract_frontend_detail_sections(value)
        cleaned = focused or clean_detail_text(value)
        if cleaned:
            parts.append(cleaned)

    return _dedupe_lines_keep_order("\n".join(parts)).strip()
