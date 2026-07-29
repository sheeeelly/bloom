"""配置管理模块 - 从 .env 文件集中加载爬虫配置。

本版兼容旧字段，并补齐近期新增的配置：
- GLOBAL_SITE_WORKERS：run.py --site all 并发数
- BASELINE_CREATE_BACKUP：基线保存备份开关
- BG product.js 并发/过滤配置
- DB PDP 属性补抓配置
- SS 颜色补抓/颜色完整性检查配置
- CL / BB / HM 站点细分配置

说明：
1. 旧代码中通过 getattr(config, "...") 读取的字段继续保留。
2. 新代码可直接使用 Config 字段，减少各 main 文件里散落 os.getenv。
3. 布尔值仍保留为 bool；若旧代码按字符串处理，请用 getattr + str() 也兼容。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _env_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning("环境变量 %s=%r 不是合法整数，使用默认值 %s", name, raw, default)
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return float(raw)
    except (TypeError, ValueError):
        logger.warning("环境变量 %s=%r 不是合法数字，使用默认值 %s", name, raw, default)
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw == "":
        return default
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    logger.warning("环境变量 %s=%r 不是合法布尔值，使用默认值 %s", name, raw, default)
    return default


@dataclass
class Config:
    """从 .env 文件加载爬虫配置，缺失项使用默认值。"""

    # =========================
    # 通用配置
    # =========================
    base_url: str = "https://www.birdygrey.com"
    request_timeout: int = 30
    search_api_url: str = ""
    request_delay_min: float = 1.0
    request_delay_max: float = 3.0
    output_dir: str = "output"
    max_products_per_collection: int = 99999
    proxy_url: Optional[str] = None
    yotpo_app_key: str = ""
    max_retries: int = 3
    log_level: str = "INFO"
    delisted_keep_days: int = 180

    # run.py / baseline
    global_site_workers: int = 2
    baseline_create_backup: bool = True

    # =========================
    # Azazie 配置
    # =========================
    az_data_source: str = "file"
    az_input_path: str = ""
    az_api_url: str = ""
    az_base_url: str = "https://www.azazie.com"
    az_collection_url: str = ""
    az_baseline_path: str = "azazie_bd_baseline.json"
    az_sheet_name: str = "AZ_伴娘服总表"
    az_category: str = "Bridesmaid Dresses"
    az_min_expected_active: int = 1

    # =========================
    # Birdy Grey 配置
    # =========================
    bg_baseline_path: str = "birdygrey_baseline.json"
    bg_sheet_name: str = "BG_伴娘服总表"

    bg_enable_product_js_enrich: bool = True
    bg_product_js_workers: int = 6
    bg_product_js_sleep_seconds: float = 0.1
    bg_product_js_retries: int = 1
    bg_product_js_429_sleep_seconds: int = 8
    bg_product_js_max_products: int = 99999
    bg_color_include_fabric: bool = True
    bg_min_expected_active: int = 200

    bg_new_arrivals_max_products: int = 800
    bg_searchspring_results_per_page: int = 72
    bg_searchspring_max_empty_pages: int = 3
    bg_strict_collection_filter: bool = False

    # =========================
    # Six Stories 配置
    # =========================
    ss_baseline_path: str = "sixstories_baseline.json"
    ss_sheet_name: str = "SS_伴娘服总表"
    ss_enable_pdp_color_enrich: bool = True
    ss_extra_collection_handles: str = ""
    ss_enable_color_audit_sheet: bool = True
    ss_pdp_recursive_color_enrich: bool = True
    ss_pdp_max_total_pages: int = 1200
    ss_pdp_max_pages_per_family: int = 80
    ss_pdp_sleep_seconds: float = 2.0
    ss_min_expected_active: int = 200

    # =========================
    # Club L London 配置
    # =========================
    cl_base_url: str = "https://clubllondon.com"
    cl_collection_handle: str = "bridesmaids"
    cl_graphql_url: str = "https://club-l-london.myshopify.com/api/2026-01/graphql.json"
    cl_graphql_country: str = "GB"
    cl_baseline_path: str = "clubllondon_baseline.json"
    cl_sheet_name: str = "CL_伴娘服总表"

    cl_graphql_collection_page_size: int = 250
    cl_graphql_collection_sleep_seconds: float = 0.3
    cl_graphql_product_batch_size: int = 15
    cl_graphql_min_batch_size: int = 5
    cl_graphql_429_sleep_seconds: int = 8
    cl_graphql_batch_sleep_seconds: float = 0.5

    cl_enable_color_expansion: bool = True
    cl_color_expansion_workers: int = 1
    cl_color_expansion_sleep_seconds: float = 1.5
    cl_color_expansion_max_seeds: int = 200

    cl_html_retries: int = 1
    cl_html_429_sleep_seconds: int = 10
    cl_enable_products_json_fallback: bool = False
    cl_products_json_max_pages: int = 20
    cl_enable_product_js_fallback: bool = True
    cl_product_js_workers: int = 2
    cl_product_js_sleep_seconds: float = 0.8
    cl_429_sleep_seconds: int = 10
    cl_enable_html_fallback: bool = False
    cl_html_max_pages: int = 5
    cl_enable_swym_fallback: bool = False
    cl_swym_max_items: int = 30
    cl_swym_wait_ms: int = 3500
    cl_swym_sleep_seconds: float = 0.5
    cl_min_expected_active: int = 200

    # =========================
    # Babyboo Fashion 配置
    # =========================
    bb_base_url: str = "https://www.babyboofashion.com"
    bb_collection_handle: str = "bridesmaid"
    bb_baseline_path: str = "babyboo_baseline.json"
    bb_sheet_name: str = "BB_伴娘服总表"

    bb_shop_domain: str = "babyboofashion-com-au.myshopify.com"
    bb_graphql_url: str = "https://babyboofashion-com-au.myshopify.com/api/2024-04/graphql.json"
    bb_graphql_country: str = "AU"
    bb_graphql_batch_size: int = 35
    bb_graphql_min_batch_size: int = 8
    bb_graphql_include_inventory: bool = False

    bb_enable_playwright_graphql_discovery: bool = True
    bb_view_more_max_clicks: int = 30
    bb_view_more_wait_ms: int = 1800
    bb_enable_products_json_fallback: bool = True
    bb_enable_html_fallback: bool = True
    bb_products_json_max_pages: int = 20
    bb_collection_max_pages: int = 3
    bb_webyze_workers: int = 8

    bb_enable_product_js_missing: bool = True
    bb_product_js_workers: int = 1
    bb_product_js_sleep_seconds: float = 1.5
    bb_429_sleep_seconds: int = 10
    bb_price_prefix: str = "$"
    bb_price_suffix: str = " AUD"
    bb_min_expected_active: int = 100

    # =========================
    # Hello Molly 配置
    # =========================
    hm_base_url: str = "https://www.hellomolly.com"
    hm_collection_path: str = "collections/wedding-edit/bridesmaid"
    hm_baseline_path: str = "hellomolly_baseline.json"
    hm_sheet_name: str = "HM_伴娘服总表"

    hm_nosto_account_id: str = "shopify-28120711254"
    hm_nosto_category_path: str = "Bridesmaid"
    hm_nosto_page_size: int = 96
    hm_nosto_max_pages: int = 30
    hm_nosto_segments: str = ""
    hm_next_build_id: str = ""
    hm_enable_html_fallback: bool = True
    hm_collection_max_pages: int = 5
    hm_detail_workers: int = 8
    hm_max_product_detail_requests: int = 2000
    hm_extra_product_handles: str = ""
    hm_min_expected_active: int = 100


    # =========================
    # Retry Queue 配置
    # =========================
    enable_async_retry_queue: bool = True
    retry_queue_dir: str = "runtime/retry_queue"
    retry_queue_max_attempts: int = 4
    retry_delay_seconds: float = 10.0
    retry_backoff_multiplier: float = 2.0
    retry_max_delay_seconds: float = 90.0
    retry_drain_max_wait_seconds: float = 600.0
    retry_drain_before_export: bool = True

    # =========================
    # Google Sheets 配置
    # =========================
    gsheet_spreadsheet_id: str = ""
    gsheet_credentials_json: str = "credentials.json"

    @classmethod
    def load(cls, env_path: Optional[str] = None) -> "Config":
        """从 .env 文件加载配置，缺失项使用默认值。"""
        target = Path(env_path) if env_path else Path(".env")

        if not target.exists():
            logger.warning(
                ".env 文件不存在（%s），将使用全部默认配置值",
                target.resolve(),
            )
        else:
            load_dotenv(dotenv_path=str(target), override=True)

        proxy_url_raw = _env_str("PROXY_URL", "")
        proxy_url = proxy_url_raw if proxy_url_raw else None

        return cls(
            # =========================
            # 通用配置
            # =========================
            base_url=_env_str("BASE_URL", "https://www.birdygrey.com"),
            request_timeout=_env_int("REQUEST_TIMEOUT", 30),
            search_api_url=_env_str("SEARCH_API_URL", ""),
            request_delay_min=_env_float("REQUEST_DELAY_MIN", 1.0),
            request_delay_max=_env_float("REQUEST_DELAY_MAX", 3.0),
            output_dir=_env_str("OUTPUT_DIR", "output"),
            max_products_per_collection=_env_int("MAX_PRODUCTS_PER_COLLECTION", 99999),
            proxy_url=proxy_url,
            yotpo_app_key=_env_str("YOTPO_APP_KEY", ""),
            max_retries=_env_int("MAX_RETRIES", 3),
            log_level=_env_str("LOG_LEVEL", "INFO").upper(),
            delisted_keep_days=_env_int("DELISTED_KEEP_DAYS", 180),
            global_site_workers=_env_int("GLOBAL_SITE_WORKERS", 2),
            baseline_create_backup=_env_bool("BASELINE_CREATE_BACKUP", True),

            # =========================
            # Azazie 配置
            # =========================
            az_data_source=_env_str("AZ_DATA_SOURCE", "file"),
            az_input_path=_env_str("AZ_INPUT_PATH", ""),
            az_api_url=_env_str("AZ_API_URL", ""),
            az_base_url=_env_str("AZ_BASE_URL", "https://www.azazie.com"),
            az_collection_url=_env_str("AZ_COLLECTION_URL", ""),
            az_baseline_path=_env_str("AZ_BASELINE_PATH", "azazie_bd_baseline.json"),
            az_sheet_name=_env_str("AZ_SHEET_NAME", "AZ_伴娘服总表"),
            az_category=_env_str("AZ_CATEGORY", "Bridesmaid Dresses"),
            az_min_expected_active=_env_int("AZ_MIN_EXPECTED_ACTIVE", 1),

            # =========================
            # Birdy Grey 配置
            # =========================
            bg_baseline_path=_env_str("BG_BASELINE_PATH", "birdygrey_baseline.json"),
            bg_sheet_name=_env_str("BG_SHEET_NAME", "BG_伴娘服总表"),
            bg_enable_product_js_enrich=_env_bool("BG_ENABLE_PRODUCT_JS_ENRICH", True),
            bg_product_js_workers=_env_int("BG_PRODUCT_JS_WORKERS", 6),
            bg_product_js_sleep_seconds=_env_float("BG_PRODUCT_JS_SLEEP_SECONDS", 0.1),
            bg_product_js_retries=_env_int("BG_PRODUCT_JS_RETRIES", 1),
            bg_product_js_429_sleep_seconds=_env_int("BG_PRODUCT_JS_429_SLEEP_SECONDS", 8),
            bg_product_js_max_products=_env_int("BG_PRODUCT_JS_MAX_PRODUCTS", 99999),
            bg_color_include_fabric=_env_bool("BG_COLOR_INCLUDE_FABRIC", True),
            bg_min_expected_active=_env_int("BG_MIN_EXPECTED_ACTIVE", 200),
            bg_new_arrivals_max_products=_env_int("BG_NEW_ARRIVALS_MAX_PRODUCTS", 800),
            bg_searchspring_results_per_page=_env_int("BG_SEARCHSPRING_RESULTS_PER_PAGE", 72),
            bg_searchspring_max_empty_pages=_env_int("BG_SEARCHSPRING_MAX_EMPTY_PAGES", 3),
            bg_strict_collection_filter=_env_bool("BG_STRICT_COLLECTION_FILTER", False),

            # =========================
            # Six Stories 配置
            # =========================
            ss_baseline_path=_env_str("SS_BASELINE_PATH", "sixstories_baseline.json"),
            ss_sheet_name=_env_str("SS_SHEET_NAME", "SS_伴娘服总表"),
            ss_enable_pdp_color_enrich=_env_bool("SS_ENABLE_PDP_COLOR_ENRICH", True),
            ss_extra_collection_handles=_env_str(
                "SS_EXTRA_COLLECTION_HANDLES",
                "",
            ),
            ss_enable_color_audit_sheet=_env_bool("SS_ENABLE_COLOR_AUDIT_SHEET", True),
            ss_pdp_recursive_color_enrich=_env_bool("SS_PDP_RECURSIVE_COLOR_ENRICH", True),
            ss_pdp_max_total_pages=_env_int("SS_PDP_MAX_TOTAL_PAGES", 1200),
            ss_pdp_max_pages_per_family=_env_int("SS_PDP_MAX_PAGES_PER_FAMILY", 80),
            ss_pdp_sleep_seconds=_env_float("SS_PDP_SLEEP_SECONDS", 2.0),
            ss_min_expected_active=_env_int("SS_MIN_EXPECTED_ACTIVE", 200),

            # =========================
            # Club L London 配置
            # =========================
            cl_base_url=_env_str("CL_BASE_URL", "https://clubllondon.com"),
            cl_collection_handle=_env_str("CL_COLLECTION_HANDLE", "bridesmaids"),
            cl_graphql_url=_env_str(
                "CL_GRAPHQL_URL",
                "https://club-l-london.myshopify.com/api/2026-01/graphql.json",
            ),
            cl_graphql_country=_env_str("CL_GRAPHQL_COUNTRY", "GB").upper(),
            cl_baseline_path=_env_str("CL_BASELINE_PATH", "clubllondon_baseline.json"),
            cl_sheet_name=_env_str("CL_SHEET_NAME", "CL_伴娘服总表"),
            cl_graphql_collection_page_size=_env_int("CL_GRAPHQL_COLLECTION_PAGE_SIZE", 250),
            cl_graphql_collection_sleep_seconds=_env_float("CL_GRAPHQL_COLLECTION_SLEEP_SECONDS", 0.3),
            cl_graphql_product_batch_size=_env_int("CL_GRAPHQL_PRODUCT_BATCH_SIZE", 15),
            cl_graphql_min_batch_size=_env_int("CL_GRAPHQL_MIN_BATCH_SIZE", 5),
            cl_graphql_429_sleep_seconds=_env_int("CL_GRAPHQL_429_SLEEP_SECONDS", 8),
            cl_graphql_batch_sleep_seconds=_env_float("CL_GRAPHQL_BATCH_SLEEP_SECONDS", 0.5),
            cl_enable_color_expansion=_env_bool("CL_ENABLE_COLOR_EXPANSION", True),
            cl_color_expansion_workers=_env_int("CL_COLOR_EXPANSION_WORKERS", 1),
            cl_color_expansion_sleep_seconds=_env_float("CL_COLOR_EXPANSION_SLEEP_SECONDS", 1.5),
            cl_color_expansion_max_seeds=_env_int("CL_COLOR_EXPANSION_MAX_SEEDS", 200),
            cl_html_retries=_env_int("CL_HTML_RETRIES", 1),
            cl_html_429_sleep_seconds=_env_int("CL_HTML_429_SLEEP_SECONDS", 10),
            cl_enable_products_json_fallback=_env_bool("CL_ENABLE_PRODUCTS_JSON_FALLBACK", False),
            cl_products_json_max_pages=_env_int("CL_PRODUCTS_JSON_MAX_PAGES", 20),
            cl_enable_product_js_fallback=_env_bool("CL_ENABLE_PRODUCT_JS_FALLBACK", True),
            cl_product_js_workers=_env_int("CL_PRODUCT_JS_WORKERS", 2),
            cl_product_js_sleep_seconds=_env_float("CL_PRODUCT_JS_SLEEP_SECONDS", 0.8),
            cl_429_sleep_seconds=_env_int("CL_429_SLEEP_SECONDS", 10),
            cl_enable_html_fallback=_env_bool("CL_ENABLE_HTML_FALLBACK", False),
            cl_html_max_pages=_env_int("CL_HTML_MAX_PAGES", 5),
            cl_enable_swym_fallback=_env_bool("CL_ENABLE_SWYM_FALLBACK", False),
            cl_swym_max_items=_env_int("CL_SWYM_MAX_ITEMS", 30),
            cl_swym_wait_ms=_env_int("CL_SWYM_WAIT_MS", 3500),
            cl_swym_sleep_seconds=_env_float("CL_SWYM_SLEEP_SECONDS", 0.5),
            cl_min_expected_active=_env_int("CL_MIN_EXPECTED_ACTIVE", 200),

            # =========================
            # Babyboo Fashion 配置
            # =========================
            bb_base_url=_env_str("BB_BASE_URL", "https://www.babyboofashion.com"),
            bb_collection_handle=_env_str("BB_COLLECTION_HANDLE", "bridesmaid"),
            bb_baseline_path=_env_str("BB_BASELINE_PATH", "babyboo_baseline.json"),
            bb_sheet_name=_env_str("BB_SHEET_NAME", "BB_伴娘服总表"),
            bb_shop_domain=_env_str("BB_SHOP_DOMAIN", "babyboofashion-com-au.myshopify.com"),
            bb_graphql_url=_env_str(
                "BB_GRAPHQL_URL",
                "https://babyboofashion-com-au.myshopify.com/api/2024-04/graphql.json",
            ),
            bb_graphql_country=_env_str("BB_GRAPHQL_COUNTRY", "AU").upper(),
            bb_graphql_batch_size=_env_int("BB_GRAPHQL_BATCH_SIZE", 35),
            bb_graphql_min_batch_size=_env_int("BB_GRAPHQL_MIN_BATCH_SIZE", 8),
            bb_graphql_include_inventory=_env_bool("BB_GRAPHQL_INCLUDE_INVENTORY", False),
            bb_enable_playwright_graphql_discovery=_env_bool("BB_ENABLE_PLAYWRIGHT_GRAPHQL_DISCOVERY", True),
            bb_view_more_max_clicks=_env_int("BB_VIEW_MORE_MAX_CLICKS", 30),
            bb_view_more_wait_ms=_env_int("BB_VIEW_MORE_WAIT_MS", 1800),
            bb_enable_products_json_fallback=_env_bool("BB_ENABLE_PRODUCTS_JSON_FALLBACK", True),
            bb_enable_html_fallback=_env_bool("BB_ENABLE_HTML_FALLBACK", True),
            bb_products_json_max_pages=_env_int("BB_PRODUCTS_JSON_MAX_PAGES", 20),
            bb_collection_max_pages=_env_int("BB_COLLECTION_MAX_PAGES", 3),
            bb_webyze_workers=_env_int("BB_WEBYZE_WORKERS", 8),
            bb_enable_product_js_missing=_env_bool("BB_ENABLE_PRODUCT_JS_MISSING", True),
            bb_product_js_workers=_env_int("BB_PRODUCT_JS_WORKERS", 1),
            bb_product_js_sleep_seconds=_env_float("BB_PRODUCT_JS_SLEEP_SECONDS", 1.5),
            bb_429_sleep_seconds=_env_int("BB_429_SLEEP_SECONDS", 10),
            bb_price_prefix=_env_str("BB_PRICE_PREFIX", "$"),
            bb_price_suffix=_env_str("BB_PRICE_SUFFIX", " AUD"),
            bb_min_expected_active=_env_int("BB_MIN_EXPECTED_ACTIVE", 100),

            # =========================
            # Hello Molly 配置
            # =========================
            hm_base_url=_env_str("HM_BASE_URL", "https://www.hellomolly.com"),
            hm_collection_path=_env_str("HM_COLLECTION_PATH", "collections/wedding-edit/bridesmaid"),
            hm_baseline_path=_env_str("HM_BASELINE_PATH", "hellomolly_baseline.json"),
            hm_sheet_name=_env_str("HM_SHEET_NAME", "HM_伴娘服总表"),
            hm_nosto_account_id=_env_str("HM_NOSTO_ACCOUNT_ID", "shopify-28120711254"),
            hm_nosto_category_path=_env_str("HM_NOSTO_CATEGORY_PATH", "Bridesmaid"),
            hm_nosto_page_size=_env_int("HM_NOSTO_PAGE_SIZE", 96),
            hm_nosto_max_pages=_env_int("HM_NOSTO_MAX_PAGES", 30),
            hm_nosto_segments=_env_str("HM_NOSTO_SEGMENTS", ""),
            hm_next_build_id=_env_str("HM_NEXT_BUILD_ID", ""),
            hm_enable_html_fallback=_env_bool("HM_ENABLE_HTML_FALLBACK", True),
            hm_collection_max_pages=_env_int("HM_COLLECTION_MAX_PAGES", 5),
            hm_detail_workers=_env_int("HM_DETAIL_WORKERS", 8),
            hm_max_product_detail_requests=_env_int("HM_MAX_PRODUCT_DETAIL_REQUESTS", 2000),
            hm_extra_product_handles=_env_str("HM_EXTRA_PRODUCT_HANDLES", ""),
            hm_min_expected_active=_env_int("HM_MIN_EXPECTED_ACTIVE", 100),


            # =========================
            # Retry Queue 配置
            # =========================
            enable_async_retry_queue=_env_bool("ENABLE_ASYNC_RETRY_QUEUE", True),
            retry_queue_dir=_env_str("RETRY_QUEUE_DIR", "runtime/retry_queue"),
            retry_queue_max_attempts=_env_int("RETRY_QUEUE_MAX_ATTEMPTS", 4),
            retry_delay_seconds=_env_float("RETRY_DELAY_SECONDS", 10.0),
            retry_backoff_multiplier=_env_float("RETRY_BACKOFF_MULTIPLIER", 2.0),
            retry_max_delay_seconds=_env_float("RETRY_MAX_DELAY_SECONDS", 90.0),
            retry_drain_max_wait_seconds=_env_float("RETRY_DRAIN_MAX_WAIT_SECONDS", 600.0),
            retry_drain_before_export=_env_bool("RETRY_DRAIN_BEFORE_EXPORT", True),

            # =========================
            # Google Sheets 配置
            # =========================
            gsheet_spreadsheet_id=_env_str("GSHEET_SPREADSHEET_ID", ""),
            gsheet_credentials_json=_env_str("GSHEET_CREDENTIALS_JSON", "credentials.json"),
        )
