"""评论 API 采集模块 - 通过 Yotpo Widget API 采集商品评论数据。

兼容性说明：
- 保留原有 ReviewAPI.fetch_product_reviews(product_id) 方法和返回结构。
- 返回结构固定为：{"average_score": float, "total_reviews": int}。
- 不依赖前面已修改的 collection_api.py / product_api.py / main_bg.py，避免冲突。

优化点：
1. 增加内存缓存，避免同一个 product_id 重复请求 Yotpo。
2. 兼容 Yotpo response.bottomline / bottomline / product_score 等多种响应结构。
3. app_key 未配置时只提示一次，避免刷屏。
4. product_id 为空或非法时直接返回默认值。
5. 请求失败或无评论时降级为 debug/info 日志，减少非关键 warning。
"""

from __future__ import annotations

import logging
from typing import Any

from utils.config import Config
from utils.request_handler import RequestHandler

logger = logging.getLogger(__name__)

YOTPO_API_BASE_URL = "https://api-cdn.yotpo.com"


class ReviewAPI:
    def __init__(self, request_handler: RequestHandler, config: Config) -> None:
        self._request_handler = request_handler
        self._config = config
        self._cache: dict[str, dict[str, Any]] = {}
        self._missing_app_key_logged = False

    @staticmethod
    def _default_result() -> dict[str, Any]:
        return {"average_score": 0.0, "total_reviews": 0}

    @staticmethod
    def _normalize_product_id(product_id: Any) -> str:
        text = str(product_id or "").strip()
        if not text:
            return ""

        # 兼容 gid://shopify/Product/123456789 这类 ID
        if "/" in text:
            text = text.rsplit("/", 1)[-1].strip()

        return text

    def fetch_product_reviews(self, product_id: Any) -> dict[str, Any]:
        """获取单个商品评论摘要。

        兼容旧调用：原来 product_id 参数是 int，现在 str/int/gid 都可以。
        """
        normalized_product_id = self._normalize_product_id(product_id)
        if not normalized_product_id:
            return self._default_result()

        if normalized_product_id in self._cache:
            return dict(self._cache[normalized_product_id])

        app_key = str(getattr(self._config, "yotpo_app_key", "") or "").strip()
        if not app_key:
            if not self._missing_app_key_logged:
                logger.info("Yotpo app_key 未配置，跳过评论采集")
                self._missing_app_key_logged = True

            result = self._default_result()
            self._cache[normalized_product_id] = result
            return dict(result)

        url = f"{YOTPO_API_BASE_URL}/v1/widget/{app_key}/products/{normalized_product_id}/reviews"
        data = self._request_handler.get(url)

        if data is None:
            # Yotpo 评论不是主流程关键字段，请求失败不打 warning，避免日志噪音。
            logger.debug("商品 [%s] 评论请求失败，使用默认值", normalized_product_id)
            result = self._default_result()
            self._cache[normalized_product_id] = result
            return dict(result)

        result = self._extract_review_summary(data, normalized_product_id)
        self._cache[normalized_product_id] = result
        return dict(result)

    def fetch_products_reviews(self, product_ids: list[Any]) -> dict[str, dict[str, Any]]:
        """批量获取评论摘要。

        当前 Yotpo Widget API 仍是逐商品接口，这里主要做统一入口和缓存复用。
        返回：{product_id: {average_score, total_reviews}}
        """
        result: dict[str, dict[str, Any]] = {}
        for product_id in product_ids:
            normalized_product_id = self._normalize_product_id(product_id)
            if not normalized_product_id:
                continue
            result[normalized_product_id] = self.fetch_product_reviews(normalized_product_id)
        return result

    def _extract_review_summary(self, data: dict[str, Any], product_id: Any) -> dict[str, Any]:
        default_result = self._default_result()

        if not isinstance(data, dict):
            return default_result

        try:
            bottomline = self._find_bottomline_block(data)
            if not isinstance(bottomline, dict) or not bottomline:
                # 无评论或接口未返回 bottomline 都是可接受情况，不作为 warning。
                logger.debug("商品 [%s] 评论响应中缺少 bottomline，使用默认值", product_id)
                return default_result

            average_score = self._to_float(
                self._first_non_empty(
                    bottomline.get("average_score"),
                    bottomline.get("averageScore"),
                    bottomline.get("average_rating"),
                    bottomline.get("averageRating"),
                    bottomline.get("score"),
                    bottomline.get("rating"),
                ),
                default=0.0,
            )

            total_reviews = self._to_int(
                self._first_non_empty(
                    bottomline.get("total_review"),
                    bottomline.get("total_reviews"),
                    bottomline.get("totalReviews"),
                    bottomline.get("reviews_count"),
                    bottomline.get("review_count"),
                    bottomline.get("count"),
                ),
                default=0,
            )

            # 合理性保护，避免异常响应污染表格
            if average_score < 0:
                average_score = 0.0
            if average_score > 5:
                average_score = 5.0
            if total_reviews < 0:
                total_reviews = 0

            return {
                "average_score": average_score,
                "total_reviews": total_reviews,
            }

        except (ValueError, TypeError, AttributeError) as exc:
            logger.debug("商品 [%s] 评论数据解析异常: %s，使用默认值", product_id, exc)
            return default_result

    @staticmethod
    def _find_bottomline_block(data: dict[str, Any]) -> dict[str, Any]:
        """兼容 Yotpo 可能出现的多层响应结构。"""
        candidates = [
            data.get("bottomline"),
            data.get("response", {}).get("bottomline") if isinstance(data.get("response"), dict) else None,
            data.get("product_score"),
            data.get("response", {}).get("product_score") if isinstance(data.get("response"), dict) else None,
            data.get("response", {}).get("bottom_line") if isinstance(data.get("response"), dict) else None,
            data.get("bottom_line"),
        ]

        for candidate in candidates:
            if isinstance(candidate, dict) and candidate:
                return candidate

        return {}

    @staticmethod
    def _first_non_empty(*values: Any) -> Any:
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            return value
        return None

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        if value is None or value == "":
            return default
        try:
            return float(str(value).replace(",", "").strip())
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        if value is None or value == "":
            return default
        try:
            return int(float(str(value).replace(",", "").strip()))
        except (TypeError, ValueError):
            return default
