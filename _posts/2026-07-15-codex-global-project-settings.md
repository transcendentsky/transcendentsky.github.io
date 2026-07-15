---
title: Codex 全局设置与项目内设置：AGENTS、Skills、MCP、Hooks 和 Rules 应该放哪里
categories:
  - technews
tags:
  - Codex
  - OpenAI
  - Agent
  - Skills
  - MCP
  - 开发工具
---

# Codex 全局设置与项目内设置：AGENTS、Skills、MCP、Hooks 和 Rules 应该放哪里

很多人在配置 Codex 时会把所有东西都塞进一个目录：全局提示词、项目规则、MCP、Skills、Hooks、认证文件混在一起。短期能跑，长期会变得不可维护，也容易把本该只属于本机的凭据或偏好提交进仓库。

这篇文章按 **全局设置** 和 **项目内设置** 分开整理 Codex 的推荐结构，并纠正两个容易混淆的路径概念：

- Skills 的官方主要路径是 `~/.agents/skills/` 和 `<repo>/.agents/skills/`，不是 `.codex/skills/`。
- MCP 通常配置在 `config.toml` 的 `[mcp_servers.*]` 中，不是固定的 `.codex/mcps/` 目录。

![Codex 全局设置与项目设置分工图](/assets/images/codex-settings/global-project-map.svg)

<!--more-->

---

## 一、先看总原则

最核心的分工可以概括成一句话：

> 全局配置定义“我怎么工作”，项目配置定义“这个仓库怎么开发”。

| 能力 | 全局位置 | 项目位置 | 推荐分工 |
| --- | --- | --- | --- |
| 长期指令 | `~/.codex/AGENTS.md` | `<repo>/AGENTS.md` | 全局放通用偏好，项目放仓库规则 |
| 主配置 | `~/.codex/config.toml` | `<repo>/.codex/config.toml` | 全局放模型、MCP、认证、默认权限；项目放执行策略 |
| Skills | `~/.agents/skills/` | `<repo>/.agents/skills/` | 多项目复用放全局，只在本仓库成立放项目 |
| Hooks | `~/.codex/hooks.json` | `<repo>/.codex/hooks.json` | 全局放安全底线，项目放 lint/test/schema 等检查 |
| Rules | `~/.codex/rules/` | `<repo>/.codex/rules/` | 全局放通用禁令，项目放具体命令策略 |
| MCP | 全局 `config.toml` 为主 | 项目可定义项目特定项 | 凭据和供应商设置应留在全局 |
| Subagents | 全局 `config.toml` | 项目 `.codex/config.toml` | 通用角色放全局，仓库专用角色放项目 |
| Auth / Logs / Sessions | `~/.codex/` | 不建议放项目 | 绝不要提交认证和会话数据 |

---

## 二、全局设置：当前用户所有项目共享

全局设置的作用范围是当前用户的所有 Codex 项目。主要目录是：

```text
~/.codex/
~/.agents/skills/
```

Windows 一般对应：

```text
%USERPROFILE%\.codex\
```

### 推荐目录结构

```text
~/
├── .codex/
│   ├── config.toml
│   ├── AGENTS.md
│   ├── hooks.json
│   ├── rules/
│   │   └── default.rules
│   ├── prompts/
│   │   ├── review-pr.md
│   │   └── write-tests.md
│   ├── deep-review.config.toml
│   ├── fast.config.toml
│   ├── auth.json
│   ├── sessions/
│   └── logs/
│
└── .agents/
    └── skills/
        ├── code-review/
        │   └── SKILL.md
        ├── research/
        │   └── SKILL.md
        └── debug/
            └── SKILL.md
```

其中 `auth.json`、`sessions/`、`logs/`、`cache/` 等通常由 Codex 自动生成，不需要手动创建，也不要复制到项目仓库。

---

## 三、全局 `AGENTS.md`：你的通用工作习惯

位置：

```text
~/.codex/AGENTS.md
```

它适合定义你希望 Codex 在所有项目中默认遵守的习惯，例如：

- 默认使用中文还是英文。
- 代码风格偏好。
- 是否先写计划再修改代码。
- 是否必须运行测试。
- 是否允许修改依赖。
- 默认 Git 操作规范。
- 输出格式要求。
- 安全操作要求。
- 是否优先修复根因而不是绕过问题。

示例：

```markdown
# Global Codex Instructions

- 使用中文解释，代码和注释使用英文。
- 修改代码前先阅读相关测试和调用链。
- 不要使用 `any` 绕过 TypeScript 类型检查。
- 完成修改后运行相关测试。
- 不主动执行 git push、git reset --hard 或删除分支。
- 不修改与当前任务无关的文件。
```

全局 `AGENTS.md` 应只放通用习惯，不要放某一个项目的架构信息。

---

## 四、全局 `config.toml`：模型、权限、MCP 和工具入口

位置：

```text
~/.codex/config.toml
```

这是用户级最核心的配置文件。

### 1. 模型配置

```toml
model = "gpt-5.5"
model_reasoning_effort = "high"
```

通常包括：

- 默认模型。
- 推理强度。
- 模型上下文管理。
- 输出详细程度。
- 自动压缩上下文策略。
- 模型提供商。

### 2. 沙箱和审批策略

```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"
```

这类配置决定 Codex：

- 能否修改文件。
- 能否访问项目外目录。
- 什么时候询问用户。
- 能否访问网络。
- 能否执行高风险命令。

常见字段包括：

| 字段 | 常见值 | 含义 |
| --- | --- | --- |
| `approval_policy` | `untrusted` / `on-request` / `never` | 控制何时请求用户批准 |
| `sandbox_mode` | `read-only` / `workspace-write` / 更高权限模式 | 控制文件系统边界 |
| 网络策略 | 依环境而定 | 控制网络访问和下载依赖 |

沙箱是操作系统层面的边界，审批策略是用户交互层面的边界，两者不要混为一谈。

### 3. MCP Servers

MCP 通常配置在 `config.toml` 的 `[mcp_servers.*]` 中：

```toml
[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]

[mcp_servers.github.env]
GITHUB_TOKEN = "${GITHUB_TOKEN}"
```

MCP 可以连接：

- GitHub / GitLab。
- Jira / Linear。
- Figma。
- 数据库。
- 浏览器。
- 文件系统。
- 企业内部接口。
- 自定义工具服务。

建议把需要凭据、依赖本机环境的 MCP 配置放在全局配置，不要提交到项目仓库。

### 4. Apps / Connectors

```toml
[apps._default]
enabled = true
default_tools_approval_mode = "prompt"
destructive_enabled = false
open_world_enabled = false
```

这类配置通常和当前用户的账号授权相关，因此更适合放在全局级别。可配置内容包括：

- 是否启用某个 App。
- App 中哪些工具可用。
- 是否允许破坏性操作。
- 是否允许访问开放网络。
- 工具调用是否需要审批。
- 每个工具的单独权限。

### 5. Subagents

```toml
[agents.reviewer]
description = "Review code for correctness, regressions, and missing tests."
config_file = "/Users/quan/.codex/agents/reviewer.toml"

[agents.explorer]
description = "Explore the repository without modifying files."
config_file = "/Users/quan/.codex/agents/explorer.toml"
```

适合定义全局通用角色：

- `explorer`
- `reviewer`
- `tester`
- `security-reviewer`
- `researcher`
- `documentation-writer`

角色配置里还可以进一步设置模型、推理强度和沙箱模式：

```toml
model = "gpt-5.5"
model_reasoning_effort = "high"
sandbox_mode = "read-only"
```

### 6. 功能开关

```toml
[features]
multi_agent = true
web_search = true
```

功能开关可能涉及：

- 多 Agent。
- Web 搜索。
- 实验性功能。
- Apps。
- Plugins。
- 特定客户端功能。

具体字段会随 Codex 版本变化，最好以当前 `config-reference` 或配置 Schema 为准。

### 7. 通知与可观测性

```toml
notify = ["python", "/Users/quan/scripts/codex_notify.py"]
```

可能包括：

- 任务完成通知。
- 桌面通知。
- 命令回调。
- 日志。
- OpenTelemetry。
- 使用情况和诊断信息。
- 会话记录位置。

这类机器相关设置只能放在用户级配置中，项目级配置不能覆盖 `notify` 和 `otel`。

### 8. 自定义模型提供商

```toml
model = "custom-model"
model_provider = "company-proxy"

[model_providers.company-proxy]
name = "Company AI Gateway"
base_url = "https://ai.example.com/v1"
env_key = "COMPANY_AI_TOKEN"
wire_api = "responses"
```

模型提供商、认证和 Base URL 只能由用户级配置控制，项目级配置不能改变这些敏感设置。

---

## 五、全局 Skills：`~/.agents/skills/`

当前用户级 Skills 路径：

```text
~/.agents/skills/
```

例如：

```text
~/.agents/skills/
├── code-review/
│   ├── SKILL.md
│   ├── scripts/
│   └── references/
├── paper-analysis/
│   └── SKILL.md
└── debug-systematically/
    └── SKILL.md
```

全局 Skill 适合：

- 通用代码审查。
- 系统化调试。
- 技术调研。
- 写单元测试。
- 生成变更日志。
- 论文分析。
- 项目规划。
- 安全审计。

官方当前定义的 Skill 层级包括：

| 层级 | 路径 |
| --- | --- |
| 用户级 | `$HOME/.agents/skills/` |
| 仓库级 | `$REPO_ROOT/.agents/skills/` |
| 管理员级 | `/etc/codex/skills/` |
| 系统级 | Codex 内置 |

判断原则很简单：

```text
多个项目都能用 -> 放 ~/.agents/skills/
只有当前仓库能用 -> 放 <repo>/.agents/skills/
```

---

## 六、全局 Hooks、Rules、Profiles 和 Prompts

### 1. Hooks

支持位置：

```text
~/.codex/hooks.json
```

也可以直接写在：

```text
~/.codex/config.toml
```

典型用途：

- 命令执行前检查。
- 工具调用前审批。
- 修改文件后格式化。
- 任务结束后运行测试。
- 完成后发送通知。
- 记录运行日志。
- 防止访问敏感目录。
- 阻止危险命令。

同一层级最好只使用 `hooks.json` 或 TOML 内联 Hooks 中的一种。如果两者同时存在，Codex 可能会同时加载并给出警告。

### 2. Rules

常见位置：

```text
~/.codex/rules/
```

适合设置：

```text
git status            -> allow
git diff              -> allow
pytest                -> allow
npm test              -> allow
docker compose up     -> prompt
curl                  -> prompt
rm -rf                -> forbid
git push --force      -> forbid
```

Rules 与沙箱不同：

```text
sandbox = 操作系统层面的边界
rules   = 针对具体命令或工具的策略判断
```

### 3. Profiles

文件位置示例：

```text
~/.codex/deep-review.config.toml
~/.codex/fast.config.toml
~/.codex/read-only.config.toml
```

调用方式：

```bash
codex --profile deep-review
```

适合建立：

| Profile | 用途 |
| --- | --- |
| `fast` | 快速日常修改 |
| `deep-review` | 深入代码审查 |
| `read-only` | 只读分析 |
| `research` | 技术调研 |
| `automation` | 无人值守执行 |

加载顺序通常是先读取 `~/.codex/config.toml`，再叠加指定 Profile。

### 4. Custom Prompts

位置：

```text
~/.codex/prompts/
```

示例：

```text
~/.codex/prompts/review-pr.md
```

调用：

```text
/prompts:review-pr
```

但需要注意：Custom Prompts 已被标记为 deprecated，更推荐把可复用流程迁移到 Skills。

---

## 七、项目内设置：当前仓库共享

项目内设置的作用范围是当前仓库或仓库中的某个子目录。它的特点是可以随 Git 仓库共享给团队。

推荐结构：

```text
project/
├── AGENTS.md
├── AGENTS.override.md
│
├── frontend/
│   └── AGENTS.md
├── backend/
│   └── AGENTS.md
│
├── .codex/
│   ├── config.toml
│   ├── hooks.json
│   ├── rules/
│   │   └── project.rules
│   └── local-environment configuration
│
├── .agents/
│   └── skills/
│       ├── run-evals/
│       │   └── SKILL.md
│       ├── database-migration/
│       │   └── SKILL.md
│       └── release-project/
│           └── SKILL.md
│
├── scripts/
├── docs/
├── tests/
└── src/
```

---

## 八、项目 `AGENTS.md`：这个仓库应该如何开发

位置：

```text
project/AGENTS.md
```

用于告诉 Codex：

- 项目是什么。
- 项目如何构建。
- 项目如何测试。
- 代码放在哪里。
- 架构边界是什么。
- 哪些目录不能修改。
- PR 审查关注什么。
- 完成标准是什么。

示例：

```markdown
# Project Instructions

## Repository structure

- `apps/web`: Next.js frontend
- `services/api`: FastAPI backend
- `packages/shared`: shared TypeScript types

## Commands

- Install: `pnpm install`
- Lint: `pnpm lint`
- Test: `pnpm test`
- Build: `pnpm build`

## Rules

- Do not edit generated files under `src/generated`.
- Add tests for every bug fix.
- Database schema changes require a migration.
- Shared API types must be defined in `packages/shared`.
```

如果是大型仓库，可以在子目录继续放置：

```text
project/
├── AGENTS.md
├── frontend/
│   └── AGENTS.md
└── backend/
    └── AGENTS.md
```

根 `AGENTS.md` 定义整个仓库的公共规则，子目录 `AGENTS.md` 定义局部技术栈和测试规范。

---

## 九、项目 `.codex/config.toml`

位置：

```text
project/.codex/config.toml
```

适合放：

- 当前项目默认模型或推理强度。
- 项目沙箱策略。
- 项目 Hooks。
- 项目 Rules。
- 项目 Subagents。
- 项目特定功能开关。
- 项目指令文件。
- 根目录识别。
- 项目工具配置。

示例：

```toml
model_reasoning_effort = "high"
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[agents.test-reviewer]
description = "Review test coverage and identify missing edge cases."
config_file = "./agents/test-reviewer.toml"

[features]
multi_agent = true
```

### 支持多级项目配置

Codex 会从项目根目录向当前工作目录查找：

```text
repo/.codex/config.toml
repo/apps/.codex/config.toml
repo/apps/web/.codex/config.toml
```

越靠近当前工作目录的配置优先级越高。

### 项目配置不能覆盖的内容

项目 `.codex/config.toml` 不能覆盖涉及账号、凭据和机器级行为的设置，包括：

```text
openai_base_url
chatgpt_base_url
model_provider
model_providers
notify
profile
profiles
otel
```

这些内容应放在全局，避免不可信仓库劫持认证、请求地址或本机通知命令。

---

## 十、项目 Skills、Hooks、Rules 和 Subagents

### 1. 项目 Skills

位置：

```text
project/.agents/skills/
```

适合放：

- 本项目特定测试流程。
- 数据库迁移规范。
- 项目发布流程。
- 内部 API 生成。
- Benchmark 运行。
- 数据处理流程。
- 特殊代码生成。
- 项目文档同步。

例如：

```text
project/.agents/skills/
├── run-project-tests/
│   ├── SKILL.md
│   └── scripts/
│       └── test.sh
├── create-db-migration/
│   └── SKILL.md
└── release-service/
    └── SKILL.md
```

### 2. 项目 Hooks

位置：

```text
project/.codex/hooks.json
```

或者写在：

```text
project/.codex/config.toml
```

适合：

- 修改 Python 后自动运行 Ruff。
- 修改 TypeScript 后运行 ESLint。
- 提交前运行单元测试。
- 修改 API Schema 后重新生成客户端。
- 修改数据库模型后检查 migration。
- 阻止修改生成文件。
- 阻止访问 `.env`。
- 检查许可证头。

### 3. 项目 Rules

常见位置：

```text
project/.codex/rules/
```

适合定义：

```text
允许：
pnpm lint
pnpm test
pytest
cargo test
go test ./...

需要确认：
docker compose down
terraform apply
kubectl apply
数据库迁移

禁止：
读取 .env.production
访问生产数据库
git push --force
删除迁移历史
修改 vendor 目录
```

### 4. 项目 Subagents

可在项目 `.codex/config.toml` 中定义专用角色：

```toml
[agents.frontend-reviewer]
description = "Review React components, accessibility, state handling, and frontend tests."
config_file = "./agents/frontend-reviewer.toml"

[agents.database-reviewer]
description = "Review database migrations, locking risks, indexes, and rollback safety."
config_file = "./agents/database-reviewer.toml"
```

项目角色可以了解当前架构、测试规范、风险边界和目录结构。

---

## 十一、Local Environments、Worktrees 和 Cloud Environment

Codex App 可以在项目 `.codex/` 中保存本地环境配置，主要包括 Setup Scripts 和 Common Actions。

### Setup Scripts

创建 Worktree 后自动执行：

```bash
pnpm install
cp .env.example .env.local
docker compose up -d postgres
pnpm db:migrate
```

### Common Actions

定义项目快捷操作：

```text
Run tests
Run lint
Start dev server
Build project
Reset database
Generate API client
```

Worktree 本身不是单独的文本配置模块，但会受到以下项目设置影响：

- Setup Scripts。
- `.codex/config.toml`。
- 项目 Hooks。
- 项目 Rules。
- `AGENTS.md`。
- 项目 Skills。
- Git 忽略规则。
- 本地环境配置。

Codex Cloud 项目还可以在 Web 设置中配置容器镜像、运行时版本、安装脚本、环境变量、Secrets、网络访问、允许域名和缓存等。

---

## 十二、配置优先级

可以概括为：

![Codex 配置加载优先级](/assets/images/codex-settings/config-priority.svg)

```text
管理员强制要求
    ↓
用户全局配置 ~/.codex/config.toml
    ↓
指定 Profile
    ↓
项目根目录 .codex/config.toml
    ↓
项目子目录 .codex/config.toml
    ↓
命令行参数
    ↓
当前会话临时设置
```

项目配置采用“距离当前工作目录越近，优先级越高”的原则。但项目配置不能覆盖模型供应商、认证、通知和 Telemetry 等敏感用户级设置。

---

## 十三、最推荐的实际结构

```text
# 用户全局
~/
├── .codex/
│   ├── AGENTS.md
│   ├── config.toml
│   ├── hooks.json
│   ├── rules/
│   ├── deep-review.config.toml
│   └── fast.config.toml
└── .agents/
    └── skills/
        ├── systematic-debugging/
        ├── code-review/
        └── technical-research/


# 单个项目
project/
├── AGENTS.md
├── .codex/
│   ├── config.toml
│   ├── hooks.json
│   ├── rules/
│   └── local environment config
├── .agents/
│   └── skills/
│       ├── run-evals/
│       ├── database-migration/
│       └── release-project/
├── src/
├── tests/
└── scripts/
```

最核心的分工：

```text
全局 AGENTS.md
= 我的通用工作偏好

项目 AGENTS.md
= 这个仓库应该如何开发

全局 config.toml
= 我的模型、权限、MCP、认证和通用 Agent

项目 config.toml
= 这个仓库的执行策略和专用 Agent

全局 Skills
= 我到任何项目都能复用的能力

项目 Skills
= 只有这个仓库才成立的工作流

全局 Rules
= 任何情况下都不能突破的安全底线

项目 Rules
= 当前项目允许和禁止的具体操作
```

---

## 十四、一个实用判断法

当你不知道配置该放哪里时，可以问这四个问题：

| 问题 | 如果答案是“是” | 推荐位置 |
| --- | --- | --- |
| 是否包含账号、Token、Base URL、模型供应商？ | 是 | 全局 |
| 是否是我的个人工作偏好？ | 是 | 全局 |
| 是否只有这个仓库才成立？ | 是 | 项目 |
| 是否需要团队共享并随仓库演进？ | 是 | 项目 |

最后记住这条底线：

> 凭据、认证、模型供应商、通知和 telemetry 留在全局；架构、测试、目录规则和项目专用流程放进仓库。

---

## 参考资料

- [Codex advanced configuration](https://developers.openai.com/codex/config-advanced.md)
- [Agent approvals and security](https://developers.openai.com/codex/agent-approvals-security.md)
- [Subagents](https://developers.openai.com/codex/concepts/subagents.md)
- [Codex config schema](https://developers.openai.com/codex/config-schema.json)
- [Skills](https://developers.openai.com/codex/skills.md)
- [Custom prompts](https://developers.openai.com/codex/custom-prompts.md)
- [Customization](https://developers.openai.com/codex/concepts/customization.md)
- [Local environments](https://developers.openai.com/codex/app/local-environments.md)
- [Worktrees](https://developers.openai.com/codex/app/worktrees.md)
- [Cloud environments](https://developers.openai.com/codex/cloud/environments.md)
