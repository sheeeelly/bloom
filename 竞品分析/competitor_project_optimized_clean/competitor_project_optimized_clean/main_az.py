"""Azazie BD 数据接入适配器。

工程口径：
- 优先读取内部导出的 CSV / Excel / JSON 商品数据，避免爬 Azazie 前台造成稳定性风险；
- 如果配置 AZ_API_URL，则按 JSON API 读取；
- 输出结构复用现有竞品三表：原始排序表 / 上新表 / 下架表；
- baseline 独立为 azazie_bd_baseline.json，避免和竞品历史混用。
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import requests
from dotenv import load_dotenv

from utils.baseline_manager import BaselineManager
from utils.config import Config
from utils.data_exporter import DataExporter
from utils.product_details import collect_product_detail_text
from utils.product_record import COLUMNS_L2, HEADER_L1_CONFIG, ProductRecord
from utils.report_builder import (
    apply_ranking_context,
    build_report_sheets,
    mark_and_build_delisted_records,
    mark_relisted_after_delisted,
    sync_change_context_from_metadata,
)
from utils.report_history import (
    cleanup_previous_site_reports,
    is_first_site_crawl,
    resolve_current_datetime,
)

logger = logging.getLogger(__name__)


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def _first_present(row: dict[str, Any], aliases: list[str], default: str = "") -> str:
    normalized = {str(key).strip().casefold(): value for key, value in row.items()}
    for alias in aliases:
        value = normalized.get(alias.casefold())
        text = _safe_str(value)
        if text:
            return text
    return default


def _parse_price(value: Any) -> float:
    text = _safe_str(value)
    if not text:
        return 0.0
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _format_price(value: Any) -> str:
    amount = _parse_price(value)
    if amount <= 0:
        return _safe_str(value)
    return f"${amount:.2f}"


def _slugify(value: Any, fallback: str = "unknown") -> str:
    text = _safe_str(value).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or fallback


def _extract_handle(url_or_handle: str) -> str:
    text = _safe_str(url_or_handle)
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        path = urlparse(text).path.strip("/")
        if path:
            return path.split("/")[-1]
    return text.strip("/").split("/")[-1]


def _split_name_color(product_name: str, fallback_color: str = "") -> tuple[str, str]:
    name = _safe_str(product_name)
    color = _safe_str(fallback_color)

    for sep in [" - ", " – ", " | "]:
        if sep in name:
            left, right = name.rsplit(sep, 1)
            if right.strip():
                return left.strip(), right.strip()

    match = re.search(r"\s+in\s+([A-Za-z][A-Za-z0-9 \-/]+)$", name, flags=re.IGNORECASE)
    if match:
        return name[: match.start()].strip(), match.group(1).strip()

    return name, color or "Default"


def _load_rows_from_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Azazie input file not found: {path}")

    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
        return df.fillna("").to_dict(orient="records")
    if suffix == ".csv":
        df = pd.read_csv(path)
        return df.fillna("").to_dict(orient="records")
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for key in ["products", "items", "data", "rows"]:
                if isinstance(data.get(key), list):
                    return [dict(item) for item in data[key] if isinstance(item, dict)]
        if isinstance(data, list):
            return [dict(item) for item in data if isinstance(item, dict)]
        raise ValueError(f"Unsupported Azazie JSON shape: {path}")

    raise ValueError(f"Unsupported Azazie input file type: {path}")


def _load_rows_from_api(url: str, timeout: int) -> list[dict[str, Any]]:
    if not url:
        raise ValueError("AZ_API_URL is empty")
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict):
        for key in ["products", "items", "data", "rows"]:
            if isinstance(data.get(key), list):
                return [dict(item) for item in data[key] if isinstance(item, dict)]
    if isinstance(data, list):
        return [dict(item) for item in data if isinstance(item, dict)]
    raise ValueError("AZ_API_URL returned unsupported JSON shape")


def fetch_all_azazie_products(config: Config) -> list[dict[str, Any]]:
    source = (getattr(config, "az_data_source", "file") or "file").strip().lower()
    timeout = int(getattr(config, "request_timeout", 30) or 30)

    if source in {"api", "internal_api", "url"}:
        return _load_rows_from_api(getattr(config, "az_api_url", ""), timeout)

    input_path = getattr(config, "az_input_path", "") or os.getenv("AZ_INPUT_PATH", "")
    if not input_path:
        logger.warning("AZ_INPUT_PATH 未配置，Azazie 本轮无数据。")
        return []
    return _load_rows_from_file(Path(input_path))


def _to_record(row: dict[str, Any], rank: int, config: Config, current_time_full: str) -> tuple[ProductRecord, str, str]:
    product_url = _first_present(row, ["商品链接", "product_url", "url", "pdp_url", "link"])
    handle = _first_present(row, ["款式 ID / SPU Key", "style_spu_key", "spu_key", "style_id", "handle"])
    handle = handle or _extract_handle(product_url)

    raw_name = _first_present(row, ["商品名称", "product_name", "name", "title", "style_name"])
    raw_style = _first_present(row, ["款式名", "style_label", "款式", "style"])
    raw_color = _first_present(row, ["颜色名称", "color_name", "color", "standard_color"])
    split_style, split_color = _split_name_color(raw_name or raw_style, raw_color)

    style_label = raw_style or split_style or raw_name or handle
    color_name = raw_color or split_color or "Default"
    product_name = raw_name or f"{style_label} - {color_name}"

    if not handle:
        handle = _slugify(style_label)
    if not product_url:
        product_url = f"{getattr(config, 'az_base_url', 'https://www.azazie.com').rstrip('/')}/{handle}"

    original_price = _first_present(row, ["标价", "original_price", "compare_at_price", "msrp", "list_price", "price"])
    sale_price = _first_present(row, ["售价", "sale_price", "current_price", "price"])
    if not sale_price:
        sale_price = original_price

    original_amount = _parse_price(original_price)
    sale_amount = _parse_price(sale_price)
    if original_amount <= 0:
        original_amount = sale_amount
    discount_type = "打折" if original_amount > sale_amount > 0 else "无折扣"

    detail_text = _first_present(row, ["商品详情描述", "detail_text", "description", "body_html", "details"])
    if not detail_text:
        detail_text = collect_product_detail_text(row)

    current_rank = _first_present(row, ["排序", "rank", "current_rank", "position"])
    rank_value = int(_parse_price(current_rank)) if _parse_price(current_rank) > 0 else rank

    record = ProductRecord(
        site_name="Azazie",
        brand=_first_present(row, ["品牌", "brand", "vendor"], "Azazie"),
        category=_first_present(row, ["类目", "category"], getattr(config, "az_category", "Bridesmaid Dresses")),
        source_page_url=getattr(config, "az_collection_url", ""),
        current_rank=rank_value,
        style_label=style_label,
        product_url=product_url,
        product_name=product_name,
        color_name=color_name,
        size=_first_present(row, ["尺码", "size", "sizes", "available_sizes"], "未获取"),
        main_image_url=_first_present(row, ["主图", "main_image_url", "image", "image_url", "featured_image"]),
        original_price=_format_price(original_amount),
        sale_price=_format_price(sale_amount),
        discount_type=discount_type,
        stock_type=_first_present(row, ["定制/现货", "stock_type", "stock_status", "availability"], "现货"),
        detail_text=detail_text,
        fabric_name=_first_present(row, ["fabric_name", "面料", "fabric"]),
        aesthetic_tag=_first_present(row, ["aesthetic_tag", "设计元素", "style_tag"]),
        length=_first_present(row, ["length", "长度"]),
        neckline=_first_present(row, ["neckline", "领型"]),
        scrape_time=current_time_full,
        status="Active",
    )

    return record, handle, color_name


def _build_delisted_record(
    baseline_mgr: BaselineManager,
    key: str,
    info: dict[str, Any],
    scrape_time: str,
) -> ProductRecord:
    metadata = info.get("metadata", {}) if isinstance(info.get("metadata"), dict) else {}
    fallback_product_name, fallback_color_name = baseline_mgr.split_key(key)

    return ProductRecord(
        site_name=metadata.get("site_name", "Azazie"),
        brand=metadata.get("brand", "Azazie"),
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
        status="Delisted",
    )


def run_az() -> None:
    load_dotenv(override=True)
    config = Config.load()
    baseline_mgr = BaselineManager(getattr(config, "az_baseline_path", "azazie_bd_baseline.json"))
    output_dir = getattr(config, "output_dir", "output")
    report_prefix = "azazie_report_"
    sheet_name = getattr(config, "az_sheet_name", "AZ_伴娘服总表")

    current_dt = resolve_current_datetime()
    current_date = current_dt.strftime("%Y-%m-%d")
    current_time_full = current_dt.strftime("%Y-%m-%d %H:%M:%S")
    is_initialization_phase = is_first_site_crawl(output_dir, report_prefix, baseline_mgr)

    rows = fetch_all_azazie_products(config)
    if not rows:
        logger.warning("Azazie 没有读取到商品数据，跳过导出和 baseline 更新。")
        return

    records: list[ProductRecord] = []
    active_keys: set[str] = set()

    for index, row in enumerate(rows, start=1):
        record, product_key, color_name = _to_record(row, index, config, current_time_full)
        baseline_key = baseline_mgr.make_key(product_key, color_name)

        report_metadata = apply_ranking_context(
            record,
            baseline_mgr,
            baseline_key,
            product_key=product_key,
            current_rank=record.current_rank or index,
            source_page_url=getattr(config, "az_collection_url", ""),
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

    delisted_records = mark_and_build_delisted_records(
        baseline_mgr=baseline_mgr,
        active_keys=active_keys,
        current_date=current_date,
        current_time_full=current_time_full,
        build_delisted_record=_build_delisted_record,
    )

    baseline_mgr.save_baseline()

    report_sheets = build_report_sheets(
        full_sheet_name=sheet_name,
        records=records,
        delisted_records=delisted_records,
        is_initialization_phase=is_initialization_phase,
        columns_l2=COLUMNS_L2,
    )

    filepath = DataExporter().export_multiple_sheets(
        report_sheets,
        output_dir,
        prefix=report_prefix,
        header_l1=HEADER_L1_CONFIG,
        columns_l2=COLUMNS_L2,
    )
    cleanup_previous_site_reports(output_dir, report_prefix, filepath)
    logger.info("Azazie 数据导出完成: %s", filepath)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_az()
