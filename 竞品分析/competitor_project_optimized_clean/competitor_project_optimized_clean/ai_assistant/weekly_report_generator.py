from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv
from pinecone import Pinecone

from ai_assistant.color_swatch_resolver import build_color_markdown, resolve_color_swatch_assets
from ai_assistant.maas_embedding import MaaSEmbeddingClient
from ai_assistant.pinecone_upsert import read_original_product_tables, normalize_columns
from analysis.cross_site_comparison import build_cross_site_comparison


load_dotenv()


class MaaSChatClient:
    def __init__(
        self,
        api_key: str | None = None,
        chat_url: str | None = None,
        model: str | None = None,
        timeout: int = 120,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or os.getenv("MAAS_API_KEY", "").strip()
        self.chat_url = chat_url or os.getenv("MAAS_CHAT_URL", "").strip()
        self.model = model or os.getenv("MAAS_CHAT_MODEL", "").strip()
        self.timeout = timeout
        self.max_retries = max_retries

        if not self.api_key:
            raise ValueError("缺少 MAAS_API_KEY，请先在 .env 中配置。")

        if not self.chat_url:
            raise ValueError("缺少 MAAS_CHAT_URL，请先在 .env 中配置。")

        if not self.model:
            raise ValueError("缺少 MAAS_CHAT_MODEL，请先在 .env 中配置。")

    def generate(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是 Azazie 的 AI 竞品分析助手，擅长电商商品趋势、颜色趋势、款式趋势和业务建议分析。",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.2,
        }

        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    self.chat_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]

                if response.status_code in {429, 500, 502, 503, 504}:
                    time.sleep(min(2 * attempt, 10))
                    continue

                raise RuntimeError(
                    f"MaaS Chat 请求失败：status={response.status_code}, body={response.text[:1000]}"
                )

            except Exception as exc:
                last_error = exc
                time.sleep(min(2 * attempt, 10))

        raise RuntimeError(f"MaaS Chat 请求重试失败：{last_error}")


def safe_str(value: Any) -> str:
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def safe_rank(value: Any) -> int | None:
    text = safe_str(value).replace(",", "")

    if not text:
        return None

    try:
        return int(float(text))
    except Exception:
        return None


def extract_simple_attributes(text: str) -> dict[str, list[str]]:
    text_lower = safe_str(text).lower()

    taxonomy = {
        "面料": [
            "satin",
            "matte satin",
            "chiffon",
            "lace",
            "mesh",
            "tulle",
            "velvet",
            "crepe",
            "jersey",
            "sequin",
        ],
        "领型": [
            "cowl neck",
            "halter",
            "strapless",
            "v-neck",
            "square neck",
            "one shoulder",
            "asymmetric",
            "off shoulder",
            "scoop neck",
        ],
        "裙型": [
            "maxi",
            "midi",
            "mini",
            "a-line",
            "mermaid",
            "column",
            "slip",
            "bodycon",
            "wrap",
        ],
        "开叉": [
            "side slit",
            "high slit",
            "thigh split",
            "leg slit",
            "split",
        ],
        "工艺细节": [
            "ruched",
            "pleated",
            "corset",
            "lace-up",
            "bow",
            "beaded",
            "draped",
            "cape",
            "scarf",
            "cut out",
            "tie back",
        ],
    }

    result: dict[str, list[str]] = {}

    for group, keywords in taxonomy.items():
        matched = [keyword for keyword in keywords if keyword in text_lower]
        result[group] = matched

    return result


def summarize_by_site(df: pd.DataFrame) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []

    for site, site_df in df.groupby("网站名", dropna=False):
        site_name = safe_str(site) or "未知网站"
        total = len(site_df)

        detail_count = site_df["商品详情描述"].fillna("").astype(str).str.strip().ne("").sum() if "商品详情描述" in site_df.columns else 0
        size_count = site_df["尺码"].fillna("").astype(str).str.strip().ne("").sum() if "尺码" in site_df.columns else 0
        size_unknown_count = site_df["尺码"].fillna("").astype(str).str.strip().eq("未获取").sum() if "尺码" in site_df.columns else 0

        top_colors = []
        if "颜色名称" in site_df.columns:
            top_colors = (
                site_df["颜色名称"]
                .fillna("")
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
                .dropna()
                .value_counts()
                .head(10)
                .to_dict()
            )

        top_products = []
        if "排序" in site_df.columns:
            temp = site_df.copy()
            temp["_rank_num"] = temp["排序"].apply(safe_rank)
            temp = temp[temp["_rank_num"].notna()].sort_values("_rank_num").head(10)

            for _, row in temp.iterrows():
                top_products.append(
                    {
                        "排序": row.get("排序", ""),
                        "商品名称": row.get("商品名称", ""),
                        "颜色名称": row.get("颜色名称", ""),
                        "售价": row.get("售价", ""),
                        "商品链接": row.get("商品链接", ""),
                    }
                )

        summaries.append(
            {
                "网站名": site_name,
                "商品数": total,
                "详情覆盖率": round(detail_count / total * 100, 2) if total else 0,
                "尺码覆盖率": round((total - size_unknown_count) / total * 100, 2) if total else 0,
                "尺码非空率": round(size_count / total * 100, 2) if total else 0,
                "Top颜色": top_colors,
                "Top10商品": top_products,
            }
        )

    return summaries


def summarize_attributes(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    attribute_counter: dict[str, dict[str, int]] = {
        "面料": {},
        "领型": {},
        "裙型": {},
        "开叉": {},
        "工艺细节": {},
    }

    if "商品详情描述" not in df.columns:
        return attribute_counter

    for detail in df["商品详情描述"].fillna("").astype(str).tolist():
        attrs = extract_simple_attributes(detail)

        for group, values in attrs.items():
            for value in values:
                attribute_counter[group][value] = attribute_counter[group].get(value, 0) + 1

    sorted_result: dict[str, dict[str, int]] = {}

    for group, values in attribute_counter.items():
        sorted_result[group] = dict(
            sorted(values.items(), key=lambda item: item[1], reverse=True)[:15]
        )

    return sorted_result


def build_report_prompt(
    week: str,
    site_summaries: list[dict[str, Any]],
    attribute_summary: dict[str, dict[str, int]],
    comparison_summary: dict[str, Any] | None = None,
) -> str:
    comparison_text = json.dumps(comparison_summary or {}, ensure_ascii=False, indent=2)
    return f"""
你现在要生成一份 Azazie 竞品商品趋势周报。

数据周次：{week}

【重要要求】
1. 只能基于我提供的数据总结，不要编造没有出现的数据。
2. 如果当前只有本周数据，没有上周数据，不要写“周对周上升/下降”，只能写“本周观察”。
3. 输出要面向产品、运营、选品团队，重点说清楚竞品在推什么，以及 Azazie 可以怎么参考。
4. 不要写太空泛的分析，要尽量结合网站、颜色、面料、领型、裙型、工艺细节、Top 商品。
5. 中文输出。

【各网站数据概览】
{site_summaries}

【从商品详情描述中解析出的设计元素统计】
{attribute_summary}

【Azazie vs 竞品横向对比数据】
{comparison_text}

请按以下结构输出：

# {week} 竞品商品趋势周报

## 一、本周整体概览
简要说明本周覆盖了哪些网站、商品量级、数据质量情况。

## 二、Azazie vs 竞品总览
如果数据中包含 Azazie，请重点比较 Azazie 与竞品在颜色、价格带、上新、下架和排名变化上的差异，并指出机会点。
如果数据中不包含 Azazie，请说明 Azazie 数据未接入，本周只能输出竞品观察。

## 三、各网站重点观察
按网站分别总结：
- 商品数量
- 排名前列商品特点
- 主要颜色
- 明显设计元素
- 数据质量风险，如果有

## 四、颜色趋势观察
总结本周主要颜色分布、Azazie 覆盖情况和竞品机会色。不要在这里编造图片链接，图片由系统自动追加。

## 五、设计趋势观察
按面料、领型、裙型、开叉、工艺细节总结。

## 六、平台共性
总结多个网站共同出现的趋势。

## 七、对 Azazie 的建议
分成：
1. 选品建议
2. 列表页排序 / 推荐位建议
3. 营销素材建议
4. 下周继续观察点

## 八、数据风险说明
如果只有本周数据，请明确说明：当前无法判断真实周对周趋势，需要接入上周 Excel 后才能计算排名涨跌、上新和下架。
""".strip()


def upsert_weekly_report_to_pinecone(
    week: str,
    report_text: str,
    embedding_client: MaaSEmbeddingClient,
) -> None:
    api_key = os.getenv("PINECONE_API_KEY", "").strip()
    index_name = os.getenv("PINECONE_INDEX_NAME", "competitor-ai-assistant").strip()
    namespace = os.getenv("PINECONE_NAMESPACE_WEEKLY_REPORTS", "weekly_reports").strip()

    if not api_key or not index_name:
        print("未配置 Pinecone，跳过周报向量写入。")
        return

    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)

    embedding = embedding_client.embed_text(report_text)

    index.upsert(
        namespace=namespace,
        vectors=[
            {
                "id": f"weekly_report::{week}",
                "values": embedding,
                "metadata": {
                    "type": "weekly_report",
                    "week": week,
                    "title": f"{week} 竞品商品趋势周报",
                },
            }
        ],
    )

    print(f"周报已写入 Pinecone：namespace={namespace}, id=weekly_report::{week}")


def generate_weekly_report(
    week: str,
    input_path: Path,
    output_path: Path,
    write_pinecone: bool = True,
    comparison_path: Path | None = None,
    color_assets_root: Path | None = None,
) -> str:
    df = read_original_product_tables(input_path)
    df = normalize_columns(df)

    print(f"读取原始商品数据完成：rows={len(df)}")

    site_summaries = summarize_by_site(df)
    attribute_summary = summarize_attributes(df)
    comparison_summary = build_cross_site_comparison(input_path)

    if comparison_path:
        comparison_path.parent.mkdir(parents=True, exist_ok=True)
        comparison_path.write_text(
            json.dumps(comparison_summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    prompt = build_report_prompt(
        week=week,
        site_summaries=site_summaries,
        attribute_summary=attribute_summary,
        comparison_summary=comparison_summary,
    )

    chat_client = MaaSChatClient()
    report_text = chat_client.generate(prompt)

    color_candidates = list((comparison_summary.get("competitor_top_colors") or {}).keys())
    if not color_candidates:
        color_candidates = list((comparison_summary.get("overall_top_colors") or {}).keys())
    color_assets = resolve_color_swatch_assets(
        color_candidates[:5],
        week=week,
        output_root=color_assets_root or Path("data/report_assets"),
    )
    color_markdown = build_color_markdown(color_assets, max_items=5)
    if color_markdown:
        report_text = f"{report_text.rstrip()}\n\n---\n\n{color_markdown}\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")

    print(f"周报已生成：{output_path}")

    if write_pinecone:
        embedding_client = MaaSEmbeddingClient()
        upsert_weekly_report_to_pinecone(
            week=week,
            report_text=report_text,
            embedding_client=embedding_client,
        )

    return report_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly competitor report with MaaS Chat.")
    parser.add_argument("--week", required=True, help="数据周次，例如 2026-W23")
    parser.add_argument("--input", required=True, help="Excel 文件或目录，例如 output")
    parser.add_argument("--output", default=None, help="周报输出路径")
    parser.add_argument("--comparison-output", default=None, help="横向对比 JSON 输出路径")
    parser.add_argument("--color-assets-root", default=None, help="颜色图资产输出目录")
    parser.add_argument("--no-pinecone", action="store_true", help="只生成周报，不写入 Pinecone")

    args = parser.parse_args()

    output_path = Path(args.output) if args.output else Path("data/weekly_reports") / f"weekly_report_{args.week}.md"

    generate_weekly_report(
        week=args.week,
        input_path=Path(args.input),
        output_path=output_path,
        write_pinecone=not args.no_pinecone,
        comparison_path=Path(args.comparison_output) if args.comparison_output else None,
        color_assets_root=Path(args.color_assets_root) if args.color_assets_root else None,
    )


if __name__ == "__main__":
    main()