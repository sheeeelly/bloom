# 本机 Cursor 配置说明（迁移后）

生成日期：2026-07-28

## 已完成

| 项 | 位置 |
|----|------|
| Skills：`grill-me-codex` / `create-prd` / `codex-review` | `~/.cursor/skills/` |
| Skill：`intelligent-selection-pm`（选品提案决策） | `~/.cursor/skills/` 与本仓库 `.cursor/skills/` |
| 项目规则 `AGENTS.md` | 仓库根目录 |
| Always-on rules | `.cursor/rules/intelligent-selection-core.mdc`、`product-manager.mdc` |
| 文档/原型 rule | `.cursor/rules/docs-and-prototype.mdc` |
| 工作区项目目录 | `/Users/azazie/Desktop/自动化选品`（自迁移包 `project/` 同步） |

## 使用方式

1. 用 Cursor **打开** `/Users/azazie/Desktop/自动化选品`（不要只开迁移包外壳）。
2. **新开 Agent 会话**（或重启 Cursor）以加载 Skills。
3. 常用触发：
   - 「按智能选品 PM 帮我写 AI 建议」→ `intelligent-selection-pm`
   - 「grill 一下这个方案」→ `grill-me-codex`
   - 「写一份 PRD」→ `create-prd`
   - 「用 Codex 审 PLAN」→ `codex-review`

## 可选未完成

- `amazon-product-manager` 官方 skill：网络克隆失败时可稍后手动安装  
  https://github.com/KKKKkrisPhillllll/amazon-product-manager-skill/  
  本仓库已用 `intelligent-selection-pm` 吸收 PRD §0.A 决策骨架，可先不依赖该仓库。

## 权威文档

- 产品：`PRD-AT智能选品MVP.md`
- 计划：`PLAN.md`
- 全文规则：`AGENTS.md`
