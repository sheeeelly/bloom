## 变更记录


| 版本 |    日期    | 变更内容 | 作者  |
|------|------------|----------|-------|
| v1.0 | 2026-06-11 | 初稿     | Kerry |

## 1. 背景与目标

### 1.1 背景

- 用户反馈分散在 **Zendesk 工单、官网商品评论、外网评价、社媒/Reddit、NPS** 等多个系统，各团队各看各的。
- 现有 AZ Report 平台只服务**研发**。
- 业务团队的共性痛点：**数据格式不统一、量级高需人工、无趋势、无法导出、处理后无改善追踪**。

### 1.2 各业务团队现状


|    团队    |                    现有反馈渠道                     |                舆情负责人                 |                                             核心诉求                                             |          及时预警          |
|------------|-----------------------------------------------------|-------------------------------------------|--------------------------------------------------------------------------------------------------|----------------------------|
| **客服**   | ticket、官网商品评论(jalen)、外网差评、NPS(jingwei) | Lindy 团队：官网每天/外网每周/ticket 随时 | 统一格式（一二级原因）、趋势、关键词/coupon 变化、最差/最好员工、外网评论定位用户/订单、打标追踪 | 支付类、物流丢包           |
| **国家站** | Trustpilot、Reddit、TikTok、IG、内网、UK TTS        | 暂无固定人                                | Reddit 定期获取、槽点排名+归因、分国家问题、给用户打标（频繁下单差评）                           | 网站售前问题（如下单）     |
| **营销**   | Facebook（指定账号）                                | 无人处理，需支持                          | 哪个广告帖差评多→排名+归因、差评多的产品广告避雷                                                 | 差评、敏感词（骗子等）     |
| **商品**   | 前台商品差评                                        | 有人看                                    | 品类/单品销量榜、热销品、差评归因、改版前后差评区分                                              | 看销量                     |
| **物流**   | 客服工单（语义划分）                                | Lan Long 负责                             | 物流投诉分类（直发/退货）、二级物流商分类、退货按国家、直发/退货占比                             | 有报表预警                 |
| **供应链** | 客服工单（质量/时效）、评论区                       | Kerwin(PMO)                               | 定性定责、质量&时效归因看板、对应部门投诉指标                                                    | 偏优化，基本不需要及时预警 |

### 1.3 产品目标


|    目标     |                          说明                           | 优先级 |
|-------------|---------------------------------------------------------|--------|
| 统一归集    | 工单/内网评论/外网评论统一入库，统一一二级原因口径      | P0     |
| 问题总览    | 管理层全局看板：好差评、趋势、平台/国家分布、Top 槽点   | P0     |
| AI 归因解析 | 语言识别、翻译、一二级原因归类、客诉点提炼、AI 简洁总结 | P0     |
| AI智能问答  | 用户直接通过聊天框获取信息                              | P0     |

## 2. 统一数据模型`opinion_records`（工单+评论统一）

```sql
CREATE TABLE opinion_records (
  id              BIGINT      NOT NULL AUTO_INCREMENT,
  domain          VARCHAR(32) NOT NULL  COMMENT 'Zendesk/官网/Trustpilot/Facebook/Reddit/...',
  url             TEXT        NULL      COMMENT '原文/工单链接',
  country         VARCHAR(8)  NOT NULL,
  reviewer_name   VARCHAR(255) NULL     COMMENT '作者/用户/工单提交人',
  user_id         VARCHAR(64) NULL      COMMENT '可关联的用户ID（外网评论尽力定位）',
  order_id        VARCHAR(64) NULL      COMMENT '可关联的订单ID',
  review_time     DATETIME    NOT NULL  COMMENT '评论/工单时间（美东）',
  content         TEXT        NOT NULL  COMMENT '原文',
  content_zh      TEXT        NULL      COMMENT 'AI 翻译（中文）',
  rating          TINYINT     NOT NULL      COMMENT '1-5',
  language        VARCHAR(16) NULL      COMMENT 'AI 语言识别',
  csl1_category     VARCHAR(32) NULL      COMMENT '客户满意度一级原因',
  csl2_category     VARCHAR(32) NULL      COMMENT '客户满意度二级原因',
  rdl1_category     VARCHAR(32) NULL      COMMENT '研发一级原因',
  rdl2_category     VARCHAR(32) NULL      COMMENT '研发二级原因',
  pdl1_category     VARCHAR(32) NULL      COMMENT '商品一级原因',
  pdl2_category     VARCHAR(32) NULL      COMMENT '商品二级原因',
  issue_summary   VARCHAR(512) NULL     COMMENT 'AI 客诉点',
  business_tags   JSON        NULL      COMMENT '命中的业务方：["物流","供应链"]',
  raw_rating_text VARCHAR(255) NULL,
  ticket_id       BIGINT      NULL,
  comment_id      BIGINT      NULL,
  extra_json      JSON        NULL      COMMENT 'subreddit/广告帖id/品类/物流商/sku 等',
  task_time       DATETIME    NOT NULL,
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='舆情统一记录表（工单+评论）';
```
客满一二级问题：

|            一级原因            |                                      二级原因                                      |
|--------------------------------|------------------------------------------------------------------------------------|
| Style 款式问题                 | p0领口太低、开衩太高、版型不好、其他款式问题                                       |
| Size 尺码问题                  | p0尺码偏小、尺码偏大、码数不合适                                                   |
| Quality 质量问题               | p0质量不满意、衣物破损、拉链问题、肩带问题、缝纫做工问题                           |
| Not-as-pictured 图货不一致问题 | p0颜色与图片不一致、款式与图片不一致、其他图货不一致                               |
| Material 面料问题              | p0面料不舒服、面料薄透、面料与色卡不一致、面料与样衣不一致                         |
| Customer 客户问题              | p0改变主意、婚礼取消/延期、活动取消、不再需要、不喜欢外观/触感、选错款式、选错颜色 |
| Wrong-item-received 发错货问题 | p0发错商品、发错颜色、发错尺码                                                     |
| Logistics 物流/履约问题        | p0送达超 DW、物流久未送达、物流延迟                                                |
| Others 其他                    | p1其他问题                                                                         |

## 3. 用户与消费方矩阵


|  角色  |         看什么数据          |                               主要页面                               |                   关键动作                   |
|--------|-----------------------------|----------------------------------------------------------------------|----------------------------------------------|
| 管理层 | 全域                        | 问题总览                                                             | 看趋势、看 Top 槽点                          |
| 研发   | 工单舆情                    | 研发工作台（工单搜索/集中问题/Ticket Intent/分类看板/月度报告/导出） | 查集中问题、查单 ticket、看技术类 L1/L2 趋势 |
| 客服   | 工单+内外网评论+NPS         | 客服工作台                                                           | 统一明细、员工榜、用户/订单定位、打标        |
| 国家站 | 内外网评论（分国家）        | 国家站工作台                                                         | 槽点榜+归因、用户打标                        |
| 营销   | Facebook、INS等社媒广告评论 | 营销工作台                                                           | 广告帖差评榜、产品避雷、敏感词预警           |
| 商品   | 前台商品评论                | 商品工作台                                                           | 品类/单品差评榜、改版前后对比                |
| 物流   | 物流相关工单，来自客服      | 物流工作台                                                           | 直发/退货分类、物流商/国家维度               |
| 供应链 | 质量/时效工单/评论          | 供应链工作台                                                         | 质量&时效归因、定性定责                      |

## 4. 数据源与接入


|  数据域  |                       接口                        |               说明                |     实时性     |
|----------|---------------------------------------------------|-----------------------------------|----------------|
| 工单     | 现有（Zendesk）                                   | 复用现有 AZ Report 链路           | 非实时（导出） |
| 内网评论 | `https://cms.azazie.com/index.php`                | 官网商品评论                      | 接口拉取       |
| 外网评论 | `https://spider.gaoyaya.com/api/external_reviews` | Trustpilot/社媒/Reddit 等外网评论 | 接口拉取       |
| NPS      | 网站开发明确接口                                  | 客服 NPS                          | 待确认         |

## 5. 平台整体架构

```plaintext
舆情监控平台
├── 📊 问题总览                ← 全局，管理层
├── 🗂️ 舆情数据
│   │     明细搜索 / 整体分析 / 分类看板 / 趋势 / 归因 / 导出
├── 🗂️ AI智能助手
└── ⚙️ 配置/分类字典            ← 数据字典
```
## 6. 功能模块设计

### 6.1 问题总览（P0 · 管理层）

**目标：** 30 秒看清全公司舆情全貌。
- **KPI 卡片：** 总反馈量、差评量、差评率、平均评分、环比（工单+评论合并口径，可切「仅评论/仅工单」）
- **趋势图：** 好差评月度/周度趋势
- **分布图：** 平台分布环形、国家分布条形
- **Top 槽点榜：** 按 L1/L2 原因聚合的差评 Top 10（点击下钻明细）

### 6.2 AI 解析层（P0）

对每条评论/工单，AI 产出：

|      能力      |           说明            |
|----------------|---------------------------|
| 语言识别       | 识别原文语种              |
| 翻译           | 非中/英文翻译为中文       |
| rating 归一    | 无星级来源AI 打 1–5 分    |
| L1/L2 原因归类 | 归入一级问题，N个二级问题 |
| 客诉点提炼     | 一句话槽点                |
| AI 简洁总结    | 聚合同类问题的执行摘要    |

### 6.3AI智能助手

用户用自然语言提问，系统自动查 `opinion_records`、按客满/研发/商品三套归因聚合，返回文字结论 + 图表 + 溯源链接，降低各业务方自助分析门槛。
### 6.4 导出（P0）

- 所有工作台支持按当前筛选导出 Excel
- 物流：各物流商发货工单数、海外仓各国退货工单次数
- 供应链：质量问题客诉明细

## 7. 前端页面


![舆情监控平台.html](https://file-paa.zoom.us/file/4lomdheLRqW2wM6n-SV0aw?filename=%E8%88%86%E6%83%85%E7%9B%91%E6%8E%A7%E5%B9%B3%E5%8F%B0.html&jwt=eyJhbGciOiJFUzI1NiIsImsiOiJ2dC8rcFVJKyJ9.eyJoZGlnIjpmYWxzZSwiZGlnIjoiZWU3MWE4Mjg2MGMwMzViYmVmNzEzODQwNjg1MmJhMDhhOWY3MzM2MzlhYzcxYWQyMGEyOTY4NWVlNGU3MWYyZSIsImlzcyI6ImZpbGUiLCJhdWQiOiJ6ZnMiLCJvcmkiOiJseW54LWludGVyYWN0aW9uIiwiaWF0IjoxNzgzOTk5MjczLCJleHAiOjE3ODQwMDAxNzMsImlpYyI6ImF3MSJ9.C37IZlCGe4iCmAhfCPuHen5rxAR_I4pV3DCfEjpqeadmz024WCDBj-UE_XEHAfhmTGt37OKf235As75lFDeCdw&Policy=eyJTdGF0ZW1lbnQiOlt7IkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NDAwMDE3M319LCJSZXNvdXJjZSI6Imh0dHBzOi8vZmlsZS1wYWEuem9vbS51cy9maWxlLzRsb21kaGVMUnFXMndNNm4tU1YwYXc~ZmlsZW5hbWU9JUU4JTg4JTg2JUU2JTgzJTg1JUU3JTlCJTkxJUU2JThFJUE3JUU1JUI5JUIzJUU1JThGJUIwLmh0bWwmand0PWV5SmhiR2NpT2lKRlV6STFOaUlzSW1zaU9pSjJkQzhyY0ZWSkt5SjkuZXlKb1pHbG5JanBtWVd4elpTd2laR2xuSWpvaVpXVTNNV0U0TWpnMk1HTXdNelZpWW1WbU56RXpPRFF3TmpnMU1tSmhNRGhoT1dZM016TTJNemxoWXpjeFlXUXlNR0V5T1RZNE5XVmxOR1UzTVdZeVpTSXNJbWx6Y3lJNkltWnBiR1VpTENKaGRXUWlPaUo2Wm5NaUxDSnZjbWtpT2lKc2VXNTRMV2x1ZEdWeVlXTjBhVzl1SWl3aWFXRjBJam94Tnpnek9UazVNamN6TENKbGVIQWlPakUzT0RRd01EQXhOek1zSW1scFl5STZJbUYzTVNKOS5DMzdJWmxDR2U0aUNtQWhmQ1B1SGVuNXJ4QVJfSTRwVjNEQ2ZFanBxZWFkbXowMjRXQ0RCai1VRV9YRUhBZmhtVEd0MzdPS2YyMzVBczc1bEZEZUNkdyJ9XX0_&Signature=iPfSOuAWwJpmqYqMxvLTi-wwfJKNGJ3VDGY-ZjFwuitarvzsROW8nRsFolggQcqAlM-PhUA3kFAUJm1n95i59A7RdlSRIVxSjUwcR~TQ0BFrhw2pL~sMyggYFL-D47UiSpKkGgFkEJ1z6QUStVta5OfA6-RKfNEYe9eBn3wO1qSzQcTOrv45e7L-C2-SZU3DuzTwv9AFGgtLd6ChXTYS2Z3ZTn6qJUM3sk6H~L1AvCi2k8cyIuvtC~1R7NVjoxpej8s5YeH0AnbIXaNNLu2C8-DcWnMaeupEasqsthjpDXVqkloVgz7kZGQ6LsITx03yhyUcwKzk5aeIPfkN1FfY1A__&Key-Pair-Id=KL18RPQB3R725)

### 问题总览


![image.png](https://file-paa.zoom.us/file/YDysrOEjRfG72ytD-Yo1sA?filename=image.png&jwt=eyJhbGciOiJFUzI1NiIsImsiOiJ2dC8rcFVJKyJ9.eyJkaWciOiI4NmI0NWE4YWQyOGM4YzUwYzc1ZGI5ZmUwY2E1NDRiZjE3ZTdlZTg1MzA0MTI1OTU1ZTcxMTQ3OTU5ZjA4OGU5Iiwib3JpIjoibHlueC1pbnRlcmFjdGlvbiIsImhkaWciOmZhbHNlLCJpaWMiOiJhdzEiLCJpc3MiOiJmaWxlIiwiZXhwIjoxNzg0MDAwMTczLCJhdWQiOiJ6ZnMiLCJpYXQiOjE3ODM5OTkyNzN9.NicE06tqfTnNQPeaBC0hDpuDma6Goh7i17oNqT7lTkEZyi8RV_2gCkrMIdxHzkUev3fpVBm93fLX0pTEDFnP2A&Policy=eyJTdGF0ZW1lbnQiOlt7IkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NDAwMDE3M319LCJSZXNvdXJjZSI6Imh0dHBzOi8vZmlsZS1wYWEuem9vbS51cy9maWxlL1lEeXNyT0VqUmZHNzJ5dEQtWW8xc0E~ZmlsZW5hbWU9aW1hZ2UucG5nJmp3dD1leUpoYkdjaU9pSkZVekkxTmlJc0ltc2lPaUoyZEM4cmNGVkpLeUo5LmV5SmthV2NpT2lJNE5tSTBOV0U0WVdReU9HTTRZelV3WXpjMVpHSTVabVV3WTJFMU5EUmlaakUzWlRkbFpUZzFNekEwTVRJMU9UVTFaVGN4TVRRM09UVTVaakE0T0dVNUlpd2liM0pwSWpvaWJIbHVlQzFwYm5SbGNtRmpkR2x2YmlJc0ltaGthV2NpT21aaGJITmxMQ0pwYVdNaU9pSmhkekVpTENKcGMzTWlPaUptYVd4bElpd2laWGh3SWpveE56ZzBNREF3TVRjekxDSmhkV1FpT2lKNlpuTWlMQ0pwWVhRaU9qRTNPRE01T1RreU56TjkuTmljRTA2dHFmVG5OUVBlYUJDMGhEcHVEbWE2R29oN2kxN29OcVQ3bFRrRVp5aThSVl8yZ0Nrck1JZHhIemtVZXYzZnBWQm05M2ZMWDBwVEVERm5QMkEifV19&Signature=TQltGY8CkoKFHkbWoum1uYEda2UfJBtH3lKBttOO5CWkctjwuxaVplUlJIEuxoJw9C~2A0px9J3YG2bxFelnzO8URGydhFEEajAeuTYWbkmXi4hl4jdBX0GrseBC4Rcs0b7ORuOFucW0KFyYyLzHcTVauzV8cWznhU2dRelqw6Xt-UG2VDA32bdiDOGQ~~~kRHINWYGhhTj~Vape6EJnq1lE8X4QfZaxS8ngQkEUXooc0g46A5ez9kxSOovb6~B6X5MBOpkaFca~A-hXMqmA0Epp61nehnkbrBeEu0uAoaadPhjLlku7HAKPbdYbAay05vw5mbCXW5PFUPFHshJkrg__&Key-Pair-Id=KL18RPQB3R725)

舆情仪表盘，可以看到全局 KPI、平台分布、趋势，以及客满/研发/商品三套归因 Top；可进各工作台。
### AI智能助手


![image.png](https://file-paa.zoom.us/file/C0Kg7pqtR-GQMplr3jyHkg?filename=image.png&jwt=eyJrIjoidnQvK3BVSSsiLCJhbGciOiJFUzI1NiJ9.eyJoZGlnIjpmYWxzZSwiZXhwIjoxNzg0MDAwMTczLCJkaWciOiIwYjgxNDk1YjliNDEyNmY5ZWE2N2YzNzQyYmUwNzRlNTg1YzUyMDBjYmM0ZGRhNjI1MjgyMThjYjkzNjJkZWM2IiwiaXNzIjoiZmlsZSIsImF1ZCI6InpmcyIsImlpYyI6ImF3MSIsImlhdCI6MTc4Mzk5OTI3Mywib3JpIjoibHlueC1pbnRlcmFjdGlvbiJ9.HBGhIevsUmfl7OaDXO_0UiUr6_4b5tWAo81FHlSW64CWKq_HMPg9KiIkjETuta6uQDH7emWHHec1giU2NiEWbw&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9maWxlLXBhYS56b29tLnVzL2ZpbGUvQzBLZzdwcXRSLUdRTXBscjNqeUhrZz9maWxlbmFtZT1pbWFnZS5wbmcmand0PWV5SnJJam9pZG5RdkszQlZTU3NpTENKaGJHY2lPaUpGVXpJMU5pSjkuZXlKb1pHbG5JanBtWVd4elpTd2laWGh3SWpveE56ZzBNREF3TVRjekxDSmthV2NpT2lJd1lqZ3hORGsxWWpsaU5ERXlObVk1WldFMk4yWXpOelF5WW1Vd056UmxOVGcxWXpVeU1EQmpZbU0wWkdSaE5qSTFNamd5TVRoallqa3pOakprWldNMklpd2lhWE56SWpvaVptbHNaU0lzSW1GMVpDSTZJbnBtY3lJc0ltbHBZeUk2SW1GM01TSXNJbWxoZENJNk1UYzRNems1T1RJM015d2liM0pwSWpvaWJIbHVlQzFwYm5SbGNtRmpkR2x2YmlKOS5IQkdoSWV2c1VtZmw3T2FEWE9fMFVpVXI2XzRiNXRXQW84MUZIbFNXNjRDV0txX0hNUGc5S2lJa2pFVHV0YTZ1UURIN2VtV0hIZWMxZ2lVMk5pRVdidyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NDAwMDE3M319fV19&Signature=I9pSTO-PqxV51R77~BxBTrkujozTjipIbQrb2bJfmXVlR-1ul5koo1NlX4ZnMgo54iocQVibbCzaAJ~y7Nf757wYMJLgNpYHg5jJuwGNeNC7SKXHulmRCoc5GVsVmL76hiRKXDPAr7bPq5lyNNUJIQIa0O2CL~9248pXTkao1~HP24ZisxmNRjQkgzZEriQiuKsNFvgn7ovHIe6LU-NBlzOfyZF7uVq38t7afqMGd7JDHvcGqcGuhKWXFBPl55WLqbxmg4y5gP8OsGZZxkzxHWKlBm1TikBdBt7erN~LQ8JhWv7uKNpU2g6du3xtEZ~I6zuffCi5JGJNhqwxhzdKcg__&Key-Pair-Id=KL18RPQB3R725)

自然语言查数、归因解读、图表与溯源，支持多轮追问。

### 客服工作台


![image.png](https://file-paa.zoom.us/file/FJwT4gRJQb6uvifwfEWEuQ?filename=image.png&jwt=eyJhbGciOiJFUzI1NiIsImsiOiJ2dC8rcFVJKyJ9.eyJpc3MiOiJmaWxlIiwiYXVkIjoiemZzIiwiaGRpZyI6ZmFsc2UsImlhdCI6MTc4Mzk5OTI3MywiZGlnIjoiOWUzMGVlOWM2OGQxNjQxODIyNjc5ZGI3OGMwMGMzNDg3NTViNDgxMzA0ZmY4MzA2M2NlNTZkODNjMDhlYmE0OSIsImlpYyI6ImF3MSIsIm9yaSI6Imx5bngtaW50ZXJhY3Rpb24iLCJleHAiOjE3ODQwMDAxNzN9.1UTK9Z0WL0wy0aMmarJePH80jrlCxC-wJI7W4UZj8eDSqCc1-i6hCsywidzs_7HeUsdYihAwVYpkUGwPb9w91w&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9maWxlLXBhYS56b29tLnVzL2ZpbGUvRkp3VDRnUkpRYjZ1dmlmd2ZFV0V1UT9maWxlbmFtZT1pbWFnZS5wbmcmand0PWV5SmhiR2NpT2lKRlV6STFOaUlzSW1zaU9pSjJkQzhyY0ZWSkt5SjkuZXlKcGMzTWlPaUptYVd4bElpd2lZWFZrSWpvaWVtWnpJaXdpYUdScFp5STZabUZzYzJVc0ltbGhkQ0k2TVRjNE16azVPVEkzTXl3aVpHbG5Jam9pT1dVek1HVmxPV00yT0dReE5qUXhPREl5TmpjNVpHSTNPR013TUdNek5EZzNOVFZpTkRneE16QTBabVk0TXpBMk0yTmxOVFprT0ROak1EaGxZbUUwT1NJc0ltbHBZeUk2SW1GM01TSXNJbTl5YVNJNklteDVibmd0YVc1MFpYSmhZM1JwYjI0aUxDSmxlSEFpT2pFM09EUXdNREF4TnpOOS4xVVRLOVowV0wwd3kwYU1tYXJKZVBIODBqcmxDeEMtd0pJN1c0VVpqOGVEU3FDYzEtaTZoQ3N5d2lkenNfN0hlVXNkWWloQXdWWXBrVUd3UGI5dzkxdyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NDAwMDE3M319fV19&Signature=RD4qOj7FEMtEZWL9J2J4eW4U9pzMJ-jZX-laSGl4cLC-Zmx6mO2IpNoIiqG2-xdyM3tgiZo7dJHR4G~gTbdOWoQ-YOqFIdkYVa3E1arCW0Jt2QTJ4GSRnJ1I9fKU3sr5Lxwke9b51B-hRGYeodbBdCS1TrW3AgJLJdsQnjJci9Ug0D2p6sqfVHTHjfAo7LJhQufPkScWQ0yH9de~JusPgnZRSxmKPhqPkeGIcZAD7WeC0VIKI2OO5nnt8H0PKzf0lQc1rnYu75HWvzRfds-wzKfr3X62GjuHtrWqF5XqVzMMRl-dg58XUr49NHAdfpJGfp5iM-8P38D-ic2NcGrSVQ__&Key-Pair-Id=KL18RPQB3R725)

广告帖差评榜、产品避雷、敏感词预警。

### 评论明细导出


![image.png](https://file-paa.zoom.us/file/lbiRoH0jTEeDzkrDctF8Vw?filename=image.png&jwt=eyJhbGciOiJFUzI1NiIsImsiOiJ2dC8rcFVJKyJ9.eyJkaWciOiIyYmI0OTdmNzEyNmU5YmFlYTUxYzIyMjk2Y2MxMjgxNWZlNmUzMjZmMDY5YjcxNTFjZmExYTIyMWY3M2IyYWNhIiwib3JpIjoibHlueC1pbnRlcmFjdGlvbiIsImhkaWciOmZhbHNlLCJpaWMiOiJhdzEiLCJpc3MiOiJmaWxlIiwiZXhwIjoxNzg0MDAwMTczLCJhdWQiOiJ6ZnMiLCJpYXQiOjE3ODM5OTkyNzN9.3bJd1KWmWXyvHNY_sO-7TwbFl2dg2b883AK8VWKVqH47Vh5ucZUAfyUplmhs7t_8PI04e9hcbttdGtOwOm9ZOA&Policy=eyJTdGF0ZW1lbnQiOlt7IkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NDAwMDE3M319LCJSZXNvdXJjZSI6Imh0dHBzOi8vZmlsZS1wYWEuem9vbS51cy9maWxlL2xiaVJvSDBqVEVlRHprckRjdEY4Vnc~ZmlsZW5hbWU9aW1hZ2UucG5nJmp3dD1leUpoYkdjaU9pSkZVekkxTmlJc0ltc2lPaUoyZEM4cmNGVkpLeUo5LmV5SmthV2NpT2lJeVltSTBPVGRtTnpFeU5tVTVZbUZsWVRVeFl6SXlNamsyWTJNeE1qZ3hOV1psTm1Vek1qWm1NRFk1WWpjeE5URmpabUV4WVRJeU1XWTNNMkl5WVdOaElpd2liM0pwSWpvaWJIbHVlQzFwYm5SbGNtRmpkR2x2YmlJc0ltaGthV2NpT21aaGJITmxMQ0pwYVdNaU9pSmhkekVpTENKcGMzTWlPaUptYVd4bElpd2laWGh3SWpveE56ZzBNREF3TVRjekxDSmhkV1FpT2lKNlpuTWlMQ0pwWVhRaU9qRTNPRE01T1RreU56TjkuM2JKZDFLV21XWHl2SE5ZX3NPLTdUd2JGbDJkZzJiODgzQUs4VldLVnFINDdWaDV1Y1pVQWZ5VXBsbWhzN3RfOFBJMDRlOWhjYnR0ZEd0T3dPbTlaT0EifV19&Signature=SVRX2wVAO2b0rPiFCj9uVI4fUTH0IXxlAzCcrAWTJHc~zya6XzaltGQgaQ71ZRKAvWqFI8yMZVlkYfA3XMP6EcKG7ChD2nZCNoCNoJOTiwQQtHDDnfS0VQCx2fo9NT7Jjh7cR9kVYNHLqMT8MQ9vmjrPMoMWhl7pi2warCzd2MDTzNoWQHilcHdBj45pxkOVZ~6ekGFMbtxmX91kIpmaJ7qNKAgEjBGZUdjpb9jJ5i5ZWjIbmLBvgXRcYgin9yFxlonkRggwipPnY3HgX6uJJGJaug6~YfVnZXbi3DgFUkPrSMqHmEMIV-fS3d5lQVSBsEe-bwe7wz-M5aQbdar1VA__&Key-Pair-Id=KL18RPQB3R725)


