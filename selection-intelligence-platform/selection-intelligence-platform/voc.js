/**
 * 社媒舆情动态 · VOC 舆情数据中心（AZ REPORT 风格 Demo）
 */

const VOC_TABS = [
  { id: "overview", label: "问题总览" },
  { id: "detail", label: "明细搜索" },
  { id: "analysis", label: "整体分析" },
  { id: "board", label: "分类看板" },
  { id: "trend", label: "趋势分析" },
  { id: "attr", label: "归因" },
];

const VOC_PLATFORMS = [
  "Website",
  "Zendesk",
  "App Store",
  "Google Play",
  "Google",
  "Trustpilot",
  "Twitter",
  "Instagram",
  "Reddit",
  "WeddingWire",
  "The Knot",
];

const VOC_PLATFORM_DIST = [
  { name: "Website", value: 682, color: "#3b5bdb" },
  { name: "Zendesk", value: 514, color: "#7048e8" },
  { name: "App Store", value: 286, color: "#339af0" },
  { name: "Twitter", value: 198, color: "#15aabf" },
  { name: "Trustpilot", value: 176, color: "#0ca678" },
  { name: "Google Play", value: 152, color: "#82c91e" },
  { name: "Instagram", value: 128, color: "#f59f00" },
  { name: "Reddit", value: 97, color: "#ff922b" },
  { name: "WeddingWire", value: 78, color: "#e64980" },
  { name: "The Knot", value: 66, color: "#ae3ec9" },
  { name: "Google", value: 50, color: "#868e96" },
];

const VOC_COUNTRY_DIST = [
  { name: "US", value: 1124 },
  { name: "CA", value: 312 },
  { name: "GB", value: 268 },
  { name: "FR", value: 186 },
  { name: "IT", value: 142 },
  { name: "AU", value: 128 },
  { name: "DE", value: 96 },
  { name: "ES", value: 74 },
  { name: "NL", value: 52 },
  { name: "Other", value: 45 },
];

const VOC_TREND_SERIES = {
  month: [
    { label: "2月", good: 180, bad: 62, rate: 25.6 },
    { label: "3月", good: 210, bad: 78, rate: 27.1 },
    { label: "4月", good: 245, bad: 96, rate: 28.2 },
    { label: "5月", good: 318, bad: 148, rate: 31.8 },
    { label: "6月", good: 386, bad: 214, rate: 35.7 },
    { label: "7月", good: 259, bad: 231, rate: 47.1 },
  ],
  week: [
    { label: "W22", good: 72, bad: 28, rate: 28.0 },
    { label: "W23", good: 81, bad: 34, rate: 29.6 },
    { label: "W24", good: 94, bad: 41, rate: 30.4 },
    { label: "W25", good: 108, bad: 52, rate: 32.5 },
    { label: "W26", good: 126, bad: 68, rate: 35.1 },
    { label: "W27", good: 118, bad: 86, rate: 42.2 },
  ],
  day: [
    { label: "07/12", good: 18, bad: 9, rate: 33.3 },
    { label: "07/13", good: 22, bad: 11, rate: 33.3 },
    { label: "07/14", good: 26, bad: 14, rate: 35.0 },
    { label: "07/15", good: 24, bad: 16, rate: 40.0 },
    { label: "07/16", good: 29, bad: 18, rate: 38.3 },
    { label: "07/17", good: 21, bad: 19, rate: 47.5 },
  ],
};

const VOC_TOP_CS = [
  { rank: 1, pri: "P0", name: "码数不合适 / Fit 偏差", count: 188 },
  { rank: 2, pri: "P0", name: "物流延误 / 履约超时", count: 156 },
  { rank: 3, pri: "P1", name: "图货不一致", count: 98 },
  { rank: 4, pri: "P0", name: "退货流程复杂", count: 86 },
  { rank: 5, pri: "P1", name: "客服响应慢", count: 74 },
  { rank: 6, pri: "P1", name: "包裹破损 / 漏发", count: 68 },
  { rank: 7, pri: "P2", name: "沟通语气生硬", count: 52 },
  { rank: 8, pri: "P1", name: "改址失败", count: 47 },
  { rank: 9, pri: "P2", name: "发票信息错误", count: 39 },
  { rank: 10, pri: "P2", name: "促销规则误解", count: 34 },
];

const VOC_TOP_RD = [
  { rank: 1, pri: "P1", name: "无法修改/取消订单（系统报错）", count: 189 },
  { rank: 2, pri: "P2", name: "订单状态不更新 / 物流追踪异常", count: 138 },
  { rank: 3, pri: "P0", name: "支付失败 / 重复扣款", count: 92 },
  { rank: 4, pri: "P1", name: "尺码表加载失败", count: 71 },
  { rank: 5, pri: "P1", name: "APP 崩溃 / 白屏", count: 63 },
  { rank: 6, pri: "P2", name: "筛选条件不生效", count: 55 },
  { rank: 7, pri: "P1", name: "优惠券无法核销", count: 48 },
  { rank: 8, pri: "P2", name: "搜索结果不准", count: 41 },
  { rank: 9, pri: "P2", name: "收藏夹同步异常", count: 33 },
  { rank: 10, pri: "P2", name: "推送重复打扰", count: 28 },
];

const VOC_COMMENTS = [
  {
    id: "REV-20260715-88421",
    platform: "Trustpilot",
    country: "US",
    date: "2026-07-15",
    sentiment: "差评",
    stars: 2,
    original:
      "The dress looks nothing like the photos and the size chart is completely off. Customer service took days to reply.",
    translated: "裙子和图完全不一样，尺码表偏差很大。客服好几天才回复。",
    cs: "Logistics / Size · 履约沟通延迟 + 码数不合适",
    rd: "订单管理 · 工单状态滞后",
    product: "Fit / 图货一致 · Stretch Satin A-Line",
    summary: "外热SKU存在 Fit 与图货双风险，建议小测验证并同步 SOP。",
  },
  {
    id: "REV-20260714-77102",
    platform: "Website",
    country: "CA",
    date: "2026-07-14",
    sentiment: "差评",
    stars: 1,
    original: "Tried to cancel my order within an hour but the system kept throwing errors.",
    translated: "下单一小时内尝试取消，系统一直报错。",
    cs: "订单变更受阻 · 需人工介入",
    rd: "P1 无法修改/取消订单（系统报错）",
    product: "—",
    summary: "高频系统故障直接影响转化与退款体验，应优先排研发修复。",
  },
  {
    id: "REV-20260713-66018",
    platform: "App Store",
    country: "GB",
    date: "2026-07-13",
    sentiment: "好评",
    stars: 5,
    original: "Beautiful color and fast shipping. Fit is true to size for Dusty Sage.",
    translated: "颜色好看、发货快。Dusty Sage 尺码很准。",
    cs: "履约体验正向",
    rd: "—",
    product: "Color / Fit 正向验证 · Dusty Sage",
    summary: "可作为选品双高机会的舆情正样本补充。",
  },
  {
    id: "REV-20260712-55209",
    platform: "Zendesk",
    country: "US",
    date: "2026-07-12",
    sentiment: "差评",
    stars: 2,
    original: "Tracking never updates and return label instructions are confusing.",
    translated: "物流轨迹从不更新，退货面单说明也很乱。",
    cs: "Logistics 物流/履约问题",
    rd: "订单状态系统不更新 / 物流追踪异常",
    product: "—",
    summary: "客满 + 研发跨部门归因典型案例，建议进避雷监控并优化 SOP。",
  },
  {
    id: "REV-20260711-44155",
    platform: "Twitter",
    country: "US",
    date: "2026-07-11",
    sentiment: "差评",
    stars: 1,
    original: "Paid for rush shipping and still missed my wedding weekend. Never again.",
    translated: "付了加急运费，还是错过了婚礼周末。不会再买了。",
    cs: "Logistics 物流/履约问题 · 加急未兑现",
    rd: "订单状态系统不更新 / 物流追踪异常",
    product: "—",
    summary: "履约承诺与系统轨迹双重失效，社媒扩散风险高，建议进避雷榜。",
  },
  {
    id: "REV-20260710-33902",
    platform: "WeddingWire",
    country: "US",
    date: "2026-07-10",
    sentiment: "好评",
    stars: 5,
    original: "Color matched perfectly across the bridal party. Square neck looked elegant in photos.",
    translated: "伴娘团颜色完全一致，方领在照片里很优雅。",
    cs: "履约与咨询体验正向",
    rd: "—",
    product: "Color / Neckline 正向 · Square Neck · Dusty Sage",
    summary: "婚礼场景正样本，可支撑选品机会池「双高」论证。",
  },
  {
    id: "REV-20260709-22871",
    platform: "Reddit",
    country: "CA",
    date: "2026-07-09",
    sentiment: "差评",
    stars: 2,
    original: "Fabric feels cheaper than the listing photos. Hem stitching came loose after one wear.",
    translated: "面料手感比详情页照片廉价，穿一次裙摆线头就开了。",
    cs: "Quality 质量投诉",
    rd: "—",
    product: "面料手感 / 做工细节 · Stretch Satin",
    summary: "商品侧质量槽点明确，建议生成商品优化建议并小测验证。",
  },
  {
    id: "REV-20260708-11764",
    platform: "Instagram",
    country: "AU",
    date: "2026-07-08",
    sentiment: "差评",
    stars: 2,
    original: "Looks nothing like the influencer try-on. Shade is way darker in person.",
    translated: "和博主试穿完全不一样，实物颜色深很多。",
    cs: "图货不一致投诉",
    rd: "—",
    product: "图货一致 · Color 偏差",
    summary: "社媒种草与实物色差冲突，需同步商详与避雷监控。",
  },
];

const VOC_CS_L1 = [
  { name: "Others 其他", value: 356 },
  { name: "Logistics 物流/履约", value: 312 },
  { name: "Size 尺码", value: 217 },
  { name: "Quality 质量", value: 148 },
  { name: "Service 服务", value: 102 },
];

const VOC_RD_L1 = [
  { name: "Others 其他", value: 421 },
  { name: "订单管理", value: 327 },
  { name: "退货与退款", value: 175 },
  { name: "支付与优惠", value: 98 },
  { name: "APP/站点稳定性", value: 86 },
];

const VOC_PD_L1 = [
  { name: "其他", value: 1283 },
  { name: "Fit / 尺码表现", value: 246 },
  { name: "图货一致", value: 168 },
  { name: "面料手感", value: 112 },
  { name: "做工细节", value: 84 },
];

const VOC_PRIORITY_TOP = [
  { name: "无法取消订单系统报错", pri: "P0", owner: "研发", count: 189 },
  { name: "码数不合适", pri: "P0", owner: "商品+客满", count: 188 },
  { name: "物流延误", pri: "P0", owner: "客满", count: 156 },
  { name: "物流轨迹不更新", pri: "P1", owner: "研发", count: 138 },
  { name: "图货不一致", pri: "P1", owner: "商品", count: 98 },
  { name: "支付失败重复扣款", pri: "P0", owner: "研发", count: 92 },
];

const VOC_PRIORITY_DIST = [
  { name: "P0", value: 42, color: "#fa5252" },
  { name: "P1", value: 33, color: "#ff922b" },
  { name: "P2", value: 25, color: "#339af0" },
];

const VOC_CROSS_CASES = [
  {
    title: "取消订单失败 + 客满被迫补偿",
    sides: "研发 · 客满",
    impact: "退款 SLA 超时 · 差评抬升",
  },
  {
    title: "轨迹不更新导致客诉升级",
    sides: "研发 · 客满 · 物流",
    impact: "Zendesk 工单堆积",
  },
  {
    title: "尺码表错误引发批量退货",
    sides: "商品 · 客满",
    impact: "特定 SKU 退货率异常",
  },
  {
    title: "图货差驱动退货与差评",
    sides: "商品 · 社媒",
    impact: "Trustpilot 评分下滑",
  },
  {
    title: "优惠券核销失败 + 客满话术缺失",
    sides: "研发 · 客满",
    impact: "促销期投诉峰值",
  },
];

const VOC_BOARD = {
  cs: [
    {
      id: "cs-others",
      title: "Others 其他",
      count: 356,
      children: [
        { pri: "P2", name: "信息咨询类", count: 142 },
        { pri: "P2", name: "未分类反馈", count: 214 },
      ],
    },
    {
      id: "cs-logistics",
      title: "Logistics 物流/履约问题",
      count: 312,
      children: [
        { pri: "P0", name: "物流延误 / 履约超时", count: 156 },
        { pri: "P1", name: "包裹破损 / 漏发", count: 68 },
        { pri: "P1", name: "改址失败", count: 47 },
        { pri: "P2", name: "派送通知缺失", count: 41 },
      ],
    },
    {
      id: "cs-size",
      title: "Size 尺码问题",
      count: 217,
      open: true,
      children: [
        { pri: "P0", name: "码数不合适", count: 188 },
        { pri: "P0", name: "尺码偏小", count: 24 },
        { pri: "P0", name: "尺码偏大", count: 5 },
      ],
    },
  ],
  rd: [
    {
      id: "rd-others",
      title: "Others 其他",
      count: 421,
      children: [
        { pri: "P2", name: "体验建议类", count: 210 },
        { pri: "P2", name: "无法归因", count: 211 },
      ],
    },
    {
      id: "rd-order",
      title: "订单管理",
      count: 327,
      open: true,
      children: [
        { pri: "P1", name: "无法修改/取消订单（系统报错）", count: 189 },
        { pri: "P2", name: "订单状态系统不更新/物流追踪异常", count: 138 },
      ],
    },
    {
      id: "rd-refund",
      title: "退货与退款",
      count: 175,
      children: [
        { pri: "P1", name: "退款时效超时", count: 96 },
        { pri: "P2", name: "退货面单异常", count: 79 },
      ],
    },
  ],
  pd: [
    {
      id: "pd-others",
      title: "其他",
      count: 1283,
      open: true,
      children: [
        { pri: "P2", name: "泛化评价 / 无明确商品锚点", count: 980 },
        { pri: "P2", name: "多商品混合评价", count: 303 },
      ],
    },
    {
      id: "pd-fit",
      title: "Fit / 尺码表现",
      count: 246,
      children: [
        { pri: "P0", name: "版型偏差集中 SKU", count: 168 },
        { pri: "P1", name: "Stretch 面料松垮", count: 78 },
      ],
    },
    {
      id: "pd-photo",
      title: "图货一致",
      count: 168,
      children: [
        { pri: "P1", name: "色差 / 光影偏差", count: 96 },
        { pri: "P1", name: "版型与实拍不符", count: 72 },
      ],
    },
  ],
};

const VOC_TREND_TOTAL = [320, 360, 410, 520, 680, 490];
const VOC_TREND_BAD = [62, 78, 96, 148, 214, 231];
const VOC_TREND_RATE = [19.4, 21.7, 23.4, 28.5, 31.5, 47.1];
const VOC_TREND_LABELS = ["2月", "3月", "4月", "5月", "6月", "7月"];
const VOC_REASON_TREND = [
  { name: "尺码问题", values: [28, 34, 41, 52, 68, 74], color: "#fa5252" },
  { name: "物流履约", values: [22, 26, 31, 44, 58, 62], color: "#ff922b" },
  { name: "订单系统", values: [18, 21, 29, 48, 71, 86], color: "#7048e8" },
];

let vocState = {
  tab: "overview",
  grain: "month",
  expanded: {
    "cs-size": true,
    "rd-order": true,
    "pd-others": true,
  },
};

function vocPriClass(pri) {
  if (pri === "P0") return "voc-pri--p0";
  if (pri === "P1") return "voc-pri--p1";
  return "voc-pri--p2";
}

function vocDelta(text, upGood = false) {
  const negative = String(text).trim().startsWith("-");
  const cls = negative === upGood ? "is-up" : negative ? "is-down" : "is-up";
  return `<span class="voc-delta ${cls}">环比 ${text}</span>`;
}

function renderVocDonut(items) {
  const total = items.reduce((s, i) => s + i.value, 0) || 1;
  let acc = 0;
  const stops = items
    .map((i) => {
      const start = (acc / total) * 100;
      acc += i.value;
      const end = (acc / total) * 100;
      return `${i.color} ${start}% ${end}%`;
    })
    .join(", ");

  return `
    <div class="voc-donut-wrap">
      <div class="voc-donut" style="background:conic-gradient(${stops})"></div>
      <div class="voc-donut-legend">
        ${items
          .map(
            (i) => `
          <div class="voc-legend-row">
            <span><i style="background:${i.color}"></i>${i.name}</span>
            <strong>${i.value}</strong>
          </div>
        `
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderVocBars(items, maxOverride) {
  const max = maxOverride || Math.max(...items.map((i) => i.value), 1);
  return `
    <div class="voc-bars">
      ${items
        .map(
          (i) => `
        <div class="voc-bar-row">
          <span class="voc-bar-label">${i.name}</span>
          <div class="voc-bar-track"><i style="width:${(i.value / max) * 100}%"></i></div>
          <strong>${i.value}</strong>
        </div>
      `
        )
        .join("")}
    </div>
  `;
}

/** 国家分布 · 竖向柱状图 */
function renderVocColumnChart(items) {
  const max = Math.max(...items.map((i) => i.value), 1);
  const w = 520;
  const h = 210;
  const padL = 36;
  const padR = 12;
  const padT = 18;
  const padB = 36;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;
  const gap = plotW / items.length;
  const barW = Math.min(28, gap * 0.55);

  const bars = items
    .map((item, idx) => {
      const bh = (item.value / max) * plotH;
      const x = padL + idx * gap + (gap - barW) / 2;
      const y = padT + plotH - bh;
      const labelX = padL + idx * gap + gap / 2;
      return `
        <rect x="${x}" y="${y}" width="${barW}" height="${bh}" rx="4" fill="${idx === 0 ? "#3b5bdb" : "#74c0fc"}"/>
        <text x="${labelX}" y="${y - 6}" text-anchor="middle" font-size="10" fill="#5c6578">${item.value}</text>
        <text x="${labelX}" y="${h - 10}" text-anchor="middle" font-size="11" font-weight="650" fill="#5c6578">${item.name}</text>
      `;
    })
    .join("");

  return `
    <svg viewBox="0 0 ${w} ${h}" class="voc-column-svg" role="img" aria-label="国家分布柱状图">
      <line x1="${padL}" y1="${padT}" x2="${padL}" y2="${padT + plotH}" stroke="#e6e9f0" />
      <line x1="${padL}" y1="${padT + plotH}" x2="${w - padR}" y2="${padT + plotH}" stroke="#e6e9f0" />
      ${bars}
    </svg>
  `;
}

function renderVocActionBar(extraClass = "") {
  return `
    <div class="voc-action-bar ${extraClass}">
      <span class="voc-action-bar__label">联动动作</span>
      <button type="button" class="btn btn-secondary" data-toast="voc-pool">加入机会池</button>
      <button type="button" class="btn btn-secondary" data-toast="voc-risk">加入避雷榜</button>
      <button type="button" class="btn btn-secondary" data-toast="voc-product">生成商品优化建议</button>
      <button type="button" class="btn btn-secondary" data-toast="voc-rd">生成研发待办</button>
      <button type="button" class="btn btn-secondary" data-toast="voc-sop">生成客服 SOP 优化建议</button>
    </div>
  `;
}

function renderVocCombo(grain) {
  const rows = VOC_TREND_SERIES[grain] || VOC_TREND_SERIES.month;
  const max = Math.max(...rows.map((r) => Math.max(r.good, r.bad)), 1);
  const w = 520;
  const h = 180;
  const pad = 28;
  const gap = (w - pad * 2) / rows.length;
  const barW = gap * 0.28;

  const goodBars = rows
    .map((r, idx) => {
      const x = pad + idx * gap + gap * 0.2;
      const bh = (r.good / max) * (h - 50);
      return `<rect x="${x}" y="${h - 24 - bh}" width="${barW}" height="${bh}" rx="3" fill="#3b5bdb"/>`;
    })
    .join("");

  const badBars = rows
    .map((r, idx) => {
      const x = pad + idx * gap + gap * 0.2 + barW + 4;
      const bh = (r.bad / max) * (h - 50);
      return `<rect x="${x}" y="${h - 24 - bh}" width="${barW}" height="${bh}" rx="3" fill="#fa5252"/>`;
    })
    .join("");

  const points = rows
    .map((r, idx) => {
      const x = pad + idx * gap + gap * 0.45;
      const y = h - 24 - (r.rate / 60) * (h - 50);
      return `${x},${y}`;
    })
    .join(" ");

  const labels = rows
    .map((r, idx) => {
      const x = pad + idx * gap + gap * 0.35;
      return `<text x="${x}" y="${h - 6}" font-size="10" fill="#9aa1b2">${r.label}</text>`;
    })
    .join("");

  return `
    <div class="voc-combo">
      <div class="voc-grain">
        <button type="button" class="voc-grain-btn${grain === "month" ? " is-active" : ""}" data-voc-grain="month">月度</button>
        <button type="button" class="voc-grain-btn${grain === "week" ? " is-active" : ""}" data-voc-grain="week">周度</button>
        <button type="button" class="voc-grain-btn${grain === "day" ? " is-active" : ""}" data-voc-grain="day">日度</button>
      </div>
      <svg viewBox="0 0 ${w} ${h}" class="voc-combo-svg" role="img" aria-label="好差评趋势">
        ${goodBars}${badBars}
        <polyline fill="none" stroke="#f59f00" stroke-width="2.5" points="${points}"/>
        ${points
          .split(" ")
          .map((p) => {
            const [x, y] = p.split(",");
            return `<circle cx="${x}" cy="${y}" r="3.5" fill="#f59f00"/>`;
          })
          .join("")}
        ${labels}
      </svg>
      <div class="voc-combo-legend">
        <span><i style="background:#3b5bdb"></i>好评</span>
        <span><i style="background:#fa5252"></i>差评</span>
        <span><i style="background:#f59f00"></i>差评率</span>
      </div>
    </div>
  `;
}

function renderVocRankList(title, items) {
  const max = Math.max(...items.map((i) => i.count), 1);
  return `
    <section class="voc-panel">
      <h4>${title}</h4>
      <div class="voc-rank-list">
        ${items
          .map(
            (item) => `
          <div class="voc-rank-row">
            <span class="voc-rank-no">${item.rank}</span>
            <span class="voc-pri ${vocPriClass(item.pri)}">${item.pri}</span>
            <div class="voc-rank-main">
              <div class="voc-rank-top">
                <strong>${item.name}</strong>
                <span>${item.count}</span>
              </div>
              <div class="voc-rank-bar"><i style="width:${(item.count / max) * 100}%"></i></div>
            </div>
          </div>
        `
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderVocOverview() {
  return `
    <div class="voc-tab-body">
      <div class="voc-filters">
        <div class="field"><label>时间</label><select><option>最近 3 个月</option><option>最近 30 天</option><option>最近 7 天</option></select></div>
        <div class="field"><label>平台</label><select><option>全部平台</option>${VOC_PLATFORMS.map((p) => `<option>${p}</option>`).join("")}</select></div>
        <div class="field"><label>国家</label><select><option>全部国家</option><option>US</option><option>CA</option><option>GB</option><option>FR</option><option>IT</option><option>AU</option><option>DE</option></select></div>
        <div class="voc-filters__actions">
          <button type="button" class="btn btn-secondary" data-toast="refresh">刷新</button>
          <span class="voc-real">REAL DATA</span>
        </div>
      </div>

      <section class="kpi-row">
        ${renderKpiCard({ id: "VOC-TOTAL", label: "总反馈量", value: "2,427", sub: vocDelta("1561.3%") })}
        ${renderKpiCard({ id: "VOC-BAD", label: "差评量", value: "829", sub: vocDelta("1976.6%") })}
        ${renderKpiCard({ id: "VOC-RATE", label: "差评率", value: "34.2%", sub: vocDelta("162.8%") })}
        ${renderKpiCard({ id: "VOC-STAR", label: "平均评分", value: "3.26 ★", sub: vocDelta("-0.24") })}
      </section>

      <section class="voc-chart-grid">
        <article class="voc-panel">
          <h4>平台分布 · 总反馈量</h4>
          ${renderVocDonut(VOC_PLATFORM_DIST)}
        </article>
        <article class="voc-panel">
          <h4>国家分布 · 总反馈量</h4>
          ${renderVocColumnChart(VOC_COUNTRY_DIST)}
        </article>
        <article class="voc-panel voc-panel--wide">
          <h4>好差评趋势</h4>
          ${renderVocCombo(vocState.grain)}
        </article>
      </section>

      <section class="voc-rank-grid">
        ${renderVocRankList("Top 10 槽点榜 · 客满侧", VOC_TOP_CS)}
        ${renderVocRankList("Top 10 槽点榜 · 研发侧", VOC_TOP_RD)}
      </section>
    </div>
  `;
}

function renderVocDetail() {
  return `
    <div class="voc-tab-body">
      <div class="voc-filters voc-filters--dense">
        <div class="field"><label>平台</label><select><option>全部平台</option>${VOC_PLATFORMS.map((p) => `<option>${p}</option>`).join("")}</select></div>
        <div class="field"><label>开始日期</label><input type="date" value="2026-04-17" /></div>
        <div class="field"><label>结束日期</label><input type="date" value="2026-07-17" /></div>
        <div class="field"><label>订单号</label><input type="text" placeholder="可选" /></div>
        <div class="field"><label>评价</label><select><option>全部</option><option>好评</option><option>差评</option></select></div>
        <div class="field"><label>关键词</label><input type="text" placeholder="size / shipping..." /></div>
        <div class="field"><label>客满原因</label><select><option>全部</option><option>Size 尺码问题</option><option>Logistics 物流/履约问题</option><option>Quality 质量</option></select></div>
        <div class="field"><label>研发原因</label><select><option>全部</option><option>订单管理</option><option>退货与退款</option><option>支付与优惠</option></select></div>
        <div class="field"><label>商品原因</label><select><option>全部</option><option>Fit / 尺码表现</option><option>图货一致</option><option>面料手感</option></select></div>
        <div class="voc-filters__actions">
          <button type="button" class="btn btn-primary" data-toast="refresh">搜索</button>
          <button type="button" class="btn btn-secondary" data-toast="export-csv">导出 CSV</button>
        </div>
      </div>

      <div class="voc-comment-list">
        ${VOC_COMMENTS.map(
          (c) => `
          <article class="voc-comment">
            <div class="voc-comment__head">
              <div class="voc-comment__ids">
                <div class="voc-meta-grid">
                  <div><span>评论 ID</span><strong>${c.id}</strong></div>
                  <div><span>平台</span><strong>${c.platform}</strong></div>
                  <div><span>国家</span><strong>${c.country}</strong></div>
                  <div><span>日期</span><strong>${c.date}</strong></div>
                </div>
              </div>
              <div class="voc-comment__tags">
                <span class="tag ${c.sentiment === "差评" ? "tag--red" : "tag--green"}">${c.sentiment}</span>
                <span class="tag tag--orange">${c.stars} ★</span>
              </div>
            </div>
            <div class="voc-comment__body">
              <div class="voc-text-block"><span>原文</span><p>${c.original}</p></div>
              <div class="voc-text-block"><span>翻译</span><p>${c.translated}</p></div>
            </div>
            <div class="voc-ai-box">
              <h5>AI 分析结果</h5>
              <div class="voc-ai-grid">
                <div class="voc-ai-col"><span>客满侧归因</span><strong>${c.cs}</strong></div>
                <div class="voc-ai-col"><span>研发侧归因</span><strong>${c.rd}</strong></div>
                <div class="voc-ai-col"><span>商品侧归因</span><strong>${c.product}</strong></div>
              </div>
              <div class="voc-ai-summary"><span>AI 总结</span><p>${c.summary}</p></div>
              <div class="filter-actions" style="margin-top:12px;">
                <button type="button" class="btn btn-secondary" data-toast="voc-pool">加入机会池</button>
                <button type="button" class="btn btn-secondary" data-toast="voc-risk">加入避雷榜</button>
                <button type="button" class="btn btn-secondary" data-toast="voc-product">生成商品优化建议</button>
              </div>
            </div>
          </article>
        `
        ).join("")}
      </div>
    </div>
  `;
}

function renderVocMiniBars(title, items) {
  return `
    <article class="voc-panel">
      <h4>${title}</h4>
      ${renderVocBars(items)}
    </article>
  `;
}

function renderVocAnalysis() {
  return `
    <div class="voc-tab-body">
      <section class="kpi-row">
        ${renderKpiCard({ id: "VA-1", label: "总反馈量", value: "1,135", sub: "归因分析窗口" })}
        ${renderKpiCard({ id: "VA-2", label: "已归因评论数", value: "373", sub: "结构化可下钻" })}
        ${renderKpiCard({ id: "VA-3", label: "跨部门归因数", value: "291", sub: "需协同治理" })}
        ${renderKpiCard({ id: "VA-4", label: "负向反馈数", value: "373", sub: "差评 / 投诉" })}
      </section>

      <section class="voc-chart-grid voc-chart-grid--3">
        ${renderVocMiniBars("客满侧一级原因分布", VOC_CS_L1)}
        ${renderVocMiniBars("研发侧一级原因分布", VOC_RD_L1)}
        ${renderVocMiniBars("商品侧一级原因分布", VOC_PD_L1)}
      </section>

      <section class="voc-analysis-bottom">
        <article class="voc-panel">
          <h4>行动优先级 Top 6</h4>
          <div class="voc-action-list">
            ${VOC_PRIORITY_TOP.map(
              (item, idx) => `
              <div class="voc-action-row">
                <span class="voc-rank-no">${idx + 1}</span>
                <span class="voc-pri ${vocPriClass(item.pri)}">${item.pri}</span>
                <div>
                  <strong>${item.name}</strong>
                  <div class="cell-sub">${item.owner} · ${item.count}</div>
                </div>
              </div>
            `
            ).join("")}
          </div>
        </article>
        <article class="voc-panel">
          <h4>优先级分布</h4>
          ${renderVocDonut(VOC_PRIORITY_DIST)}
        </article>
        <article class="voc-panel">
          <h4>跨部门归因案例 Top 5</h4>
          <div class="voc-case-list">
            ${VOC_CROSS_CASES.map(
              (c) => `
              <div class="voc-case-item">
                <strong>${c.title}</strong>
                <div class="cell-sub">${c.sides}</div>
                <p>${c.impact}</p>
              </div>
            `
            ).join("")}
          </div>
        </article>
      </section>

      ${renderVocActionBar()}
    </div>
  `;
}

function renderVocBoardCol(title, items) {
  return `
    <section class="voc-board-col">
      <h4>${title}</h4>
      <div class="voc-board-list">
          ${items
          .map((item) => {
            const open =
              vocState.expanded[item.id] !== undefined
                ? !!vocState.expanded[item.id]
                : !!item.open;
            return `
              <article class="voc-board-card${open ? " is-open" : ""}">
                <button type="button" class="voc-board-head" data-voc-expand="${item.id}">
                  <span>${item.title}</span>
                  <strong>${item.count}</strong>
                  <em>${open ? "收起" : "展开"}</em>
                </button>
                <div class="voc-board-children">
                  ${(item.children || [])
                    .map(
                      (ch) => `
                    <div class="voc-board-child">
                      <span class="voc-pri ${vocPriClass(ch.pri)}">${ch.pri}</span>
                      <span>${ch.name}</span>
                      <strong>${ch.count}</strong>
                    </div>
                  `
                    )
                    .join("")}
                </div>
              </article>
            `;
          })
          .join("")}
      </div>
    </section>
  `;
}

function renderVocBoard() {
  return `
    <div class="voc-tab-body">
      <section class="voc-board-grid">
        ${renderVocBoardCol("客满侧归因汇总", VOC_BOARD.cs)}
        ${renderVocBoardCol("研发侧归因汇总", VOC_BOARD.rd)}
        ${renderVocBoardCol("商品侧归因汇总", VOC_BOARD.pd)}
      </section>
    </div>
  `;
}

function renderVocTrendLine(title, values, color) {
  const max = Math.max(...values, 1);
  const w = 360;
  const h = 140;
  const pad = 16;
  const step = (w - pad * 2) / (values.length - 1);
  const pts = values
    .map((v, i) => {
      const x = pad + i * step;
      const y = h - 28 - (v / max) * (h - 48);
      return `${x},${y}`;
    })
    .join(" ");
  const labels = VOC_TREND_LABELS.map((lab, i) => {
    const x = pad + i * step - 8;
    return `<text x="${x}" y="${h - 8}" font-size="10" fill="#9aa1b2">${lab}</text>`;
  }).join("");

  return `
    <article class="voc-panel">
      <h4>${title}</h4>
      <svg viewBox="0 0 ${w} ${h}" class="voc-line-svg">
        <polyline fill="none" stroke="${color}" stroke-width="2.5" points="${pts}"/>
        ${pts
          .split(" ")
          .map((p) => {
            const [x, y] = p.split(",");
            return `<circle cx="${x}" cy="${y}" r="3.2" fill="${color}"/>`;
          })
          .join("")}
        ${labels}
      </svg>
    </article>
  `;
}

function renderVocTrend() {
  const w = 640;
  const h = 180;
  const pad = 28;
  const max = Math.max(...VOC_REASON_TREND.flatMap((r) => r.values), 1);
  const step = (w - pad * 2) / (VOC_TREND_LABELS.length - 1);
  const polylines = VOC_REASON_TREND.map((series) => {
    const pts = series.values
      .map((v, i) => {
        const x = pad + i * step;
        const y = h - 28 - (v / max) * (h - 50);
        return `${x},${y}`;
      })
      .join(" ");
    return `<polyline fill="none" stroke="${series.color}" stroke-width="2.4" points="${pts}"/>`;
  }).join("");

  return `
    <div class="voc-tab-body">
      <section class="voc-chart-grid voc-chart-grid--3">
        ${renderVocTrendLine("总反馈量趋势", VOC_TREND_TOTAL, "#3b5bdb")}
        ${renderVocTrendLine("差评量趋势", VOC_TREND_BAD, "#fa5252")}
        ${renderVocTrendLine("差评率趋势", VOC_TREND_RATE, "#f59f00")}
      </section>

      <section class="voc-panel">
        <h4>Top 原因趋势对比</h4>
        <svg viewBox="0 0 ${w} ${h}" class="voc-line-svg voc-line-svg--wide">
          ${polylines}
          ${VOC_TREND_LABELS.map((lab, i) => {
            const x = pad + i * step - 8;
            return `<text x="${x}" y="${h - 8}" font-size="10" fill="#9aa1b2">${lab}</text>`;
          }).join("")}
        </svg>
        <div class="voc-combo-legend">
          ${VOC_REASON_TREND.map((s) => `<span><i style="background:${s.color}"></i>${s.name}</span>`).join("")}
        </div>
      </section>

      <section class="voc-insight-card">
        <h4>AI 趋势洞察</h4>
        <ul>
          <li>近 3 个月差评率由 19.4% 抬升至 47.1%，主驱动为 <strong>订单系统故障</strong> 与 <strong>尺码 Fit</strong>。</li>
          <li>US / CA 贡献了过半负向反馈；WeddingWire / The Knot 对礼服品类口碑敏感度更高。</li>
          <li>建议：将「无法取消订单」「码数不合适」「物流延误」同步进机会池 / 避雷榜，并形成跨部门行动清单。</li>
        </ul>
        ${renderVocActionBar()}
      </section>
    </div>
  `;
}

function renderVocAttr() {
  return `
    <div class="voc-tab-body">
      <section class="voc-board-grid">
        ${renderVocBoardCol("客满侧归因汇总", VOC_BOARD.cs)}
        ${renderVocBoardCol("研发侧归因汇总", VOC_BOARD.rd)}
        ${renderVocBoardCol("商品侧归因汇总", VOC_BOARD.pd)}
      </section>

      <section class="voc-panel">
        <h4>跨部门归因案例</h4>
        <div class="voc-case-grid">
          ${VOC_CROSS_CASES.map(
            (c) => `
            <div class="voc-case-item">
              <strong>${c.title}</strong>
              <div class="cell-sub">${c.sides}</div>
              <p>${c.impact}</p>
            </div>
          `
          ).join("")}
        </div>
      </section>

      ${renderVocActionBar("voc-action-bar--sticky")}
    </div>
  `;
}

function renderSentimentPage() {
  const tabBody = {
    overview: renderVocOverview,
    detail: renderVocDetail,
    analysis: renderVocAnalysis,
    board: renderVocBoard,
    trend: renderVocTrend,
    attr: renderVocAttr,
  }[vocState.tab];

  return `
    <div class="page-stack voc-page">
      <section class="card card-pad voc-hub">
        <div class="card-head">
          <div>
            <h3>舆情数据中心</h3>
            <p>明细检索 · 整体洞察 · 分类钻取 · 趋势监测 · 归因汇总</p>
          </div>
          <div class="voc-hub-badges">
            <span class="voc-real">VOC Hub</span>
            <span class="voc-real voc-real--muted">多平台聚合</span>
          </div>
        </div>
        <div class="voc-tabs" role="tablist">
          ${VOC_TABS.map(
            (t) => `
            <button
              type="button"
              class="voc-tab${vocState.tab === t.id ? " is-active" : ""}"
              data-voc-tab="${t.id}"
              role="tab"
              aria-selected="${vocState.tab === t.id}"
            >${t.label}</button>
          `
          ).join("")}
        </div>
        <div class="voc-tab-panel">
          ${tabBody ? tabBody() : ""}
        </div>
      </section>
    </div>
  `;
}

function updateSentimentHeader() {
  const meta = pageMetaById["monitor-sentiment"];
  $("#page-crumb").textContent = meta.crumb;
  $("#page-title").textContent = meta.title;
  $("#page-desc").textContent = meta.desc;
  const right = $("#topbar-right");
  if (right) {
    right.innerHTML = `<div class="voc-updated">更新于 2026/7/17 17:24:08</div>`;
  }
}

function restoreDefaultHeaderActions() {
  const right = $("#topbar-right");
  if (!right) return;
  right.innerHTML = `
    <div class="global-filters">
      <select aria-label="周次">
        <option>2026-W27</option>
        <option>2026-W26</option>
      </select>
      <select aria-label="业务线">
        <option>BD</option>
        <option>AT</option>
      </select>
      <button type="button" class="btn btn-secondary" data-toast="refresh">刷新</button>
    </div>
  `;
}
