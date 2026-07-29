const pageMeta = {
  dashboard: {
    title: "刊登任务",
    description: "以任务工作台承接筛选、处理、审核流转和异常回看。",
  },
  "new-task": {
    title: "新建刊登任务",
    description: "按标准素材包录入基础信息，完成 AI 生成前的准备动作。",
  },
  review: {
    title: "AI结果与审核",
    description: "把图片判断、文本修订和双人审核合并在同一工作面内完成。",
  },
  users: {
    title: "用户管理",
    description: "以最小治理成本承接账号新增、角色管理与启停控制。",
  },
};

const sampleGoodsId = "1079007";
const sampleDdid = "377518";
const sampleStyleNameCn = "Harlow 礼服";
const sampleStyleNameEn = "Harlow";
const necklineOptions = [
  "one-shoulder单肩领",
  "Off-the-shoulder卡肩领",
  "High Neck高领",
  "Square Neckline方领",
  "Cowl Neck垂褶领",
  "V-neckV字领",
  "Sweetheart心形领",
  "Scoop大圆领",
  "Straight平直领",
  "Illusion透视领",
  "Halter挂脖领",
  "Boatneck一字领",
  "Convertible可变换领型",
  "Strapless抹胸",
];
const silhouetteOptions = [
  "A-LineA字裙",
  "Ball-Gown舞会袍",
  "Empire高腰裙",
  "Mermaid鱼尾裙",
  "Jumpsuit连体裤",
  "Sheath紧身裙",
];
const sleevesOptions = [
  "Long Sleeve长袖",
  "Short Sleeve短袖",
  "Off The Shoulder露肩",
  "Strapless无肩带",
  "Spaghettistraps细肩带",
  "Sleeveless无袖",
  "Sleeves有袖子",
  "Cap straps包肩",
  "Straps肩带",
];
const featuresOptions = [
  "Pockets口袋",
  "Side slit侧开衩",
  "Convertible可变换式",
  "Beaded钉珠",
  "Belt腰带",
  "Sash飘片",
  "Belt/Sash系带装饰",
  "Bow蝴蝶结",
  "Without Slit无开衩",
  "Corset束身设计",
  "Detachable Sleeves可拆卸袖子",
  "Detachable Straps可拆卸肩带",
];
const backStyleOptions = [
  "Bow/Tie Back后背蝴蝶结 / 系带",
  "covered button包扣",
  "Crossed Straps后背交叉肩带",
  "Illusion后背透视",
  "Keyhole后背钥匙孔镂空",
  "laceup后背绑带",
  "ScoopU形露背",
  "Straight平直后背",
  "V backV形露背",
  "Zipper Up at Side侧面拉链",
];
const embellishmentOptions = [
  "Lace蕾丝",
  "Ruffle褶皱",
  "Pleated百褶",
  "Ruched抽褶",
  "Cascading Ruffles荷叶边",
  "Beaded缝珠",
  "Bow(s)蝴蝶结",
  "Sequins亮片",
  "Split Front开衩",
];
const fabricOptions = [
  "Chiffon雪纺",
  "Stretch Satin弹力缎面",
  "Metallic Satin金属光泽缎面",
  "Velvet天鹅绒",
  "Floral Burnout花卉烂花面料",
  "Mesh网纱",
  "Stretch Crepe弹力绉布",
  "Stretch Chiffon弹力雪纺",
  "Luxe Knit奢华针织面料",
  "Tulle薄纱网",
  "Bloom花卉面料",
  "Blossom花朵面料",
  "Dreamy Floral梦幻花卉面料",
  "Embroidered Sequin亮片刺绣面料",
  "Floral Burnout Jacquard花卉烂花提花面料",
  "Floral Jacquard花卉提花面料",
  "Matte Satin哑光缎面",
  "Jacquard提花面料",
  "Lace蕾丝",
  "Mesh Sequin亮片网纱",
  "Mikado厚缎",
  "Printed Chiffon印花雪纺",
  "Sequins亮片",
  "viscose粘胶纤维",
  "Watercolor Floral水彩花卉印花面料",
];
const mainFabricOptions = [
  "Tulle网纱",
  "Chiffon雪纺",
  "Stretch Satin水晶麻",
  "Metallic Satin金属光泽缎面",
  "velvet天鹅绒",
  "Floral Burnout花卉烂花面料",
  "Stretch Crepe弹力绉布",
  "Stretch Chiffon弹力雪纺",
  "Lace蕾丝",
  "Luxe Knit高级针织面料",
  "Mesh网眼布",
  "MatteSatin缎布",
  "Blossom花朵面料",
  "Bloom花卉面料",
  "Charmeuse柔光缎",
  "Crinkle Chiffon皱褶雪纺",
  "Dreamy Floral梦幻花卉面料",
  "Floral Jacquard花卉提花面料",
  "Jacquard提花面料",
  "Jersey针织平纹布",
  "Mesh Sequin亮片网纱",
  "Mikado厚缎",
  "Printed Chiffon印花雪纺",
  "Sequined亮片",
  "Shimmer Knit闪光针织面料",
  "Signature Sequin特色亮片面料",
  "Viscose粘胶纤维",
  "Watercolor Floral水彩花卉印花面料",
];
const lengthOptions = [
  "Ankle-Length九分裙",
  "Tea-Length七分裙",
  "Knee-Length及膝",
  "Floor-Length及地长",
  "Asymmetrical不对称尾",
  "Midi Length中长裙",
  "Ballerina Length芭蕾裙长",
  "Short/Mini短装/迷你",
  "Cathedral Train(拖尾80cm)",
  "ChapelTrain(拖尾60cm)",
  "CourtTrain小拖(拖尾45cm)",
  "SweepTrain很小的拖(拖尾15cm、拖尾30cm)",
];
const highestPointOptions = [
  "Ankle-Length九分裙",
  "Ballerina Length八分裙",
  "Floor-Length及地长",
  "Knee-Length及膝",
  "Knee-up膝上",
  "Midi Length中长裙",
  "Short/Mini短装/迷你",
  "Tea-Length七分裙",
];
const lowestPointOptions = [
  "Ankle-Length九分裙",
  "Ballerina Length八分裙",
  "Floor-Length及地长",
  "Knee-Length及膝",
  "Knee-up膝上",
  "MidiLength中长裙",
  "Short/Mini短装/迷你",
  "Tea-Length七分裙",
];
const yesNoOptions = ["yes", "no"];
const liningOptions = [
  "fully lined全里衬",
  "stretch lining弹力里衬",
];
const typeOfClosureOptions = [
  "Hidden back zipper后背隐形拉链",
  "Hidden side zipper侧边隐形拉链",
  "Hook and eye closure钩眼扣 / 风纪扣闭合",
  "Button closure纽扣闭合",
  "Covered back zipper遮盖式后背拉链",
  "Elastic waistband松紧腰",
  "Half button半纽扣式闭合",
  "Half corset半绑带式束身",
  "No Zipper无拉链",
  "Tie halter系带挂脖",
];
const hookAndEyeOptions = [
  "metal hook and eye金属钩眼扣",
  "metal hook and thread eye金属钩 + 线环扣",
  "no hook and eye无钩眼扣",
];
const sampleDescriptionCn =
  "Harlow 伴娘礼服采用双件弹力缎面设计，整体为及地修身廓形，搭配平直领口与可拆卸细肩带。柔和褶皱和灵感来自 peplum 的腰部结构强化了上身线条，后背绑带与自系蝴蝶结完成收束，后中开衩并配有同款颈巾。";
const sampleDescriptionEn =
  "The Harlow bridesmaid dress is a two-piece stretch satin design featuring a floor-length sheath skirt and a strapless top with a straight neckline and detachable spaghetti straps. Soft pleating, a peplum-inspired waist, and a lace-up back with a self-tie bow define the structured bodice, while the clean skirt is finished with a back slit and complemented by a matching neck scarf.";
const sampleAttributes = {
  color: "Dusty Blue",
  neckline: "Straight平直领",
  silhouette: "Sheath紧身裙",
  sleeves: "Spaghettistraps细肩带",
  backStyle: ["laceup后背绑带"],
  embellishment: ["Pleated百褶"],
  fabric: ["Stretch Satin弹力缎面"],
  mainFabric: ["Stretch Satin水晶麻"],
  length: ["Floor-Length及地长"],
  highestPoint: ["Floor-Length及地长"],
  lowestPoint: ["Floor-Length及地长"],
  boning: "yes",
  padding: "no",
  rushProduction: "yes",
  lining: "stretch lining弹力里衬",
  typeOfClosure: ["Half corset半绑带式束身"],
  hookAndEye: "no hook and eye无钩眼扣",
  onlineSize: "US2, US4, US6, US8, US10, US12, US14, US16",
  features: ["Detachable Straps可拆卸肩带"],
};

const currentTaskDraft = {
  rushProduction: sampleAttributes.rushProduction,
};

const uploadAssets = [
  {
    title: "图片素材",
    file: "front.jpg、back.jpg",
    note: "支持上传多张图片，最少 1 张，最多 3 张",
    actions: ["上传", "替换", "查看", "删除"],
  },
  {
    title: "工艺备注",
    file: "craft-note.docx",
    note: "上传格式为 Word（.doc / .docx）",
    actions: ["上传", "替换", "查看", "删除"],
  },
];

const modelLibrary = {
  selectedName: "Mila Chen",
  note: "选择模特后在此处展示预览图，具体可用模特信息放在模特库管理弹窗内查看。",
};

const reviewFieldSections = [
  {
    title: "价格与基础信息",
    description: "人工确认字段和任务基础字段优先放在最上方，便于先核对推送前必填项。",
    fields: [
      { label: "Goods ID", value: sampleGoodsId },
      { label: "DDID", value: sampleDdid },
      { label: "Base Price", value: "89.00" },
      { label: "US Price", value: "129.00" },
      { label: "Rush Production", value: currentTaskDraft.rushProduction },
    ],
  },
  {
    title: "标题与描述",
    description: "补回 CN team 与 US team 的标题、描述字段，方便审核页直接查看完整文案结果。",
    fields: [
      { label: "Style Name (CN team)", value: sampleStyleNameCn },
      { label: "Style Name (US team)", value: sampleStyleNameEn },
      {
        label: "Description (CN team)",
        type: "textarea",
        full: true,
        value: sampleDescriptionCn,
      },
      {
        label: "Description (US team)",
        type: "textarea",
        full: true,
        value: sampleDescriptionEn,
      },
    ],
  },
  {
    title: "商品属性",
    description: "以下字段与 MVP 文档保持一致，作为 AI 优先生成、人工审核修订的核心属性区。",
    fields: [
      { label: "Online Color", value: sampleAttributes.color },
      {
        label: "Neckline（可多选，必选）",
        type: "select",
        multiple: true,
        required: true,
        options: necklineOptions,
        value: [sampleAttributes.neckline],
      },
      {
        label: "Silhouette（单选，必选）",
        type: "select",
        options: silhouetteOptions,
        value: sampleAttributes.silhouette,
      },
      {
        label: "Sleeves（单选，必选）",
        type: "select",
        options: sleevesOptions,
        value: sampleAttributes.sleeves,
      },
      {
        label: "Back Style（可多选，必选）",
        type: "select",
        multiple: true,
        required: true,
        options: backStyleOptions,
        value: sampleAttributes.backStyle,
      },
      {
        label: "Embellishment（可多选，可不选）",
        type: "select",
        multiple: true,
        options: embellishmentOptions,
        value: sampleAttributes.embellishment,
      },
      {
        label: "Fabric（可多选，必选）",
        type: "select",
        multiple: true,
        required: true,
        options: fabricOptions,
        value: sampleAttributes.fabric,
      },
      {
        label: "Main Fabric（可多选，必选）",
        type: "select",
        multiple: true,
        required: true,
        options: mainFabricOptions,
        value: sampleAttributes.mainFabric,
      },
      {
        label: "Length（可多选，必选）",
        type: "select",
        multiple: true,
        required: true,
        options: lengthOptions,
        value: sampleAttributes.length,
      },
      {
        label: "Highest Point（可多选，可不选）",
        type: "select",
        multiple: true,
        options: highestPointOptions,
        value: sampleAttributes.highestPoint,
      },
      {
        label: "Lowest Point（可多选，可不选）",
        type: "select",
        multiple: true,
        options: lowestPointOptions,
        value: sampleAttributes.lowestPoint,
      },
      {
        label: "Boning（单选，必选）",
        type: "select",
        required: true,
        options: yesNoOptions,
        value: sampleAttributes.boning,
      },
      {
        label: "Padding（单选，必选）",
        type: "select",
        required: true,
        options: yesNoOptions,
        value: sampleAttributes.padding,
      },
      {
        label: "Lining（单选，必选）",
        type: "select",
        required: true,
        options: liningOptions,
        value: sampleAttributes.lining,
      },
      {
        label: "Type of Closure（可多选，必选）",
        type: "select",
        multiple: true,
        required: true,
        options: typeOfClosureOptions,
        value: sampleAttributes.typeOfClosure,
      },
      {
        label: "Hook and Eye（单选，必选）",
        type: "select",
        required: true,
        options: hookAndEyeOptions,
        value: sampleAttributes.hookAndEye,
      },
      {
        label: "Features（可多选，可不选）",
        type: "select",
        multiple: true,
        options: featuresOptions,
        value: sampleAttributes.features,
      },
      {
        label: "Online Size",
        type: "textarea",
        full: true,
        value: sampleAttributes.onlineSize,
      },
    ],
  },
  {
    title: "AI提取依据",
    description: "保留 AI 依据摘要，便于审核人理解字段来源并形成后续反馈闭环。",
    fields: [
      {
        label: "AI提取依据摘要",
        type: "textarea",
        full: true,
        value:
          "来源于工艺备注、图片纹理、尺码表和历史同类商品字段映射，当前建议人工重点复核 neckline、embellishment、type_of_closure 与英文化表达。",
      },
    ],
  },
];

const reviewStructuredSections = reviewFieldSections.filter((section) =>
  ["价格与基础信息", "标题与描述", "商品属性"].includes(section.title)
);

const taskRows = [
  {
    no: "T20260715001",
    goods: sampleGoodsId,
    ddid: sampleDdid,
    category: "BD",
    ai: "AI生成完成",
    aiClass: "success",
    audit: "待美国团队审核",
    auditClass: "processing",
    push: "未推送",
    pushClass: "waiting",
    owner: "Mia",
    creator: "Lucy",
    time: "2026-07-15 10:24",
  },
  {
    no: "T20260715002",
    goods: "1079012",
    ddid: "377524",
    category: "BD",
    ai: "AI生成中",
    aiClass: "processing",
    audit: "待上海运营审核",
    auditClass: "waiting",
    push: "未推送",
    pushClass: "waiting",
    owner: "Lucy",
    creator: "Lucy",
    time: "2026-07-15 11:08",
  },
  {
    no: "T20260715003",
    goods: "1079028",
    ddid: "377531",
    category: "BD",
    ai: "AI生成失败",
    aiClass: "danger",
    audit: "待上海运营审核",
    auditClass: "waiting",
    push: "推送失败",
    pushClass: "danger",
    owner: "管理员",
    creator: "Amy",
    time: "2026-07-15 11:46",
  },
];

const renderers = {
  dashboard: renderDashboard,
  "new-task": renderNewTask,
  review: renderReview,
  users: renderUsers,
};

const routes = Object.keys(renderers);
const app = document.getElementById("app");
const titleEl = document.getElementById("page-title");
const descriptionEl = document.getElementById("page-description");
const workspaceEl = document.querySelector(".workspace");

function getRoute() {
  const hash = window.location.hash.replace("#", "");
  return routes.includes(hash) ? hash : "dashboard";
}

function setActive(route) {
  document.querySelectorAll(".sidenav-link").forEach((node) => {
    node.classList.toggle("is-active", node.dataset.route === route);
  });
}

function render() {
  const route = getRoute();
  const meta = pageMeta[route];
  titleEl.textContent = meta.title;
  descriptionEl.textContent = meta.description;
  setActive(route);
  app.innerHTML = renderers[route]();
  if (workspaceEl) {
    workspaceEl.scrollTop = 0;
  }
}

function tag(text, kind) {
  return `<span class="tag tag--${kind}">${text}</span>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatValue(value) {
  return Array.isArray(value) ? value.join("、") : value;
}

function renderSelectField(field, className) {
  const selectedValues = Array.isArray(field.value) ? field.value : [field.value];
  const summary = field.multiple
    ? selectedValues.length
      ? selectedValues.join("、")
      : "请选择"
    : selectedValues[0] || "请选择";
  return `
    <div class="${className}">
      <label>${field.label}</label>
      <div
        class="multi-select"
        data-multiselect
        data-multiple="${field.multiple ? "true" : "false"}"
        data-required="${field.required ? "true" : "false"}"
        data-selected="${escapeHtml(JSON.stringify(selectedValues))}"
      >
        <button type="button" class="multi-select__trigger" data-multiselect-trigger aria-expanded="false">
          <span class="multi-select__value">${escapeHtml(summary)}</span>
          <span class="multi-select__arrow">▾</span>
        </button>
        <div class="multi-select__panel">
          ${field.options
            .map((option) => {
              const isSelected = selectedValues.includes(option);
              return `
                <button
                  type="button"
                  class="multi-select__option${isSelected ? " is-selected" : ""}"
                  data-multiselect-option
                  data-value="${escapeHtml(option)}"
                >
                  <span>${escapeHtml(option)}</span>
                  <span class="multi-select__check">${isSelected ? "已选" : ""}</span>
                </button>
              `;
            })
            .join("")}
        </div>
      </div>
    </div>
  `;
}

function renderField(field) {
  const className = field.full ? "field field--full" : "field";
  if (field.type === "select") {
    return renderSelectField(field, className);
  }

  if (field.type === "textarea") {
    return `
      <div class="${className}">
        <label>${field.label}</label>
        <textarea>${field.value}</textarea>
      </div>
    `;
  }

  return `
    <div class="${className}">
      <label>${field.label}</label>
      <input value="${field.value}" />
    </div>
  `;
}

function renderFieldSection(section) {
  return `
    <section class="form-section">
      <div>
        <h4>${section.title}</h4>
        <p>${section.description}</p>
      </div>
      <div class="field-group">
        ${section.fields.map(renderField).join("")}
      </div>
    </section>
  `;
}

function renderDashboard() {
  const rows = taskRows
    .map(
      (row) => `
        <tr>
          <td>
            <strong>${row.no}</strong>
            <span class="table-sub">精品路线 / ${row.category}</span>
          </td>
          <td>${row.goods}</td>
          <td>${row.ddid}</td>
          <td>${row.category}</td>
          <td>${tag(row.ai, row.aiClass)}</td>
          <td>${tag(row.audit, row.auditClass)}</td>
          <td>${tag(row.push, row.pushClass)}</td>
          <td>${row.owner}</td>
          <td>${row.creator}</td>
          <td>${row.time}</td>
          <td>
            <button class="table-link" data-route="review">处理</button>
          </td>
        </tr>
      `
    )
    .join("");

  return `
    <div class="page">
      <section class="summary-grid">
        <article class="summary-card">
          <span>今日新增任务</span>
          <strong>18</strong>
          <span>较昨日 +4，精品路线占 100%</span>
        </article>
        <article class="summary-card">
          <span>待上海运营审核</span>
          <strong>07</strong>
          <span>AI结果已完成，等待中文与图片核对</span>
        </article>
        <article class="summary-card">
          <span>待美国团队审核</span>
          <strong>05</strong>
          <span>英文表达与标题描述待确认</span>
        </article>
        <article class="summary-card">
          <span>推送异常任务</span>
          <strong>02</strong>
          <span>建议优先处理失败重试与异常回流</span>
        </article>
      </section>

      <section class="card">
        <div class="card-header">
          <div>
            <h3>任务筛选</h3>
            <p>围绕状态、创建人和关键标识快速定位当前待处理任务。</p>
          </div>
          <div class="pill-row">
            <span class="chip is-active">全部任务</span>
            <span class="chip">待我处理</span>
            <span class="chip">待审核</span>
            <span class="chip">推送失败</span>
          </div>
        </div>
        <div class="filter-grid">
          <div class="field">
            <label>品类</label>
            <select><option>BD</option></select>
          </div>
          <div class="field">
            <label>审核状态</label>
            <select><option>全部</option></select>
          </div>
          <div class="field">
            <label>AI状态</label>
            <select><option>全部</option></select>
          </div>
          <div class="field">
            <label>盘古推送状态</label>
            <select><option>全部</option></select>
          </div>
          <div class="field">
            <label>创建人</label>
            <select><option>全部</option></select>
          </div>
          <div class="field">
            <label>Goods ID</label>
            <input placeholder="输入 1079007" />
          </div>
          <div class="field">
            <label>DDID</label>
            <input placeholder="输入 377518" />
          </div>
          <div class="field">
            <label>创建时间</label>
            <input value="2026-07-15 至 2026-07-15" />
          </div>
        </div>
      </section>

      <section class="table-card">
        <div class="table-toolbar">
          <div>
            <h3>刊登任务列表</h3>
            <p>共 18 条记录，当前聚焦 3 条重点样例任务。</p>
          </div>
          <div class="hero-actions">
            <button class="secondary-btn">重置筛选</button>
            <button class="primary-btn" data-route="new-task">+ 新建刊登任务</button>
          </div>
        </div>
        <div class="table-wrap">
          <table class="task-table">
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
            <tbody>${rows}</tbody>
          </table>
        </div>
        <div class="pagination">
          <span class="chip is-active">1</span>
          <span class="chip">2</span>
          <span class="chip">3</span>
        </div>
      </section>
    </div>
  `;
}

function renderNewTask() {
  return `
    <div class="page">
      <section class="card">
        <div class="section-title">
          <div>
            <h3>基础信息</h3>
            <p>先确认本次刊登任务的品类、标识与价格基线。</p>
          </div>
          ${tag("上海运营可编辑", "processing")}
        </div>
        <div class="form-grid">
          <div class="field">
            <label>品类</label>
            <select><option>BD</option></select>
          </div>
          <div class="field">
            <label>路线类型</label>
            <select><option>精品路线</option></select>
          </div>
          <div class="field">
            <label>Goods ID</label>
            <input value="${sampleGoodsId}" />
          </div>
          <div class="field">
            <label>DDID</label>
            <input value="${sampleDdid}" />
          </div>
          <div class="field">
            <label>Base Price</label>
            <input value="89.00" />
          </div>
          <div class="field">
            <label>US Price</label>
            <input value="129.00" />
          </div>
          <div class="field">
            <label>Rush Production</label>
            <select data-draft-field="rushProduction">
              ${yesNoOptions
                .map(
                  (option) => `
                    <option value="${option}"${option === currentTaskDraft.rushProduction ? " selected" : ""}>${option}</option>
                  `
                )
                .join("")}
            </select>
          </div>
          <div class="field field--full">
            <label>业务备注</label>
            <textarea>本批次优先验证 BD 品类精品路线的自动刊登闭环，要求输出正面、背面、侧面图并保留 AI 留痕。</textarea>
          </div>
        </div>
      </section>

      <section class="card">
        <div class="section-title">
          <div>
            <h3>素材上传</h3>
            <p>按素材类型分别上传，保证图片与工艺文档状态清晰可见。</p>
          </div>
          <button class="ghost-btn">下载模板说明</button>
        </div>
        <div class="upload-list">
          ${uploadAssets
            .map(
              ({ title, file, note, actions }) => `
                <div class="upload-row">
                  <div class="upload-meta">
                    <strong>${title}</strong>
                    <div class="muted">${file}</div>
                    <div class="form-hint">${note}</div>
                  </div>
                  <div class="upload-actions">
                    ${actions
                      .map((action, index) => {
                        const className =
                          action === "删除"
                            ? "danger-btn"
                            : index === 0
                              ? "secondary-btn"
                              : "ghost-btn";
                        return `<button class="${className}">${action}</button>`;
                      })
                      .join("")}
                  </div>
                </div>
              `
            )
            .join("")}
        </div>
      </section>

      <section class="card">
        <div class="section-title">
          <div>
            <h3>模特库</h3>
            <p>先选择本次任务使用的模特，当前页面只展示已选模特预览。</p>
          </div>
          <div class="hero-actions">
            <button class="ghost-btn">模特库管理</button>
            <button class="secondary-btn">选择模特</button>
          </div>
        </div>
        <div class="model-library">
          <div class="model-library__selected">
            <div class="model-library__visual" aria-hidden="true"></div>
            <div class="model-library__summary">
              <strong>已选模特预览</strong>
              <h4>${modelLibrary.selectedName}</h4>
              <p class="form-hint">${modelLibrary.note}</p>
            </div>
          </div>
        </div>
      </section>

      <section class="card sticky-actions">
        <div>
          <strong>任务将在保存后进入 AI 生成阶段</strong>
          <p class="muted">系统会自动抽取文本字段、生成标题描述并完成一站式换装。</p>
        </div>
        <div class="hero-actions">
          <button class="secondary-btn" data-route="dashboard">取消</button>
          <button class="primary-btn" data-route="review">保存并发起AI生成</button>
        </div>
      </section>
    </div>
  `;
}

function renderReview() {
  return `
    <div class="page">
      <section class="review-shell">
        <div class="review-top">
          <div>
            <div class="eyebrow">Task Context</div>
            <h3>任务 T20260715001</h3>
            <p class="muted">Goods ID ${sampleGoodsId} · DDID ${sampleDdid} · 当前阶段为待美国团队审核</p>
          </div>
          <div class="review-badges">
            ${tag("AI生成完成", "success")}
            ${tag("待美国团队审核", "processing")}
            ${tag("当前处理人 Mia", "waiting")}
          </div>
        </div>

        <section class="card">
          <div class="card-header">
            <div>
              <h3>任务筛选</h3>
              <p>围绕状态、创建人和关键标识快速定位当前待处理任务。</p>
            </div>
            <div class="pill-row">
              <span class="chip is-active">全部任务</span>
              <span class="chip">待我处理</span>
              <span class="chip">已驳回</span>
              <span class="chip">推送失败</span>
            </div>
          </div>
          <div class="filter-grid">
            <div class="field">
              <label>品类</label>
              <select><option>BD</option></select>
            </div>
            <div class="field">
              <label>审核状态</label>
              <select><option>全部</option></select>
            </div>
            <div class="field">
              <label>AI状态</label>
              <select><option>全部</option></select>
            </div>
            <div class="field">
              <label>盘古推送状态</label>
              <select><option>全部</option></select>
            </div>
            <div class="field">
              <label>创建人</label>
              <select><option>全部</option></select>
            </div>
            <div class="field">
              <label>Goods ID</label>
              <input placeholder="输入 1079007" />
            </div>
            <div class="field">
              <label>DDID</label>
              <input placeholder="输入 377518" />
            </div>
            <div class="field">
              <label>创建时间</label>
              <input value="2026-07-15 至 2026-07-15" />
            </div>
          </div>
        </section>

        <div class="meta-grid meta-grid--review">
          <div class="metric-card"><span>品类</span><strong>BD</strong></div>
          <div class="metric-card"><span>路线类型</span><strong>精品路线</strong></div>
          <div class="metric-card"><span>已通过图片</span><strong>6 / 8</strong></div>
          <div class="metric-card"><span>盘古状态</span><strong>待推送</strong></div>
          <div class="metric-card"><span>上海运营已完成</span><strong>14:10</strong></div>
          <div class="metric-card"><span>美国团队状态</span><strong>待审核</strong></div>
          <div class="metric-card"><span>AI完成时间</span><strong>13:22</strong></div>
          <div class="metric-card"><span>创建时间</span><strong>2026-07-15 10:24</strong></div>
          <div class="metric-card"><span>更新时间</span><strong>2026-07-15 15:06</strong></div>
        </div>

        <div class="review-body">
          <article class="form-panel">
            <div class="split-header">
              <div>
                <h3>结构化字段</h3>
                <p>当前审核页先聚焦任务基础字段与商品属性，方便业务快速完成关键字段确认。</p>
              </div>
            </div>
            <div class="form-sections">
              ${reviewStructuredSections.map(renderFieldSection).join("")}
            </div>
          </article>

          <article class="gallery-panel">
            <div class="split-header">
              <div>
                <h3>图片工作区</h3>
                <p>把图片区放在结构化字段下方，方便字段确认后再统一看图与替换。</p>
              </div>
              <div class="pill-row">
                <span class="chip is-active">正面</span>
                <span class="chip">背面</span>
                <span class="chip">侧面</span>
                <span class="chip">其他</span>
              </div>
            </div>
            <div class="gallery-grid gallery-grid--four">
              ${["Front A", "Front B", "Back A", "Side A"].map(
                (label, index) => `
                  <div class="gallery-card">
                    <div class="gallery-visual"></div>
                    <div class="gallery-caption">
                      <div>
                        <strong>${label}</strong>
                        <span class="muted">AI生成图 · 顺位 ${index + 1}</span>
                      </div>
                      ${index < 3 ? tag("已通过", "success") : tag("待确认", "waiting")}
                    </div>
                    <div class="hero-actions">
                      <button class="ghost-btn">替换</button>
                      <button class="ghost-btn">排序</button>
                      <button class="ghost-btn">阅览</button>
                    </div>
                  </div>
                `
              ).join("")}
            </div>
          </article>
        </div>

        <div class="sticky-actions sticky-actions--review">
          <div class="hero-actions">
            <button class="ghost-btn">重置</button>
            <button class="secondary-btn">保存修改</button>
            <button class="secondary-btn">运营审核通过</button>
            <button class="primary-btn" data-route="dashboard">美国审核通过</button>
          </div>
        </div>
      </section>
    </div>
  `;
}

function renderUsers() {
  return `
    <div class="page">
      <section class="two-col">
        <article class="card">
          <div class="table-toolbar">
            <div>
              <h3>账号治理</h3>
              <p>保持轻量后台结构，只承接账号、角色和状态管理。</p>
            </div>
            <button class="primary-btn">新增账号</button>
          </div>
          <div class="table-wrap">
            <table class="user-table">
              <thead>
                <tr>
                  <th>用户名</th>
                  <th>角色</th>
                  <th>状态</th>
                  <th>创建时间</th>
                  <th>更新时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Lucy</strong><span class="table-sub">上海运营</span></td>
                  <td>sh_operator</td>
                  <td>${tag("启用", "success")}</td>
                  <td>2026-07-01</td>
                  <td>2026-07-15</td>
                  <td><button class="table-link">编辑</button> <button class="table-link">禁用</button></td>
                </tr>
                <tr>
                  <td><strong>Mia</strong><span class="table-sub">美国团队</span></td>
                  <td>us_reviewer</td>
                  <td>${tag("启用", "success")}</td>
                  <td>2026-07-02</td>
                  <td>2026-07-15</td>
                  <td><button class="table-link">编辑</button> <button class="table-link">禁用</button></td>
                </tr>
                <tr>
                  <td><strong>Admin</strong><span class="table-sub">系统管理员</span></td>
                  <td>admin</td>
                  <td>${tag("启用", "success")}</td>
                  <td>2026-06-20</td>
                  <td>2026-07-10</td>
                  <td><button class="table-link">编辑</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>

        <article class="card">
          <div class="section-title">
            <div>
              <h3>新增 / 编辑弹窗示意</h3>
              <p>这里用静态卡片模拟弹窗内容，后续很容易直接转成 Semi Modal。</p>
            </div>
            ${tag("管理员专属", "waiting")}
          </div>
          <div class="form-grid">
            <div class="field">
              <label>用户名</label>
              <input value="new.operator" />
            </div>
            <div class="field">
              <label>角色</label>
              <select><option>sh_operator</option></select>
            </div>
            <div class="field">
              <label>状态</label>
              <select><option>启用</option></select>
            </div>
            <div class="field">
              <label>默认队列</label>
              <select><option>上海运营</option></select>
            </div>
          </div>
          <div class="status-note">
            本期用户管理只保留最小治理能力，不引入复杂组织树和字段配置中心。
          </div>
          <div class="sticky-actions">
            <span class="muted">适合在视觉稿阶段转成弹窗或抽屉。</span>
            <div class="hero-actions">
              <button class="secondary-btn">取消</button>
              <button class="primary-btn">保存账号</button>
            </div>
          </div>
        </article>
      </section>
    </div>
  `;
}

function syncRoute(route) {
  window.location.hash = route;
}

function syncTaskDraftField(field, value) {
  if (field in currentTaskDraft) {
    currentTaskDraft[field] = value;
  }
}

function closeMultiSelects() {
  document.querySelectorAll("[data-multiselect].is-open").forEach((node) => {
    node.classList.remove("is-open");
    const trigger = node.querySelector("[data-multiselect-trigger]");
    if (trigger) {
      trigger.setAttribute("aria-expanded", "false");
    }
  });
}

function updateMultiSelect(root, selectedValues) {
  root.dataset.selected = JSON.stringify(selectedValues);
  const valueNode = root.querySelector(".multi-select__value");
  const isMultiple = root.dataset.multiple === "true";
  if (valueNode) {
    valueNode.textContent = isMultiple
      ? selectedValues.length
        ? selectedValues.join("、")
        : "请选择"
      : selectedValues[0] || "请选择";
  }

  root.querySelectorAll("[data-multiselect-option]").forEach((optionNode) => {
    const isSelected = selectedValues.includes(optionNode.dataset.value);
    optionNode.classList.toggle("is-selected", isSelected);
    const checkNode = optionNode.querySelector(".multi-select__check");
    if (checkNode) {
      checkNode.textContent = isSelected ? "已选" : "";
    }
  });
}

document.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-multiselect-trigger]");
  if (trigger) {
    const root = trigger.closest("[data-multiselect]");
    const shouldOpen = !root.classList.contains("is-open");
    closeMultiSelects();
    root.classList.toggle("is-open", shouldOpen);
    trigger.setAttribute("aria-expanded", String(shouldOpen));
    return;
  }

  const optionNode = event.target.closest("[data-multiselect-option]");
  if (optionNode) {
    const root = optionNode.closest("[data-multiselect]");
    const currentValues = JSON.parse(root.dataset.selected || "[]");
    const isMultiple = root.dataset.multiple === "true";
    const isRequired = root.dataset.required === "true";
    const value = optionNode.dataset.value;
    const selectedValues = isMultiple
      ? currentValues.includes(value)
        ? isRequired && currentValues.length === 1
          ? currentValues
          : currentValues.filter((item) => item !== value)
        : [...currentValues, value]
      : [value];
    updateMultiSelect(root, selectedValues);
    closeMultiSelects();
    return;
  }

  if (!event.target.closest("[data-multiselect]")) {
    closeMultiSelects();
  }

  const target = event.target.closest("[data-route]");
  if (target) {
    syncRoute(target.dataset.route);
  }
});

document.addEventListener("change", (event) => {
  const field = event.target.dataset.draftField;
  if (field) {
    syncTaskDraftField(field, event.target.value);
  }
});

window.addEventListener("hashchange", render);
render();
