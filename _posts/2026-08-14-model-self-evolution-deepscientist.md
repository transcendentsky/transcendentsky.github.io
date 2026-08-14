---
title: 【模型自进化】DeepScientist：用 Findings Memory 推动前沿科学发现
tags:
  - 模型自进化
  - DeepScientist
  - AI for Science
  - Agent
  - Research Automation
---

> 原论文题目：**DeepScientist: Advancing Frontier-Pushing Scientific Findings Progressively**。DeepScientist 关注的不是“一次性生成一个看起来像论文的结果”，而是让 AI 在长周期研究中持续提出假设、验证假设、分析结果，并把每一轮发现沉淀到 Findings Memory 里，成为下一轮探索的起点。它把科学发现形式化为 Bayesian Optimization 问题，试图让 AI 从局部最优逐步走向更有价值的前沿发现。

![DeepScientist closed-loop discovery architecture](/assets/images/model-self-evolution-deepscientist/closed-loop.svg)

<!--more-->

## 一、论文和项目信息

| 项目 | 信息 |
| --- | --- |
| 论文题目 | DeepScientist: Advancing Frontier-Pushing Scientific Findings Progressively |
| arXiv 编号 | arXiv:2509.26603 |
| DOI | 10.48550/arXiv.2509.26603 |
| 首次提交 | 2025 年 9 月 30 日 |
| 研究方向 | AI for Science、Autonomous Scientific Discovery、LLM Agent、Bayesian Optimization |
| 论文链接 | https://arxiv.org/abs/2509.26603 |
| OpenReview | https://openreview.net/forum?id=cZFgsLq8Gs |
| 项目仓库 | https://github.com/ResearAI/DeepScientist |
| 项目官网 | https://deepscientist.cc/ |
| 开源许可证 | Apache-2.0 |

论文作者如下。

| 作者 |
| --- |
| Yixuan Weng |
| Minjun Zhu |
| Qiujie Xie |
| Qiyao Sun |
| Zhen Lin |
| Sifan Liu |
| Yue Zhang |

GitHub README 中给出的 BibTeX 显示，该工作被列为 ICLR 2026 论文；arXiv 页面当前显示 v1，提交时间为 2025 年 9 月 30 日。由于 OpenReview 页面当前需要浏览器校验，本文主要依据 arXiv、项目 README 和官网公开信息整理。

## 二、DeepScientist 想解决什么问题

前面几篇“模型自进化”文章里已经提到，AI Scientist 类系统有几个常见瓶颈：

| 问题 | 表现 |
| --- | --- |
| 一次性探索 | Agent 生成一些想法后就结束，下一轮不能继承经验 |
| 目标不聚焦 | 想法很多，但未必指向人类真正关心的前沿挑战 |
| 实验不连续 | baseline、消融、失败路径和结果分析散落在文件和终端里 |
| 缺少探索策略 | 不知道什么时候 exploit 当前强方向，什么时候 explore 新方向 |
| 状态不可持久 | 上下文消失后，研究过程难以复盘和继续 |

DeepScientist 的目标是解决“长周期科学发现如何持续推进”的问题。

它不是只问：

```text
AI 能不能生成一个新想法？
```

而是问：

```text
AI 能不能在一个月级别的时间线上持续探索、验证、分析，并逐步推进到超过人类 SOTA 的发现？
```

这也是它和普通 research chatbot 的区别。DeepScientist 不是总结论文、给几个 idea，然后把执行留给人类；它把 literature、baseline、experiment rounds、findings、figures、paper-ready outputs 放到一个连续工作空间里。

## 三、核心思想：把科学发现形式化为 Bayesian Optimization

论文摘要里最关键的一句话是：DeepScientist 将 discovery formalize 为 Bayesian Optimization problem。

可以把它理解成：

```text
研究方法空间：I
真实科学价值函数：f(I)
每次完整研究循环：一次昂贵的 f(I) 评估
目标：在有限实验预算下找到更高价值的 I
```

这和传统 Bayesian Optimization 的相似点是：

| BO 概念 | DeepScientist 中的对应 |
| --- | --- |
| 搜索空间 | 候选研究想法、模型方法、实验配置 |
| 黑盒函数 | 一个研究想法真正带来的科学价值 |
| 代理模型 | LLM Reviewer / utility estimator |
| acquisition function | 平衡探索和利用的选择策略 |
| expensive evaluation | 实现、训练、评测、分析一轮完整实验 |
| observation history | Findings Memory |

这比“让 Agent 随机想点新方法”更严肃。因为科学发现的核心问题不是 idea 数量，而是在有限计算和时间预算下选择最值得验证的方向。

## 四、三阶段闭环：Hypothesize、Verify、Analyze

DeepScientist 的发现循环可以概括为三步。

| 阶段 | 目标 | 关键问题 |
| --- | --- | --- |
| Hypothesize | 生成候选研究假设和方法 | 哪些方向既新颖又有潜在价值？ |
| Verify | 实现并验证候选方法 | 哪些想法能经受 baseline、实验和消融？ |
| Analyze | 分析结果并沉淀发现 | 结果说明了什么，失败说明了什么？ |

这三步不断循环：

```text
Hypothesize -> Verify -> Analyze -> Findings Memory -> 下一轮 Hypothesize
```

我认为 DeepScientist 的关键不在某一个单点模块，而在于它把“分析结果”变成了下一轮研究的输入，而不是把它只当成论文写作材料。

## 五、Findings Memory：自进化的核心存储层

Findings Memory 是 DeepScientist 里最贴近“模型自进化”的设计。

普通 Agent 的 memory 很多时候只是：

```text
保存对话历史
保存用户偏好
保存检索文档
```

DeepScientist 的 Findings Memory 更像研究状态数据库，保存的是：

| 内容 | 价值 |
| --- | --- |
| 成功发现 | 后续可以围绕强方向继续 exploit |
| 失败路径 | 避免重复尝试低价值方向 |
| 实验结果 | 支持下一轮方法选择 |
| baseline 复现经验 | 降低后续实验启动成本 |
| 消融结论 | 判断哪个组件真正有用 |
| 研究假设之间的关系 | 帮助系统建立 Research Map |
| 写作和图表材料 | 让 paper-ready output 不和实验脱节 |

从自进化角度看，Findings Memory 的意义是：**系统不会每一轮从零开始，而是带着自己的研究经验继续搜索。**

这和参数自训练不同。它不是更新模型权重，而是更新系统的“科学状态”和“搜索先验”。

## 六、Research Map：从局部最优走向全局洞察

官网把 DeepScientist 的探索路径描述为从 Local Optimum 到 Global Optimum，中间经过 Learn & Adapt 和 Escape Local。

这个叙事背后对应一个实际问题：科学研究很容易陷入局部最优。

例如：

1. 当前 baseline 上小改动能带来一点提升。
2. Agent 继续围绕这个方向做局部变体。
3. 指标略有提升，但没有真正突破。
4. 系统需要识别 plateau，并引入更远的新假设。

Research Map 的价值在于把研究状态可视化、结构化：

| 状态 | 系统应该做什么 |
| --- | --- |
| baseline 未复现 | 先修复环境和实验可信度 |
| 有小幅稳定提升 | 继续 refine 和 ablation |
| 连续多轮 plateau | 增加探索半径，尝试新机制 |
| 发现强信号 | 提高验证保真度，加更多实验 |
| 发现失败模式 | 写入 Findings Memory，避免重复 |

这就是 DeepScientist 的“progressively”含义：不是一次跳到最优，而是随着证据积累逐步推进研究边界。

## 七、论文中的大规模实验结果

arXiv 摘要给出的结果非常激进，也最值得讨论。

| 指标 | 论文摘要信息 |
| --- | --- |
| 计算量 | 超过 20,000 GPU hours |
| 生成想法 | 约 5,000 个 unique scientific ideas |
| 实验验证 | 约 1,100 个想法经过实验验证 |
| 任务结果 | 在三个 frontier AI tasks 上超过人类设计 SOTA |
| 提升幅度 | 183.7%、1.9%、7.9% |

这些数字说明 DeepScientist 不是小规模 toy demo，而是一次大规模自动研究运行。

但也要谨慎理解。

| 需要追问的问题 | 原因 |
| --- | --- |
| 三个 frontier AI tasks 具体是什么 | 不同任务的难度和 benchmark 饱和程度差异很大 |
| SOTA 基线是否公平 | 自动系统能否真正超越强人类调参，需要严格复现 |
| GPU hours 如何分配 | 大规模搜索本身也可能带来 brute-force 优势 |
| 1.9% 和 7.9% 是否统计显著 | 小幅提升要看 variance、seed 和置信区间 |
| 失败 idea 如何统计 | 只看最终成功会高估系统效率 |

我的判断是：DeepScientist 最重要的贡献不是单个提升数字，而是把“AI 科学发现”从小样本演示推向了大规模闭环实验。

## 八、DeepScientist 项目形态：Local-first Research Studio

项目仓库 README 对工程形态说得很清楚：DeepScientist 是 local-first autonomous research studio。

几个关键词很重要：

| 特性 | 含义 |
| --- | --- |
| 15-minute local setup | 希望研究者能快速在本机或服务器启动 |
| One repo per quest | 每个研究任务有独立仓库状态 |
| Visible research progress | 过程可见，而不是黑盒自动跑 |
| Human takeover anytime | 人可以随时暂停、接管、修改计划、继续 |
| Built-in runners | 支持 Codex、Claude Code、Kimi Code、OpenCode |
| Web workspace / TUI | 支持浏览器工作区和终端 UI |

这和纯论文系统不同。它更像一个研究工作台：

```text
project files + terminal + agent runner + memory + artifacts + web workspace
```

我很认同这个方向。长周期科研 Agent 如果不能让人类随时看见、接管、修正，就不适合真实研究。

## 九、和 SAGA、ARIS、AutoResearchClaw 的区别

![Self-evolving AI scientist systems comparison](/assets/images/model-self-evolution-deepscientist/comparison.svg)

| 项目 | 自进化对象 | 核心闭环 |
| --- | --- | --- |
| SAGA | 科学目标和评分函数 | 分析失败模式 -> 修改 objective -> 重新优化候选 |
| ARIS | 科研流程和证据审计 harness | 执行 -> 跨模型审查 -> 证据链修复 |
| AutoResearchClaw | 端到端科研流水线和跨运行 lesson | debate -> execution -> verification -> future runs |
| DeepScientist | Findings Memory 和研究搜索策略 | hypothesize -> verify -> analyze -> BO selection |

DeepScientist 的不同点在于，它特别强调：

1. 目标导向，而不是开放式随机探索。
2. 大规模实验验证，而不是只生成想法。
3. Findings Memory，而不是单轮上下文。
4. Bayesian Optimization，用 acquisition strategy 选择下一个研究方向。
5. Local-first workspace，把长期研究过程做成可持续使用的产品形态。

如果说 SAGA 问的是“科学目标如何演化”，ARIS 问的是“研究过程如何可信”，AutoResearchClaw 问的是“端到端科研管线如何自增强”，DeepScientist 问的是：

```text
AI 如何在长周期中持续积累发现，并选择最值得投入实验预算的下一步？
```

## 十、为什么它属于“模型自进化”

DeepScientist 并不是参数级自进化。它不等于：

```text
模型生成数据 -> 训练自己 -> 权重更新
```

它更像系统级自进化：

| 自进化层级 | DeepScientist 是否涉及 | 说明 |
| --- | --- | --- |
| 参数自训练 | 不是重点 | 论文重点不是更新 foundation model 权重 |
| 研究记忆演化 | 是 | Findings Memory 累积实验和发现 |
| 搜索策略演化 | 是 | BO 框架根据历史结果选择下一步 |
| 实验保真度演化 | 是 | 有价值方向被推进到更高验证层级 |
| 工作空间状态演化 | 是 | 文件、分支、artifacts、论文草稿持续积累 |
| 人机协作策略 | 是 | 支持 visible progress 和 human takeover |

这里的“模型自进化”更准确说是“Agent 系统自进化”：模型作为推理组件，嵌入一个会积累经验、调整搜索、推进验证的系统里。

## 十一、对 AI Infra 的启发

DeepScientist 对 AI Infra 很有参考价值。

### 1. 长周期 Agent 需要 durable state

聊天上下文不是状态。真实科研状态应该落到：

```text
repo
branch
artifact
metric
finding
decision
paper draft
experiment log
```

DeepScientist 的 one repo per quest 就是这个思路。

### 2. Agent 需要 research-grade observability

科研 Agent 不是只看最终答案。需要看到：

| 观测对象 | 价值 |
| --- | --- |
| 每轮假设 | 判断探索是否发散或重复 |
| 实验配置 | 保证可复现 |
| 指标变化 | 判断是否真的改进 |
| 失败路径 | 避免重复踩坑 |
| Findings Memory 更新 | 解释下一轮为什么这样选 |
| 人类接管记录 | 明确责任边界 |

### 3. 需要任务级资源调度

论文提到的 20,000+ GPU hours 说明，真正的 autonomous research 不是轻量 chat workflow。它需要：

| Infra 能力 | 说明 |
| --- | --- |
| 任务队列 | 管理大量实验 |
| GPU 调度 | 控制训练和验证资源 |
| checkpoint | 长任务中断恢复 |
| experiment tracking | 记录参数、指标、日志 |
| artifact store | 保存模型、图表、结果和论文材料 |
| cost control | 避免无边界探索 |

如果把 DeepScientist 做成生产系统，Ray、MLflow、W&B、Prometheus、对象存储、Git worktree、容器沙箱都会变得很重要。

## 十二、局限性和风险

DeepScientist 很有野心，但也需要冷静看。

| 风险 | 说明 |
| --- | --- |
| 大规模计算成本 | 20,000+ GPU hours 不是普通个人或小团队能轻松复现的规模 |
| 任务选择影响结论 | 三个 frontier tasks 的性质会极大影响“超越 SOTA”的含义 |
| BO 代理评价可能偏 | LLM Reviewer 估计 utility 时可能偏向熟悉模式 |
| 局部最优仍可能存在 | Research Map 能帮助识别，但不能保证全局最优 |
| 实验工程复杂 | baseline repo、依赖、数据、训练随机性都会影响结果 |
| 写作和 claim 仍需审计 | 生成 paper-ready outputs 不等于科学结论自动可信 |
| 人类责任不能移除 | README 中也建议披露 DeepScientist 参与工作流，人类仍对最终判断负责 |

尤其需要注意：**可持续发现系统越强，越需要可审计性。** 如果系统持续积累 Findings Memory，但 memory 里混入了错误实验、错误解释或偏置评价，后续探索会被系统性带偏。

所以 DeepScientist 需要和 ARIS/AutoResearchClaw 那类 evidence audit、citation verification、cross-model review 结合，才能更适合高风险科研。

## 十三、如果要借鉴 DeepScientist，可以怎么做

不一定要复刻完整系统。可以从四个设计开始。

### 1. 给每个研究任务建独立 repo

```text
quest-001/
  papers/
  baselines/
  experiments/
  findings/
  figures/
  drafts/
  logs/
```

### 2. 建一个 Findings Memory

```yaml
finding_id: f001
hypothesis: "Sparse routing improves long-context retrieval efficiency"
status: supported
evidence:
  - experiments/run_012/metrics.json
  - figures/ablation_latency.svg
limitations:
  - "only tested on one dataset"
next_actions:
  - "verify on multi-hop benchmark"
```

### 3. 用 BO 思路选择下一轮实验

每个候选想法打几个分：

| 分数 | 含义 |
| --- | --- |
| expected_gain | 预期收益 |
| uncertainty | 不确定性 |
| cost | 实验成本 |
| novelty | 与已有 findings 的距离 |
| risk | 失败概率和工程复杂度 |

然后不是选最高预期收益，而是选：

```text
高潜力 + 高不确定性 + 成本可控
```

这就是 exploration 和 exploitation 的平衡。

### 4. 保留 human takeover

自动研究系统必须允许人类随时接管：

| 接管点 | 原因 |
| --- | --- |
| baseline 复现失败 | 人类可能知道环境或数据细节 |
| 多轮 plateau | 需要研究品味判断是否换方向 |
| 强结果出现 | 需要提高验证标准 |
| 论文 claim 形成 | 需要人类判断结论边界 |

全自动不是目标。高质量可持续协作才是目标。

## 十四、总结

DeepScientist 在“模型自进化”系列里的位置很清晰：它不是目标函数演化器，也不是证据审计 harness，而是一个面向长周期科学发现的自推进系统。

它的核心价值可以概括为：

1. 把科学发现形式化为 Bayesian Optimization。
2. 用 Hypothesize、Verify、Analyze 形成闭环。
3. 用 Findings Memory 保存成功、失败、消融和可复用经验。
4. 用 Research Map 帮助系统从局部最优走向更有价值方向。
5. 用 local-first workspace 让长周期研究过程可见、可接管、可持续。

我认为它给“模型自进化”提供了一个非常务实的方向：**不急着让模型权重自己进化，而是先让模型所在的研究系统具备持续记忆、持续验证、持续选择和持续推进的能力。**

真正的 AI Scientist 可能不是一个单体大模型，而是一套会积累发现、管理实验、审计证据、选择方向并允许人类接管的研究操作系统。DeepScientist 正是在朝这个方向走。

## 参考资料

- arXiv 论文页面：https://arxiv.org/abs/2509.26603
- DeepScientist GitHub 仓库：https://github.com/ResearAI/DeepScientist
- DeepScientist 官网：https://deepscientist.cc/
- DeepScientist 文档：https://github.com/ResearAI/DeepScientist/tree/main/docs
- DeepScientist Releases：https://github.com/ResearAI/DeepScientist/releases
