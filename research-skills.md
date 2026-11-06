---
layout: article
title: 研究相关 Skills 清单
permalink: /research-skills/
key: page-research-skills
aside:
  toc: true
---

> 更新时间：2026-07-09（UTC+8）

这个页面整理“辅助科研 / 自主科研”常用的可复用 skill 或内置能力，并优先选了和 **grill-me / deep research** 语义接近的条目。来源是公开文档，便于持续回看更新。

## 一、官方/内置研究能力

### 1. OpenAI Skills
- 作用：把可复用工作流标准化，支持在 ChatGPT（Business/Enterprise/Edu/Teachers/Healthcare）和 Codex 使用。
- 说明：ChatGPT Help Center 提到 Skills 通过 `SKILL.md` 驱动结构化流程。
- 链接：[OpenAI Skills](https://help.openai.com/en/articles/20001066)

### 2. ChatGPT Deep Research
- 作用：用于多源归纳复杂问题；支持起始提示、计划确认、可追溯来源和长时任务。
- 链接：[Deep research in ChatGPT](https://help.openai.com/en/articles/10500283)

### 3. Mistral Vibe Work `deep-research`
- 作用：内置 Skill `/deep-research`，做多源调研并返回结构化报告。
- 链接：[Mistral Skills](https://docs.mistral.ai/vibe/work/skills)

### 4. Google Gemini Deep Research Agent
- 作用：`interactions` 接口提供 `deep-research-preview-04-2026` 与 `deep-research-max-preview-04-2026` 两档深度研究代理。
- 链接：[Gemini Deep Research Skill 说明](https://github.com/google-gemini/gemini-skills/blob/main/skills/gemini-interactions-api/SKILL.md)

## 二、可安装/社区 Skill（偏近似任务执行器）

### 1) grill-me（mattpocock）
- 作用：强制式追问，适合在实施前压测计划/设计，减少反复。
- 安装（示例）：
```bash
npx skills add mattpocock/skills --skill=grill-me -y -g
```
- 链接：[mattpocock/skills - grill-me](https://www.skills.sh/mattpocock/skills/grill-me)
- 说明源页同源： [a2a-mcp grill-me](https://a2a-mcp.org/skill/grill-me)

### 2) research（mattpocock）
- 作用：围绕“只用一手/官方源”做研究并写入 Markdown。
- 安装（示例）：
```bash
npx skills add https://github.com/mattpocock/skills --skill research
```
- 链接：[mattpocock/skills - research](https://www.skills.sh/mattpocock/skills/research)

### 3) deep-research（bytedance/deer-flow）
- 作用：强调“单次搜索不够”，要求宽泛探索 + 多维验证后再综合。
- 安装（Claude Code 示例）：
```bash
npx -y skills add bytedance/deer-flow --skill deep-research --agent claude-code
```
- 链接：
  - [SKILL（raw）](https://raw.githubusercontent.com/bytedance/deer-flow/main/skills/public/deep-research/SKILL.md)
  - [crossai/tools 镜像页](https://crossaitools.com/skills/bytedance/deer-flow/deep-research)

### 4) academic-deep-research（openclaw）
- 作用：学术风格的深度研究，强调双循环验证、证据层级和 APA 引用。
- 链接：[openclaw skill（raw）](https://raw.githubusercontent.com/kesslerio/academic-deep-research-clawhub-skill/main/SKILL.md)

### 5) aiq-research（NVIDIA）
- 作用：NVIDIA AI-Q 蓝图里对应浅/深研究工作流类 skill。
- 安装方式：NVIDIA 官方目录示例为统一入口后按 `--skill` 安装。
- 链接：[NVIDIA skills](https://github.com/NVIDIA/skills)

### 6) deep-research-mcp（仓库 skill）
- 作用：研究型 MCP 套件，仓库自带 `skills/deep-research-mcp/SKILL.md` 指南，偏研究基础设施。
- 链接：[pminervini/deep-research-mcp](https://github.com/pminervini/deep-research-mcp)

## 三、使用建议（按科研流程）

- **先不急着跑大模型研究**：先用 `grill-me` 或你自己的研究提纲，明确问题边界。
- **信息搜集与综述**：选 `deep-research` 类技能或平台能力。
- **论文导向/高严谨场景**：优先 `research`、`academic-deep-research`。
- **团队化/多模型栈**：加 `deep-research-mcp`、NVIDIA 的相关 skill 作为基础设施层。

## 四、说明

上面是“常见且可直接落地”的名单，不代表绝对穷尽。后续我会按月补充来源目录新增项（尤其是 skills.sh / MCP 目录）。
