"""HTTP 请求处理模块 - 封装反爬策略与请求重试逻辑。

兼容说明：
1. 保留原来的 RequestHandler(config).get(url, params=..., headers=...) 调用方式。
2. get() 默认仍返回 JSON 对象；请求失败返回 None。
3. 404 默认不再 warning 刷屏，避免 Birdy Grey 颜色级 handle / product.js 兜底时大量噪音。
4. 新增 get_text() / post_json() / request_json()，供后续站点复用。
"""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any

import requests

from utils.config import Config

logger = logging.getLogger(__name__)


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) "
    "Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_quiet_statuses() -> set[int]:
    """
    默认静默 404。
    如需调整，可在 .env 中配置：
    HTTP_QUIET_STATUS_CODES=404,410
    """
    raw = os.getenv("HTTP_QUIET_STATUS_CODES", "404")
    result: set[int] = set()

    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            result.add(int(item))
        except ValueError:
            continue

    return result


class RequestHandler:
    """HTTP 请求处理器。

    功能：
    - 随机 User-Agent
    - 请求前随机延迟
    - 失败自动重试
    - 支持 429 Retry-After
    - 可选 HTTP 代理
    - 兼容 JSON / Text / POST JSON
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._session = requests.Session()

        proxy_url = getattr(config, "proxy_url", None)
        if proxy_url:
            self._session.proxies = {"http": proxy_url, "https": proxy_url}
            logger.info("已配置 HTTP 代理: %s", proxy_url)

        self._quiet_statuses = _parse_quiet_statuses()
        self._log_404_as_warning = _env_bool("HTTP_LOG_404_WARNING", False)
        self._retry_429_sleep_seconds = _env_int("HTTP_429_SLEEP_SECONDS", 10)

    # =========================
    # 对外兼容方法
    # =========================

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any | None:
        """发送 GET 请求并返回 JSON。

        保持旧版兼容：
        - 成功：返回 response.json()
        - 失败：返回 None
        """
        return self.request_json(
            "GET",
            url,
            params=params,
            headers=headers,
        )

    def get_text(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str | None:
        """发送 GET 请求并返回文本内容。"""
        response = self.request(
            "GET",
            url,
            params=params,
            headers=headers,
        )
        if response is None:
            return None
        return response.text

    def post_json(
        self,
        url: str,
        *,
        payload: dict[str, Any] | list[Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any | None:
        """发送 POST JSON 请求并返回 JSON。"""
        return self.request_json(
            "POST",
            url,
            params=params,
            json_payload=payload,
            headers=headers,
        )

    # =========================
    # 通用请求方法
    # =========================

    def request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
        expected_statuses: set[int] | None = None,
    ) -> Any | None:
        """发送请求并解析 JSON。"""
        response = self.request(
            method,
            url,
            params=params,
            json_payload=json_payload,
            headers=headers,
            expected_statuses=expected_statuses,
        )

        if response is None:
            return None

        try:
            return response.json()
        except ValueError:
            logger.error(
                "JSON 解析失败 (%s)，原始响应内容: %.500s",
                response.url,
                response.text,
            )
            return None

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | list[Any] | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        expected_statuses: set[int] | None = None,
        timeout: int | float | None = None,
    ) -> requests.Response | None:
        """发送 HTTP 请求并返回 Response。

        expected_statuses:
        - 默认 {200}
        - 如果你想把 404 当成可接受结果，可传 {200, 404}
        """
        expected_statuses = expected_statuses or {200}

        delay_min = float(getattr(self._config, "request_delay_min", 0) or 0)
        delay_max = float(getattr(self._config, "request_delay_max", 0) or 0)
        if delay_max > 0:
            delay = random.uniform(delay_min, max(delay_min, delay_max))
            time.sleep(delay)

        max_retries = max(0, int(getattr(self._config, "max_retries", 3) or 0))
        request_timeout = timeout or getattr(self._config, "request_timeout", 30) or 30

        method_upper = method.upper().strip()

        for attempt in range(max_retries + 1):
            try:
                request_headers = self._build_headers(headers)

                response = self._session.request(
                    method_upper,
                    url,
                    params=params,
                    json=json_payload,
                    data=data,
                    headers=request_headers,
                    timeout=request_timeout,
                )

                if response.status_code in expected_statuses:
                    return response

                if response.status_code in self._quiet_statuses:
                    self._log_quiet_status(response, attempt, max_retries)
                    return None

                if response.status_code == 429:
                    self._log_retryable_status(response, attempt, max_retries)
                    if attempt < max_retries:
                        self._sleep_for_429(response, attempt)
                        continue
                    return None

                if 500 <= response.status_code < 600:
                    self._log_retryable_status(response, attempt, max_retries)
                    if attempt < max_retries:
                        self._sleep_before_retry(attempt)
                        continue
                    return None

                logger.warning(
                    "请求 %s 返回状态码 %s（第 %s/%s 次尝试）",
                    response.url,
                    response.status_code,
                    attempt + 1,
                    max_retries + 1,
                )

                if attempt < max_retries:
                    self._sleep_before_retry(attempt)
                    continue

                return None

            except requests.exceptions.RequestException as exc:
                logger.warning(
                    "请求 %s 发生异常: %s（第 %s/%s 次尝试）",
                    url,
                    exc,
                    attempt + 1,
                    max_retries + 1,
                )
                if attempt < max_retries:
                    self._sleep_before_retry(attempt)
                    continue
                return None

        return None

    # =========================
    # 内部工具
    # =========================

    def _build_headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        request_headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
        }

        if headers:
            request_headers.update(headers)

        return request_headers

    def _log_quiet_status(
        self,
        response: requests.Response,
        attempt: int,
        max_retries: int,
    ) -> None:
        if response.status_code == 404 and self._log_404_as_warning:
            logger.warning("请求 %s 返回 404，资源不存在，不再重试", response.url)
            return

        logger.debug(
            "请求 %s 返回状态码 %s，按静默状态处理，不再重试（第 %s/%s 次尝试）",
            response.url,
            response.status_code,
            attempt + 1,
            max_retries + 1,
        )

    @staticmethod
    def _log_retryable_status(
        response: requests.Response,
        attempt: int,
        max_retries: int,
    ) -> None:
        logger.warning(
            "请求 %s 返回状态码 %s（第 %s/%s 次尝试）",
            response.url,
            response.status_code,
            attempt + 1,
            max_retries + 1,
        )

    def _sleep_for_429(self, response: requests.Response, attempt: int) -> None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                delay = min(max(float(retry_after), 1), 120)
                logger.info("命中 429，将按 Retry-After 等待 %.1f 秒后重试...", delay)
                time.sleep(delay)
                return
            except ValueError:
                pass

        delay = max(self._retry_429_sleep_seconds, min(2 ** (attempt + 1), 30))
        logger.info("命中 429，将等待 %s 秒后重试...", delay)
        time.sleep(delay)

    @staticmethod
    def _sleep_before_retry(attempt: int) -> None:
        retry_delay = min(2 ** (attempt + 1), 30)
        logger.info("将在 %s 秒后重试...", retry_delay)
        time.sleep(retry_delay)
