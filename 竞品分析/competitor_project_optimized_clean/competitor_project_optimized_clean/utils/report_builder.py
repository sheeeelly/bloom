"""竞品监控报表分表工具。

当前业务口径：
- 每个网站输出 3 类表：原始排序表 / 上新表 / 下架表。
- 原始排序表：按官网列表页真实展示顺序输出，并展示本周 vs 上周排名涨跌。
- 排名涨跌只输出一个值：上新留空、持平 +0、上升 +N、下降 -N。
- 上新表：本周新增 SKC，排序取本周原始排序表中的官网展示排序。
- 下架表：本周消失 SKC，排序取该 SKC 最近一次出现时的官网展示排序。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable

from utils.baseline_manager import BaselineManager

NEW_STATUS_VALUES = {"是", "老款补货"}

ORIGINAL_COLUMNS = [
    "排序", "排名涨跌",
    "网站名", "品牌", "类目",
    "商品唯一键 / SKC Key", "款式 ID / SPU Key", "款式名",
    "商品链接", "商品名称", "颜色名称", "尺码", "主图",
    "标价", "售价", "折扣类型", "定制/现货",
    "商品详情描述", "爬取时间", "数据周次",
]

NEW_COLUMNS = [
    "排序",
    "网站名", "品牌", "类目",
    "商品唯一键 / SKC Key", "款式 ID / SPU Key", "款式名",
    "商品链接", "商品名称", "颜色名称", "尺码", "主图",
    "标价", "售价", "折扣类型", "定制/现货",
    "商品详情描述", "上新类型", "上新时间", "最近下架时间",
    "爬取时间", "数据周次",
]

DELISTED_COLUMNS = [
    "下架前排序",
    "网站名", "品牌", "类目",
    "商品唯一键 / SKC Key", "款式 ID / SPU Key", "款式名",
    "商品链接", "商品名称", "颜色名称", "尺码", "主图",
    "下架前标价", "下架前售价", "下架前折扣类型", "定制/现货",
    "商品详情描述", "最近一次出现时间", "下架时间", "数据周次",
]


def _normalize_header_l1(columns_l2: list[str], title: str = "数据") -> list[tuple[str, int]]:
    """为分表生成简单一级表头，避免原始一级表头跨度和列数不一致。"""
    return [(title, len(columns_l2))]


def _site_prefix_from_name(name: str) -> str:
    text = str(name or "").lower()
    if "bird" in text or text.startswith("bg"):
        return "BG"
    if "six" in text or text.startswith("ss"):
        return "SS"
    if "club" in text or text.startswith("cl"):
        return "CL"
    if "baby" in text or text.startswith("bb"):
        return "BB"
    if "hello" in text or "molly" in text or text.startswith("hm"):
        return "HM"
    return str(name or "SITE").split("_")[0].upper()[:8]


def _site_prefix_from_records(full_sheet_name: str, records: list[Any], delisted_records: list[Any]) -> str:
    for row in list(records or []) + list(delisted_records or []):
        site_name = getattr(row, "site_name", "") or ""
        if site_name:
            return _site_prefix_from_name(site_name)
    return _site_prefix_from_name(full_sheet_name)


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _format_rank_change(previous_rank: int | None, current_rank: int | None) -> str:
    """格式化排名涨跌。

    业务口径：
    - 新品 / 上周没有排序：留空；
    - 排名持平：+0；
    - 排名上升：+N；
    - 排名下降：-N。

    计算公式仍为：上周排序 - 本周排序。
    """
    if current_rank is None or previous_rank is None:
        return ""

    change = previous_rank - current_rank
    if change >= 0:
        return f"+{change}"
    return str(change)


def iso_week_from_date(date_text: str) -> str:
    """YYYY-MM-DD -> YYYY-Www；异常时原样返回。"""
    try:
        dt = datetime.strptime(str(date_text or "").strip()[:10], "%Y-%m-%d")
        iso = dt.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    except Exception:
        return str(date_text or "")


def make_skc_key(product_key: Any, color_name: Any) -> str:
    product = str(product_key or "").strip()
    color = str(color_name or "Default").strip() or "Default"
    return f"{product}:::{color}"


def apply_ranking_context(
    record: Any,
    baseline_mgr: BaselineManager,
    baseline_key: str,
    *,
    product_key: Any,
    current_rank: Any,
    source_page_url: str,
    current_date: str,
) -> dict[str, Any]:
    """在 check_and_update 之前调用，为记录和 metadata 写入排序上下文。

    - 上周官网展示排序取 baseline 里上一次保存的 current_rank。
    - 排名涨跌口径：上周排序 - 本周排序。
    - 新品留空，持平输出 +0，上升输出 +N，下降输出 -N。
    - 商品唯一键/SKC Key 使用 product_key + color_name，保留可读性；baseline_key 仍用于生命周期判断。
    """
    existing = baseline_mgr.baseline.get(baseline_key, {}) if baseline_key else {}
    old_meta = existing.get("metadata", {}) if isinstance(existing, dict) else {}
    if not isinstance(old_meta, dict):
        old_meta = {}

    curr = _safe_int(current_rank)
    prev = _safe_int(old_meta.get("current_rank") or old_meta.get("website_rank") or old_meta.get("排序") or old_meta.get("本周官网展示排序"))
    change = _format_rank_change(prev, curr)

    data_week = iso_week_from_date(current_date)
    color_name = getattr(record, "color_name", "")
    skc_key = make_skc_key(product_key, color_name)

    setattr(record, "source_page_url", source_page_url or old_meta.get("source_page_url", ""))
    setattr(record, "current_rank", curr or "")
    setattr(record, "previous_rank", prev or "")
    setattr(record, "rank_change", change)
    # 排名趋势不再输出；保留空值仅为兼容旧字段。
    setattr(record, "rank_trend", "")
    setattr(record, "product_skc_key", skc_key)
    setattr(record, "style_spu_key", str(product_key or ""))
    setattr(record, "data_week", data_week)

    metadata = record.to_metadata() if hasattr(record, "to_metadata") else {}
    if not isinstance(metadata, dict):
        metadata = {}
    metadata.update(
        {
            "source_page_url": getattr(record, "source_page_url", ""),
            "current_rank": getattr(record, "current_rank", ""),
            "previous_rank": getattr(record, "previous_rank", ""),
            "rank_change": getattr(record, "rank_change", ""),
            "rank_trend": "",
            "product_skc_key": getattr(record, "product_skc_key", ""),
            "style_spu_key": getattr(record, "style_spu_key", ""),
            "data_week": data_week,
        }
    )
    return metadata


def sync_change_context_from_metadata(record: Any, metadata: dict[str, Any]) -> None:
    """check_and_update 会补充上新类型等信息，这里同步回 record 供 Excel 导出。"""
    if not isinstance(metadata, dict):
        return
    for attr, key in [
        ("previous_rank", "previous_rank"),
        ("rank_change", "rank_change"),
        ("new_type", "new_type"),
        ("last_delisted_at", "last_delisted_at"),
        ("relisted_after_delisted", "relisted_after_delisted"),
    ]:
        if key in metadata:
            setattr(record, attr, metadata.get(key, ""))


def make_full_columns(columns_l2: list[str]) -> list[str]:
    """原始排序表列。忽略旧 columns_l2，统一使用已确认的新口径字段。"""
    return list(ORIGINAL_COLUMNS)


def make_new_columns(columns_l2: list[str]) -> list[str]:
    """上新表列。"""
    return list(NEW_COLUMNS)


def make_delisted_columns(columns_l2: list[str]) -> list[str]:
    """下架表列。"""
    return list(DELISTED_COLUMNS)


def mark_relisted_after_delisted(record: Any, baseline_mgr: BaselineManager, baseline_key: str) -> None:
    """如果当前记录是历史下架后重新抓到的商品，在记录上补充下架时间。"""
    if str(getattr(record, "is_new_color", "") or "").strip() != "老款补货":
        return

    baseline_record = baseline_mgr.baseline.get(baseline_key, {})
    if not isinstance(baseline_record, dict):
        return

    last_delisted_at = (
        baseline_record.get("last_delisted_at")
        or baseline_record.get("delisted_at")
        or ""
    )
    setattr(record, "relisted_after_delisted", "是")
    setattr(record, "last_delisted_at", last_delisted_at)
    setattr(record, "new_type", "下架后又上新")

    metadata = baseline_record.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata.update({
        "relisted_after_delisted": "是",
        "last_delisted_at": last_delisted_at,
        "new_type": "下架后又上新",
    })
    baseline_record["metadata"] = metadata


def _apply_delisted_display_fields(record: Any, info: dict[str, Any], key: str) -> None:
    metadata = info.get("metadata", {}) if isinstance(info.get("metadata", {}), dict) else {}
    current_rank = metadata.get("current_rank") or metadata.get("website_rank") or ""
    setattr(record, "delisted_previous_rank", current_rank)
    # 复用 current_rank 字段便于 DataExporter alias 到「下架前排序」。
    setattr(record, "current_rank", current_rank)
    setattr(record, "previous_rank", current_rank)
    setattr(record, "rank_change", "")
    setattr(record, "rank_trend", "")
    setattr(record, "source_page_url", metadata.get("source_page_url", ""))
    setattr(record, "product_skc_key", metadata.get("product_skc_key") or key)
    setattr(record, "style_spu_key", metadata.get("style_spu_key", ""))
    setattr(record, "data_week", metadata.get("data_week", ""))
    setattr(record, "last_seen_at", info.get("last_seen", ""))


def mark_and_build_delisted_records(
    baseline_mgr: BaselineManager,
    active_keys: Iterable[str],
    current_date: str,
    current_time_full: str,
    build_delisted_record: Callable[[BaselineManager, str, dict[str, Any], str], Any],
) -> list[Any]:
    """本次没抓到即认为下架，并构建下架表记录。"""
    newly_delisted = baseline_mgr.mark_missing_as_delisted(active_keys, current_date)
    delisted_records: list[Any] = []
    for key in newly_delisted:
        info = baseline_mgr.baseline.get(key, {})
        if isinstance(info, dict):
            record = build_delisted_record(baseline_mgr, key, info, current_time_full)
            # 给下架表按列名取值使用。
            setattr(record, "delisted_at", info.get("delisted_at", current_date))
            _apply_delisted_display_fields(record, info, key)
            setattr(record, "data_week", iso_week_from_date(current_date))
            delisted_records.append(record)
    return delisted_records


def build_report_sheets(
    full_sheet_name: str,
    records: list[Any],
    delisted_records: list[Any],
    is_initialization_phase: bool,
    columns_l2: list[str],
) -> dict[str, Any]:
    """输出原始排序 / 上新 / 下架三类表。

    初始化阶段也输出上新表/下架表，但行数为空，避免 sheet 缺失；首次全量不误判为上新。
    """
    site_prefix = _site_prefix_from_records(full_sheet_name, records, delisted_records)
    original_sheet_name = f"{site_prefix}_原始排序表"
    new_sheet_name = f"{site_prefix}_上新表"
    delisted_sheet_name = f"{site_prefix}_下架表"

    full_records = sorted(
        list(records),
        key=lambda r: _safe_int(getattr(r, "current_rank", None)) or 999999,
    )
    full_columns = make_full_columns(columns_l2)

    full_payload = {
        "rows": full_records,
        "columns_l2": full_columns,
        "header_l1": _normalize_header_l1(full_columns, "原始排序表"),
    }

    new_columns = make_new_columns(columns_l2)
    delisted_columns = make_delisted_columns(columns_l2)

    if is_initialization_phase:
        new_records = []
        output_delisted_records = []
    else:
        new_records = [
            record for record in full_records
            if str(getattr(record, "is_new_color", "") or "").strip() in NEW_STATUS_VALUES
        ]
        output_delisted_records = sorted(
            list(delisted_records),
            key=lambda r: _safe_int(getattr(r, "current_rank", None)) or 999999,
        )

    return {
        original_sheet_name: full_payload,
        new_sheet_name: {
            "rows": new_records,
            "columns_l2": new_columns,
            "header_l1": _normalize_header_l1(new_columns, "上新表"),
        },
        delisted_sheet_name: {
            "rows": output_delisted_records,
            "columns_l2": delisted_columns,
            "header_l1": _normalize_header_l1(delisted_columns, "下架表"),
        },
    }
