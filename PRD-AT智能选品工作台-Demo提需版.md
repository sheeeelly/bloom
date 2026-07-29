# PRD-AT智能选品工作台（Demo 提需版）

> **版本**：v2.0.0 · **日期**：2026-07-29 · **试点**：AT（Atelier）  
> **受众**：产品 / 前端 / 后端 / 数据 / 测试（需求评审用）  
> **Demo 原型（验收对照）**：[`选品工作台/demo-at-mvp.html`](./选品工作台/demo-at-mvp.html) + [`demo-at-mvp.css`](./选品工作台/demo-at-mvp.css)  
> **Grill 锁定计划**：[`PLAN-demo-at-mvp-Bloom对齐.md`](./PLAN-demo-at-mvp-Bloom对齐.md)（已签核改 Demo）  
> **产品权威**：业务硬边界与 KR 以 [`PRD-AT智能选品MVP.md`](./PRD-AT智能选品MVP.md)（v0.5.x）为准；**本文是「工作台信息架构 + 页面合同 → 工程提需」**。  
> **冲突处理**：业务规则（AT 隔离、list_rank、BOM×5、generation_source、非目标）→ 总 PRD；**页面 IA / 筛选 / 三场景交互 / 回执形态** → 以本文 + 当前 Demo 为准，并回写总 PRD。

---

## 1. Summary

建设 Azazie **AT 智能选品工作台**：品类运营与负责人在同一系统完成「总览洞察 → 六频道监控 → 三场景选品管理 → 方案（左表单+右 AI）→ 审批写选款 + 历史回执」。本期按已验收 Demo 的信息架构交付可联调版本；数据优先对接竞品雷达周频产物（`source_line=atelier`）、广告投放、邮件主推、社媒人工录入、站内爆款；审批通过后写入选款并打 `generation_source=system_hub_at`（审批 UI 不展示为推荐理由）。

---

## 2. Contacts

| 姓名 | 角色 | 说明 |
|------|------|------|
| （Owner） | 产品负责人 | 范围、KR、五信号/爬取口径终审 |
| （AT 运营） | 主用户 | 流程可用性、字段必填、筛选手感 |
| （品类负责人） | 审批权威 | 通过/驳回/批注口径 |
| （研发接口人） | 前后端 | API / 表结构 / 权限 / 联调 |
| （数据/雷达） | 数据供给 | 周频批次、热卖榜主爬 + 上新轻量 WoW |
| Demo 参考 | 静态原型 | `选品工作台/demo-at-mvp.*` |

---

## 3. Background

### 3.1 现状

- 找款依赖人工逛站与表格，监控、机会、方案、审批分散。  
- 已有选款系统、竞品雷达、VOC/社媒入口，缺统一工作台闭环。  
- 妈妈版 Demo 已吸收 Bloom 合同面（五信号总览、映射、回执）并完成 Owner 向交互打磨，需工程化：真数据、权限、持久化、写选款。

### 3.2 为何现在

AT 试点要验证「少漏可跟机会 + 缩短成稿 + AI 可审 + 写选款可归因」；Demo 交互已冻结，适合按模块提需开工。

### 3.3 与总 PRD（v0.5）差异（评审必看）

| 项 | 总 PRD v0.5 | 本工作台合同（v2 / Demo） |
|----|-------------|---------------------------|
| 信号 | 三信号 | **五信号正式**：雷达·广告·邮件·社媒·AZ 相似；**流行趋势=第 6 监控频道，不进五源健康度分母** |
| 爬取 | 含 `recency_proxy` 分池叙事 | **热卖榜主爬 + 上新轻量 WoW**；禁止再用 recency 站统称「热销」 |
| 流水线 | 草稿 → AI → 审批 | **无独立 AI 路由**；打开/创建方案即右栏出 AI 全文 |
| 机会池 | 未细拆三场景 UI | **选品管理三 Tab**：纯新款 / 负向改款 / 正向改款（不用 Bloom 四池） |
| 站点配置页 | — | Demo 曾有「站点与市场」侧栏，**已删**；站点归属由主数据/账号上下文承接（本期可不单开菜单） |
| 属性映射 | — | **侧栏底部「演示数据」下入口**，全员可维护（真系统需审计，Later） |

> Owner 开放问题：总 PRD 正文「三信号 / recency」升版 checkbox 仍待勾选（见 Grill 计划）。未勾选前，工程实现以**本文五信号 + 爬取口径**交付，并在评审纪要中记录 Owner 确认。

---

## 4. Objective

### 4.1 Objective

让 AT 品类运营与负责人在工作台内完成可追溯选品闭环，减少漏跟与重复开款，缩短方案准备时间，并为增量 GMV 归因打底。

### 4.2 Key Results（沿用总 PRD，验收对照）

| KR | 目标 | 本期工作台映射 |
|----|------|----------------|
| KR1 | 不漏「上新且列表靠前」可跟机会；跟爬取批次（默认周频） | 监控·竞品网站 + 纯新款机会入池 |
| KR2 | 单方案信息搜集+成稿时长 **−50%** | 监控→入池→方案预填→右栏 AI |
| KR3 | 进入负责人审批的方案 **100%** 有 AI 建议记录 | 提交审批前必须存在 `ai_review` |
| KR4 | 负责人一次通过率 **≥80%**（驳回必填原因） | 审批页 + 历史回执可回看驳回/批注 |
| KR5 | 写入选款 100% 带 `generation_source=system_hub_at`；审批 UI 不展示为推荐理由 | 通过写选款 + 回执列表 |

---

## 5. Market Segment(s)

| 角色 | Jobs | 约束 |
|------|------|------|
| 品类运营（ops） | 看监控、入池、编方案、看 AI、提交审批、查阅回执/批注 | 仅 AT 轨数据；不可终审 |
| 品类负责人（lead） | 看完整方案+AI、批注、通过/驳回 | 驳回必填原因；审批页隐藏 generation_source 推荐文案 |
| 管理员（admin） | 切品类上下文（演示）、主数据类配置 | **不可终审**；BD 等品类文案须「接入中」 |
| 商品/管理层 | 总览只读（可后置深化） | MVP 可不写 |

**账号上下文（左下角）**

| 项 | 规则 |
|----|------|
| 身份 | ops / lead / admin 可切换（演示）；真系统接 SSO+RBAC |
| 品类 | **仅 admin 可改**；默认 AT；非 admin 锁定 AT |
| 市场 | 全员可切：全部 / US / UK / AU；监控与机会按「站点服务该市场」过滤，跨市场不混排 |

---

## 6. Value Proposition(s)

| 收益 | 避免的痛苦 |
|------|------------|
| 六频道监控 + 知衣式精简筛选一站看齐 | 多系统拷贝、漏看邮件/广告 |
| 三场景分治：纯新 / 修雷 / 热卖叠加 | 机会池语义混杂、重复开款 |
| 方案左表单对齐下版单，右栏 AI 可审 | 审批后再补资料、AI 与方案脱节 |
| 回执可看审批进度、驳回建议、批注、goods_id | 不知道卡在哪、驳回原因找不到 |
| 五源健康度与落地漏斗可对 Owner 汇报 | 只有局部报表、无法讲闭环 |

---

## 7. Solution

### 7.1 信息架构

```text
侧栏一级（固定顺序）
├─ 总览摘要
├─ 监控报告
│    ├─ 流行趋势          ← 不计入五源健康度
│    ├─ 竞品网站          ← 动态 | 分析报告
│    ├─ 广告投流
│    ├─ 竞品邮件主推
│    ├─ 社媒舆情          ← 一期人工录入
│    └─ 站内爆款
├─ 选品管理               ← 纯新款 | 负向改款 | 正向改款
├─ 方案编辑               ← 左方案字段 + 右 AI 全文（无独立 AI 菜单）
└─ 审批与选款             ← 上：审批；下：历史方案/回执

侧栏底部
├─ 演示数据（批次 · 品类轨 · 市场）
├─ 属性映射表             ← footer 入口
└─ 账号菜单（身份 / 品类 / 市场）
```

**明确删除（相对旧 Demo 提需 v1）**

- 独立「AI选款分析」导航与路由（`#ai` → 重定向方案页）  
- 侧栏「站点与市场」菜单（`#sitesConfig` → 重定向总览）  
- 选品卡片「AI分析」双按钮（统一为通栏「创建方案」）  
- 回执展开区「goods_id 与落地链路」大面板（goods_id 保留在列表列；生管打通后另开）

#### 7.1.1 跳转矩阵

| 从 | 动作 | 到 | 携带上下文 |
|----|------|----|------------|
| 监控·各频道 | 勾选 → 加入机会池 | 选品管理 | `monitor_ids[]` → `opportunity` |
| 选品管理·卡片 | 创建方案 | 方案编辑 | `opportunity_id`；预填 + **自动展示 AI** |
| AI 分项「数据来源」 | 点击 | 监控对应频道 / VOC 外链 | `mcTab` 或外链 |
| 方案编辑 | 提交 / 进入审批 | 审批与选款 | `scheme_id`；须已有 AI 记录 |
| 审批 | 通过 | 选款系统 | 同事务写选款 + `generation_source` |
| 审批 | 驳回 | 方案可再编辑 | `reject_reason` 必填 |
| 回执 | 查看进度 | 本页展开 | 进度条 + 驳回/批注 |

#### 7.1.2 前端路由建议

| route | 说明 |
|-------|------|
| `/dashboard` | 总览 |
| `/monitor/trends` | 流行趋势 |
| `/monitor/sites?view=feed\|report` | 竞品动态 / 周报 |
| `/monitor/ads` | 广告投流 |
| `/monitor/email` | 竞品邮件主推 |
| `/monitor/social` | 社媒舆情 |
| `/monitor/internal` | 站内爆款 |
| `/opportunities?scenario=` | 选品管理 |
| `/schemes/:id` | 方案编辑（含右栏 AI） |
| `/approvals/:schemeId` | 审批与选款（含回执） |
| `/attr-mapping` | 属性映射表 |

---

### 7.2 用户故事与验收标准（评审主表）

#### ep0 账号与权限

| ID | 用户故事 | 验收标准 |
|----|----------|----------|
| E0.1 | 作为运营，我只在 AT 上下文看数 | 非 admin 品类选择器禁用；数据 `source_line=atelier` / 品类线 AT |
| E0.2 | 作为任一角色，我可切换市场 | 切换后监控/邮件等按站点 markets 过滤；全部=不限 |
| E0.3 | 作为管理员，我可切到「BD·接入中」 | 界面明示接入中，不得表现为 BD 已上线全功能 |
| E0.4 | 作为运营，我不能通过/驳回 | 审批操作区仅「提交至负责人」；无通过/驳回按钮 |

#### M0 总览摘要

| ID | 用户故事 | 验收标准 |
|----|----------|----------|
| M0.1 | 作为 Owner，我看到北极星与护栏 | 展示增量 GMV/动销类北极星 + KR 护栏（覆盖/成稿/AI）示意 |
| M0.2 | 我看到五源健康度 | 仅五信号；流行趋势不进分母 |
| M0.3 | 我看到三场景机会分布 | 纯新 / 负向 / 正向计数可点击或对应到选品管理 |

#### M1 监控报告

| ID | 用户故事 | 验收标准 |
|----|----------|----------|
| M1.1 | 流行趋势可按周看元素/面料/颜色 | 有批次/周次；证据可点；**不进五源健康度** |
| M1.2 | 竞品网站动态可浏览并入池 | 卡片含站点、状态、价、折扣角标、list_rank、Ships Now；可勾选加入机会池 |
| M1.3 | 竞品筛选为三行知衣精简结构 | **R1 基础**：周次、品类、状态、Ships Now；**R2 竞品网站多选**；**R3 设计细节**（面料/廓形/领型/裙长/颜色/图案/袖长）；紧凑横排；checkbox 与站名同行对齐 |
| M1.4 | 折扣展示可读 | 角标文案为 **`{n}% OFF`**（非 `-n%`）；无折扣不展示 |
| M1.5 | 竞品分析报告可按周导出摘要 | 消费同批雷达数据；导出 Demo 可用 MD/文件 |
| M1.6 | 广告投流可看投放卡片 | 仅有投放或可筛有投放；指标：播放/天数/互动 |
| M1.7 | 广告筛选 | **媒体平台多选**：Facebook / Instagram / Tik Tok；+ 基础筛选 + 设计细节 |
| M1.8 | 邮件主推可浏览 | Hero/次推位；可关联机会；市场过滤生效 |
| M1.9 | 社媒可人工录入并挂机会 | 一期不做全自动爬取；好评/翻车可区分 |
| M1.10 | 站内爆款可进正负向机会 | 热榜+详情；可「加入负向/正向改款机会」 |
| M1.11 | 站内爆款筛选含设计细节 | 与监控共用设计细节字段过滤 |
| M1.12 | AT 硬隔离 | 禁止 BD 线商品洗入 AT 机会池；批处理遇洗线应失败或拒绝入池 |

**竞品监控 SKU 字段合同**

| 字段 | 类型 | 说明 |
|------|------|------|
| monitor_sku_id | string | 主键 |
| site / line | string | 站点 / 品类线；AT 硬隔离 |
| title, category, color, silhouette, neckline, fabric, length, sleeve?, pattern? | string | 属性 |
| price, list_price, discount | number | 现价/原价/折扣% |
| list_rank, prev_rank | int\|null | 列表序 |
| rank_semantics | enum | `sales_proxy` \| 其他；**仅 sales_proxy 可称热销靠前** |
| status | enum | 上新/上升/下降/下架 |
| ships_now | bool | 现货代理（非交期） |
| ad_plays, ad_clicks, ad_days | number | 投放 |
| platform | enum | Facebook / Instagram / TikTok |
| product_url | string | 外链 |
| batch_id / week_key | string | 周批次 |
| source_line | string | 必须 `atelier` 才可进 AT 池 |

#### M2 选品管理（机会池）

| ID | 用户故事 | 验收标准 |
|----|----------|----------|
| M2.1 | 三场景 Tab 语义清晰 | 纯新款 / 负向改款 / 正向改款；有说明 tip；**一层主类型 + 次行工具**（排序/筛选）感知分离 |
| M2.2 | 纯新款可排序 | 互斥：按热销榜（默认）/ 按上新时间 / 按广告投流力度；广告力度公式评审锁定（建议：归一后 `plays × days`） |
| M2.3 | 纯新款可筛邮件主推 | Checkbox「仅看竞品邮件主推」 |
| M2.4 | 纯新款卡片一行两张 | 大图；底部**仅通栏「创建方案」**（无 AI 分析按钮） |
| M2.5 | 负向改款 | 池顶警示定义口径；Bloom 式卡片：负反馈证据、市场销量分布、改款方向、信号条；一行两张；通栏「创建方案」 |
| M2.6 | 正向改款 | **上**：竞品热卖属性榜（集中度≥阈值，默认 1.5×）；点属性筛机会；**下**：底座×叠加卡片；一行两张；通栏「创建方案」 |
| M2.7 | 场景 key | `pure_new` \| `fix_negative` \| `fix_positive`（与映射/库表一致，禁止混用 `form_*`） |

**机会对象字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| opportunity_id / opportunity_code | string | 如 `OPP-AT-YYMM-xxx` |
| scenario | enum | 见上 |
| title, site, price | — | 展示 |
| monitor_sku_id | string\|null | 关联监控 |
| list_rank, rank_semantics | — | 冗余 |
| ships_now, ad_* , colors | — | 展示 |
| similar | `{ goods_id, note }`\|null | 内部关联 |
| neg_feedback | object\|null | 负向：退货/VOC/社媒 |
| overlay | `{ attr, src }`\|null | 正向叠加属性 |
| email_hero | bool\|null | 是否邮件主推 |
| status | enum | open / in_scheme / approved / rejected / archived |

#### M3 方案编辑 + AI（同页）

| ID | 用户故事 | 验收标准 |
|----|----------|----------|
| M3.1 | 从机会创建方案即预填 | 对齐下版单字段；展示关联机会 banner |
| M3.2 | 右侧自动出 AI | 无需「开始分析」主按钮；换机会重置分析上下文 |
| M3.3 | Decision 三枚举 | 建议推 / 谨慎·MTO / 不建议推 |
| M3.4 | 五维评分表 | 流行趋势、竞品网站热度、广告投放、内部相似款销售、社媒舆情；含结论与可跳转来源 |
| M3.5 | 建议动作 / 证据缺口 / 风险 | 缺数标 unknown；禁止伪装无风险 |
| M3.6 | 权重可调 | 弹窗调权重与阈值；保存快照进 `ai_review` |
| M3.7 | 定价展示 | 计划售价 + 品类倍率 → **最高成本价反算**；BOM×5 真成本可后置模块，但 KR/总 PRD F5 仍须在成本模块兑现 |
| M3.8 | 提交审批门禁 | **无 ai_review 不可提交**（KR3） |

**默认权重与阈值**

| 维度 | 默认权重 | 来源跳转 |
|------|----------|----------|
| 流行趋势 | 25% | 监控·流行趋势 |
| 竞品网站热度 | 25% | 监控·竞品网站 |
| 广告投放 | 20% | 监控·广告投流 |
| 内部相似款销售 | 15% | 监控·站内爆款 |
| 社媒舆情 | 15% | VOC/社媒频道 |

| 阈值 | 默认 | 决策 |
|------|------|------|
| go_score | 75 | ≥ → 建议推 |
| caution_score | 50 | ≥且 &lt; go → 谨慎·MTO |
| — | — | 否则不建议推 |

**相似款判定**：`silhouette, fabric, neckline, color, length` 双方均有值的属性相同比例 **≥ 80%**。

#### M4 审批与选款 + 回执

| ID | 用户故事 | 验收标准 |
|----|----------|----------|
| M4.1 | 运营提交 | 状态 → pending_approval |
| M4.2 | 负责人查看完整方案 | Modal/页：左方案 + 右 AI；可写批注 |
| M4.3 | 通过 | 写选款；`generation_source=system_hub_at`；审批 UI **不**把该字段当推荐理由 |
| M4.4 | 驳回 | `reject_reason` 必填；方案可回改再提 |
| M4.5 | 历史回执列表 | 列：方案、场景、审批状态、goods_id、写入选款状态、更新、操作 |
| M4.6 | 查看进度 | 展开区**仅**：① 横向审批进度条（成稿→提交→审批→写入选款）；② 驳回建议/负责人批注（**运营可阅**）。**不**展示落地链路大面板 |
| M4.7 | goods_id | 列表明示已关联/未关联；同步失败可重试 |
| M4.8 | 生管链路 | 本期进度节点可保留 future 占位文案「打通生管后可追踪」，但**不**在展开区做五段落地轨 UI |

**回执对象字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| scheme_id | string | 方案号 |
| title, scenario | — | 展示 |
| approval_status | enum | approved / rejected / in_review / submitted |
| sync_status | enum | Synced_To_Selection / Sync_Pending / Sync_Failed / N/A |
| goods_id | string\|null | 选款回写 |
| retries | int | 同步重试 |
| reject_reason | string\|null | 驳回建议 |
| annotations | string\|null | 负责人批注 |
| progress[] | `{ key, label, at, state, detail }` | key: draft/submit/review/sync/(plm/launch 可存库不展示) |
| updated_at | datetime | 更新时间 |

#### M5 属性映射表

| ID | 用户故事 | 验收标准 |
|----|----------|----------|
| M5.1 | 从侧栏底部进入 | 不在主导航抢注意力 |
| M5.2 | 维护内部标准属性 ⇄ 竞品叫法 | 待确认可生效；热卖属性榜与相似款依赖本表 |
| M5.3 | Demo 全员可写 | 真系统需审计日志（Later） |

---

### 7.3 状态机

#### 机会

```text
open → in_scheme → pending_approval → approved
                              ↘ rejected → open/in_scheme（可再提）
任意 → archived
```

#### 方案

```text
draft → pending_approval → approved → synced_to_selection
                 ↘ rejected → draft
synced 过程：sync_pending → synced | sync_failed（可重试）
```

#### 审批权限

```text
ops:   submit only
lead:  approve / reject(+reason) / annotate
admin: config only（品类等）；禁止 approve/reject
```

---

### 7.4 API / 数据落点（建议）

| 能力 | 方法（建议） | 备注 |
|------|--------------|------|
| 监控列表 | `GET /api/at/monitor/skus` | week, sites[], platforms[], design filters, market |
| 入池 | `POST /api/at/opportunities:bulkFromMonitor` | 校验 source_line |
| 机会列表 | `GET /api/at/opportunities` | scenario, sort, email_only, attr |
| 生成/更新方案 | `POST/PATCH /api/at/schemes` | |
| AI 分析 | `POST /api/at/schemes/{id}/ai-reviews` | 落库 params 快照 |
| 提交审批 | `POST /api/at/schemes/{id}/submit` | 校验 ai_review 存在 |
| 审批 | `POST /api/at/schemes/{id}/approve\|reject` | lead only |
| 回执列表 | `GET /api/at/schemes/receipts` | |
| 同步重试 | `POST /api/at/schemes/{id}/sync:retry` | |
| 属性映射 | `CRUD /api/at/attr-mappings` | |
| 写选款 | 内部同事务调用选款 API | 带 generation_source |

时区：业务时间默认美西 `America/Los_Angeles`（与公司规范冲突时在接口文档标明）。

---

### 7.5 Technology（实现约束）

- 前端：工作台 SPA；路由守卫按角色裁剪操作，不只藏按钮。  
- 后端：机会/方案/AI/审批/回执持久化；写选款失败进 outbox + 可重试。  
- 数据：雷达周频 AT 轨；广告库；邮件解析；社媒人工；站内销量/退货/VOC。  
- 安全：禁止把密钥与真实隐私运营数据写入前端仓库。

### 7.6 Assumptions

1. Owner 将确认总 PRD 五信号 + 爬取口径升版（或书面接受本文为过渡合同）。  
2. 一期社媒以人工录入为主；VOC 外链可用。  
3. BOM 真成本与库存可生产性可与工作台并行交付，但不得长期缺位导致 KR/总 PRD 无法验收。  
4. 生管/打版/上架状态回传为后续迭代；本期只保证选款 `goods_id` 回写与同步状态。

---

### 7.7 非目标（写死）

- 日频爬取、Ins/社媒全自动爬取  
- 交期大盘、全自动打样下单、全自动 AI 素材上架  
- 默认同时铺开 BD/MOB 全功能（admin「接入中」≠上线）  
- 用 `list_rank` 与热销混称；`recency_proxy` 站禁止统称「热销」  
- 独立 AI 菜单、独立 Gates 页、独立「写入选款回执」菜单  
- 回执展开区做生管五段落地轨大盘（本期）  
- 监控做竞品库存变化、智能合并/跨区合并、复色/大码/近 30 天价格变化（要则另开）

---

## 8. Release

| 阶段 | 相对时间 | 范围 |
|------|----------|------|
| **V1（本提需）** | T0–T+N（联调） | 上述 IA 全页面；Mock→真数据按频道切流；权限；方案+AI；审批写选款；回执列表+横向进度+批注；属性映射 |
| **V1.1** | V1 后 | BOM×5 真成本进方案/AI；库存可生产性 gates；广告力度公式配置化 |
| **V2** | 生管对接后 | goods_id 贯穿打版→齐套→上架→动销追踪 UI；回执展开可加落地轨 |
| **Later** | — | BD/MOB 扩面；社媒自动；日频；映射审计 |

### 8.1 评审检查清单（开会用）

- [ ] 五信号 vs 总 PRD 三信号：Owner 是否签字升版  
- [ ] 无独立 AI 页、创建方案通栏按钮：研发是否无歧义  
- [ ] 竞品三行筛选 + 广告媒体平台多选：字段与 API 是否对齐  
- [ ] 三场景 UI 差异（排序/属性榜/负向证据）：测试用例是否覆盖  
- [ ] KR3 提交门禁、KR5 generation_source：接口与埋点谁负责  
- [ ] 回执展开范围（仅进度+批注）：是否与生管 V2 边界清晰  
- [ ] AT 硬隔离与市场过滤：数据侧如何保证  

### 8.2 Demo 验收映射

| 模块 | Demo 入口 |
|------|-----------|
| 总览 | `#dashboard` |
| 监控六频道 | `#monitor` + 侧栏二级 |
| 选品三场景 | `#pool` |
| 方案+AI | `#scheme` |
| 审批+回执 | `#approval` →「查看进度」 |
| 属性映射 | 侧栏底部「属性映射表」 |

---

## 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-07-29 | 首版 Demo 提需（四频道、独立 AI、站点配置菜单） |
| **v2.0.0** | **2026-07-29** | **对齐 Grill 签核 + 当前 `demo-at-mvp`：六频道、五信号总览、方案右栏 AI、footer 映射、删站点菜单、筛选/卡片/回执交互冻结；升为开发需求评审合同** |
