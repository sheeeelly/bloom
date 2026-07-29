## 一、背景

### 1.1 业务背景

新品发布流程中，快速上架是业务关键动作。当前上新链路横跨中山产品研发、上海运营、美国团队、修图组等多个角色，文本信息和图片信息分别由人工处理，最终由上海运营和修图组在盘古系统完成上传与发布。
随着自动化选品能力逐步推进，业务侧需要建设一套与之衔接的自动刊登能力，承接自动化选品结果，并将商品从素材阶段更快转化为可上架状态。
### 1.2 本次MVP聚焦方向

本期 `MVP` 聚焦以下几个方向：
1. 标准化格式 
    - 文本信息： 
        - 可从图片或素材中提取基础信息，如服装特征、面料等
        - 需人工确认部分关键字段，如价格
        - 标题、描述等标准格式内容支持自动生成
        - 支持多语言翻译
    - 图片信息： 
        - 支持一站式换装，至少覆盖正面、背面、侧面
        - 可结合老系统已有能力进行能力调用
        - 选项图自动复色为后续能力，本期不纳入
2. 迭代路径 
    - 一期以半自动化为目标
    - 在推送盘古前保留人工抽查审核
    - 后续逐步演进为全自动化
3. 业务承接 
    - 承接自动化选品能力，为新品发布提供自动刊登闭环
4. 数据回收 
    - 本期先做过程留痕，不做可视化看板
    - 为后续分析 `人工 vs AI`、效率提升、人力节约打基础

### 1.3 现有原始业务流程

当前刊登 `SOP` 主要面向 `BD、JBD、mob、wd、fgd` 等品类，流程如下：
1. 上海运营根据上新要求，提前约一个半月向中山产品研发提出需求。
2. 中山产品研发提供全套纸样、激光纸样、尺码表、图片、工艺备注给到工厂，工厂负责生产。
3. 工厂生产完成后，将服装返还给中山产品研发；中山产品研发整理图片及对应属性，形成最终属性表。
4. 属性表传递到美国团队，由美国团队负责撰写商品描述并核对相关信息，重点确认翻译表达是否地道。
5. 上海运营拿到对应表格后，上传到盘古系统。
6. 修图组负责将图片上传到盘古。

### 1.4 当前痛点

1. 流程链路长，跨团队协作成本高，整体上新效率低。
2. 文本属性、图片处理、翻译表达分散在多个角色中，依赖人工传递，标准化不足。
3. 图片与文本处理高度依赖人工经验，质量稳定性和复用性不足。
4. 盘古推送前缺少统一的中间承接平台，无法形成标准化的审核与留痕流程。
5. 自动化结果与人工修订差异没有沉淀，后续模型优化缺少高质量反馈数据。

### 1.5 本期需求价值

1. 跑通 `BD品类` 的自动刊登闭环，验证一期 `POC` 可行性。
2. 实现文本结构化、标题描述标准化、英文翻译和一站式换装的半自动化处理。
3. 通过双人审核机制保证上线质量，同时降低人工处理成本。
4. 为后续扩展到更多品类、更多来源路线以及全自动化推送提供业务和数据基础。

## 二、本期范围与阶段目标

### 2.1 本期路线选择

本期 `MVP` 仅聚焦：
- 试点品类：`BD`、**Atelier 、MOB**==**（未完全确定）**==
- 自动化路线：`精品路线`

即：
`板房提供基础素材（模特图 + 文本信息） → AI数据清洗 → AI换装 → 人工审核 → 一键推送盘古`
### 2.2 一期目标

1. 完成 `BD品类 + 精品路线` 的自动刊登闭环方案设计与 `POC` 验证。
2. 重点完成以下三类能力： 
    - 一站式换装能力，支撑模特图生成与输出


![image.png](https://file-paa.zoom.us/file/ht6MFtHhSJCaJm44R6qfsA?filename=image.png&jwt=eyJrIjoidnQvK3BVSSsiLCJhbGciOiJFUzI1NiJ9.eyJpYXQiOjE3ODQyNTQyMTAsIm9yaSI6Imx5bngtaW50ZXJhY3Rpb24iLCJpaWMiOiJhdzEiLCJleHAiOjE3ODQyNTUxMTAsImhkaWciOmZhbHNlLCJpc3MiOiJmaWxlIiwiYXVkIjoiemZzIiwiZGlnIjoiNjgzZDY1M2Q3OWU1NzdhMDNmMGI4ZDRlMDUzZGUzYjlkNTBhNWJkZGYyNDE5NzYxOGEzMjgyNGJjNzE2MGZjMSJ9.C1aiPTl3wbiSSBI9e72ms82jnH2pdhEomMVtiKCdsxVWj23l9ctdl64glWLIKYQUZNmXcmyPcb9D96SK0SrcMw&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9maWxlLXBhYS56b29tLnVzL2ZpbGUvaHQ2TUZ0SGhTSkNhSm00NFI2cWZzQT9maWxlbmFtZT1pbWFnZS5wbmcmand0PWV5SnJJam9pZG5RdkszQlZTU3NpTENKaGJHY2lPaUpGVXpJMU5pSjkuZXlKcFlYUWlPakUzT0RReU5UUXlNVEFzSW05eWFTSTZJbXg1Ym5ndGFXNTBaWEpoWTNScGIyNGlMQ0pwYVdNaU9pSmhkekVpTENKbGVIQWlPakUzT0RReU5UVXhNVEFzSW1oa2FXY2lPbVpoYkhObExDSnBjM01pT2lKbWFXeGxJaXdpWVhWa0lqb2llbVp6SWl3aVpHbG5Jam9pTmpnelpEWTFNMlEzT1dVMU56ZGhNRE5tTUdJNFpEUmxNRFV6WkdVellqbGtOVEJoTldKa1pHWXlOREU1TnpZeE9HRXpNamd5TkdKak56RTJNR1pqTVNKOS5DMWFpUFRsM3diaVNTQkk5ZTcybXM4MmpuSDJwZGhFb21NVnRpS0Nkc3hWV2oyM2w5Y3RkbDY0Z2xXTElLWVFVWk5tWGNteVBjYjlEOTZTSzBTcmNNdyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NDI1NTExMH19fV19&Signature=dLwAFiJwZobZ2Xk9bXW2rsMN~LdjUadTD97VL9AUYtLDcJwcOMOZwiGWv9x64JFiayJ2Y5wSpe0PuJ9-FZZNpFPXJLQFkwkbZ34wND1iBWy9YemcHmbnQuo7wuS9-K0L2P9sMGU9uUflleMQPqzP-Jh0v7HNe6MNRYX31sEc3ZEIg8cJZ2lHO3HeX~ic9dlNOvpaOCZhSIMqv-kBUSgb~pQTyUNRUDEHWhRbzfDJ2WXzuY7RKwXZWtmZ4L8tgSD~6F5E3kE51MeLMEnZD~R9mKsCVAc-4WtfdN9hov4FEyeGArBntbQ4eJAkhfMcMSiiiM-oqZbkUIjtVuBFSULqmQ__&Key-Pair-Id=KL18RPQB3R725)

    - 商品数据清洗与结构化输出
    - 半自动化审核流程，支持人工修改后再推送盘古
3. 本周完成方案产出与 `POC` 验证结论沉淀。

### 2.3 本期纳入范围

1. 中山产品研发提供标准素材包，作为系统输入来源。
2. 上海运营上传素材并发起 `AI` 生成。
3. 系统完成文本结构化清洗、标题/描述生成、多语言翻译。
4. 系统完成一站式换装，至少生成正面、背面、侧面图片，且总产出不少于 `6` 张。
5. 上海运营完成第一轮审核，可边改边审。
6. 美国团队完成第二轮审核，可边改边审。
7. 审核通过后，支持一键推送盘古。
8. 系统保留全流程留痕，包括 `AI` 输出结果、人工修改结果、审核记录、推送记录。

### 2.4 本期不纳入范围

1. `主流路线`：竞品图片 + 文本信息进入自动刊登流程。
2. 选项图自动复色。
3. 审核通过后自动直接推送盘古，不经过人工点击确认。
4. 数据看板与可视化分析。
5. 中山产品研发直接登录系统操作。
6. 面向多品类的复杂配置中心，本期仅保留最小可用配置能力。

## 三、角色职能及对应权限


|     角色     |               展示权限               |                                           操作权限                                           |
|--------------|--------------------------------------|----------------------------------------------------------------------------------------------|
| 上海运营     | 查看自己负责的刊登任务及审核记录     | 上传素材、发起AI生成、编辑中文字段与基础属性、编辑价格、替换图片、提交美国团队审核、推送盘古 |
| 美国团队     | 查看待其审核及已审核的刊登任务       | 编辑英文标题、英文描述及英文表达相关内容、完成英文审核                                       |
| 管理员       | 查看全部刊登任务、审核记录、异常记录 | 管理账号权限、处理异常任务、查看全量数据                                                     |
| 中山产品研发 | 本期不登录系统                       | 线下提供标准素材包                                                                           |

### 3.1 权限设计说明

1. 本期采用双人分步审核机制： 
    - 上海运营先审
    - 美国团队后审
2. 审核不是纯通过/驳回，而是允许审核人直接修改内容后提交。
3. 所有人工修改必须留痕，用于后续 `人工 vs AI` 数据分析。
4. 管理员仅对账号权限做配置；字段枚举项本期采用写死/初始化导入方式。

## 四、需求点

### 4.1 核心能力需求

1. 支持上海运营创建刊登任务并上传素材。
2. 支持系统对素材进行 `AI` 文本清洗与结构化抽取。
3. 支持系统自动生成标准化商品标题、商品描述及英文翻译内容。
4. 支持系统进行一站式换装，输出可用于刊登的模特图。
5. 支持上海运营审核并编辑中文文本、价格及图片结果。
6. 支持美国团队审核并编辑英文标题、英文描述及翻译表达。
7. 支持审核完成后一键推送盘古。
8. 支持记录 `AI` 结果、人工修订内容、审核过程及推送结果。

### 4.2 一期业务规则

1. `Goods ID` 和 `DDID` 在推送盘古前已存在，由人工录入或带入。
2. `Base Price`、`US Price` 由人工确认。
3. 其他主要文本字段由 `AI` 优先生成，人工审核修订。
4. 图片结果至少覆盖 `正面 / 背面 / 侧面` 三类图，最终通过审核的图不少于 `6` 张。
5. 推送盘古前必须完成上海运营审核和美国团队审核。
6. 驳回后任务回到上海运营处理，不允许直接跳回 `AI` 生成阶段。

## 五、字段设计

本期建议至少包含以下几类数据表：
1. 刊登任务表
2. 文本结果表
3. 图片结果表
4. 审核记录表
5. 用户表

以下按 `MVP` 最小可用方案展开。
### 5.1 刊登任务表


|       字段名       |    中文名    |    类型     | 必填 |                                 说明                                 |
|--------------------|--------------|-------------|------|----------------------------------------------------------------------|
| id                 | 主键         | varchar(50) | ✓    | 主键                                                                 |
| task_no            | 刊登任务编号 | varchar(50) | ✓    | 系统内唯一编号                                                       |
| category           | 品类         | varchar(20) | ✓    | 本期固定为 `BD`                                                      |
| route_type         | 路线类型     | varchar(20) | ✓    | 本期固定为 `精品路线`                                                |
| goods_id           | Goods ID     | varchar(50) | ✓    | 推送前已存在，由人工录入/带入                                        |
| ddid               | DDID         | varchar(50) | ✓    | 推送前已存在，由人工录入/带入                                        |
| ai_generate_status | AI生成状态   | varchar(20) | ✓    | 待AI生成 / AI生成中 / AI生成完成 / AI生成失败                        |
| audit_status       | 审核状态     | varchar(30) | ✓    | 待上海运营审核 / 待美国团队审核 / 待推送盘古 / 审核驳回 / 已推送盘古 |
| pangu_push_status  | 盘古推送状态 | varchar(20) | ✓    | 未推送 / 推送中 / 推送成功 / 推送失败                                |
| current_handler    | 当前处理人   | varchar(50) | ✗    | 当前待处理角色或人员                                                 |
| creator_name       | 创建人       | varchar(50) | ✓    | 上海运营                                                             |
| created_at         | 创建时间     | datetime    | ✓    | 记录创建时间                                                         |
| updated_at         | 更新时间     | datetime    | ✓    | 最近更新时间                                                         |

### 5.2 文本结果表


|              字段名               |     中文名      |     类型     |                                                                                                                                                                                                                                                                示例                                                                                                                                                                                                                                                                 |            说明             |
|-----------------------------------|-----------------|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------|
| id                                | 主键            | varchar(50)  |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 主键                        |
| task_id                           | 刊登任务ID      | varchar(50)  |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 关联刊登任务表              |
| online_color                      | Online Color    | varchar(100) |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |                             |
| **Style Name **<br/>**(US team)** | 风格            | varchar(255) | Harlow                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | 必填                        |
| **Description**<br/>**(US team)** | 描述            | text         | The Harlow bridesmaid dress is a two-piece stretch satin design featuring a floor-length sheath skirt and a strapless top with a straight neckline and detachable spaghetti straps. Soft pleating, a peplum-inspired waist, and a lace-up back with a self-tie bow define the structured bodice, while the clean skirt is finished with a back slit and complemented by a matching neck scarf.                                                                                                                                      | 必填                        |
| **Neckline**<br/>**(US team)**    | 领口            | varchar(100) | one-shoulder单肩领  Off-the-shoulder卡肩领  High Neck高领  Square Neckline方领  Cowl Neck垂褶领 V-neckV字领  Sweetheart心形领  Scoop大圆领  Straight平直领  Illusion透视领  Halter挂脖领  Boatneck一字领  Convertible可变换领型  Strapless抹胸                                                                                                                                                                                                                                                                                      | 样衣提取可多选，必选        |
| **Silhouette**<br/>**(US team)**  | 轮廓 / 裙型     | varchar(100) | A-LineA字裙Ball-Gown舞会袍Empire高腰裙Mermaid鱼尾裙Jumpsuit连体裤Sheath紧身裙                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 样衣提取<br/>单选，必选     |
| Sleeves<br/>(US team)             | 袖型            | varchar(100) | Long Sleeve长袖Short Sleeve短袖Off The Shoulder露肩Strapless无肩带Spaghettistraps细肩带Sleeveless无袖Sleeves有袖子Cap straps包肩Straps肩带                                                                                                                                                                                                                                                                                                                                                                                          | 样衣提取单选，必选          |
| Features<br/>(US team)            | 特征 / 设计特点 | varchar(100) | Pockets口袋Side slit侧开衩 Convertible可变换式Beaded钉珠Belt腰带Sash飘片Belt/Sash系带装饰Bow蝴蝶结Without Slit无开衩Corset束身设计Detachable Sleeves可拆卸袖子Detachable Straps可拆卸肩带                                                                                                                                                                                                                                                                                                                                           | 样衣提取可以不选，可多选    |
| Back Style<br/>(US team)          | 后背款式        | varchar(100) | Bow/Tie Back后背蝴蝶结 / 系带covered button包扣Crossed Straps后背交叉肩带Illusion后背透视Keyhole后背钥匙孔镂空laceup后背绑带ScoopU形露背Straight平直后背V backV形露背Zipper Up at Side侧面拉链                                                                                                                                                                                                                                                                                                                                      | 样衣提取可多选，必选        |
| Embellishment<br/>(US team)       | 装饰            | varchar(100) | Lace蕾丝Ruffle褶皱Pleated百褶Ruched抽褶Cascading Ruffles荷叶边Beaded缝珠Bow(s)蝴蝶结Sequins亮片Split Front开衩                                                                                                                                                                                                                                                                                                                                                                                                                      | 样衣提取可以不选，可多选    |
| Fabric                            | 面料            | varchar(100) | Chiffon雪纺Stretch Satin弹力缎面Metallic Satin金属光泽缎面Velvet天鹅绒Floral Burnout花卉烂花面料Mesh网纱Stretch Crepe弹力绉布Stretch Chiffon弹力雪纺Luxe Knit奢华针织面料Tulle薄纱网<br/>Bloom花卉面料Blossom花朵面料Dreamy Floral梦幻花卉面料Embroidered Sequin亮片刺绣面料Floral Burnout Jacquard花卉烂花提花面料Floral Jacquard花卉提花面料Matte Satin哑光缎面Jacquard提花面料Lace蕾丝Mesh Sequin亮片网纱Mikado厚缎Printed Chiffon印花雪纺Sequins亮片viscose粘胶纤维Watercolor Floral水彩花卉印花面料                            | 工艺备注提取可多选，必选    |
| Main fabric                       | 主面料          | varchar(100) | Tulle网纱Chiffon雪纺Stretch Satin水晶麻Metallic Satin金属光泽缎面velvet天鹅绒Floral Burnout花卉烂花面料Stretch Crepe弹力绉布Stretch Chiffon弹力雪纺Lace蕾丝Luxe Knit高级针织面料Mesh网眼布MatteSatin缎布Blossom花朵面料Bloom花卉面料Charmeuse柔光缎Crinkle Chiffon皱褶雪纺Dreamy Floral梦幻花卉面料Floral Jacquard花卉提花面料Jacquard提花面料Jersey针织平纹布Mesh Sequin亮片网纱Mikado厚缎Printed Chiffon印花雪纺Sequined亮片Shimmer Knit闪光针织面料Signature Sequin特色亮片面料Viscose粘胶纤维Watercolor Floral水彩花卉印花面料  | 工艺备注提取可多选，必选    |
| Length                            | 长度            | varchar(100) | Ankle-Length九分裙Tea-Length七分裙Knee-Length及膝Floor-Length及地长Asymmetrical不对称尾Midi Length中长裙Ballerina Length芭蕾裙长Short/Mini短装/迷你Cathedral Train(拖尾80cm)ChapelTrain(拖尾60cm)CourtTrain小拖(拖尾45cm)SweepTrain很小的拖(拖尾15cm、拖尾30cm)                                                                                                                                                                                                                                                                     | 样衣提取,<br/>可多选，必选  |
| Highest Point                     | 裙摆最高点      | varchar(100) | Ankle-Length九分裙Ballerina Length八分裙Floor-Length及地长Knee-Length及膝Knee-up膝上Midi Length中长裙Short/Mini短装/迷你Tea-Length七分裙                                                                                                                                                                                                                                                                                                                                                                                            | 样衣提取<br/>可多选，可不选 |
| Lowest Point                      | 裙摆最低点      | varchar(100) | Ankle-Length九分裙Ballerina Length八分裙Floor-Length及地长Knee-Length及膝Knee-up膝上MidiLength中长裙Short/Mini短装/迷你Tea-Length七分裙                                                                                                                                                                                                                                                                                                                                                                                             | 样衣提取可多选，可不选      |
| Boning                            | 鱼骨 / 支撑骨   | varchar(50)  | yesno                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 工艺备注提取单选，必选      |
| Padding                           | 胸垫            | varchar(50)  | yesno                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 工艺备注提取单选，必选      |
| Rush Production                   | 加急生产        | varchar(50)  | yesno                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 人工输入单选，必选          |
| Lining                            | 里衬            | varchar(50)  | fully lined全里衬stretch lining弹力里衬                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 工艺备注提取单选，必选      |
| Type of Closure                   | 闭合方式        | varchar(100) | Hidden back zipper后背隐形拉链Hidden side zipper侧边隐形拉链Hook and eye closure钩眼扣 / 风纪扣闭合Button closure纽扣闭合Covered back zipper遮盖式后背拉链Elastic waistband松紧腰Half button半纽扣式闭合Half corset半绑带式束身No Zipper无拉链Tie halter系带挂脖                                                                                                                                                                                                                                                                    | 工艺备注提取可多选，必选    |
| Hook and Eye                      | 钩眼扣          | varchar(50)  | metal hook and eye金属钩眼扣metal hook and thread eye金属钩 + 线环扣no hook and eye无钩眼扣                                                                                                                                                                                                                                                                                                                                                                                                                                         | 工艺备注提取单选，必选      |
| Online Size                       | 尺码            | text         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |                             |
| created_at                        | 创建时间        | datetime     |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 记录生成时间                |
| updated_at                        | 更新时间        | datetime     |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 最近更新时间                |

### 5.3 图片结果表


|    字段名    |   中文名   |     类型     | 必填 |             说明             |
|--------------|------------|--------------|------|------------------------------|
| id           | 主键       | varchar(50)  | ✓    | 主键                         |
| task_id      | 刊登任务ID | varchar(50)  | ✓    | 关联刊登任务表               |
| image_type   | 图片类型   | varchar(20)  | ✓    | 正面 / 背面 / 侧面 / 其他    |
| image_url    | 图片地址   | varchar(500) | ✓    | AI输出或人工替换后的最终图片 |
| image_source | 图片来源   | varchar(20)  | ✓    | AI生成 / 人工替换            |
| image_sort   | 图片排序   | int          | ✓    | 用于盘古推送顺序             |
| audit_result | 审核结果   | varchar(20)  | ✗    | 待审 / 通过 / 驳回           |
| remark       | 备注       | varchar(255) | ✗    | 图片问题说明                 |
| created_at   | 创建时间   | datetime     | ✓    |                              |
| updated_at   | 更新时间   | datetime     | ✓    |                              |

### 5.4 审核记录表


|     字段名     |   中文名   |    类型     | 必填 |             说明              |
|----------------|------------|-------------|------|-------------------------------|
| id             | 主键       | varchar(50) | ✓    | 主键                          |
| task_id        | 刊登任务ID | varchar(50) | ✓    | 关联刊登任务表                |
| audit_node     | 审核节点   | varchar(30) | ✓    | 上海运营审核 / 美国团队审核   |
| auditor_name   | 审核人     | varchar(50) | ✓    | 审核人员姓名                  |
| action_type    | 操作类型   | varchar(20) | ✓    | 提交审核 / 修改 / 通过 / 驳回 |
| change_summary | 变更摘要   | text        | ✗    | 记录本次人工修改内容          |
| audit_comment  | 审核意见   | text        | ✗    | 备注说明                      |
| created_at     | 创建时间   | datetime    | ✓    |                               |

### 5.5 用户表


|   字段名   |  中文名  |    类型     | 必填 |               说明                |
|------------|----------|-------------|------|-----------------------------------|
| user_name  | 用户名   | varchar(50) | ✓    | 主键                              |
| role       | 角色     | varchar(30) | ✓    | sh_operator / us_reviewer / admin |
| status     | 状态     | tinyint     | ✓    | 0:禁用 1:启用                     |
| created_at | 创建时间 | datetime    | ✓    |                                   |
| updated_at | 更新时间 | datetime    | ✓    |                                   |

### 5.6 字段生成口径

#### 人工确认/录入字段

- `Goods ID`
- `DDID`
- `Base Price`
- `US Price`

#### AI优先生成字段

- `Online Color`
- `Style Name`
- `Description`
- `Neckline`
- `Silhouette`
- `Sleeves`
- `Features`
- `Back Style`
- `Embellishment`
- `Fabric`
- `Length`
- `main fabric`
- `Highest Point`
- `Lowest Point`
- `Boning`
- `Padding`
- `Rush Production`
- `Lining`
- `Type of Closure`
- `Hook and Eye`
- `Online Size`

## 六、前端页面设计

本期建议建设以下页面：
1. 登录页
2. 刊登任务列表页
3. 新建任务/素材上传页
4. AI结果与审核页
5. 任务详情页
6. 用户管理页（仅管理员）

### 6.1 登录页

#### 页面布局

- 居中卡片式登录框
- 系统名称：`AI自动刊登系统`
- 用户名/密码输入框
- 登录按钮

#### 交互说明

- 登录成功后跳转刊登任务列表页
- 根据账号角色加载对应权限

### 6.2 刊登任务列表页

#### 页面布局

顶部导航栏：
```plaintext
[Logo AI自动刊登系统]  [刊登任务]  [用户管理(仅管理员可见)]  [用户名 ▼]

```
筛选区域：
```plaintext
品类: [BD▼]  状态: [全部▼]  创建人: [全部▼]
创建时间: [日期范围选择器]  Goods ID / DDID: [输入框]
[搜索] [重置]

```
操作区域：
```plaintext
[+ 新建刊登任务(仅上海运营可见)]                     共 XX 条记录

```
列表字段建议：

|   任务编号   | Goods ID |  DDID  | 品类 | AI生成状态 |    审核状态    | 当前处理人 | 创建人 |  创建时间  |     操作      |
|--------------|----------|--------|------|------------|----------------|------------|--------|------------|---------------|
| T20260715001 | G12345   | D56789 | BD   | AI生成完成 | 待美国团队审核 | Lucy       | Amy    | 2026-07-15 | [查看] [编辑] |

#### 权限控制

- 上海运营： 
    - 可新建任务
    - 可查看自己创建或负责的任务
    - 在对应状态下可编辑与提交审核
- 美国团队： 
    - 查看待其审核和已处理任务
    - 不可新建任务
- 管理员： 
    - 查看全部任务
    - 处理异常和权限问题

### 6.3 新建任务/素材上传页

#### 页面布局

面包屑：
```plaintext
刊登任务 > 新建任务

```
表单分组建议：
```plaintext
基础信息
- 品类：BD（默认）
- 路线类型：精品路线（默认）
- Goods ID
- DDID
- Base Price
- US Price

素材上传
- 全套纸样
- 激光纸样
- 尺码表
- 图片素材
- 工艺备注

操作按钮
- [取消] [保存并发起AI生成]

```
#### 交互说明

1. 上海运营上传中山产品研发提供的标准素材包。
2. 素材上传完成后，可点击 `保存并发起AI生成`。
3. 任务创建成功后进入 `待AI生成` 或 `AI生成中` 状态。

### 6.4 AI结果与审核页

#### 页面布局

页面建议采用左右结构：
- 左侧：素材预览与生成图片预览
- 右侧：结构化文本字段表单

页面顶部显示关键信息：
```plaintext
任务编号 / Goods ID / DDID / 当前状态 / 当前处理人

```
文本区域分组建议：
1. 价格与基础信息
2. 中文信息
3. 英文信息
4. 商品属性
5. AI提取依据摘要

图片区域建议：
- 至少展示正面、背面、侧面三类图
- 支持查看最终通过图片总数
- 支持图片替换、删除、排序

#### 审核交互

上海运营审核阶段：
- 可编辑： 
    - `Base Price`
    - `US Price`
    - 中文标题与描述
    - 中文属性字段
    - 图片结果
- 操作按钮： 
    - `[保存修改]`
    - `[驳回]`
    - `[提交美国团队审核]`

美国团队审核阶段：
- 可编辑： 
    - 英文 `Style Name`
    - 英文 `Description`
    - 英文表达相关内容
- 操作按钮： 
    - `[保存修改]`
    - `[驳回]`
    - `[审核通过，待推送盘古]`

待推送盘古阶段：
- 上海运营可见按钮： 
    - `[一键推送盘古]`

### 6.5 任务详情页

#### 页面布局

面包屑：
```plaintext
刊登任务 > 任务详情 T20260715001

```
展示内容包括：
1. 基础信息
2. 文本结果
3. 图片结果
4. 审核记录
5. 推送记录

#### 交互说明

- 默认只读
- 根据权限和状态决定是否出现编辑、继续处理等按钮

### 6.6 用户管理页

仅管理员可见，支持：
1. 新增账号
2. 编辑账号角色
3. 启用/禁用账号

本期只管理账号与角色，不做复杂组织架构和字段枚举配置。
## 七、通用交互规范

### 7.1 响应式设计

- 最小支持宽度：`1280px`
- 建议使用宽度：`1440px` 及以上

### 7.2 加载状态

- 列表加载：显示骨架屏
- 素材上传：显示上传进度
- `AI` 生成中：显示处理中状态和轮询刷新
- 表单提交：按钮显示 `loading` 且禁用重复点击

### 7.3 提示反馈

- 成功操作：`Toast` 提示（绿色，3秒自动消失）
- 失败操作：`Toast` 提示（红色，3秒自动消失）
- 审核驳回：显示明确原因提示
- 盘古推送失败：显示失败原因并支持重试

### 7.4 空状态

- 无任务数据时展示空状态页
- 对有权限用户提供 `新建刊登任务` 按钮

### 7.5 错误处理

- 网络异常：展示错误提示和重试按钮
- 权限不足：展示 `403` 页面
- 页面不存在：展示 `404` 页面
- `AI` 生成失败：允许管理员或上海运营重新发起生成

## 八、关键流程图

### 8.1 新建任务并发起AI流程

```plaintext
上海运营进入列表页 → 点击「新建刊登任务」→ 录入基础信息 → 上传素材包
→ 点击「保存并发起AI生成」→ 系统校验通过 → 创建任务
→ 进入「待AI生成 / AI生成中」→ AI生成完成 → 进入「待上海运营审核」

```

![whiteboard_exported_image.png](https://file-paa.zoom.us/file/nKCKq3x6QtWuvqZc4MQlNA?filename=whiteboard_exported_image.png&jwt=eyJrIjoidnQvK3BVSSsiLCJhbGciOiJFUzI1NiJ9.eyJleHAiOjE3ODQyNTUxMTAsImlhdCI6MTc4NDI1NDIxMCwiaWljIjoiYXcxIiwiYXVkIjoiemZzIiwiaGRpZyI6ZmFsc2UsIm9yaSI6Imx5bngtaW50ZXJhY3Rpb24iLCJpc3MiOiJmaWxlIiwiZGlnIjoiMGI3OWQ5NWY2NjMzYWY0OTI5MzM1NWU4OGM3MzdlM2E0MDI0YzMxZWMyYTEwZjBjNTYxMGFjY2VmMzJhNzI0ZCJ9.YYMa0Er5nJ0KtZ_pU_TDaqmDGRo48ag3KkXZ6X2WdWOLFNTK9ATeCvqZVdFV4E9WacLzUviX38lZTMaP3XCz6g&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9maWxlLXBhYS56b29tLnVzL2ZpbGUvbktDS3EzeDZRdFd1dnFaYzRNUWxOQT9maWxlbmFtZT13aGl0ZWJvYXJkX2V4cG9ydGVkX2ltYWdlLnBuZyZqd3Q9ZXlKcklqb2lkblF2SzNCVlNTc2lMQ0poYkdjaU9pSkZVekkxTmlKOS5leUpsZUhBaU9qRTNPRFF5TlRVeE1UQXNJbWxoZENJNk1UYzROREkxTkRJeE1Dd2lhV2xqSWpvaVlYY3hJaXdpWVhWa0lqb2llbVp6SWl3aWFHUnBaeUk2Wm1Gc2MyVXNJbTl5YVNJNklteDVibmd0YVc1MFpYSmhZM1JwYjI0aUxDSnBjM01pT2lKbWFXeGxJaXdpWkdsbklqb2lNR0kzT1dRNU5XWTJOak16WVdZME9USTVNek0xTldVNE9HTTNNemRsTTJFME1ESTBZek14WldNeVlURXdaakJqTlRZeE1HRmpZMlZtTXpKaE56STBaQ0o5LllZTWEwRXI1bkowS3RaX3BVX1REYXFtREdSbzQ4YWczS2tYWjZYMldkV09MRk5USzlBVGVDdnFaVmRGVjRFOVdhY0x6VXZpWDM4bFpUTWFQM1hDejZnIiwiQ29uZGl0aW9uIjp7IkRhdGVMZXNzVGhhbiI6eyJBV1M6RXBvY2hUaW1lIjoxNzg0MjU1MTEwfX19XX0_&Signature=jZAa1e3f4bMJkIE0uc1kRMi7ynlnFvq9H8TFij5fAwv9HDPZo-lUSu75J3NhgCQR5jg94et1oPM5VzKj8iOoP9h22F2vBqKQGsKZaIQ4i-j2PFBKP6dz8KDmNrR8bpcCdHHPUI~7vfwXAV-mF8uJ7pnzN2UK2DtrpiIPX4uy8lJBymaq8z-NQj~yI6fvEY6jXqzYjsvubAlusqI9Yt1vkcCcc651GTvd2N9NR0VD2luFHxcCwK77pbhHmFzDy0eV~FGJylGPZ4R7PpuV-ovUGztYuvv6j0~u8FmDSK6xBQTFyKWpE28ziStOsJJeDxsEzT9bu26Qt1HA9OBeng48Aw__&Key-Pair-Id=KL18RPQB3R725)

### 8.2 审核流程

```plaintext
AI生成完成 → 上海运营审核并修改 → 提交美国团队审核
→ 美国团队审核并修改 → 审核通过 → 进入「待推送盘古」
→ 上海运营点击「一键推送盘古」→ 推送成功 → 进入「已推送盘古」

```

![whiteboard_exported_image (1).png](https://file-paa.zoom.us/file/X75yAqCPRyevtNZascCGMw?filename=whiteboard_exported_image%20%281%29.png&jwt=eyJhbGciOiJFUzI1NiIsImsiOiJ2dC8rcFVJKyJ9.eyJvcmkiOiJseW54LWludGVyYWN0aW9uIiwiaXNzIjoiZmlsZSIsImF1ZCI6InpmcyIsImhkaWciOmZhbHNlLCJpYXQiOjE3ODQyNTQyMTEsImV4cCI6MTc4NDI1NTExMSwiaWljIjoiYXcxIiwiZGlnIjoiZGUwMDE1ZDcyZmQ1Zjc0OGI4OTc1ODZmYzc0NWEyOGRiZDU1ZGVhZjA5OGQ5MjA3MjM3NDFmYzQwMDk5YzA2NyJ9.YzxsO3ahFDizg8hROINv9G4p9hRuE80mESzDFxRlIQeHDhq7R0Rx3LbljT7fVCQ6dVDQpFHLv28IwU7D_RDifw&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9maWxlLXBhYS56b29tLnVzL2ZpbGUvWDc1eUFxQ1BSeWV2dE5aYXNjQ0dNdz9maWxlbmFtZT13aGl0ZWJvYXJkX2V4cG9ydGVkX2ltYWdlJTIwJTI4MSUyOS5wbmcmand0PWV5SmhiR2NpT2lKRlV6STFOaUlzSW1zaU9pSjJkQzhyY0ZWSkt5SjkuZXlKdmNta2lPaUpzZVc1NExXbHVkR1Z5WVdOMGFXOXVJaXdpYVhOeklqb2labWxzWlNJc0ltRjFaQ0k2SW5wbWN5SXNJbWhrYVdjaU9tWmhiSE5sTENKcFlYUWlPakUzT0RReU5UUXlNVEVzSW1WNGNDSTZNVGM0TkRJMU5URXhNU3dpYVdsaklqb2lZWGN4SWl3aVpHbG5Jam9pWkdVd01ERTFaRGN5Wm1RMVpqYzBPR0k0T1RjMU9EWm1ZemMwTldFeU9HUmlaRFUxWkdWaFpqQTVPR1E1TWpBM01qTTNOREZtWXpRd01EazVZekEyTnlKOS5ZenhzTzNhaEZEaXpnOGhST0lOdjlHNHA5aFJ1RTgwbUVTekRGeFJsSVFlSERocTdSMFJ4M0xibGpUN2ZWQ1E2ZFZEUXBGSEx2MjhJd1U3RF9SRGlmdyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NDI1NTExMX19fV19&Signature=gJcCu7TtU6W6mKFwG~A2WpZ9y68dSznLqLqiXYlB8o6BmSgwxwjkd~nWANgI~6oHzk~kNVpLFV4RTpS-TFDW4v-T6abSSJpkUThxlhrA1OjxiJjBYSnpzmEl0RKTQ47UFowQPTyc-yEJXz2GYFCo3kTHUchJVdB-KXlU9UiQ0c8DLwyIXEScJe8J66ax0Ru3foRBEddzQEFwlUtumwBvT1T3gASR2lSLXmQ3dT6UrfTv-RcmJNPhon24Vz6zEONKcMsUgNpZQcIzLPc9~75A9J8rqG3paQFJ0rCaW66gX7qM0YwC2qp~Gxy7WEv2hZtNQYU4NqFo1bRsdbjfSAkFQw__&Key-Pair-Id=KL18RPQB3R725)

### 8.3 驳回流程

```plaintext
上海运营或美国团队审核时点击「驳回」
→ 任务进入「审核驳回」
→ 回到「待上海运营处理」
→ 上海运营修改后重新提交美国团队审核

```

![whiteboard_exported_image (2).png](https://file-paa.zoom.us/file/VVN-9jn9TB-rUgYr0HZ6Ag?filename=whiteboard_exported_image%20%282%29.png&jwt=eyJrIjoidnQvK3BVSSsiLCJhbGciOiJFUzI1NiJ9.eyJpYXQiOjE3ODQyNTQyMTEsIm9yaSI6Imx5bngtaW50ZXJhY3Rpb24iLCJpaWMiOiJhdzEiLCJleHAiOjE3ODQyNTUxMTEsImhkaWciOmZhbHNlLCJpc3MiOiJmaWxlIiwiYXVkIjoiemZzIiwiZGlnIjoiYjM2ZjlmYzQxMGZkOGRhNzYzZWFjNDdhOTY5MjdkYTAxNzNlYjIyZmNiN2MzYmE0MjFjZTE2NDk0Y2VmOWNiMCJ9.DGyJpZ0ESMf9vtlCf7if1OAgNsRECzA4mJ1Z-LZTyQSKOQbRTvAEB7qosEyqc5EAo9RhqJGai6zsQfSXYgKJOg&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9maWxlLXBhYS56b29tLnVzL2ZpbGUvVlZOLTlqbjlUQi1yVWdZcjBIWjZBZz9maWxlbmFtZT13aGl0ZWJvYXJkX2V4cG9ydGVkX2ltYWdlJTIwJTI4MiUyOS5wbmcmand0PWV5SnJJam9pZG5RdkszQlZTU3NpTENKaGJHY2lPaUpGVXpJMU5pSjkuZXlKcFlYUWlPakUzT0RReU5UUXlNVEVzSW05eWFTSTZJbXg1Ym5ndGFXNTBaWEpoWTNScGIyNGlMQ0pwYVdNaU9pSmhkekVpTENKbGVIQWlPakUzT0RReU5UVXhNVEVzSW1oa2FXY2lPbVpoYkhObExDSnBjM01pT2lKbWFXeGxJaXdpWVhWa0lqb2llbVp6SWl3aVpHbG5Jam9pWWpNMlpqbG1ZelF4TUdaa09HUmhOell6WldGak5EZGhPVFk1TWpka1lUQXhOek5sWWpJeVptTmlOMk16WW1FME1qRmpaVEUyTkRrMFkyVm1PV05pTUNKOS5ER3lKcFowRVNNZjl2dGxDZjdpZjFPQWdOc1JFQ3pBNG1KMVotTFpUeVFTS09RYlJUdkFFQjdxb3NFeXFjNUVBbzlSaHFKR2FpNnpzUWZTWFlnS0pPZyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NDI1NTExMX19fV19&Signature=WZj-s8friwsbM4eyht~ieSx-sExU6LgE4NvVAdTeRciY2CpDqRQ5efwUHjPExAkaF5FYNmxkw7BrnMkTrmMWIjWXu9pBvg2seWeoX0w8DXRQRIPQ35ReyTvti18xLS6OzZT7zyWBp1vts0MXnsHrjbmGAM16s3lryJPE1SCCKduAVTxsKjU6H6LG21ycNaJw6doZz0dPrvxUZjZdZwcZJnVoN3G5pOX5-rmvpdbS-AOywUKtyGFA9H9PRy-D0rL4tei03tR-n8ff4EHh2b06cjzTrto6Vihn8r5gEmqvII9hr7cfNjABpg1EUbEzkDtZK85exNbwcP3qfgnop~yB4Q__&Key-Pair-Id=KL18RPQB3R725)

### 8.4 权限校验流程

```plaintext
用户登录 → 获取角色 → 进入任务列表
→ 根据角色展示对应任务数据和按钮
→ 处理任务时后端二次校验权限
→ 不符合权限时返回错误提示

```

![whiteboard_exported_image (4).png](https://file-paa.zoom.us/file/28JBAJYeSbesLcq92ukuNg?filename=whiteboard_exported_image%20%284%29.png&jwt=eyJrIjoidnQvK3BVSSsiLCJhbGciOiJFUzI1NiJ9.eyJhdWQiOiJ6ZnMiLCJpaWMiOiJhdzEiLCJpYXQiOjE3ODQyNTQyMTEsImRpZyI6IjliNGRiMzRkNzcyYjYxOTE5NzkxOTM3OTg3MTAyZmJiYTY4ZjgxNTNjY2U1Mzc0MWU3NjQxOWNjZjQxMTUzY2EiLCJoZGlnIjpmYWxzZSwib3JpIjoibHlueC1pbnRlcmFjdGlvbiIsImV4cCI6MTc4NDI1NTExMSwiaXNzIjoiZmlsZSJ9.TqXjsJsTf79gOH6c8tIvIIDEAPXFfsxg6Wq2ShmJf11nthOYom7k_5647tNT_DaztrGInjXzLnZQT0qslAIZmA&Policy=eyJTdGF0ZW1lbnQiOlt7IkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NDI1NTExMX19LCJSZXNvdXJjZSI6Imh0dHBzOi8vZmlsZS1wYWEuem9vbS51cy9maWxlLzI4SkJBSlllU2Jlc0xjcTkydWt1Tmc~ZmlsZW5hbWU9d2hpdGVib2FyZF9leHBvcnRlZF9pbWFnZSUyMCUyODQlMjkucG5nJmp3dD1leUpySWpvaWRuUXZLM0JWU1NzaUxDSmhiR2NpT2lKRlV6STFOaUo5LmV5SmhkV1FpT2lKNlpuTWlMQ0pwYVdNaU9pSmhkekVpTENKcFlYUWlPakUzT0RReU5UUXlNVEVzSW1ScFp5STZJamxpTkdSaU16UmtOemN5WWpZeE9URTVOemt4T1RNM09UZzNNVEF5Wm1KaVlUWTRaamd4TlROalkyVTFNemMwTVdVM05qUXhPV05qWmpReE1UVXpZMkVpTENKb1pHbG5JanBtWVd4elpTd2liM0pwSWpvaWJIbHVlQzFwYm5SbGNtRmpkR2x2YmlJc0ltVjRjQ0k2TVRjNE5ESTFOVEV4TVN3aWFYTnpJam9pWm1sc1pTSjkuVHFYanNKc1RmNzlnT0g2Yzh0SXZJSURFQVBYRmZzeGc2V3EyU2htSmYxMW50aE9Zb203a181NjQ3dE5UX0RhenRyR0lualh6TG5aUVQwcXNsQUlabUEifV19&Signature=nUhoS59h9LLQtMb-BLi6QMSy0-4eshEMtXigen1TVphy2VzrhaOVrDbKkwa8IF8WMIf0LlP1y-wmZMS~rXoHg2mH5IQ1rk~MQoPZG9X3N06STKoVVzulfFMMwmQgC33zlu7nJndMoxFPPESAmGYSmuHNPNkXJJqIPyPOrq1Zk--Z~aky2ujF4C8H2yccQOatp2VaUemQp8yhuS6T61r1UXds6Xa7Fgjj67obkbD2HotCGX8MC~OfXzdlwf1IFDARJGMPNAB0is-JhaI5MNAqsG6aWmHONdnIhu4znHYmL~5TVrV7L6pjGA7o9HLOKnYdPJyPsazjMbT8e5dLkJY~mA__&Key-Pair-Id=KL18RPQB3R725)

## 九、数据回收设计

本期不做数据看板，但需为后续分析保留数据基础。
### 9.1 本期需留痕的数据

1. `AI` 首次生成的文本结果
2. 人工最终确认后的文本结果
3. `AI` 首次生成的图片结果
4. 人工替换、删除、调整后的最终图片结果
5. 各阶段处理时间： 
    - 任务创建时间
    - `AI` 生成完成时间
    - 上海运营审核完成时间
    - 美国团队审核完成时间
    - 盘古推送完成时间
6. 审核驳回原因
7. 推送成功/失败结果

### 9.2 后续可支持的数据分析方向

1. 图片维度：人工方案 vs `AI` 方案
2. 文本维度：人工填写 vs `AI` 生成
3. 效率维度：原始上新时间 vs 自动化上新时间
4. 人力维度：原始上新所涉人力 vs 自动化上新所需人力

## 十、一期方案总结

本期 `AI自动刊登MVP` 以 `BD品类 + 精品路线`==（未完全确定 ）== 为唯一试点范围，目标不是一次性实现完全自动化，而是优先跑通从素材上传、`AI` 生成、双人审核到一键推送盘古的业务闭环。
一期重点聚焦三件事：
1. 一站式换装能力，形成可上架的模特图结果
2. 商品文本数据清洗与结构化输出，支持标准化标题、描述和英文翻译
3. 半自动化审核机制，在可控风险下提升整体上新效率

该方案既能满足本周 `POC` 验证需要，也能为后续扩展主流路线、选项图复色、自动推送盘古和数据看板提供基础。
