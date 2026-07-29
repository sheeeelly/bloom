"""列表页 API 采集模块 - 通过 SearchSpring search API 采集 Birdy Grey collection 商品。

本版优化：
1. 仍然使用 SearchSpring search.json 作为 Birdy Grey 列表页商品池。
2. 请求参数继续带 bgfilter.collection_handle。
3. SearchSpring 返回后再做本地 collection_handle 二次过滤，避免接口忽略筛选时抓到全站商品。
4. collection_handle 字段缺失时默认保留，避免接口字段为空导致误删全部。
5. 支持通过 .env 配置 resultsPerPage / 严格过滤开关。
"""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from utils.config import Config
from utils.request_handler import RequestHandler

logger = logging.getLogger(__name__)


def _as_list(value: Any) -> list[str]:
    """兼容 SearchSpring 返回的字符串 / 列表 / 空值。"""
    if value is None:
        return []

    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]

    if isinstance(value, str):
        # SearchSpring 有时返回逗号分隔字符串
        return [v.strip() for v in value.split(",") if v.strip()]

    return [str(value).strip()]


def _first_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return str(value[0]).strip() if value else ""

    return str(value).strip()


def _normalize_handle(value: Any) -> str:
    text = _first_text(value).strip().lower()

    if not text:
        return ""

    text = text.split("?", 1)[0].split("#", 1)[0].strip("/")

    if "/collections/" in text:
        text = text.split("/collections/", 1)[1].strip("/")

    return text


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


class CollectionAPI:
    def __init__(self, request_handler: RequestHandler, config: Config) -> None:
        self._request_handler = request_handler
        self._config = config

    def fetch_collection_products(self, collection_slug: str, max_count: int = 50) -> list[dict[str, Any]]:
        collection_map = {
            "best-selling-dresses": {
                "handle": "best-selling-dresses",
                "is_bestseller": "是",
                "is_new": "否",
            },
            "bridesmaid-dress-new-arrivals": {
                "handle": "bridesmaid-dress-new-arrivals",
                "is_bestseller": "否",
                "is_new": "是",
            },
            "bridesmaid-dresses": {
                "handle": "bridesmaid-dresses",
                "is_bestseller": "否",
                "is_new": "否",
            },
        }

        collection_conf = collection_map.get(collection_slug)
        if not collection_conf:
            logger.error("未支持的 collection_slug: %s", collection_slug)
            return []

        real_handle = collection_conf["handle"]
        logger.info("开始采集 SearchSpring collection [%s]，目标数量: %d", real_handle, max_count)

        base_url = self._normalize_searchspring_url(self._config.search_api_url)
        if not base_url:
            logger.error("未配置 SEARCH_API_URL，请检查 .env 文件")
            return []

        parsed_url = urlparse(base_url)
        query_params = parse_qs(parsed_url.query)

        results_per_page = os.getenv("BG_SEARCHSPRING_RESULTS_PER_PAGE", "72").strip() or "72"

        # SearchSpring 当前真实可用参数：
# - 使用 search.json 作为 Birdy Grey 列表页商品池接口
# - bgfilter.collection_handle 用于限定 collection
        query_params.update(
            {
                "siteId": ["c220gm"],
                "resultsFormat": ["json"],
                "q": [""],
                "resultsPerPage": [results_per_page],
                "redirectResponse": ["direct"],
                "bgfilter.ss_no_index": ["0"],
                "bgfilter.collection_handle": [real_handle],
            }
        )

        # 旧参数清理，避免同时存在 filter.collection_handle 和 bgfilter.collection_handle
        query_params.pop("filter.collection_handle", None)

        # 当前业务要求按官网 Best Sellers 链接顺序分析：
        # https://www.birdygrey.com/collections/bridesmaid-dresses?sort.ga_unique_purchases=desc
        # 默认保留/写入该排序参数，避免抓到默认排序后影响周对周趋势。
        if real_handle == "bridesmaid-dresses":
            query_params["sort.ga_unique_purchases"] = [os.getenv("BG_COLLECTION_SORT_VALUE", "desc").strip() or "desc"]

        products: list[dict[str, Any]] = []
        seen_keys: set[str] = set()

        page = 1
        empty_pages = 0
        max_empty_pages = int(os.getenv("BG_SEARCHSPRING_MAX_EMPTY_PAGES", "3"))
        max_count = max(1, max_count)

        while len(products) < max_count:
            query_params["page"] = [str(page)]
            current_url = urlunparse(parsed_url._replace(query=urlencode(query_params, doseq=True)))
            logger.info("请求 SearchSpring collection [%s] 第 %d 页", real_handle, page)

            data = self._request_handler.get(current_url)
            if data is None:
                logger.warning("SearchSpring collection [%s] 第 %d 页请求失败，停止翻页", real_handle, page)
                break

            raw_page_products = self._extract_products(data)
            page_products = self._filter_products_by_collection(raw_page_products, real_handle)

            if not page_products:
                empty_pages += 1
                logger.info(
                    "collection [%s] 第 %d 页未返回有效商品，原始=%d，过滤后=0，连续空页 %d/%d",
                    real_handle,
                    page,
                    len(raw_page_products),
                    empty_pages,
                    max_empty_pages,
                )
            else:
                empty_pages = 0
                added = 0

                for product in page_products:
                    product["is_bestseller"] = collection_conf["is_bestseller"]
                    product["is_new"] = collection_conf["is_new"]

                    key = self._product_dedupe_key(product)
                    if not key:
                        continue

                    if key in seen_keys:
                        continue

                    seen_keys.add(key)
                    product["_collection_order"] = len(products) + 1
                    products.append(product)
                    added += 1

                    if len(products) >= max_count:
                        break

                logger.info(
                    "collection [%s] 第 %d 页获取 原始=%d 过滤后=%d 新增=%d 累计=%d",
                    real_handle,
                    page,
                    len(raw_page_products),
                    len(page_products),
                    added,
                    len(products),
                )

            total_pages = self._safe_int(data.get("pagination", {}).get("totalPages"), default=1)

            if page >= total_pages:
                logger.info("collection [%s] 已到最后一页 page=%s totalPages=%s", real_handle, page, total_pages)
                break

            if empty_pages >= max_empty_pages:
                logger.info("collection [%s] 连续空页达到阈值，停止翻页", real_handle)
                break

            page += 1

        logger.info(
            "SearchSpring collection [%s] 采集完成：返回=%d，目标=%d",
            real_handle,
            len(products),
            max_count,
        )

        return products[:max_count]

    @staticmethod
    def _normalize_searchspring_url(url: str) -> str:
        """
        读取 SearchSpring search.json 接口地址。

        注意：
        .env 中 SEARCH_API_URL 必须直接配置为 search.json，例如：
        https://c220gm.a.searchspring.io/api/search/search.json?siteId=c220gm&resultsFormat=json
        """
        url = (url or "").strip()
        if not url:
            return ""

        if url.startswith("SEARCH_API_URL="):
            url = url.replace("SEARCH_API_URL=", "", 1).strip()

        return url

    @staticmethod
    def _safe_int(value: Any, default: int = 1) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _product_dedupe_key(product: dict[str, Any]) -> str:
        return (
            _first_text(product.get("handle"))
            or _first_text(product.get("admin_graphql_api_id"))
            or _first_text(product.get("id"))
            or _first_text(product.get("sku"))
            or _first_text(product.get("title"))
        )

    def _filter_products_by_collection(
        self,
        products: list[dict[str, Any]],
        expected_collection_handle: str,
    ) -> list[dict[str, Any]]:
        """SearchSpring 有时会忽略 collection filter，因此这里再做一次本地过滤。

        策略：
        - product.collection_handle 有值时：必须包含 expected_collection_handle。
        - product.collection_handle 为空时：默认保留，避免接口不返回该字段时误删全部。
        - 如需严格丢弃空 collection_handle，可设置 BG_STRICT_COLLECTION_FILTER=true。
        """
        expected = _normalize_handle(expected_collection_handle)
        strict_filter = _env_bool("BG_STRICT_COLLECTION_FILTER", False)

        if not expected:
            return products

        kept: list[dict[str, Any]] = []
        dropped = 0
        empty_collection_kept = 0

        for product in products:
            handles = [
                _normalize_handle(item)
                for item in _as_list(product.get("collection_handle"))
                if _normalize_handle(item)
            ]

            if not handles:
                if strict_filter:
                    dropped += 1
                    continue

                empty_collection_kept += 1
                kept.append(product)
                continue

            if expected in handles:
                kept.append(product)
            else:
                dropped += 1

        if dropped or empty_collection_kept:
            logger.info(
                "SearchSpring 本地 collection 过滤: expected=%s 原始=%d 保留=%d 丢弃=%d 空collection保留=%d strict=%s",
                expected,
                len(products),
                len(kept),
                dropped,
                empty_collection_kept,
                strict_filter,
            )

        return kept

    def _extract_products(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        results = data.get("results", [])
        if not isinstance(results, list):
            logger.warning("SearchSpring 响应 results 不是列表，已忽略")
            return []

        products: list[dict[str, Any]] = []
        for item in results:
            if not isinstance(item, dict):
                continue

            tags = _as_list(item.get("ss_tags") or item.get("tags"))
            collection_handle = _as_list(
                item.get("collection_handle")
                or item.get("ss_collection_handle")
                or item.get("collection_handles")
                or item.get("collections")
            )

            image_url = _first_text(
                item.get("imageUrl")
                or item.get("thumbnailImageUrl")
                or item.get("thumbnail")
                or item.get("image")
            )

            handle = _first_text(item.get("handle"))
            title = _first_text(item.get("name") or item.get("title"))

            products.append(
                {
                    "handle": handle,
                    "title": title,
                    "name": title,
                    "admin_graphql_api_id": _first_text(item.get("admin_graphql_api_id")),
                    "id": _first_text(item.get("id")),
                    "sku": _first_text(item.get("sku")),
                    "price": _first_text(item.get("price")),
                    "compare_at_price": _first_text(item.get("msrp") or item.get("compare_at_price")),
                    "mfield_attr_color": _first_text(item.get("mfield_attr_color")),
                    "mfield_attr_fabric": _first_text(item.get("mfield_attr_fabric")),
                    "mfield_attr_style": _first_text(item.get("mfield_attr_style")),
                    "mfield_attr_type": _first_text(item.get("mfield_attr_type")),
                    "product_type": _first_text(item.get("product_type")),
                    "tags": tags,
                    "collection_handle": collection_handle,
                    "available": str(item.get("ss_available", "0")) == "1",
                    "is_ready_to_ship": str(item.get("ss_ships_now", "0")) == "1",
                    "images": [{"src": image_url}] if image_url else [],
                }
            )

        return products
