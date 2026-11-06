---
title: 【模型自进化】ARIS：用跨模型对抗协作让科研 Agent 变得可审计
tags:
  - 模型自进化
  - ARIS
  - Agent
  - AI for Science
  - Research Automation
---

> ARIS，全称 **Autonomous Research via Adversarial Multi-Agent Collaboration**，也叫 Auto-Research-In-Sleep。它不是一个单纯的“自动写论文 Agent”，而是一套面向机器学习科研的 research harness：用 Markdown 技能、跨模型审查、研究 Wiki、证据到声明审计和 meta-optimize 闭环，把长周期科研任务拆成可执行、可恢复、可审计、可迭代的工作流。

![ARIS three-layer research harness architecture](/assets/images/model-self-evolution-aris/architecture.svg)

<!--more-->

## 一、项目和论文基本信息

| 项目 | 信息 |
| --- | --- |
| 论文题目 | ARIS: Autonomous Research via Adversarial Multi-Agent Collaboration |
| 项目名称 | ARIS / Auto-Research-In-Sleep |
| arXiv 编号 | arXiv:2605.03042 |
| DOI | 10.48550/arXiv.2605.03042 |
| 首次提交 | 2026 年 5 月 4 日 |
| 论文类型 | Technical report |
| 研究方向 | Software Engineering、Artificial Intelligence、自主科研 Agent |
| 项目仓库 | https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep |
| 项目介绍页 | https://wanshuiyin.github.io/Auto-claude-code-research-in-sleep/ARIS_INTRO.html |
| 开源许可证 | MIT |

论文作者和单位如下。

| 作者 | 单位 |
| --- | --- |
| Ruofeng Yang | Shanghai Jiao Tong University |
| Yongcan Li | Shanghai Innovation Institute |
| Shuai Li | Shanghai Jiao Tong University |

ARIS 的一句话定位是：**让一个执行模型推进科研工作，让另一个不同模型家族的 reviewer 持续挑错、打分、要求修复，并用可追溯的 artifact contracts 保存研究过程。**

## 二、为什么 ARIS 值得放进“模型自进化”系列

ARIS 的“自进化”不是模型参数自训练。它没有声称让大模型自己更新权重，也没有把模型生成内容直接递归喂回训练集。

它更接近一种系统级自进化：

| 自进化层级 | ARIS 是否涉及 | 说明 |
| --- | --- | --- |
| 模型参数自进化 | 否 | 不更新 LLM 权重 |
| 工作流自改进 | 是 | `/meta-optimize` 根据使用日志提出 skill 改进 |
| 研究记忆自积累 | 是 | Research Wiki 保存论文、想法、失败实验和 claim 状态 |
| 审查标准自强化 | 是 | reviewer 反馈会变成下一轮修复、实验和写作约束 |
| 证据链自完善 | 是 | claim ledger、result-to-claim、paper-claim-audit 把结果和声明绑定 |
| 跨模型纠错 | 是 | executor 与 reviewer 采用不同模型家族，降低同模型自审盲区 |

这很重要。很多“Agent 自进化”讨论容易直接跳到 RL、self-play、recursive self-training，但工程上更先落地的路线可能是：**先让 Agent 的流程、记忆、审查、证据链和工具库持续变好。**

ARIS 正是这条路线。

## 三、ARIS 要解决的核心问题：长期任务里的“看起来成功”

论文里有一个很关键的判断：长周期研究 Agent 的中心风险不是明显崩溃，而是 **plausible unsupported success**。

也就是：

```text
论文看起来写完了；
实验看起来跑过了；
图表看起来合理；
结论看起来有贡献；
但证据链其实不完整，结果被误报，claim 超出了实验支持范围。
```

这比直接失败更危险。直接失败容易发现；“看起来成功”会让后续读者、审稿人甚至作者自己继承错误叙事。

ARIS 的基本假设很严格：

> 任何由单个 Agent 完成的长周期任务默认不可靠。

所以它不把“让同一个模型反思一下”当成充分审查，而是默认使用跨模型对抗协作：

| 角色 | 职责 |
| --- | --- |
| Executor | 负责推进工作：读文献、写代码、跑实验、改论文 |
| Reviewer | 使用不同模型家族，从外部视角审查、打分、质疑、要求修复 |

这和普通 self-refinement 的差别在于：reviewer 不只是继续 executor 的思路，而是尽量从不同归纳偏置、不同上下文策略、不同审查角色出发寻找问题。

## 四、三层架构：Execution、Orchestration、Assurance

ARIS 把系统拆成三层。

| 层级 | 作用 | 关键组件 |
| --- | --- | --- |
| Execution Layer | 执行具体研究动作 | 65+ Markdown-defined skills、MCP 模型集成、Research Wiki、deterministic figure generation |
| Orchestration Layer | 把技能串成端到端科研流程 | idea discovery、experiment bridge、auto-review、paper writing、rebuttal 等 workflow |
| Assurance Layer | 检查研究结果是否可信 | evidence-to-claim audit、five-pass editing、proof check、citation audit、visual PDF review |

这种拆法很工程化。它没有把所有能力塞进一个巨大的 Agent prompt，而是把科研过程拆成可复用技能，再通过 artifact contracts 串起来。

### 1. Execution Layer：技能是最小执行单元

ARIS 的技能是 Markdown 文件。每个 skill 本质上是一个可读、可改、可迁移的过程说明。

这有几个好处：

| 设计 | 好处 |
| --- | --- |
| Markdown-only | 人可以直接审查，模型也容易读取 |
| 无框架锁定 | 可迁移到 Claude Code、Codex CLI、Cursor、OpenClaw 等环境 |
| 技能可组合 | 一个复杂工作流可以由多个简单技能串联 |
| 技能可版本化 | Git 能追踪技能变化 |
| 技能可被 meta-optimize | 使用日志能反过来推动技能改造 |

我觉得这是 ARIS 最务实的部分。相比“做一个巨大 agent framework”，把研究操作拆成一堆 `SKILL.md`，反而更贴近真实科研流程。

### 2. Orchestration Layer：科研生命周期不是一条 prompt

ARIS 把端到端科研拆成多个 workflow。

![ARIS research lifecycle workflow](/assets/images/model-self-evolution-aris/workflow.svg)

| Workflow | 作用 | 典型输出 |
| --- | --- | --- |
| W1 Idea Discovery | 文献调研、想法生成、novelty check、实验计划 | `IDEA_REPORT.md` |
| W1.5 Experiment Bridge | 把实验计划转成代码、部署、监控、收集结果 | 实验代码、`EXPERIMENT_LOG.md` |
| W2 Auto Review Loop | 跨模型审查、打分、修复、再审 | reviewer 报告、修复记录 |
| W3 Paper Writing | 从 narrative report 写成论文，编译 PDF，做 claim audit | paper draft、PDF、审计报告 |
| W4 Rebuttal | 解析审稿意见，写 rebuttal，做压力测试 | rebuttal draft |
| W5 Resubmit | 把已有论文迁移到新 venue | resubmission package |
| W6 Paper Talk | 从论文生成报告、PPT、演讲稿和审查材料 | talk materials |

这种设计的关键是“中间产物明确”。不是让 Agent 在上下文里隐式记住所有东西，而是每一步都落到文件、日志、报告或 wiki 中。

### 3. Assurance Layer：把可信度当成一等公民

ARIS 最有价值的地方不是自动化，而是 assurance stack。

论文中提到一个三阶段 evidence-to-claim audit cascade：

| 阶段 | 目标 |
| --- | --- |
| Stage 1：Experiment-integrity audit | 检查实验是否真实运行、日志是否完整、结果是否可信 |
| Stage 2：Result-to-claim mapping | 把实验结果映射到可支持的论文 claim |
| Stage 3：Paper-claim audit | 检查论文中的声明是否超出 claim ledger 和原始证据 |

这比“请 reviewer 看看论文有没有问题”强很多。它把研究可信度拆成：

```text
实验是否可信 -> 结果支持哪些声明 -> 论文有没有越界表达
```

这也是 AI 科研系统真正难的地方。自动写作不稀奇，自动保持证据链才难。

## 五、跨模型对抗协作：为什么不是同一个模型自审

很多 Agent 系统的默认做法是：

```text
模型生成答案 -> 同一个模型反思 -> 同一个模型修改
```

这当然有用，但容易有同源盲区。模型会倾向于继续自己已经建立的叙事，遗漏同一类错误。

ARIS 推荐：

```text
Executor model 负责推进
Reviewer model 使用不同模型家族负责质疑
```

比如仓库说明中提到，Claude Code 可以作为快速执行者，Codex / GPT 系列通过 MCP 作为更严格的审查者。项目也强调不强绑定 Claude 或 OpenAI，可以使用其他模型组合。

这种异质模型审查有几个价值：

| 价值 | 说明 |
| --- | --- |
| 降低相关错误 | 不同模型家族更可能发现不同类型问题 |
| 形成外部压力 | reviewer 不只是顺着 executor 的上下文继续写 |
| 支持质量门禁 | reviewer 可以要求补实验、改表述、修证据链 |
| 让审查可记录 | reviewer 输出被保存，下一轮修复可以对照 |

从“模型自进化”的角度看，ARIS 的自进化不是模型自我欣赏，而是让模型暴露在一个持续挑错的制度环境里。

## 六、Research Wiki：把失败也变成记忆

Research Wiki 是 ARIS 的长期记忆层。它保存：

| 内容 | 价值 |
| --- | --- |
| 读过的论文 | 后续 idea discovery 不从零开始 |
| 生成过的想法 | 避免重复生成旧想法 |
| 失败实验 | 作为 anti-repetition memory |
| 实验结果 | 支持后续 claim mapping |
| claim 状态 | 记录哪些结论被证据支持 |
| 项目决策 | 让长周期任务可以恢复 |

这个设计很重要。很多 Agent 项目看起来有 memory，但只是在向量库里塞聊天记录。ARIS 的 memory 更接近研究项目的状态数据库：它记录的不只是信息，还有失败、判断、证据和声明。

如果一个系统能记住“哪些路走不通”，它就已经具备了某种经验积累能力。

## 七、Meta-Optimization：工作流也可以被优化

ARIS 里最贴近“自进化”的组件是 `/meta-optimize`。

它的思路是：

```text
记录使用日志 -> 分析失败模式和摩擦点 -> 提出 skill 改进 -> reviewer 审查 -> 人类批准后合并
```

这和直接让 Agent 自动改自己不同。ARIS 更谨慎：自改进建议需要 reviewer approval，而不是无条件自我修改。

可以把它理解成一种受控的 harness evolution。

| 普通 Agent 改进 | ARIS 式改进 |
| --- | --- |
| 改 prompt | 改技能文件、工作流、检查点 |
| 凭经验修 | 基于 usage logs 和失败 trace |
| 同模型自评 | 跨模型 reviewer 审查 |
| 直接生效 | 需要批准后采用 |
| 难以追踪 | Git 和 artifact 记录可追溯 |

这比“Agent 自己改自己”听起来保守，但实际更可落地。工程系统要能长期使用，自进化必须可控。

## 八、和 SAGA 的区别：一个演化目标，一个演化流程

上一篇“模型自进化”里写到 SAGA。SAGA 和 ARIS 都可以放在“模型自进化”谱系中，但它们演化的对象不同。

| 项目 | 演化对象 | 核心闭环 |
| --- | --- | --- |
| SAGA | 科学目标和评分函数 | 分析结果 -> 修改 objective -> 重新优化候选解 |
| ARIS | 科研流程和证据保障机制 | 执行研究 -> 跨模型审查 -> 修复 -> 沉淀记忆 -> 改进技能 |

SAGA 更像“目标函数自演化的科学发现 Agent”；ARIS 更像“科研工作流自进化的 Agent harness”。

两者放在一起看，可以得到一个更完整的图景：

```text
SAGA：研究该优化什么
ARIS：研究过程如何可信地跑下去
```

未来真正强的 AI Scientist 可能需要二者结合：既能演化科学目标，也能维护证据链、审查链和流程记忆。

## 九、ARIS 对 AI Infra 的启发

ARIS 看起来是科研项目，但它对 AI Infra 很有参考价值。

| ARIS 设计 | AI Infra 启发 |
| --- | --- |
| Markdown skills | 用可读的程序化模板表达 agent capability |
| Artifact contracts | 用文件/结构化产物连接长流程 |
| Cross-model review | 用异质模型做质量门禁 |
| Claim ledger | 把模型输出和证据绑定 |
| Research Wiki | 项目级持久记忆，而不是临时上下文 |
| Meta-optimize | 基于 trace 改进工具链 |
| Effort levels | 根据任务风险和预算调节审查强度 |
| Reviewer routing | 不同任务路由到不同 reviewer |

如果迁移到企业 Agent 系统，可以对应为：

```text
业务 Agent -> 生成方案 -> reviewer 模型质检 -> 证据链审计 -> 人类批准 -> 写入知识库 -> 复用到下一次任务
```

这比“Agent 直接给答案”更适合高风险场景，比如医疗、法律、金融、科研、工程运维。

## 十、局限性和风险

ARIS 很有启发，但不能过度神化。

| 局限 | 说明 |
| --- | --- |
| 不保证正确性 | 跨模型审查降低风险，但不能证明结果一定正确 |
| reviewer 也会偏 | 不同模型家族仍可能共享错误知识或评价偏差 |
| 自动实验成本高 | GPU、数据、环境和复现实验仍然复杂 |
| 人类责任不能移除 | 论文也强调 human-in-the-loop 对质量和研究品味很重要 |
| 安全问题现实存在 | Agent 能写代码、跑实验、访问文件和网络，必须限制权限 |
| 证据审计有边界 | 审计链依赖日志、原始结果和工具可靠性 |
| 容易变成流程膨胀 | 技能多、审查多，也会带来维护成本 |

我尤其关注两个风险。

第一，**reviewer bias amplification**。如果 reviewer 偏好某种写作风格或评价标准，系统可能向这种风格收敛，而不一定向真实科学质量收敛。

第二，**self-referential disclosure**。当系统参与论文生产，应该披露自动化系统在研究、写作、实验、审查中的角色，否则读者无法判断责任边界。

## 十一、如果要借鉴 ARIS，可以怎么做

不一定要完整复制 ARIS。可以先借鉴它的几个关键设计。

### 1. 给自己的 Agent 项目加 cross-model review

最小版本：

```text
executor 生成结果
reviewer 使用不同模型检查
executor 根据 reviewer action items 修复
保存 reviewer 原文和修复记录
```

### 2. 给长任务加 artifact contracts

不要让长流程只存在于上下文里。每一步都输出明确文件：

```text
PLAN.md
EXPERIMENT_LOG.md
RESULTS.md
CLAIMS.md
REVIEW.md
FINAL_REPORT.md
```

### 3. 建一个 claim ledger

每个结论都绑定证据：

```yaml
claim_id: c001
claim: "方法 A 在数据集 X 上优于 baseline B"
evidence:
  - runs/exp_20260814/metrics.json
  - tables/main_results.csv
status: supported
limitations:
  - "仅在三个随机种子上验证"
```

### 4. 用 usage logs 改进 workflow

记录失败位置：

| 失败类型 | 可能改进 |
| --- | --- |
| reviewer 总是要求补实验 | experiment plan skill 太弱 |
| citation 经常错 | citation audit 需要加强 |
| claim 经常越界 | 写作 prompt 要约束证据边界 |
| 任务经常中断 | workflow state 和 resume 机制不够 |

这就是 ARIS 的 meta-optimize 思路。

## 十二、总结

ARIS 的核心价值不是“睡一觉醒来论文自动写好了”这个宣传口号，而是它把自主科研 Agent 里最难、最容易被忽略的部分工程化了：

1. 长周期任务默认不可靠，所以需要跨模型审查。
2. 科研结果不能只看最终论文，而要看证据链。
3. Agent 的记忆不能只是聊天记录，而要保存论文、想法、失败实验和 claim 状态。
4. 工作流不能藏在 prompt 里，而要拆成可读、可组合、可版本化的技能。
5. 自进化不能无约束自改，而要基于 trace 提出改进，并经过 reviewer 和人类批准。

所以，ARIS 代表的是一种很务实的模型自进化路线：不是让模型自己训练自己，而是让模型所在的 harness 持续积累记忆、强化审查、改进技能、沉淀证据。对科研 Agent、企业 Agent 和 AI Infra 来说，这条路线都比单纯追求“更长上下文、更强模型”更接近真实系统演进。

## 参考资料

- arXiv 论文页面：https://arxiv.org/abs/2605.03042
- arXiv HTML 版本：https://arxiv.org/html/2605.03042
- ARIS GitHub 仓库：https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep
- ARIS 项目介绍页：https://wanshuiyin.github.io/Auto-claude-code-research-in-sleep/ARIS_INTRO.html
