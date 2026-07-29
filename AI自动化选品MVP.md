## 变更记录


|  版本  |    日期    | 变更内容 |  作者  |
|--------|------------|----------|--------|
| v1.0.0 | 2026-07-24 | 初稿     | shelly |


---
## 框架

三信号 → 机会池 → 选品方案草稿 → AI审批 → 负责人审批 → 写入选款 → 打版线下<br/>│                 │<br/>│                └─ 核心找款：竞品「上新 × 列表/热销靠前」<br/>├─ 竞品网站（雷达 AT 轨）<br/>├─ 社媒舆情（人工录入）<br/>└─ AZ 相似款历史销量（内部同属性）

![智能选品MVP流程图.png](https://file-paa.zoom.us/file/s3Za0_s_RcS9OD3DlQJpJA?filename=%E6%99%BA%E8%83%BD%E9%80%89%E5%93%81MVP%E6%B5%81%E7%A8%8B%E5%9B%BE.png&jwt=eyJhbGciOiJFUzI1NiIsImsiOiJ2dC8rcFVJKyJ9.eyJoZGlnIjpmYWxzZSwib3JpIjoibHlueC1pbnRlcmFjdGlvbiIsImV4cCI6MTc4NDg5MDkwMSwiZGlnIjoiNzVjN2U1ZjcwNTMzNWI1Yzc4MjYwODczZDgzNWVhN2UzMzM0ZTIwMWQ0YTc2ZGVkODg3OGM3ZGFmMmRjNGI1OSIsImlzcyI6ImZpbGUiLCJhdWQiOiJ6ZnMiLCJpaWMiOiJhdzEiLCJpYXQiOjE3ODQ4OTAwMDF9.qfwnrhujOlwgZYG7Ak25kAh5JtTWDN0apVnsO-1Puy-oO98YA8lrlXcQqm7_D2IAryWNmQk-xheTVj4ZerxwZw&Policy=eyJTdGF0ZW1lbnQiOlt7IkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NDg5MDkwMX19LCJSZXNvdXJjZSI6Imh0dHBzOi8vZmlsZS1wYWEuem9vbS51cy9maWxlL3MzWmEwX3NfUmNTOU9EM0RsUUpwSkE~ZmlsZW5hbWU9JUU2JTk5JUJBJUU4JTgzJUJEJUU5JTgwJTg5JUU1JTkzJTgxTVZQJUU2JUI1JTgxJUU3JUE4JThCJUU1JTlCJUJFLnBuZyZqd3Q9ZXlKaGJHY2lPaUpGVXpJMU5pSXNJbXNpT2lKMmRDOHJjRlZKS3lKOS5leUpvWkdsbklqcG1ZV3h6WlN3aWIzSnBJam9pYkhsdWVDMXBiblJsY21GamRHbHZiaUlzSW1WNGNDSTZNVGM0TkRnNU1Ea3dNU3dpWkdsbklqb2lOelZqTjJVMVpqY3dOVE16TldJMVl6YzRNall3T0RjelpEZ3pOV1ZoTjJVek16TTBaVEl3TVdRMFlUYzJaR1ZrT0RnM09HTTNaR0ZtTW1Sak5HSTFPU0lzSW1semN5STZJbVpwYkdVaUxDSmhkV1FpT2lKNlpuTWlMQ0pwYVdNaU9pSmhkekVpTENKcFlYUWlPakUzT0RRNE9UQXdNREY5LnFmd25yaHVqT2x3Z1pZRzdBazI1a0FoNUp0VFdETjBhcFZuc08tMVB1eS1vTzk4WUE4bHJsWGNRcW03X0QySUFyeVdObVFrLXhoZVRWajRaZXJ4d1p3In1dfQ__&Signature=jhTcNJnK6Cb5JgCbB5O0cQCZkraJcpDPvFuKnfNJQW6vVsH4rDSFprKDAjSlkfUcz00WTIJVQTAYHoKPkAuMrqb3gkFdYOcPFejMQxWgJKyKF3LPGk-uUquwfK7qOodmV7bwGsK5ngScdOGH09We0EBMjKFRwBUHUvmswrW4NEmmuFzRKRiprUoCCyrJWwBJaof-~vxbVcEdnURXwwp~banC1QmE1d4i51pi6PgTuABGkQlDLLEw5dkniWf6lBcou9mqMkQQyWFs0j9yc~gM5egKwRbwuyymFVrVGQMPP2ciIV7eIL8aC-DhIGIBJyBlz5H3soydo9yWqEc2yKmEhQ__&Key-Pair-Id=KL18RPQB3R725)


|  模块  |                  意图                   |          实现落点          |
|--------|-----------------------------------------|----------------------------|
| 目标   | 增量 + 提效；少漏竞品上新；缩短选品周期 | F1 机会池覆盖率 + 时长埋点 |
| 定价   | 基于 BOM 评价格优势                     | F5                         |
| 供应链 | **基于库存信息**评可生产性              | F6                         |
| AI     | 正式建议环节                            | F7                         |
| 埋点   | 追踪归因                                | F9                         |


---
## 1. Summary

本项目为 Azazie 各品类建设智能化选品闭环：
聚合竞品分析、社媒舆情、AZ 相似款历史销量表现，生成可编辑选品方案；
基于 **BOM 标准成本** 与竞品价带判断价格竞争力；
经 **AI 审批** 与 **品类负责人审批** 后写入选款提案。
目标是缩短信息搜集与方案准备时间，提高可上新质量，并通过轻量埋点为网站 **增量 GMV** 归因打底。

---
## 2. Background

### 2.1 Context

现网选款偏存档与销售追踪；运营找款依赖人工逛竞品站与社媒，信息搜集耗时长。
目前已具备信息监控、提案审批流，但缺少 **可量化的选品规则、成本预估、AI** **建议与审批能力**。
### 2.2 变更点


|   项    | 一期方案 |                                    本 PRD                                    |
|---------|----------|------------------------------------------------------------------------------|
| 主目标  | 提效搜集 | **增量** **+ 提效**（过程验收 + GMV 埋点）                                   |
| AI 分析 | 预填辅助 | **正式建议环节，参考 amazon-product-manager-skill 决策框架（生成选品提案）** |
| 定价    | 价带建议 | **基于** **BOM 评估价格优势**                                                |
| 供应链  | 弱       | **基于库存信息评估可生产性**                                                 |

### 2.3 用户矩阵


|  **角色**  |       **主要页面**        |                       **关键动作**                        |
|------------|---------------------------|-----------------------------------------------------------|
| 品类运营   | 监控 / 机会池 / 方案编辑  | 浏览监控信息 → 判断找款机会 → 生成方案 → AI建议→ 提交审批 |
| 品类负责人 | 审批队列 · 证据区         | 通过/驳回，看风险与冲突                                   |
| 商品负责人 | 成本/可生产性只读         | 本期协同查阅                                              |
| 管理层     | 总览摘要                  | 总览                                                      |


---
## 3. Objective

### 3.1 Objective

让商品运营在一个工作台完成「看见机会 → 写清改款与定价方案 → AI 建议 → 负责人审批 → 进选款」，减少无效跟款（价无优势、雷款、无生产能力），提升上新质量与速度，服务网站增量。
### 3.2 Key Results（SMART）


| KR  |            指标             |                                                一期目标                                                |             测量             |
|-----|-----------------------------|--------------------------------------------------------------------------------------------------------|------------------------------|
| KR1 | 竞品上新覆盖 + 选品周期     | **不漏**监控的竞品网站「上新且热销」机会；选品节奏从月/周缩短为 **按爬取批次**（目前为周频）           | 机会池覆盖率；方案创建时间戳 |
| KR2 | 单方案「信息搜集+成稿」时长 | **−50%**                                                                                               | 抽样日记 / 系统时间戳        |
| KR3 | AI 建议通过率               | ≥ **80%**（负责人若驳回记录原因，回流优化提示词/规则）                                                 | 审批日志                     |
| KR4 | 增量埋点完备                | 100% 写入选款的提案带系统字段 generation_source=system_hub_at。上架后可关联 30/60 天 GMV（报表可后置） | 数据验收                     |


---
## 4. Solution

### 4.1 UX / 用户流

flowchart LR<br/>S[三信号入库] --> P[机会池]<br/> P --> D[选品方案草稿]<br/> D --> AI[AI审批]<br/> AI --> F[选品方案]<br/> F --> R[负责人审批]<br/> R -->|通过| W[写入选款提案]<br/> R -->|驳回| D<br/> AI -->|运营override| F<br/> W --> Offline[打版线下]
**页面**
1. **监控报告**：竞品网站动态、社媒舆情、内部相似款表现
2. **分析洞察** **· 机会池**：上新 × 列表/热销靠前列表 → 生成草稿
3. **选品方案**：草稿编辑 → 提交 AI 建议 → 修改 → 提交审批
4. **审批队列**（负责人）
5. **写入选款结果回执**

**信息来源与附录**

|     信号      | 功能节 |                                                                                  详细字段                                                                                  |
|---------------|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 竞品网站      | F1     | 本节展开                                                                                                                                                                   |
| 社媒舆情      | F2     | Appendix C https://docs.zoom.us/doc/dIiDeRdkQpyx_RUSEk2PcQ?from=hub#appendix-c--%E7%A4%BE%E5%AA%92%E8%AF%81%E6%8D%AE%E6%9D%A5%E6%BA%90%E5%AD%97%E6%AE%B5                   |
| AZ 相似款销量 | F3     | Appendix D https://docs.zoom.us/doc/dIiDeRdkQpyx_RUSEk2PcQ?from=hub#appendix-d--%E5%86%85%E9%83%A8%E5%90%8C%E6%AC%BE%E5%8C%B9%E9%85%8D%E6%9D%A5%E6%BA%90%E5%AD%97%E6%AE%B5 |
| BOM 成本链    | F5     | Appendix E https://docs.zoom.us/doc/dIiDeRdkQpyx_RUSEk2PcQ?from=hub#appendix-e--bom-%E6%88%90%E6%9C%AC%E9%93%BE%E6%9D%A5%E6%BA%90%E5%AD%97%E6%AE%B5                        |
| 库存可生产性  | F6     | 本节 + 库存字段表                                                                                                                                                          |

### 4.2 Key Features

#### *F1 竞品机会：上新* *× 列表/热销靠前（核心找款）*

**业务定义**：竞品站「本轮上新」的款色，按官网列表序（销量向站可称热销）优先呈现，保证 **不漏可跟的上新机会**。<br/>**事实源**：竞品监控雷达 **AT 轨** Excel/GSheet（侧方案 §4.2、上新下架表逻辑说明.md）。
##### F1.1 心智模型


|    产品口头     |                                          系统含义                                          |
|-----------------|--------------------------------------------------------------------------------------------|
| 本周 / 上周     | **本轮爬取** vs **上一轮基线**（非自然周 SQL）                                             |
| 热销 / 列表靠前 | list_rank = 官网列表序；越小越靠前。仅 rank_semantics=sales_proxy 的站在 UI 写「热销靠前」 |
| 上新            | 本轮出现且上轮非 Active（新 SKC / 新颜色 / 下架后又上）                                    |
| 数据周次        | ISO 周 YYYY-Www                                                                            |

上新机会 = 上新表 LEFT JOIN 同批原始排序表.本周排序<br/>排序 = ORDER BY list_rank ASC NULLS LAST （仅 sales_proxy 默认池）<br/>主键 = normalize(product_key):::normalize(color_name)  → skc_key
##### F1.2 上新入表

is_new_color ∈ {是, 老款补货} 才进上新表。

| is_new_color |   new_type   |              判定              |
|--------------|--------------|--------------------------------|
| 是           | 新 SKC       | key 从未出现，且同款也不在基线 |
| 是           | 新颜色       | key 从未出现，同款已有其他色   |
| 老款补货     | 下架后又上新 | 曾 Delisted，本轮再出现        |
| 否           | —            | 不进上新表                     |

保护：空基线/初始化不上新爆炸；Active 过少跳过下架；新站首周只建档。
##### F1.3 排序字段


|      字段      |              含义              |
|----------------|--------------------------------|
| list_rank      | 列表页本周序                   |
| hot_rank       | **仅**独立热销榜；无则 null    |
| rank_joined    | list_rank 非空                 |
| on_hotlist     | hot_rank 非空（≠ rank_joined） |
| rank_semantics | sales_proxy | recency_proxy    |

recency_proxy 站（Oh Polly、House of CB 等）进「新到」池，**禁止**与销量池混排、禁止统称热销。
##### F1.4 AT 站点（现网）


|     站点      |        列表口径        | rank_semantics（上线前标定） |
|---------------|------------------------|------------------------------|
| Babyboo       | dresses                | 标定后写入；未标定不进默认池 |
| Oh Polly      | dresses · created-desc | recency_proxy                |
| House of CB   | category 时间戳        | recency_proxy                |
| Club L London | all-dresses            | 标定后写入                   |
| Azazie        | atelier-formal-dresses | 标定后写入                   |

只消费 **source_line=atelier**（由雷达 crawl_run / manifest 校验，禁止手填洗线）。故意导入 BD → 整批失败。
##### F1.5 Ingest（编码步骤）


| 步 |                                  行为                                   |
|----|-------------------------------------------------------------------------|
|  1 | 拉 AT 轨最新 *_report_*.xlsx 或 GSheet；校验 crawl_run / 双表 hash 同批 |
|  2 | 落 snapshot_id（文件）+ snapshot_row_id（行）；保留 ≥90 天              |
|  3 | 新鲜度：age>12h 告警；强制导入打 stale_forced                           |
|  4 | 按站点字段合同生成 skc_key；类目→AT 映射                                |
|  5 | 上新 ⋈ 排序 → 写 competitor_new_hot_opportunities                       |
|  6 | 幂等键 (ingest_batch_id, site_name, skc_key)                            |

**伪代码**
new  := 上新表 WHERE batch=:b AND source_line='atelier' AND site=:s<br/>rank := 原始排序表 WHERE batch=:b AND site=:s<br/>opp  := new LEFT JOIN rank ON skc_key<br/>opp.list_rank = coalesce(本周排序, 排序)<br/>opp.rank_joined = list_rank IS NOT NULL<br/>-- URL 不参与自动 join
##### F1.6 机会表核心字段（实现用）


|                        字段                         |    类型     |            说明             |
|-----------------------------------------------------|-------------|-----------------------------|
| opportunity_id                                      | string      | AT-{batch}-{site}-{skc_key} |
| ingest_batch_id                                     | string      | 批隔离                      |
| snapshot_id / snapshot_row_id                       | string      | 证据回溯                    |
| source_line                                         | string      | 校验后的 atelier            |
| data_week                                           | string      | YYYY-Www                    |
| site_name / brand / category_raw                    | string      |                             |
| skc_key / spu_key                                   | string      |                             |
| product_name / product_url / color_name / image_url | string      | url 仅佐证                  |
| list_price / sale_price                             | decimal     | 价带输入                    |
| detail_text / review_snippets / nav_context         | text        | AT 列优先                   |
| new_type / first_seen / last_delisted_at            |             |                             |
| list_rank / prev_rank / rank_delta                  |             |                             |
| rank_joined / on_hotlist / rank_semantics           |             |                             |
| quarantine_reason                                   | string null | join 冲突                   |

雷达列映射：排序→list_rank；上新类型/时间→new_type/first_seen；其余同构拷贝。下架表只进监控「下架动态」，不进机会主列表。
##### F1.7 机会池 UI 默认


|    筛选项    |                默认                |
|--------------|------------------------------------|
| 批次         | 最新 ingest_batch_id               |
| 站点         | AT 白名单                          |
| 仅有列表排名 | 开（rank_joined）                  |
| 池           | sales_proxy 默认；recency 单独 Tab |
| list_rank    | ≤50（可配）                        |

文案：默认「上新且列表靠前」；销量向站可显示「上新且热销靠前」。
##### F1.8 验收（编码完成定义）

6. 样例 Excel：有排名行顺序 = 按本周排序升序。
7. 无排名行标记「上新未上榜」，默认筛掉。
8. 初始化周机会=0 + 提示。
9. BD 伪装源整批失败、零写入。
10. 同 ISO 周两批不串配。
11. 方案可回溯到 snapshot_row_id。



---

#### *F2 社媒证据录入*

一期：**人工**粘贴 Ins（默认）链接 / 上传图文；自动爬取二期。

| 要点 |                               规格                               |
|------|------------------------------------------------------------------|
| 必填 | platform；post_url 或 media 至少一个；关联 opportunity 或 scheme |
| 翻车 | is_negative_viral → 人工支路 high_voc_risk                       |
| 存储 | 见 Appendix C；媒体不可覆盖 key；变更 bump evidence_version      |


---
#### *F3 AZ 相似款（内部同款）匹配*

维度：盘古 silhouette + fabric + color（母体=AT，不与 BD 混算）。

|    规则    |                          规格                          |
|------------|--------------------------------------------------------|
| 代表销量   | peers.sales_12m 的 **中位数**                          |
| 代表退货率 | Σ退货 / Σ售出；全 0 售出 → 退货维 unknown              |
| 信号       | internal_signal ∈ {poor, good, unknown}                |
| poor       | 销量中位 < AT 单 SKC P25 **或** 退货率 > AT P75        |
| unknown    | 无 peers / 低于 min_peers / 维不可判；**禁止**当无风险 |
| min_peers  | exact≥1；放宽丢色/丢面料族各 ≥3                        |
| 放宽顺序   | 命中率<20% 时：①丢颜色 ②丢面料族；记 match_level       |

详情见 Appendix D。

---
#### *F4 选品方案草稿（必填）*


|  字段组  |                                    字段                                     |
|----------|-----------------------------------------------------------------------------|
| 参考     | 竞品链接/图；可选内部 dd_goods_id                                           |
| 改款     | 改哪里（文本 + 领/袖/背/长度等结构）                                        |
| 规格     | 面料、廓形、领形、长度、颜色                                                |
| 定价     | cost_source、adopted_cost、currency、suggest_price、价带、no_cost_advantage |
| 可生产性 | inventory_* 标签与备注（F6）                                                |
| 销售意向 | 现货 / MTO（人可改 AI 建议）                                                |

草稿可保存；提交 AI / 审批前校验必填。

---
#### *F5 成本与定价（BOM* *链）*

优先级：bom → similar_bom → rule_estimate → manual（均记 cost_source）。

|    规则    |                                  规格                                   |
|------------|-------------------------------------------------------------------------|
| 建议售价   | adopted_cost * 5（倍数可配）                                            |
| BOM        | 当前版 APPLY_PRICE **恰好** **1 行**且状态有效才可自动 adopted          |
| stale      | 唯一行但更新 >180 天 → 需 at_ops_lead 确认才可 adopted                  |
| invalid    | 0 行禁止 adopted；多行须点选具体 version/row 后才可                     |
| 币种       | adopted_cost_currency 必填；与价带同币种同 FX 日，否则 band_valid=false |
| 价带       | 同站同批；按 SPU 中位价再算 P25–P75；SPU≥5 才 band_valid；禁止 min–max  |
| 无成本优势 | band_valid && suggest_price > band_high → no_cost_advantage=true        |
| 手填价带   | 仅 lead/负责人 + 理由                                                   |

SQL / 字段表见 Appendix E。

---
#### *F6 可生产性（基于库存信息）*

Owner：**基于库存信息评估可生产性**。一期不做完整采购交期大盘，用 **可落地的库存代理**。
##### F6.1 信号定义


|        标签         |                       计算（MVP）                        |                 数据来源（待联调确认表名）                  |
|---------------------|----------------------------------------------------------|-------------------------------------------------------------|
| similar_stock_depth | 同三维（或 match_level）内部 peers 的可用库存合计 / 中位 | ERP 库存（如 quantity_on_hand 类，见内部选品引擎 PRD §9.6） |
| fabric_stock_ok     | 方案主料对应物料/近似 pp_id 是否有可用库存               | BOM FABRIC pp_id × 物料库存                                 |
| low_inventory_risk  | peers 库存深度 < AT 品类 P25 **或** 主料无库存           | 上两行派生                                                  |
| second_process_flag | 存在二次工艺（辅助，非库存）                             | mps.goods_craft 或 BOM TRIMMING.is_second_process           |
| producibility       | ok / risky / unknown                                     | 见下                                                        |

if 无库存数据源: producibility = unknown（展示「库存数据未接，需人工判断」）<br/>else if low_inventory_risk: producibility = risky<br/>else: producibility = ok
capability_gap / fabric_gap（历史是否做过）作为 **辅证** 仍可计算，但 UI 主文案改为「库存可生产性」，避免与 Owner 表述冲突。
##### F6.2 方案字段


|        字段         |       说明       |
|---------------------|------------------|
| producibility       | ok/risky/unknown |
| similar_stock_depth | 数值可空         |
| fabric_stock_ok     | bool/unknown     |
| low_inventory_risk  | bool             |
| second_process_flag | bool             |
| producibility_note  | 短文本           |

##### F6.3 验收

12. 接上库存只读后，相似款有库存 → 多为 ok。
13. 主料无库存 → risky。
14. 库存源不可用 → unknown，不阻断建稿，AI/审批高亮「需人工确认可生产性」。


---
#### *F7 AI 建议*

 参考：[amazon-product-manager-skill](<u>https://github.com/KKKKkrisPhillllll/amazon-product-manager-skill/</u>)  
> 用途：指导 **如何把证据收成可审的选品提案建议**（Product Selection Memo 形态）
1. **结论先行**：先 Decision，再证据。  
2. **枚举决策**：`建议推 / 谨慎·MTO / 不建议推`。  
3. **多维再判**：上新热销、内部同款、BOM 价带、舆情、库存可生产性。  
4. **缺数坦白**：无证据标 unknown / 假设，禁止伪装无风险。  
5. **固定输出骨架**：结论 → 为什么(3–5) → 证据缺口 → 建议动作 → 风险 → **何种新证据会改结论**。  
6. **可推翻**：人 override + 负责人终审。

输入：方案内容 + gates 快照 + scheme_version（内容哈希）。
**Gates（事实，不算分）**
- no_cost_advantage
- high_voc_risk（VOC 自动「商品问题」P75 **或** 社媒翻车勾选）
- internal_signal（poor/good/unknown）
- producibility（ok/risky/unknown）及 low_inventory_risk

**输出四档**：recommend | cautious | mto | reject<br/>（建议推 / 谨慎 / 建议 MTO / 不建议推）
##### F7.1 允许集（LLM 不得越界）


| #  |                   条件                    |        允许         |                    附加                    |
|----|-------------------------------------------|---------------------|--------------------------------------------|
| R1 | high_voc ∧ internal=poor                  | cautious/mto/reject |                                            |
| R2 | no_cost_advantage ∧ internal=poor         | cautious/mto/reject |                                            |
| R3 | producibility=risky 或 low_inventory_risk | cautious/mto/reject |                                            |
| R4 | high_voc ∧ no_cost_advantage              | cautious/mto/reject |                                            |
| R5 | 仅单一风险（价/舆情/内部差）              | 四档                | recommend 须运营填 risk_ack_code，审批确认 |
| R6 | internal=unknown 或 producibility=unknown | 四档                | 必填 evidence_gap，审批高亮                |
| R7 | 全绿                                      | 四档                |                                            |

多规则：允许集取交集；必填字段取并集。<br/>risk_ack_code **仅运营填**，LLM 不得自填。
软闸门：可 override 后交审批；scheme_version 变更废止旧建议。<br/>输出结构：结论 → 证据（引用 gates）→ 建议动作 → 何种新证据会改结论。

---
#### *F8 负责人审批与写入选款*

- 角色：AT 品类负责人；通过 / 驳回（原因必填，服务 KR4）。
- 同事务：审批事件（approved_at）+ outbox + 主状态 **Sync_Pending**。
- 成功 → Synced_To_Selection；失败 → Sync_Failed（≤5 重试）→ Sync_Abandoned。
- generation_source **仅** system_hub_at（DB 约束）。
- 审批 UI：**不展示** generation_source 为推荐文案；可展示 AI 建议、gates、成本、库存结论。


---
#### *F9 增量埋点*


|                  字段                  |       位置        |   是否对人可见   |
|----------------------------------------|-------------------|------------------|
| generation_source=system_hub_at        | 方案/提案系统字段 | 审批默认隐藏     |
| scheme_id / ai_verdict / override_flag | 系统              | 内部/BI          |
| goods_id 回写                          | 上架后            | BI 做 30/60d GMV |


---
### 4.3 Technology

#### *状态机*


|       status        |      含义      |                可转                 |
|---------------------|----------------|-------------------------------------|
| Draft               | 编辑中         | → AI_Reviewing                      |
| AI_Reviewing        | 出建议中       | → AI_Done / Draft                   |
| AI_Done             | 有建议+version | → Pending_Approval / Draft          |
| Pending_Approval    | 待审           | → Sync_Pending / Rejected           |
| Rejected            | 驳回           | → Draft                             |
| Sync_Pending        | 已批，同步中   | → Synced_To_Selection / Sync_Failed |
| Sync_Failed         | 失败可重试     | → Sync_Pending / Sync_Abandoned     |
| Sync_Abandoned      | 放弃同步       | 终态                                |
| Synced_To_Selection | 已写入选款     | 终态                                |

#### *核心表*

- competitor_new_hot_opportunities
- selection_scheme_social_evidence
- internal_style_peers（视图/缓存）
- selection_schemes
- selection_scheme_ai_reviews
- selection_scheme_approvals
- selection_scheme_sync_outbox

#### *API（示意）*


|                  API                  |            说明             |
|---------------------------------------|-----------------------------|
| POST /at/opportunities/ingest         | 雷达批次入库                |
| GET /at/opportunities                 | 机会池列表                  |
| POST /at/schemes                      | 从机会建草稿                |
| PUT /at/schemes/{id}                  | 编辑（bump scheme_version） |
| POST /at/schemes/{id}/cost/resolve    | 成本解析                    |
| GET /at/schemes/{id}/producibility    | 库存可生产性                |
| POST /at/schemes/{id}/ai-review       | AI 建议                     |
| POST /at/schemes/{id}/submit-approval | 提交审批                    |
| POST /at/schemes/{id}/approve         | 事件+outbox+Sync_Pending    |
| POST /at/schemes/{id}/reject          | 驳回                        |
| POST /at/sync/retry                   | 重试                        |
| POST /at/social-evidence              | 社媒 CRUD                   |
| GET /at/internal-peers                | 相似款查询                  |

#### *LLM*

提示词版本化；金样例 ≥20；输出 JSON schema；关键规则违背数=0。
### 4.4 Assumptions

15. 列表靠前以 list_rank 为准；仅 sales_proxy 称「热销」。
16. 上周/本周 = 轮次基线 diff。
17. AT 站点与 rank_semantics 上线前标定。
18. BOM、库存只读账号可通。
19. VOC「商品问题」code 可映射；未就绪则仅社媒人工支路。
20. 选款 create-from-hub 支持 AT + system_hub_at。
21. 库存字段名以 ERP 联调锁定为准（见 F6）。


---
## Appendix A — 开发故事切片

22. 机会 ingest + 列表 API
23. 机会池 UI（上新×靠前）
24. 社媒证据 CRUD
25. 内部相似款 + internal_signal
26. 方案草稿 CRUD
27. Cost resolver + 价带
28. 库存 producibility
29. Gates + AI 建议
30. 审批 + outbox 同步
31. 埋点与时长统计

## Appendix B — 与 Demo 映射

selection-intelligence-platform：复用机会池/竞品动态/提案壳；新增状态机、AI 建议页、成本、库存结论、AT 审批队列；默认品类 AT。


---

## Appendix C — 社媒证据：来源+字段

### C.1 心智


|    口头     |           系统            |
|-------------|---------------------------|
| Ins 好/翻车 | 一条 social_evidence      |
| 社媒信号    | 挂机会/方案，非自动排名源 |

不做：自动爬取、全量情感分析。
### C.2 表 selection_scheme_social_evidence


|                 字段                  | 必填 |                  说明                  |
|---------------------------------------|------|----------------------------------------|
| evidence_id                           | 是   | PK                                     |
| scheme_id / opportunity_id            | 条件 | 至少关联其一（提交审批前 scheme 必填） |
| category                              | 是   | AT                                     |
| platform                              | 是   | instagram 默认                         |
| account_handle                        | 否   |                                        |
| post_url / media_uris                 | 条件 | 至少一                                 |
| caption_or_note                       | 否   |                                        |
| is_negative_viral                     | 是   | 默认 false                             |
| negative_summary                      | 条件 | 翻车建议填                             |
| evidence_version                      | 是   | 内容变更新增版本                       |
| media_content_hash                    | 条件 | 有媒体时                               |
| posted_at / captured_at / captured_by |      |                                        |

投影：social_refs 计数；翻车 → high_voc 人工支路。
### C.3 验收

仅链接或仅图可存；翻车置风险；变更废止 AI 建议。


---

## Appendix D — 内部同款：来源+字段

### D.1 来源

盘古属性 + AT 近 12m 销量/退货事实表（表名数据 Owner 锁定）。
### D.2 逻辑

peers := AT SKC 按 match_level 匹配<br/>rep_sales := MEDIAN(sales_12m)<br/>rep_return := SUM(return)/SUM(sold)  or unknown if SUM(sold)=0<br/>signal := poor | good | unknown   -- 见 F3
### D.3 视图字段 internal_style_peers

dd_goods_id、sales_12m、return_rate_12m、分位、is_poor_peer、match_level、image_url、computed_at。
方案汇总：internal_peer_count、internal_signal、internal_peers_snapshot（Top10）。
### D.4 验收

缺维提示；P25/P75 样例；unknown 不伪装 good；BD 不入 AT peers。


---

## Appendix E — BOM 成本链：来源+字段

### E.1 优先级

bom（valid 自动）→ similar_bom → rule_estimate（均价×米数+工艺费）→ manual。
### E.2 SQL（申报价）

**SELECT** bqvd.amount **AS** apply_price, bq.currency, bqv.version_no, bqv.updated_at, bq.status<br/>**FROM** ecshop.bom_quotation bq<br/>**JOIN** ecshop.bom_quotation_version bqv<br/>**ON** bqv.quotation_id = bq.**id** **AND** bqv.version_no = bq.current_version_no<br/>**JOIN** ecshop.bom_quotation_version_detail bqvd<br/>**ON** bqvd.version_id = bqv.**id** **AND** bqvd.**category** = 'APPLY_PRICE'<br/>**WHERE** bq.dd_goods_id = :dd_goods_id<br/>**AND** bq.status **IN** ('APPROVED','ACTIVE') *-- 联调锁定实枚举*<br/>**AND** bqvd.amount **IS** **NOT** **NULL**;<br/>*-- 应用层：cardinality==1 且未过期 → valid*<br/>*-- cardinality==1 且 updated_at 过旧 → stale*<br/>*-- 否则 invalid；多行需 UI 点选 detail_id*
### E.3 方案字段

cost_candidate_*、validation_status、adopted_cost、adopted_cost_currency、cost_source、selected_by/at/reason、suggest_price、band_low/high、band_valid、band_method（spu_p25_p75|manual_lead）、no_cost_advantage、cost_resolve_trace。
### E.4 价带

同批同站 → SPU 中位 → P25/P75；SPU<5 → band_valid=false。
### E.5 验收

valid 自动；stale 确认；0 行不可 adopted；4 vs 5 SPU；跨币种不对齐则不判优势。


---

## Appendix F — 文档与 PLAN


|     项     |                                               说明                                               |
|------------|--------------------------------------------------------------------------------------------------|
| 旧 MOB PRD | 废止跳转                                                                                         |
| PLAN.md    | 工程加固仍有效；与 v0.5 冲突处（如供应链叙事、KR）以 **本** **PRD 为准**，PLAN 需标注 superseded |
| 实现入口   | 建议先 M1：F1 ingest + 机会池 UI                                                                 |


