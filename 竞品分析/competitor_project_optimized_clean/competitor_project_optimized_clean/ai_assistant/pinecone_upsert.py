from __future__ import annotations

import argparse
import os
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

from ai_assistant.maas_embedding import MaaSEmbeddingClient, build_product_embedding_text


load_dotenv()


ORIGINAL_SHEET_KEYWORD = "原始排序表"


COLUMN_ALIASES = {
    "排序": ["排序", "排名", "Rank", "rank"],
    "排名涨跌": ["排名涨跌", "Rank Change", "rank_change"],
    "网站名": ["网站名", "网站", "Site", "site"],
    "品牌": ["品牌", "Brand", "brand"],
    "类目": ["类目", "Category", "category"],
    "商品唯一键 / SKC Key": [
        "商品唯一键 / SKC Key",
        "商品唯一键/SKC Key",
        "商品唯一键",
        "SKC Key",
        "skc_key",
    ],
    "款式 ID / SPU Key": [
        "款式 ID / SPU Key",
        "款式ID / SPU Key",
        "款式ID",
        "SPU Key",
        "spu_key",
    ],
    "款式名": ["款式名", "Style Name", "style_name"],
    "商品链接": ["商品链接", "链接", "Product URL", "product_url"],
    "商品名称": ["商品名称", "商品名", "Product Name", "product_name"],
    "颜色名称": ["颜色名称", "颜色", "Color", "color"],
    "尺码": ["尺码", "Size", "size"],
    "主图": ["主图", "图片", "Image", "image_url"],
    "标价": ["标价", "Original Price", "original_price"],
    "售价": ["售价", "Sale Price", "sale_price"],
    "折扣类型": ["折扣类型", "Discount Type", "discount_type"],
    "定制/现货": ["定制/现货", "库存状态", "Stock Type", "stock_type"],
    "商品详情描述": ["商品详情描述", "商品描述", "Description", "description"],
    "爬取时间": ["爬取时间", "Scrape Time", "scrape_time"],
    "数据周次": ["数据周次", "Week", "week"],
}


class PineconeProductUpserter:
    def __init__(
        self,
        api_key: str | None = None,
        index_name: str | None = None,
        cloud: str | None = None,
        region: str | None = None,
        metric: str | None = None,
        dimension: int | None = None,
        namespace: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("PINECONE_API_KEY", "").strip()
        self.index_name = index_name or os.getenv("PINECONE_INDEX_NAME", "competitor-ai-assistant").strip()
        self.cloud = cloud or os.getenv("PINECONE_CLOUD", "aws").strip()
        self.region = region or os.getenv("PINECONE_REGION", "us-east-1").strip()
        self.metric = metric or os.getenv("PINECONE_METRIC", "cosine").strip()
        self.namespace = namespace or os.getenv("PINECONE_NAMESPACE_PRODUCTS", "products").strip()

        if not self.api_key:
            raise ValueError("缺少 PINECONE_API_KEY，请先在 .env 中配置。")

        try:
            self.api_key.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError("PINECONE_API_KEY 包含中文或非法字符，请检查 .env。") from exc

        if not self.index_name:
            raise ValueError("缺少 PINECONE_INDEX_NAME，请先在 .env 中配置。")

        if not dimension:
            dimension_value = os.getenv("PINECONE_DIMENSION", "").strip()

            if not dimension_value or "待填写" in dimension_value:
                raise ValueError(
                    "缺少有效的 PINECONE_DIMENSION。请先运行 python -m ai_assistant.maas_embedding 获取向量维度，"
                    "然后写入 .env，例如 PINECONE_DIMENSION=1536。"
                )

            dimension = int(dimension_value)

        self.dimension = int(dimension)

        self.pc = Pinecone(api_key=self.api_key)

        self._ensure_index()
        self.index = self.pc.Index(self.index_name)

    def _ensure_index(self) -> None:
        if self.pc.has_index(self.index_name):
            return

        self.pc.create_index(
            name=self.index_name,
            dimension=self.dimension,
            metric=self.metric,
            spec=ServerlessSpec(
                cloud=self.cloud,
                region=self.region,
            ),
        )

        print(f"Pinecone index 已创建：{self.index_name}")

        # 新建 index 后稍等一下，避免马上 upsert 时 index 还没 ready
        time.sleep(10)

    def upsert_products(
        self,
        df: pd.DataFrame,
        week: str,
        embedding_client: MaaSEmbeddingClient,
        embedding_batch_size: int = 64,
        upsert_batch_size: int = 100,
    ) -> None:
        df = df.copy()
        df = normalize_columns(df)
        df = self._filter_valid_rows(df)

        if df.empty:
            print("没有可写入 Pinecone 的商品数据。")
            return

        texts = [
            build_product_embedding_text(row)
            for row in df.to_dict(orient="records")
        ]

        embeddings = embedding_client.embed_texts(
            texts=texts,
            batch_size=embedding_batch_size,
        )

        if len(embeddings) != len(df):
            raise RuntimeError(
                f"embedding 数量与商品行数不一致：embeddings={len(embeddings)}, rows={len(df)}"
            )

        vectors: list[dict[str, Any]] = []

        for row, embedding in zip(df.to_dict(orient="records"), embeddings):
            vector_id = self._build_product_vector_id(row=row, week=week)
            metadata = self._build_product_metadata(row=row, week=week)

            vectors.append(
                {
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata,
                }
            )

        total = len(vectors)

        for start in range(0, total, upsert_batch_size):
            batch = vectors[start:start + upsert_batch_size]

            self.index.upsert(
                vectors=batch,
                namespace=self.namespace,
            )

            print(f"Pinecone products upsert 进度：{min(start + upsert_batch_size, total)}/{total}")

        print(f"Pinecone products upsert 完成：namespace={self.namespace}, total={total}")

    def _filter_valid_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        required_columns = [
            "网站名",
            "商品唯一键 / SKC Key",
            "商品名称",
        ]

        for column in required_columns:
            if column not in df.columns:
                raise ValueError(f"缺少必要字段：{column}，当前字段={list(df.columns)}")

        df["商品唯一键 / SKC Key"] = df["商品唯一键 / SKC Key"].fillna("").astype(str).str.strip()
        df["商品名称"] = df["商品名称"].fillna("").astype(str).str.strip()

        df = df[df["商品唯一键 / SKC Key"] != ""]
        df = df[df["商品名称"] != ""]

        return df

    def _build_product_vector_id(self, row: dict[str, Any], week: str) -> str:
        site = self._slug(row.get("网站名", "unknown"))
        skc_key = self._slug(row.get("商品唯一键 / SKC Key", ""))

        return f"product::{week}::{site}::{skc_key}"

    def _build_product_metadata(self, row: dict[str, Any], week: str) -> dict[str, Any]:
        metadata = {
            "type": "product",
            "week": week,
            "site": row.get("网站名", ""),
            "brand": row.get("品牌", ""),
            "category": row.get("类目", ""),
            "skc_key": row.get("商品唯一键 / SKC Key", ""),
            "spu_key": row.get("款式 ID / SPU Key", ""),
            "product_name": row.get("商品名称", ""),
            "style_name": row.get("款式名", ""),
            "color": row.get("颜色名称", ""),
            "size": row.get("尺码", ""),
            "rank": self._safe_number(row.get("排序")),
            "rank_change": str(row.get("排名涨跌", "") or ""),
            "sale_price": str(row.get("售价", "") or ""),
            "product_url": row.get("商品链接", ""),
            "image_url": row.get("主图", ""),
        }

        return self._clean_metadata(metadata)

    @staticmethod
    def _safe_number(value: Any) -> int | float | str:
        if value is None:
            return ""

        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass

        if isinstance(value, (int, float)):
            return value

        text = str(value).strip()

        if not text:
            return ""

        try:
            number = float(text)
            if number.is_integer():
                return int(number)
            return number
        except Exception:
            return text

    @staticmethod
    def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}

        for key, value in metadata.items():
            if value is None:
                cleaned[key] = ""
                continue

            try:
                if pd.isna(value):
                    cleaned[key] = ""
                    continue
            except Exception:
                pass

            if isinstance(value, (str, int, float, bool)):
                cleaned[key] = value
            else:
                cleaned[key] = str(value)

        return cleaned

    @staticmethod
    def _slug(value: Any) -> str:
        text = str(value or "").strip().lower()
        text = re.sub(r"\s+", "-", text)
        text = re.sub(r"[^a-z0-9_\-:.]+", "-", text)
        text = re.sub(r"-+", "-", text).strip("-")
        return text or "unknown"


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    rename_map: dict[str, str] = {}

    for standard_name, aliases in COLUMN_ALIASES.items():
        if standard_name in df.columns:
            continue

        for alias in aliases:
            if alias in df.columns:
                rename_map[alias] = standard_name
                break

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


def read_sheet_with_auto_header(excel_file: Path, sheet_name: str) -> pd.DataFrame:
    """
    适配当前 Excel：
    第 1 行是标题：原始排序表
    第 2 行才是真正表头：排序、排名涨跌、网站名...
    """
    raw = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)

    header_row_index: int | None = None

    for index in range(min(10, len(raw))):
        row_values = [str(value).strip() for value in raw.iloc[index].tolist() if not pd.isna(value)]

        if "商品唯一键 / SKC Key" in row_values and "商品名称" in row_values:
            header_row_index = index
            break

        if "排序" in row_values and "商品链接" in row_values and "商品名称" in row_values:
            header_row_index = index
            break

    if header_row_index is None:
        raise ValueError(f"无法识别表头行：file={excel_file.name}, sheet={sheet_name}")

    headers = raw.iloc[header_row_index].tolist()
    headers = [str(header).strip() if not pd.isna(header) else "" for header in headers]

    data = raw.iloc[header_row_index + 1:].copy()
    data.columns = headers

    data = data.loc[:, [column for column in data.columns if column]]

    data = data.dropna(how="all")

    data["source_file"] = excel_file.name
    data["source_sheet"] = sheet_name

    data = normalize_columns(data)

    if "网站名" not in data.columns or data["网站名"].fillna("").astype(str).str.strip().eq("").all():
        data["网站名"] = infer_site_name(excel_file.name, sheet_name)

    return data


def infer_site_name(file_name: str, sheet_name: str) -> str:
    source_text = f"{file_name} {sheet_name}".lower()

    if "babyboo" in source_text or "bb_" in source_text or "bb" in source_text:
        return "Babyboo Fashion"

    if "club" in source_text or "cl_" in source_text or "cl" in source_text:
        return "Club L London"

    if "hello" in source_text or "hm_" in source_text or "hm" in source_text:
        return "Hello Molly"

    if "six" in source_text or "ss_" in source_text or "ss" in source_text:
        return "Six Stories"

    if "birdy" in source_text or "bg_" in source_text or "bg" in source_text:
        return "Birdy Grey"

    return ""


def read_original_product_tables(input_path: Path) -> pd.DataFrame:
    if input_path.is_dir():
        excel_files = sorted(
            file for file in input_path.glob("*.xlsx")
            if not file.name.startswith("~$")
        )
    else:
        excel_files = [input_path]

    if not excel_files:
        raise ValueError(f"没有找到 Excel 文件：{input_path}")

    frames: list[pd.DataFrame] = []

    for excel_file in excel_files:
        xls = pd.ExcelFile(excel_file)

        for sheet_name in xls.sheet_names:
            if ORIGINAL_SHEET_KEYWORD not in sheet_name:
                continue

            df = read_sheet_with_auto_header(excel_file, sheet_name)
            frames.append(df)

    if not frames:
        raise ValueError(f"没有读取到任何包含「{ORIGINAL_SHEET_KEYWORD}」的 sheet：{input_path}")

    return pd.concat(frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Upsert competitor product vectors to Pinecone.")
    parser.add_argument("--week", required=True, help="数据周次，例如 2026-W23")
    parser.add_argument("--input", required=True, help="Excel 文件或目录，例如 output 或 data/raw_excel/2026-W23")
    parser.add_argument("--embedding-batch-size", type=int, default=64)
    parser.add_argument("--upsert-batch-size", type=int, default=100)

    args = parser.parse_args()

    input_path = Path(args.input)

    df = read_original_product_tables(input_path)

    print(f"读取商品数据完成：rows={len(df)}")
    print(f"字段：{list(df.columns)}")

    embedding_client = MaaSEmbeddingClient()
    upserter = PineconeProductUpserter()

    upserter.upsert_products(
        df=df,
        week=args.week,
        embedding_client=embedding_client,
        embedding_batch_size=args.embedding_batch_size,
        upsert_batch_size=args.upsert_batch_size,
    )


if __name__ == "__main__":
    main()