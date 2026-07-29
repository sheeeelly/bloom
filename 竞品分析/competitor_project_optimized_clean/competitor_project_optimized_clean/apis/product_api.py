"""商品详情 API 采集模块 - 通过 Shopify JSON API 采集商品详情数据。

兼容说明：
1. 保留原有 ProductAPI.fetch_product_detail(product_handle) 调用方式。
2. 兼容 Shopify /products/{handle}.json 与 /products/{handle}.js 两种结构。
3. 对 Birdy Grey 这类 SearchSpring 返回颜色级 handle、但 Shopify 详情页不存在的情况，404 不再刷 warning。
4. 新增 fetch_product_detail_candidates()，方便上游按「基础 handle / 颜色级 handle / URL handle」多候选兜底。
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any
from urllib.parse import urlparse

import requests

from utils.config import Config
from utils.request_handler import RequestHandler, USER_AGENTS

logger = logging.getLogger(__name__)


class ProductAPI:
    def __init__(self, request_handler: RequestHandler, config: Config) -> None:
        self._request_handler = request_handler
        self._config = config
        self._session = requests.Session()

        proxy_url = getattr(config, "proxy_url", None)
        if proxy_url:
            self._session.proxies = {"http": proxy_url, "https": proxy_url}

    # =========================
    # 对外方法
    # =========================

    def fetch_product_detail(self, product_handle: str) -> dict[str, Any] | None:
        """
        获取 Shopify 商品详情。

        兼容：
        - product_handle: "grace-chiffon-dress"
        - product_handle: "/products/grace-chiffon-dress"
        - product_handle: "https://www.xxx.com/products/grace-chiffon-dress"

        返回结构保持旧版兼容：
        id/title/body_html/vendor/product_type/tags/variants/images/handle/
        is_out_of_stock/original_price/sale_price/discount_type
        """
        return self.fetch_product_detail_candidates([product_handle])

    def fetch_product_detail_candidates(self, candidates: list[str]) -> dict[str, Any] | None:
        """
        多候选 handle 兜底。

        用途：
        SearchSpring / 搜索接口有时返回颜色级 handle，例如：
        gwen-matte-satin-dress-blush-pink
        但 Shopify 真实商品详情可能只存在：
        gwen-matte-satin-dress

        上游可以传多个候选，按顺序尝试，命中第一个有效商品即返回。
        """
        handles_or_urls = self._normalize_candidates(candidates)

        if not handles_or_urls:
            return None

        for item in handles_or_urls:
            urls = self._build_candidate_urls(item)

            for url in urls:
                logger.debug("请求商品详情候选: %s", url)
                data = self._get_json_quiet(url)

                if not data:
                    continue

                product = self._unwrap_shopify_product(data)
                if not isinstance(product, dict):
                    logger.debug("商品详情响应缺少 product 结构: %s", url)
                    continue

                detail = self._extract_product_detail(product)
                if detail:
                    detail["_source_detail_url"] = url
                    return detail

        logger.debug("商品详情所有候选均未命中: %s", handles_or_urls)
        return None

    # =========================
    # 请求与 URL 构造
    # =========================

    @staticmethod
    def _safe_str(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _normalize_candidates(self, candidates: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for candidate in candidates:
            text = self._safe_str(candidate)
            if not text:
                continue

            # 去掉 query/hash/后缀
            text = text.split("?", 1)[0].split("#", 1)[0].strip()
            text = re.sub(r"\.(json|js)$", "", text, flags=re.IGNORECASE)
            text = text.rstrip("/")

            if not text:
                continue

            if text in seen:
                continue

            seen.add(text)
            result.append(text)

        return result

    def _build_candidate_urls(self, handle_or_url: str) -> list[str]:
        text = self._safe_str(handle_or_url)
        if not text:
            return []

        # 如果传入完整 URL，则优先使用原域名；否则使用 config.base_url
        if text.startswith("http://") or text.startswith("https://"):
            base_product_url = text
        else:
            handle = text
            if "/products/" in handle:
                handle = handle.split("/products/", 1)[1]
            handle = handle.strip("/")

            if not handle or "." in handle:
                return []

            base_url = self._safe_str(getattr(self._config, "base_url", "")) or "https://www.birdygrey.com"
            base_product_url = f"{base_url.rstrip('/')}/products/{handle}"

        base_product_url = re.sub(r"\.(json|js)$", "", base_product_url.rstrip("/"), flags=re.IGNORECASE)

        # .json 是 Shopify Admin-like public JSON；.js 是 storefront product JSON。
        # 不同站点可能只开放其中一种。
        return [
            f"{base_product_url}.json",
            f"{base_product_url}.js",
        ]

    def _get_json_quiet(self, url: str) -> dict[str, Any] | None:
        """
        静默请求 JSON。

        不使用 RequestHandler.get() 的原因：
        RequestHandler 对 404 会逐条 warning。Birdy Grey 颜色级 handle 404 是预期兜底行为，
        如果逐条 warning 会刷屏，影响真实异常判断。
        """
        timeout = int(getattr(self._config, "request_timeout", 30) or 30)
        max_retries = int(os.getenv("PRODUCT_API_RETRIES", str(getattr(self._config, "max_retries", 1) or 1)))
        sleep_seconds = float(os.getenv("PRODUCT_API_SLEEP_SECONDS", "0"))

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

        headers = {
            "User-Agent": USER_AGENTS[0] if USER_AGENTS else "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
        }

        for attempt in range(max_retries + 1):
            try:
                response = self._session.get(url, headers=headers, timeout=timeout)

                if response.status_code == 404:
                    logger.debug("商品详情 404，跳过候选: %s", response.url)
                    return None

                if response.status_code == 429:
                    wait_seconds = int(response.headers.get("Retry-After") or os.getenv("PRODUCT_API_429_SLEEP_SECONDS", "8"))
                    logger.warning("商品详情触发 429，等待 %s 秒后重试: %s", wait_seconds, response.url)
                    if attempt < max_retries:
                        time.sleep(wait_seconds)
                        continue
                    return None

                if response.status_code != 200:
                    logger.debug("商品详情请求失败: status=%s url=%s", response.status_code, response.url)
                    if attempt < max_retries:
                        time.sleep(min(2 ** (attempt + 1), 10))
                        continue
                    return None

                try:
                    data = response.json()
                except ValueError:
                    logger.debug("商品详情 JSON 解析失败: %s", response.url)
                    return None

                return data if isinstance(data, dict) else None

            except requests.RequestException as exc:
                logger.debug("商品详情请求异常: %s | url=%s", exc, url)
                if attempt < max_retries:
                    time.sleep(min(2 ** (attempt + 1), 10))
                    continue
                return None

        return None

    # =========================
    # 数据标准化
    # =========================

    @staticmethod
    def _unwrap_shopify_product(data: dict[str, Any]) -> dict[str, Any] | None:
        """
        兼容两种响应：
        /products/{handle}.json -> {"product": {...}}
        /products/{handle}.js   -> {...}
        """
        product = data.get("product")
        if isinstance(product, dict):
            return product

        # product.js 通常顶层就是商品对象
        if data.get("handle") or data.get("title") or data.get("variants"):
            return data

        return None

    def _extract_product_detail(self, product: dict[str, Any]) -> dict[str, Any]:
        variants = product.get("variants", []) if isinstance(product.get("variants", []), list) else []
        images = product.get("images", []) if isinstance(product.get("images", []), list) else []
        tags = self._normalize_tags(product.get("tags", []))

        is_out_of_stock = self._check_out_of_stock(variants)
        original_price, sale_price, discount_type = self._calculate_discount(product, variants)

        return {
            "id": product.get("id", 0),
            "title": product.get("title", ""),
            "body_html": product.get("body_html", "") or product.get("description", ""),
            "vendor": product.get("vendor", ""),
            "product_type": product.get("product_type", "") or product.get("type", ""),
            "tags": tags,
            "variants": variants,
            "images": images,
            "image": product.get("image"),
            "handle": product.get("handle", ""),
            "is_out_of_stock": is_out_of_stock,
            "original_price": original_price,
            "sale_price": sale_price,
            "discount_type": discount_type,
        }

    @staticmethod
    def _normalize_tags(tags: Any) -> list[str]:
        if isinstance(tags, list):
            return [str(tag).strip() for tag in tags if str(tag).strip()]
        if isinstance(tags, str):
            return [tag.strip() for tag in tags.split(",") if tag.strip()]
        return []

    @staticmethod
    def _check_out_of_stock(variants: list[dict[str, Any]]) -> bool:
        if not variants:
            return False

        availability_values = []
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            if "available" in variant:
                availability_values.append(bool(variant.get("available")))
            elif "availableForSale" in variant:
                availability_values.append(bool(variant.get("availableForSale")))

        if not availability_values:
            return False

        return all(not value for value in availability_values)

    @classmethod
    def _calculate_discount(cls, product: dict[str, Any], variants: list[dict[str, Any]]) -> tuple[str, str, str]:
        price_candidates: list[float] = []
        compare_candidates: list[float] = []

        for field in ["price", "price_min", "min_price"]:
            value = cls._parse_price(product.get(field))
            if value:
                price_candidates.append(value)

        for field in ["compare_at_price", "compare_at_price_max", "compare_at_price_min"]:
            value = cls._parse_price(product.get(field))
            if value:
                compare_candidates.append(value)

        for variant in variants:
            if not isinstance(variant, dict):
                continue
            price = cls._parse_price(variant.get("price"))
            compare = cls._parse_price(variant.get("compare_at_price"))

            if price:
                price_candidates.append(price)
            if compare:
                compare_candidates.append(compare)

        if not price_candidates:
            return "", "", "无折扣"

        sale_price_num = min(price_candidates)
        original_price_num = max(compare_candidates) if compare_candidates else sale_price_num

        if original_price_num > sale_price_num:
            return cls._format_price(original_price_num), cls._format_price(sale_price_num), "打折"

        return cls._format_price(sale_price_num), cls._format_price(sale_price_num), "无折扣"

    @staticmethod
    def _parse_price(value: Any) -> float:
        if value is None or value == "":
            return 0.0

        if isinstance(value, dict):
            value = value.get("amount") or value.get("price") or value.get("value")

        if isinstance(value, list):
            value = value[0] if value else ""

        text = str(value).replace("$", "").replace(",", "").strip()
        text = re.sub(r"[^0-9.\-]", "", text)

        if not text:
            return 0.0

        try:
            price = float(text)
        except ValueError:
            return 0.0

        # Shopify .js 常用 cents 整数，例如 12900 表示 129.00
        if "." not in text and price >= 1000:
            price = price / 100

        return price

    @staticmethod
    def _format_price(value: float) -> str:
        if not value:
            return ""
        return f"${value:.2f}"
