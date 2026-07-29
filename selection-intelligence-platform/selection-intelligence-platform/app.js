/**
 * 选品智能化平台 · Demo
 * Merchandising Intelligence Platform
 */

const NAV_TREE = [
  {
    group: "监控报告",
    items: [
      {
        id: "monitor-competitor",
        label: "竞品网站动态",
        crumb: "监控报告 / 竞品网站动态",
        title: "竞品网站动态",
        desc: "雷达上新 / 下架 / 排名监控 + 竞品热榜 + 上新趋势，支持加入机会池。",
      },
      {
        id: "monitor-internal",
        label: "内部数据动态",
        crumb: "监控报告 / 内部数据动态",
        title: "内部数据动态",
        desc: "基于内部商品、销售、行为和退货数据，识别属性机会、覆盖空档与可执行选品建议。",
      },
      {
        id: "monitor-sentiment",
        label: "社媒舆情动态",
        crumb: "监控报告 / 社媒舆情动态",
        title: "社媒舆情动态",
        desc: "聚合多平台用户反馈，识别商品机会、体验槽点与选品风险。",
      },
    ],
  },
  {
    group: "分析洞察",
    items: [
      {
        id: "insight-pool",
        label: "机会池",
        crumb: "分析洞察 / 机会池",
        title: "机会池",
        desc: "竞品网站 · 产品数据 · 社媒舆情三信号融合主入口 · 形成可执行选品方案",
      },
      {
        id: "insight-attr",
        label: "属性分析",
        crumb: "分析洞察 / 属性分析",
        title: "属性分析",
        desc: "颜色 / 廓形 / 领型 / 面料 / 设计元素榜单与四象限。",
      },
      {
        id: "insight-pricing",
        label: "定价建议",
        crumb: "分析洞察 / 定价建议",
        title: "定价建议",
        desc: "竞品价带 vs AZ 价带，生成建议价格。",
      },
    ],
  },
  {
    group: "选品提案",
    items: [
      {
        id: "proposal-list",
        label: "提案列表",
        crumb: "选品提案 / 提案列表",
        title: "提案列表",
        desc: "对齐选款管理系统提案列表。",
      },
      {
        id: "proposal-create",
        label: "创建提案",
        crumb: "选品提案 / 创建提案",
        title: "创建提案",
        desc: "对齐现网选款创建提案表单，支持手工录入与来源预填。",
      },
    ],
  },
  {
    group: "自动刊登",
    items: [
      {
        id: "listing-list",
        label: "任务列表",
        crumb: "自动刊登 / 任务列表",
        title: "刊登任务",
        desc: "以任务工作台承接筛选、处理、审核流转和异常回看。",
      },
      {
        id: "listing-new",
        label: "新建任务",
        crumb: "自动刊登 / 新建任务",
        title: "新建刊登任务",
        desc: "按标准素材包录入基础信息，完成 AI 生成前的准备动作。",
      },
      {
        id: "listing-review",
        label: "AI审核页",
        crumb: "自动刊登 / AI审核页",
        title: "AI结果与审核",
        desc: "把图片判断、文本修订和双人审核合并在同一工作面内完成。",
      },
    ],
  },
  {
    group: "配置",
    items: [
      {
        id: "cfg-line",
        label: "业务线权限",
        crumb: "配置 / 业务线权限",
        title: "业务线权限",
        desc: "JP / BD / AT / WD / PROM",
      },
      {
        id: "cfg-mapping",
        label: "数据映射",
        crumb: "配置 / 数据映射",
        title: "数据映射",
        desc: "属性字典映射 + 类目映射：统一竞品/雷达原始值到盘古标准值与选款品类下拉。",
      },
      {
        id: "cfg-weight",
        label: "打分权重",
        crumb: "配置 / 打分权重",
        title: "打分权重",
        desc: "Trend / Internal / Gap / Risk",
      },
      {
        id: "cfg-users",
        label: "用户管理",
        crumb: "配置 / 用户管理",
        title: "用户管理",
        desc: "账号 / 角色与业务线权限",
      },
    ],
  },
];

const DEFAULT_ROUTE = "insight-pool";

const TOAST_MESSAGES = {
  "download-report": { text: "周报下载任务已创建", type: "success" },
  "export-ppt": { text: "PPT 导出已开始", type: "success" },
  "sync-selection": { text: "已同步选款草稿", type: "success" },
  "create-listing": { text: "已保存并发起 AI 生成", type: "success" },
  "export-csv": { text: "CSV 导出已就绪", type: "info" },
  refresh: { text: "数据已刷新", type: "info" },
  "gen-draft": { text: "已生成选品方案", type: "success" },
  "submit-scheme": { text: "选品方案已提交 · 可在提案列表跟进", type: "success" },
  "voc-pool": { text: "已加入机会池", type: "success" },
  "voc-risk": { text: "已加入避雷榜", type: "success" },
  "voc-product": { text: "已生成商品优化建议", type: "success" },
  "voc-rd": { text: "已生成研发待办", type: "success" },
  "voc-sop": { text: "已生成客服 SOP 优化建议", type: "success" },
  "create-proposal": { text: "提案已提交 · 进入提案列表", type: "success" },
  "price-apply": { text: "已应用定价建议", type: "success" },
  "user-add": { text: "已打开新增用户（演示）", type: "info" },
  "user-edit": { text: "已保存用户信息（演示）", type: "success" },
  "user-toggle": { text: "用户状态已更新", type: "success" },
  "review-pass": { text: "审核已通过", type: "success" },
  "review-reject": { text: "已驳回并通知提交人", type: "info" },
  "int-adopt": { text: "建议状态已更新为已采纳", type: "success" },
  "int-reject": { text: "建议状态已更新为已拒绝", type: "info" },
  "int-gen-rec": { text: "已生成建议并加入建议清单", type: "success" },
  "int-draft": { text: "已生成方案草案", type: "success" },
  "cp-save": { text: "提案已保存为草稿", type: "success" },
  "cp-submit": { text: "提案已提交，等待品类负责人审核", type: "success" },
  "cp-upload": { text: "图片上传组件（演示）", type: "info" },
  "cfg-save": { text: "配置已保存", type: "success" },
};

/** action → bubble color class */
const ACTION_STYLE = {
  主力候选: { tag: "purple", bubble: "main" },
  跟款机会: { tag: "blue", bubble: "follow" },
  小测验证: { tag: "orange", bubble: "test" },
  保守维护: { tag: "green", bubble: "hold" },
  回避风险: { tag: "red", bubble: "avoid" },
};

const STATUS_STYLE = {
  Insight_Ready: "blue",
  Case_Ready: "purple",
  Drafted: "green",
  In_Review: "orange",
  Blocked: "red",
  Watching: "muted",
};

/**
 * Scores 0-100.
 * X = Internal Fit (left→right), Y = Market Trend (bottom→top, so CSS top = 100 - y)
 */
const OPPORTUNITIES = [
  {
    id: "SC-2026W27-BD-0042",
    theme: "Dusty Sage · A-Line · Square Neck",
    bubbleLabel: "Dusty Sage · A-Line",
    line: "BD",
    category: "Bridesmaid Dresses",
    color: "Dusty Sage",
    silhouette: "A-Line",
    neckline: "Square Neck",
    fabric: "Stretch Chiffon",
    sources: ["竞品", "内部", "舆情"],
    trend: 88,
    internal: 82,
    gap: 76,
    risk: 18,
    action: "主力候选",
    status: "Case_Ready",
    riskLevel: "低",
    insight:
      "竞品 Birdy Grey 上新且排名升；内部 Color=Dusty Sage 适配度 82、重点机会；舆情无集中图货/质量雷 → 双高，建议主力推进。",
  },
  {
    id: "SC-2026W27-BD-0043",
    theme: "Burgundy · Mermaid · Sweetheart",
    bubbleLabel: "Burgundy · Mermaid",
    line: "BD",
    category: "Bridesmaid Dresses",
    color: "Burgundy",
    silhouette: "Mermaid",
    neckline: "Sweetheart",
    fabric: "Stretch Satin",
    sources: ["竞品", "舆情"],
    trend: 91,
    internal: 54,
    gap: 72,
    risk: 42,
    action: "跟款机会",
    status: "Insight_Ready",
    riskLevel: "中",
    insight: "外部热、内部适配不足；Gap 高但存在 Size 风险备注，建议跟款机会并小批量验证。",
  },
  {
    id: "SC-2026W27-BD-0044",
    theme: "Emerald · Ball-Gown",
    bubbleLabel: "Emerald · Ball-Gown",
    line: "BD",
    category: "Bridesmaid Dresses",
    color: "Emerald",
    silhouette: "Ball-Gown",
    neckline: "Strapless",
    fabric: "Tulle",
    sources: ["竞品"],
    trend: 84,
    internal: 48,
    gap: 81,
    risk: 35,
    action: "跟款机会",
    status: "Insight_Ready",
    riskLevel: "中",
    insight: "AZ 同廓形覆盖不足，竞品站在推 Emerald Ball-Gown → Gap 高，归类跟款机会。",
  },
  {
    id: "SC-2026W27-BD-0045",
    theme: "Dusty Blue · Straight Neck",
    bubbleLabel: "—",
    line: "BD",
    category: "Bridesmaid Dresses",
    color: "Dusty Blue",
    silhouette: "A-Line",
    neckline: "Straight",
    fabric: "Stretch Satin",
    sources: ["内部"],
    trend: 42,
    internal: 86,
    gap: 40,
    risk: 12,
    action: "保守维护",
    status: "Watching",
    riskLevel: "低",
    insight: "内部成熟优势、外部偏冷 → 保守维护，不强跟外部热度。",
  },
  {
    id: "SC-2026W27-BD-0046",
    theme: "Mulberry · A-Line",
    bubbleLabel: "—",
    line: "BD",
    category: "Bridesmaid Dresses",
    color: "Mulberry",
    silhouette: "A-Line",
    neckline: "V-neck",
    fabric: "Chiffon",
    sources: ["内部"],
    trend: 38,
    internal: 80,
    gap: 35,
    risk: 15,
    action: "保守维护",
    status: "Watching",
    riskLevel: "低",
    insight: "内部验证强、竞品少跟，维持现有覆盖即可。",
  },
  {
    id: "SC-2026W27-BD-0047",
    theme: "White · Bridesmaid",
    bubbleLabel: "White · Bridesmaid",
    line: "BD",
    category: "Bridesmaid Dresses",
    color: "White",
    silhouette: "Sheath",
    neckline: "Scoop",
    fabric: "Matte Satin",
    sources: ["竞品", "舆情"],
    trend: 70,
    internal: 32,
    gap: 44,
    risk: 78,
    action: "回避风险",
    status: "Blocked",
    riskLevel: "高",
    insight: "高退货 / 高差评（图货不一致 + Size）密集，即使有外部热度也建议回避。",
  },
  {
    id: "SC-2026W27-AT-0031",
    theme: "Champagne · Satin · Slit Gown",
    bubbleLabel: "Champagne · Satin",
    line: "AT",
    category: "Atelier",
    color: "Champagne",
    silhouette: "Sheath",
    neckline: "One Shoulder",
    fabric: "Satin",
    sources: ["竞品", "社媒舆情"],
    trend: 86,
    internal: 46,
    gap: 68,
    risk: 40,
    action: "小测验证",
    status: "Insight_Ready",
    riskLevel: "中",
    insight: "外热内弱场景；建议小测验证后再扩量。",
  },
  {
    id: "SC-2026W27-MOB-0026",
    theme: "Navy · Column · 3/4 Sleeve",
    bubbleLabel: "Navy · Column",
    line: "MOB",
    category: "Mother of the Bride",
    color: "Navy",
    silhouette: "Column",
    neckline: "Boatneck",
    fabric: "Crepe",
    sources: ["内部", "竞品"],
    trend: 45,
    internal: 74,
    gap: 38,
    risk: 22,
    action: "保守维护",
    status: "Watching",
    riskLevel: "低",
    insight: "内部表现稳定，外部趋势一般，按保守维护跟进。",
  },
];

/** Extra bubbles shown on quadrant that map to related cases */
const QUAD_BUBBLES = [
  { label: "Dusty Sage · A-Line", caseId: "SC-2026W27-BD-0042", trend: 88, internal: 82, gap: 76, action: "主力候选" },
  { label: "Burgundy · Mermaid", caseId: "SC-2026W27-BD-0043", trend: 91, internal: 54, gap: 72, action: "跟款机会" },
  { label: "Emerald · Ball-Gown", caseId: "SC-2026W27-BD-0044", trend: 84, internal: 48, gap: 81, action: "跟款机会" },
  { label: "White · Bridesmaid", caseId: "SC-2026W27-BD-0047", trend: 70, internal: 32, gap: 44, action: "回避风险" },
  { label: "Terracotta · One Shoulder", caseId: "SC-2026W27-AT-0031", trend: 78, internal: 40, gap: 65, action: "小测验证" },
  { label: "Navy · Column", caseId: "SC-2026W27-MOB-0026", trend: 45, internal: 74, gap: 38, action: "保守维护" },
  { label: "Champagne · Satin", caseId: "SC-2026W27-AT-0031", trend: 86, internal: 46, gap: 68, action: "小测验证" },
];

const PIPELINE = [
  { name: "信号包", count: 42 },
  { name: "洞察就绪", count: 24 },
  { name: "选品方案", count: 18 },
  { name: "选款提案", count: 7 },
  { name: "刊登任务", count: 3 },
];

/** 来源信号固定三格，保证列对齐 */
const SIGNAL_SLOTS = [
  { key: "竞品", aliases: ["竞品"] },
  { key: "内部", aliases: ["内部", "产品数据"] },
  { key: "舆情", aliases: ["舆情", "社媒舆情"] },
];

const pageMetaById = (() => {
  const map = {};
  NAV_TREE.forEach((g) => g.items.forEach((item) => (map[item.id] = item)));
  return map;
})();

let currentRoute = DEFAULT_ROUTE;
let selectedId = null;
let detailCaseId = null;
let schemeCaseId = null;
let poolFilters = {
  line: "全部",
  category: "全部",
  color: "全部",
  silhouette: "全部",
  neckline: "全部",
  fabric: "全部",
  source: "全部",
  action: "全部",
  riskLevel: "全部",
};

function $(sel) {
  return document.querySelector(sel);
}

function showToast(message, type = "info") {
  const host = $("#toast-host");
  if (!host) return;
  const el = document.createElement("div");
  el.className = `toast toast--${type}`;
  el.textContent = message;
  host.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity 0.2s ease";
    setTimeout(() => el.remove(), 200);
  }, 2600);
}

function handleToastAction(key, caseId) {
  const msg = TOAST_MESSAGES[key];
  if (!msg) return;
  const suffix = caseId ? ` · ${caseId}` : "";
  showToast(msg.text + suffix, msg.type);
}

function renderTag(text, tone) {
  return `<span class="tag tag--${tone || "muted"}">${text}</span>`;
}

function normalizeSources(sources) {
  const set = new Set(sources || []);
  return SIGNAL_SLOTS.map((slot) => {
    const on = slot.aliases.some((a) => set.has(a));
    return { key: slot.key, on };
  });
}

function renderSignalTags(sources) {
  return `
    <div class="signal-stack" role="list">
      ${normalizeSources(sources)
        .map(
          (s) =>
            `<span class="tag tag--signal${s.on ? " is-on" : ""}" role="listitem" title="${s.key}${s.on ? "（已命中）" : "（未命中）"}">${s.key}</span>`
        )
        .join("")}
    </div>
  `;
}

function renderKpiCard({ id, label, value, sub }) {
  return `
    <article class="kpi-card" data-inspect="${id}" data-inspect-kind="kpi">
      <span class="kpi-card__label">${label}</span>
      <strong class="kpi-card__value">${value}</strong>
      <div class="kpi-card__sub"><span>${sub}</span></div>
    </article>
  `;
}

function uniqueOptions(key) {
  const set = new Set(OPPORTUNITIES.map((o) => o[key]).filter(Boolean));
  return ["全部", ...set];
}

function renderSelect(name, label, options, current) {
  return `
    <div class="field">
      <label>${label}</label>
      <select data-pool-filter="${name}">
        ${options
          .map((opt) => `<option${opt === current ? " selected" : ""}>${opt}</option>`)
          .join("")}
      </select>
    </div>
  `;
}

function renderPoolFilters() {
  const sourceOpts = ["全部", "竞品", "内部", "舆情", "社媒舆情"];
  return `
    <section class="filter-card">
      <div class="filter-grid filter-grid--9">
        ${renderSelect("line", "业务线", uniqueOptions("line"), poolFilters.line)}
        ${renderSelect("category", "品类", uniqueOptions("category"), poolFilters.category)}
        ${renderSelect("color", "颜色", uniqueOptions("color"), poolFilters.color)}
        ${renderSelect("silhouette", "廓形", uniqueOptions("silhouette"), poolFilters.silhouette)}
        ${renderSelect("neckline", "领型", uniqueOptions("neckline"), poolFilters.neckline)}
        ${renderSelect("fabric", "面料", uniqueOptions("fabric"), poolFilters.fabric)}
        ${renderSelect("source", "来源", sourceOpts, poolFilters.source)}
        ${renderSelect("action", "建议动作", ["全部", ...Object.keys(ACTION_STYLE)], poolFilters.action)}
        ${renderSelect("riskLevel", "风险等级", ["全部", "低", "中", "高"], poolFilters.riskLevel)}
      </div>
      <div class="filter-actions filter-actions--bar">
        <button type="button" class="btn btn-secondary" data-pool-reset>重置筛选</button>
        <button type="button" class="btn btn-secondary" data-toast="refresh">刷新</button>
        <button type="button" class="btn btn-secondary" data-toast="export-csv">导出 CSV</button>
      </div>
    </section>
  `;
}

function filteredOpportunities() {
  return OPPORTUNITIES.filter((o) => {
    if (poolFilters.line !== "全部" && o.line !== poolFilters.line) return false;
    if (poolFilters.category !== "全部" && o.category !== poolFilters.category) return false;
    if (poolFilters.color !== "全部" && o.color !== poolFilters.color) return false;
    if (poolFilters.silhouette !== "全部" && o.silhouette !== poolFilters.silhouette) return false;
    if (poolFilters.neckline !== "全部" && o.neckline !== poolFilters.neckline) return false;
    if (poolFilters.fabric !== "全部" && o.fabric !== poolFilters.fabric) return false;
    if (poolFilters.action !== "全部" && o.action !== poolFilters.action) return false;
    if (poolFilters.riskLevel !== "全部" && o.riskLevel !== poolFilters.riskLevel) return false;
    if (poolFilters.source !== "全部" && !(o.sources || []).includes(poolFilters.source)) return false;
    return true;
  });
}

function scoreToPos(internal, trend) {
  const pad = 8;
  const left = pad + (internal / 100) * (100 - pad * 2);
  const top = pad + ((100 - trend) / 100) * (100 - pad * 2);
  return { left, top };
}

function gapToSize(gap) {
  return 36 + (gap / 100) * 42;
}

function renderQuadrant() {
  const bubbles = QUAD_BUBBLES.map((b) => {
    const { left, top } = scoreToPos(b.internal, b.trend);
    const size = gapToSize(b.gap);
    const style = ACTION_STYLE[b.action] || ACTION_STYLE["保守维护"];
    return `
      <button
        type="button"
        class="bubble bubble--${style.bubble}${selectedId === b.caseId ? " is-selected" : ""}"
        style="left:${left}%;top:${top}%;width:${size}px;height:${size}px;"
        data-inspect="${b.caseId}"
        title="${b.label} · 缺口分 ${b.gap}"
      >
        <span>${b.label}</span>
      </button>
    `;
  }).join("");

  return `
    <section class="quad-panel">
      <h3>机会四象限</h3>
      <p class="quad-meta">横轴 内部适配度 · 纵轴 市场趋势 · 气泡大小 = 缺口分 · 颜色 = 建议动作</p>
      <div class="quad-legend">
        <span><i style="background:#7048e8"></i>主力候选</span>
        <span><i style="background:#339af0"></i>跟款机会</span>
        <span><i style="background:#ff922b"></i>小测验证</span>
        <span><i style="background:#0ca678"></i>保守维护</span>
        <span><i style="background:#fa5252"></i>回避风险</span>
      </div>
      <div class="quad-board">
        <span class="quad-label quad-label--tr">双高机会</span>
        <span class="quad-label quad-label--tl">外热内弱</span>
        <span class="quad-label quad-label--br">内部优势</span>
        <span class="quad-label quad-label--bl">低优先级</span>
        <span class="axis-x">内部适配度 →</span>
        <span class="axis-y">市场趋势 →</span>
        ${bubbles}
      </div>
    </section>
  `;
}

function renderFunnel() {
  const max = PIPELINE[0].count;
  return `
    <section class="funnel-panel">
      <h3>流转漏斗</h3>
      <p class="quad-meta">从信号包到刊登任务的流转规模</p>
      <div class="funnel-list">
        ${PIPELINE.map(
          (step) => `
          <div class="funnel-step">
            <span>${step.name}</span>
            <strong>${step.count}</strong>
            <div class="funnel-bar"><i style="width:${(step.count / max) * 100}%"></i></div>
          </div>
        `
        ).join("")}
      </div>
    </section>
  `;
}

function renderPoolTable(rows) {
  const body = rows
    .map((o) => {
      const aStyle = ACTION_STYLE[o.action] || { tag: "muted" };
      const sTone = STATUS_STYLE[o.status] || "muted";
      return `
      <tr data-inspect="${o.id}" class="${selectedId === o.id ? "is-selected" : ""}">
        <td><span class="cell-title">${o.id}</span></td>
        <td>
          <span class="cell-title">${o.theme}</span>
          <span class="cell-sub">${o.color} · ${o.silhouette}</span>
        </td>
        <td>${o.line}</td>
        <td>${o.category}</td>
        <td>${renderSignalTags(o.sources)}</td>
        <td class="score-num">${o.trend}</td>
        <td class="score-num">${o.internal}</td>
        <td class="score-num">${o.gap}</td>
        <td class="score-num">${o.risk}</td>
        <td>${renderTag(o.action, aStyle.tag)}</td>
        <td>${renderTag(o.status, sTone)}</td>
        <td>
          <div class="row-actions">
            <button type="button" class="btn-text" data-open-detail="${o.id}">查看洞察</button>
            <button type="button" class="btn-text" data-open-scheme="${o.id}">生成选品方案</button>
          </div>
        </td>
      </tr>
    `;
    })
    .join("");

  return `
    <section class="table-card">
      <div class="table-toolbar">
        <div>
          <h3>选品方案列表</h3>
          <p>共 ${rows.length} 条 · 点击行打开详情侧栏 · 「查看洞察」进入详情子页</p>
        </div>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>选品方案 ID</th>
              <th>机会主题</th>
              <th>业务线</th>
              <th>品类</th>
              <th>来源信号</th>
              <th>市场趋势</th>
              <th>内部适配度</th>
              <th>缺口分</th>
              <th>风险分</th>
              <th>系统建议动作</th>
              <th>当前状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>${body || `<tr><td colspan="12" class="muted">无匹配结果</td></tr>`}</tbody>
        </table>
      </div>
    </section>
  `;
}

function getCase(id) {
  return OPPORTUNITIES.find((o) => o.id === id);
}

function openInspector(id) {
  const data = getCase(id);
  if (!data) return;

  selectedId = id;
  const shell = $("#content-shell");
  const inspector = $("#inspector");
  const body = $("#inspector-body");
  const sub = $("#inspector-sub");

  shell.classList.add("inspector-open");
  inspector.classList.remove("is-collapsed");
  if (sub) sub.textContent = data.theme;

  const aStyle = ACTION_STYLE[data.action] || { tag: "muted" };
  const sTone = STATUS_STYLE[data.status] || "muted";

  body.innerHTML = `
    <div class="inspector-block">
      <h4>对象编号</h4>
      <div class="inspector-id">${data.id}</div>
    </div>
    <div class="inspector-block">
      <h4>当前状态</h4>
      ${renderTag(data.status, sTone)}
    </div>
    <div class="inspector-block">
      <h4>建议动作</h4>
      ${renderTag(data.action, aStyle.tag)}
    </div>
    <div class="inspector-block">
      <h4>关键字段</h4>
      <div class="kv-list">
        <div class="kv-row"><span>机会主题</span><strong>${data.theme}</strong></div>
        <div class="kv-row"><span>业务线</span><strong>${data.line}</strong></div>
        <div class="kv-row"><span>品类</span><strong>${data.category}</strong></div>
        <div class="kv-row"><span>来源</span><strong>${data.sources.join(" / ")}</strong></div>
        <div class="kv-row"><span>市场趋势</span><strong>${data.trend}</strong></div>
        <div class="kv-row"><span>内部适配度</span><strong>${data.internal}</strong></div>
        <div class="kv-row"><span>缺口分</span><strong>${data.gap}</strong></div>
        <div class="kv-row"><span>风险分</span><strong>${data.risk}（${data.riskLevel}）</strong></div>
      </div>
    </div>
    <div class="inspector-block">
      <h4>操作日志</h4>
      <div class="timeline">
        <div class="timeline-item"><time>2026-W27</time><div>竞品网站 / 产品数据 / 社媒舆情三信号融合生成选品方案</div></div>
        <div class="timeline-item"><time>刚刚</time><div>运营在机会池打开 Inspector</div></div>
      </div>
    </div>
    <div class="filter-actions">
      <button type="button" class="btn btn-secondary" data-open-detail="${data.id}">查看洞察</button>
      <button type="button" class="btn btn-primary" data-open-scheme="${data.id}">生成选品方案</button>
    </div>
  `;

  document.querySelectorAll("#page-content .is-selected").forEach((el) => el.classList.remove("is-selected"));
  document.querySelectorAll(`[data-inspect="${CSS.escape(id)}"]`).forEach((el) => el.classList.add("is-selected"));
}

function closeInspector() {
  selectedId = null;
  $("#content-shell")?.classList.remove("inspector-open");
  $("#inspector")?.classList.add("is-collapsed");
  const body = $("#inspector-body");
  const sub = $("#inspector-sub");
  if (sub) sub.textContent = "点击表格行或卡片展开";
  if (body) {
    body.innerHTML = `
      <div class="empty-panel">
        <strong>暂无选中对象</strong>
        <p>在机会池等页面选中一行后，将在此展示编号、状态、建议动作、字段与操作日志。</p>
      </div>
    `;
  }
  document.querySelectorAll(".is-selected").forEach((el) => el.classList.remove("is-selected"));
}

function renderCaseDetail(id) {
  const data = getCase(id);
  if (!data) {
    return `<section class="card card-pad"><p>未找到 ${id}</p></section>`;
  }
  const aStyle = ACTION_STYLE[data.action] || { tag: "muted" };
  const sTone = STATUS_STYLE[data.status] || "muted";

  return `
    <div class="detail-page">
      <div>
        <button type="button" class="btn btn-secondary detail-back" data-back-pool>← 返回机会池</button>
      </div>
      <section class="card card-pad">
        <div class="detail-hero">
          <div>
            <p class="muted">${data.id}</p>
            <h2 style="margin:6px 0 10px;font-size:22px;">${data.theme}</h2>
            <div>
              ${renderTag(data.action, aStyle.tag)}
              ${renderTag(data.status, sTone)}
              ${renderTag(`风险 ${data.riskLevel}`, data.riskLevel === "高" ? "red" : data.riskLevel === "中" ? "orange" : "green")}
            </div>
            <p style="margin:14px 0 0;color:var(--text-soft);line-height:1.65;max-width:720px;">${data.insight}</p>
          </div>
          <div class="filter-actions" style="flex-direction:column;align-items:stretch;">
            <button type="button" class="btn btn-primary" data-open-scheme="${data.id}">生成选品方案</button>
          </div>
        </div>
      </section>
      <section class="detail-grid">
        <div class="detail-metric"><span>市场趋势</span><strong>${data.trend}</strong></div>
        <div class="detail-metric"><span>内部适配度</span><strong>${data.internal}</strong></div>
        <div class="detail-metric"><span>缺口分</span><strong>${data.gap}</strong></div>
        <div class="detail-metric"><span>风险分</span><strong>${data.risk}</strong></div>
        <div class="detail-metric"><span>业务线 / 品类</span><strong style="font-size:15px;">${data.line} · ${data.category}</strong></div>
        <div class="detail-metric"><span>来源信号</span><strong style="font-size:15px;">${data.sources.join(" / ")}</strong></div>
      </section>
      <section class="card card-pad">
        <div class="card-head">
          <div>
            <h3>信号拆解</h3>
            <p>竞品网站动态 · 内部数据动态 · 社媒舆情动态（选品侧切片）</p>
          </div>
        </div>
        <div class="kv-list">
          <div class="kv-row"><span>颜色</span><strong>${data.color}</strong></div>
          <div class="kv-row"><span>廓形</span><strong>${data.silhouette}</strong></div>
          <div class="kv-row"><span>领型</span><strong>${data.neckline}</strong></div>
          <div class="kv-row"><span>面料</span><strong>${data.fabric}</strong></div>
        </div>
      </section>
    </div>
  `;
}

function renderSchemePage(id) {
  const data = getCase(id);
  if (!data) {
    return `<section class="card card-pad"><p>未找到 ${id}</p></section>`;
  }
  const aStyle = ACTION_STYLE[data.action] || { tag: "muted" };

  return `
    <div class="detail-page">
      <div>
        <button type="button" class="btn btn-secondary detail-back" data-back-pool>← 返回机会池</button>
      </div>
      <section class="card card-pad">
        <div class="card-head">
          <div>
            <h3>生成选品方案</h3>
            <p>基于机会洞察预填方案内容，确认后提交进入选款提案流转</p>
          </div>
          ${renderTag(data.action, aStyle.tag)}
        </div>
        <div class="kv-list" style="margin-top:14px;">
          <div class="kv-row"><span>关联机会</span><strong>${data.id}</strong></div>
          <div class="kv-row"><span>机会主题</span><strong>${data.theme}</strong></div>
          <div class="kv-row"><span>业务线 / 品类</span><strong>${data.line} · ${data.category}</strong></div>
          <div class="kv-row"><span>来源信号</span><strong>${data.sources.join(" / ")}</strong></div>
          <div class="kv-row"><span>建议动作</span><strong>${data.action}</strong></div>
        </div>
        <div class="scheme-note">
          <label for="scheme-note">方案备注</label>
          <textarea id="scheme-note" rows="3" placeholder="补充选品理由、风险备注、建议打样数量等">${data.insight}</textarea>
        </div>
        <div class="filter-actions" style="margin-top:16px;">
          <button type="button" class="btn btn-secondary" data-back-pool>取消</button>
          <button type="button" class="btn btn-primary" data-toast="submit-scheme" data-case="${data.id}">提交</button>
        </div>
      </section>
    </div>
  `;
}

function renderOpportunityPool() {
  if (schemeCaseId) {
    return renderSchemePage(schemeCaseId);
  }
  if (detailCaseId) {
    return renderCaseDetail(detailCaseId);
  }

  const rows = filteredOpportunities();
  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "KPI-WEEK", label: "本周机会数", value: "18", sub: "竞品网站 / 产品数据 / 社媒舆情融合生成" })}
        ${renderKpiCard({ id: "KPI-MAIN", label: "主力候选", value: "6", sub: "双高机会" })}
        ${renderKpiCard({ id: "KPI-TEST", label: "小测验证", value: "7", sub: "外热内弱 / 需验证" })}
        ${renderKpiCard({ id: "KPI-AVOID", label: "回避风险", value: "5", sub: "高退货 / 高差评风险" })}
      </section>
      ${renderPoolFilters()}
      <section class="pool-mid">
        ${renderQuadrant()}
        ${renderFunnel()}
      </section>
      ${renderPoolTable(rows)}
    </div>
  `;
}

function renderPlaceholder(meta) {
  return `
    <div class="page-stack">
      <section class="card card-pad">
        <div class="card-head">
          <div>
            <h3>${meta.title}</h3>
            <p>${meta.desc}</p>
          </div>
          ${renderTag("骨架占位", "muted")}
        </div>
        <p class="muted">业务详情尚未接入。请先到「分析洞察 > 机会池」查看完整交互。</p>
      </section>
    </div>
  `;
}

function renderNav() {
  const nav = $("#side-nav");
  nav.innerHTML = NAV_TREE.map(
    (group) => `
    <div class="nav-group">
      <p class="nav-group__label">${group.group}</p>
      ${group.items
        .map(
          (item) => `
        <button
          type="button"
          class="nav-item${item.id === currentRoute && !detailCaseId && !schemeCaseId ? " is-active" : ""}"
          data-route="${item.id}"
        >
          <span class="nav-item__dot" aria-hidden="true"></span>
          <span>${item.label}</span>
        </button>
      `
        )
        .join("")}
    </div>
  `
  ).join("");
}

function updateHeaderForPool() {
  if (schemeCaseId) {
    const c = getCase(schemeCaseId);
    $("#page-crumb").textContent = "分析洞察 / 机会池 / 生成选品方案";
    $("#page-title").textContent = "生成选品方案";
    $("#page-desc").textContent = c ? `${c.id} · ${c.theme}` : "";
    return;
  }
  if (detailCaseId) {
    const c = getCase(detailCaseId);
    $("#page-crumb").textContent = `分析洞察 / 机会池 / 洞察详情`;
    $("#page-title").textContent = c ? c.theme : "洞察详情";
    $("#page-desc").textContent = c ? c.id : "";
    return;
  }
  const meta = pageMetaById["insight-pool"];
  $("#page-crumb").textContent = meta.crumb;
  $("#page-title").textContent = meta.title;
  $("#page-desc").textContent = meta.desc;
}

function paintContent() {
  const meta = pageMetaById[currentRoute];
  if (!meta) return;

  if (currentRoute === "insight-pool") {
    restoreDefaultHeaderActions();
    updateHeaderForPool();
    $("#page-content").innerHTML = renderOpportunityPool();
  } else if (currentRoute === "monitor-sentiment") {
    detailCaseId = null;
    schemeCaseId = null;
    closeInspector();
    updateSentimentHeader();
    $("#page-content").innerHTML = renderSentimentPage();
  } else if (currentRoute === "monitor-internal") {
    detailCaseId = null;
    schemeCaseId = null;
    closeInspector();
    updateInternalHeader();
    $("#page-content").innerHTML = renderInternalPage();
  } else {
    detailCaseId = null;
    schemeCaseId = null;
    restoreDefaultHeaderActions();
    $("#page-crumb").textContent = meta.crumb;
    $("#page-title").textContent = meta.title;
    $("#page-desc").textContent = meta.desc;
    const extra = typeof renderExtraPage === "function" ? renderExtraPage(currentRoute) : null;
    $("#page-content").innerHTML = extra || renderPlaceholder(meta);
  }

  document.querySelectorAll(".nav-item").forEach((btn) => {
    const onPoolSub = currentRoute === "insight-pool" && (detailCaseId || schemeCaseId);
    const active =
      btn.dataset.route === "insight-pool"
        ? currentRoute === "insight-pool"
        : btn.dataset.route === currentRoute && !onPoolSub;
    btn.classList.toggle("is-active", active);
  });
}

function navigate(routeId) {
  const meta = pageMetaById[routeId];
  if (!meta) return;
  currentRoute = routeId;
  detailCaseId = null;
  schemeCaseId = null;
  if (routeId === "proposal-create") {
    if (!window.__keepCreatePrefill && typeof setCreateProposalPrefill === "function") {
      setCreateProposalPrefill(null);
      if (typeof createProposalUi !== "undefined") {
        createProposalUi.showErrors = false;
        createProposalUi.source = "Trend";
        createProposalUi.hasFabric = "是";
        createProposalUi.reuse = "是";
        createProposalUi.frontUploaded = false;
      }
    }
    window.__keepCreatePrefill = false;
  }
  window.location.hash = routeId;
  closeInspector();
  if (routeId !== "monitor-sentiment" && routeId !== "monitor-internal") {
    restoreDefaultHeaderActions();
  }
  paintContent();
}

function openDetail(caseId) {
  if (!getCase(caseId)) return;
  detailCaseId = caseId;
  schemeCaseId = null;
  currentRoute = "insight-pool";
  window.location.hash = `insight-pool/detail/${caseId}`;
  closeInspector();
  paintContent();
  showToast(`已打开洞察详情 · ${caseId}`, "info");
}

function openScheme(caseId) {
  if (!getCase(caseId)) return;
  schemeCaseId = caseId;
  detailCaseId = null;
  currentRoute = "insight-pool";
  window.location.hash = `insight-pool/scheme/${caseId}`;
  closeInspector();
  paintContent();
  showToast(`已进入生成选品方案 · ${caseId}`, "info");
}

function getInitialRoute() {
  const raw = window.location.hash.replace("#", "");
  if (raw.startsWith("insight-pool/scheme/")) {
    const id = raw.split("/")[2];
    if (getCase(id)) {
      schemeCaseId = id;
      detailCaseId = null;
      return "insight-pool";
    }
  }
  if (raw.startsWith("insight-pool/detail/")) {
    const id = raw.split("/")[2];
    if (getCase(id)) {
      detailCaseId = id;
      schemeCaseId = null;
      return "insight-pool";
    }
  }
  return pageMetaById[raw] ? raw : DEFAULT_ROUTE;
}

function bindEvents() {
  $("#side-nav").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-route]");
    if (!btn) return;
    navigate(btn.dataset.route);
  });

  document.addEventListener("change", (e) => {
    const sel = e.target.closest("[data-pool-filter]");
    if (sel) {
      poolFilters[sel.dataset.poolFilter] = sel.value;
      if (currentRoute === "insight-pool" && !detailCaseId && !schemeCaseId) {
        paintContent();
      }
      return;
    }

    const cpUi = e.target.closest("[data-cp-ui]");
    if (cpUi && currentRoute === "proposal-create" && typeof createProposalUi !== "undefined") {
      createProposalUi[cpUi.dataset.cpUi] = cpUi.value;
      if (cpUi.dataset.cpUi === "source" || cpUi.dataset.cpUi === "hasFabric" || cpUi.dataset.cpUi === "reuse") {
        paintContent();
      }
      return;
    }

    const cpField = e.target.closest("[data-cp-field]");
    if (cpField && currentRoute === "proposal-create") {
      if (!createProposalPrefill) createProposalPrefill = {};
      createProposalPrefill[cpField.dataset.cpField] = cpField.value;
    }
  });

  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-pool-reset]")) {
      Object.keys(poolFilters).forEach((k) => (poolFilters[k] = "全部"));
      paintContent();
      showToast("已重置筛选", "info");
      return;
    }

    if (e.target.closest("[data-back-pool]")) {
      detailCaseId = null;
      schemeCaseId = null;
      window.location.hash = "insight-pool";
      paintContent();
      return;
    }

    const toastBtn = e.target.closest("[data-toast]");
    if (toastBtn) {
      e.stopPropagation();
      if (toastBtn.dataset.toast === "cp-upload" && typeof createProposalUi !== "undefined") {
        createProposalUi.frontUploaded = true;
      }
      handleToastAction(toastBtn.dataset.toast, toastBtn.dataset.case);
      if (toastBtn.dataset.routeJump) {
        navigate(toastBtn.dataset.routeJump);
      }
      return;
    }

    if (e.target.closest("[data-cp-save]") && currentRoute === "proposal-create") {
      createProposalUi.showErrors = false;
      handleToastAction("cp-save");
      return;
    }

    if (e.target.closest("[data-cp-submit]") && currentRoute === "proposal-create") {
      const line = document.querySelector('select[data-cp-field="line"]')?.value || "";
      const category = document.querySelector('select[data-cp-field="category"]')?.value || "";
      const price = (document.querySelector('input[data-cp-field="price"]')?.value || "").trim();
      const evidence = (document.querySelector('textarea[data-cp-field="evidence"]')?.value || "").trim();
      const hasFront = !!createProposalUi.frontUploaded || !!createProposalPrefill?.caseId || !!createProposalPrefill?.recId;
      if (!line || !category || !price || !evidence || !hasFront) {
        createProposalUi.showErrors = true;
        if (!createProposalPrefill) createProposalPrefill = {};
        createProposalPrefill.line = line;
        createProposalPrefill.category = category;
        createProposalPrefill.price = price;
        createProposalPrefill.evidence = evidence;
        paintContent();
        showToast("请先填写业务线、品类、正面图、提案佐证和目标价格", "info");
        return;
      }
      createProposalUi.showErrors = false;
      handleToastAction("cp-submit");
      return;
    }

    if (e.target.closest("[data-cp-remove-person]") && currentRoute === "proposal-create") {
      createProposalUi.proposer = "admin";
      if (createProposalPrefill) createProposalPrefill.proposer = "admin";
      showToast("已重置提案人", "info");
      paintContent();
      return;
    }

    const vocTabBtn = e.target.closest("[data-voc-tab]");
    if (vocTabBtn && currentRoute === "monitor-sentiment") {
      vocState.tab = vocTabBtn.dataset.vocTab;
      paintContent();
      return;
    }

    const vocGrainBtn = e.target.closest("[data-voc-grain]");
    if (vocGrainBtn && currentRoute === "monitor-sentiment") {
      vocState.grain = vocGrainBtn.dataset.vocGrain;
      paintContent();
      return;
    }

    const vocExpandBtn = e.target.closest("[data-voc-expand]");
    if (vocExpandBtn && currentRoute === "monitor-sentiment") {
      const id = vocExpandBtn.dataset.vocExpand;
      const currently =
        vocState.expanded[id] !== undefined
          ? !!vocState.expanded[id]
          : ["cs-size", "rd-order"].includes(id);
      vocState.expanded[id] = !currently;
      paintContent();
      return;
    }

    const intTabBtn = e.target.closest("[data-int-tab]");
    if (intTabBtn && currentRoute === "monitor-internal") {
      intState.tab = intTabBtn.dataset.intTab;
      intState.drawerAttrId = null;
      paintContent();
      return;
    }

    const intDimBtn = e.target.closest("[data-int-dim]");
    if (intDimBtn && currentRoute === "monitor-internal") {
      intState.attrDim = intDimBtn.dataset.intDim;
      paintContent();
      return;
    }

    const intDrawerBtn = e.target.closest("[data-int-drawer]");
    if (intDrawerBtn && currentRoute === "monitor-internal") {
      e.stopPropagation();
      intState.drawerAttrId = intDrawerBtn.dataset.intDrawer;
      paintContent();
      return;
    }

    if (e.target.closest("[data-int-close-drawer]") && currentRoute === "monitor-internal") {
      intState.drawerAttrId = null;
      paintContent();
      return;
    }

    const intTraceBtn = e.target.closest("[data-int-trace]");
    if (intTraceBtn && currentRoute === "monitor-internal") {
      e.stopPropagation();
      intState.selectedRecId = intTraceBtn.dataset.intTrace;
      intState.tab = "trace";
      paintContent();
      return;
    }

    const intSelectRec = e.target.closest("[data-int-select-rec]");
    if (intSelectRec && currentRoute === "monitor-internal") {
      intState.selectedRecId = intSelectRec.dataset.intSelectRec;
      paintContent();
      return;
    }

    const intMetricBtn = e.target.closest("[data-int-metric]");
    if (intMetricBtn && currentRoute === "monitor-internal") {
      intState.trendMetric = intMetricBtn.dataset.intMetric;
      paintContent();
      return;
    }

    const pageUiBtn = e.target.closest("[data-page-ui]");
    if (pageUiBtn && typeof PAGE_UI !== "undefined") {
      PAGE_UI[pageUiBtn.dataset.pageUi] = pageUiBtn.dataset.pageVal;
      paintContent();
      return;
    }

    const listingUiBtn = e.target.closest("[data-listing-ui]");
    if (listingUiBtn && typeof listingUi !== "undefined") {
      listingUi[listingUiBtn.dataset.listingUi] = listingUiBtn.dataset.listingVal;
      paintContent();
      return;
    }

    const jumpBtn = e.target.closest("[data-route-jump]");
    if (jumpBtn) {
      e.stopPropagation();
      navigate(jumpBtn.dataset.routeJump);
      return;
    }

    const schemeBtn = e.target.closest("[data-open-scheme]");
    if (schemeBtn) {
      e.stopPropagation();
      openScheme(schemeBtn.dataset.openScheme);
      return;
    }

    const detailBtn = e.target.closest("[data-open-detail]");
    if (detailBtn) {
      e.stopPropagation();
      openDetail(detailBtn.dataset.openDetail);
      return;
    }

    if (e.target.closest("#inspector-close")) {
      closeInspector();
      return;
    }

    const inspectEl = e.target.closest("[data-inspect]");
    if (
      inspectEl &&
      inspectEl.closest("#page-content") &&
      currentRoute === "insight-pool" &&
      !detailCaseId &&
      !schemeCaseId
    ) {
      if (inspectEl.dataset.inspect.startsWith("KPI-")) {
        showToast("KPI 汇总卡片 · 详见下方列表", "info");
        return;
      }
      openInspector(inspectEl.dataset.inspect);
    }
  });

  window.addEventListener("hashchange", () => {
    const raw = window.location.hash.replace("#", "");
    if (raw.startsWith("insight-pool/scheme/")) {
      const id = raw.split("/")[2];
      if (getCase(id)) {
        schemeCaseId = id;
        detailCaseId = null;
        currentRoute = "insight-pool";
        paintContent();
        return;
      }
    }
    if (raw.startsWith("insight-pool/detail/")) {
      const id = raw.split("/")[2];
      if (getCase(id)) {
        detailCaseId = id;
        schemeCaseId = null;
        currentRoute = "insight-pool";
        paintContent();
        return;
      }
    }
    if (pageMetaById[raw] && (raw !== currentRoute || detailCaseId || schemeCaseId)) {
      navigate(raw);
    }
  });
}

function init() {
  renderNav();
  bindEvents();
  const route = getInitialRoute();
  currentRoute = route;
  if (schemeCaseId) {
    window.location.hash = `insight-pool/scheme/${schemeCaseId}`;
  } else if (detailCaseId) {
    window.location.hash = `insight-pool/detail/${detailCaseId}`;
  } else {
    window.location.hash = route;
  }
  paintContent();
}

/* init 由 pages.js 在渲染器注册后调用 */
