const DATA_WEEK = "2026-W27";
const CATEGORY_LINE = "BD";

const pageMeta = {
  overview: {
    title: "机会总览",
    description: "三信号汇总后的一页式洞察：本周市场在推什么、内部是否验证、有哪些避雷。",
  },
  pool: {
    title: "机会池",
    description: "按颜色/属性/站点筛选候选，查看四维分数与建议动作，可一键进入提案。",
  },
  "new-arrivals": {
    title: "竞品上新监控",
    description: "基于雷达「上新表」按周聚合：上新数、Top 站点、升温属性。",
  },
  gap: {
    title: "AZ vs 竞品 Gap",
    description: "盘古 AZ 数据与竞品雷达横向对比，识别覆盖缺口与跟款机会。",
  },
  risk: {
    title: "避雷榜",
    description: "舆情 PDL + 雷达差评，跟款前先看 Size/Quality/图货不一致 Top 槽点。",
  },
  draft: {
    title: "一键出提案",
    description: "30 秒内生成对齐选款「创建提案」的草案，含佐证与 signal_refs。",
  },
};

const opportunities = [
  {
    id: "opp-001",
    title: "Dusty Sage · A-Line · Square Neck",
    brand: "Birdy Grey",
    site: "Birdy Grey",
    skcKey: "BG-W27-8842",
    url: "https://www.birdygrey.com/products/dusty-sage-a-line",
    color: "Dusty Sage",
    silhouette: "A-Line",
    neckline: "Square Neckline",
    fabric: "Stretch Chiffon",
    price: "$119.00",
    rankChange: "+12",
    newType: "新色上新",
    trend: 88,
    internal: 82,
    gap: 76,
    risk: 18,
    composite: 84,
    quadrant: "重点机会",
    priority: "P0",
    status: "active",
    action: "主力候选",
    actionClass: "primary",
    conflict: null,
    internalNote: "内部适配度 82 · 覆盖 8 SKC · 趋势↑",
  },
  {
    id: "opp-002",
    title: "Burgundy · Mermaid · Sweetheart",
    brand: "Club L London",
    site: "Club L London",
    skcKey: "CL-W27-3310",
    url: "https://www.clublondon.com/product/burgundy-mermaid",
    color: "Burgundy",
    silhouette: "Mermaid",
    neckline: "Sweetheart",
    fabric: "Stretch Satin",
    price: "$149.00",
    rankChange: "+8",
    newType: "新款",
    trend: 91,
    internal: 54,
    gap: 72,
    risk: 42,
    composite: 68,
    quadrant: "持续观察",
    priority: "P1",
    status: "watching",
    action: "小测",
    actionClass: "warn",
    conflict: "外热内弱",
    internalNote: "内部未充分验证 · 建议小批量测色",
  },
  {
    id: "opp-003",
    title: "Black · Sheath · V-neck",
    brand: "Six Stories",
    site: "Six Stories",
    skcKey: "SS-W27-1204",
    url: "https://www.sixstories.com/black-sheath-vneck",
    color: "Black",
    silhouette: "Sheath",
    neckline: "V-neck",
    fabric: "Matte Satin",
    price: "$99.00",
    rankChange: "+5",
    newType: "补货回归",
    trend: 79,
    internal: 38,
    gap: 55,
    risk: 71,
    composite: 52,
    quadrant: "风险冗余",
    priority: "P2",
    status: "blocked",
    action: "回避",
    actionClass: "danger",
    conflict: "外热内冗余 + 高退货",
    internalNote: "内部适配度 38 · 退货率偏高",
  },
  {
    id: "opp-004",
    title: "Dusty Blue · A-Line · Straight Neck",
    brand: "Azazie 内部",
    site: "Azazie",
    skcKey: "AZ-INT-7721",
    url: "",
    color: "Dusty Blue",
    silhouette: "A-Line",
    neckline: "Straight",
    fabric: "Stretch Satin",
    price: "$109.00",
    rankChange: "—",
    newType: "内部驱动",
    trend: 42,
    internal: 86,
    gap: 81,
    risk: 12,
    composite: 78,
    quadrant: "成熟优势",
    priority: "P0",
    status: "ready",
    action: "内部扩产",
    actionClass: "internal",
    conflict: null,
    internalNote: "竞品冷 · 内部高分低覆盖 · 建议扩配色",
  },
];

const newArrivalsBySite = [
  { site: "Birdy Grey", count: 18, delta: "+6" },
  { site: "Club L London", count: 14, delta: "+3" },
  { site: "Six Stories", count: 11, delta: "+2" },
  { site: "Hello Molly", count: 9, delta: "+1" },
  { site: "Babyboo", count: 7, delta: "0" },
];

const newArrivalsByAttr = [
  { attr: "Color · Dusty Sage", count: 12, pct: 92 },
  { attr: "Silhouette · A-Line", count: 10, pct: 78 },
  { attr: "Neckline · Square", count: 8, pct: 64 },
  { attr: "Fabric · Stretch Chiffon", count: 7, pct: 56 },
  { attr: "Color · Burgundy", count: 6, pct: 48 },
];

const gapData = {
  competitorOnly: [
    { label: "Burgundy + Mermaid + Sweetheart", site: "Club L", note: "AZ 同廓形覆盖不足" },
    { label: "Emerald + Ball-Gown", site: "Birdy Grey", note: "AZ 无对应色" },
    { label: "One-shoulder + Side slit", site: "Six Stories", note: "设计元素 gap" },
  ],
  azOnly: [
    { label: "Dusty Blue + Straight Neck", note: "成熟优势 · 可维持" },
    { label: "Mulberry + A-Line", note: "内部验证强 · 竞品少跟" },
  ],
  bothHot: [
    { label: "Dusty Sage + A-Line", note: "双高 · 建议主力跟款/加色" },
    { label: "Navy + V-neck", note: "竞品升 · 内部已验证" },
  ],
};

const riskItems = [
  { pdl1: "Size 尺码问题", pdl2: "尺码偏小", count: 42, trend: "+8", impact: "高", related: "Black · Sheath" },
  { pdl1: "Not-as-pictured 图货不一致", pdl2: "颜色与图片不一致", count: 31, trend: "+5", impact: "高", related: "Burgundy · Mermaid" },
  { pdl1: "Quality 质量问题", pdl2: "拉链问题", count: 24, trend: "+2", impact: "中", related: "—" },
  { pdl1: "Material 面料问题", pdl2: "面料薄透", count: 19, trend: "-1", impact: "中", related: "—" },
  { pdl1: "Style 款式问题", pdl2: "领口太低", count: 15, trend: "+3", impact: "中", related: "—" },
];

const socialKeywords = [
  { keyword: "sage green bridesmaid", platform: "TikTok", heat: 86 },
  { keyword: "square neck satin", platform: "Instagram", heat: 72 },
  { keyword: "mix and match bd", platform: "Pinterest", heat: 68 },
];

let selectedOppId = "opp-001";
let poolFilters = { color: "全部", action: "全部", site: "全部", search: "" };
let draftSynced = false;

const renderers = {
  overview: renderOverview,
  pool: renderPool,
  "new-arrivals": renderNewArrivals,
  gap: renderGap,
  risk: renderRisk,
  draft: renderDraft,
};

const routes = Object.keys(renderers);
const app = document.getElementById("app");
const titleEl = document.getElementById("page-title");
const descriptionEl = document.getElementById("page-description");
const globalFiltersEl = document.getElementById("global-filters");
const workspaceEl = document.querySelector(".workspace");

function getRoute() {
  const hash = window.location.hash.replace("#", "");
  return routes.includes(hash) ? hash : "overview";
}

function getSelectedOpp() {
  return opportunities.find((item) => item.id === selectedOppId) || opportunities[0];
}

function scoreClass(score) {
  if (score >= 75) return "high";
  if (score >= 55) return "mid";
  return "low";
}

function quadrantClass(quadrant) {
  const map = {
    "重点机会": "opportunity",
    "风险冗余": "risk",
    "成熟优势": "mature",
    "持续观察": "watch",
  };
  return map[quadrant] || "watch";
}

function statusLabel(status) {
  const map = {
    active: "可推进",
    watching: "观察中",
    blocked: "已阻断",
    ready: "待扩产",
  };
  return map[status] || status;
}

function quadrantTag(quadrant) {
  return `<span class="quadrant-tag quadrant-tag--${quadrantClass(quadrant)}">${quadrant}</span>`;
}

function priorityBadge(priority) {
  const cls = priority.toLowerCase();
  return `<span class="priority-badge priority-badge--${cls}">${priority}</span>`;
}

function statusTag(status) {
  return `<span class="status-tag status-tag--${status}">${statusLabel(status)}</span>`;
}

function adaptBar(score) {
  const cls = scoreClass(score);
  return `
    <div class="adapt-bar">
      <div class="adapt-bar__track">
        <div class="adapt-bar__fill adapt-bar__fill--${cls}" style="width:${score}%"></div>
      </div>
      <span class="adapt-bar__val">${score}</span>
    </div>
  `;
}

function actionTag(action, cls) {
  return `<span class="action-tag action-tag--${cls}">${action}</span>`;
}

function tag(text, kind) {
  return `<span class="tag tag--${kind}">${text}</span>`;
}

function renderGlobalFilters() {
  if (!globalFiltersEl) return;
  globalFiltersEl.innerHTML = `
    <div class="global-filter">
      <label>数据周次</label>
      <select disabled><option>${DATA_WEEK}</option></select>
    </div>
    <div class="global-filter">
      <label>业务线</label>
      <select disabled><option>${CATEGORY_LINE} · Bridesmaid</option></select>
    </div>
    <div class="global-filter">
      <label>市场</label>
      <select disabled><option>US</option></select>
    </div>
    <span class="global-filter__divider"></span>
    <span class="muted">三信号引擎 · 内部版</span>
  `;
}

function renderFilterCard(fieldsHtml, showSearch = true) {
  return `
    <section class="filter-card">
      <div class="filter-card__row">
        ${showSearch ? `
          <div class="field field--search">
            <label>搜索</label>
            <input type="search" data-filter="search" placeholder="SKC / 款式 / 品牌 / 颜色..." value="${poolFilters.search}" />
          </div>
        ` : ""}
        ${fieldsHtml}
        <div class="filter-card__actions">
          <button class="btn btn--ghost" data-action="reset-filters">重置</button>
        </div>
      </div>
    </section>
  `;
}

function renderKpiStrip(items) {
  return `
    <section class="kpi-strip">
      ${items
        .map(
          (item) => `
        <article class="kpi-card">
          <span class="kpi-card__label">${item.label}</span>
          <strong class="kpi-card__value">${item.value}</strong>
          <span class="kpi-card__hint">${item.hint}</span>
        </article>
      `
        )
        .join("")}
    </section>
  `;
}

function renderOpportunityTable(rows, { showDraft = true, compact = false } = {}) {
  if (!rows.length) {
    return `<div class="empty-state">暂无匹配数据，请调整筛选条件</div>`;
  }

  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>优先级</th>
            <th>款式 / SKC</th>
            <th>站点</th>
            <th>象限</th>
            <th>适配度</th>
            <th class="col-num">Trend</th>
            <th class="col-num">Gap</th>
            <th class="col-num">Risk</th>
            <th class="col-num">综合</th>
            <th>状态</th>
            <th>建议动作</th>
            ${showDraft ? '<th class="col-actions">操作</th>' : ""}
          </tr>
        </thead>
        <tbody>
          ${rows
            .map((item) => {
              const conflict = item.conflict
                ? `<span class="table-sub" style="color:var(--danger)">${item.conflict}</span>`
                : "";
              return `
            <tr data-opp-id="${item.id}">
              <td>${priorityBadge(item.priority)}</td>
              <td>
                <strong>${item.title}</strong>
                <span class="table-sub">${item.skcKey} · ${item.price} · 排名 ${item.rankChange}</span>
                ${conflict}
              </td>
              <td>${item.site}</td>
              <td>${quadrantTag(item.quadrant)}</td>
              <td>${adaptBar(item.internal)}</td>
              <td class="col-num score-cell score-cell--${scoreClass(item.trend)}">${item.trend}</td>
              <td class="col-num score-cell score-cell--${scoreClass(item.gap)}">${item.gap}</td>
              <td class="col-num score-cell score-cell--${item.risk >= 60 ? "low" : scoreClass(100 - item.risk)}">${item.risk}</td>
              <td class="col-num score-cell score-cell--${scoreClass(item.composite)}">${item.composite}</td>
              <td>${statusTag(item.status)}</td>
              <td>${actionTag(item.action, item.actionClass)}</td>
              ${
                showDraft
                  ? `<td class="col-actions"><button class="table-link" data-route="draft" data-select-opp="${item.id}">生成提案</button></td>`
                  : ""
              }
            </tr>
          `;
            })
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function filteredOpportunities() {
  const q = poolFilters.search.trim().toLowerCase();
  return opportunities.filter((item) => {
    if (poolFilters.color !== "全部" && item.color !== poolFilters.color) return false;
    if (poolFilters.site !== "全部" && item.site !== poolFilters.site) return false;
    if (poolFilters.action !== "全部" && item.action !== poolFilters.action) return false;
    if (q) {
      const hay = `${item.title} ${item.skcKey} ${item.brand} ${item.color} ${item.site}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function renderOverview() {
  const sorted = [...opportunities].sort((a, b) => b.composite - a.composite);

  return `
    <div class="page">
      ${renderKpiStrip([
        { label: "本周竞品上新", value: "59", hint: "较 W26 +11 · Birdy Grey 最多" },
        { label: "重点机会", value: "02", hint: "P0 主力候选 · 可直接提案" },
        { label: "冲突待判", value: "01", hint: "外热内弱需写清佐证" },
        { label: "Top 避雷", value: "Size", hint: "尺码偏小 42 条" },
      ])}

      ${renderFilterCard(`
        <div class="field">
          <label>象限</label>
          <select disabled><option>全部象限</option></select>
        </div>
        <div class="field">
          <label>优先级</label>
          <select disabled><option>全部</option></select>
        </div>
        <div class="field">
          <label>状态</label>
          <select disabled><option>全部状态</option></select>
        </div>
      `, false)}

      <section class="data-panel">
        <div class="data-panel__header">
          <div>
            <h3>本周机会矩阵</h3>
            <p>四维综合分排序 · 象限标签 + 适配度 + 状态</p>
          </div>
          <div class="data-panel__meta">
            <button class="btn btn--ghost" data-route="pool">进入机会池 →</button>
          </div>
        </div>
        ${renderOpportunityTable(sorted)}
      </section>

      <section class="two-col">
        <article class="data-panel">
          <div class="data-panel__header">
            <div><h3>社媒热词</h3><p>场外热度补充 · 映射盘古属性</p></div>
          </div>
          <div class="mini-bars">
            ${socialKeywords
              .map(
                (item) => `
              <div class="mini-bar-row">
                <span>${item.platform}</span>
                <div class="mini-bar-track"><div class="mini-bar-fill" style="width:${item.heat}%"></div></div>
                <strong>${item.heat}</strong>
              </div>
              <span class="table-sub" style="margin:-4px 0 4px 108px;display:block">${item.keyword}</span>
            `
              )
              .join("")}
          </div>
        </article>

        <article class="data-panel">
          <div class="data-panel__header">
            <div><h3>Top 避雷速览</h3><p>商品 PDL · 跟款前必看</p></div>
            <button class="btn btn--ghost" data-route="risk">完整避雷榜 →</button>
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr><th>一级原因</th><th>二级原因</th><th class="col-num">条数</th><th>影响</th></tr>
              </thead>
              <tbody>
                ${riskItems
                  .slice(0, 3)
                  .map(
                    (item) => `
                  <tr>
                    <td><strong>${item.pdl1}</strong></td>
                    <td>${item.pdl2}</td>
                    <td class="col-num">${item.count}</td>
                    <td>${tag(item.impact, item.impact === "高" ? "danger" : "warning")}</td>
                  </tr>
                `
                  )
                  .join("")}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </div>
  `;
}

function renderPool() {
  const colors = ["全部", ...new Set(opportunities.map((item) => item.color))];
  const sites = ["全部", ...new Set(opportunities.map((item) => item.site))];
  const actions = ["全部", ...new Set(opportunities.map((item) => item.action))];
  const rows = filteredOpportunities().sort((a, b) => b.composite - a.composite);

  return `
    <div class="page">
      ${renderKpiStrip([
        { label: "候选总数", value: String(opportunities.length).padStart(2, "0"), hint: "三信号融合推荐" },
        { label: "当前筛选", value: String(rows.length).padStart(2, "0"), hint: "匹配筛选条件" },
        { label: "P0 主力", value: "02", hint: "重点机会 + 成熟优势" },
        { label: "默认权重", value: "30/30/20/20", hint: "T / I / G / R" },
      ])}

      ${renderFilterCard(`
        <div class="field">
          <label>颜色</label>
          <select data-filter="color">
            ${colors.map((c) => `<option${poolFilters.color === c ? " selected" : ""}>${c}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label>竞品站点</label>
          <select data-filter="site">
            ${sites.map((s) => `<option${poolFilters.site === s ? " selected" : ""}>${s}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label>建议动作</label>
          <select data-filter="action">
            ${actions.map((a) => `<option${poolFilters.action === a ? " selected" : ""}>${a}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label>象限</label>
          <select disabled><option>全部象限</option></select>
        </div>
      `)}

      <section class="data-panel">
        <div class="data-panel__header">
          <div>
            <h3>机会池候选列表</h3>
            <p>共 ${rows.length} 条 · 按综合分降序</p>
          </div>
          <button class="btn btn--primary" data-route="draft" data-select-opp="${rows[0]?.id || "opp-001"}">从 Top1 生成提案</button>
        </div>
        ${renderOpportunityTable(rows)}
      </section>
    </div>
  `;
}

function renderNewArrivals() {
  return `
    <div class="page">
      ${renderKpiStrip([
        { label: "本周上新总数", value: "59", hint: "上新表聚合 · W27" },
        { label: "Top 站点", value: "Birdy Grey", hint: "18 款 · +6 vs W26" },
        { label: "升温属性", value: "Dusty Sage", hint: "12 款命中" },
        { label: "价格带", value: "$99–149", hint: "与 AZ BD 主力带重叠" },
      ])}

      ${renderFilterCard(`
        <div class="field">
          <label>站点</label>
          <select disabled><option>全部站点</option></select>
        </div>
        <div class="field">
          <label>上新类型</label>
          <select disabled><option>全部类型</option></select>
        </div>
        <div class="field">
          <label>颜色</label>
          <select disabled><option>全部颜色</option></select>
        </div>
      `, false)}

      <section class="two-col">
        <article class="data-panel">
          <div class="data-panel__header"><div><h3>Top 站点 · 上新数</h3><p>雷达上新表按网站名聚合</p></div></div>
          <div class="mini-bars">
            ${newArrivalsBySite
              .map(
                (item) => `
              <div class="mini-bar-row">
                <span>${item.site}</span>
                <div class="mini-bar-track"><div class="mini-bar-fill" style="width:${(item.count / 18) * 100}%"></div></div>
                <strong>${item.count} ${item.delta}</strong>
              </div>
            `
              )
              .join("")}
          </div>
        </article>
        <article class="data-panel">
          <div class="data-panel__header"><div><h3>Top 属性 · 命中</h3><p>颜色/廓形/领型/面料</p></div></div>
          <div class="mini-bars">
            ${newArrivalsByAttr
              .map(
                (item) => `
              <div class="mini-bar-row">
                <span>${item.attr.split(" · ")[0]}</span>
                <div class="mini-bar-track"><div class="mini-bar-fill mini-bar-fill--success" style="width:${item.pct}%"></div></div>
                <strong>${item.count}</strong>
              </div>
            `
              )
              .join("")}
          </div>
        </article>
      </section>

      <section class="data-panel">
        <div class="data-panel__header">
          <div><h3>本周上新明细</h3><p>字段对齐雷达上新表 · 点击可溯源 SKC</p></div>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>站点/品牌</th>
                <th>款式</th>
                <th>颜色</th>
                <th>上新类型</th>
                <th class="col-num">售价</th>
                <th>排名涨跌</th>
                <th>象限</th>
                <th class="col-actions">操作</th>
              </tr>
            </thead>
            <tbody>
              ${opportunities
                .filter((item) => item.site !== "Azazie")
                .map(
                  (item) => `
                <tr>
                  <td><strong>${item.site}</strong><span class="table-sub">${item.brand}</span></td>
                  <td>${item.silhouette} · ${item.neckline}</td>
                  <td>${item.color}</td>
                  <td>${item.newType}</td>
                  <td class="col-num">${item.price}</td>
                  <td>${tag(item.rankChange, "success")}</td>
                  <td>${quadrantTag(item.quadrant)}</td>
                  <td class="col-actions"><button class="table-link" data-route="draft" data-select-opp="${item.id}">生成提案</button></td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `;
}

function renderGap() {
  const gapRows = [
    ...gapData.competitorOnly.map((item) => ({ ...item, type: "竞品有 · AZ 缺", quadrant: "重点机会", action: "跟款机会", actionClass: "warn" })),
    ...gapData.azOnly.map((item) => ({ ...item, type: "AZ 有 · 竞品少", quadrant: "成熟优势", action: "维持", actionClass: "internal" })),
    ...gapData.bothHot.map((item) => ({ ...item, type: "双高", quadrant: "重点机会", action: "主力候选", actionClass: "primary" })),
  ];

  return `
    <div class="page">
      ${renderKpiStrip([
        { label: "竞品缺口", value: "03", hint: "AZ 覆盖不足" },
        { label: "成熟优势", value: "02", hint: "AZ 有竞品少跟" },
        { label: "双高机会", value: "02", hint: "外部热 + 内部验证" },
        { label: "数据周次", value: DATA_WEEK, hint: `${CATEGORY_LINE} · Bridesmaid` },
      ])}

      ${renderFilterCard(`
        <div class="field">
          <label>Gap 类型</label>
          <select disabled><option>全部类型</option></select>
        </div>
        <div class="field">
          <label>象限</label>
          <select disabled><option>全部象限</option></select>
        </div>
      `, false)}

      <section class="data-panel">
        <div class="data-panel__header">
          <div><h3>Gap 对照矩阵</h3><p>盘古 AZ 数据 + 雷达竞品横向对比</p></div>
          ${tag(`${DATA_WEEK} · ${CATEGORY_LINE}`, "processing")}
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Gap 类型</th>
                <th>属性组合</th>
                <th>站点/备注</th>
                <th>象限</th>
                <th>建议动作</th>
              </tr>
            </thead>
            <tbody>
              ${gapRows
                .map(
                  (item) => `
                <tr>
                  <td><strong>${item.type}</strong></td>
                  <td>${item.label}</td>
                  <td><span class="muted">${item.site || "—"}</span> ${item.note ? `<span class="table-sub">${item.note}</span>` : ""}</td>
                  <td>${quadrantTag(item.quadrant)}</td>
                  <td>${actionTag(item.action, item.actionClass)}</td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </section>

      <section class="data-panel">
        <div class="data-panel__header"><div><h3>Gap 分组视图</h3><p>按缺口类型快速浏览</p></div></div>
        <div class="gap-grid">
          <article class="gap-card">
            <h4>竞品有 · AZ 缺口</h4>
            <div class="gap-list">
              ${gapData.competitorOnly
                .map(
                  (item) => `
                <div class="gap-item">
                  <span><strong>${item.label}</strong><span class="table-sub">${item.site} · ${item.note}</span></span>
                  ${actionTag("跟款机会", "warn")}
                </div>
              `
                )
                .join("")}
            </div>
          </article>
          <article class="gap-card">
            <h4>AZ 有 · 竞品少跟</h4>
            <div class="gap-list">
              ${gapData.azOnly
                .map(
                  (item) => `
                <div class="gap-item">
                  <span><strong>${item.label}</strong><span class="table-sub">${item.note}</span></span>
                  ${quadrantTag("成熟优势")}
                </div>
              `
                )
                .join("")}
            </div>
          </article>
        </div>
      </section>
    </div>
  `;
}

function renderRisk() {
  const highRisk = opportunities.filter((item) => item.risk >= 60);

  return `
    <div class="page">
      ${renderKpiStrip([
        { label: "商品差评总量", value: "131", hint: "BD 品类 · W27 滚动" },
        { label: "最高频 PDL1", value: "Size", hint: "尺码偏小占 32%" },
        { label: "跟款高风险", value: "01", hint: "外热 + 高退货密集" },
        { label: "雷达差评列", value: "AT", hint: "BD 无列走舆情包" },
      ])}

      ${renderFilterCard(`
        <div class="field">
          <label>PDL 一级</label>
          <select disabled><option>全部原因</option></select>
        </div>
        <div class="field">
          <label>影响等级</label>
          <select disabled><option>全部</option></select>
        </div>
        <div class="field">
          <label>周环比</label>
          <select disabled><option>全部</option></select>
        </div>
      `)}

      <section class="data-panel">
        <div class="data-panel__header">
          <div><h3>商品 PDL 避雷榜</h3><p>复用舆情 opinion_records 口径 · 进 risk 维与提案佐证</p></div>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>一级原因</th>
                <th>二级原因</th>
                <th class="col-num">条数</th>
                <th class="col-num">周环比</th>
                <th>影响</th>
                <th>关联款式</th>
                <th class="col-actions">操作</th>
              </tr>
            </thead>
            <tbody>
              ${riskItems
                .map(
                  (item) => `
                <tr>
                  <td><strong>${item.pdl1}</strong></td>
                  <td>${item.pdl2}</td>
                  <td class="col-num">${item.count}</td>
                  <td class="col-num">${item.trend}</td>
                  <td>${tag(item.impact, item.impact === "高" ? "danger" : "warning")}</td>
                  <td>${item.related}</td>
                  <td class="col-actions"><button class="table-link" data-route="pool">查看候选</button></td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </section>

      <section class="data-panel">
        <div class="data-panel__header">
          <div><h3>高风险候选联动</h3><p>外热但 risk ≥ 60 · 默认建议回避</p></div>
        </div>
        ${renderOpportunityTable(highRisk)}
      </section>
    </div>
  `;
}

function renderDraft() {
  const item = getSelectedOpp();
  const sourceType = item.action === "内部扩产" ? "Internal Data" : "Competitor";

  return `
    <div class="page">
      <section class="draft-panel">
        <div class="draft-header">
          <div>
            <p class="muted" style="margin:0 0 4px;text-transform:uppercase;letter-spacing:0.06em;font-size:11px">Proposal Draft · ${DATA_WEEK}</p>
            <h3>${item.title}</h3>
            <p class="muted" style="margin:4px 0 0">
              ${actionTag(item.action, item.actionClass)} · 综合分 ${item.composite} · ${quadrantTag(item.quadrant)} · ${priorityBadge(item.priority)}
            </p>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            ${tag("三信号已融合", "success")}
            ${item.conflict ? tag(item.conflict, "danger") : tag("无冲突", "success")}
            ${draftSynced ? tag("已同步选款", "success") : tag("本地草案", "waiting")}
          </div>
        </div>

        <div class="meta-grid">
          <div class="metric-card"><span>业务线</span><strong>${CATEGORY_LINE}</strong></div>
          <div class="metric-card"><span>品类</span><strong>伴娘服</strong></div>
          <div class="metric-card"><span>新款来源</span><strong>${sourceType}</strong></div>
          <div class="metric-card"><span>目标价格</span><strong>${item.price}</strong></div>
          <div class="metric-card"><span>适配度</span><strong>${item.internal}</strong></div>
          <div class="metric-card"><span>状态</span><strong>${statusLabel(item.status)}</strong></div>
        </div>

        <div class="two-col">
          <div class="form-sections">
            <section class="form-section">
              <h4>选款「创建提案」字段预填</h4>
              <div class="field-group">
                <div class="field"><label>业务线</label><input value="${CATEGORY_LINE}" /></div>
                <div class="field"><label>品类</label><input value="伴娘服" /></div>
                <div class="field"><label>新款来源</label><input value="${sourceType}" /></div>
                <div class="field"><label>提案人</label><input value="Shelly" /></div>
                <div class="field field--full"><label>目标价格</label><input value="${item.price}" /></div>
                <div class="field field--full"><label>面料</label><input value="${item.fabric}" /></div>
                <div class="field field--full"><label>关键设计点</label><input value="${item.color} · ${item.silhouette} · ${item.neckline}" /></div>
              </div>
            </section>
            <section class="form-section">
              <h4>提案佐证 source_evidence</h4>
              <div class="evidence-box">
                <strong>数据周次：</strong>${DATA_WEEK}<br/>
                <strong>品牌/网站：</strong>${item.brand} / ${item.site}<br/>
                <strong>链接：</strong>${item.url || "（内部驱动，无竞品链接）"}<br/>
                <strong>SKC：</strong>${item.skcKey} · 排名涨跌 ${item.rankChange}<br/>
                <strong>内部交叉：</strong>${item.internalNote} · 象限 ${item.quadrant}<br/>
                ${item.conflict ? `<strong>冲突说明：</strong>${item.conflict}，建议 ${item.action}<br/>` : ""}
                <strong>结论：</strong>${item.action} — 综合分 ${item.composite}（T${item.trend}/I${item.internal}/G${item.gap}/R${item.risk}）
              </div>
            </section>
          </div>

          <div class="form-sections">
            <section class="form-section">
              <h4>参考图 · 溯源</h4>
              <div class="gallery-grid">
                <div class="gallery-card">
                  <div class="gallery-visual"></div>
                  <strong style="font-size:12px">正面图 front_image</strong>
                  <span class="table-sub">来自雷达主图</span>
                </div>
                <div class="gallery-card">
                  <div class="gallery-visual"></div>
                  <strong style="font-size:12px">signal_refs</strong>
                  <span class="table-sub">competitor_trend + internal_fit</span>
                </div>
              </div>
            </section>
            <section class="form-section">
              <h4>同步元数据</h4>
              <div style="display:grid;gap:6px">
                <div class="record-row"><strong>hub_draft_id</strong><span class="muted">HUB-${DATA_WEEK}-${item.skcKey}</span></div>
                <div class="record-row"><strong>generation_source</strong><span class="muted">system_hub</span></div>
                <div class="record-row"><strong>幂等同步</strong><span class="muted">POST /api/proposal/create-from-hub</span></div>
              </div>
            </section>
          </div>
        </div>

        <div class="sticky-actions">
          <div>
            <strong style="font-size:13px">保存后将写入选款草稿，不替代一审/终审</strong>
            <p class="muted" style="margin:2px 0 0">P0 Demo：点击同步模拟返回 proposal_id</p>
          </div>
          <div style="display:flex;gap:8px">
            <button class="btn btn--ghost" data-route="pool">返回机会池</button>
            <button class="btn btn--primary" id="sync-draft-btn">同步至选款草稿</button>
          </div>
        </div>
      </section>
    </div>
  `;
}

function setActive(route) {
  document.querySelectorAll(".sidenav-link").forEach((node) => {
    node.classList.toggle("is-active", node.dataset.route === route);
  });
}

function showToast(message) {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();
  const node = document.createElement("div");
  node.className = "toast";
  node.textContent = message;
  document.body.appendChild(node);
  setTimeout(() => node.remove(), 2800);
}

function resetFilters() {
  poolFilters = { color: "全部", action: "全部", site: "全部", search: "" };
  if (getRoute() === "pool" || getRoute() === "risk") render();
}

function render() {
  const route = getRoute();
  const meta = pageMeta[route];
  titleEl.textContent = meta.title;
  descriptionEl.textContent = meta.description;
  renderGlobalFilters();
  setActive(route);
  app.innerHTML = renderers[route]();
  if (workspaceEl) workspaceEl.scrollTop = 0;

  const syncBtn = document.getElementById("sync-draft-btn");
  if (syncBtn) {
    syncBtn.addEventListener("click", () => {
      draftSynced = true;
      showToast("已同步选款草稿 · proposal_id = PROP-2026W27-0042");
      render();
    });
  }
}

function syncRoute(route) {
  window.location.hash = route;
}

document.addEventListener("click", (event) => {
  const resetBtn = event.target.closest("[data-action='reset-filters']");
  if (resetBtn) {
    resetFilters();
    return;
  }

  const selectOpp = event.target.closest("[data-select-opp]");
  if (selectOpp) {
    selectedOppId = selectOpp.dataset.selectOpp;
  }

  const target = event.target.closest("[data-route]");
  if (target) {
    syncRoute(target.dataset.route);
  }
});

document.addEventListener("change", (event) => {
  const filterKey = event.target.dataset.filter;
  if (filterKey) {
    poolFilters[filterKey] = event.target.value;
    const route = getRoute();
    if (route === "pool" || route === "risk") render();
  }
});

document.addEventListener("input", (event) => {
  if (event.target.dataset.filter === "search") {
    poolFilters.search = event.target.value;
    const route = getRoute();
    if (route === "pool" || route === "risk") render();
  }
});

window.addEventListener("hashchange", render);
render();
