# Plan: AT 智能选品 MVP（可落地）
_Locked via grill — by Claude + Shelly / 业务确认_  
_Act 2 Codex APPROVED — 2026-07-24_  
_**PRD v0.5（产品 Owner 审阅）为产品权威**；与下文冲突时以 [PRD-AT智能选品MVP.md](./PRD-AT智能选品MVP.md) 为准_

> 选品逻辑来自 **AT 运营访谈**；试点 **AT**。实现规格以 **PRD v0.5** 为准。

## Goal

以 **AT** 跑通智能化选品闭环，服务网站 **增量**：竞品上新不漏可跟、成稿提速（KR2 −50%）、AI 建议全覆盖、负责人一次通过率 ≥80%；BOM×5 评价格优势；**库存信息**评可生产性；审批通过写入选款。埋点 `system_hub_at` 仅系统/BI，不干扰审批观感。

## Approach（与 PRD v0.5 对齐）

1. **信号**：雷达 AT 轨上新⋈列表序；社媒人工；AZ 相似款三维匹配。  
2. **机会池**：上新×列表/热销靠前 → 草稿。  
3. **成本**：bom→similar→rule→manual；价带 SPU P25–P75。  
4. **可生产性（Owner）**：相似款/物料 **库存** → producibility ok/risky/unknown（非交期大盘）。  
5. **AI 建议**：gates 事实 + 允许集内四档；可 override。  
6. **审批→选款**：同事务 Sync_Pending；generation_source 唯一。

## Key decisions（superseded notes）

| 原 Act2 表述 | v0.5 Owner 对齐 |
|--------------|-----------------|
| craft/capability/fabric 为主供应链叙事 | **库存可生产性为主**；craft 为辅 |
| KR1 +50% 方案数 | **不漏上新 + 缩短周期**（周频默认；日频另评估） |
| KR2 −40% / 一次通过 60% | **−50% / ≥80%** |
| 埋点可进提案展示 | **系统字段，审批默认隐藏** |
| PLAN 与 PRD 冲突以 PLAN 为准 | **以 PRD v0.5 产品意图为准** |

工程加固仍建议保留（实现时按 PRD F1/F5/F8）：批次幂等、manifest 校验、list_rank≠on_hotlist、scheme_version、outbox。

## Out of scope

- 打板系统；Ins 自动爬；采购交期大盘；日频爬取（未立项）；BD/MOB 推广
