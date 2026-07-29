/**
 * 内部数据动态 · 内部数据选品建议引擎 Demo
 */

const INT_TABS = [
  { id: "attr", label: "属性钻取" },
  { id: "recs", label: "建议清单" },
  { id: "trace", label: "明细追溯" },
];

const INT_ATTR_DIMS = [
  { id: "color", label: "颜色" },
  { id: "silhouette", label: "廓形" },
  { id: "back", label: "后背款式" },
  { id: "fabric", label: "面料" },
  { id: "hem", label: "裙摆/拖尾" },
  { id: "neckline", label: "领型" },
  { id: "sleeve", label: "袖型" },
  { id: "combo", label: "属性组合" },
];

const INT_QUAD_STYLE = {
  成熟优势: "green",
  重点机会: "purple",
  风险冗余: "red",
  低优先级: "muted",
};

const INT_ATTR_ROWS = [
  {
    id: "attr-charcoal",
    rank: 1,
    name: "Charcoal",
    quad: "成熟优势",
    fit: 90.5,
    sales: 4101,
    revenue: "$969,956",
    sellThrough: "78.8%",
    addCart: "18.2%",
    wish: "11.1%",
    returnRate: "11.6%",
    skc: 30,
    trend: "+22.0%",
    action: "维持规模",
    goods: [
      { id: "980112", name: "Charcoal A-Line Chiffon", color: "Charcoal", sil: "A-Line", fabric: "Chiffon", sales: 612, rev: "$142k", add: "19%", wish: "12%", ret: "10%" },
      { id: "980188", name: "Charcoal Mermaid Satin", color: "Charcoal", sil: "Mermaid", fabric: "Satin", sales: 488, rev: "$128k", add: "17%", wish: "11%", ret: "13%" },
    ],
  },
  {
    id: "attr-navy",
    rank: 2,
    name: "Navy",
    quad: "成熟优势",
    fit: 87.9,
    sales: 3789,
    revenue: "$744,144",
    sellThrough: "74.2%",
    addCart: "16.8%",
    wish: "10.4%",
    returnRate: "12.1%",
    skc: 17,
    trend: "+39.5%",
    action: "维持规模",
    goods: [
      { id: "970221", name: "Navy Column Crepe", color: "Navy", sil: "Column", fabric: "Crepe", sales: 540, rev: "$98k", add: "15%", wish: "9%", ret: "11%" },
    ],
  },
  {
    id: "attr-ivory",
    rank: 3,
    name: "Ivory",
    quad: "重点机会",
    fit: 86.0,
    sales: 4370,
    revenue: "$1,067,999",
    sellThrough: "81.0%",
    addCart: "15.6%",
    wish: "12.8%",
    returnRate: "9.2%",
    skc: 7,
    trend: "+18.4%",
    action: "增加覆盖",
    goods: [
      { id: "960301", name: "Ivory Ball-Gown Tulle", color: "Ivory", sil: "Ball-Gown", fabric: "Tulle", sales: 820, rev: "$210k", add: "16%", wish: "14%", ret: "8%" },
    ],
  },
  {
    id: "attr-sage",
    rank: 4,
    name: "Sage",
    quad: "重点机会",
    fit: 79.8,
    sales: 4217,
    revenue: "$970,432",
    sellThrough: "76.5%",
    addCart: "14.2%",
    wish: "9.8%",
    returnRate: "6.4%",
    skc: 2,
    trend: "+10.8%",
    action: "增加覆盖",
    goods: [
      { id: "950410", name: "Sage A-Line Chiffon", color: "Sage", sil: "A-Line", fabric: "Chiffon", sales: 2410, rev: "$540k", add: "14%", wish: "10%", ret: "6%" },
      { id: "950411", name: "Sage A-Line Satin", color: "Sage", sil: "A-Line", fabric: "Satin", sales: 1807, rev: "$430k", add: "14%", wish: "9%", ret: "7%" },
    ],
  },
  {
    id: "attr-burgundy",
    rank: 5,
    name: "Burgundy",
    quad: "重点机会",
    fit: 78.2,
    sales: 2980,
    revenue: "$712,400",
    sellThrough: "69.4%",
    addCart: "13.8%",
    wish: "9.1%",
    returnRate: "8.8%",
    skc: 5,
    trend: "+15.2%",
    action: "增加覆盖",
    goods: [],
  },
  {
    id: "attr-champagne",
    rank: 6,
    name: "Champagne",
    quad: "成熟优势",
    fit: 84.1,
    sales: 3510,
    revenue: "$802,100",
    sellThrough: "72.0%",
    addCart: "15.1%",
    wish: "10.0%",
    returnRate: "10.3%",
    skc: 14,
    trend: "+8.6%",
    action: "维持规模",
    goods: [],
  },
  {
    id: "attr-white",
    rank: 7,
    name: "White",
    quad: "风险冗余",
    fit: 48.2,
    sales: 2650,
    revenue: "$510,220",
    sellThrough: "55.0%",
    addCart: "11.2%",
    wish: "7.4%",
    returnRate: "24.8%",
    skc: 21,
    trend: "-6.4%",
    action: "风险提示",
    goods: [],
  },
  {
    id: "attr-blush",
    rank: 8,
    name: "Blush",
    quad: "低优先级",
    fit: 58.6,
    sales: 1120,
    revenue: "$198,400",
    sellThrough: "41.2%",
    addCart: "8.6%",
    wish: "5.2%",
    returnRate: "14.0%",
    skc: 9,
    trend: "-2.1%",
    action: "收缩观察",
    goods: [],
  },
];

const INT_RECS = [
  {
    id: "REC-2026-001",
    title: "扩展 Sage 色系在 A-Line 礼服中的覆盖",
    dim: "颜色",
    value: "Sage",
    quad: "重点机会",
    priority: "高",
    fit: 79.8,
    skc: 2,
    status: "待讨论",
    owner: "未分配",
    updated: "2026-07-18",
    desc: "Sage 在近 30 天内销量增长 10.8%，内部适配度达到 80，但当前仅覆盖 2 个 SKC。建议优先在 A-Line 和 Chiffon 商品中补充 3-5 个关联款。",
    metrics: [
      { label: "内部适配度", value: "79.8", avg: "品类均值：65.6", delta: "+14.2", good: true },
      { label: "销量", value: "4,217", avg: "品类均值：2,917", delta: "+1,300", good: true },
      { label: "销售额", value: "$970,432", avg: "品类均值：$576,906", delta: "+$393,526", good: true },
      { label: "加购率", value: "14.2%", avg: "品类均值：12.8%", delta: "+1.4%", good: true },
      { label: "收藏率", value: "9.8%", avg: "品类均值：8.6%", delta: "+1.2%", good: true },
      { label: "退货率", value: "6.4%", avg: "品类均值：13.8%", delta: "-7.4%", good: true },
    ],
    goods: [
      { id: "950410", name: "Sage A-Line Chiffon", color: "Sage", sil: "A-Line", fabric: "Chiffon", sales: 2410, rev: "$540,120", add: "14.2%", wish: "10.1%", ret: "6.1%" },
      { id: "950411", name: "Sage A-Line Satin", color: "Sage", sil: "A-Line", fabric: "Satin", sales: 1807, rev: "$430,312", add: "14.0%", wish: "9.4%", ret: "6.8%" },
    ],
    returns: [
      { reason: "尺码不合适", count: 86, share: "38%", high: false },
      { reason: "图货差异", count: 42, share: "19%", high: false },
      { reason: "面料手感不达预期", count: 31, share: "14%", high: false },
      { reason: "物流破损", count: 18, share: "8%", high: true },
    ],
    behavior: { pv: "128,420", cart: "18,240", wish: "12,560", cvr: "3.28%", wow: "+6.4%" },
  },
  {
    id: "REC-2026-008",
    title: "增加 Puff Sleeve + Satin 关联款",
    dim: "属性组合",
    value: "Puff Sleeve + Satin",
    quad: "重点机会",
    priority: "高",
    fit: 88.9,
    skc: 7,
    status: "已采纳",
    owner: "Marcus Lee",
    updated: "2026-07-18",
    desc: "Puff Sleeve + Satin 组合适配度高且退货可控，建议在 AT/BD 同步增加关联款覆盖。",
    metrics: [
      { label: "内部适配度", value: "88.9", avg: "品类均值：65.6", delta: "+23.3", good: true },
      { label: "销量", value: "3,120", avg: "品类均值：2,917", delta: "+203", good: true },
      { label: "销售额", value: "$682,100", avg: "品类均值：$576,906", delta: "+$105k", good: true },
      { label: "加购率", value: "16.4%", avg: "品类均值：12.8%", delta: "+3.6%", good: true },
      { label: "收藏率", value: "11.2%", avg: "品类均值：8.6%", delta: "+2.6%", good: true },
      { label: "退货率", value: "9.1%", avg: "品类均值：13.8%", delta: "-4.7%", good: true },
    ],
    goods: [
      { id: "940801", name: "Puff Sleeve Satin Midi", color: "Champagne", sil: "Sheath", fabric: "Satin", sales: 980, rev: "$210k", add: "17%", wish: "12%", ret: "9%" },
    ],
    returns: [
      { reason: "袖型不满意", count: 40, share: "28%", high: true },
      { reason: "尺码偏小", count: 36, share: "25%", high: false },
    ],
    behavior: { pv: "86,200", cart: "14,120", wish: "9,660", cvr: "3.61%", wow: "+4.2%" },
  },
  {
    id: "REC-2026-017",
    title: "排查 Chapel Train 裙摆/拖尾的退货风险",
    dim: "裙摆/拖尾",
    value: "Chapel Train",
    quad: "风险冗余",
    priority: "高",
    fit: 42.9,
    skc: 19,
    status: "已拒绝",
    owner: "Kevin Wu",
    updated: "2026-07-17",
    desc: "Chapel Train 覆盖较广但退货率显著高于品类均值，建议收缩高风险 SKC 并复核模特图/尺码表。",
    metrics: [
      { label: "内部适配度", value: "42.9", avg: "品类均值：65.6", delta: "-22.7", good: false },
      { label: "销量", value: "2,140", avg: "品类均值：2,917", delta: "-777", good: false },
      { label: "销售额", value: "$410,200", avg: "品类均值：$576,906", delta: "-$166k", good: false },
      { label: "加购率", value: "9.2%", avg: "品类均值：12.8%", delta: "-3.6%", good: false },
      { label: "收藏率", value: "6.1%", avg: "品类均值：8.6%", delta: "-2.5%", good: false },
      { label: "退货率", value: "28.4%", avg: "品类均值：13.8%", delta: "+14.6%", good: false },
    ],
    goods: [
      { id: "930170", name: "Chapel Train Lace", color: "Ivory", sil: "A-Line", fabric: "Lace", sales: 410, rev: "$92k", add: "8%", wish: "5%", ret: "31%" },
    ],
    returns: [
      { reason: "拖尾易脏/破损", count: 120, share: "42%", high: true },
      { reason: "尺码不合适", count: 68, share: "24%", high: false },
    ],
    behavior: { pv: "52,100", cart: "4,780", wish: "3,180", cvr: "1.92%", wow: "-3.8%" },
  },
  {
    id: "REC-2026-020",
    title: "维持 Lace 的现有选款规模",
    dim: "面料",
    value: "Lace",
    quad: "成熟优势",
    priority: "低",
    fit: 90.1,
    skc: 23,
    status: "待讨论",
    owner: "未分配",
    updated: "2026-07-16",
    desc: "Lace 内部表现成熟稳定，建议维持现有覆盖，不主动扩款。",
    metrics: [
      { label: "内部适配度", value: "90.1", avg: "品类均值：65.6", delta: "+24.5", good: true },
      { label: "销量", value: "5,020", avg: "品类均值：2,917", delta: "+2,103", good: true },
      { label: "销售额", value: "$1.12M", avg: "品类均值：$576,906", delta: "+$", good: true },
      { label: "加购率", value: "17.8%", avg: "品类均值：12.8%", delta: "+5.0%", good: true },
      { label: "收藏率", value: "12.4%", avg: "品类均值：8.6%", delta: "+3.8%", good: true },
      { label: "退货率", value: "10.2%", avg: "品类均值：13.8%", delta: "-3.6%", good: true },
    ],
    goods: [],
    returns: [],
    behavior: { pv: "160,000", cart: "28,400", wish: "19,800", cvr: "3.14%", wow: "+1.2%" },
  },
  {
    id: "REC-2026-018",
    title: "维持 Strapless 的现有选款规模",
    dim: "领型",
    value: "Strapless",
    quad: "成熟优势",
    priority: "低",
    fit: 91.8,
    skc: 22,
    status: "观察中",
    owner: "Shelly",
    updated: "2026-07-16",
    desc: "Strapless 适配度高且覆盖充分，建议维持规模并持续观察季节波动。",
    metrics: [
      { label: "内部适配度", value: "91.8", avg: "品类均值：65.6", delta: "+26.2", good: true },
      { label: "销量", value: "4,880", avg: "品类均值：2,917", delta: "+1,963", good: true },
      { label: "销售额", value: "$1.05M", avg: "品类均值：$576,906", delta: "+$", good: true },
      { label: "加购率", value: "18.1%", avg: "品类均值：12.8%", delta: "+5.3%", good: true },
      { label: "收藏率", value: "12.9%", avg: "品类均值：8.6%", delta: "+4.3%", good: true },
      { label: "退货率", value: "11.0%", avg: "品类均值：13.8%", delta: "-2.8%", good: true },
    ],
    goods: [],
    returns: [],
    behavior: { pv: "142,000", cart: "25,700", wish: "18,300", cvr: "3.44%", wow: "+0.8%" },
  },
  {
    id: "REC-2026-011",
    title: "扩展 Mini Hem 裙摆/拖尾的商品覆盖",
    dim: "裙摆/拖尾",
    value: "Mini Hem",
    quad: "重点机会",
    priority: "高",
    fit: 88.1,
    skc: 2,
    status: "待讨论",
    owner: "未分配",
    updated: "2026-07-15",
    desc: "Mini Hem 适配度高但覆盖极薄，建议补充短礼服场景覆盖。",
    metrics: [
      { label: "内部适配度", value: "88.1", avg: "品类均值：65.6", delta: "+22.5", good: true },
      { label: "销量", value: "1,860", avg: "品类均值：2,917", delta: "-1,057", good: false },
      { label: "销售额", value: "$320,400", avg: "品类均值：$576,906", delta: "-$", good: false },
      { label: "加购率", value: "15.9%", avg: "品类均值：12.8%", delta: "+3.1%", good: true },
      { label: "收藏率", value: "11.0%", avg: "品类均值：8.6%", delta: "+2.4%", good: true },
      { label: "退货率", value: "7.8%", avg: "品类均值：13.8%", delta: "-6.0%", good: true },
    ],
    goods: [],
    returns: [],
    behavior: { pv: "41,200", cart: "6,540", wish: "4,520", cvr: "4.51%", wow: "+9.2%" },
  },
  {
    id: "REC-2026-002",
    title: "精简高退货率的 Off-Shoulder Satin 款式",
    dim: "属性组合",
    value: "Off-Shoulder + Satin",
    quad: "风险冗余",
    priority: "高",
    fit: 43.0,
    skc: 22,
    status: "待讨论",
    owner: "Marcus Lee",
    updated: "2026-07-15",
    desc: "该组合覆盖过密但退货偏高，建议精简低动销高退货 SKC。",
    metrics: [
      { label: "内部适配度", value: "43.0", avg: "品类均值：65.6", delta: "-22.6", good: false },
      { label: "销量", value: "2,560", avg: "品类均值：2,917", delta: "-357", good: false },
      { label: "销售额", value: "$498,000", avg: "品类均值：$576,906", delta: "-$", good: false },
      { label: "加购率", value: "10.1%", avg: "品类均值：12.8%", delta: "-2.7%", good: false },
      { label: "收藏率", value: "6.8%", avg: "品类均值：8.6%", delta: "-1.8%", good: false },
      { label: "退货率", value: "26.2%", avg: "品类均值：13.8%", delta: "+12.4%", good: false },
    ],
    goods: [],
    returns: [
      { reason: "容易滑落", count: 150, share: "36%", high: true },
      { reason: "图货不一致", count: 88, share: "21%", high: true },
    ],
    behavior: { pv: "72,800", cart: "7,360", wish: "4,950", cvr: "1.85%", wow: "-5.1%" },
  },
  {
    id: "REC-2026-003",
    title: "增加 Square Neck + Chiffon 关联款",
    dim: "属性组合",
    value: "Square Neck + Chiffon",
    quad: "重点机会",
    priority: "中",
    fit: 70.5,
    skc: 5,
    status: "观察中",
    owner: "Shelly",
    updated: "2026-07-14",
    desc: "该组合适配度中上、覆盖不足，建议小批量扩款并验证 Fit。",
    metrics: [
      { label: "内部适配度", value: "70.5", avg: "品类均值：65.6", delta: "+4.9", good: true },
      { label: "销量", value: "2,420", avg: "品类均值：2,917", delta: "-497", good: false },
      { label: "销售额", value: "$455,000", avg: "品类均值：$576,906", delta: "-$", good: false },
      { label: "加购率", value: "13.4%", avg: "品类均值：12.8%", delta: "+0.6%", good: true },
      { label: "收藏率", value: "8.9%", avg: "品类均值：8.6%", delta: "+0.3%", good: true },
      { label: "退货率", value: "9.6%", avg: "品类均值：13.8%", delta: "-4.2%", good: true },
    ],
    goods: [],
    returns: [],
    behavior: { pv: "58,400", cart: "7,820", wish: "5,200", cvr: "2.94%", wow: "+3.1%" },
  },
];

let intState = {
  tab: "recs",
  attrDim: "color",
  drawerAttrId: null,
  selectedRecId: "REC-2026-001",
  trendMetric: "sales",
};

function intGetRec(id) {
  return INT_RECS.find((r) => r.id === id) || INT_RECS[0];
}

function intGetAttr(id) {
  return INT_ATTR_ROWS.find((a) => a.id === id) || INT_ATTR_ROWS[0];
}

function intStatusTone(status) {
  if (status === "已采纳") return "green";
  if (status === "已拒绝") return "red";
  if (status === "观察中") return "orange";
  if (status === "待讨论") return "blue";
  return "muted";
}

function intPriorityTone(p) {
  if (p === "高") return "red";
  if (p === "中") return "orange";
  return "muted";
}

function intTrendTone(trend) {
  return String(trend).startsWith("-") ? "red" : "green";
}

function renderIntGlobalFilters() {
  return `
    <section class="filter-card int-global-filters">
      <div class="filter-grid filter-grid--5">
        <div class="field"><label>时间</label><select><option>近30天</option><option>近7天</option><option>近90天</option></select></div>
        <div class="field"><label>站点</label><select><option>US</option><option>CA</option><option>GB</option><option>AU</option></select></div>
        <div class="field"><label>品类</label><select><option>Wedding Dresses</option><option>Bridesmaid Dresses</option><option>Atelier</option></select></div>
        <div class="field"><label>范围</label><select><option>全部</option><option>仅在售</option><option>含归档</option></select></div>
        <div class="field int-filter-actions">
          <label>&nbsp;</label>
          <button type="button" class="btn btn-secondary" data-toast="refresh">刷新</button>
        </div>
      </div>
    </section>
  `;
}

function renderIntTrendSpark(metric) {
  const series = {
    sales: [2800, 2950, 3100, 3050, 3320, 3480, 3600, 3720, 3900, 4010, 4120, 4217],
    cart: [11.2, 11.5, 11.8, 12.0, 12.4, 12.6, 12.9, 13.1, 13.4, 13.6, 13.9, 14.2],
    wish: [7.8, 8.0, 8.1, 8.3, 8.5, 8.6, 8.8, 9.0, 9.2, 9.4, 9.6, 9.8],
    return: [8.2, 8.0, 7.8, 7.6, 7.4, 7.2, 7.0, 6.9, 6.8, 6.7, 6.5, 6.4],
  }[metric] || [];
  const max = Math.max(...series);
  const min = Math.min(...series);
  const w = 560;
  const h = 160;
  const pad = 16;
  const step = (w - pad * 2) / (series.length - 1);
  const pts = series
    .map((v, i) => {
      const x = pad + i * step;
      const y = h - 24 - ((v - min) / (max - min || 1)) * (h - 48);
      return `${x},${y}`;
    })
    .join(" ");
  return `
    <svg viewBox="0 0 ${w} ${h}" class="int-trend-svg" role="img" aria-label="近12周趋势">
      <polyline fill="none" stroke="#7048e8" stroke-width="2.5" points="${pts}" />
      ${pts
        .split(" ")
        .map((p) => {
          const [x, y] = p.split(",");
          return `<circle cx="${x}" cy="${y}" r="3.2" fill="#7048e8" />`;
        })
        .join("")}
    </svg>
  `;
}

function renderIntAttrTab() {
  return `
    <div class="int-tab-body">
      <div class="page-tabs int-dim-tabs">
        ${INT_ATTR_DIMS.map(
          (d) => `
          <button type="button" class="page-tab${intState.attrDim === d.id ? " is-active" : ""}" data-int-dim="${d.id}">${d.label}</button>
        `
        ).join("")}
      </div>

      <section class="filter-card">
        <div class="filter-grid filter-grid--6">
          <div class="field"><label>搜索属性值</label><input type="text" placeholder="如 Sage / Navy" /></div>
          <div class="field"><label>象限</label><select><option>全部</option><option>成熟优势</option><option>重点机会</option><option>风险冗余</option><option>低优先级</option></select></div>
          <div class="field"><label>趋势方向</label><select><option>全部</option><option>上升</option><option>下降</option><option>稳定</option></select></div>
          <div class="field"><label>最低适配度</label><input type="text" placeholder="如 70" value="70" /></div>
          <div class="field"><label>最高退货率</label><input type="text" placeholder="如 20%" value="20%" /></div>
          <div class="field"><label>最低销量</label><input type="text" placeholder="如 1000" /></div>
          <div class="field"><label>排序方式</label><select><option>内部适配度从高到低</option><option>销量从高到低</option><option>退货率从高到低</option></select></div>
        </div>
        <div class="filter-actions filter-actions--bar">
          <button type="button" class="btn btn-secondary" data-toast="refresh">重置筛选</button>
          <button type="button" class="btn btn-secondary" data-toast="export-csv">导出 CSV</button>
        </div>
      </section>

      <section class="table-card">
        <div class="table-toolbar">
          <div>
            <h3>属性表现表 · ${INT_ATTR_DIMS.find((d) => d.id === intState.attrDim)?.label || "颜色"}</h3>
            <p>共 ${INT_ATTR_ROWS.length} 条 · 点击属性值或详情打开抽屉</p>
          </div>
        </div>
        <div class="table-wrap">
          <table class="data-table int-dense-table">
            <thead>
              <tr>
                <th>排名</th><th>属性值</th><th>象限</th><th>内部适配度</th><th>销量</th><th>销售额</th>
                <th>动销率</th><th>加购率</th><th>收藏率</th><th>退货率</th><th>覆盖 SKC</th><th>近 30 天趋势</th><th>详情</th>
              </tr>
            </thead>
            <tbody>
              ${INT_ATTR_ROWS.map(
                (r) => `
                <tr data-int-attr-row="${r.id}">
                  <td class="score-num">${r.rank}</td>
                  <td><button type="button" class="btn-text cell-title" data-int-drawer="${r.id}">${r.name}</button></td>
                  <td>${renderTag(r.quad, INT_QUAD_STYLE[r.quad] || "muted")}</td>
                  <td class="score-num">${r.fit}</td>
                  <td class="score-num">${r.sales.toLocaleString()}</td>
                  <td>${r.revenue}</td>
                  <td>${r.sellThrough}</td>
                  <td>${r.addCart}</td>
                  <td>${r.wish}</td>
                  <td>${r.returnRate}</td>
                  <td>${r.skc} 个</td>
                  <td>${renderTag(r.trend, intTrendTone(r.trend))}</td>
                  <td><button type="button" class="btn-text" data-int-drawer="${r.id}">详情</button></td>
                </tr>
              `
              ).join("")}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `;
}

function renderIntRecsTab() {
  return `
    <div class="int-tab-body">
      <div class="card-head" style="margin-bottom:4px;">
        <div>
          <h3 style="margin:0;font-size:16px;">内部选品建议清单</h3>
          <p style="margin:4px 0 0;color:var(--text-soft);font-size:12px;">将内部数据中的机会和风险转化为可讨论、可追溯的结构化选品建议。</p>
        </div>
      </div>

      <section class="filter-card">
        <div class="filter-grid filter-grid--6">
          <div class="field"><label>搜索</label><input type="text" placeholder="搜索建议标题或属性值" /></div>
          <div class="field"><label>建议状态</label><select><option>全部</option><option>待讨论</option><option>已采纳</option><option>已拒绝</option><option>观察中</option></select></div>
          <div class="field"><label>建议类型</label><select><option>全部</option><option>增加覆盖</option><option>维持规模</option><option>风险提示</option><option>收缩观察</option></select></div>
          <div class="field"><label>象限</label><select><option>全部</option><option>重点机会</option><option>成熟优势</option><option>风险冗余</option></select></div>
          <div class="field"><label>属性维度</label><select><option>全部</option><option>颜色</option><option>廓形</option><option>面料</option><option>领型</option><option>属性组合</option></select></div>
          <div class="field"><label>优先级</label><select><option>全部</option><option>高</option><option>中</option><option>低</option></select></div>
          <div class="field"><label>负责人</label><select><option>全部</option><option>未分配</option><option>Marcus Lee</option><option>Kevin Wu</option><option>Shelly</option></select></div>
        </div>
        <div class="filter-actions filter-actions--bar">
          <button type="button" class="btn btn-secondary" data-toast="refresh">重置筛选</button>
          <button type="button" class="btn btn-secondary" data-toast="export-csv">导出 CSV</button>
        </div>
      </section>

      <section class="table-card">
        <div class="table-toolbar">
          <div>
            <h3>建议列表</h3>
            <p>共 ${INT_RECS.length} 条 · 点击整行进入明细追溯</p>
          </div>
        </div>
        <div class="table-wrap">
          <table class="data-table int-dense-table">
            <thead>
              <tr>
                <th>建议编号</th><th>建议标题</th><th>属性维度</th><th>属性值/组合</th><th>象限</th>
                <th>优先级</th><th>适配度</th><th>覆盖 SKC</th><th>状态</th><th>负责人</th><th>更新时间</th><th>操作</th>
              </tr>
            </thead>
            <tbody>
              ${INT_RECS.map(
                (r) => `
                <tr class="int-rec-row" data-int-trace="${r.id}">
                  <td><span class="cell-title">${r.id}</span></td>
                  <td><span class="cell-title">${r.title}</span></td>
                  <td>${r.dim}</td>
                  <td>${r.value}</td>
                  <td>${renderTag(r.quad, INT_QUAD_STYLE[r.quad] || "muted")}</td>
                  <td>${renderTag(r.priority, intPriorityTone(r.priority))}</td>
                  <td class="score-num">${r.fit}</td>
                  <td>${r.skc} 个</td>
                  <td>${renderTag(r.status, intStatusTone(r.status))}</td>
                  <td>${r.owner}</td>
                  <td>${r.updated}</td>
                  <td>
                    <div class="row-actions" onclick="event.stopPropagation()">
                      <button type="button" class="btn-text" data-int-trace="${r.id}">查看明细</button>
                      <button type="button" class="btn-text" data-toast="int-draft" data-case="${r.id}">生成方案草案</button>
                      <button type="button" class="btn-text" data-toast="voc-pool" data-case="${r.id}">加入机会池</button>
                      <button type="button" class="btn-text" data-toast="int-adopt" data-case="${r.id}">标记已采纳</button>
                      <button type="button" class="btn-text" data-toast="int-reject" data-case="${r.id}">标记已拒绝</button>
                    </div>
                  </td>
                </tr>
              `
              ).join("")}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `;
}

function renderIntTraceTab() {
  const rec = intGetRec(intState.selectedRecId);
  return `
    <div class="int-tab-body">
      <section class="int-trace-layout">
        <aside class="int-trace-list voc-panel">
          <div class="field" style="margin-bottom:12px;">
            <label>搜索建议</label>
            <input type="text" placeholder="搜索建议标题或属性" />
          </div>
          <div class="int-rec-cards">
            ${INT_RECS.map(
              (r) => `
              <button type="button" class="int-rec-card${intState.selectedRecId === r.id ? " is-active" : ""}" data-int-select-rec="${r.id}">
                <strong>${r.title}</strong>
                <div class="int-rec-card__meta">
                  ${renderTag(r.status, intStatusTone(r.status))}
                  ${renderTag(r.quad, INT_QUAD_STYLE[r.quad] || "muted")}
                  ${renderTag(r.priority, intPriorityTone(r.priority))}
                </div>
                <span class="muted">${r.id} · ${r.updated}</span>
              </button>
            `
            ).join("")}
          </div>
        </aside>

        <div class="int-trace-detail">
          <section class="card card-pad">
            <div class="detail-hero">
              <div>
                <p class="muted">${rec.id}</p>
                <h2 style="margin:6px 0 10px;font-size:20px;">${rec.title}</h2>
                <div>
                  ${renderTag(rec.quad, INT_QUAD_STYLE[rec.quad] || "muted")}
                  ${renderTag(`优先级 ${rec.priority}`, intPriorityTone(rec.priority))}
                  ${renderTag(rec.status, intStatusTone(rec.status))}
                  <span class="tag tag--muted">负责人 ${rec.owner}</span>
                </div>
                <p style="margin:14px 0 0;color:var(--text-soft);line-height:1.65;max-width:820px;">${rec.desc}</p>
              </div>
              <div class="filter-actions" style="flex-direction:column;align-items:stretch;">
                <button type="button" class="btn btn-primary" data-toast="int-draft" data-case="${rec.id}">生成方案草案</button>
                <button type="button" class="btn btn-secondary" data-toast="voc-pool" data-case="${rec.id}">加入机会池</button>
                <button type="button" class="btn btn-secondary" data-toast="export-csv">导出追溯明细</button>
              </div>
            </div>
          </section>

          <section class="int-metric-grid">
            ${rec.metrics
              .map(
                (m) => `
              <article class="int-metric-card">
                <span>${m.label}</span>
                <strong>${m.value}</strong>
                <em>${m.avg}</em>
                <b class="${m.good ? "is-up" : "is-down"}">差值 ${m.delta}</b>
              </article>
            `
              )
              .join("")}
          </section>

          <section class="voc-panel">
            <div class="card-head">
              <div>
                <h4 style="margin:0;">趋势分析 · 近 12 周</h4>
                <p style="margin:4px 0 0;font-size:12px;color:var(--text-soft);">切换指标查看走势</p>
              </div>
            </div>
            <div class="voc-grain" style="margin:10px 0;">
              <button type="button" class="voc-grain-btn${intState.trendMetric === "sales" ? " is-active" : ""}" data-int-metric="sales">销量</button>
              <button type="button" class="voc-grain-btn${intState.trendMetric === "cart" ? " is-active" : ""}" data-int-metric="cart">加购率</button>
              <button type="button" class="voc-grain-btn${intState.trendMetric === "wish" ? " is-active" : ""}" data-int-metric="wish">收藏率</button>
              <button type="button" class="voc-grain-btn${intState.trendMetric === "return" ? " is-active" : ""}" data-int-metric="return">退货率</button>
            </div>
            ${renderIntTrendSpark(intState.trendMetric)}
          </section>

          <section class="table-card">
            <div class="table-toolbar"><div><h3>代表商品明细</h3><p>支撑该建议的样本 SKC</p></div></div>
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Goods ID</th><th>商品名称</th><th>颜色</th><th>廓形</th><th>面料</th>
                    <th>销量</th><th>销售额</th><th>加购率</th><th>收藏率</th><th>退货率</th>
                  </tr>
                </thead>
                <tbody>
                  ${(rec.goods || []).length
                    ? rec.goods
                        .map(
                          (g) => `
                    <tr>
                      <td>${g.id}</td>
                      <td><span class="cell-title">${g.name}</span></td>
                      <td>${g.color}</td><td>${g.sil}</td><td>${g.fabric}</td>
                      <td class="score-num">${g.sales.toLocaleString()}</td>
                      <td>${g.rev}</td><td>${g.add}</td><td>${g.wish}</td><td>${g.ret}</td>
                    </tr>
                  `
                        )
                        .join("")
                    : `<tr><td colspan="10" class="muted">暂无代表商品样本（Demo）</td></tr>`}
                </tbody>
              </table>
            </div>
          </section>

          <section class="page-split">
            <article class="table-card">
              <div class="table-toolbar"><div><h3>退货原因明细</h3></div></div>
              <div class="table-wrap">
                <table class="data-table">
                  <thead><tr><th>退货原因</th><th>数量</th><th>占比</th><th>是否高于品类均值</th></tr></thead>
                  <tbody>
                    ${(rec.returns || []).length
                      ? rec.returns
                          .map(
                            (x) => `
                      <tr>
                        <td>${x.reason}</td>
                        <td class="score-num">${x.count}</td>
                        <td>${x.share}</td>
                        <td>${renderTag(x.high ? "是" : "否", x.high ? "red" : "green")}</td>
                      </tr>
                    `
                          )
                          .join("")
                      : `<tr><td colspan="4" class="muted">暂无退货拆分</td></tr>`}
                  </tbody>
                </table>
              </div>
            </article>
            <article class="voc-panel">
              <h4>行为明细</h4>
              <div class="kv-list">
                <div class="kv-row"><span>浏览量</span><strong>${rec.behavior.pv}</strong></div>
                <div class="kv-row"><span>加购量</span><strong>${rec.behavior.cart}</strong></div>
                <div class="kv-row"><span>收藏量</span><strong>${rec.behavior.wish}</strong></div>
                <div class="kv-row"><span>转化率</span><strong>${rec.behavior.cvr}</strong></div>
                <div class="kv-row"><span>周环比</span><strong>${rec.behavior.wow}</strong></div>
              </div>
            </article>
          </section>
        </div>
      </section>
    </div>
  `;
}

function renderIntDrawer() {
  if (!intState.drawerAttrId) return "";
  const a = intGetAttr(intState.drawerAttrId);
  return `
    <div class="int-drawer-mask" data-int-close-drawer></div>
    <aside class="int-drawer" role="dialog" aria-label="属性详情">
      <div class="int-drawer__head">
        <div>
          <p class="muted">属性详情</p>
          <h3>${a.name}</h3>
        </div>
        <button type="button" class="btn-icon" data-int-close-drawer aria-label="关闭">×</button>
      </div>
      <div class="int-drawer__body">
        <div class="int-drawer__tags">
          ${renderTag(a.quad, INT_QUAD_STYLE[a.quad] || "muted")}
          ${renderTag(`适配度 ${a.fit}`, "purple")}
          ${renderTag(a.trend, intTrendTone(a.trend))}
        </div>
        <div class="kv-list" style="margin-top:14px;">
          <div class="kv-row"><span>销量</span><strong>${a.sales.toLocaleString()}</strong></div>
          <div class="kv-row"><span>销售额</span><strong>${a.revenue}</strong></div>
          <div class="kv-row"><span>退货率</span><strong>${a.returnRate}</strong></div>
          <div class="kv-row"><span>覆盖 SKC</span><strong>${a.skc} 个</strong></div>
          <div class="kv-row"><span>建议动作</span><strong>${a.action}</strong></div>
        </div>
        <h4 style="margin:18px 0 10px;font-size:13px;">代表商品</h4>
        <div class="int-drawer-goods">
          ${(a.goods || []).length
            ? a.goods
                .map(
                  (g) => `
            <div class="int-drawer-good">
              <strong>${g.name}</strong>
              <span>${g.id} · ${g.sil} · ${g.fabric}</span>
              <span>销量 ${g.sales} · 退货 ${g.ret}</span>
            </div>
          `
                )
                .join("")
            : `<p class="muted">暂无代表商品</p>`}
        </div>
        <div class="filter-actions" style="margin-top:16px;">
          <button type="button" class="btn btn-primary" data-toast="int-gen-rec" data-case="${a.name}">生成建议</button>
          <button type="button" class="btn btn-secondary" data-toast="voc-pool" data-case="${a.name}">加入机会池</button>
        </div>
      </div>
    </aside>
  `;
}

function renderInternalPage() {
  const body =
    intState.tab === "attr"
      ? renderIntAttrTab()
      : intState.tab === "trace"
        ? renderIntTraceTab()
        : renderIntRecsTab();

  return `
    <div class="page-stack int-page">
      ${renderIntGlobalFilters()}
      <section class="card card-pad int-hub">
        <div class="card-head">
          <div>
            <h3>内部数据选品建议引擎</h3>
            <p>属性钻取 · 建议清单 · 明细追溯 · 可执行内部建议闭环</p>
          </div>
          <span class="voc-real">INTERNAL ENGINE</span>
        </div>
        <div class="voc-tabs" role="tablist">
          ${INT_TABS.map(
            (t) => `
            <button type="button" class="voc-tab${intState.tab === t.id ? " is-active" : ""}" data-int-tab="${t.id}" role="tab">${t.label}</button>
          `
          ).join("")}
        </div>
        <div class="voc-tab-panel">${body}</div>
      </section>
      ${renderIntDrawer()}
    </div>
  `;
}

function updateInternalHeader() {
  const meta = pageMetaById["monitor-internal"];
  $("#page-crumb").textContent = meta.crumb;
  $("#page-title").textContent = "内部数据动态";
  $("#page-desc").textContent =
    "基于内部商品、销售、行为和退货数据，识别属性机会、覆盖空档与可执行选品建议。";
  const right = $("#topbar-right");
  if (right) {
    right.innerHTML = `<div class="voc-updated">数据更新时间：2026-07-17 10:52</div>`;
  }
}
