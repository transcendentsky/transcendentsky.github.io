---
title: AI for Mathematical Reasoning：从语言模型、神经符号系统到可验证发现
tags:
  - AI for Math
  - Mathematical Reasoning
  - Survey
  - Formal Methods
---

> 原论文题目：**Artificial Intelligence for Mathematical Reasoning: An Integrated Survey of Language Models, Neuro-symbolic Systems, and Verified Discovery**。这是一篇关于 AI 数学推理的综合综述，它把自然语言解题、几何多模态推理、形式化证明、神经符号系统、数学发现和可验证推理工作流放在同一张地图里观察。

![AI for Mathematical Reasoning landscape](/assets/images/ai4math-survey/landscape.svg)

<!--more-->

## 一、论文基本信息

| 项目 | 信息 |
| --- | --- |
| 论文题目 | Artificial Intelligence for Mathematical Reasoning: An Integrated Survey of Language Models, Neuro-symbolic Systems, and Verified Discovery |
| arXiv 编号 | arXiv:2606.08728 |
| DOI | 10.48550/arXiv.2606.08728 |
| 最新版本 | v4，2026 年 7 月 26 日修订 |
| 首次提交 | 2026 年 6 月 7 日 |
| 状态 | Under review |
| 篇幅 | 47 页，14 张图，22 张表 |
| 论文链接 | https://arxiv.org/abs/2606.08728 |
| HTML 版本 | https://arxiv.org/html/2606.08728 |
| 配套资料 | https://github.com/Starscream-11813/awesome-AI4Math |

作者和单位如下。

| 作者 | 单位 |
| --- | --- |
| Syed Rifat Raiyan | Systems and Software Lab, Department of Computer Science and Engineering, Islamic University of Technology, Gazipur, Bangladesh |
| Mohsinul Kabir | Department of Computer Science, University of Manchester, Manchester, United Kingdom |
| Hasan Mahmud | Systems and Software Lab, Department of Computer Science and Engineering, Islamic University of Technology, Gazipur, Bangladesh |
| Md Kamrul Hasan | Systems and Software Lab, Department of Computer Science and Engineering, Islamic University of Technology, Gazipur, Bangladesh |
| Sophia Ananiadou | Department of Computer Science, University of Manchester, Manchester, United Kingdom |

其中 Mohsinul Kabir 为通讯作者。

## 二、为什么数学推理是 AI 的硬问题？

数学推理一直是 AI 的核心试金石，因为它同时要求模型具备三类能力。

| 能力 | 含义 | 难点 |
| --- | --- | --- |
| 语义理解 | 理解自然语言题目、公式、图形和隐含条件 | 题面经常省略关系，数字和对象的绑定容易错 |
| 多步推导 | 把条件组织成表达式、证明链或搜索策略 | 中间一步错，最终答案可能看起来仍然合理 |
| 可验证性 | 答案、证明或构造需要能被检查 | 自然语言解释不等于数学证明，形式化系统又很严格 |

这篇综述的一个重要价值，是没有把“数学能力”简单等同于 benchmark 分数，而是把它拆成多个层次：从小学应用题，到竞赛题，到带图几何题，到 Lean 形式化证明，再到开放数学问题上的发现式探索。

## 三、这篇综述的四条主线

论文把 AI 数学推理的技术版图组织成四条主线。

| 主线 | 代表任务 | 核心问题 |
| --- | --- | --- |
| 非形式化推理 | Math Word Problem、竞赛数学、几何题、多模态数学题 | 模型能否从题面中抽取结构，并生成正确推理链 |
| 形式化推理 | Lean、Isabelle、autoformalization、tactic prediction、proof search | 模型能否把自然语言数学转成机器可检查的证明 |
| 数学发现 | 生成构造、改进边界、搜索反例、辅助开放问题 | AI 是否能从“解题机器”变成“候选发现机器” |
| 推理与训练技术 | Chain-of-thought、tool use、process reward model、RLVR、verifier-assisted pass@k | 如何把生成模型和验证器连接起来 |

这四条线共同指向一个趋势：未来的数学 AI 不太可能只是一个单次输出答案的聊天模型，而更像一个带搜索、验证、修复和证据记录的工作流系统。

## 四、从应用题求解到 reasoning-model era

早期 Math Word Problem 系统主要依赖规则、模板、语义解析和表达式生成。它们能处理结构固定的问题，但一旦题面换一种说法、条件顺序变化，或者出现无关信息，就很容易失效。

深度学习阶段把问题变成序列到表达式、树结构生成、图神经网络建模等任务，提升了覆盖范围，但依然存在泛化问题。LLM 出现后，数学推理进入了新的阶段：模型可以直接用自然语言写出解题过程，也可以通过 chain-of-thought、self-consistency、tool use 等方法提高答案命中率。

论文把 OpenAI o1 之后的一段时期称为 reasoning-model era。这个阶段的特点不是模型突然“懂数学”了，而是推理时计算被显著放大：模型会生成更长的思考链，尝试多条路径，并借助奖励模型、验证器或工具筛掉错误候选。

## 五、多模态几何：图形不是装饰，而是条件来源

几何问题比纯文本应用题更难，因为它需要同时处理文字和图形。图中一个角标、垂线、相交点、平行关系，都可能是解题关键。

| 挑战 | 说明 |
| --- | --- |
| 图形解析 | 需要识别点、线、角、圆、相交、垂直、平行等结构 |
| 跨模态指代 | 题目文字中的 “this angle”“the segment” 往往依赖图形上下文 |
| 定理选择 | 需要知道什么时候用相似三角形、勾股定理、圆周角定理等 |
| 标注噪声 | 图形可能不按比例绘制，视觉近似不能直接当作数学事实 |

这也是 vision-language model 在数学推理中最容易暴露短板的地方。普通图像理解强调“看见了什么”，几何推理更关心“哪些关系是可推导条件”。

## 六、形式化证明：从会解释到能被机器检查

自然语言证明有弹性，Lean 或 Isabelle 里的形式化证明则没有弹性。一个定理必须被写成精确的形式语言，每一步推理都要通过 proof assistant 的内核检查。

![Generate verify repair loop](/assets/images/ai4math-survey/verification-loop.svg)

形式化数学推理通常包括几个环节。

| 环节 | 作用 | 典型技术 |
| --- | --- | --- |
| Autoformalization | 把自然语言命题翻译成 Lean 等形式语言 | LLM 翻译、检索相似定理、语义对齐 |
| Tactic prediction | 预测下一步证明策略 | 序列模型、树搜索、上下文检索 |
| Proof search | 在证明空间中搜索可通过检查的路径 | best-first search、MCTS、verifier-guided search |
| Compiler-guided repair | 根据 Lean 报错修复证明 | 错误定位、局部重写、迭代生成 |

这条路线的关键优势在于：验证不是靠“模型自己觉得对”，而是靠 proof assistant 的 kernel 做机械检查。也正因为如此，形式化证明是通往可靠 AI 数学系统的重要基础设施。

## 七、数学发现：从回答已知题，到提出可验证候选

论文中特别值得注意的一条线，是 AI-assisted mathematical discovery。这里的目标不只是求出已有题目的答案，而是让系统提出新的构造、改进已知边界、找到反例，或者辅助研究者攻击开放问题。

这类系统通常不是单纯靠语言模型完成，而是组合了生成模型、程序搜索、评估函数和验证机制。例如，模型可以生成候选程序或数学对象，外部评估器负责计算分数，系统再把高质量候选反馈给下一轮搜索。

这带来一个重要转变：数学 AI 的输出不一定是一段漂亮解释，而可以是一个可运行程序、一个被检查过的证明、一个满足约束的构造，或者一组带证据的搜索结果。

## 八、训练与推理：验证器正在变成核心组件

这篇综述反复强调一个趋势：数学推理能力的提升，越来越依赖生成模型与验证机制的耦合。

| 技术 | 作用 | 局限 |
| --- | --- | --- |
| Chain-of-thought | 让模型显式展开中间步骤 | 中间步骤可能看似合理但实际错误 |
| Self-consistency | 多次采样后投票 | 需要更多推理成本，投票不等于证明 |
| Tool use | 调用计算器、CAS、Python、检索器 | 工具调用接口和问题分解仍可能出错 |
| Process reward model | 对中间推理步骤打分 | 奖励模型可能学到表面模式 |
| RLVR | 用可验证答案或反馈做强化学习 | 容易受验证器覆盖范围限制，也可能 reward hacking |
| Verifier-assisted pass@k | 生成多个候选，再用验证器筛选 | 分数依赖采样次数和验证器能力 |

我的理解是，AI for Math 正在从“prompt 工程问题”变成“验证基础设施问题”。谁能更好地构造可检查任务、可靠反馈、错误修复和搜索预算，谁就更接近真正可用的数学智能。

## 九、Benchmark 分数应该怎么看？

论文对评价问题的讨论很重要。数学 benchmark 很容易给人一种确定性幻觉：一个模型在某榜单上得分高，似乎就说明它数学能力强。但实际情况复杂得多。

![Evaluation risks in AI mathematical reasoning](/assets/images/ai4math-survey/evaluation-risks.svg)

至少要同时看几个问题。

| 问题 | 为什么重要 |
| --- | --- |
| 是否存在数据污染 | 题目可能已经出现在训练集、网页、解题库或衍生数据里 |
| 是否 benchmark 饱和 | 小学算术和常见竞赛题很快会被模型刷高 |
| 报告的是 pass@1 还是 pass@k | 一次答对和采样一百次后选对不是同一个能力 |
| 是否用了验证器 | verifier-assisted 成绩不能直接和纯生成成绩比较 |
| 推理预算是多少 | 长思考、多轮搜索和工具调用会显著增加成本 |
| 是否测试扰动鲁棒性 | 改写题面、加入无关信息、换语言后模型可能明显退化 |

所以，评价数学推理模型时，不能只问“准确率是多少”，还要问“用了多少次机会、多少计算、什么验证器、什么数据来源、什么失败案例”。

## 十、主要失败模式

论文总结的失败模式，对工程实践很有参考价值。

| 失败模式 | 表现 |
| --- | --- |
| Brittleness under perturbation | 题面轻微改写、条件顺序变化、加入干扰信息后推理崩溃 |
| Reward hacking | 模型学会迎合奖励信号，而不是真正学会数学 |
| Multimodal grounding failure | 图形关系识别错误，导致后续推理全错 |
| Fragile formalization | 自然语言命题翻译到形式语言时语义漂移 |
| Reporting mismatch | 不同论文的采样次数、验证方式、计算预算不可比 |
| Energy cost | reasoning-scale inference 需要大量 token、采样和搜索 |

这些问题说明，数学推理系统的瓶颈并不只在模型参数量，也在数据治理、验证器设计、评测协议和推理成本控制。

## 十一、对 AI Agent 的启发

这篇论文虽然讨论的是数学推理，但对通用 Agent 系统也有直接启发。

第一，复杂任务不能只依赖一次生成。可靠系统需要把任务拆成理解、生成、验证、修复、记录几个阶段。

第二，工具调用不是“外接功能”，而是推理链的一部分。计算器、CAS、Lean、搜索器、代码执行器都可以成为 Agent 的外部认知结构。

第三，证据记录会越来越重要。一个数学 Agent 不仅要给答案，还要保留用了哪些引理、调用了什么工具、哪些候选被验证器拒绝、最终结果为什么可信。

第四，形式化系统为 AI 提供了一种少见的硬反馈。在很多领域，我们只能靠人类偏好或弱标签训练模型；而在数学中，证明检查器和可执行测试可以提供更明确的对错信号。

## 十二、我的判断

这篇综述的核心价值，不在于列举了多少数学 benchmark，而在于把 AI 数学推理重新定义为一个系统工程问题。

从这个视角看，未来几年更值得关注的不是“某个模型在某个数学榜单上又涨了几分”，而是下面几个方向：

| 方向 | 判断 |
| --- | --- |
| 可验证发现 workflow | 生成模型负责提出候选，验证系统负责筛选和修复，这是走向科研辅助的关键 |
| Autoformalization 基础设施 | 如果自然语言数学能更稳定地进入 Lean 生态，AI 数学会得到更可靠的反馈闭环 |
| 推理效率 | 长思考和大规模采样有效，但成本不可忽视，未来需要更聪明的搜索策略 |
| 多模态 grounding | 几何、图表、公式图像仍是数学 AI 的薄弱环节 |
| 评价协议标准化 | 没有统一报告采样预算、验证器和数据来源，分数比较意义有限 |

一句话概括：数学推理正在把 AI 从“会生成答案”推向“能组织可检查的发现过程”。这可能也是它对整个 AI Agent 领域最大的启发。

## 参考链接

1. arXiv 论文页：https://arxiv.org/abs/2606.08728
2. arXiv HTML 版本：https://arxiv.org/html/2606.08728
3. 配套资料仓库：https://github.com/Starscream-11813/awesome-AI4Math
4. Hugging Face Papers 页面：https://huggingface.co/papers/2606.08728
