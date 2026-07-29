# 选品智能化平台 · Demo

面向 Azazie 选品链路的前端演示原型（Merchandising Intelligence）。  
用静态页面把「三信号监控 → 分析洞察 → 选品提案 → 自动刊登 → 配置」串成可点可看的工作台，便于评审信息架构与交互，不依赖后端。

---

## 正确打开路径（重要）

本 Demo 位于**嵌套目录**，请不要打开外层的「AI 自动刊登」页面：

```text
自动化选品/
└── selection-intelligence-platform/          ← 外层：另一套 AI 自动刊登 Demo（勿混用）
    ├── app.js / index.html / styles.css
    └── selection-intelligence-platform/      ← 本项目：选品智能化平台 ★
        ├── index.html
        ├── app.js
        ├── style.css
        ├── voc.js
        ├── internal.js
        ├── proposal.js
        ├── listing.js
        ├── pages.js
        └── README.md
```

请打开：

`自动化选品/selection-intelligence-platform/selection-intelligence-platform/index.html`

---

## 如何运行

本项目为纯静态前端，无需安装依赖。

**方式一：直接打开**

用浏览器打开 `index.html`（部分浏览器对本地模块/路径限制较少，一般可用）。

**方式二：本地静态服务（推荐）**

在本目录执行：

```bash
# Python
python -m http.server 5173

# 或 Node
npx --yes serve -l 5173
```

浏览器访问：`http://localhost:5173`

默认进入 **分析洞察 > 机会池**（`#insight-pool`）。

---

## 产品定位（一句话）

聚合 **竞品网站 · 产品数据 · 社媒舆情** 三信号，生成可执行选品方案，并衔接选款提案与 AI 自动刊登。

---

## 信息架构

| 能力域 | 菜单 | 说明 |
|--------|------|------|
| 监控报告 | 竞品网站动态 | 上新 / 排名 / 下架监控 |
| | 内部数据动态 | 内部选品建议引擎（属性钻取 / 建议清单 / 明细追溯） |
| | 社媒舆情动态 | VOC 舆情数据中心（问题总览 → 归因） |
| 分析洞察 | 机会池 | 三信号融合主入口，四象限 + 选品方案列表 |
| | 竞品热榜 | 上新 / 热榜 / 排名涨跌 |
| | 上新趋势 | 周度趋势与站点对比 |
| | 属性分析 | 颜色 / 廓形等维度榜单与四象限 |
| | 定价建议 | 竞品价带 vs AZ 价带 |
| 选品提案 | 提案列表 | 对齐选款管理系统列表 |
| | 创建提案 | 对齐现网创建提案表单（支持预填预留） |
| 自动刊登 | 任务列表 | 刊登任务工作台 |
| | 新建任务 | 基础信息 / 素材 / 模特 |
| | AI审核页 | 结构化字段 + 图片工作区 + 双人审核 |
| 配置 | 业务线权限 / 属性字典 / 打分权重 / 类目映射 / 用户管理 | 治理与映射 |

---

## 目录与脚本职责

| 文件 | 职责 |
|------|------|
| `index.html` | 壳层：侧栏、顶栏、内容区、Inspector、Toast |
| `style.css` | 统一视觉（深蓝侧栏、浅灰底、白卡片、紫/蓝主色） |
| `app.js` | 导航树、路由、机会池、全局事件、Toast |
| `voc.js` | 社媒舆情动态（六 Tab VOC 工作台） |
| `internal.js` | 内部数据动态（建议引擎三 Tab + 抽屉） |
| `proposal.js` | 创建提案完整表单与预填预留 |
| `listing.js` | 自动刊登三页（对齐 AI 刊登参考站的板块内容） |
| `pages.js` | 其余中等保真页面渲染与 `EXTRA_PAGE_RENDERERS` |

加载顺序：`voc.js` → `internal.js` → `proposal.js` → `listing.js` → `app.js` → `pages.js`（最后 `init()`）。

---

## 核心页面说明

### 1. 机会池（默认页）

- KPI、筛选、机会四象限、流转漏斗、选品方案列表  
- 操作：查看洞察、生成选品方案（进入独立生成页再提交）  
- 来源信号固定三格：**竞品 / 内部 / 舆情**

### 2. 内部数据动态

- 全局筛选 + 三 Tab：**属性钻取** / **建议清单（默认）** / **明细追溯**  
- 建议行进入追溯；属性详情抽屉；「生成方案草案 / 加入机会池」等 Toast

### 3. 社媒舆情动态

- VOC Hub 六 Tab：问题总览、明细搜索、整体分析、分类看板、趋势分析、归因  
- 联动：机会池 / 避雷榜 / 商品优化 / 研发待办 / SOP 建议

### 4. 创建提案

- 分组表单：基础信息、选款信息（图+佐证）、规格信息、补充信息  
- 保存草稿 / 提交提案校验  
- 预填预留（控制台可测）：

```js
openCreateProposalWithPrefill("pool");      // 机会池样例
openCreateProposalWithPrefill("internal");  // 内部建议样例
```

### 5. 自动刊登

- 任务列表：KPI + 快筛 + 盘古/AI/审核状态表  
- 新建任务：基础信息、素材上传、模特预览 → 发起 AI 生成  
- AI 审核页：指标条、中英描述与属性、图片工作区、运营/美国审核

---

## 路由约定

使用 hash 路由，例如：

| Hash | 页面 |
|------|------|
| `#insight-pool` | 机会池 |
| `#insight-pool/detail/{id}` | 机会洞察详情 |
| `#insight-pool/scheme/{id}` | 生成选品方案 |
| `#monitor-internal` | 内部数据动态 |
| `#monitor-sentiment` | 社媒舆情动态 |
| `#proposal-create` | 创建提案 |
| `#listing-list` / `#listing-new` / `#listing-review` | 自动刊登 |

---

## 设计约定

- **不做真实后端**：数据为 Mock，操作用 Toast 反馈  
- **不改导航结构时**：只改对应模块文件（如 `listing.js`），避免动 `NAV_TREE`  
- **视觉统一**：沿用 `style.css` 变量（`--primary` / `--accent` / `--bg` 等），新增样式写在同文件末尾分区注释下  
- **术语**：选品侧优先「提案 / 选品方案」，避免「案件」；三信号写清为竞品网站、产品数据、社媒舆情

---

## 当前边界

- 无登录鉴权、无真实上传与接口  
- 外层 `selection-intelligence-platform/` 的 AI 刊登 Demo 与本项目**并存但独立**  
- 部分页面仍为中等保真骨架，重点页（机会池、内部引擎、舆情、创建提案、自动刊登）保真度更高

---

## 建议后续

1. 理顺目录：将本 Demo 提升为独立文件夹名（如 `mi-platform/`），避免嵌套同名  
2. 接 API：先替换 `OPPORTUNITIES` / `INT_RECS` / `LISTING_TASKS` 等 Mock  
3. 打通「机会池 / 内部建议 → 创建提案」一键预填按钮（预填函数已预留）

---

## 维护提示

改功能时优先落点：

| 改什么 | 改哪里 |
|--------|--------|
| 侧栏菜单 | `app.js` → `NAV_TREE` |
| 机会池 | `app.js` |
| 舆情 | `voc.js` |
| 内部建议引擎 | `internal.js` |
| 创建提案 | `proposal.js` |
| 自动刊登 | `listing.js` |
| 其他列表页 | `pages.js` |
| 样式 | `style.css` |
