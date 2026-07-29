/**
 * 选品提案 > 创建提案 · 对齐现网选款管理系统表单（不含其侧栏）
 * 预填入口预留：setCreateProposalPrefill(...) / openCreateProposalWithPrefill(...)
 */

const CREATE_PROPOSAL_PRESETS = {
  pool: {
    line: "BD",
    category: "Bridesmaid Dresses",
    source: "Trend",
    proposer: "admin",
    caseId: "SC-2026W27-BD-0042",
    recId: "",
    fromModule: "机会池",
    prefillTag: "系统预填",
    price: "$119-139",
    fabricName: "Stretch Chiffon",
    scene: "Spring / Summer Bridesmaid Wedding",
    design: "Dusty Sage、A-Line、Square Neck、Light Pleated Waist",
    evidence:
      "Birdy Grey 同类属性排名上升，AZ 内部相近色系转化高于类目均值，社媒中 Dusty Sage 与 Square Neck 提及量增长。",
  },
  internal: {
    line: "WD",
    category: "Wedding Dresses",
    source: "Internal",
    proposer: "admin",
    caseId: "",
    recId: "REC-2026-001",
    fromModule: "内部数据动态",
    prefillTag: "系统预填",
    price: "",
    fabricName: "Chiffon",
    scene: "",
    design: "Sage、A-Line、Chiffon",
    evidence:
      "Sage 在近 30 天内销量增长 10.8%，内部适配度达到 79.8，但当前仅覆盖 2 个 SKC，建议优先扩展 A-Line + Chiffon 相关款式。",
  },
};

/** 预填数据；null 表示手工新建。后续一键创建时赋值即可。 */
let createProposalPrefill = null;

let createProposalUi = {
  hasFabric: "是",
  reuse: "是",
  source: "Trend",
  sizeType: "基础码",
  proposer: "admin",
  showErrors: false,
  frontUploaded: false,
};

function setCreateProposalPrefill(data) {
  createProposalPrefill = data ? { ...data } : null;
  if (data?.source) createProposalUi.source = data.source;
  if (data?.proposer) createProposalUi.proposer = data.proposer;
}

function openCreateProposalWithPrefill(presetKeyOrData) {
  const data =
    typeof presetKeyOrData === "string"
      ? CREATE_PROPOSAL_PRESETS[presetKeyOrData]
      : presetKeyOrData;
  setCreateProposalPrefill(data || null);
  createProposalUi.showErrors = false;
  window.__keepCreatePrefill = true;
  if (typeof navigate === "function") navigate("proposal-create");
}

function getCpValue(key, fallback = "") {
  if (createProposalPrefill && createProposalPrefill[key] != null && createProposalPrefill[key] !== "") {
    return createProposalPrefill[key];
  }
  return fallback;
}

function cpEvidenceHint(source) {
  const map = {
    Internal: "Internal：请填写搜索词 / 定制数据等内部证据。",
    Competitor: "Competitor：请填写品牌名 + 链接 + 截图。",
    Trend: "Trend：请填写关键词 + 平台 + 截图。",
    Original: "Original：请填写设计说明（约 150 字）。",
    Social: "Social：请补充社媒平台、热词与截图。",
    Manual: "Manual：请说明人工创建背景与依据。",
  };
  return map[source] || map.Trend;
}

function renderCpUpload(sideLabel, required, multi = false) {
  const req = required ? `<span class="cp-req">*</span>` : "";
  const tips = multi
    ? "点击或拖拽上传图片<br />最多 5 张，jpg/png，不超过 5MB"
    : "点击上传图片<br />限 1 张，jpg/png，不超过 5MB";
  return `
    <div class="cp-row cp-row--upload">
      <div class="cp-label">${req}${sideLabel}</div>
      <div class="cp-upload-block">
        <div class="cp-upload-previews ${multi ? "is-multi" : ""}">
          ${
            multi
              ? `<div class="cp-ph"></div><div class="cp-ph"></div><div class="cp-ph"></div>`
              : `<div class="cp-ph cp-ph--lg"></div>`
          }
        </div>
        <button type="button" class="cp-upload-box" data-toast="cp-upload">
          <strong>点击上传图片</strong>
          <span>${tips}</span>
        </button>
      </div>
    </div>
  `;
}

function renderProposalCreateForm() {
  const source = createProposalUi.source || getCpValue("source", "Trend");
  const hasFabric = createProposalUi.hasFabric;
  const reuse = createProposalUi.reuse;
  const err = createProposalUi.showErrors;
  const hasLink = !!(getCpValue("caseId") || getCpValue("recId") || getCpValue("fromModule"));

  const line = getCpValue("line");
  const category = getCpValue("category");
  const proposer = getCpValue("proposer", createProposalUi.proposer || "admin");
  const price = getCpValue("price");
  const fabricName = getCpValue("fabricName", "Stretch Chiffon");
  const scene = getCpValue("scene");
  const design = getCpValue("design");
  const evidence = getCpValue(
    "evidence",
    "不同来源分别必须填写：\nInternal：搜索词 / 定制数据\nCompetitor：品牌名 + 链接 + 截图\nTrend：关键词 + 平台 + 截图\nOriginal：设计说明（150 字）"
  );

  return `
    <div class="page-stack cp-page">
      <section class="cp-sheet">
        <div class="cp-sheet__head">
          <div>
            <h2>创建提案</h2>
            <p>承接机会池、内部建议、竞品趋势或人工原创，提交至选款管理系统。</p>
          </div>
          <span class="tag tag--orange">草稿</span>
        </div>

        ${
          hasLink
            ? `
          <div class="cp-link-banner">
            <div><span>关联 Case ID</span><strong>${getCpValue("caseId") || "—"}</strong></div>
            <div><span>关联建议编号</span><strong>${getCpValue("recId") || "—"}</strong></div>
            <div><span>来源模块</span><strong>${getCpValue("fromModule") || "—"}</strong></div>
            <div>${renderTag(getCpValue("prefillTag", "系统预填"), "purple")}</div>
          </div>
        `
            : ""
        }

        ${err ? `<div class="cp-error">请先填写业务线、品类、正面图、提案佐证和目标价格</div>` : ""}

        <div class="cp-section">
          <h3 class="cp-section__title">基础信息</h3>
          <div class="cp-form">
            <div class="cp-row">
              <label class="cp-label"><span class="cp-req">*</span>业务线</label>
              <select class="cp-control${err && !line ? " is-invalid" : ""}" data-cp-field="line">
                <option value="">请选择业务线</option>
                ${["BD", "WD", "MOB", "Atelier", "Prom"]
                  .map((o) => `<option${line === o ? " selected" : ""}>${o}</option>`)
                  .join("")}
              </select>
            </div>
            <div class="cp-row">
              <label class="cp-label"><span class="cp-req">*</span>品类</label>
              <select class="cp-control${err && !category ? " is-invalid" : ""}" data-cp-field="category">
                <option value="">请选择品类</option>
                ${["Bridesmaid Dresses", "Wedding Dresses", "Mother Dresses", "Formal Dresses"]
                  .map((o) => `<option${category === o ? " selected" : ""}>${o}</option>`)
                  .join("")}
              </select>
            </div>
            <div class="cp-row">
              <label class="cp-label"><span class="cp-req">*</span>新款来源</label>
              <select class="cp-control" data-cp-ui="source">
                ${["Internal", "Competitor", "Trend", "Original", "Social", "Manual"]
                  .map((o) => `<option${source === o ? " selected" : ""}>${o}</option>`)
                  .join("")}
              </select>
            </div>
            <div class="cp-row">
              <label class="cp-label"><span class="cp-req">*</span>提案人</label>
              <div class="cp-people">
                <span class="cp-person-tag" data-cp-remove-person>${proposer} <em>×</em></span>
                <select class="cp-control cp-control--sm" data-cp-ui="proposer">
                  ${["admin", "Shelly", "Marcus Lee", "Kevin Wu"]
                    .map((o) => `<option${proposer === o ? " selected" : ""}>${o}</option>`)
                    .join("")}
                </select>
              </div>
            </div>
          </div>
        </div>

        <div class="cp-section">
          <h3 class="cp-section__title">选款信息</h3>
          <div class="cp-form">
            ${renderCpUpload("正面图", true, false)}
            ${renderCpUpload("背面图", false, false)}
            ${renderCpUpload("细节图", false, true)}
            <div class="cp-row cp-row--top">
              <label class="cp-label"><span class="cp-req">*</span>提案佐证</label>
              <div class="cp-editor${err ? " is-invalid" : ""}">
                <div class="cp-editor__toolbar" aria-label="富文本工具栏">
                  <button type="button" title="加粗"><b>B</b></button>
                  <button type="button" title="斜体"><i>I</i></button>
                  <button type="button" title="下划线"><u>U</u></button>
                  <button type="button" title="删除线"><s>S</s></button>
                  <span class="cp-editor__sep"></span>
                  <button type="button" title="段落">¶</button>
                  <button type="button" title="有序列表">1.</button>
                  <button type="button" title="无序列表">•</button>
                  <button type="button" title="链接">Link</button>
                  <button type="button" title="图片">Img</button>
                </div>
                <textarea class="cp-editor__body" data-cp-field="evidence" rows="8" placeholder="请填写提案佐证">${evidence}</textarea>
                <p class="cp-hint">${cpEvidenceHint(source)}</p>
              </div>
            </div>
            <div class="cp-row">
              <label class="cp-label"><span class="cp-req">*</span>目标价格</label>
              <input class="cp-control${err && !price ? " is-invalid" : ""}" data-cp-field="price" type="text" placeholder="例如：$200-300" value="${price}" />
            </div>
          </div>
        </div>

        <div class="cp-section">
          <h3 class="cp-section__title">规格信息</h3>
          <div class="cp-form">
            <div class="cp-row">
              <label class="cp-label"><span class="cp-req">*</span>尺码类型</label>
              <div class="cp-radios">
                ${["基础码", "Plus码", "全码"]
                  .map(
                    (o) => `
                  <label class="cp-radio">
                    <input type="radio" name="cp-size" data-cp-ui="sizeType" value="${o}"${createProposalUi.sizeType === o ? " checked" : ""} />
                    <span>${o}</span>
                  </label>
                `
                  )
                  .join("")}
              </div>
            </div>
            <div class="cp-row">
              <label class="cp-label"><span class="cp-req">*</span>已有面料</label>
              <div class="cp-radios">
                ${["是", "否"]
                  .map(
                    (o) => `
                  <label class="cp-radio">
                    <input type="radio" name="cp-fabric" data-cp-ui="hasFabric" value="${o}"${hasFabric === o ? " checked" : ""} />
                    <span>${o}</span>
                  </label>
                `
                  )
                  .join("")}
              </div>
            </div>
            <div class="cp-row">
              <label class="cp-label"><span class="cp-req">*</span>可复用旧版</label>
              <div class="cp-radios">
                ${["是", "否"]
                  .map(
                    (o) => `
                  <label class="cp-radio">
                    <input type="radio" name="cp-reuse" data-cp-ui="reuse" value="${o}"${reuse === o ? " checked" : ""} />
                    <span>${o}</span>
                  </label>
                `
                  )
                  .join("")}
              </div>
            </div>
            ${
              hasFabric === "是"
                ? `
              <div class="cp-row">
                <label class="cp-label"><span class="cp-req">*</span>面料名称</label>
                <input class="cp-control" data-cp-field="fabricName" type="text" placeholder="请输入面料名称" value="${fabricName}" />
              </div>
            `
                : `
              <div class="cp-row">
                <label class="cp-label">面料名称</label>
                <div class="cp-soft-tip">需开发新面料（当前「已有面料 = 否」）</div>
              </div>
            `
            }
            ${
              reuse === "否"
                ? `<div class="cp-soft-tip cp-soft-tip--bar">需补充打版类型与特殊工艺说明。</div>`
                : ""
            }
          </div>
        </div>

        <div class="cp-section">
          <h3 class="cp-section__title">补充信息</h3>
          <div class="cp-form">
            <div class="cp-row cp-row--top">
              <label class="cp-label">穿着场景</label>
              <textarea class="cp-control" data-cp-field="scene" rows="3" placeholder="请输入穿着场景">${scene}</textarea>
            </div>
            <div class="cp-row cp-row--top">
              <label class="cp-label">关键设计点</label>
              <textarea class="cp-control" data-cp-field="design" rows="3" placeholder="请输入关键设计点">${design}</textarea>
            </div>
            <div class="cp-row cp-row--top">
              <label class="cp-label">特殊工艺说明</label>
              <textarea class="cp-control" data-cp-field="craft" rows="3" placeholder="请输入特殊工艺说明"></textarea>
            </div>
            <div class="cp-row">
              <label class="cp-label">打版类型</label>
              <select class="cp-control" data-cp-field="pattern">
                <option value="">请选择打版类型</option>
                ${["新版型", "旧版微调", "旧版复用", "改色", "改面料", "改细节"]
                  .map((o) => `<option>${o}</option>`)
                  .join("")}
              </select>
            </div>
            <div class="cp-row">
              <label class="cp-label">状态</label>
              <div>${renderTag("草稿", "orange")}</div>
            </div>
          </div>
        </div>

        <div class="cp-footer">
          <button type="button" class="btn btn-secondary" data-cp-save>保存草稿</button>
          <button type="button" class="btn btn-primary" data-cp-submit>提交提案</button>
        </div>
      </section>
    </div>
  `;
}
