---
title: 开源 Auto Research / AI Scientist 项目调研：它们如何总结经验并自我改进
tags:
  - AI Scientist
  - Auto Research
  - Agent
  - AI Infra
  - 模型自进化
---

> 过去两年，开源 Auto Research / AI Scientist 项目从“自动生成一篇论文”的演示，逐渐走向更工程化的方向：保存失败、复用经验、跨模型审查、实验可恢复、结果可验证、跨运行学习。本文调研几个有代表性的开源项目，重点不放在“谁最强”，而是看它们如何做经验总结，以及这些机制对我们自己做科研 Agent、AI Infra 和模型自进化系统有什么启发。

![Open source auto research and AI scientist project map](/assets/images/auto-research-experience-summary/project-map.svg)

<!--more-->

## 一、先说结论：经验总结正在成为 Auto Research 的核心能力

早期 AI Scientist 系统主要追求端到端自动化：

```text
idea generation -> experiment -> analysis -> paper writing -> review
```

但现在更有价值的问题变成：

```text
这一轮研究失败或成功之后，系统到底学到了什么？
这些经验能不能进入下一轮？
经验是自由文本，还是结构化 finding？
经验会不会被错误结论污染？
经验如何检索、衰减、审计和复用？
```

我把目前开源项目里的经验总结机制分成五类。

| 类型 | 代表项目 | 经验如何沉淀 |
| --- | --- | --- |
| Review Feedback | AI Scientist v1/v2、Agent Laboratory | 自动 reviewer 给论文或实验反馈，反馈进入修订或后续 idea |
| Search Tree / Journal | AI Scientist v2、AIDE | 保存实验路径、失败节点、debug 记录和最优 solution |
| Findings Memory | DeepScientist | 保存 idea finding、implemented finding、progress finding，失败也保留 |
| Cross-run Lessons | AutoResearchClaw | 从失败、HITL、verification 中抽取 lesson，注入未来运行 |
| External Collective Memory | AgentRxiv | 多个 agent 实验室通过预印本服务器共享研究产出 |

趋势很清楚：**Auto Research 的竞争点，正在从“能不能自动跑一轮”变成“能不能把每一轮变成可复用经验”。**

## 二、项目清单：当前值得关注的开源系统

下面列的是我认为目前最值得关注的一批开源 Auto Research / AI Scientist 项目。

| 项目 | 开源仓库 / 页面 | 主要定位 | 经验总结方式 |
| --- | --- | --- | --- |
| The AI Scientist v1 | `SakanaAI/AI-Scientist` | 端到端自动科学发现，从 idea 到 paper | 自动 review、论文反馈、开放式下一代 idea |
| The AI Scientist v2 | `SakanaAI/AI-Scientist-v2` | 用 agentic tree search 做 workshop-level 自动科研 | BFTS tree、experiment manager、debug path、review |
| Agent Laboratory | `SamuelSchmidgall/AgentLaboratory` | 多角色科研助手，辅助人类完成 research workflow | literature summaries、experiment logs、report revisions |
| AgentRxiv | `AgentRxiv` 项目页 | 面向 autonomous research agents 的预印本服务器 | agent-generated papers 作为外部 collective memory |
| AIDE / AIDE ML | `wecoai/aideml` / `TheSDEs/aideML` | ML engineering / AI R&D 的代码搜索型 agent | solution tree、journal、metric feedback、best code |
| DeepScientist | `ResearAI/DeepScientist` | local-first 长周期科学发现工作台 | Findings Memory、Research Map、BO selection |
| AutoResearchClaw | `aiming-lab/AutoResearchClaw` | 23 阶段自增强科研管线 | lessons、Pivot/Refine、numeric registry、cross-run evolution |
| ARIS | `wanshuiyin/Auto-claude-code-research-in-sleep` | 基于跨模型对抗协作的科研 harness | Research Wiki、claim ledger、cross-model review、meta-optimize |
| SAGA | `btyu/SAGA` | 目标自演化科学发现 Agent | objective evolution、scorer generation、failure analysis |

这份清单不是穷尽式排名。我的筛选标准是：开源、和科研/AI R&D 自动化直接相关、机制上对“经验总结”有可借鉴价值。

## 三、AI Scientist v1/v2：从自动科研流水线到 Agentic Tree Search

Sakana AI 的 AI Scientist 是这个方向绕不开的起点。v1 的基本流程包括 idea generation、literature search、experiment iteration、paper write-up、automated review。官方介绍里明确提到，automated review 不只是评价当前 paper，也可以把反馈用于进一步改进结果，或为未来 open-ended ideation 提供信息。

v1 的经验总结方式比较朴素：

| 产物 | 作用 |
| --- | --- |
| idea JSON | 保存生成的研究想法、假设、实验计划 |
| experiment notes | 保存图表、数值、实验解释 |
| paper draft | 把实验结论组织成论文 |
| automated review | 给出质量评价和修改建议 |
| previous ideas / feedback | 可用于下一代 idea generation |

v2 的关键变化是 agentic tree search。它不再只是线性执行一个 idea，而是在实验空间里扩展多个节点。README 里提到，BFTS 配置包含并行 worker、steps、debug depth、debug probability、initial drafts 等参数，并输出 tree visualization。

这意味着经验从“单次反馈文本”变成了“搜索树状态”。

| 机制 | 经验形态 |
| --- | --- |
| Tree node | 一个候选实验方向或代码状态 |
| Debug path | 某个方向失败后如何修复 |
| Best-first search | 哪些节点值得继续扩展 |
| Tree visualization | 人类可以查看系统怎么探索 |
| Automated reviewer | 对最终 paper 或中间结果给反馈 |

我的判断：AI Scientist v2 的价值不只是生成论文，而是把科研实验变成可以搜索、剪枝、可视化的树。经验总结的粒度因此更细。

## 四、Agent Laboratory 和 AgentRxiv：从单个实验室到集体记忆

Agent Laboratory 把研究过程拆成多个角色：PhD、Postdoc、ML Engineer、Professor 等，并组织成 Literature Review、Experimentation、Report Writing 三个阶段。它强调 assisting human researcher，而不是完全取代研究者。

它的经验总结主要体现在：

| 阶段 | 经验沉淀 |
| --- | --- |
| Literature Review | 检索和总结已有论文，避免从零开始 |
| Experimentation | 记录实验实现、结果和失败 |
| Report Writing | 把发现汇总成 LaTeX 报告，并通过多轮编辑改进 |
| Co-pilot mode | 人类反馈进入关键 checkpoint |

AgentRxiv 则进一步把“经验总结”从单个 agent 的私有记忆，推到公共研究基础设施层。它模拟 arXiv/bioRxiv/medRxiv，为 autonomous research agents 提供一个 agent-generated preprint server。新的 agent lab 可以检索过去 agent 生成的论文，并在此基础上继续研究。

AgentRxiv 的关键思想是：

```text
单个 Agent 的经验有限；
多个 Agent 实验室的产出可以变成外部 collective memory。
```

项目页中提到，使用 AgentRxiv 的 autonomous agent laboratories 在 MATH-500 上通过持续构建先前研究输出，发现了新的 reasoning strategies；没有 AgentRxiv 访问时，性能更容易 plateau。

这给我们一个重要启发：经验总结不一定只存在于一个系统内部，也可以做成共享知识库或预印本服务器。

## 五、AIDE：把经验总结成 Solution Tree 和 Journal

AIDE / AIDE ML 不是完整“自动写论文”系统，但它在 ML engineering 和 AI R&D 自动化里很重要。它把问题建模为 code solution space tree search。

基本流程是：

```text
生成初始 solution drafts -> 执行代码 -> 解析 metric -> 选择 promising node -> 继续 debug 或 improve
```

它的经验总结很工程化：

| 产物 | 作用 |
| --- | --- |
| solution tree | 记录每个候选代码解和父子关系 |
| journal entries | 记录每一步做了什么、为什么、结果如何 |
| metric feedback | 用实际指标决定搜索方向 |
| best_solution.py | 保存当前最优可复现代码 |
| tree_plot.html | 让人类查看探索过程 |

这类经验总结特别适合借鉴到 AI Infra 项目里。因为它不是泛泛写“本轮失败了”，而是保存：

1. 哪段代码失败。
2. 失败日志是什么。
3. 修复后指标如何变化。
4. 哪个节点成为下一轮 base solution。

这比普通 reflection 文本更可执行。

## 六、DeepScientist：Findings Memory 是最清晰的经验系统

DeepScientist 是当前“经验总结”设计最明确的项目之一。它自称 local-first autonomous research studio，强调 one repo per quest、visible research progress、human takeover anytime。

它的核心是 Findings Memory 和 Research Map。

Findings Memory 不只是聊天历史，而是研究状态数据库。

| 记忆内容 | 价值 |
| --- | --- |
| idea finding | 保存生成过的研究假设和估值 |
| implement finding | 保存已实现 idea、实验结果、baseline delta |
| progress finding | 保存真正超过 baseline、值得深入分析的发现 |
| negative result | 保留失败路径，避免重复探索 |
| ablation finding | 记录哪个组件真正贡献收益 |
| reproduction lesson | 记录 baseline 复现和环境问题 |

DeepScientist 把 discovery 形式化为 Bayesian Optimization：每轮实验是一次昂贵评估，系统用历史 findings 选择下一步。它的经验总结不是事后写日志，而是直接影响 acquisition strategy。

这点很关键：

```text
经验不是归档材料；
经验是下一轮搜索策略的输入。
```

如果自己做 Auto Research 系统，我会优先借鉴 DeepScientist 的 finding schema。

## 七、AutoResearchClaw：把失败变成 Cross-run Lessons

AutoResearchClaw 的定位是 self-reinforcing autonomous research。论文和 README 都强调五个机制：structured multi-agent debate、self-healing execution、verifiable reporting、human collaboration、evolutionary learning。

它的经验总结分两层。

第一层是单次运行内的经验：

| 机制 | 经验如何被使用 |
| --- | --- |
| Multi-Agent Debate | Innovator、Pragmatist、Contrarian 等角色挑战假设 |
| Self-Healing Execution | 实验失败后进行 repair，并决定 Proceed / Refine / Pivot |
| Numeric Registry | 论文数字必须来自实验 registry |
| Citation Verification | 引用通过 CrossRef、OpenAlex、arXiv、Semantic Scholar 等验证 |
| HITL Gates | 人类在高杠杆节点介入 |

第二层是跨运行经验：

```text
运行日志 -> 失败归因 -> lesson extraction -> severity/category/mitigation -> time-decayed injection
```

也就是说，系统会把过去的失败和人类反馈变成可复用 lesson，并在未来类似任务中注入。它还使用时间衰减，避免旧经验永久支配新环境。

这是一种很成熟的设计思路。经验不是无限保留，而是带权重、带范围、带时间。

## 八、ARIS：经验总结要经过跨模型审查

ARIS 的重点是 adversarial multi-agent collaboration。它让执行模型推进研究，让不同模型家族的 reviewer 进行冷启动审查，降低同模型自审的盲区。

ARIS 的经验总结有几个很有价值的设计。

| 机制 | 作用 |
| --- | --- |
| Research Wiki | 保存论文、想法、失败实验、项目决策和 claim 状态 |
| Claim Ledger | 每个结论绑定证据、状态和限制 |
| Evidence-to-Claim Audit | 检查实验结果是否支持论文声明 |
| Reviewer Independence Protocol | 每轮 reviewer 使用新线程，避免 reviewer 继承旧叙事 |
| Meta-optimize | 基于 usage logs 提出 skill 改进，由 reviewer 和人类批准 |

ARIS 的关键教训是：经验总结本身也需要审查。

如果 Agent 从错误日志里总结出错误经验，或者 reviewer 因为连续对话开始维护自己之前的判断，这些经验反而会污染未来运行。

所以 ARIS 强调：

1. reviewer 要跨模型。
2. reviewer 要新线程。
3. claim 要绑定证据。
4. skill 改进不能无条件自动合并。

这对高风险科研 Agent 特别重要。

## 九、SAGA：总结失败模式，然后演化目标函数

SAGA 的方向和前面几个不同。它不是主要做论文生成，而是科学发现中的目标自演化。

它的经验总结路径是：

```text
候选解搜索 -> Analyzer 分析失败模式 -> Planner 提出新 objective -> Implementer 生成 scoring function -> Optimizer 再搜索
```

SAGA 的经验不是总结成“下次注意事项”，而是直接变成新的 objective。

例如在药物或蛋白设计里，系统可能发现：

| 失败模式 | 经验总结 | 下一步 |
| --- | --- | --- |
| 活性高但毒性差 | 单一活性指标不够 | 加入安全性 objective |
| 分数高但结构不合理 | proxy reward 被 exploit | 加入 developability filter |
| 候选缺乏新颖性 | 搜索陷入已知结构附近 | 加入 novelty objective |
| 评分器与实验不一致 | 代理指标失真 | 调整 composite scorer |

这类经验总结最激进：**经验会改变评价函数本身。**

这也是模型自进化里非常值得关注的一条线。系统不是只记住过去，而是修改自己判断“好坏”的标准。

## 十、经验总结机制分层

把这些项目放在一起看，可以总结出一套通用架构。

![Experience summarization stack for autonomous research systems](/assets/images/auto-research-experience-summary/experience-stack.svg)

| 层级 | 内容 | 代表项目 |
| --- | --- | --- |
| Raw Trace | 保存原始 prompt、代码、日志、指标、错误和 artifact | AIDE、AI Scientist v2、AutoResearchClaw |
| Structured Finding | 把结果整理成假设、证据、状态、限制和下一步 | DeepScientist、ARIS |
| Failure Lesson | 把失败归因成触发条件、严重性、修复动作、复用范围 | AutoResearchClaw、ARIS |
| Policy / Skill Update | 把高频 lesson 变成 checklist、review gate、scorer 或 skill | ARIS、AutoResearchClaw、SAGA |
| Retrieval into Future Runs | 按任务相似度、时间衰减和严重性注入下一轮 | DeepScientist、AgentRxiv、AutoResearchClaw |

我认为一个成熟 Auto Research 系统至少要有前三层。没有 Raw Trace，经验不可验证；没有 Structured Finding，经验不可检索；没有 Failure Lesson，系统会重复犯错。

## 十一、经验总结应该保存什么

如果自己实现一个 Auto Research 系统，我建议每轮都保存下面这些结构化对象。

### 1. Finding

```yaml
finding_id: f_20260829_001
type: idea | implementation | progress | negative
hypothesis: "加入检索阶段 reranker 可以提升多跳问答准确率"
evidence:
  - experiments/run_012/metrics.json
  - reports/ablation_reranker.md
status: supported
baseline_delta:
  metric: exact_match
  value: 0.037
limitations:
  - "只在一个数据集上验证"
next_actions:
  - "增加更多 seed"
  - "测试长上下文设置"
```

### 2. Failure Lesson

```yaml
lesson_id: l_20260829_004
category: experiment_design
trigger: "模型声称提升，但 baseline 未固定随机种子"
severity: high
evidence:
  - reviews/reviewer_round_2.md
  - experiments/run_018/log.txt
mitigation:
  - "所有对比实验必须固定 seed"
  - "报告均值和标准差"
reuse_scope:
  - "classification"
  - "rag-eval"
decay_half_life_days: 90
approved_by_human: true
```

### 3. Claim Ledger

```yaml
claim_id: c_001
claim: "方法 A 在 HotpotQA 上比 baseline 提升 3.7 个点"
evidence:
  - experiments/run_012/metrics.json
  - tables/main_results.csv
allowed_wording: "improves on this benchmark in our setting"
forbidden_wording:
  - "solves multi-hop reasoning"
  - "generalizes to all RAG systems"
status: supported_with_limitations
```

这三个对象分别对应：发现、教训、声明。它们比自由文本 reflection 更适合长期系统。

## 十二、经验总结的常见坑

### 1. 只总结成功，不保存失败

这会导致系统不断重复走死路。DeepScientist 和 AutoResearchClaw 都强调 negative results / failure lessons 的价值。

### 2. 总结太抽象

例如：

```text
下次要更加严谨。
```

这没有用。好的 lesson 应该是：

```text
当实验比较 baseline 和 method 时，如果没有固定随机种子和报告方差，禁止生成强 claim。
```

### 3. 经验没有证据链

经验必须能回溯到日志、指标、代码或 reviewer 反馈。否则它可能只是模型的二次幻觉。

### 4. 经验永久有效

工具、模型、数据集、依赖版本都会变化。AutoResearchClaw 的 time-decay 是值得借鉴的：旧经验可以保留，但权重要下降。

### 5. 经验不区分作用范围

一个 NLP benchmark 的教训不一定适用于化学分子设计。lesson 要有 domain、task、metric、environment scope。

### 6. 让同一个模型无审查地总结自己

ARIS 的 cross-model review 提醒我们：经验总结也需要独立审查，尤其是涉及 claim、paper、实验成功与否时。

## 十三、我建议的实现方案

如果要在自己的科研 Agent 项目里加入经验总结，我会按这个顺序做。

| 阶段 | 目标 | 实现 |
| --- | --- | --- |
| 第 1 阶段 | 保存完整 trace | 每次 run 保存 prompt、工具调用、代码 diff、日志、指标 |
| 第 2 阶段 | 抽取 findings | 用规则 + LLM 把实验结果整理成 finding YAML |
| 第 3 阶段 | 抽取 failure lessons | 对失败 run 做归因，保存 trigger、severity、mitigation |
| 第 4 阶段 | 建 claim ledger | 论文/报告中的每个强 claim 都绑定 evidence |
| 第 5 阶段 | 检索复用经验 | 新任务开始时按 topic、method、metric 检索相关 findings/lessons |
| 第 6 阶段 | 经验审查 | 高严重度 lesson 和 claim 由不同模型 reviewer 或人类确认 |
| 第 7 阶段 | skill/policy 更新 | 高频 lesson 变成 checklist、eval gate 或 skill 修改建议 |

最小可用版本不复杂：

```text
runs/<run_id>/
  trace.json
  metrics.json
  logs/
  artifacts/
  finding.yaml
  lessons.yaml
  claims.yaml
```

再加一个检索器：

```text
before new run:
  retrieve top-k relevant findings
  retrieve high-severity active lessons
  inject into planning prompt
```

这就已经具备跨运行经验复用能力。

## 十四、对 AI Infra 的启发

Auto Research 项目的经验总结机制，本质上是一种 Agent Infra 能力。

| Auto Research 机制 | AI Infra 对应能力 |
| --- | --- |
| run trace | observability / tracing |
| finding memory | task memory / artifact store |
| failure lesson | incident postmortem / runbook |
| claim ledger | evidence provenance / audit |
| reviewer loop | quality gate / policy checker |
| search tree | experiment tracking / lineage |
| cross-run retrieval | long-term memory / vector index |
| time decay | memory freshness / relevance scoring |
| HITL approval | governance / release control |

如果你的目标是做 AI Infra 工作，这些设计非常值得写进项目：

1. Agent 每次运行有 trace。
2. 每个结果有 evidence。
3. 每个失败能生成 postmortem。
4. 每条经验有 scope、severity、status。
5. 新任务开始前会检索历史经验。
6. 高风险经验修改需要 review gate。

这会让项目明显区别于普通 Agent demo。

## 十五、总结

现在开源 Auto Research / AI Scientist 项目的经验总结，大致正在从四个方向收敛：

1. **从输出论文到保存过程**：AI Scientist v2、AIDE 都开始保存 tree、journal、debug path。
2. **从聊天历史到结构化记忆**：DeepScientist 的 Findings Memory 更像研究数据库。
3. **从失败终止到失败复用**：AutoResearchClaw 把失败变成 lesson，并注入未来运行。
4. **从自我反思到外部审查**：ARIS 强调跨模型 reviewer、claim ledger 和 evidence audit。
5. **从单体系统到集体记忆**：AgentRxiv 让多个 agent 实验室共享研究产物。

我的判断是，下一代 AI Scientist 的关键不只是更强模型，而是更强的经验系统。它应该能回答：

```text
我们试过什么？
什么失败了？
为什么失败？
哪些结论有证据？
哪些经验还有效？
下一轮应该避免什么？
下一轮应该优先探索什么？
```

如果一个 Auto Research 系统能把这些问题回答清楚，它就不只是“自动写论文工具”，而是逐渐接近一个可积累、可审计、可自我改进的科研操作系统。

## 参考资料

- The AI Scientist v1 官方介绍：https://sakana.ai/ai-scientist/
- The AI Scientist v2 GitHub：https://github.com/SakanaAI/AI-Scientist-v2
- Agent Laboratory GitHub：https://github.com/SamuelSchmidgall/AgentLaboratory
- AgentRxiv 项目页：https://agentrxiv.github.io/
- AIDE ML GitHub：https://github.com/wecoai/aideml
- DeepScientist GitHub：https://github.com/ResearAI/DeepScientist
- AutoResearchClaw GitHub：https://github.com/aiming-lab/AutoResearchClaw
- ARIS 项目说明：https://github.com/HJXA/ARIS/blob/main/docs/ARIS_INTRO.md
- SAGA GitHub：https://github.com/btyu/SAGA
