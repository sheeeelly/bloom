from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from ai_assistant.pinecone_upsert import normalize_columns, read_sheet_with_auto_header


ORIGINAL_SHEET_KEYWORD = "原始排序表"
NEW_SHEET_KEYWORD = "上新表"
DELISTED_SHEET_KEYWORD = "下架表"
AZ_SITE_NAMES = {"azazie", "az"}


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def _safe_float(value: Any) -> float | None:
    text = re.sub(r"[^0-9.\-]", "", _safe_str(value))
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _safe_rank(value: Any) -> int | None:
    amount = _safe_float(value)
    if amount is None:
        return None
    return int(amount)


def _is_azazie(site: Any) -> bool:
    return _safe_str(site).casefold() in AZ_SITE_NAMES


def _read_matching_sheets(input_path: Path, sheet_keyword: str) -> pd.DataFrame:
    excel_files = (
        sorted(file for file in input_path.glob("*.xlsx") if not file.name.startswith("~$"))
        if input_path.is_dir()
        else [input_path]
    )

    frames: list[pd.DataFrame] = []
    for excel_file in excel_files:
        if not excel_file.exists():
            continue
        xls = pd.ExcelFile(excel_file)
        for sheet_name in xls.sheet_names:
            if sheet_keyword not in sheet_name:
                continue
            df = read_sheet_with_auto_header(excel_file, sheet_name)
            df["source_file"] = excel_file.name
            df["source_sheet"] = sheet_name
            frames.append(normalize_columns(df))

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _value_counts(df: pd.DataFrame, column: str, limit: int = 15) -> dict[str, int]:
    if column not in df.columns or df.empty:
        return {}
    series = (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
    )
    return {str(key): int(value) for key, value in series.value_counts().head(limit).to_dict().items()}


def _price_summary(df: pd.DataFrame) -> dict[str, Any]:
    if "售价" not in df.columns or df.empty:
        return {"count": 0, "min": None, "max": None, "avg": None, "bands": {}}

    prices = [
        price for price in (_safe_float(value) for value in df["售价"].tolist())
        if price is not None and price > 0
    ]
    if not prices:
        return {"count": 0, "min": None, "max": None, "avg": None, "bands": {}}

    bands = {
        "0-100": 0,
        "100-150": 0,
        "150-200": 0,
        "200-300": 0,
        "300+": 0,
    }
    for price in prices:
        if price < 100:
            bands["0-100"] += 1
        elif price < 150:
            bands["100-150"] += 1
        elif price < 200:
            bands["150-200"] += 1
        elif price < 300:
            bands["200-300"] += 1
        else:
            bands["300+"] += 1

    return {
        "count": len(prices),
        "min": round(min(prices), 2),
        "max": round(max(prices), 2),
        "avg": round(sum(prices) / len(prices), 2),
        "bands": bands,
    }


def _rank_movers(df: pd.DataFrame, limit: int = 10) -> dict[str, list[dict[str, Any]]]:
    if "排名涨跌" not in df.columns or df.empty:
        return {"up": [], "down": []}

    temp = df.copy()
    temp["_rank_change_num"] = temp["排名涨跌"].apply(_safe_rank)
    temp = temp[temp["_rank_change_num"].notna()]

    def row_payload(row: pd.Series) -> dict[str, Any]:
        return {
            "site": _safe_str(row.get("网站名")),
            "rank": _safe_str(row.get("排序")),
            "rank_change": _safe_str(row.get("排名涨跌")),
            "product_name": _safe_str(row.get("商品名称")),
            "color": _safe_str(row.get("颜色名称")),
            "price": _safe_str(row.get("售价")),
            "url": _safe_str(row.get("商品链接")),
        }

    up = temp[temp["_rank_change_num"] > 0].sort_values("_rank_change_num", ascending=False).head(limit)
    down = temp[temp["_rank_change_num"] < 0].sort_values("_rank_change_num", ascending=True).head(limit)
    return {
        "up": [row_payload(row) for _, row in up.iterrows()],
        "down": [row_payload(row) for _, row in down.iterrows()],
    }


def _site_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty or "网站名" not in df.columns:
        return []

    summaries: list[dict[str, Any]] = []
    for site, site_df in df.groupby("网站名", dropna=False):
        site_name = _safe_str(site) or "未知网站"
        summaries.append(
            {
                "site": site_name,
                "product_count": int(len(site_df)),
                "top_colors": _value_counts(site_df, "颜色名称", 10),
                "price": _price_summary(site_df),
                "rank_movers": _rank_movers(site_df, 5),
            }
        )
    return summaries


def _coverage_gap(az_df: pd.DataFrame, competitor_df: pd.DataFrame, column: str, limit: int = 15) -> dict[str, Any]:
    az_values = set(_value_counts(az_df, column, 9999).keys())
    competitor_counts = _value_counts(competitor_df, column, 9999)
    missing = {
        key: value
        for key, value in sorted(competitor_counts.items(), key=lambda item: item[1], reverse=True)
        if key not in az_values
    }
    az_only = {
        key: value
        for key, value in _value_counts(az_df, column, 9999).items()
        if key not in competitor_counts
    }
    return {
        "missing_in_azazie": dict(list(missing.items())[:limit]),
        "azazie_only": dict(list(az_only.items())[:limit]),
    }


def build_cross_site_comparison(input_path: Path) -> dict[str, Any]:
    original_df = _read_matching_sheets(input_path, ORIGINAL_SHEET_KEYWORD)
    new_df = _read_matching_sheets(input_path, NEW_SHEET_KEYWORD)
    delisted_df = _read_matching_sheets(input_path, DELISTED_SHEET_KEYWORD)

    if original_df.empty:
        return {
            "input": str(input_path),
            "has_data": False,
            "error": "No original ranking sheets found",
        }

    az_mask = original_df["网站名"].apply(_is_azazie) if "网站名" in original_df.columns else pd.Series([False] * len(original_df))
    az_df = original_df[az_mask].copy()
    competitor_df = original_df[~az_mask].copy()

    return {
        "input": str(input_path),
        "has_data": True,
        "total_rows": int(len(original_df)),
        "azazie_rows": int(len(az_df)),
        "competitor_rows": int(len(competitor_df)),
        "site_summaries": _site_summary(original_df),
        "overall_top_colors": _value_counts(original_df, "颜色名称", 15),
        "competitor_top_colors": _value_counts(competitor_df, "颜色名称", 15),
        "azazie_top_colors": _value_counts(az_df, "颜色名称", 15),
        "color_gap": _coverage_gap(az_df, competitor_df, "颜色名称", 15),
        "price": {
            "azazie": _price_summary(az_df),
            "competitors": _price_summary(competitor_df),
        },
        "rank_movers": _rank_movers(original_df, 10),
        "new_summary": {
            "rows": int(len(new_df)),
            "by_site": _value_counts(new_df, "网站名", 20),
            "top_colors": _value_counts(new_df, "颜色名称", 15),
        },
        "delisted_summary": {
            "rows": int(len(delisted_df)),
            "by_site": _value_counts(delisted_df, "网站名", 20),
            "top_colors": _value_counts(delisted_df, "颜色名称", 15),
        },
    }


def write_comparison_json(input_path: Path, output_path: Path) -> dict[str, Any]:
    comparison = build_cross_site_comparison(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return comparison


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Azazie vs competitor comparison JSON.")
    parser.add_argument("--input", required=True, help="Excel 文件或目录，例如 output")
    parser.add_argument("--output", required=True, help="输出 JSON 路径")
    args = parser.parse_args()

    write_comparison_json(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
