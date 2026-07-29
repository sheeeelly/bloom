"""基线数据管理模块 - 支持新增颜色、老款补货、下架对账与历史基线迁移。

兼容性说明：
1. 保留原 BaselineManager 对外方法与返回值，不影响现有 main_bg/main_ss/main_cl/main_bb/main_hm 调用。
2. check_and_update(product_key, color_name, current_date, metadata=None) 保持不变。
3. mark_missing_as_delisted(active_keys, current_date) 保持不变，同时新增可选安全参数。
4. save_baseline() 改为原子写入，避免写入中断导致基线文件损坏。
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

logger = logging.getLogger(__name__)


class BaselineManager:
    """商品颜色生命周期基线库。

    key 统一为：product_key + ::: + color_name。
    record 格式：
    {
        "first_seen": "YYYY-MM-DD",
        "last_seen": "YYYY-MM-DD",
        "status": "Active" | "Delisted",
        "delisted_at": "YYYY-MM-DD" | "",
        "metadata": {...}
    }
    """

    KEY_SEPARATOR = ":::"
    VALID_STATUS = {"Active", "Delisted"}

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.baseline: dict[str, dict[str, Any]] = self._load_baseline()

    # =========================
    # Key 与日期工具
    # =========================

    @staticmethod
    def _normalize(value: Any, fallback: str = "UNKNOWN") -> str:
        text = str(value or "").strip()
        text = " ".join(text.split())
        return text if text else fallback

    @classmethod
    def _normalize_key_part(cls, value: Any, fallback: str = "UNKNOWN") -> str:
        """用于生命周期 baseline 判断的 key 标准化。

        注意：这里只影响 key，不影响导出展示字段。
        目的：避免 Dusty Blue / dusty blue / DUSTY  Blue 被当成不同颜色，
        导致 baseline 重复、误下架或误补货。
        """
        return cls._normalize(value, fallback=fallback).casefold()

    def _normalize_existing_key(self, key: Any) -> str:
        text = str(key or "").strip()
        if self.KEY_SEPARATOR in text:
            product_key, color_name = text.split(self.KEY_SEPARATOR, 1)
            return self.make_key(product_key, color_name)
        return self._normalize_key_part(text)

    @staticmethod
    def _safe_date(value: Any, fallback: str = "") -> str:
        """只接受 YYYY-MM-DD；异常则返回 fallback。"""
        text = str(value or "").strip()
        if not text:
            return fallback
        try:
            datetime.strptime(text, "%Y-%m-%d")
            return text
        except ValueError:
            return fallback

    def make_key(self, product_key: Any, color_name: Any) -> str:
        return (
            f"{self._normalize_key_part(product_key)}"
            f"{self.KEY_SEPARATOR}"
            f"{self._normalize_key_part(color_name, 'Default')}"
        )

    def split_key(self, key: str) -> tuple[str, str]:
        if self.KEY_SEPARATOR not in key:
            return key, ""
        product_key, color_name = key.split(self.KEY_SEPARATOR, 1)
        return product_key, color_name

    # =========================
    # 基线加载 / 迁移
    # =========================

    def _load_baseline(self) -> dict[str, dict[str, Any]]:
        if not os.path.exists(self.file_path):
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as exc:
            logger.error("加载基线文件失败: %s | %s", self.file_path, exc)
            return {}

        if not isinstance(raw_data, dict):
            logger.warning("基线文件格式不是 dict，已忽略: %s", self.file_path)
            return {}

        migrated = False
        cleaned: dict[str, dict[str, Any]] = {}

        for raw_key, value in raw_data.items():
            key = str(raw_key).strip()
            if not key:
                migrated = True
                continue

            normalized_key = self._normalize_existing_key(key)
            if normalized_key != key:
                migrated = True

            if isinstance(value, str):
                seen_date = self._safe_date(value) or value
                cleaned_record = {
                    "first_seen": seen_date,
                    "last_seen": seen_date,
                    "status": "Active",
                    "delisted_at": "",
                    "metadata": {},
                }
                self._merge_cleaned_record(cleaned, normalized_key, cleaned_record)
                migrated = True
                continue

            if not isinstance(value, dict):
                logger.warning("跳过无法识别的基线记录: %s=%r", key, value)
                migrated = True
                continue

            first_seen = (
                value.get("first_seen")
                or value.get("release_date")
                or value.get("last_seen")
                or ""
            )
            last_seen = value.get("last_seen") or first_seen
            status = value.get("status") or "Active"
            if status not in self.VALID_STATUS:
                status = "Active"

            metadata = value.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
                migrated = True

            cleaned_record = {
                "first_seen": first_seen,
                "last_seen": last_seen,
                "status": status,
                "delisted_at": value.get("delisted_at", "") if status == "Delisted" else "",
                "metadata": metadata,
            }

            # 保留未来扩展字段，避免新版本写入的信息被旧清洗逻辑误删。
            for extra_key, extra_value in value.items():
                if extra_key not in cleaned_record:
                    cleaned_record[extra_key] = extra_value

            self._merge_cleaned_record(cleaned, normalized_key, cleaned_record)
            if cleaned_record != value or normalized_key != key:
                migrated = True

        if migrated:
            logger.info("已将历史基线数据平滑升级为当前生命周期格式: %s", self.file_path)

        return cleaned

    def _merge_cleaned_record(
        self,
        cleaned: dict[str, dict[str, Any]],
        key: str,
        incoming: dict[str, Any],
    ) -> None:
        """合并大小写/空格差异造成的重复 baseline key。"""
        if key not in cleaned:
            cleaned[key] = incoming
            return

        existing = cleaned[key]

        existing_first = self._safe_date(existing.get("first_seen"))
        incoming_first = self._safe_date(incoming.get("first_seen"))
        if existing_first and incoming_first:
            existing["first_seen"] = min(existing_first, incoming_first)
        elif incoming_first and not existing_first:
            existing["first_seen"] = incoming_first

        existing_last = self._safe_date(existing.get("last_seen"))
        incoming_last = self._safe_date(incoming.get("last_seen"))
        if existing_last and incoming_last:
            existing["last_seen"] = max(existing_last, incoming_last)
        elif incoming_last and not existing_last:
            existing["last_seen"] = incoming_last

        # 只要任一重复记录是 Active，就以 Active 为准，避免大小写变化导致误下架。
        if incoming.get("status") == "Active" or existing.get("status") == "Active":
            existing["status"] = "Active"
            existing["delisted_at"] = ""
        else:
            existing["status"] = incoming.get("status") or existing.get("status") or "Delisted"
            existing["delisted_at"] = incoming.get("delisted_at") or existing.get("delisted_at", "")

        existing_metadata = existing.get("metadata") if isinstance(existing.get("metadata"), dict) else {}
        incoming_metadata = incoming.get("metadata") if isinstance(incoming.get("metadata"), dict) else {}
        existing["metadata"] = {**existing_metadata, **incoming_metadata}

        for extra_key, extra_value in incoming.items():
            if extra_key not in existing:
                existing[extra_key] = extra_value

    def is_empty(self) -> bool:
        return len(self.baseline) == 0

    # =========================
    # 状态更新
    # =========================

    def check_and_update(
        self,
        product_key: Any,
        color_name: Any,
        current_date: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """比对并更新当前商品颜色状态。

        返回：
        - 状态标记："是" / "否" / "老款补货"
        - 上新时间：first_seen
        """
        unique_key = self.make_key(product_key, color_name)
        metadata = dict(metadata or {})
        normalized_product_key = self._normalize_key_part(product_key)

        def _same_product_exists_before() -> bool:
            for existing_key in self.baseline.keys():
                existing_product_key, _ = self.split_key(existing_key)
                if existing_product_key == normalized_product_key:
                    return True
            return False

        if unique_key in self.baseline:
            record = self.baseline[unique_key]
            previous_status = record.get("status", "Active")

            release_date = record.get("first_seen") or current_date
            record["first_seen"] = release_date
            record["last_seen"] = current_date
            record["status"] = "Active"
            record["delisted_at"] = ""

            if previous_status == "Delisted":
                # 本轮重新抓到之前已下架的商品颜色：标记为“下架后又上新”，
                # 并保留最近一次下架时间，供上新表展示。
                last_delisted_at = (
                    record.get("delisted_at")
                    or record.get("last_delisted_at")
                    or record.get("last_seen")
                    or ""
                )
                record["last_delisted_at"] = last_delisted_at
                metadata["relisted_after_delisted"] = "是"
                metadata["last_delisted_at"] = last_delisted_at
                metadata["new_type"] = "下架后又上新"

                if metadata:
                    record["metadata"] = metadata

                return "老款补货", release_date

            metadata.setdefault("new_type", "")
            if metadata:
                record["metadata"] = metadata

            return "否", release_date

        product_exists_before = _same_product_exists_before()
        metadata["new_type"] = "新颜色" if product_exists_before else "新 SKC"

        self.baseline[unique_key] = {
            "first_seen": current_date,
            "last_seen": current_date,
            "status": "Active",
            "delisted_at": "",
            "metadata": metadata,
        }
        return "是", current_date

    def mark_missing_as_delisted(
        self,
        active_keys: Iterable[str],
        current_date: str,
        *,
        min_active_count: int | None = None,
        site_name: str = "",
    ) -> list[str]:
        """将本次完整抓取后缺失的 Active key 标记为 Delisted。

        兼容旧调用：mark_missing_as_delisted(active_keys, current_date)。

        新增可选安全保护：
        - min_active_count：如果本次 active key 数低于阈值，直接跳过下架标记，避免接口异常导致误判。
        - site_name：仅用于日志提示。
        """
        active_key_set = set(active_keys)

        if min_active_count is not None and min_active_count > 0 and len(active_key_set) < min_active_count:
            logger.error(
                "%s 下架保护触发：active_keys=%s 低于阈值 min_active_count=%s，跳过 Delisted 标记",
                f"[{site_name}]" if site_name else "",
                len(active_key_set),
                min_active_count,
            )
            return []

        newly_delisted: list[str] = []

        for key, record in self.baseline.items():
            if key in active_key_set:
                continue
            if record.get("status") == "Active":
                record["status"] = "Delisted"
                record["delisted_at"] = current_date
                record["last_delisted_at"] = current_date
                newly_delisted.append(key)

        return newly_delisted

    # =========================
    # 遍历 / 统计
    # =========================

    def iter_delisted(self) -> Iterator[tuple[str, dict[str, Any]]]:
        for key, record in self.baseline.items():
            if record.get("status") == "Delisted":
                yield key, record

    def iter_active(self) -> Iterator[tuple[str, dict[str, Any]]]:
        for key, record in self.baseline.items():
            if record.get("status", "Active") == "Active":
                yield key, record

    def stats(self) -> dict[str, int]:
        active = 0
        delisted = 0
        other = 0
        for record in self.baseline.values():
            status = record.get("status", "Active")
            if status == "Active":
                active += 1
            elif status == "Delisted":
                delisted += 1
            else:
                other += 1
        return {
            "total": len(self.baseline),
            "active": active,
            "delisted": delisted,
            "other": other,
        }

    # =========================
    # 清理 / 保存
    # =========================

    def purge_old_delisted(self, current_date: str, keep_days: int = 180) -> int:
        """删除下架超过 keep_days 的历史记录，避免基线文件无限增长。"""
        try:
            curr_dt = datetime.strptime(current_date, "%Y-%m-%d")
        except ValueError:
            logger.error("current_date 格式错误，跳过 purge_old_delisted: %s", current_date)
            return 0

        deleted = 0

        for key, record in list(self.baseline.items()):
            if record.get("status") != "Delisted":
                continue

            compare_date = record.get("delisted_at") or record.get("last_seen") or record.get("first_seen")
            try:
                compare_dt = datetime.strptime(str(compare_date), "%Y-%m-%d")
            except (TypeError, ValueError):
                continue

            if (curr_dt - compare_dt).days > keep_days:
                del self.baseline[key]
                deleted += 1

        return deleted

    def save_baseline(self, *, create_backup: bool | None = None) -> None:
        """保存基线数据。

        - 默认原子写入：先写临时文件，再 os.replace 覆盖，避免中途异常写坏 JSON。
        - 可通过 BASELINE_CREATE_BACKUP=true 开启 .bak 备份。
        """
        if create_backup is None:
            create_backup = os.getenv("BASELINE_CREATE_BACKUP", "true").strip().lower() in {
                "1",
                "true",
                "yes",
                "y",
            }

        target_path = Path(self.file_path)
        parent = target_path.parent
        parent.mkdir(parents=True, exist_ok=True)

        tmp_path = ""
        try:
            if create_backup and target_path.exists():
                backup_path = target_path.with_suffix(target_path.suffix + ".bak")
                try:
                    shutil.copy2(target_path, backup_path)
                except Exception as exc:
                    logger.warning("创建基线备份失败，继续保存: %s | %s", backup_path, exc)

            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                delete=False,
                dir=str(parent),
                prefix=f".{target_path.name}.",
                suffix=".tmp",
            ) as f:
                tmp_path = f.name
                json.dump(self.baseline, f, ensure_ascii=False, indent=2)

            os.replace(tmp_path, target_path)
            stats = self.stats()
            logger.info(
                "基线数据已保存至 %s，总数=%s 在售=%s 下架=%s",
                self.file_path,
                stats["total"],
                stats["active"],
                stats["delisted"],
            )
        except Exception as exc:
            logger.error("保存基线数据失败: %s | %s", self.file_path, exc)
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
