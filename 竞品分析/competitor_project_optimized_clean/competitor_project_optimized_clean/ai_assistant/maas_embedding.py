from __future__ import annotations

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()


class MaaSEmbeddingClient:
    def __init__(
        self,
        api_key: str | None = None,
        embedding_url: str | None = None,
        model: str | None = None,
        timeout: int = 60,
        max_retries: int = 3,
        batch_size: int = 64,
    ) -> None:
        self.api_key = api_key or os.getenv("MAAS_API_KEY", "").strip()
        self.embedding_url = embedding_url or os.getenv("MAAS_EMBEDDING_URL", "").strip()
        self.model = model or os.getenv("MAAS_EMBEDDING_MODEL", "MaaS_Embedding_3_small").strip()
        self.timeout = timeout
        self.max_retries = max_retries
        self.batch_size = batch_size

        if not self.api_key:
            raise ValueError("缺少 MAAS_API_KEY，请先在 .env 中配置。")

        if not self.embedding_url:
            raise ValueError("缺少 MAAS_EMBEDDING_URL，请先在 .env 中配置。")

        try:
            self.api_key.encode("latin-1")
        except UnicodeEncodeError as exc:
            raise ValueError("MAAS_API_KEY 包含中文或非法字符，请检查 .env。") from exc

    def embed_text(self, text: str) -> list[float]:
        """
        单条文本 embedding。
        内部复用批量方法，保证单条和批量逻辑一致。
        """
        embeddings = self.embed_texts([text])
        return embeddings[0]

    def embed_texts(self, texts: list[str], batch_size: int | None = None) -> list[list[float]]:
        """
        批量文本 embedding。

        这里是真正的批量请求：
        - 每批把多条文本一起放到 input 里；
        - MaaS 一次返回多条 embedding；
        - 不是 for 循环一条一条请求。
        """
        clean_texts = [self._clean_text(text) for text in texts]
        clean_texts = [text for text in clean_texts if text]

        if not clean_texts:
            raise ValueError("embedding 文本列表不能为空。")

        real_batch_size = batch_size or self.batch_size
        all_embeddings: list[list[float]] = []

        for start in range(0, len(clean_texts), real_batch_size):
            batch_texts = clean_texts[start:start + real_batch_size]

            payload = {
                "model": self.model,
                "input": batch_texts,
            }

            data = self._post_with_retry(payload)
            batch_embeddings = self._extract_embeddings(data, expected_count=len(batch_texts))

            all_embeddings.extend(batch_embeddings)

            print(
                f"Embedding 批量进度：{min(start + real_batch_size, len(clean_texts))}/{len(clean_texts)}"
            )

        return all_embeddings

    def get_embedding_dimension(self) -> int:
        """
        获取向量维度。
        后面创建 Pinecone index 时要用。
        """
        vector = self.embed_text("dimension test")
        return len(vector)

    def _post_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    self.embedding_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    return response.json()

                error_text = response.text[:1000]

                if response.status_code in {429, 500, 502, 503, 504}:
                    time.sleep(min(2 * attempt, 8))
                    continue

                raise RuntimeError(
                    f"MaaS Embedding 请求失败: status={response.status_code}, body={error_text}"
                )

            except Exception as exc:
                last_error = exc
                time.sleep(min(2 * attempt, 8))

        raise RuntimeError(f"MaaS Embedding 请求重试失败: {last_error}")

    def _extract_embeddings(
        self,
        data: dict[str, Any],
        expected_count: int,
    ) -> list[list[float]]:
        """
        从 MaaS 返回结果中提取 embedding。

        兼容 OpenAI 风格返回：
        {
            "data": [
                {"index": 0, "embedding": [...]},
                {"index": 1, "embedding": [...]}
            ]
        }
        """
        try:
            items = data["data"]
        except Exception as exc:
            raise RuntimeError(f"MaaS Embedding 返回结构异常: {data}") from exc

        if not isinstance(items, list):
            raise RuntimeError(f"MaaS Embedding data 不是列表: {data}")

        try:
            items = sorted(items, key=lambda item: item.get("index", 0))
        except Exception:
            pass

        embeddings: list[list[float]] = []

        for item in items:
            embedding = item.get("embedding")

            if not isinstance(embedding, list) or not embedding:
                raise RuntimeError(f"MaaS Embedding 单条结果异常: {item}")

            embeddings.append(embedding)

        if len(embeddings) != expected_count:
            raise RuntimeError(
                f"MaaS Embedding 返回数量不一致: expected={expected_count}, actual={len(embeddings)}, data={data}"
            )

        return embeddings

    @staticmethod
    def _clean_text(text: str) -> str:
        text = str(text or "").strip()
        return " ".join(text.split())


def build_product_embedding_text(row: dict[str, Any]) -> str:
    """
    把一行商品数据拼成适合 embedding 的文本。
    后面写入 Pinecone 时会用这个方法。
    """
    site = row.get("网站名", "")
    week = row.get("数据周次", "")
    rank = row.get("排序", "")
    rank_change = row.get("排名涨跌", "")
    product_name = row.get("商品名称", "")
    style_name = row.get("款式名", "")
    color = row.get("颜色名称", "")
    size = row.get("尺码", "")
    sale_price = row.get("售价", "")
    detail = row.get("商品详情描述", "")

    return f"""
Site: {site}
Week: {week}
Rank: {rank}
Rank Change: {rank_change}
Product Name: {product_name}
Style Name: {style_name}
Color: {color}
Size: {size}
Sale Price: {sale_price}
Description: {detail}
""".strip()


if __name__ == "__main__":
    client = MaaSEmbeddingClient()

    test_texts = [
        "Satin bridesmaid dress with cowl neckline and side slit.",
        "Ruched chiffon maxi dress with lace-up back.",
        "Strapless formal dress with corset bodice.",
    ]

    embeddings = client.embed_texts(test_texts)

    print("批量 Embedding 调用成功")
    print(f"返回数量：{len(embeddings)}")
    print(f"向量维度：{len(embeddings[0])}")
    print(f"第一条前 5 个向量值：{embeddings[0][:5]}")