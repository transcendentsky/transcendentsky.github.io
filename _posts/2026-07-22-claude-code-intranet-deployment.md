---
title: Claude Code 内网部署攻略：离线安装包、统一网关与本地模型
tags:
  - Claude Code
  - Intranet
  - Offline
  - LLM Gateway
---

> 一句话总结：内网部署 Claude Code 不应该只理解为“把 claude 命令装进去”。真正要拆成三件事：CLI 如何离线分发、模型请求如何走受控出口、权限和审计如何落地。离线安装包解决安装问题，`ANTHROPIC_BASE_URL` 解决模型出口问题，统一网关解决企业内网的安全和运维问题。

![Claude Code 内网部署三种模式](/assets/images/claude-code-intranet/deployment-modes.svg)

<!--more-->

最近很多团队都在问一个问题：能不能把 Claude Code 放到内网使用？

这个问题不能直接回答“能”或“不能”，因为它至少包含三层含义：

1. **Claude Code CLI 能不能离线安装？**
2. **Claude Code 的模型请求能不能不直连 Anthropic？**
3. **代码、日志、凭证、审计能不能满足内网安全要求？**

这三件事要分开看。

Claude Code 本质上是一个运行在终端里的编码代理。它会读取本地代码、运行命令、编辑文件，并把需要模型推理的上下文发送给后端模型服务。官方 GitHub 仓库也明确把它描述为一个 lives in your terminal 的 agentic coding tool。

所以内网部署的关键不是“把一个二进制文件复制进去”这么简单，而是要把下面三层打通：

| 层次 | 解决什么问题 |
| --- | --- |
| 安装分发层 | 内网机器如何安装 `claude` 命令 |
| 模型访问层 | `claude` 的请求发到哪里 |
| 治理运维层 | 凭证、权限、审计、升级、回滚怎么管 |

本文参考了公开的 Claude Code 官方文档、官方 GitHub 仓库，以及社区里类似 `claude-code-offline` 的离线包思路。需要说明：用户提到的 `DeepTrail/claude-code-offline` 仓库当前我无法从 GitHub 验证到可访问内容，因此本文不会把它当作可靠事实来源逐条引用，只吸收“离线包分发 + 校验 + 公共目录安装”这种工程思路。

## 一、先明确目标：你要的是哪种“内网部署”？

内网部署有三种常见目标。

| 目标 | 说明 | 难度 |
| --- | --- | --- |
| 内网离线安装 Claude Code | 公网机器下载二进制，打包后发到内网安装 | 低 |
| Claude Code 走企业统一 LLM 网关 | 开发机不直连 Anthropic，所有请求走内网网关 | 中 |
| 完全本地模型推理 | Claude Code 请求本地或内网开源模型，不出公网 | 高 |

三种目标不要混在一起。

如果你的公司允许受控公网出口，最推荐的是：

```text
Claude Code CLI 离线分发
  + 内网 LLM Gateway
  + 网关受控访问 Anthropic / Bedrock / Vertex / 私有模型
```

如果你的环境完全不能出网，那就要走：

```text
Claude Code CLI 离线分发
  + 本地或内网模型服务
  + Anthropic Messages API 兼容层
```

第二种会遇到更明显的模型能力差距。Claude Code 的代理工作流对模型的工具调用、长上下文、代码理解、遵循指令能力要求很高。不是所有本地模型都能稳定胜任。

## 二、推荐架构

推荐架构如下：

![Claude Code 内网网关架构](/assets/images/claude-code-intranet/gateway-architecture.svg)

核心原则：

1. 开发机只安装 Claude Code CLI。
2. 开发机不保存真实 Anthropic API Key。
3. 开发机通过 `ANTHROPIC_BASE_URL` 指向内网 LLM Gateway。
4. Gateway 统一做鉴权、审计、限流、模型路由。
5. Gateway 后端可以接 Anthropic、Bedrock、Vertex，也可以接本地模型。
6. 所有版本、配置、日志都可追踪。

为什么要加网关？

| 没有网关 | 有网关 |
| --- | --- |
| 每台机器都要配置 API Key | 开发机只配置内网 token |
| 调用审计分散 | 审计集中 |
| 难以限流 | 可按人、项目、部门限流 |
| 难以切模型 | 网关统一路由 |
| 凭证泄露风险高 | 上游凭证只在网关侧 |

内网环境里，网关不是可有可无。它是安全边界。

## 三、安装方式选择：不要再默认 npm

Claude Code 官方 GitHub README 里已经提示：npm 安装方式已 deprecated，推荐使用官方安装脚本、Homebrew、WinGet 等方式。

公网环境常见安装：

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

macOS/Linux 也可以：

```bash
brew install --cask claude-code
```

Windows 可以用：

```powershell
irm https://claude.ai/install.ps1 | iex
```

内网环境不建议让每台机器各自访问公网安装脚本。更合理的做法是：

1. 在受控公网机器下载官方 release。
2. 固定版本号。
3. 计算 checksum。
4. 生成离线包。
5. 上传内网制品库。
6. 内网机器从制品库安装。
7. 保留旧版本用于回滚。

## 四、离线包分发流程

离线安装包的工程目标：

1. 可重复。
2. 可校验。
3. 可审计。
4. 可回滚。

流程图：

![Claude Code 离线包分发流程](/assets/images/claude-code-intranet/package-flow.svg)

推荐目录：

```text
claude-code-offline/
  latest
  versions/
    2.1.91/
      linux-x64/
        claude
        sha256
      darwin-arm64/
        claude
        sha256
  install.sh
  manifest.json
```

`manifest.json` 示例：

```json
{
  "name": "claude-code-offline",
  "version": "2.1.91",
  "source": "https://github.com/anthropics/claude-code/releases",
  "build_time": "2026-07-22T10:00:00+08:00",
  "platforms": ["linux-x64", "darwin-arm64"],
  "maintainer": "platform-team"
}
```

内网安装脚本要做三件事：

1. 读取版本。
2. 校验 sha256。
3. 安装到公共目录。

示例：

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION="$(cat "$SCRIPT_DIR/latest")"
PLATFORM="${CLAUDE_CODE_PLATFORM:-linux-x64}"
INSTALL_DIR="${1:-/opt/claude-code/bin}"

BINARY="$SCRIPT_DIR/versions/$VERSION/$PLATFORM/claude"
CHECKSUM_FILE="$SCRIPT_DIR/versions/$VERSION/$PLATFORM/sha256"

if [ ! -f "$BINARY" ]; then
  echo "missing binary: $BINARY" >&2
  exit 1
fi

if [ -f "$CHECKSUM_FILE" ]; then
  expected="$(cat "$CHECKSUM_FILE")"
  actual="$(sha256sum "$BINARY" | awk '{print $1}')"
  if [ "$expected" != "$actual" ]; then
    echo "checksum mismatch" >&2
    exit 1
  fi
fi

mkdir -p "$INSTALL_DIR"
install -m 0755 "$BINARY" "$INSTALL_DIR/claude"

echo "installed: $INSTALL_DIR/claude"
```

公共目录建议：

```text
/opt/claude-code/
  versions/
    2.1.91/
  current -> versions/2.1.91
  bin/
    claude -> ../current/claude
```

这样回滚只需要切 symlink。

## 五、开发机环境变量

Claude Code 官方环境变量文档里，和内网部署最相关的是这几个：

| 变量 | 作用 |
| --- | --- |
| `ANTHROPIC_BASE_URL` | 覆盖 API endpoint，把请求发到代理或网关 |
| `ANTHROPIC_AUTH_TOKEN` | 设置 Bearer token |
| `ANTHROPIC_API_KEY` | 设置 Anthropic API key，优先级较高 |
| `ANTHROPIC_MODEL` | 指定模型 |
| `ANTHROPIC_CUSTOM_HEADERS` | 增加自定义请求头 |
| `API_TIMEOUT_MS` | 调整超时 |
| `DISABLE_TELEMETRY` | 关闭 telemetry |
| `DISABLE_LOGIN_COMMAND` | 隐藏 `/login` 命令 |
| `DISABLE_UPGRADE_COMMAND` | 隐藏 `/upgrade` 命令 |

开发机推荐配置：

```bash
export ANTHROPIC_BASE_URL="https://llm-gateway.intra.example.com"
export ANTHROPIC_AUTH_TOKEN="your-intranet-token"
export ANTHROPIC_MODEL="claude-sonnet-4-5"
export DISABLE_TELEMETRY=1
export DISABLE_UPGRADE_COMMAND=1
```

注意：如果同时设置了 `ANTHROPIC_API_KEY`，它可能优先于登录态。官方帮助中心也提醒，环境变量 API key 会覆盖订阅登录方式，可能导致意外计费或鉴权混乱。

内网统一部署时，建议明确禁止在个人 shell rc 中长期写真实上游 API Key。

检查：

```bash
env | grep -E 'ANTHROPIC|CLAUDE_CODE|DISABLE'
```

如果希望回到订阅登录：

```bash
unset ANTHROPIC_API_KEY
unset ANTHROPIC_AUTH_TOKEN
unset ANTHROPIC_BASE_URL
```

## 六、settings.json 统一下发

比起让每个用户手动 export，更可控的方式是下发 Claude Code settings。

示例：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://llm-gateway.intra.example.com",
    "ANTHROPIC_AUTH_TOKEN": "replace-with-user-token",
    "ANTHROPIC_MODEL": "claude-sonnet-4-5",
    "DISABLE_TELEMETRY": "1",
    "DISABLE_UPGRADE_COMMAND": "1"
  },
  "permissions": {
    "defaultMode": "ask"
  }
}
```

这里有两个重点：

1. `ANTHROPIC_AUTH_TOKEN` 不应该在公共模板里写死。
2. 权限默认建议保守，尤其是内网生产仓库。

团队可以做一个初始化脚本：

```bash
mkdir -p ~/.claude
cp /opt/claude-code/templates/settings.json ~/.claude/settings.json
```

然后通过 SSO、Vault、内部令牌服务写入用户 token。

## 七、内网 LLM Gateway 要做什么？

LLM Gateway 至少要提供这些能力：

| 能力 | 说明 |
| --- | --- |
| API 兼容 | 对 Claude Code 暴露 Anthropic API 兼容接口 |
| 鉴权 | 校验开发机 token |
| 审计 | 记录用户、项目、模型、token 用量、时间 |
| 限流 | 按用户/项目/部门控制并发和预算 |
| 脱敏 | 对日志做敏感信息处理 |
| 路由 | 不同模型、不同后端统一路由 |
| 超时 | 防止长请求拖垮网关 |
| 熔断 | 上游不可用时快速失败 |

最重要的是：网关日志不能直接明文永久保存完整代码上下文。

建议分级记录：

| 数据 | 建议 |
| --- | --- |
| 用户 ID | 保留 |
| 项目 ID | 保留 |
| 模型名 | 保留 |
| token 用量 | 保留 |
| 请求耗时 | 保留 |
| 工具调用摘要 | 可保留 |
| 完整 prompt | 默认不保留，或短期加密留存 |
| 完整代码片段 | 默认不保留 |

内网环境的主要目标不是“什么都记”，而是“出问题能定位，同时不扩大泄露面”。

## 八、完全离线本地模型模式

如果环境完全不能出网，可以让 Claude Code 请求一个本地或内网模型服务。

关键前提：这个服务要兼容 Anthropic Messages API，或者通过 LiteLLM/网关转换成兼容格式。

常见后端：

| 后端 | 说明 |
| --- | --- |
| Ollama | 适合单机快速验证 |
| LiteLLM | 适合做多模型路由和协议转换 |
| vLLM | 适合高性能 OpenAI 兼容推理，需要额外适配 Anthropic 协议 |
| LMDeploy | 适合高性能部署，同样需要协议适配 |
| LM Studio | 适合桌面本地模型测试 |

示例环境变量：

```bash
export ANTHROPIC_BASE_URL="http://localhost:11434"
export ANTHROPIC_AUTH_TOKEN="ollama"
export ANTHROPIC_MODEL="qwen2.5-coder:14b"
```

然后：

```bash
claude --model qwen2.5-coder:14b
```

但是这里要讲清楚限制：

1. 本地模型不等于 Claude。
2. 工具调用稳定性可能不足。
3. 长上下文能力可能不足。
4. 多文件复杂修改能力可能明显下降。
5. Claude Code 的某些特性可能依赖后端兼容程度。

因此，完全离线模式更适合：

| 场景 | 是否适合 |
| --- | --- |
| 简单代码解释 | 适合 |
| 小范围重构 | 可以 |
| 写测试和样板代码 | 可以 |
| 大规模跨文件改造 | 谨慎 |
| 安全敏感代码库初步辅助 | 适合 |
| 需要最强模型能力 | 不适合 |

本地模型建议先用小仓库压测，不要直接推广到核心生产仓库。

## 九、模型选择建议

内网部署 Claude Code，模型选择要看任务类型。

| 任务 | 推荐模型能力 |
| --- | --- |
| 代码解释 | 7B-14B coder 模型可试 |
| 单文件修改 | 14B 以上更稳 |
| 多文件重构 | 需要强 agent 能力和长上下文 |
| 测试生成 | 14B-32B coder 模型较合适 |
| 架构设计 | 云端 Claude 或更强私有模型 |
| 安全审计 | 需要更强推理和上下文，不建议只靠小模型 |

本地模型部署时重点看：

1. 上下文长度。
2. 工具调用稳定性。
3. 代码补丁准确率。
4. 指令遵循能力。
5. 推理速度。
6. 显存占用。

Claude Code 是 agent，不是普通 chat。能聊天的模型不一定能稳定当编码 agent。

## 十、权限策略

Claude Code 能运行命令和编辑文件，所以内网部署必须明确权限策略。

推荐默认策略：

| 行为 | 策略 |
| --- | --- |
| 读取项目文件 | 允许 |
| 编辑文件 | 需要用户确认 |
| 运行测试 | 允许或确认 |
| 安装依赖 | 需要确认 |
| 访问网络 | 默认禁止或走代理 |
| 删除文件 | 强确认 |
| 修改 Git 历史 | 禁止或强确认 |
| 读取密钥文件 | 禁止 |

项目内建议维护 `CLAUDE.md`：

```markdown
# Project Rules

- Do not read files under `secrets/`, `.env`, or `credentials/`.
- Do not run destructive git commands.
- Use `pytest` for tests.
- Do not install dependencies without explicit approval.
- All generated code must pass lint and tests.
```

安全团队可以提供企业级模板：

```text
/opt/claude-code/templates/CLAUDE.md
/opt/claude-code/templates/settings.json
/opt/claude-code/templates/allowed-tools.json
```

## 十一、内网代理和证书

很多内网环境需要 HTTP/HTTPS proxy 或自签 CA。

常见配置：

```bash
export HTTPS_PROXY="http://proxy.intra.example.com:8080"
export HTTP_PROXY="http://proxy.intra.example.com:8080"
export NO_PROXY="localhost,127.0.0.1,.intra.example.com"
```

如果网关使用企业自签证书，建议把 CA 安装到系统信任链，而不是让用户到处关 TLS 校验。

错误做法：

```bash
export NODE_TLS_REJECT_UNAUTHORIZED=0
```

不建议这样做。它会扩大中间人风险。

正确做法：

1. 内网 CA 纳入系统信任。
2. 网关证书按域名签发。
3. 开发机使用 HTTPS 访问网关。
4. 定期轮换证书。

## 十二、升级和回滚

内网部署最容易忽略升级策略。

Claude Code 官方安装方式可能会自动更新；但内网离线部署通常要禁用自动升级，由平台团队统一发版。

推荐策略：

1. 每月或每两周评估新版本。
2. 先在测试项目验证。
3. 固定版本号和 checksum。
4. 灰度给小组使用。
5. 收集问题。
6. 全量推广。
7. 保留上一个稳定版本。

目录：

```text
/opt/claude-code/
  versions/
    2.1.91/
    2.1.95/
  current -> versions/2.1.95
```

回滚：

```bash
ln -sfn /opt/claude-code/versions/2.1.91 /opt/claude-code/current
```

开发机不要各自升级，否则问题很难定位。

## 十三、验收清单

部署完成后，用下面清单验收。

| 项目 | 验收方法 |
| --- | --- |
| CLI 安装 | `claude --version` |
| PATH 配置 | `which claude` |
| 网关连通 | `curl https://llm-gateway.intra.example.com/health` |
| 模型调用 | `claude -p "用一句话介绍这个仓库"` |
| 鉴权 | 无 token 时应失败 |
| 审计 | 网关能看到用户和项目记录 |
| 限流 | 超并发时返回明确错误 |
| 权限 | 文件修改会请求确认 |
| 回滚 | 切换 symlink 后版本变化 |
| 离线安装 | 无公网环境可安装 |

非交互测试：

```bash
claude -p "列出这个项目的主要目录，并说明每个目录的用途"
```

如果使用本地模型，再加三类测试：

1. 单文件解释。
2. 单文件修改。
3. 多文件测试生成。

不要只测 hello world。

## 十四、常见问题

### 1. 设置了 `ANTHROPIC_BASE_URL` 但还是走官方？

检查是否有 shell、settings、启动脚本互相覆盖：

```bash
env | grep ANTHROPIC
```

再进 Claude Code 里看 `/status`。

### 2. 为什么提示登录？

如果你走网关或本地模型，通常要提供 `ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_API_KEY` 或 `apiKeyHelper`。否则 Claude Code 会尝试默认登录流程。

### 3. 本地模型能不能完全替代 Claude？

不能简单等价。Claude Code 是 agent 工作流，本地模型需要具备足够强的代码理解、工具调用、长上下文和补丁生成能力。小模型适合简单任务，不适合所有复杂工程任务。

### 4. 能不能把真实 Anthropic API Key 发给每个人？

不建议。更合理的是开发机拿内网 token，网关持有上游凭证。

### 5. 需要保存完整 prompt 做审计吗？

默认不建议长期保存完整 prompt。可以保存摘要、token 用量、模型、时间、项目、用户。完整内容如需留存，应有明确合规依据、访问控制和保留周期。

## 十五、推荐落地方案

如果是企业内网，我建议分三阶段落地。

### 阶段一：离线安装包

目标：

1. 所有开发机能安装同一版本 Claude Code。
2. 无需每台机器访问公网。
3. 支持 checksum 校验和版本回滚。

产物：

```text
claude-code-offline-2.1.91.tar.gz
manifest.json
install.sh
```

### 阶段二：统一 LLM 网关

目标：

1. 开发机只访问内网网关。
2. 网关统一鉴权、审计、限流。
3. 上游可以先接 Anthropic 或云厂商托管 Claude。

配置：

```bash
export ANTHROPIC_BASE_URL="https://llm-gateway.intra.example.com"
export ANTHROPIC_AUTH_TOKEN="user-or-machine-token"
```

### 阶段三：本地模型试点

目标：

1. 在少数低风险项目上验证本地模型。
2. 对比云端 Claude 和本地 coder 模型。
3. 记录任务成功率、修改准确率、耗时、人工返工率。

不要一上来全员切本地模型。先做可量化评估。

## 十六、总结

内网部署 Claude Code 的关键，不是找到一个神奇脚本，而是把架构拆清楚。

| 问题 | 解决方案 |
| --- | --- |
| 内网怎么安装 | 离线包 + checksum + 公共目录 |
| 请求发到哪里 | `ANTHROPIC_BASE_URL` 指向网关 |
| 如何鉴权 | `ANTHROPIC_AUTH_TOKEN` 或 `apiKeyHelper` |
| 如何避免泄露上游 key | 网关持有上游凭证 |
| 如何审计 | 网关记录用户、项目、模型、用量 |
| 如何完全离线 | 本地模型 + Anthropic API 兼容层 |
| 如何保证质量 | 小范围试点 + 任务评测 |
| 如何运维 | 固定版本、灰度、回滚 |

最推荐的企业方案是：

```text
Claude Code 离线安装包
  + 内网 LLM Gateway
  + 统一鉴权审计
  + 受控云模型或私有模型后端
  + 版本化升级和回滚
```

完全离线本地模型可以做，但要把能力边界讲清楚。它适合安全敏感、低风险、可人工复核的任务；对于复杂跨文件工程任务，云端 Claude 或更强的私有模型仍然更稳。

参考：

1. [Claude Code 官方 GitHub 仓库](https://github.com/anthropics/claude-code)
2. [Claude Code Quickstart](https://code.claude.com/docs/en/quickstart)
3. [Claude Code Environment Variables](https://code.claude.com/docs/en/env-vars)
4. [Claude Code Authentication / Credential Management](https://code.claude.com/docs/en/team)
5. [Claude Help Center: Manage API key environment variables](https://support.claude.com/en/articles/12304248-manage-api-key-environment-variables-in-claude-code)
