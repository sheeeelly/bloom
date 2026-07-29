"""本次运行内延迟重试队列。

设计目标：
1. 主抓取流程遇到可重试错误时不直接丢数据，而是放入队列；
2. 队列按退避时间稍后重试；
3. 成功后通过 on_success 回填到当前内存对象；
4. 导出 Excel 前 drain 队列，让最终表尽量拿到补抓后的结果；
5. 失败任务写入 runtime/retry_queue，便于排查和后续升级 Redis/消息队列。

第一阶段为本地脚本友好的 in-memory queue + JSON/JSONL 运行日志。
后续如要升级企业级 Redis/Celery，只需要替换本模块的 backend。

本版新增 run_id：
- 同一次 Python 进程运行内，所有 RetryQueue 共用一个 run_id；
- retry event / failed tasks 文件名带 run_id，避免不同运行之间互相覆盖；
- DataExporter 只收集当前 run_id 对应的失败任务，避免历史失败任务污染本次 Excel。
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from utils.retry_errors import NonRetryableTaskError, RetryableTaskError, is_retryable_exception

logger = logging.getLogger(__name__)

Handler = Callable[[], Any]
OnSuccess = Callable[[Any], None]
AcceptResult = Callable[[Any], bool]

# 进程级 run_id。不要在模块 import 时直接生成，避免没有使用 retry queue 的脚本也产生 run_id。
_PROCESS_RETRY_RUN_ID: str | None = None


def _sanitize_for_filename(value: str) -> str:
    """把 run_id/site_key 等清洗成安全文件名片段。"""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip())
    return cleaned.strip("._-") or "unknown"


def _new_retry_run_id() -> str:
    """生成一个足够可读、可排序、低冲突的运行 ID。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{ts}_{os.getpid()}_{uuid.uuid4().hex[:8]}"


def get_retry_run_id(*, create_if_missing: bool = True) -> str:
    """返回本进程 retry run_id。

    优先级：
    1. 环境变量 RETRY_RUN_ID：适合外部调度系统主动指定；
    2. 本进程内已经生成的 _PROCESS_RETRY_RUN_ID；
    3. create_if_missing=True 时自动生成，并写回 os.environ，保证后续模块可拿到同一个值。

    当 create_if_missing=False 且当前没有 run_id 时，返回空字符串。
    DataExporter 会用这个模式避免为了收集失败任务而凭空生成新 run_id。
    """
    global _PROCESS_RETRY_RUN_ID

    env_run_id = os.getenv("RETRY_RUN_ID", "").strip()
    if env_run_id:
        _PROCESS_RETRY_RUN_ID = _sanitize_for_filename(env_run_id)
        os.environ["RETRY_RUN_ID"] = _PROCESS_RETRY_RUN_ID
        return _PROCESS_RETRY_RUN_ID

    if _PROCESS_RETRY_RUN_ID:
        return _PROCESS_RETRY_RUN_ID

    if not create_if_missing:
        return ""

    _PROCESS_RETRY_RUN_ID = _new_retry_run_id()
    os.environ["RETRY_RUN_ID"] = _PROCESS_RETRY_RUN_ID
    return _PROCESS_RETRY_RUN_ID


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return float(raw)
    except Exception:
        return default


@dataclass
class RetrySettings:
    enabled: bool = True
    queue_dir: str = "runtime/retry_queue"
    max_attempts: int = 4
    delay_seconds: float = 10.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 90.0
    drain_max_wait_seconds: float = 600.0
    drain_before_export: bool = True

    @classmethod
    def from_env(cls) -> "RetrySettings":
        return cls(
            enabled=_env_bool("ENABLE_ASYNC_RETRY_QUEUE", True),
            queue_dir=os.getenv("RETRY_QUEUE_DIR", "runtime/retry_queue").strip() or "runtime/retry_queue",
            max_attempts=max(1, _env_int("RETRY_QUEUE_MAX_ATTEMPTS", 4)),
            delay_seconds=max(0.0, _env_float("RETRY_DELAY_SECONDS", 10.0)),
            backoff_multiplier=max(1.0, _env_float("RETRY_BACKOFF_MULTIPLIER", 2.0)),
            max_delay_seconds=max(1.0, _env_float("RETRY_MAX_DELAY_SECONDS", 90.0)),
            drain_max_wait_seconds=max(1.0, _env_float("RETRY_DRAIN_MAX_WAIT_SECONDS", 600.0)),
            drain_before_export=_env_bool("RETRY_DRAIN_BEFORE_EXPORT", True),
        )


@dataclass
class RetryTask:
    site_key: str
    task_type: str
    identity_key: str
    payload: dict[str, Any]
    handler: Handler
    run_id: str
    on_success: OnSuccess | None = None
    accept_result: AcceptResult | None = None
    max_attempts: int = 4
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    attempts: int = 0
    next_run_at: float = field(default_factory=time.time)
    status: str = "queued"
    last_error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "site_key": self.site_key,
            "task_type": self.task_type,
            "identity_key": self.identity_key,
            "payload": self.payload,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "next_run_at": round(self.next_run_at, 3),
            "status": self.status,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class RetryQueue:
    """本次运行内 retry queue。"""

    def __init__(self, site_key: str, settings: RetrySettings | None = None, run_id: str | None = None) -> None:
        self.site_key = site_key
        self.settings = settings or RetrySettings.from_env()
        self.run_id = _sanitize_for_filename(run_id) if run_id else get_retry_run_id()
        self._tasks: list[RetryTask] = []
        self._lock = threading.Lock()
        self._summary = {"queued": 0, "success": 0, "failed": 0, "skipped": 0}
        self._queue_dir = Path(self.settings.queue_dir)
        self._queue_dir.mkdir(parents=True, exist_ok=True)

        safe_site_key = _sanitize_for_filename(self.site_key)
        # 文件名带 run_id，防止不同运行互相覆盖/混淆。
        self._events_path = self._queue_dir / f"{self.run_id}_{safe_site_key}_retry_events.jsonl"
        self._failed_path = self._queue_dir / f"{self.run_id}_{safe_site_key}_failed_tasks.json"

        logger.info("[%s] retry queue 初始化：run_id=%s", self.site_key, self.run_id)

    @property
    def enabled(self) -> bool:
        return bool(self.settings.enabled)

    def submit(
        self,
        *,
        task_type: str,
        identity_key: str,
        payload: dict[str, Any] | None,
        handler: Handler,
        on_success: OnSuccess | None = None,
        accept_result: AcceptResult | None = None,
        max_attempts: int | None = None,
    ) -> None:
        if not self.enabled:
            return

        task = RetryTask(
            site_key=self.site_key,
            task_type=task_type,
            identity_key=identity_key,
            payload=payload or {},
            handler=handler,
            run_id=self.run_id,
            on_success=on_success,
            accept_result=accept_result,
            max_attempts=max_attempts or self.settings.max_attempts,
        )
        with self._lock:
            # 去重：同一 site/task_type/identity 未完成时不重复入队。
            for existing in self._tasks:
                if (
                    existing.status in {"queued", "retrying"}
                    and existing.task_type == task.task_type
                    and existing.identity_key == task.identity_key
                ):
                    return
            self._tasks.append(task)
            self._summary["queued"] += 1
        self._write_event("queued", task)

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for task in self._tasks if task.status in {"queued", "retrying"})

    def summary(self) -> dict[str, int]:
        return dict(self._summary)

    def drain(self, *, max_wait_seconds: float | None = None) -> dict[str, int]:
        if not self.enabled:
            return self.summary()

        max_wait_seconds = self.settings.drain_max_wait_seconds if max_wait_seconds is None else max_wait_seconds
        started_at = time.time()

        if self.pending_count():
            logger.info(
                "[%s] retry queue drain 开始：run_id=%s pending=%s max_wait=%ss",
                self.site_key,
                self.run_id,
                self.pending_count(),
                max_wait_seconds,
            )

        while self.pending_count() > 0:
            if time.time() - started_at > max_wait_seconds:
                logger.warning(
                    "[%s] retry queue 达到最大等待时间，run_id=%s 剩余任务=%s",
                    self.site_key,
                    self.run_id,
                    self.pending_count(),
                )
                self._mark_remaining_failed("drain max wait exceeded")
                break

            task = self._pop_ready_task()
            if task is None:
                next_delay = self._seconds_until_next_ready()
                time.sleep(min(max(next_delay, 0.2), 2.0))
                continue

            self._run_task(task)

        if self._summary["queued"]:
            logger.info("[%s] retry queue drain 完成：run_id=%s summary=%s", self.site_key, self.run_id, self._summary)
        return self.summary()

    def _pop_ready_task(self) -> RetryTask | None:
        now = time.time()
        with self._lock:
            ready = [task for task in self._tasks if task.status in {"queued", "retrying"} and task.next_run_at <= now]
            if not ready:
                return None
            ready.sort(key=lambda item: (item.next_run_at, item.created_at))
            task = ready[0]
            task.status = "retrying"
            task.updated_at = datetime.now().isoformat(timespec="seconds")
            return task

    def _seconds_until_next_ready(self) -> float:
        with self._lock:
            future_times = [task.next_run_at for task in self._tasks if task.status in {"queued", "retrying"}]
        if not future_times:
            return 0.5
        return min(future_times) - time.time()

    def _run_task(self, task: RetryTask) -> None:
        task.attempts += 1
        task.updated_at = datetime.now().isoformat(timespec="seconds")
        try:
            result = task.handler()
            if task.accept_result and not task.accept_result(result):
                raise RetryableTaskError("retry task result not accepted")

            if task.on_success:
                task.on_success(result)

            task.status = "success"
            task.last_error = ""
            self._summary["success"] += 1
            self._write_event("success", task)
            return

        except NonRetryableTaskError as exc:
            task.status = "skipped"
            task.last_error = str(exc)
            self._summary["skipped"] += 1
            self._write_event("skipped", task)
            return

        except BaseException as exc:  # noqa: BLE001 - queue 需要兜住所有任务异常
            retryable = is_retryable_exception(exc) or isinstance(exc, RetryableTaskError)
            task.last_error = str(exc)
            if retryable and task.attempts < task.max_attempts:
                delay = self._delay_for_attempt(task.attempts)
                task.next_run_at = time.time() + delay
                task.status = "queued"
                task.updated_at = datetime.now().isoformat(timespec="seconds")
                self._write_event("rescheduled", task)
                logger.info(
                    "[%s] retry task 重新入队：run_id=%s %s/%s %s identity=%s delay=%.1fs error=%s",
                    self.site_key,
                    self.run_id,
                    task.attempts,
                    task.max_attempts,
                    task.task_type,
                    task.identity_key,
                    delay,
                    task.last_error,
                )
                return

            task.status = "failed"
            self._summary["failed"] += 1
            self._write_event("failed", task)
            self._write_failed_tasks()
            logger.warning(
                "[%s] retry task 最终失败：run_id=%s %s identity=%s attempts=%s error=%s",
                self.site_key,
                self.run_id,
                task.task_type,
                task.identity_key,
                task.attempts,
                task.last_error,
            )

    def _delay_for_attempt(self, attempts: int) -> float:
        raw_delay = self.settings.delay_seconds * (self.settings.backoff_multiplier ** max(0, attempts - 1))
        return min(max(raw_delay, 0.0), self.settings.max_delay_seconds)

    def _mark_remaining_failed(self, reason: str) -> None:
        with self._lock:
            for task in self._tasks:
                if task.status in {"queued", "retrying"}:
                    task.status = "failed"
                    task.last_error = reason
                    task.updated_at = datetime.now().isoformat(timespec="seconds")
                    self._summary["failed"] += 1
                    self._write_event("failed", task)
        self._write_failed_tasks()

    def _write_event(self, event: str, task: RetryTask) -> None:
        try:
            row = {"event": event, "event_at": datetime.now().isoformat(timespec="seconds"), **task.to_dict()}
            with self._events_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            logger.debug("retry queue event 写入失败", exc_info=True)

    def _write_failed_tasks(self) -> None:
        try:
            failed = [task.to_dict() for task in self._tasks if task.status == "failed"]
            self._failed_path.write_text(json.dumps(failed, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            logger.debug("retry queue failed tasks 写入失败", exc_info=True)


def collect_failed_retry_rows(
    queue_dir: str | None = None,
    *,
    run_id: str | None = None,
    site_key: str | None = None,
    include_all_runs: bool = False,
) -> list[dict[str, Any]]:
    """供 DataExporter 自动追加 Retry_Failed_Tasks sheet。

    默认只收集当前 run_id 的失败任务，避免把 runtime/retry_queue 下历史运行遗留的失败任务
    混入本次导出的 Excel。

    参数：
    - queue_dir：retry 文件目录；默认读取 RETRY_QUEUE_DIR；
    - run_id：指定收集哪个 run_id；不传则读取当前进程/环境变量里的 run_id；
    - site_key：可选，只收集某个站点；
    - include_all_runs：兼容排查场景，设置为 True 时才扫描所有历史失败文件。
    """
    base_dir = Path(queue_dir or os.getenv("RETRY_QUEUE_DIR", "runtime/retry_queue"))
    if not base_dir.exists():
        return []

    target_run_id = _sanitize_for_filename(run_id) if run_id else get_retry_run_id(create_if_missing=False)
    target_site_key = _sanitize_for_filename(site_key) if site_key else ""

    if include_all_runs:
        pattern = "*_failed_tasks.json"
    elif target_run_id and target_site_key:
        pattern = f"{target_run_id}_{target_site_key}_failed_tasks.json"
    elif target_run_id:
        pattern = f"{target_run_id}_*_failed_tasks.json"
    else:
        # 没有当前 run_id 时，不扫描历史文件，避免污染。
        return []

    rows: list[dict[str, Any]] = []
    for path in sorted(base_dir.glob(pattern)):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            # 旧文件可能没有 run_id；默认模式不收。include_all_runs=True 时保留。
            item_run_id = str(item.get("run_id", "")).strip()
            if not include_all_runs and target_run_id and item_run_id and item_run_id != target_run_id:
                continue
            row = dict(item)
            row["failed_file"] = path.name
            rows.append(row)
    return rows
