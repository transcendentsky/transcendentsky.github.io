---
title: ShinkaEvolve：让大模型驱动的程序演化更省样本、更开放
tags:
  - AI Scientist
  - Auto Research
  - Agent
  - 模型自进化
  - LLM
---

> ShinkaEvolve 是 Sakana AI 提出的开源 LLM 引导程序演化框架。它把大模型当作“变异算子”，在程序档案、岛模型、代码新颖性筛选、动态模型选择和元经验总结的共同作用下，寻找更好的算法、Agent scaffold 和训练目标。本文基于论文 **ShinkaEvolve: Towards Open-Ended And Sample-Efficient Program Evolution**，重点解释它解决了什么问题、为什么有效、论文展示了哪些结果，以及它距离真正的开放式科研还有多远。

![ShinkaEvolve evolutionary discovery architecture](/assets/images/shinkaevolve/shinkaevolve-architecture.svg)

<!--more-->

## 一、论文基本信息

| 项目 | 信息 |
| --- | --- |
| 原论文题目 | *ShinkaEvolve: Towards Open-Ended And Sample-Efficient Program Evolution* |
| 作者 | Robert Tjarko Lange、Yuki Imajuku、Edoardo Cetin |
| 单位 | Sakana AI |
| arXiv | [arXiv:2509.19349](https://arxiv.org/abs/2509.19349) |
| 首次提交 | 2025 年 9 月 17 日，v1 |
| 论文规模 | 52 页，14 张图 |
| 代码 | [SakanaAI/ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve) |
| 开源许可 | 论文摘要和项目说明标注为 Apache 2.0 |

这篇工作的背景，是近两年逐渐兴起的 **LLM-driven program evolution**：给大模型一个初始程序，让它不断修改、运行和比较候选代码，然后把表现更好的程序继续作为后续变异的素材。它与普通代码生成的差别在于，目标不是一次性生成“看起来合理”的代码，而是在一个可执行评价函数上持续搜索。

但这种方法很容易遇到两个瓶颈：第一，候选程序的数量太少时，搜索可能找不到好解；候选程序数量一多，评估成本又迅速升高。第二，如果每次都围绕当前最好程序做局部修改，搜索很快会陷入局部最优。ShinkaEvolve 的目标，就是用更好的搜索控制，让每一次昂贵的程序评估都更有价值。

## 二、它究竟在解决什么问题？

把程序演化抽象一下，可以写成：

```text
初始程序 P0
    -> 选择父代与灵感程序
    -> LLM 生成代码变异
    -> 检查代码是否合法、是否足够新
    -> 执行程序并获得 fitness / metrics / textual feedback
    -> 更新档案、模型选择概率和经验总结
    -> 继续下一代搜索
```

其中真正昂贵的环节通常不是文本生成，而是 `evaluate(program)`：它可能需要运行一个优化器、解决一组数学题、提交竞赛测试，甚至训练一个小型语言模型。因此，ShinkaEvolve 的核心评价标准不是“生成了多少代码”，而是：

> 在相同或更少的程序评估预算下，能否更快到达高质量解？

论文把问题称为 sample efficiency。这里的 sample 可以理解为一次被真正执行并计入搜索的程序提案，而不是一次普通的 token 采样。

## 三、整体架构：一个带记忆的进化搜索器

ShinkaEvolve 的运行状态可以看作四部分：

| 组件 | 保存或决定什么 | 解决的问题 |
| --- | --- | --- |
| Archive | 已评估程序、fitness、公共指标、文本反馈、父子关系 | 让系统记住过去的搜索历史 |
| Island populations | 多个相对独立的子种群 | 避免所有搜索分支过早收敛到同一条路径 |
| LLM ensemble | GPT、Gemini、Claude、DeepSeek 等模型及其采样参数 | 组合不同模型的代码能力和风格 |
| Meta-scratchpad | 对近期成功程序的策略总结和实现建议 | 把局部成功提炼成下一轮可复用经验 |

一次变异不只是“把最好程序交给一个模型”。系统会先从某个 island 中选择一个主父代，再选取 top-k 程序和随机档案程序作为 inspiration。随后从 LLM ensemble 中选择模型和温度，生成 diff edit、full rewrite 或 crossover proposal。

这样设计的直觉是：

- 只选最好程序，容易过早收敛；
- 只随机选程序，容易浪费评估预算；
- 只使用一个模型，容易被单一模型的偏好限制；
- 只保留分数，无法告诉后续模型“为什么这个程序更好”。

## 四、三个核心创新点

### 1. 带新颖性偏好的父代采样

传统的 hill climbing 会持续选择当前分数最高的程序作为父代。这种方法前期提升很快，但一旦当前解附近没有好的邻居，就会停滞。

ShinkaEvolve 的 weighted sampling 同时考虑程序表现和它已经产生的子代数量。用直观形式表示：

```text
parent weight = performance score × novelty opportunity
novelty opportunity ≈ 1 / (number of offspring + 1)
```

高分程序仍然更容易被选中，但已经被反复扩展的程序会逐渐降低采样权重；那些表现不错、却还没有被充分探索的程序，会获得更多机会。论文还讨论了 uniform、hill climbing、power-law 等策略，使探索与利用之间可以连续调节。

这比简单的 best-of-N 更像真正的种群搜索：质量很重要，但搜索空间覆盖率也很重要。

### 2. 基于 embedding 和 LLM judge 的代码新颖性拒绝采样

LLM 很容易生成“改了变量名、换了注释、算法几乎不变”的近重复程序。如果这些候选都进入执行队列，API 调用和评估时间会被消耗在没有新信息的样本上。

ShinkaEvolve 对可变代码片段做 embedding，计算它与 island 中已有程序的余弦相似度。当最大相似度超过阈值时，系统会拒绝该提案；如果需要更细的判断，还可以让另一个 LLM 充当 novelty judge，判断两个程序是否在算法意义上真的不同。

这个机制有两层价值：

1. 在执行前过滤明显的近重复候选，节约昂贵的 world feedback。
2. 把“新颖性”从一个模糊的提示词要求，变成搜索流程中的显式约束。

论文的消融实验显示，embedding-based rejection 相比不做拒绝采样有明显收益；额外加入 LLM novelty judge 的提升相对有限。这是一个很有工程价值的结论：便宜、稳定的向量相似度过滤，可能已经覆盖了大部分重复样本。

### 3. 基于 bandit 的 LLM ensemble selection

不同大模型的优势并不固定。有的模型擅长小步 diff，有的模型更容易提出大胆的结构重写；同一个模型在搜索初期和后期的效果也可能不同。

ShinkaEvolve 不把所有 LLM 以固定概率均匀采样，而是把每个模型看作一个 bandit arm。系统根据该模型生成的变异相对于父代的改进幅度，动态更新模型选择概率。它采用 UCB1 思路，在探索尚未充分使用的模型和利用当前高收益模型之间取得平衡。

论文特别使用了相对改进而非绝对 fitness：如果某个父代本来就已经很强，那么一个小的绝对分数也可能是有价值的进步；反过来，弱父代上的高分也不能简单等价比较。这个处理是为了适应不断变化的档案状态。

从系统设计角度看，这相当于让“模型路由”也参与了进化，而不是把模型路由当作静态配置。

## 五、Meta-scratchpad：系统如何总结经验？

每隔若干代，ShinkaEvolve 会让一个 meta-agent 分析近期程序的评估结果，提炼出：

- 哪些设计模式反复出现在高分程序中；
- 哪些修改虽然新颖，但没有改善目标；
- 哪些实现技巧值得后续程序继续尝试；
- 下一轮变异时应优先检查哪些风险。

这些内容会被整理成 implementation recommendations，并追加到后续 mutation prompt 中。它不是完整的参数更新，也不是重新训练一个模型，而是通过在线文本记忆改变下一轮的搜索上下文。

我认为这是 ShinkaEvolve 里容易被忽略、但对 Auto Research 很重要的一点：**搜索档案保存的是“发生过什么”，meta-scratchpad 尝试进一步总结“为什么会这样，以及下一步应该怎么做”。**

不过，这类总结仍然依赖语言模型的归纳能力。它可能把偶然相关性误认为通用规律，因此在真正生产化时，最好同时保留原始实验、指标、代码版本和可追溯的 recommendation 来源。

## 六、三种代码变异方式

ShinkaEvolve 支持三种主要 mutation operator：

| 方式 | 特点 | 适合场景 |
| --- | --- | --- |
| Diff-based edit | 用 SEARCH/REPLACE 等局部补丁修改代码 | 已经有可运行基线，需要定向优化 |
| Full rewrite | 在约束不可变代码块的前提下整体重写 | 需要大幅调整算法结构 |
| Crossover | 从另一个档案程序中取灵感，与当前父代组合 | 合并两条不同搜索分支的有效思路 |

系统使用 `EVOLVE-BLOCK-START` 和 `EVOLVE-BLOCK-END` 标记不可变区域，并对无效补丁进行解析和重新采样。这是一个很实用的工程约束：LLM 可以负责提出创意，但执行环境不能因为它误改评估接口、数据读取或输出协议而失效。

## 七、论文实验：它到底发现了什么？

### 1. Circle Packing：150 次评估超过 AlphaEvolve 解

圆打包任务要求把 26 个圆放入单位正方形，在不重叠且不越界的约束下最大化半径总和。论文报告 ShinkaEvolve 在少于 150 次程序评估内超过了 AlphaEvolve 的已有解，而此前类似方法通常需要数千次评估。

最终方案不是一个单点技巧，而是多种策略的组合：

- 用 golden-angle spiral、角落和边缘位置构造更好的初始化；
- 结合 SLSQP 等梯度优化与 simulated annealing；
- 在局部圆移动和全局环旋转之间切换；
- 使用自适应温度和 reheating 避免过早收敛；
- 通过约束感知的半径计算维持可行性。

这个结果说明，程序演化的价值不只是优化已有参数，也可能自动组合出人类没有直接写出的算法管线。

### 2. AIME：演化数学推理 Agent scaffold

在 AIME 2024 任务上，论文把每道题最多 10 次 LLM query 作为约束，使用 gpt-4.1-nano 作为基础模型，演化包含提示、多个解题角色和验证步骤的 agent scaffold。

论文报告发现了明显的 performance-efficiency Pareto frontier：一个方案用 7 次调用就达到最高性能，另一个方案使用完整 10 次预算取得相近结果。搜索过程探索了多步反思、专家 ensemble、错误检测和两阶段验证等结构。

更有意思的是迁移实验：在 2023、2025 AIME 题目以及 gpt-4.1-mini、gpt-4.1、o4-mini 等模型上，发现的 scaffold 仍能工作。论文将此视为架构策略具有一定泛化性，而不是只对单一模型和单一题集过拟合。

### 3. ALE-Bench：在已有高质量程序上继续改进

ALE-Bench LITE 包含 10 个 AtCoder 启发式竞赛任务。ShinkaEvolve 以 ALE-Agent 找到的程序作为初始解，再用公开测试集 fitness 继续演化，最后在私有测试集上验证。

论文报告平均提升约 2.3%。在 `ahc039` 任务上，加入缓存验证过程和 targeted edge move 后，方案从原先的第 5 名水平提升到如果参赛可达第 2 名的水平。

但这个实验也暴露了一个重要问题：很多修改仍然贴近初始 ALE-Agent 解，说明系统可能对 initialization solution 存在依赖，而不是在整个算法空间中自由探索。

### 4. MoE：演化新的 load-balancing loss

论文还把 ShinkaEvolve 用到 Mixture-of-Experts 训练目标设计。小规模搜索模型有 556M 参数、64 个 experts、每个 token 激活 8 个 experts，并用超过 2B tokens 的 FineWeb 数据进行预训练。搜索出的 loss 再被迁移到 2.7B MoE 模型和接近 30B tokens 的训练中。

它发现的核心思路是在传统 global-batch load-balancing loss 之外，对低使用率 expert 增加一个由路由熵调节的软约束：当某一层的路由过于集中、某些 expert 低于最低使用阈值时，额外惩罚会增强；当 expert 达到最低使用程度后，这个项会自然减弱。

直观地说，它试图修复一个盲点：整体统计看起来平衡，并不意味着每个 expert 都真正被充分使用。

| 实验方向 | 搜索对象 | 论文报告的主要结果 |
| --- | --- | --- |
| Circle Packing | 数值优化程序 | 少于 150 次评估超过 AlphaEvolve 解 |
| AIME | 数学推理 Agent scaffold | 找到性能与 LLM 调用次数之间的 Pareto 解，并有跨模型迁移 |
| ALE-Bench | 启发式竞赛程序 | 10 个任务平均提升约 2.3% |
| MoE Training | load-balancing loss | 发现针对低使用率 expert 的新正则项，并在更大训练设置中验证 |

## 八、消融实验告诉了我们什么？

ShinkaEvolve 的贡献不是一个无法拆解的黑盒，论文做了三组关键消融：

| 组件 | 对照方法 | 论文结论 |
| --- | --- | --- |
| 父代采样 | random / hill climbing / weighted | weighted sampling 更能兼顾早期提升和后期持续探索 |
| LLM ensemble | 单模型 / 固定均匀 ensemble / bandit ensemble | bandit 动态选择整体表现最好 |
| 新颖性过滤 | 不过滤 / embedding threshold / 加 LLM judge | embedding 过滤收益明显，额外 LLM judge 只带来边际提升 |

这三项消融共同说明：ShinkaEvolve 的效果来自搜索控制，而不是单纯把更多模型或更高温度堆在一起。尤其是 parent selection 和 novelty rejection，分别从“选谁来变异”和“哪些候选值得执行”两个方向减少了搜索浪费。

## 九、ShinkaEvolve 的优势和创新点

### 优势一：把 sample efficiency 当作一等公民

很多 Agent 论文强调最终分数，却不充分讨论为此花了多少次模型调用、多少次程序执行和多少训练成本。ShinkaEvolve 直接把评估预算放到方法设计中心，这对科研自动化和个人研究者很重要。

### 优势二：开放源码，具备可复用的搜索基础设施属性

它不是只发布一个任务脚本，而是提供 archive、island、mutation、novelty、LLM selection、评估队列和可视化等框架组件。对想做 Auto Research、Agent self-improvement 或 AI Infra 的开发者来说，这种模块化比单个 benchmark 结果更有价值。

### 优势三：把“模型路由”纳入在线学习

大模型 ensemble 通常被当作静态列表。ShinkaEvolve 根据不同模型对 fitness 的边际贡献动态调节采样概率，说明模型选择本身也可以被优化。这一思想可以迁移到代码修复、工具调用、RAG 查询规划甚至多 Agent 角色分配。

### 优势四：支持跨领域验证

圆打包、数学推理 Agent、竞赛程序和 MoE loss 横跨数值优化、Agent 设计、算法工程和模型训练。虽然这些任务仍有共同点，即都能定义明确的执行反馈，但跨任务验证增强了框架作为通用搜索器的说服力。

### 优势五：经验可以进入下一代 prompt

Meta-scratchpad 让系统不止记住当前最优代码，还能提炼策略并传播到后续 mutation。这比简单保存 top-k solution 更接近一个具有“经验积累”的研究系统。

## 十、它的劣势和现实边界

### 1. 仍然依赖人工定义目标函数

ShinkaEvolve 可以搜索程序，但不会自动决定什么是值得优化的问题。研究者仍然要提供初始程序、可运行环境、评估脚本、fitness 定义和预算约束。作者也明确指出，任务规格和评价函数需要人类专业知识。

因此它目前更准确的定位是：**开放式程序优化和发现引擎**，而不是完全自主的科学家。

### 2. 对“可执行、可数值评价”的问题更友好

如果一个研究结论需要长期观察、主观判断、复杂实验设计或多维审稿，单一 scalar fitness 就不够了。ShinkaEvolve 的架构天然适合有明确 world feedback 的任务，例如竞赛分数、验证误差、训练 loss、约束违反程度等。

### 3. 探索与利用仍有手工配置

论文承认，当前实现对 exploration-exploitation balance 的自动控制有限。岛数量、archive 大小、父代策略、novelty threshold、LLM ensemble、mutation 比例和 meta-scratchpad 间隔等参数，仍可能显著影响结果。

一个在圆打包上有效的阈值，不一定适合代码修复或模型训练。要成为更稳定的通用框架，需要让这些超参数也被监控、校准甚至自适应演化。

### 4. 可能对初始程序和公开反馈过拟合

ALE-Bench 实验已经观察到演化结果经常贴近 ALE-Agent 的初始化解。对于有强 baseline 的任务，这种局部改进很有用；但对于真正需要新范式的科研问题，初始化程序可能把搜索限制在一个狭窄区域。

### 5. API 成本和并行评估成本仍然存在

样本效率提升不等于成本为零。一次候选可能需要多个 LLM 调用、embedding、novelty judge 和真实程序运行。MoE loss 实验还需要小模型搜索与大模型迁移验证。论文也指出，大规模 API 使用本身可能形成新的经济门槛。

### 6. “发现”需要独立复现和更强验证

一个程序在公开 fitness 上提升，不自动等于发现了普适的新知识。对于算法任务，需要隐藏测试、跨随机种子和跨环境验证；对于模型训练，需要不同规模、数据和下游任务验证；对于科研结论，还需要人类审查和独立复现。

## 十一、和普通 AI Agent 的本质区别

普通工具型 Agent 通常优化的是一次任务的完成率：根据用户输入调用工具、生成答案或执行工作流。ShinkaEvolve 优化的是一个“能被反复运行和比较的程序对象”。

| 维度 | 普通 AI Agent | ShinkaEvolve |
| --- | --- | --- |
| 主要对象 | 对话、任务轨迹、工具调用 | 可执行程序及其变体 |
| 反馈 | 人类偏好、规则、结果状态 | fitness、公共指标、文本反馈、运行日志 |
| 记忆 | 对话历史、向量库、任务状态 | 程序 archive、岛种群、父子树、meta-scratchpad |
| 改进方式 | prompt、策略或模型更新 | 选择、变异、拒绝采样、重组、动态模型路由 |
| 适合任务 | 一次性或短流程工作 | 可重复执行、可比较、目标明确的搜索问题 |
| 风险 | 幻觉、工具误用、流程失败 | 局部最优、目标投机、评估过拟合、成本失控 |

这也是为什么 ShinkaEvolve 对 AI Infra 求职者有启发：它把模型调用、异步队列、实验数据库、沙箱执行、指标采集、搜索策略和可视化连成了一个完整系统。

## 十二、如果把它用于自己的 Agent 项目

可以先从一个小而明确的任务开始，而不是直接尝试“让 Agent 自己做科研”。一个实用的落地路径是：

1. 先把 Agent 的关键策略写成可执行程序，例如路由策略、检索 top-k、工具选择、反思次数或多 Agent 协作拓扑。
2. 把线上或离线评测拆成 scalar fitness、可解释 public metrics 和 textual feedback。
3. 保存每个候选的代码、配置、父代、模型、随机种子、日志和成本。
4. 加入 novelty rejection，避免不断重复同一种 prompt 或策略。
5. 用多个模型生成变异，并记录每个模型带来的相对收益。
6. 每隔若干代总结成功模式，但不覆盖原始实验记录。
7. 在验证集搜索，在隐藏测试集和不同随机种子上确认结果。

例如，对一个电力智能体项目，可以让程序演化搜索：意图识别阈值、工具路由规则、检索策略、异常回退策略和多轮澄清流程。fitness 不应只看最终回答准确率，还可以同时考虑响应时延、工具调用次数、故障恢复率和人工审核通过率。

## 十三、我的总体评价

ShinkaEvolve 最有价值的地方，不是它宣称“让 AI 自动发现一切”，而是它把 LLM 作为搜索过程中的一种可替换能力，并认真处理了三个现实问题：如何减少无效样本，如何保持搜索多样性，以及如何让不同模型在不同阶段发挥作用。

它可以被看成连接以下几类系统的桥梁：

```text
LLM code generation
        +
Evolutionary search
        +
Executable evaluation
        +
Experiment memory
        =
More sample-efficient discovery
```

但它还没有解决最难的那一步：系统如何自己提出重要目标、判断目标是否值得研究，并在开放世界里验证结论。论文把自动任务规格、真正的 open-ended objective generation、自指式 refinement 和在线元学习列为未来方向，这也正是后续 AI Scientist 和模型自进化系统的核心战场。

所以，如果把它放进今天的技术版图里，我会这样定位：ShinkaEvolve 是一个非常扎实的 **LLM 引导程序演化与搜索基础设施**，已经展示了跨任务的样本效率和可复用性；但它距离“完全自主的科学发现系统”，还需要更强的任务生成、事实验证、长期记忆和安全约束。

## 参考资料

1. Robert Tjarko Lange, Yuki Imajuku, Edoardo Cetin. [ShinkaEvolve: Towards Open-Ended And Sample-Efficient Program Evolution](https://arxiv.org/abs/2509.19349), arXiv:2509.19349, v1, 2025-09-17.
2. Sakana AI. [ShinkaEvolve GitHub repository](https://github.com/SakanaAI/ShinkaEvolve).

