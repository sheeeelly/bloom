"""Google Sheets 数据同步模块。

兼容：
1. 原有 ProductRecord / SSProductRecord 等 dataclass 记录对象。
2. 新增品牌字段后的统一表结构。
3. Six Stories 颜色完整性检查表等 dict/list 行数据。
4. 行列数不一致时自动补齐/截断，避免因为局部 sheet 结构不同导致同步失败。
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import gspread
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)


def _gsheet_retry_max_attempts() -> int:
    try:
        return max(1, int(os.getenv("GSHEET_RETRY_ATTEMPTS", "5")))
    except ValueError:
        return 5


def _gsheet_retry_sleep_seconds() -> float:
    try:
        return max(0.0, float(os.getenv("GSHEET_RETRY_BASE_SLEEP_SECONDS", "5")))
    except ValueError:
        return 5.0


def _is_retryable_gsheet_error(exc: Exception) -> bool:
    """Google Sheets 偶发 429/5xx 时允许重试。"""
    status_code = None
    response = getattr(exc, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)

    text = str(exc).lower()
    if status_code in {408, 429, 500, 502, 503, 504}:
        return True
    return any(token in text for token in ["[429]", "[500]", "[502]", "[503]", "[504]", "temporarily unavailable", "service is currently unavailable"])


def _with_gsheet_retry(action_name: str, func):
    attempts = _gsheet_retry_max_attempts()
    base_sleep = _gsheet_retry_sleep_seconds()

    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts or not _is_retryable_gsheet_error(exc):
                raise
            wait = base_sleep * attempt
            logger.warning(
                "Google Sheets %s 临时失败，准备重试: attempt=%s/%s wait=%.1fs error=%s",
                action_name,
                attempt,
                attempts,
                wait,
                exc,
            )
            time.sleep(wait)

    raise last_exc  # pragma: no cover


class GSheetSync:
    def __init__(self, spreadsheet_id: str, credentials_json: str):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]

        if os.path.exists(credentials_json):
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                credentials_json,
                scope,
            )
        else:
            try:
                creds_dict = json.loads(credentials_json)
                creds = ServiceAccountCredentials.from_json_keyfile_dict(
                    creds_dict,
                    scope,
                )
            except json.JSONDecodeError as exc:
                raise FileNotFoundError(
                    "GSHEET_CREDENTIALS_JSON 既不是有效文件路径，也不是有效 JSON 字符串"
                ) from exc

        self.client = gspread.authorize(creds)
        self.spreadsheet = _with_gsheet_retry(
            "open_by_key",
            lambda: self.client.open_by_key(spreadsheet_id),
        )

    @staticmethod
    def _safe_sheet_name(name: str) -> str:
        """Google Sheets 工作表名最长 100 字符。"""
        text = str(name or "Sheet").strip()
        return text[:100] or "Sheet"

    @staticmethod
    def _normalize_cell_value(value: Any) -> Any:
        """把复杂对象转换成 Google Sheets 可写入的值。"""
        if value is None:
            return ""

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, (list, tuple, set)):
            return " | ".join(str(v) for v in value if v is not None)

        if isinstance(value, dict):
            try:
                return json.dumps(value, ensure_ascii=False)
            except TypeError:
                return str(value)

        return str(value)

    @classmethod
    def _normalize_row(cls, row: list[Any], expected_cols: int) -> list[Any]:
        """行长度与表头对齐：短了补空，长了截断。"""
        normalized = [cls._normalize_cell_value(value) for value in row]

        if len(normalized) < expected_cols:
            normalized.extend([""] * (expected_cols - len(normalized)))

        if len(normalized) > expected_cols:
            normalized = normalized[:expected_cols]

        return normalized

    @staticmethod
    def _value_from_mapping(data: dict[str, Any], header: str) -> Any:
        aliases = {
            "网站名": "site_name",
            "品牌": "brand",
            "类目": "category",
            "排序": "current_rank",
            "排名涨跌": "rank_change",
            "商品唯一键 / SKC Key": "product_skc_key",
            "款式 ID / SPU Key": "style_spu_key",
            "款式名": "style_label",
            "商品链接": "product_url",
            "商品名称": "product_name",
            "颜色名称": "color_name",
            "尺码": "size",
            "颜色数量": "color_count",
            "颜色列表": "color_list",
            "主图": "main_image_url",
            "标价": "original_price",
            "售价": "sale_price",
            "折扣类型": "discount_type",
            "定制/现货": "stock_type",
            "商品详情描述": "detail_text",
            "爬取时间": "scrape_time",
            "数据周次": "data_week",
            "上新时间": "release_date",
            "上新类型": "new_type",
            "最近下架时间": "last_delisted_at",
            "下架前排序": "current_rank",
            "下架前标价": "original_price",
            "下架前售价": "sale_price",
            "下架前折扣类型": "discount_type",
            "最近一次出现时间": "last_seen_at",
            "下架时间": "delisted_at",
            "是否异常": "is_abnormal",
            "异常原因": "abnormal_reason",
            "代表链接": "representative_url",
        }
        if header in data:
            return data.get(header, "")
        alias = aliases.get(header)
        if alias:
            return data.get(alias, "")
        return ""

    @classmethod
    def _record_to_row(cls, record: Any, headers: list[str]) -> list[Any]:
        """兼容 record 对象、dict、list/tuple。"""
        if hasattr(record, "to_metadata") and callable(record.to_metadata):
            metadata = record.to_metadata()
            if not isinstance(metadata, dict):
                metadata = {}
            if hasattr(record, "delisted_at") and "delisted_at" not in metadata:
                metadata["delisted_at"] = getattr(record, "delisted_at", "")
            return [cls._value_from_mapping(metadata, header) for header in headers]

        if hasattr(record, "to_row") and callable(record.to_row):
            return list(record.to_row())

        if isinstance(record, dict):
            return [cls._value_from_mapping(record, header) for header in headers]

        if isinstance(record, (list, tuple)):
            return list(record)

        # dataclass / 普通对象兜底：按 header 名尝试取属性。
        return [getattr(record, header, "") for header in headers]

    def _build_data_matrix(
        self,
        product_records: list[Any],
        headers: list[str],
        *,
        strict_columns: bool = False,
    ) -> list[list[Any]]:
        """生成待写入矩阵。

        strict_columns=false 时自动补齐/截断行数据，避免不同 sheet 的列结构不一致导致同步中断。
        strict_columns=true 时保持旧版严格校验行为。
        """
        headers = [str(header) for header in headers]
        expected_cols = len(headers)
        data_matrix: list[list[Any]] = [headers]

        for index, record in enumerate(product_records, start=1):
            row = self._record_to_row(record, headers)

            if strict_columns and len(row) != expected_cols:
                raise ValueError(
                    f"Google Sheets 同步失败：第 {index} 条数据列数为 {len(row)}，"
                    f"但表头列数为 {expected_cols}。请检查 product_record.py 的 to_row() 和 COLUMNS_L2 是否一致。"
                )

            if len(row) != expected_cols:
                logger.debug(
                    "Google Sheets 行列数自动对齐：sheet row=%s actual=%s expected=%s",
                    index,
                    len(row),
                    expected_cols,
                )

            data_matrix.append(self._normalize_row(row, expected_cols))

        return data_matrix

    def _get_or_create_worksheet(
        self,
        sheet_name: str,
        rows: int,
        cols: int,
    ):
        safe_name = self._safe_sheet_name(sheet_name)

        try:
            return _with_gsheet_retry(
                f"worksheet({safe_name})",
                lambda: self.spreadsheet.worksheet(safe_name),
            )
        except gspread.exceptions.WorksheetNotFound:
            worksheet = _with_gsheet_retry(
                f"add_worksheet({safe_name})",
                lambda: self.spreadsheet.add_worksheet(
                    title=safe_name,
                    rows=max(rows, 100),
                    cols=max(cols, 20),
                ),
            )
            logger.info("新建工作表: %s", safe_name)
            return worksheet

    def sync_data(
        self,
        sheet_name: str,
        product_records: list[Any],
        headers: list[str],
        *,
        strict_columns: bool | None = None,
    ) -> None:
        """清空并同步数据到指定工作表。

        兼容旧调用：sync_data(sheet_name, product_records, headers)
        新增可选参数 strict_columns：
        - True：列数不一致时报错，保持旧版强校验。
        - False：自动补齐/截断，适合颜色检查表、dict/list 行。
        - None：从 GSHEET_STRICT_COLUMNS 环境变量读取，默认 False。
        """
        if strict_columns is None:
            strict_columns = os.getenv("GSHEET_STRICT_COLUMNS", "false").strip().lower() in {
                "1",
                "true",
                "yes",
                "y",
            }

        try:
            headers = [str(header) for header in headers]
            product_records = product_records or []

            data_matrix = self._build_data_matrix(
                product_records,
                headers,
                strict_columns=strict_columns,
            )

            worksheet = self._get_or_create_worksheet(
                sheet_name=sheet_name,
                rows=max(len(data_matrix), 1),
                cols=max(len(headers), 1),
            )

            _with_gsheet_retry(
                f"resize({self._safe_sheet_name(sheet_name)})",
                lambda: worksheet.resize(
                    rows=max(len(data_matrix), 1),
                    cols=max(len(headers), 1),
                ),
            )

            _with_gsheet_retry(
                f"clear({self._safe_sheet_name(sheet_name)})",
                lambda: worksheet.clear(),
            )

            def do_update():
                try:
                    return worksheet.update(values=data_matrix, range_name="A1")
                except TypeError:
                    return worksheet.update("A1", data_matrix)

            _with_gsheet_retry(
                f"update({self._safe_sheet_name(sheet_name)})",
                do_update,
            )

            logger.info(
                "成功同步 %d 条数据到 Google Sheets: [%s]",
                len(product_records),
                self._safe_sheet_name(sheet_name),
            )

        except Exception as exc:
            logger.error("同步到 Google Sheets 失败: %s", exc, exc_info=True)
            raise


    @staticmethod
    def _site_prefix_from_sheet_name(full_sheet_name: str) -> str:
        """从“CL_伴娘服总表”提取“CL”，用于生成 CL_本次上新 / CL_本次下架。"""
        name = str(full_sheet_name or "竞品").strip()
        if "_" in name:
            return name.split("_", 1)[0].strip() or name
        for suffix in ["伴娘服总表", "商品总表", "总表"]:
            if name.endswith(suffix):
                return name[: -len(suffix)].strip("_ -") or name
        return name

    @classmethod
    def _change_sheet_name(cls, full_sheet_name: str, change_type: str) -> str:
        prefix = cls._site_prefix_from_sheet_name(full_sheet_name)
        return f"{prefix}_本次{change_type}"

    @staticmethod
    def _payload_rows_and_headers(payload: Any, default_headers: list[str] | None = None) -> tuple[list[Any], list[str]]:
        if isinstance(payload, dict):
            rows = payload.get("rows")
            if rows is None:
                rows = payload.get("records")
            if rows is None:
                rows = payload.get("data")
            if rows is None:
                rows = []
            headers = payload.get("headers") or payload.get("columns_l2") or payload.get("columns") or default_headers or []
            return list(rows or []), [str(h) for h in headers]
        return list(payload or []), [str(h) for h in (default_headers or [])]

    @classmethod
    def _record_to_metadata(cls, record: Any) -> dict[str, Any]:
        if hasattr(record, "to_metadata") and callable(record.to_metadata):
            metadata = record.to_metadata()
            if isinstance(metadata, dict):
                metadata = dict(metadata)
            else:
                metadata = {}
        elif isinstance(record, dict):
            metadata = dict(record)
        else:
            metadata = {}

        if hasattr(record, "delisted_at") and "delisted_at" not in metadata:
            metadata["delisted_at"] = getattr(record, "delisted_at", "")
        return metadata

    def _build_change_history_rows(
        self,
        *,
        site_name: str,
        change_type: str,
        records: list[Any],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for record in records or []:
            metadata = self._record_to_metadata(record)
            rows.append(
                {
                    "记录时间": metadata.get("scrape_time") or metadata.get("爬取时间") or "",
                    "网站": metadata.get("site_name") or metadata.get("网站名") or site_name,
                    "变化类型": change_type,
                    "商品名称": metadata.get("product_name") or metadata.get("商品名称") or "",
                    "颜色名称": metadata.get("color_name") or metadata.get("颜色名称") or "",
                    "商品链接": metadata.get("product_url") or metadata.get("商品链接") or "",
                    "款式名": metadata.get("style_label") or metadata.get("款式名") or "",
                    "标价": metadata.get("original_price") or metadata.get("标价") or "",
                    "售价": metadata.get("sale_price") or metadata.get("售价") or "",
                    "上新时间": metadata.get("release_date") or metadata.get("上新时间") or "",
                    "下架时间": metadata.get("delisted_at") or metadata.get("下架时间") or "",
                }
            )
        return rows

    def append_data(
        self,
        sheet_name: str,
        records: list[Any],
        headers: list[str],
        *,
        ensure_header: bool = True,
    ) -> None:
        """向指定工作表追加数据，用于沉淀“竞品变动历史”。"""
        headers = [str(header) for header in headers]
        records = records or []
        if not records:
            return

        worksheet = self._get_or_create_worksheet(
            sheet_name=sheet_name,
            rows=max(len(records) + 1, 100),
            cols=max(len(headers), 20),
        )

        if ensure_header:
            existing_header = _with_gsheet_retry(
                f"row_values({self._safe_sheet_name(sheet_name)})",
                lambda: worksheet.row_values(1),
            )
            if not existing_header:
                _with_gsheet_retry(
                    f"update_header({self._safe_sheet_name(sheet_name)})",
                    lambda: worksheet.update(values=[headers], range_name="A1"),
                )
            elif [str(v) for v in existing_header[: len(headers)]] != headers:
                logger.warning(
                    "Google Sheets 历史表表头与当前配置不一致，仍继续追加: sheet=%s",
                    self._safe_sheet_name(sheet_name),
                )

        data_rows = [
            self._normalize_row(self._record_to_row(record, headers), len(headers))
            for record in records
        ]
        _with_gsheet_retry(
            f"append_rows({self._safe_sheet_name(sheet_name)})",
            lambda: worksheet.append_rows(data_rows, value_input_option="USER_ENTERED"),
        )
        logger.info(
            "成功追加 %d 条数据到 Google Sheets: [%s]",
            len(records),
            self._safe_sheet_name(sheet_name),
        )

    def sync_competitor_report(
        self,
        full_sheet_name: str,
        report_sheets: dict[str, Any],
        *,
        history_sheet_name: str | None = None,
        append_history: bool | None = None,
    ) -> None:
        """同步竞品报表到 Google Sheets。

        输出规则：
        - 商品总表：沿用配置的 full_sheet_name，例如 CL_伴娘服总表。
        - 上新表：按网站前缀生成，例如 CL_本次上新。
        - 下架表：按网站前缀生成，例如 CL_本次下架。
        - 变动历史：追加到“竞品变动历史”，用于后续周报汇总。
        """
        if append_history is None:
            append_history = os.getenv("GSHEET_APPEND_CHANGE_HISTORY", "true").strip().lower() in {
                "1",
                "true",
                "yes",
                "y",
            }
        if history_sheet_name is None:
            history_sheet_name = os.getenv("GSHEET_CHANGE_HISTORY_SHEET_NAME", "竞品变动历史")

        site_prefix = self._site_prefix_from_sheet_name(full_sheet_name)
        name_map = {
            "上新表": self._change_sheet_name(full_sheet_name, "上新"),
            "下架表": self._change_sheet_name(full_sheet_name, "下架"),
        }

        new_records: list[Any] = []
        delisted_records: list[Any] = []

        for raw_sheet_name, payload in (report_sheets or {}).items():
            rows, headers = self._payload_rows_and_headers(payload)
            if not headers:
                logger.warning("跳过 Google Sheets 同步：sheet=%s 缺少 headers", raw_sheet_name)
                continue

            target_sheet_name = name_map.get(raw_sheet_name, raw_sheet_name)
            self.sync_data(target_sheet_name, rows, headers=headers)

            if raw_sheet_name == "上新表" or str(raw_sheet_name).endswith("_上新表"):
                new_records = rows
            elif raw_sheet_name == "下架表" or str(raw_sheet_name).endswith("_下架表"):
                delisted_records = rows

        if append_history and (new_records or delisted_records):
            history_headers = [
                "记录时间",
                "网站",
                "变化类型",
                "商品名称",
                "颜色名称",
                "商品链接",
                "款式名",
                "标价",
                "售价",
                "上新时间",
                "下架时间",
            ]
            history_rows = []
            history_rows.extend(
                self._build_change_history_rows(
                    site_name=site_prefix,
                    change_type="上新",
                    records=new_records,
                )
            )
            history_rows.extend(
                self._build_change_history_rows(
                    site_name=site_prefix,
                    change_type="下架",
                    records=delisted_records,
                )
            )
            self.append_data(history_sheet_name, history_rows, headers=history_headers)

    def sync_multiple_sheets(
        self,
        sheets_data: dict[str, Any],
        default_headers: list[str] | None = None,
        *,
        strict_columns: bool | None = None,
        sleep_seconds: float | None = None,
    ) -> None:
        """同步多个 sheet。

        支持两种结构：
        1. {"Sheet1": records}
        2. {"颜色完整性检查": {"rows": rows, "headers": headers}}
        """
        if sleep_seconds is None:
            sleep_seconds = float(os.getenv("GSHEET_SYNC_SLEEP_SECONDS", "0.3"))

        for sheet_name, payload in (sheets_data or {}).items():
            if isinstance(payload, dict):
                rows = payload.get("rows") or payload.get("records") or []
                headers = payload.get("headers") or payload.get("columns_l2") or default_headers or []
            else:
                rows = payload or []
                headers = default_headers or []

            if not headers:
                logger.warning("跳过 Google Sheets 同步：sheet=%s 缺少 headers", sheet_name)
                continue

            self.sync_data(
                sheet_name=sheet_name,
                product_records=rows,
                headers=headers,
                strict_columns=strict_columns,
            )

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
