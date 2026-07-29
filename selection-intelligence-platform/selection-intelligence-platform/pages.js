/**
 * 其余业务页 · 中等保真 Demo
 * 依赖 app.js：renderKpiCard / renderTag / showToast
 */

const PAGE_UI = {
  newHotTab: "new",
  attrDim: "color",
  hotTab: "site",
  mcTab: "dynamic",
  pricingCountry: "US",
  mappingTab: "dict",
};

function pageFilters(fields, actionsHtml = "") {
  return `
    <section class="filter-card">
      <div class="filter-grid filter-grid--${Math.min(fields.length, 6)}">
        ${fields
          .map(
            (f) => `
          <div class="field">
            <label>${f.label}</label>
            ${
              f.type === "input"
                ? `<input type="text" placeholder="${f.placeholder || ""}" value="${f.value || ""}" />`
                : `<select>${(f.options || []).map((o) => `<option>${o}</option>`).join("")}</select>`
            }
          </div>
        `
          )
          .join("")}
      </div>
      <div class="filter-actions filter-actions--bar">
        ${actionsHtml || `
          <button type="button" class="btn btn-secondary" data-toast="refresh">刷新</button>
          <button type="button" class="btn btn-secondary" data-toast="export-csv">导出 CSV</button>
        `}
      </div>
    </section>
  `;
}

function pageTable(headers, rowsHtml, title, sub) {
  return `
    <section class="table-card">
      <div class="table-toolbar">
        <div>
          <h3>${title}</h3>
          <p>${sub || ""}</p>
        </div>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
    </section>
  `;
}

function pageMiniBars(items, color = "var(--primary)") {
  const max = Math.max(...items.map((i) => i.value), 1);
  return `
    <div class="page-bars">
      ${items
        .map(
          (i) => `
        <div class="page-bar-row">
          <span>${i.name}</span>
          <div class="page-bar-track"><i style="width:${(i.value / max) * 100}%;background:${i.color || color}"></i></div>
          <strong>${i.value}${i.suffix || ""}</strong>
        </div>
      `
        )
        .join("")}
    </div>
  `;
}

function pageSpark(values, color = "#3b5bdb") {
  const max = Math.max(...values, 1);
  const w = 420;
  const h = 120;
  const pad = 12;
  const step = (w - pad * 2) / (values.length - 1);
  const pts = values
    .map((v, i) => `${pad + i * step},${h - 20 - (v / max) * (h - 36)}`)
    .join(" ");
  return `
    <svg viewBox="0 0 ${w} ${h}" class="page-spark" aria-hidden="true">
      <polyline fill="none" stroke="${color}" stroke-width="2.5" points="${pts}" />
      ${pts
        .split(" ")
        .map((p) => {
          const [x, y] = p.split(",");
          return `<circle cx="${x}" cy="${y}" r="3" fill="${color}" />`;
        })
        .join("")}
    </svg>
  `;
}

function pageTabs(tabs, active, dataKey) {
  return `
    <div class="page-tabs">
      ${tabs
        .map(
          (t) => `
        <button type="button" class="page-tab${active === t.id ? " is-active" : ""}" data-page-ui="${dataKey}" data-page-val="${t.id}">${t.label}</button>
      `
        )
        .join("")}
    </div>
  `;
}

function thumb(label, hue) {
  return `<div class="prod-thumb" style="--hue:${hue}" aria-hidden="true">${label.slice(0, 1)}</div>`;
}

/* ——— 监控报告：竞品网站动态（tab 容器：动态明细 / 竞品热榜 / 上新趋势） ——— */
function renderMonitorCompetitor() {
  const tab = PAGE_UI.mcTab;
  const tabs = pageTabs(
    [
      { id: "dynamic", label: "竞品动态明细" },
      { id: "hot", label: "竞品热榜" },
      { id: "trend", label: "上新趋势" },
    ],
    tab,
    "mcTab"
  );
  const body =
    tab === "hot"
      ? renderInsightNewHot()
      : tab === "trend"
        ? renderInsightTrend()
        : renderCompetitorDynamic();

  return `
    <div class="mc-tabbar">${tabs}</div>
    ${body}
  `;
}

/* ——— 竞品动态明细（原竞品网站动态内容） ——— */
function renderCompetitorDynamic() {
  const rows = [
    ["Birdy Grey", "Dusty Sage Wrap", "BD", "Dusty Sage", "A-Line", "$98", 12, 5, "+7", "上新", "跟款机会", 210],
    ["Azazie Comp", "Burgundy Mermaid", "BD", "Burgundy", "Mermaid", "$119", 8, 3, "+5", "上升", "主力候选", 340],
    ["JJ's House", "Champagne Satin", "AT", "Champagne", "Sheath", "$86", 21, 28, "-7", "下降", "小测验证", 40],
    ["Revelry", "Emerald Ball-Gown", "BD", "Emerald", "Ball-Gown", "$135", 15, 9, "+6", "上升", "跟款机会", 160],
    ["Lulus", "Navy Column", "MOB", "Navy", "Column", "$78", 34, "—", "—", "下架", "回避风险", 200],
    ["Show Me Yours", "Terracotta One Shoulder", "AT", "Terracotta", "Sheath", "$109", 6, 4, "+2", "上新", "小测验证", 25],
  ];

  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "MC1", label: "本周竞品上新数", value: "126", sub: "覆盖 8 个重点站点" })}
        ${renderKpiCard({ id: "MC2", label: "排名上升商品数", value: "84", sub: "周环比 +18" })}
        ${renderKpiCard({ id: "MC3", label: "下架商品数", value: "21", sub: "含高退货关联款" })}
        ${renderKpiCard({ id: "MC4", label: "重点关注站点数", value: "8", sub: "BD / AT 雷达" })}
      </section>
      ${pageFilters([
        { label: "周次", options: ["2026-W27", "2026-W26", "2026-W25"] },
        { label: "竞品站点", options: ["全部站点", "Birdy Grey", "JJ's House", "Revelry", "Lulus"] },
        { label: "业务线", options: ["全部", "BD", "AT", "MOB"] },
        { label: "品类", options: ["全部", "Bridesmaid Dresses", "Atelier", "Mother of the Bride"] },
        { label: "颜色", options: ["全部", "Dusty Sage", "Burgundy", "Champagne"] },
        { label: "廓形", options: ["全部", "A-Line", "Mermaid", "Sheath"] },
        { label: "排名变化", options: ["全部", "上升", "下降", "新入榜", "下架"] },
      ])}
      ${pageTable(
        ["站点", "商品图", "商品名", "品类", "颜色", "廓形", "价格", "原始排名", "当前排名", "涨跌", "状态", "建议动作", "操作"],
        rows
          .map(
            (r) => `
          <tr>
            <td>${r[0]}</td>
            <td>${thumb(r[1], r[11])}</td>
            <td><span class="cell-title">${r[1]}</span></td>
            <td>${r[2]}</td>
            <td>${r[3]}</td>
            <td>${r[4]}</td>
            <td>${r[5]}</td>
            <td class="score-num">${r[6]}</td>
            <td class="score-num">${r[7]}</td>
            <td class="score-num">${r[8]}</td>
            <td>${renderTag(r[9], r[9] === "下架" ? "red" : r[9] === "上升" || r[9] === "上新" ? "green" : "orange")}</td>
            <td>${renderTag(r[10], ACTION_STYLE[r[10]]?.tag || "muted")}</td>
            <td><button type="button" class="btn-text" data-toast="voc-pool">加入机会池</button></td>
          </tr>
        `
          )
          .join(""),
        "竞品动态明细",
        "本周监控 · 点击加入机会池"
      )}
    </div>
  `;
}

/* ——— 监控报告：内部数据动态 ——— */
function renderMonitorInternal() {
  const rows = [
    ["Dusty Sage · A-Line · Square", "BD", "Bridesmaid", "跟款机会", "双高机会", 82, 76, "主力候选", "外部热度抬升 + 内部适配稳定"],
    ["Burgundy · Mermaid", "BD", "Bridesmaid", "双高机会", "外热内弱", 54, 72, "小测验证", "Internal Fit 回落"],
    ["Champagne · Satin", "AT", "Atelier", "低优先级", "外热内弱", 46, 68, "小测验证", "竞品热榜进入"],
    ["Navy · Column", "MOB", "MOB", "内部优势", "内部优势", 74, 38, "保守维护", "无显著变化"],
    ["White · Sheath", "BD", "Bridesmaid", "外热内弱", "回避风险", 32, 44, "回避风险", "退货/差评上升"],
  ];

  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "MI1", label: "新增内部机会", value: "14", sub: "本周新入库" })}
        ${renderKpiCard({ id: "MI2", label: "适配度上升属性", value: "9", sub: "Internal Fit ↑" })}
        ${renderKpiCard({ id: "MI3", label: "适配度下降属性", value: "6", sub: "需复核风险" })}
        ${renderKpiCard({ id: "MI4", label: "建议动作变更数", value: "11", sub: "相对上周" })}
      </section>
      ${pageFilters([
        { label: "周次", options: ["2026-W27", "2026-W26"] },
        { label: "业务线", options: ["全部", "BD", "AT", "MOB"] },
        { label: "品类", options: ["全部", "Bridesmaid", "Atelier", "MOB"] },
        { label: "变化类型", options: ["全部", "上升", "下降", "动作变更"] },
      ])}
      <section class="page-split">
        <article class="voc-panel">
          <h4>内部适配度趋势</h4>
          ${pageSpark([68, 70, 71, 73, 75, 74, 76], "#0ca678")}
          <p class="muted" style="margin:8px 0 0;">近 7 周均值 · BD 线</p>
        </article>
        <article class="voc-panel">
          <h4>建议清单变动</h4>
          <div class="page-change-list">
            <div><strong>+4</strong><span>新晋主力候选</span></div>
            <div><strong>+5</strong><span>转入小测验证</span></div>
            <div><strong>+2</strong><span>升为回避风险</span></div>
            <div><strong>-3</strong><span>退出跟款机会</span></div>
          </div>
        </article>
      </section>
      ${pageTable(
        ["属性组合", "业务线", "品类", "上周象限", "本周象限", "Internal Fit", "Gap Score", "建议动作", "变化原因"],
        rows
          .map(
            (r) => `
          <tr>
            <td><span class="cell-title">${r[0]}</span></td>
            <td>${r[1]}</td>
            <td>${r[2]}</td>
            <td>${r[3]}</td>
            <td>${r[4]}</td>
            <td class="score-num">${r[5]}</td>
            <td class="score-num">${r[6]}</td>
            <td>${renderTag(r[7], ACTION_STYLE[r[7]]?.tag || "muted")}</td>
            <td><span class="cell-sub" style="margin:0;display:inline;">${r[8]}</span></td>
          </tr>
        `
          )
          .join(""),
        "象限变化列表",
        "对比上周 · 建议动作联动更新"
      )}
    </div>
  `;
}

/* ——— 竞品上新 / 热榜 ——— */
function renderInsightNewHot() {
  const tab = PAGE_UI.newHotTab;
  const tabs = pageTabs(
    [
      { id: "new", label: "竞品上新" },
      { id: "hot", label: "竞品热榜" },
      { id: "move", label: "排名涨跌" },
    ],
    tab,
    "newHotTab"
  );

  const data = {
    new: [
      ["Birdy Grey", "Misty Rose A-Line", "$99", "新上架", "—", "否"],
      ["Revelry", "Sage Cape Sleeve", "$128", "新上架", "—", "是"],
      ["JJ's House", "Blush Empire", "$76", "新上架", "—", "否"],
      ["Lulus", "Cocoa Satin Midi", "$84", "新上架", "—", "否"],
    ],
    hot: [
      ["Birdy Grey", "Dusty Sage Wrap", "$98", 1, "—", "是"],
      ["Azazie Comp", "Burgundy Mermaid", "$119", 2, "—", "是"],
      ["Revelry", "Emerald Ball-Gown", "$135", 3, "—", "否"],
      ["Show Me Yours", "Champagne Slit", "$109", 4, "—", "是"],
    ],
    move: [
      ["Birdy Grey", "Dusty Sage Wrap", "$98", 5, "+7", "是"],
      ["JJ's House", "Champagne Satin", "$86", 28, "-7", "否"],
      ["Revelry", "Emerald Ball-Gown", "$135", 9, "+6", "否"],
      ["Lulus", "Navy Column", "$78", "下架", "—", "否"],
    ],
  }[tab];

  const headers =
    tab === "move"
      ? ["站点", "商品名", "价格", "当前排名", "涨跌", "是否进入机会池", "操作"]
      : tab === "hot"
        ? ["站点", "商品名", "价格", "排名", "涨跌", "是否进入机会池", "操作"]
        : ["站点", "商品名", "价格", "状态", "排名", "是否进入机会池", "操作"];

  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "NH1", label: "本周上新", value: "126", sub: "多站点合计" })}
        ${renderKpiCard({ id: "NH2", label: "热榜 Top20", value: "20", sub: "滚动监控" })}
        ${renderKpiCard({ id: "NH3", label: "显著上涨", value: "37", sub: "涨幅 ≥ 5 名" })}
        ${renderKpiCard({ id: "NH4", label: "已入机会池", value: "12", sub: "本周新增" })}
      </section>
      ${pageFilters([
        { label: "周次", options: ["2026-W27", "2026-W26"] },
        { label: "站点", options: ["全部", "Birdy Grey", "Revelry", "JJ's House"] },
        { label: "业务线", options: ["全部", "BD", "AT"] },
        { label: "品类", options: ["全部", "Bridesmaid Dresses", "Atelier"] },
      ])}
      <section class="card card-pad">
        ${tabs}
        ${pageTable(
          headers,
          data
            .map(
              (r) => `
            <tr>
              <td>${r[0]}</td>
              <td><span class="cell-title">${r[1]}</span></td>
              <td>${r[2]}</td>
              <td>${r[3]}</td>
              <td>${r[4]}</td>
              <td>${renderTag(r[5], r[5] === "是" ? "green" : "muted")}</td>
              <td>
                <button type="button" class="btn-text" data-toast="voc-pool">${r[5] === "是" ? "查看机会" : "加入机会池"}</button>
              </td>
            </tr>
          `
            )
            .join(""),
          tab === "new" ? "竞品上新列表" : tab === "hot" ? "竞品热榜" : "排名涨跌",
          "支持标记是否进入机会池"
        )}
      </section>
    </div>
  `;
}

/* ——— 上新趋势 ——— */
function renderInsightTrend() {
  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "IT1", label: "本周上新量", value: "126", sub: "环比 +14%" })}
        ${renderKpiCard({ id: "IT2", label: "BD 占比", value: "58%", sub: "主贡献品类" })}
        ${renderKpiCard({ id: "IT3", label: "峰值站点", value: "Birdy Grey", sub: "32 款" })}
        ${renderKpiCard({ id: "IT4", label: "连续 3 周上涨", value: "4", sub: "品类信号" })}
      </section>
      ${pageFilters([
        { label: "周次范围", options: ["近 8 周", "近 12 周"] },
        { label: "业务线", options: ["全部", "BD", "AT", "MOB"] },
        { label: "品类", options: ["全部", "Bridesmaid", "Atelier"] },
      ])}
      <section class="page-split page-split--3">
        <article class="voc-panel">
          <h4>上新量趋势图</h4>
          ${pageSpark([78, 86, 92, 101, 110, 118, 122, 126])}
        </article>
        <article class="voc-panel">
          <h4>品类上新占比</h4>
          ${pageMiniBars([
            { name: "BD", value: 58, suffix: "%" },
            { name: "AT", value: 24, suffix: "%" },
            { name: "MOB", value: 12, suffix: "%" },
            { name: "WD", value: 6, suffix: "%" },
          ])}
        </article>
        <article class="voc-panel">
          <h4>竞品站点上新对比</h4>
          ${pageMiniBars([
            { name: "Birdy Grey", value: 32 },
            { name: "Revelry", value: 27 },
            { name: "JJ's House", value: 22 },
            { name: "Lulus", value: 18 },
            { name: "Show Me", value: 15 },
          ], "#7048e8")}
        </article>
      </section>
      ${pageTable(
        ["周次", "上新总量", "BD", "AT", "MOB", "环比", "备注"],
        [
          ["2026-W27", 126, 73, 30, 15, "+3.3%", "Sage / Burgundy 集中"],
          ["2026-W26", 122, 70, 28, 16, "+3.4%", "Satin 抬升"],
          ["2026-W25", 118, 66, 29, 14, "+7.3%", "Ball-Gown 增多"],
          ["2026-W24", 110, 61, 27, 13, "+8.9%", "—"],
        ]
          .map(
            (r) => `
          <tr>
            <td>${r[0]}</td>
            <td class="score-num">${r[1]}</td>
            <td>${r[2]}</td><td>${r[3]}</td><td>${r[4]}</td>
            <td>${r[5]}</td>
            <td>${r[6]}</td>
          </tr>
        `
          )
          .join(""),
        "周度上新明细",
        "按周汇总"
      )}
    </div>
  `;
}

/* ——— 属性分析 ——— */
function renderInsightAttr() {
  const dim = PAGE_UI.attrDim;
  const labels = {
    color: "颜色",
    silhouette: "廓形",
    neckline: "领型",
    fabric: "面料",
    design: "设计元素",
  };
  const rank = {
    color: [
      ["Dusty Sage", 188, 82, 76, "主力候选"],
      ["Burgundy", 156, 54, 72, "小测验证"],
      ["Champagne", 132, 46, 68, "小测验证"],
      ["Emerald", 98, 48, 81, "跟款机会"],
      ["Navy", 86, 74, 38, "保守维护"],
    ],
    silhouette: [
      ["A-Line", 210, 80, 70, "主力候选"],
      ["Mermaid", 148, 55, 74, "小测验证"],
      ["Sheath", 126, 62, 58, "跟款机会"],
      ["Ball-Gown", 92, 48, 81, "跟款机会"],
      ["Column", 71, 74, 35, "保守维护"],
    ],
    neckline: [
      ["Square Neck", 120, 78, 66, "主力候选"],
      ["Sweetheart", 101, 60, 62, "跟款机会"],
      ["One Shoulder", 88, 46, 68, "小测验证"],
      ["V-neck", 76, 70, 40, "保守维护"],
      ["Strapless", 64, 52, 55, "小测验证"],
    ],
    fabric: [
      ["Stretch Chiffon", 140, 81, 60, "主力候选"],
      ["Stretch Satin", 128, 58, 70, "小测验证"],
      ["Matte Satin", 96, 65, 52, "跟款机会"],
      ["Tulle", 72, 48, 75, "跟款机会"],
      ["Crepe", 58, 72, 36, "保守维护"],
    ],
    design: [
      ["Slit", 90, 50, 68, "小测验证"],
      ["Pockets", 84, 76, 42, "保守维护"],
      ["Bow", 66, 55, 58, "跟款机会"],
      ["Cape", 48, 44, 72, "小测验证"],
      ["Corset", 41, 48, 65, "跟款机会"],
    ],
  }[dim];

  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "IA1", label: "监控属性数", value: "86", sub: labels[dim] + " 维度" })}
        ${renderKpiCard({ id: "IA2", label: "双高属性", value: "12", sub: "Internal × Trend" })}
        ${renderKpiCard({ id: "IA3", label: "外热内弱", value: "19", sub: "需验证" })}
        ${renderKpiCard({ id: "IA4", label: "高风险属性", value: "7", sub: "退货关联" })}
      </section>
      ${pageFilters([
        { label: "业务线", options: ["BD", "AT", "MOB", "全部"] },
        { label: "品类", options: ["Bridesmaid Dresses", "Atelier", "全部"] },
        { label: "周次", options: ["2026-W27", "2026-W26"] },
      ])}
      <section class="card card-pad">
        ${pageTabs(
          [
            { id: "color", label: "颜色" },
            { id: "silhouette", label: "廓形" },
            { id: "neckline", label: "领型" },
            { id: "fabric", label: "面料" },
            { id: "design", label: "设计元素" },
          ],
          dim,
          "attrDim"
        )}
        <div class="page-split" style="margin-top:14px;">
          <article class="voc-panel">
            <h4>属性榜单 · ${labels[dim]}</h4>
            ${pageMiniBars(rank.map((r) => ({ name: r[0], value: r[1] })))}
          </article>
          <article class="voc-panel">
            <h4>属性四象限（示意）</h4>
            <div class="page-quad">
              <span class="page-quad__lab tl">外热内弱</span>
              <span class="page-quad__lab tr">双高机会</span>
              <span class="page-quad__lab bl">低优先级</span>
              <span class="page-quad__lab br">内部优势</span>
              ${rank
                .slice(0, 5)
                .map((r, i) => {
                  const left = 20 + (r[2] / 100) * 60;
                  const top = 70 - (r[3] / 100) * 50;
                  return `<i class="page-quad-dot" style="left:${left}%;top:${top}%;" title="${r[0]}"></i>`;
                })
                .join("")}
            </div>
          </article>
        </div>
        ${pageTable(
          [labels[dim], "样本量", "Internal Fit", "Gap Score", "建议动作", "操作"],
          rank
            .map(
              (r) => `
            <tr>
              <td><span class="cell-title">${r[0]}</span></td>
              <td class="score-num">${r[1]}</td>
              <td class="score-num">${r[2]}</td>
              <td class="score-num">${r[3]}</td>
              <td>${renderTag(r[4], ACTION_STYLE[r[4]]?.tag || "muted")}</td>
              <td><button type="button" class="btn-text" data-toast="voc-pool">加入机会池</button></td>
            </tr>
          `
            )
            .join(""),
          `${labels[dim]}属性明细`,
          "切换维度查看榜单与象限"
        )}
      </section>
    </div>
  `;
}

/* ——— 热榜 ——— */
function renderInsightRank() {
  const tab = PAGE_UI.hotTab;
  const tabs = pageTabs(
    [
      { id: "site", label: "站点热榜" },
      { id: "cat", label: "品类热榜" },
      { id: "move", label: "排名涨跌榜" },
    ],
    tab,
    "hotTab"
  );

  const tables = {
    site: {
      title: "站点热榜",
      headers: ["站点", "热度分", "上新数", "Top 商品", "环比", "操作"],
      rows: [
        ["Birdy Grey", 92, 32, "Dusty Sage Wrap", "+6", "查看"],
        ["Revelry", 88, 27, "Emerald Ball-Gown", "+4", "查看"],
        ["JJ's House", 81, 22, "Champagne Satin", "-2", "查看"],
        ["Show Me Yours", 76, 15, "Terracotta One Shoulder", "+5", "查看"],
      ],
    },
    cat: {
      title: "品类热榜",
      headers: ["品类", "热度分", "SKU 数", "代表属性", "环比", "操作"],
      rows: [
        ["Bridesmaid Dresses", 94, 186, "Dusty Sage · A-Line", "+5", "查看"],
        ["Atelier", 82, 94, "Champagne · Satin", "+3", "查看"],
        ["Mother of the Bride", 71, 58, "Navy · Column", "0", "查看"],
        ["Prom", 66, 41, "Slit · Metallic", "+8", "查看"],
      ],
    },
    move: {
      title: "排名涨跌榜",
      headers: ["商品", "站点", "上周", "本周", "涨跌", "操作"],
      rows: [
        ["Dusty Sage Wrap", "Birdy Grey", 12, 5, "+7", "加入机会池"],
        ["Emerald Ball-Gown", "Revelry", 15, 9, "+6", "加入机会池"],
        ["Champagne Satin", "JJ's House", 21, 28, "-7", "观察"],
        ["Navy Column", "Lulus", 34, "下架", "—", "加入避雷榜"],
      ],
    },
  }[tab];

  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "IR1", label: "监控站点", value: "8", sub: "核心雷达" })}
        ${renderKpiCard({ id: "IR2", label: "热榜条目", value: "160", sub: "本周快照" })}
        ${renderKpiCard({ id: "IR3", label: "上涨条目", value: "37", sub: "涨幅 ≥ 5" })}
        ${renderKpiCard({ id: "IR4", label: "下跌 / 下架", value: "19", sub: "含风险关联" })}
      </section>
      ${pageFilters([
        { label: "周次", options: ["2026-W27", "2026-W26"] },
        { label: "业务线", options: ["全部", "BD", "AT"] },
        { label: "品类", options: ["全部", "Bridesmaid", "Atelier"] },
      ])}
      <section class="card card-pad">
        ${tabs}
        ${pageTable(
          tables.headers,
          tables.rows
            .map(
              (r) => `
            <tr>
              ${r
                .slice(0, -1)
                .map((c, idx) => `<td>${idx === 0 ? `<span class="cell-title">${c}</span>` : c}</td>`)
                .join("")}
              <td><button type="button" class="btn-text" data-toast="${String(r[r.length - 1]).includes("避雷") ? "voc-risk" : "voc-pool"}">${r[r.length - 1]}</button></td>
            </tr>
          `
            )
            .join(""),
          tables.title,
          "热榜切片 · Demo 数据"
        )}
      </section>
    </div>
  `;
}

/* ——— 定价建议：按国家 + 轻量诊断 ——— */
const PRICING_COUNTRIES = [
  { id: "US", label: "美国", cur: "$", fx: 1.0 },
  { id: "UK", label: "英国", cur: "£", fx: 0.82 },
  { id: "CA", label: "加拿大", cur: "C$", fx: 1.35 },
  { id: "AU", label: "澳大利亚", cur: "A$", fx: 1.5 },
  { id: "DE", label: "德国", cur: "€", fx: 0.92 },
  { id: "FR", label: "法国", cur: "€", fx: 0.92 },
];

/** 基准（USD）；dumping 标记该主题在这些市场存在竞品异常低价（疑倾销） */
const PRICING_BASE = [
  { theme: "Dusty Sage · A-Line", compMedian: 95, compLow: 88, compHigh: 105, azPrice: 89, addToCartIdx: 1.12, dumping: [] },
  { theme: "Burgundy · Mermaid", compMedian: 118, compLow: 110, compHigh: 130, azPrice: 119, addToCartIdx: 1.0, dumping: [] },
  { theme: "Champagne · Satin", compMedian: 96, compLow: 85, compHigh: 105, azPrice: 109, addToCartIdx: 0.82, dumping: ["DE"] },
  { theme: "Emerald · Ball-Gown", compMedian: 132, compLow: 120, compHigh: 145, azPrice: 129, addToCartIdx: 1.06, dumping: [] },
  { theme: "Navy · Column", compMedian: 96, compLow: 88, compHigh: 112, azPrice: 98, addToCartIdx: 0.9, dumping: ["AU", "CA"] },
];

/** 价带分布（代表性，跨国一致；边界按币种换算） */
const PRICING_BANDS = { comp: [18, 42, 36, 21, 9], az: [22, 48, 28, 14, 5] };
const BAND_BOUNDS = [[60, 79], [80, 99], [100, 119], [120, 139], [140, null]];

function pricingCountry() {
  return PRICING_COUNTRIES.find((c) => c.id === PAGE_UI.pricingCountry) || PRICING_COUNTRIES[0];
}

function money(cur, n) {
  return `${cur}${Math.round(n)}`;
}

function buildPricingRows(country) {
  const k = PRICING_COUNTRIES.findIndex((c) => c.id === country.id);
  const fx = country.fx;
  return PRICING_BASE.map((b, i) => {
    const azTweak = 1 + (((k * 7 + i * 13) % 11) - 5) / 100; // -5%..+5% 市场差异
    const cartTweak = (((k + i) % 5) - 2) * 0.05;
    return {
      theme: b.theme,
      cur: country.cur,
      compMedian: Math.round(b.compMedian * fx),
      compLow: Math.round(b.compLow * fx),
      compHigh: Math.round(b.compHigh * fx),
      azPrice: Math.round(b.azPrice * fx * azTweak),
      addToCartIdx: Math.max(0.6, +(b.addToCartIdx + cartTweak).toFixed(2)),
      compLowFlag: (b.dumping || []).includes(country.id),
    };
  });
}

/** 轻量定价诊断：竞品价带中位 vs AZ现价 + 加购率相对价带均值 + 竞品倾销标记 */
function diagnosePricing(r) {
  const cur = r.cur;
  const diffPct = Math.round(((r.azPrice - r.compMedian) / r.compMedian) * 100);
  const cartPct = Math.round((r.addToCartIdx - 1) * 100);

  if (r.compLowFlag && r.azPrice >= r.compMedian) {
    return {
      tag: "竞品低价(不跟)",
      tone: "purple",
      action: "维持",
      suggest: r.azPrice,
      basis: `竞品中位 ${money(cur, r.compMedian)} 明显低于合理价带（疑低价倾销）→ 不建议跟价，维持 ${money(cur, r.azPrice)} 并强化差异化（面料/版型/服务）`,
    };
  }
  if (diffPct >= 6 && r.addToCartIdx < 0.95) {
    const s = Math.round(r.compMedian * 1.03);
    return {
      tag: "定价过高",
      tone: "orange",
      action: "下调",
      suggest: s,
      basis: `AZ ${money(cur, r.azPrice)} 高于竞品中位 ${money(cur, r.compMedian)}（+${diffPct}%）且加购率低于价带均值 ${Math.abs(cartPct)}% → 判定我方定价过高，建议下调至 ${money(cur, s)}`,
    };
  }
  if (diffPct <= -6 && r.addToCartIdx >= 1.05) {
    const s = Math.round(r.compMedian * 0.98);
    return {
      tag: "定价过低",
      tone: "blue",
      action: "上调",
      suggest: s,
      basis: `AZ ${money(cur, r.azPrice)} 低于竞品中位 ${money(cur, r.compMedian)}（${diffPct}%）且加购率高于均值 ${cartPct}% → 存在提价空间，建议上调至 ${money(cur, s)}`,
    };
  }
  return {
    tag: "合理",
    tone: "green",
    action: "维持",
    suggest: r.azPrice,
    basis: `AZ ${money(cur, r.azPrice)} 与竞品中位 ${money(cur, r.compMedian)} 基本一致、加购率正常 → 维持现价`,
  };
}

function pricingMedian(arr) {
  const s = [...arr].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : Math.round((s[m - 1] + s[m]) / 2);
}

function renderInsightPricing() {
  const country = pricingCountry();
  const cur = country.cur;
  const rows = buildPricingRows(country);
  const diags = rows.map((r) => diagnosePricing(r));

  const compMed = pricingMedian(rows.map((r) => r.compMedian));
  const azMed = pricingMedian(rows.map((r) => r.azPrice));
  const spread = azMed - compMed;
  const adjustCount = diags.filter((d) => d.action !== "维持").length;
  const avgCart = Math.round((rows.reduce((s, r) => s + r.addToCartIdx, 0) / rows.length - 1) * 100);

  const bandItems = (counts) =>
    BAND_BOUNDS.map((b, i) => {
      const lo = Math.round(b[0] * country.fx);
      const name = b[1] === null ? `${cur}${lo}+` : `${cur}${lo}-${Math.round(b[1] * country.fx)}`;
      return { name, value: counts[i] };
    });

  const countryTabs = pageTabs(
    PRICING_COUNTRIES.map((c) => ({ id: c.id, label: `${c.label} ${c.cur}` })),
    country.id,
    "pricingCountry"
  );

  return `
    <div class="page-stack">
      <section class="card card-pad">
        ${countryTabs}
        <p class="muted" style="margin:10px 0 0;">当前市场：${country.label} · 计价币种 ${cur} · 价格已按市场换算，诊断基于各市场竞品价带与本地加购率</p>
      </section>
      <section class="kpi-row kpi-row--5">
        ${renderKpiCard({ id: "IP1", label: "竞品中位价", value: money(cur, compMed), sub: `${country.label} · 同品类` })}
        ${renderKpiCard({ id: "IP2", label: "AZ 中位价", value: money(cur, azMed), sub: "同品类" })}
        ${renderKpiCard({ id: "IP3", label: "AZ−竞品价差", value: `${spread >= 0 ? "+" : ""}${money(cur, spread)}`, sub: spread > 0 ? "整体偏高" : spread < 0 ? "整体偏低" : "基本持平" })}
        ${renderKpiCard({ id: "IP4", label: "建议调价主题", value: String(adjustCount), sub: "过高 / 过低 / 需处置" })}
        ${renderKpiCard({ id: "IP5", label: "加购率对比", value: `${avgCart >= 0 ? "+" : ""}${avgCart}%`, sub: "相对价带均值" })}
      </section>
      ${pageFilters([
        { label: "业务线", options: ["BD", "AT", "全部"] },
        { label: "品类", options: ["Bridesmaid Dresses", "Atelier"] },
        { label: "颜色", options: ["全部", "Dusty Sage", "Burgundy"] },
      ])}
      <section class="page-split">
        <article class="voc-panel">
          <h4>竞品价格带分布 · ${country.label}</h4>
          ${pageMiniBars(bandItems(PRICING_BANDS.comp))}
        </article>
        <article class="voc-panel">
          <h4>AZ 当前价格带 · ${country.label}</h4>
          ${pageMiniBars(bandItems(PRICING_BANDS.az), "#0ca678")}
        </article>
      </section>
      <section class="card card-pad pricing-basis">
        <div class="card-head">
          <div>
            <h3>定价依据 · 计算方式（轻量模型）</h3>
            <p>用于判断「我方定价过高」还是「外部竞品定价过低」，并给出建议价</p>
          </div>
        </div>
        <ol class="pricing-basis__list">
          <li><strong>① 竞品价带中位 vs AZ 现价</strong>：计算价差百分比。AZ 高于中位 ≥6% 记为偏高，低于中位 ≥6% 记为偏低。</li>
          <li><strong>② 加购率相对价带均值</strong>：加购率低于均值说明高价抑制转化（支持「定价过高」），高于均值说明有提价空间（支持「定价过低」）。</li>
          <li><strong>③ 竞品价带异常低标记（倾销）</strong>：若竞品中位显著低于合理价带，判为外部低价倾销，不建议跟价，改走差异化。</li>
          <li><strong>建议价</strong>：向竞品中位靠拢（偏高下调、偏低上调），且不低于毛利下限（示意）；倾销市场维持现价。</li>
        </ol>
      </section>
      ${pageTable(
        ["机会主题", "竞品价带", "竞品中位", "AZ 现价", "加购率对比", "诊断", "建议价", "依据", "操作"],
        rows
          .map((r, i) => {
            const d = diags[i];
            const cartPct = Math.round((r.addToCartIdx - 1) * 100);
            return `
          <tr>
            <td><span class="cell-title">${r.theme}</span></td>
            <td>${money(cur, r.compLow)}-${money(cur, r.compHigh)}</td>
            <td>${money(cur, r.compMedian)}</td>
            <td>${money(cur, r.azPrice)}</td>
            <td class="${cartPct < 0 ? "score-down" : "score-up"}">${cartPct >= 0 ? "+" : ""}${cartPct}%</td>
            <td>${renderTag(d.tag, d.tone)}</td>
            <td><strong>${money(cur, d.suggest)}</strong></td>
            <td><span class="cell-sub" style="margin:0;display:inline;max-width:320px;">${d.basis}</span></td>
            <td><button type="button" class="btn-text" data-toast="price-apply">${d.action === "维持" ? "维持现价" : "应用建议"}</button></td>
          </tr>
        `;
          })
          .join(""),
        "分国家建议价与诊断",
        `${country.label} · 结合竞品价带、加购率与倾销标记生成`
      )}
    </div>
  `;
}

/* ——— 选品提案 ——— */
function renderProposalList() {
  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "PL1", label: "提案总数", value: "42", sub: "本季" })}
        ${renderKpiCard({ id: "PL2", label: "审核中", value: "9", sub: "待选款评审" })}
        ${renderKpiCard({ id: "PL3", label: "已通过", value: "18", sub: "可同步打样" })}
        ${renderKpiCard({ id: "PL4", label: "已驳回", value: "5", sub: "需回炉" })}
      </section>
      ${pageFilters([
        { label: "业务线", options: ["全部", "BD", "AT"] },
        { label: "状态", options: ["全部", "草稿", "审核中", "已通过", "已驳回"] },
        { label: "来源", options: ["全部", "机会池", "手工创建"] },
        { label: "关键词", type: "input", placeholder: "提案号 / 主题" },
      ], `<button type="button" class="btn btn-primary" data-route-jump="proposal-create">创建提案</button>
         <button type="button" class="btn btn-secondary" data-toast="export-csv">导出</button>`)}
      ${pageTable(
        ["提案号", "主题", "业务线", "来源", "状态", "更新时间", "操作"],
        [
          ["PR-2026-0812", "Dusty Sage · A-Line", "BD", "机会池", "审核中", "07-17 16:20"],
          ["PR-2026-0808", "Burgundy · Mermaid", "BD", "机会池", "已通过", "07-16 11:02"],
          ["PR-2026-0801", "Champagne Slit Gown", "AT", "手工创建", "草稿", "07-15 09:40"],
          ["PR-2026-0794", "Navy · Column", "MOB", "机会池", "已驳回", "07-14 18:12"],
        ]
          .map(
            (r) => `
          <tr>
            <td><span class="cell-title">${r[0]}</span></td>
            <td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td>
            <td>${renderTag(r[4], r[4] === "已通过" ? "green" : r[4] === "审核中" ? "orange" : r[4] === "已驳回" ? "red" : "muted")}</td>
            <td>${r[5]}</td>
            <td>
              <button type="button" class="btn-text" data-toast="sync-selection">同步选款</button>
              <button type="button" class="btn-text" data-toast="export-ppt">导出 PPT</button>
            </td>
          </tr>
        `
          )
          .join(""),
        "提案列表",
        "对齐选款管理系统"
      )}
    </div>
  `;
}

function renderProposalCreate() {
  return renderProposalCreateForm();
}

function renderProposalDraft() {
  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "PD1", label: "方案草案", value: "11", sub: "待确认" })}
        ${renderKpiCard({ id: "PD2", label: "可导出", value: "8", sub: "PPT / CSV" })}
        ${renderKpiCard({ id: "PD3", label: "已同步选款", value: "5", sub: "本周" })}
        ${renderKpiCard({ id: "PD4", label: "关联机会", value: "18", sub: "来自机会池" })}
      </section>
      ${pageTable(
        ["草案 ID", "主题", "来源机会", "建议动作", "状态", "操作"],
        [
          ["DR-0042", "Dusty Sage · A-Line", "SC-2026W27-BD-0042", "主力候选", "待提交"],
          ["DR-0043", "Burgundy · Mermaid", "SC-2026W27-BD-0043", "跟款机会", "已导出"],
          ["DR-0031", "Champagne · Satin", "SC-2026W27-AT-0031", "小测验证", "已同步"],
        ]
          .map(
            (r) => `
          <tr>
            <td><span class="cell-title">${r[0]}</span></td>
            <td>${r[1]}</td><td>${r[2]}</td>
            <td>${renderTag(r[3], ACTION_STYLE[r[3]]?.tag || "muted")}</td>
            <td>${r[4]}</td>
            <td>
              <button type="button" class="btn-text" data-toast="export-ppt">导出</button>
              <button type="button" class="btn-text" data-toast="sync-selection">同步选款</button>
              <button type="button" class="btn-text" data-toast="submit-scheme">提交</button>
            </td>
          </tr>
        `
          )
          .join(""),
        "方案草案列表",
        "中枢生成 · 可导出 · 可同步"
      )}
    </div>
  `;
}

function renderUsersPage(scope) {
  const title =
    scope === "listing"
      ? "自动刊登 · 用户管理"
      : scope === "proposal"
        ? "选品提案 · 用户管理"
        : "配置 · 用户管理";
  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "U1", label: "账号数", value: "28", sub: title })}
        ${renderKpiCard({ id: "U2", label: "启用中", value: "24", sub: "可登录" })}
        ${renderKpiCard({ id: "U3", label: "角色数", value: "6", sub: "运营 / 审核 / 管理员" })}
        ${renderKpiCard({ id: "U4", label: "本周变更", value: "3", sub: "启停 / 角色调整" })}
      </section>
      ${pageFilters([
        { label: "角色", options: ["全部", "品类运营", "选款审核", "刊登审核", "管理员"] },
        { label: "状态", options: ["全部", "启用", "停用"] },
        { label: "关键词", type: "input", placeholder: "姓名 / 邮箱" },
      ], `<button type="button" class="btn btn-primary" data-toast="user-add">新增用户</button>`)}
      ${pageTable(
        ["姓名", "邮箱", "角色", "业务线", "状态", "最近登录", "操作"],
        [
          ["Shelly", "shelly@azazie.com", "品类运营", "BD", "启用", "07-17 17:10"],
          ["Lucy", "lucy@azazie.com", "刊登审核", "ALL", "启用", "07-17 15:22"],
          ["Tom", "tom@azazie.com", "选款审核", "AT/BD", "启用", "07-16 09:01"],
          ["Amy", "amy@azazie.com", "品类运营", "AT", "停用", "06-30 11:18"],
        ]
          .map(
            (r) => `
          <tr>
            <td><span class="cell-title">${r[0]}</span></td>
            <td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td>
            <td>${renderTag(r[4], r[4] === "启用" ? "green" : "muted")}</td>
            <td>${r[5]}</td>
            <td>
              <button type="button" class="btn-text" data-toast="user-edit">编辑</button>
              <button type="button" class="btn-text" data-toast="user-toggle">${r[4] === "启用" ? "停用" : "启用"}</button>
            </td>
          </tr>
        `
          )
          .join(""),
        "用户列表",
        "账号 / 角色治理"
      )}
    </div>
  `;
}

/* ——— 自动刊登（内容见 listing.js） ——— */
function renderListingList() {
  return renderListingListPage();
}

function renderListingNew() {
  return renderListingNewPage();
}

function renderListingReview() {
  return renderListingReviewPage();
}

/* ——— 配置 ——— */
function renderCfgLine() {
  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "CL1", label: "业务线", value: "5", sub: "JP/BD/AT/WD/PROM" })}
        ${renderKpiCard({ id: "CL2", label: "授权用户", value: "24", sub: "启用中" })}
        ${renderKpiCard({ id: "CL3", label: "只读角色", value: "7", sub: "观察帐号" })}
        ${renderKpiCard({ id: "CL4", label: "本周变更", value: "2", sub: "权限调整" })}
      </section>
      ${pageTable(
        ["业务线", "负责人", "可读写", "只读", "状态", "操作"],
        [
          ["BD", "Shelly", 8, 3, "启用"],
          ["AT", "Amy", 5, 2, "启用"],
          ["WD", "Tom", 4, 1, "启用"],
          ["PROM", "Lucy", 3, 1, "启用"],
          ["JP", "—", 2, 0, "停用"],
        ]
          .map(
            (r) => `
          <tr>
            <td><span class="cell-title">${r[0]}</span></td>
            <td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td>
            <td>${renderTag(r[4], r[4] === "启用" ? "green" : "muted")}</td>
            <td><button type="button" class="btn-text" data-toast="cfg-save">编辑权限</button></td>
          </tr>
        `
          )
          .join(""),
        "业务线权限",
        "控制可见品类与操作范围"
      )}
    </div>
  `;
}

/* ——— 数据映射（tab 容器：属性字典映射 / 类目映射） ——— */
function renderCfgMapping() {
  const tab = PAGE_UI.mappingTab;
  const tabs = pageTabs(
    [
      { id: "dict", label: "属性字典映射" },
      { id: "category", label: "类目映射" },
    ],
    tab,
    "mappingTab"
  );
  const note =
    tab === "category"
      ? "类目映射：把竞品雷达的类目体系对齐到选款系统「品类」下拉，创建提案时可自动带出正确品类。"
      : "属性字典映射：把竞品/雷达原始属性值（颜色/廓形/领型/面料）归一到盘古 md_attribute_dict 标准值，保证机会池筛选、属性榜单与三信号交叉分析口径一致。";
  const body = tab === "category" ? renderCfgCategory() : renderCfgDict();

  return `
    <div class="mc-tabbar">${tabs}</div>
    <p class="muted" style="margin:-6px 2px 2px;">${note}</p>
    ${body}
  `;
}

function renderCfgDict() {
  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "CD1", label: "字典条目", value: "1,286", sub: "md_attribute_dict" })}
        ${renderKpiCard({ id: "CD2", label: "已映射", value: "1,102", sub: "85.7%" })}
        ${renderKpiCard({ id: "CD3", label: "待校准", value: "184", sub: "需人工确认" })}
        ${renderKpiCard({ id: "CD4", label: "本周新增", value: "26", sub: "竞品新属性" })}
      </section>
      ${pageFilters([
        { label: "维度", options: ["颜色", "廓形", "领型", "面料"] },
        { label: "状态", options: ["全部", "已映射", "待校准"] },
      ])}
      ${pageTable(
        ["竞品原始值", "维度", "盘古标准值", "映射状态", "操作"],
        [
          ["Dusty Sage", "颜色", "Dusty Sage", "已映射"],
          ["Sage Green", "颜色", "Dusty Sage", "待校准"],
          ["A Line", "廓形", "A-Line", "已映射"],
          ["Squareneck", "领型", "Square Neck", "待校准"],
          ["Chiffon Stretch", "面料", "Stretch Chiffon", "已映射"],
        ]
          .map(
            (r) => `
          <tr>
            <td><span class="cell-title">${r[0]}</span></td>
            <td>${r[1]}</td><td>${r[2]}</td>
            <td>${renderTag(r[3], r[3] === "已映射" ? "green" : "orange")}</td>
            <td><button type="button" class="btn-text" data-toast="cfg-save">保存映射</button></td>
          </tr>
        `
          )
          .join(""),
        "属性字典映射",
        "竞品值 → 盘古标准"
      )}
    </div>
  `;
}

function renderCfgWeight() {
  const weights = [
    { name: "Market Trend", value: 30 },
    { name: "Internal Fit", value: 30 },
    { name: "Gap Score", value: 25 },
    { name: "Risk Score", value: 15 },
  ];
  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "CW1", label: "权重之和", value: "100%", sub: "需恒等于 100" })}
        ${renderKpiCard({ id: "CW2", label: "当前版本", value: "v1.4", sub: "2026-W26 生效" })}
        ${renderKpiCard({ id: "CW3", label: "业务线差异", value: "2", sub: "BD / AT 分配置" })}
        ${renderKpiCard({ id: "CW4", label: "待发布", value: "1", sub: "草稿" })}
      </section>
      <section class="card card-pad">
        <div class="card-head">
          <div>
            <h3>打分权重</h3>
            <p>Trend / Internal / Gap / Risk</p>
          </div>
          <button type="button" class="btn btn-primary" data-toast="cfg-save">保存权重</button>
        </div>
        <div class="weight-list">
          ${weights
            .map(
              (w) => `
            <div class="weight-row">
              <strong>${w.name}</strong>
              <input type="range" min="0" max="50" value="${w.value}" />
              <span>${w.value}%</span>
            </div>
          `
            )
            .join("")}
        </div>
      </section>
    </div>
  `;
}

function renderCfgCategory() {
  return `
    <div class="page-stack">
      <section class="kpi-row">
        ${renderKpiCard({ id: "CC1", label: "雷达类目", value: "46", sub: "竞品侧" })}
        ${renderKpiCard({ id: "CC2", label: "选款品类", value: "22", sub: "系统侧" })}
        ${renderKpiCard({ id: "CC3", label: "已映射", value: "39", sub: "可下拉匹配" })}
        ${renderKpiCard({ id: "CC4", label: "未映射", value: "7", sub: "需补齐" })}
      </section>
      ${pageTable(
        ["雷达类目", "选款品类下拉", "业务线", "状态", "操作"],
        [
          ["Bridesmaid Dresses", "伴娘裙", "BD", "已映射"],
          ["Mother of the Bride", "妈妈装", "MOB", "已映射"],
          ["Atelier Formal", "晚宴礼服", "AT", "已映射"],
          ["Junior Bridesmaid", "Jr 伴娘", "BD", "待映射"],
          ["Flower Girl", "花童", "WD", "待映射"],
        ]
          .map(
            (r) => `
          <tr>
            <td><span class="cell-title">${r[0]}</span></td>
            <td>${r[1]}</td><td>${r[2]}</td>
            <td>${renderTag(r[3], r[3] === "已映射" ? "green" : "orange")}</td>
            <td><button type="button" class="btn-text" data-toast="cfg-save">编辑映射</button></td>
          </tr>
        `
          )
          .join(""),
        "类目映射",
        "雷达类目 → 选款品类下拉"
      )}
    </div>
  `;
}

const EXTRA_PAGE_RENDERERS = {
  "monitor-competitor": renderMonitorCompetitor,
  "insight-attr": renderInsightAttr,
  "insight-rank": renderInsightRank,
  "insight-pricing": renderInsightPricing,
  "proposal-list": renderProposalList,
  "proposal-create": renderProposalCreate,
  "proposal-draft": renderProposalDraft,
  "proposal-users": () => renderUsersPage("proposal"),
  "listing-list": renderListingList,
  "listing-new": renderListingNew,
  "listing-review": renderListingReview,
  "listing-users": () => renderUsersPage("listing"),
  "cfg-line": renderCfgLine,
  "cfg-mapping": renderCfgMapping,
  "cfg-weight": renderCfgWeight,
  "cfg-users": () => renderUsersPage("config"),
};

function renderExtraPage(routeId) {
  const fn = EXTRA_PAGE_RENDERERS[routeId];
  return fn ? fn() : null;
}

init();
