"""企业级重试错误分类工具。

用途：
- 404/410 这类明确不存在的资源不进入队列；
- 429/5xx/连接重置/响应提前结束/超时等进入延迟重试队列；
- 让各站点不用重复写一套异常判断。
"""

from __future__ import annotations

import socket
from typing import Any

import requests


RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404, 410, 422}


class RetryableTaskError(Exception):
    """可重试错误：进入 retry queue。"""


class NonRetryableTaskError(Exception):
    """不可重试错误：直接跳过，不进入 retry queue。"""


class RetryableHttpStatusError(RetryableTaskError):
    def __init__(self, status_code: int, url: str = "", message: str = "") -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(message or f"retryable http status={status_code} url={url}")


class NonRetryableHttpStatusError(NonRetryableTaskError):
    def __init__(self, status_code: int, url: str = "", message: str = "") -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(message or f"non-retryable http status={status_code} url={url}")


def is_retryable_status(status_code: int | None) -> bool:
    try:
        return int(status_code or 0) in RETRYABLE_STATUS_CODES
    except Exception:
        return False


def is_non_retryable_status(status_code: int | None) -> bool:
    try:
        return int(status_code or 0) in NON_RETRYABLE_STATUS_CODES
    except Exception:
        return False


def is_retryable_exception(exc: BaseException) -> bool:
    """判断 requests/网络异常是否适合延迟重试。"""
    if isinstance(exc, RetryableTaskError):
        return True
    if isinstance(exc, NonRetryableTaskError):
        return False

    retryable_types: tuple[type[Any], ...] = (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectTimeout,
        requests.exceptions.ReadTimeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.ChunkedEncodingError,
        requests.exceptions.ContentDecodingError,
        requests.exceptions.SSLError,
        socket.timeout,
        ConnectionResetError,
        BrokenPipeError,
    )
    if isinstance(exc, retryable_types):
        return True

    text = str(exc).lower()
    retryable_markers = [
        "response ended prematurely",
        "connection aborted",
        "connection reset",
        "remote host",
        "10054",
        "timed out",
        "timeout",
        "read operation timed out",
        "max retries exceeded",
        "temporarily unavailable",
        "server disconnected",
        "chunkedencodingerror",
        "incomplete read",
    ]
    return any(marker in text for marker in retryable_markers)


def classify_http_status(status_code: int, url: str = "") -> None:
    """根据 status code 抛出可重试/不可重试异常；200 调用方自行处理。"""
    if is_non_retryable_status(status_code):
        raise NonRetryableHttpStatusError(status_code, url)
    if is_retryable_status(status_code) or 500 <= int(status_code) < 600:
        raise RetryableHttpStatusError(status_code, url)
    raise RetryableHttpStatusError(status_code, url, f"unexpected http status={status_code} url={url}")
