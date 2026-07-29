/**
 * 自动刊登三页 · 板块内容对齐 AI自动刊登参考站
 * 视觉仍用选品智能化平台现有样式体系
 */

let listingUi = {
  listChip: "all",
  reviewAngle: "front",
};

const LISTING_TASKS = [
  {
    no: "T20260715001",
    goods: "1079007",
    ddid: "377518",
    category: "BD",
    route: "精品路线",
    ai: "AI生成完成",
    audit: "待美国团队审核",
    push: "未推送",
    owner: "Mia",
    creator: "Lucy",
    time: "2026-07-15 10:24",
  },
  {
    no: "T20260715002",
    goods: "1079012",
    ddid: "377524",
    category: "BD",
    route: "精品路线",
    ai: "AI生成中",
    audit: "待上海运营审核",
    push: "未推送",
    owner: "Lucy",
    creator: "Lucy",
    time: "2026-07-15 11:08",
  },
  {
    no: "T20260715003",
    goods: "1079028",
    ddid: "377531",
    category: "BD",
    route: "精品路线",
    ai: "AI生成失败",
    audit: "待上海运营审核",
    push: "推送失败",
    owner: "管理员",
    creator: "Amy",
    time: "2026-07-15 11:46",
  },
  {
    no: "T20260714018",
    goods: "1065510",
    ddid: "376102",
    category: "BD",
    route: "精品路线",
    ai: "AI生成完成",
    audit: "已通过",
    push: "待推送",
    owner: "Tom",
    creator: "Shelly",
    time: "2026-07-14 16:40",
  },
];

function listingAiTone(v) {
  if (v === "AI生成完成") return "green";
  if (v === "AI生成中") return "blue";
  if (v === "AI生成失败") return "red";
  return "muted";
}

function listingAuditTone(v) {
  if (v === "已通过") return "green";
  if (v.includes("美国")) return "orange";
  if (v.includes("上海")) return "blue";
  return "muted";
}

function listingPushTone(v) {
  if (v === "推送失败") return "red";
  if (v === "待推送") return "orange";
  return "muted";
}

function renderListingChips(active, items, dataKey) {
  return `
    <div class="page-tabs listing-chips">
      ${items
        .map(
          (it) => `
        <button type="button" class="page-tab${active === it.id ? " is-active" : ""}" data-listing-ui="${dataKey}" data-listing-val="${it.id}">${it.label}</button>
      `
        )
        .join("")}
    </div>
  `;
}

function renderListingFilters(extraActions = "") {
  return `
    <section class="filter-card">
      <div class="card-head" style="margin-bottom:12px;">
        <div>
          <h3 style="margin:0;font-size:15px;">任务筛选</h3>
          <p style="margin:4px 0 0;font-size:12px;color:var(--text-soft);">围绕状态、创建人和关键标识快速定位当前待处理任务。</p>
        </div>
      </div>
      ${renderListingChips(listingUi.listChip, [
        { id: "all", label: "全部任务" },
        { id: "mine", label: "待我处理" },
        { id: "review", label: "待审核" },
        { id: "fail", label: "推送失败" },
      ], "listChip")}
      <div class="filter-grid filter-grid--4" style="margin-top:12px;">
        <div class="field"><label>品类</label><select><option>BD</option><option>AT</option><option>全部</option></select></div>
        <div class="field"><label>审核状态</label><select><option>全部</option><option>待上海运营审核</option><option>待美国团队审核</option><option>已通过</option></select></div>
        <div class="field"><label>AI状态</label><select><option>全部</option><option>AI生成完成</option><option>AI生成中</option><option>AI生成失败</option></select></div>
        <div class="field"><label>盘古推送状态</label><select><option>全部</option><option>未推送</option><option>待推送</option><option>推送失败</option></select></div>
        <div class="field"><label>创建人</label><select><option>全部</option><option>Lucy</option><option>Amy</option><option>Shelly</option></select></div>
        <div class="field"><label>Goods ID</label><input type="text" placeholder="输入 1079007" /></div>
        <div class="field"><label>DDID</label><input type="text" placeholder="输入 377518" /></div>
        <div class="field"><label>创建时间</label><input type="text" value="2026-07-15 至 2026-07-15" /></div>
      </div>
      <div class="filter-actions filter-actions--bar">
        <button type="button" class="btn btn-secondary" data-toast="refresh">重置筛选</button>
        ${extraActions}
      </div>
    </section>
  `;
}

function renderListingListPage() {
  return `
    <div class="page-stack listing-page">
      <section class="kpi-row">
        ${renderKpiCard({ id: "L1", label: "今日新增任务", value: "18", sub: "较昨日 +4，精品路线占 100%" })}
        ${renderKpiCard({ id: "L2", label: "待上海运营审核", value: "07", sub: "AI结果已完成，等待中文与图片核对" })}
        ${renderKpiCard({ id: "L3", label: "待美国团队审核", value: "05", sub: "英文表达与标题描述待确认" })}
        ${renderKpiCard({ id: "L4", label: "推送异常任务", value: "02", sub: "建议优先处理失败重试与异常回流" })}
      </section>

      ${renderListingFilters(`<button type="button" class="btn btn-primary" data-route-jump="listing-new">+ 新建刊登任务</button>`)}

      <section class="table-card">
        <div class="table-toolbar">
          <div>
            <h3>刊登任务列表</h3>
            <p>共 18 条记录，当前聚焦 ${LISTING_TASKS.length} 条重点样例任务。</p>
          </div>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>任务编号</th>
                <th>Goods ID</th>
                <th>DDID</th>
                <th>品类</th>
                <th>AI生成状态</th>
                <th>审核状态</th>
                <th>盘古推送状态</th>
                <th>当前处理人</th>
                <th>创建人</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              ${LISTING_TASKS.map(
                (t) => `
                <tr>
                  <td>
                    <span class="cell-title">${t.no}</span>
                    <span class="cell-sub">${t.route} / ${t.category}</span>
                  </td>
                  <td>${t.goods}</td>
                  <td>${t.ddid}</td>
                  <td>${t.category}</td>
                  <td>${renderTag(t.ai, listingAiTone(t.ai))}</td>
                  <td>${renderTag(t.audit, listingAuditTone(t.audit))}</td>
                  <td>${renderTag(t.push, listingPushTone(t.push))}</td>
                  <td>${t.owner}</td>
                  <td>${t.creator}</td>
                  <td>${t.time}</td>
                  <td>
                    <button type="button" class="btn-text" data-route-jump="listing-review">处理</button>
                    <button type="button" class="btn-text" data-toast="create-listing">重跑 AI</button>
                  </td>
                </tr>
              `
              ).join("")}
            </tbody>
          </table>
        </div>
        <div class="listing-pager">
          <button type="button" class="page-tab is-active">1</button>
          <button type="button" class="page-tab">2</button>
          <button type="button" class="page-tab">3</button>
        </div>
      </section>
    </div>
  `;
}

function renderListingUploadRow(title, files, note) {
  return `
    <div class="listing-upload-row">
      <div>
        <strong>${title}</strong>
        <div class="cell-sub" style="margin-top:4px;">${files}</div>
        <p class="muted" style="margin:6px 0 0;font-size:12px;">${note}</p>
      </div>
      <div class="row-actions">
        <button type="button" class="btn-text" data-toast="cp-upload">上传</button>
        <button type="button" class="btn-text" data-toast="cp-upload">替换</button>
        <button type="button" class="btn-text" data-toast="refresh">查看</button>
        <button type="button" class="btn-text" data-toast="refresh">删除</button>
      </div>
    </div>
  `;
}

function renderListingNewPage() {
  return `
    <div class="page-stack listing-page">
      <section class="card card-pad">
        <div class="card-head">
          <div>
            <h3>基础信息</h3>
            <p>先确认本次刊登任务的品类、标识与价格基线。</p>
          </div>
          ${renderTag("上海运营可编辑", "blue")}
        </div>
        <div class="form-grid">
          <div class="field"><label>品类</label><select><option>BD</option><option>AT</option></select></div>
          <div class="field"><label>路线类型</label><select><option>精品路线</option><option>常规路线</option></select></div>
          <div class="field"><label>Goods ID</label><input type="text" value="1079007" /></div>
          <div class="field"><label>DDID</label><input type="text" value="377518" /></div>
          <div class="field"><label>Base Price</label><input type="text" value="89.00" /></div>
          <div class="field"><label>US Price</label><input type="text" value="129.00" /></div>
          <div class="field"><label>Rush Production</label><select><option>yes</option><option>no</option></select></div>
          <div class="field field--full"><label>业务备注</label>
            <textarea rows="3">本批次优先验证 BD 品类精品路线的自动刊登闭环，要求输出正面、背面、侧面图并保留 AI 留痕。</textarea>
          </div>
        </div>
      </section>

      <section class="card card-pad">
        <div class="card-head">
          <div>
            <h3>素材上传</h3>
            <p>按素材类型分别上传，保证图片与工艺文档状态清晰可见。</p>
          </div>
          <button type="button" class="btn btn-secondary" data-toast="download-report">下载模板说明</button>
        </div>
        ${renderListingUploadRow("图片素材", "front.jpg、back.jpg", "支持上传多张图片，最少 1 张，最多 3 张")}
        ${renderListingUploadRow("工艺备注", "craft-note.docx", "上传格式为 Word（.doc / .docx）")}
      </section>

      <section class="card card-pad">
        <div class="card-head">
          <div>
            <h3>模特库</h3>
            <p>先选择本次任务使用的模特，当前页面只展示已选模特预览。</p>
          </div>
          <div class="filter-actions">
            <button type="button" class="btn btn-secondary" data-toast="refresh">模特库管理</button>
            <button type="button" class="btn btn-secondary" data-toast="refresh">选择模特</button>
          </div>
        </div>
        <div class="listing-model">
          <div class="listing-model__ph">M</div>
          <div>
            <strong>已选模特预览 · Mila Chen</strong>
            <p class="muted" style="margin:6px 0 0;line-height:1.5;">选择模特后在此处展示预览图，具体可用模特信息放在模特库管理弹窗内查看。</p>
          </div>
        </div>
      </section>

      <section class="listing-sticky-footer">
        <div>
          <strong>任务将在保存后进入 AI 生成阶段</strong>
          <p class="muted" style="margin:4px 0 0;">系统会自动抽取文本字段、生成标题描述并完成一站式换装。</p>
        </div>
        <div class="filter-actions">
          <button type="button" class="btn btn-secondary" data-route-jump="listing-list">取消</button>
          <button type="button" class="btn btn-primary" data-toast="create-listing" data-route-jump="listing-review">保存并发起AI生成</button>
        </div>
      </section>
    </div>
  `;
}

function renderListingAttrSelect(label, value, hint = "") {
  return `
    <div class="field">
      <label>${label}${hint ? `<em class="listing-field-hint">${hint}</em>` : ""}</label>
      <input type="text" value="${value}" />
    </div>
  `;
}

function renderListingReviewPage() {
  const angles = [
    { id: "front", label: "正面" },
    { id: "back", label: "背面" },
    { id: "side", label: "侧面" },
    { id: "other", label: "其他" },
  ];
  const gallery = [
    { name: "Front A", status: "已通过", tone: "green" },
    { name: "Front B", status: "已通过", tone: "green" },
    { name: "Back A", status: "已通过", tone: "green" },
    { name: "Side A", status: "待确认", tone: "orange" },
  ];

  return `
    <div class="page-stack listing-page">
      <section class="card card-pad">
        <div class="detail-hero">
          <div>
            <p class="muted">Task Context</p>
            <h2 style="margin:6px 0 10px;font-size:20px;">任务 T20260715001</h2>
            <p class="muted" style="margin:0 0 10px;">Goods ID 1079007 · DDID 377518 · 当前阶段为待美国团队审核</p>
            <div>
              ${renderTag("AI生成完成", "green")}
              ${renderTag("待美国团队审核", "orange")}
              ${renderTag("当前处理人 Mia", "blue")}
            </div>
          </div>
          <div class="filter-actions" style="flex-direction:column;align-items:stretch;">
            <button type="button" class="btn btn-secondary" data-route-jump="listing-list">返回任务列表</button>
          </div>
        </div>
      </section>

      <section class="listing-metric-grid">
        ${[
          ["品类", "BD"],
          ["路线类型", "精品路线"],
          ["已通过图片", "6 / 8"],
          ["盘古状态", "待推送"],
          ["上海运营已完成", "14:10"],
          ["美国团队状态", "待审核"],
          ["AI完成时间", "13:22"],
          ["创建时间", "07-15 10:24"],
          ["更新时间", "07-15 15:06"],
        ]
          .map(
            ([k, v]) => `
          <article class="listing-metric">
            <span>${k}</span>
            <strong>${v}</strong>
          </article>
        `
          )
          .join("")}
      </section>

      <section class="card card-pad">
        <div class="card-head">
          <div>
            <h3>结构化字段</h3>
            <p>当前审核页先聚焦任务基础字段与商品属性，方便业务快速完成关键字段确认。</p>
          </div>
        </div>

        <h4 class="listing-subhead">价格与基础信息</h4>
        <div class="form-grid">
          ${renderListingAttrSelect("Goods ID", "1079007")}
          ${renderListingAttrSelect("DDID", "377518")}
          ${renderListingAttrSelect("Base Price", "89.00")}
          ${renderListingAttrSelect("US Price", "129.00")}
          ${renderListingAttrSelect("Rush Production", "yes")}
        </div>

        <h4 class="listing-subhead">标题与描述</h4>
        <div class="form-grid">
          ${renderListingAttrSelect("Style Name (CN team)", "Harlow 礼服")}
          ${renderListingAttrSelect("Style Name (US team)", "Harlow")}
          <div class="field field--full"><label>Description (CN team)</label>
            <textarea rows="4">Harlow 伴娘礼服采用双件弹力缎面设计，整体为及地修身廓形，搭配平直领口与可拆卸细肩带。柔和褶皱和灵感来自 peplum 的腰部结构强化了上身线条，后背绑带与自系蝴蝶结完成收束，后中开衩并配有同款颈巾。</textarea>
          </div>
          <div class="field field--full"><label>Description (US team)</label>
            <textarea rows="4">The Harlow bridesmaid dress is a two-piece stretch satin design featuring a floor-length sheath skirt and a strapless top with a straight neckline and detachable spaghetti straps. Soft pleating, a peplum-inspired waist, and a lace-up back with a self-tie bow define the structured bodice, while the clean skirt is finished with a back slit and complemented by a matching neck scarf.</textarea>
          </div>
        </div>

        <h4 class="listing-subhead">商品属性</h4>
        <div class="form-grid">
          ${renderListingAttrSelect("Online Color", "Dusty Blue")}
          ${renderListingAttrSelect("Neckline", "Straight平直领", "可多选，必选")}
          ${renderListingAttrSelect("Silhouette", "Sheath紧身裙", "单选，必选")}
          ${renderListingAttrSelect("Sleeves", "Spaghettistraps细肩带", "单选，必选")}
          ${renderListingAttrSelect("Back Style", "laceup后背绑带", "可多选，必选")}
          ${renderListingAttrSelect("Embellishment", "Pleated百褶", "可多选，可不选")}
          ${renderListingAttrSelect("Fabric", "Stretch Satin弹力缎面", "可多选，必选")}
          ${renderListingAttrSelect("Main Fabric", "Stretch Satin水晶麻", "可多选，必选")}
          ${renderListingAttrSelect("Length", "Floor-Length及地长", "可多选，必选")}
          ${renderListingAttrSelect("Boning", "yes", "单选，必选")}
          ${renderListingAttrSelect("Padding", "no", "单选，必选")}
          ${renderListingAttrSelect("Lining", "stretch lining弹力里衬", "单选，必选")}
          ${renderListingAttrSelect("Type of Closure", "Half corset半绑带式束身", "可多选，必选")}
          ${renderListingAttrSelect("Hook and Eye", "no hook and eye无钩眼扣", "单选，必选")}
          ${renderListingAttrSelect("Features", "Detachable Straps可拆卸肩带", "可多选，可不选")}
          <div class="field field--full"><label>Online Size</label>
            <textarea rows="2">US2, US4, US6, US8, US10, US12, US14, US16</textarea>
          </div>
        </div>
      </section>

      <section class="card card-pad">
        <div class="card-head">
          <div>
            <h3>图片工作区</h3>
            <p>把图片区放在结构化字段下方，方便字段确认后再统一看图与替换。</p>
          </div>
        </div>
        ${renderListingChips(listingUi.reviewAngle, angles, "reviewAngle")}
        <div class="listing-gallery">
          ${gallery
            .map(
              (g, idx) => `
            <article class="listing-gallery-card">
              <div class="listing-gallery-ph">${g.name.slice(0, 1)}</div>
              <div class="listing-gallery-meta">
                <strong>${g.name}</strong>
                <span class="cell-sub">AI生成图 · 顺位 ${idx + 1}</span>
                ${renderTag(g.status, g.tone)}
              </div>
              <div class="row-actions">
                <button type="button" class="btn-text" data-toast="cp-upload">替换</button>
                <button type="button" class="btn-text" data-toast="refresh">排序</button>
                <button type="button" class="btn-text" data-toast="refresh">阅览</button>
              </div>
            </article>
          `
            )
            .join("")}
        </div>
      </section>

      <section class="listing-sticky-footer">
        <div>
          <strong>双人审核操作</strong>
          <p class="muted" style="margin:4px 0 0;">上海运营与美国团队可分别确认后推进盘古推送。</p>
        </div>
        <div class="filter-actions">
          <button type="button" class="btn btn-secondary" data-toast="refresh">重置</button>
          <button type="button" class="btn btn-secondary" data-toast="cfg-save">保存修改</button>
          <button type="button" class="btn btn-secondary" data-toast="review-pass">运营审核通过</button>
          <button type="button" class="btn btn-primary" data-toast="review-pass" data-route-jump="listing-list">美国审核通过</button>
        </div>
      </section>
    </div>
  `;
}
