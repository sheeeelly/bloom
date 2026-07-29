"""商品数据记录模型 - 统一管理多站点表结构。

统一字段原则：
- 所有主商品表前置字段统一为：网站名 / 品牌 / 类目。
- 有款式名的站点继续保留「款式名」；有款号的站点继续保留「款号」。
- 保留原有类名与调用方式：ProductRecord / SSProductRecord / CLProductRecord。
- CLProductRecord 继续兼容 Babyboo 使用；若未显式传 brand，会自动用 site_name 填充品牌。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _default_brand(site_name: str, fallback: str = "") -> str:
    """根据 site_name 推断默认品牌，避免新增 brand 字段后旧代码不传 brand 造成空值。"""
    text = _safe_str(site_name)
    lower = text.lower()

    if "bird" in lower:
        return "Birdy Grey"
    if "six" in lower:
        return "Six Stories"
    if "club" in lower:
        return "Club L London"
    if "babyboo" in lower or "baby boo" in lower:
        return "Babyboo Fashion"
    if "hello" in lower or "molly" in lower:
        return "Hello Molly"

    return fallback or text


# ==========================================
# 👗 Birdy Grey (BG) 表结构
# ==========================================

HEADER_L1_CONFIG = [("原始排序表", 20)]

# 原始排序表字段：保留能还原官网顺序、识别 SKC、支持周对周排名涨跌的必要字段。
COLUMNS_L2 = [
    "排序", "排名涨跌",
    "网站名", "品牌", "类目",
    "商品唯一键 / SKC Key", "款式 ID / SPU Key", "款式名",
    "商品链接", "商品名称", "颜色名称", "尺码", "主图",
    "标价", "售价", "折扣类型", "定制/现货",
    "商品详情描述", "爬取时间", "数据周次",
]


@dataclass
class ProductRecord:
    site_name: str = "Birdy Grey"
    category: str = "Bridesmaid Dresses"
    brand: str = ""

    source_page_url: str = ""
    current_rank: int | str = ""
    previous_rank: int | str = ""
    rank_change: int | str = ""
    rank_trend: str = ""
    product_skc_key: str = ""
    style_spu_key: str = ""
    style_label: str = ""
    data_week: str = ""
    new_type: str = ""

    product_url: str = ""
    product_name: str = ""
    color_name: str = ""
    size: str = ""
    main_image_url: str = ""

    original_price: str = ""
    sale_price: str = ""
    discount_type: str = "无折扣"

    stock_type: str = "现货"
    detail_text: str = ""

    fabric_name: str = ""
    aesthetic_tag: str = ""
    length: str = ""
    neckline: str = ""

    scrape_time: str = ""
    release_date: str = ""
    is_new_color: str = "否"
    relisted_after_delisted: str = "否"
    last_delisted_at: str = ""
    is_official_new: str = "否"
    status: str = "Active"

    def __post_init__(self) -> None:
        if not _safe_str(self.brand):
            self.brand = _default_brand(self.site_name, "Birdy Grey")

    def to_row(self) -> list:
        return [
            self.current_rank, self.rank_change,
            self.site_name, self.brand, self.category,
            self.product_skc_key, self.style_spu_key, self.style_label,
            self.product_url, self.product_name, self.color_name, self.size, self.main_image_url,
            self.original_price, self.sale_price, self.discount_type, self.stock_type,
            self.detail_text, self.scrape_time, self.data_week,
        ]

    def to_metadata(self) -> dict:
        return {
            "site_name": self.site_name,
            "brand": self.brand,
            "category": self.category,
            "source_page_url": self.source_page_url,
            "current_rank": self.current_rank,
            "previous_rank": self.previous_rank,
            "rank_change": self.rank_change,
            "rank_trend": self.rank_trend,
            "product_skc_key": self.product_skc_key,
            "style_spu_key": self.style_spu_key,
            "style_label": self.style_label,
            "data_week": self.data_week,
            "new_type": self.new_type,
            "product_url": self.product_url,
            "product_name": self.product_name,
            "color_name": self.color_name,
            "size": self.size,
            "main_image_url": self.main_image_url,
            "original_price": self.original_price,
            "sale_price": self.sale_price,
            "discount_type": self.discount_type,
            "stock_type": self.stock_type,
            "detail_text": self.detail_text,
            "fabric_name": self.fabric_name,
            "aesthetic_tag": self.aesthetic_tag,
            "length": self.length,
            "neckline": self.neckline,
            "scrape_time": self.scrape_time,
            "release_date": self.release_date,
            "is_new_color": self.is_new_color,
            "relisted_after_delisted": self.relisted_after_delisted,
            "last_delisted_at": self.last_delisted_at,
            "is_official_new": self.is_official_new,
            "status": self.status,
        }


# ==========================================
# 🇬🇧 Six Stories (SS) 表结构
# ==========================================

HEADER_L1_CONFIG_SS = [("原始排序表", 20)]

COLUMNS_L2_SS = COLUMNS_L2


@dataclass
class SSProductRecord:
    site_name: str = "Six Stories"
    category: str = "Bridesmaid Dresses"
    brand: str = ""

    source_page_url: str = ""
    current_rank: int | str = ""
    previous_rank: int | str = ""
    rank_change: int | str = ""
    rank_trend: str = ""
    product_skc_key: str = ""
    style_spu_key: str = ""
    data_week: str = ""
    new_type: str = ""

    style_label: str = ""
    product_url: str = ""
    product_name: str = ""
    color_name: str = ""
    size: str = ""
    main_image_url: str = ""

    original_price: str = ""
    sale_price: str = ""
    discount_type: str = "无折扣"

    stock_type: str = "现货"
    detail_text: str = ""

    fabric_name: str = ""
    aesthetic_tag: str = ""
    length: str = ""
    neckline: str = ""

    scrape_time: str = ""
    release_date: str = ""
    is_new_color: str = "否"
    relisted_after_delisted: str = "否"
    last_delisted_at: str = ""
    is_official_new: str = "否"
    status: str = "Active"

    def __post_init__(self) -> None:
        if not _safe_str(self.brand):
            self.brand = _default_brand(self.site_name, "Six Stories")

    def to_row(self) -> list:
        return [
            self.current_rank, self.rank_change,
            self.site_name, self.brand, self.category,
            self.product_skc_key, self.style_spu_key, self.style_label,
            self.product_url, self.product_name, self.color_name, self.size, self.main_image_url,
            self.original_price, self.sale_price, self.discount_type, self.stock_type,
            self.detail_text, self.scrape_time, self.data_week,
        ]

    def to_metadata(self) -> dict:
        return {
            "site_name": self.site_name,
            "brand": self.brand,
            "category": self.category,
            "source_page_url": self.source_page_url,
            "current_rank": self.current_rank,
            "previous_rank": self.previous_rank,
            "rank_change": self.rank_change,
            "rank_trend": self.rank_trend,
            "product_skc_key": self.product_skc_key,
            "style_spu_key": self.style_spu_key,
            "data_week": self.data_week,
            "new_type": self.new_type,
            "style_label": self.style_label,
            "product_url": self.product_url,
            "product_name": self.product_name,
            "color_name": self.color_name,
            "size": self.size,
            "main_image_url": self.main_image_url,
            "original_price": self.original_price,
            "sale_price": self.sale_price,
            "discount_type": self.discount_type,
            "stock_type": self.stock_type,
            "detail_text": self.detail_text,
            "fabric_name": self.fabric_name,
            "aesthetic_tag": self.aesthetic_tag,
            "length": self.length,
            "neckline": self.neckline,
            "scrape_time": self.scrape_time,
            "release_date": self.release_date,
            "is_new_color": self.is_new_color,
            "relisted_after_delisted": self.relisted_after_delisted,
            "last_delisted_at": self.last_delisted_at,
            "is_official_new": self.is_official_new,
            "status": self.status,
        }


# ==========================================
# 🇬🇧 Club L London / Babyboo 共用表结构
# ==========================================

HEADER_L1_CONFIG_CL = [("原始排序表", 20)]

COLUMNS_L2_CL = COLUMNS_L2

# Babyboo 当前复用 CLProductRecord，为避免主流程改动，提供别名。
HEADER_L1_CONFIG_BB = HEADER_L1_CONFIG_CL
COLUMNS_L2_BB = COLUMNS_L2_CL


@dataclass
class CLProductRecord:
    site_name: str = "Club L London"
    category: str = "Bridesmaids"
    brand: str = ""

    source_page_url: str = ""
    current_rank: int | str = ""
    previous_rank: int | str = ""
    rank_change: int | str = ""
    rank_trend: str = ""
    product_skc_key: str = ""
    style_spu_key: str = ""
    data_week: str = ""
    new_type: str = ""

    style_label: str = ""
    product_url: str = ""
    product_name: str = ""
    color_name: str = ""
    size: str = ""
    main_image_url: str = ""

    original_price: str = ""
    sale_price: str = ""
    discount_type: str = "无折扣"

    stock_type: str = "现货"
    detail_text: str = ""

    fabric_name: str = ""
    aesthetic_tag: str = ""
    length: str = ""
    neckline: str = ""

    scrape_time: str = ""
    release_date: str = ""
    is_new_color: str = "否"
    relisted_after_delisted: str = "否"
    last_delisted_at: str = ""
    is_official_new: str = "否"
    status: str = "Active"

    def __post_init__(self) -> None:
        if not _safe_str(self.brand):
            self.brand = _default_brand(self.site_name, "Club L London")

    def to_row(self) -> list:
        return [
            self.current_rank, self.rank_change,
            self.site_name, self.brand, self.category,
            self.product_skc_key, self.style_spu_key, self.style_label,
            self.product_url, self.product_name, self.color_name, self.size, self.main_image_url,
            self.original_price, self.sale_price, self.discount_type, self.stock_type,
            self.detail_text, self.scrape_time, self.data_week,
        ]

    def to_metadata(self) -> dict:
        return {
            "site_name": self.site_name,
            "brand": self.brand,
            "category": self.category,
            "source_page_url": self.source_page_url,
            "current_rank": self.current_rank,
            "previous_rank": self.previous_rank,
            "rank_change": self.rank_change,
            "rank_trend": self.rank_trend,
            "product_skc_key": self.product_skc_key,
            "style_spu_key": self.style_spu_key,
            "data_week": self.data_week,
            "new_type": self.new_type,
            "style_label": self.style_label,
            "product_url": self.product_url,
            "product_name": self.product_name,
            "color_name": self.color_name,
            "size": self.size,
            "main_image_url": self.main_image_url,
            "original_price": self.original_price,
            "sale_price": self.sale_price,
            "discount_type": self.discount_type,
            "stock_type": self.stock_type,
            "detail_text": self.detail_text,
            "fabric_name": self.fabric_name,
            "aesthetic_tag": self.aesthetic_tag,
            "length": self.length,
            "neckline": self.neckline,
            "scrape_time": self.scrape_time,
            "release_date": self.release_date,
            "is_new_color": self.is_new_color,
            "relisted_after_delisted": self.relisted_after_delisted,
            "last_delisted_at": self.last_delisted_at,
            "is_official_new": self.is_official_new,
            "status": self.status,
        }


# ==========================================
# 颜色完整性检查表结构（用于 SS 等站点）
# ==========================================

HEADER_L1_CONFIG_COLOR_AUDIT = [
    ("颜色完整性检查", 8),
]

COLUMNS_L2_COLOR_AUDIT = [
    "网站名",
    "品牌",
    "款式名",
    "商品名称",
    "颜色数量",
    "颜色列表",
    "是否异常",
    "异常原因",
]


@dataclass
class ColorAuditRecord:
    site_name: str = ""
    brand: str = ""
    style_label: str = ""
    product_name: str = ""
    color_count: int = 0
    color_list: str = ""
    is_abnormal: str = "否"
    abnormal_reason: str = ""

    def __post_init__(self) -> None:
        if not _safe_str(self.brand):
            self.brand = _default_brand(self.site_name)

    def to_row(self) -> list:
        return [
            self.site_name,
            self.brand,
            self.style_label,
            self.product_name,
            self.color_count,
            self.color_list,
            self.is_abnormal,
            self.abnormal_reason,
        ]

    def to_metadata(self) -> dict:
        return {
            "site_name": self.site_name,
            "brand": self.brand,
            "style_label": self.style_label,
            "product_name": self.product_name,
            "color_count": self.color_count,
            "color_list": self.color_list,
            "is_abnormal": self.is_abnormal,
            "abnormal_reason": self.abnormal_reason,
        }
