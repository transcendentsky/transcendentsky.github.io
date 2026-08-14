---
title: 【模型自进化】SAGA：让科学发现智能体学会自主演化目标
tags:
  - 模型自进化
  - Scientific Discovery
  - Agent
  - AI for Science
---

> 原论文题目：**Accelerating Scientific Discovery with Autonomous Goal-evolving Agents**。这篇论文提出 SAGA：Scientific Autonomous Goal-evolving Agent。它真正有意思的地方，不是又做了一个能搜索分子或蛋白的 Agent，而是把“目标函数本身”也放进智能体的演化闭环里：当固定 reward 被优化器钻空子时，Agent 能分析失败模式、提出新目标、实现新评分函数，再继续搜索候选解。

![SAGA bi-level goal-evolving architecture](/assets/images/model-self-evolution-saga/saga-architecture.svg)

<!--more-->

## 一、论文基本信息

| 项目 | 信息 |
| --- | --- |
| 原论文题目 | Accelerating Scientific Discovery with Autonomous Goal-evolving Agents |
| 框架名称 | SAGA：Scientific Autonomous Goal-evolving Agent |
| arXiv 编号 | arXiv:2512.21782 |
| DOI | 10.48550/arXiv.2512.21782 |
| 领域 | AI for Science、Agent、科学发现、多目标优化 |
| 首次提交 | 2025 年 12 月 25 日 |
| 最新版本 | v2，2026 年 3 月 30 日 |
| 代码 | https://github.com/btyu/SAGA |
| 代码许可证 | MIT License |
| 论文链接 | https://arxiv.org/abs/2512.21782 |
| HTML 版本 | https://arxiv.org/html/2512.21782 |

作者阵容很大，论文在 arXiv v2 中列出 28 位作者。

| 作者 | 单位 |
| --- | --- |
| Yuanqi Du | Cornell University |
| Botao Yu | The Ohio State University |
| Tianyu Liu | Yale University |
| Tony Shen | Simon Fraser University |
| Junwu Chen | École Polytechnique Fédérale de Lausanne |
| Jan G. Rittig | École Polytechnique Fédérale de Lausanne |
| Kunyang Sun | University of California Berkeley |
| Yikun Zhang | Northeastern University；Broad Institute of MIT and Harvard |
| Aarti Krishnan | Broad Institute of MIT and Harvard；MIT；Wyss Institute；Whitehead Institute |
| Yu Zhang | Broad Institute of MIT and Harvard；MIT；Wyss Institute |
| Daniel Rosen | Broad Institute of MIT and Harvard；Brigham and Women’s Hospital；Dana-Farber Cancer Institute |
| Rosali Pirone | Broad Institute of MIT and Harvard |
| Zhangde Song | Deep Principle |
| Bo Zhou | University of Illinois Chicago |
| Cassandra Masschelein | École Polytechnique Fédérale de Lausanne |
| Yingze Wang | University of California Berkeley |
| Haorui Wang | Georgia Institute of Technology |
| Haojun Jia | Deep Principle |
| Chao Zhang | Georgia Institute of Technology |
| Hongyu Zhao | Yale University |
| Martin Ester | Simon Fraser University |
| Nir Hacohen | Broad Institute of MIT and Harvard；Massachusetts General Hospital |
| Teresa Head-Gordon | University of California Berkeley |
| Carla P. Gomes | Cornell University |
| Huan Sun | The Ohio State University |
| Chenru Duan | Deep Principle |
| Philippe Schwaller | École Polytechnique Fédérale de Lausanne |
| Wengong Jin | Northeastern University；Broad Institute of MIT and Harvard |

## 二、这篇论文解决的核心问题

很多科学发现系统的默认范式是：

```text
科学家定义目标函数 -> 优化器最大化目标函数 -> 得到候选分子/蛋白/材料
```

问题在于，科学里的目标函数经常只是现实目标的代理变量。比如药物设计里，模型可以优化“预测活性”，但高预测活性并不等于真的可合成、低毒、稳定、有新颖性、能穿透细胞膜。优化器越强，越容易 exploit 这些代理指标的漏洞。

这篇论文的核心判断是：**科学发现 Agent 的瓶颈不只是“怎么优化候选解”，而是“怎么持续发现和修正应该优化什么”。**

也就是说，过去很多系统做的是 solution optimization；SAGA 想做的是 objective evolution。

| 传统科学优化 Agent | SAGA 的目标演化 Agent |
| --- | --- |
| 目标函数由科学家预先写死 | 目标函数可以被 Agent 持续修正 |
| 优化器只负责找高分候选 | Agent 还要分析高分候选为什么不可靠 |
| reward 是输入 | reward 也变成搜索对象 |
| 容易被 proxy reward 欺骗 | 通过新 objective 补上失败模式 |
| 更像“自动优化工具” | 更像“会反思目标的科学合作者” |

这正是我觉得它值得放进“模型自进化”系列的原因：它不是让模型参数自己更新，而是让 Agent 的任务目标、评价函数、搜索方向和实验策略持续演化。

## 三、SAGA 的双层架构

SAGA 采用 bi-level architecture，分成外层目标演化和内层候选优化。

### 1. 外层：Objective Evolution

外层由多个 LLM Agent 模块构成，负责分析当前优化结果，提出新的目标函数，并把目标函数变成可执行评分器。

| 模块 | 作用 |
| --- | --- |
| Planner | 把高层科学目标拆成可度量 objective，并根据进展提出新 objective |
| Implementer | 把 Planner 提出的 objective 转换为可执行 scoring function |
| Analyzer | 分析当前候选解分布、失败模式和优化瓶颈 |
| Optimizer 接口 | 接收当前 objectives，并驱动内层候选搜索 |

论文里的关键变化是：目标不再是固定输入，而是一个可以被 Planner 和 Analyzer 迭代修正的对象。

### 2. 内层：Solution Optimization

内层仍然是传统意义上的优化：给定当前评分函数，搜索更好的候选解。这个优化器可以是遗传算法、强化学习搜索、分子生成模型、序列设计器，也可以是某个领域已有的优化算法。

可以理解为：

```text
外层负责“想清楚该优化什么”
内层负责“在当前目标下尽可能优化候选解”
```

这点非常重要。SAGA 不是替代所有领域优化器，而是在它们之上加了一个目标演化层。

## 四、三种自动化模式

SAGA 支持三种人机协作水平。

| 模式 | 人类参与 | 适合场景 |
| --- | --- | --- |
| Co-pilot | 科学家同时参与 Planner 和 Analyzer | 高风险、早期探索、专家需要深度控制 |
| Semi-pilot | 科学家只给 Analyzer 输出反馈 | 需要专家把关，但希望目标规划自动化 |
| Autopilot | Planner 和 Analyzer 全自动 | 成熟任务、批量探索、低成本初筛 |

这个设计比“全自动科学家”更现实。很多科学任务里，人类专家不应该被完全移出闭环；更好的形态是让系统在不同风险等级下调整自动化程度。

我的理解是：

| 任务阶段 | 推荐模式 |
| --- | --- |
| 新问题定义 | Co-pilot |
| 已有基础实验数据，但目标还不稳定 | Semi-pilot |
| 已验证过目标空间和评价器 | Autopilot |
| 大规模批量筛选 | Autopilot + 人类抽检 |

## 五、五类科学任务验证

论文不是只在一个 toy benchmark 上验证，而是覆盖了五类科学设计任务。

![SAGA scientific applications map](/assets/images/model-self-evolution-saga/domain-map.svg)

| 任务 | SAGA 做了什么 | 论文中的关键结果 |
| --- | --- | --- |
| 抗生素设计 | 设计针对 E. coli 的新候选分子 | 合成测试 28 个候选；4 个化合物在 128 μg/mL + PMB 下显示超过 80% 生长抑制；其中 compound 8 在 MIC 下对 HEK293 和 HepG2 细胞毒性较低 |
| 纳米抗体设计 | 设计 PD-L1 de novo binders | 实验验证 3 个新纳米抗体结合 PD-L1，K_D 约 300-400 nM |
| 功能 DNA 序列设计 | 设计细胞类型特异 enhancer | HepG2 场景相对最佳 baseline 接近 50% 提升 |
| 无机材料设计 | 设计低供应链风险永磁体和超硬材料 | 用 DFT 等计算方法验证候选性质 |
| 化工流程设计 | 自动生成 chemical process flowsheet | 展示目标演化可以迁移到流程设计空间 |

这里需要注意，论文最强的证据来自两个有实验验证的任务：抗生素设计和纳米抗体设计。DNA、材料和化工流程任务更多依赖计算评估与领域指标。

## 六、抗生素设计：为什么目标演化有用

抗生素设计是一个很典型的多目标问题。你不能只要“预测活性高”，还要考虑：

| 目标 | 为什么重要 |
| --- | --- |
| 活性 | 对目标细菌有效 |
| 安全性 | 对人类细胞低毒 |
| 新颖性 | 不只是已知抗生素附近的小修小补 |
| drug-likeness | 更接近真实药物候选 |
| 可合成性 | 后续实验和开发可行 |
| 代谢稳定性 | 避免体内快速失效 |

论文指出，固定目标优化容易出现一个问题：候选分子可能在主目标上得分高，但在药物化学质量上很差。SAGA 的 Analyzer 会分析候选群体的分布，发现例如高活性与 drug-likeness 之间的负相关，或者 top molecules 中反复出现不理想结构片段。

然后 Planner 会提出新的 objective，比如代谢稳定性评分、自定义 drug-likeness filter 等。Implementer 再把这些目标变成可执行评分函数，重新喂给 Optimizer。

这就是目标演化的价值：不是一次性把所有规则写进去，而是在优化过程中发现“当前目标缺了什么”。

实验层面，论文合成并测试了 SAGA 设计的 28 个候选分子，其中 4 个在 128 μg/mL、结合 PMB 的条件下显示超过 80% 的 E. coli 生长抑制。进一步测试中，compound 8 在 MIC 条件下对 HEK293 和 HepG2 两类人类细胞显示较低细胞毒性，并且与已知抗生素的 Tanimoto similarity 只有 0.28。

这不能直接说明它已经是可用抗生素，但足以说明 SAGA 可以找到有实验信号的新颖 hit。

## 七、纳米抗体设计：目标组合比单一指标更关键

纳米抗体设计也很适合 SAGA，因为它天然是多目标优化：

| 目标 | 例子 |
| --- | --- |
| 结合能力 | ipTM、interface confidence、接触面积 |
| 稳定性 | pLDDT、结构置信度 |
| 界面质量 | 氢键、盐桥、ΔSASA |
| 序列合理性 | ProteinMPNN score、sequence recovery |
| developability | 聚集风险、可表达性、序列性质 |

论文在 PD-L1 纳米抗体设计中比较了 SAGA、BoltzGen、Germinal 等方法。SAGA 在多个指标上达到或超过 baseline，并且 oracle calls 数量约为后两者的 1/2 到 1/5。

更关键的是，SAGA 会根据失败模式修正 objective。比如 Semi-pilot 模式下，人类专家发现 CDR3 区域稳定性不足，SAGA 随后提出提高 pLDDT 权重、引入 alpha-helix secondary structure constraint 等策略。

最终实验验证发现 3 个 de novo PD-L1 binders，K_D 约 300-400 nM。论文还指出，SAGA 演化出的 composite scoring function 对 binder / non-binder 的区分显著性优于若干单独 in silico metric。

这说明它不是简单“多塞几个指标”，而是在寻找更有效的目标组合。

## 八、为什么这篇论文属于“模型自进化”

严格说，SAGA 并不是参数级 self-improvement。它没有让 foundation model 自己训练自己，也没有直接更新 LLM 权重。

但它体现了另一类更实用的自进化：**系统级自进化**。

| 自进化层级 | SAGA 是否涉及 | 说明 |
| --- | --- | --- |
| 参数自进化 | 否 | 没有更新 LLM 参数 |
| Prompt / plan 自进化 | 是 | Planner 会随迭代修改目标和策略 |
| Reward / objective 自进化 | 是 | 这是 SAGA 的核心 |
| Tool / scorer 自生成 | 是 | Implementer 把目标变成可执行评分函数 |
| Search policy 自适应 | 部分是 | Optimizer 在新 objective 下继续搜索 |
| Human feedback 自融合 | 是 | Co-pilot 和 Semi-pilot 支持专家反馈 |

从工程视角看，它提示我们：很多 Agent 的下一步进化，不一定是直接训练更大模型，而是让 Agent 拥有“改写评价标准”的能力。

普通 Agent 的闭环是：

```text
任务 -> 计划 -> 执行 -> 输出
```

SAGA 式 Agent 的闭环是：

```text
任务 -> 初始目标 -> 执行 -> 分析失败 -> 修改目标 -> 再执行
```

这一步很关键。因为真实世界里的目标往往一开始就不完整。

## 九、这篇论文的贡献

我认为可以概括为四点。

### 1. 把 objective design 明确提升为科学发现 Agent 的核心问题

过去很多系统默认目标函数已知，SAGA 则指出：目标函数本身就是一个需要搜索的空间。

这对 AI for Science 很重要，因为科学任务经常不是“优化已知函数”，而是“不断发现什么函数才接近真实目标”。

### 2. 提出双层目标演化架构

外层 Agent 负责目标规划、目标实现和结果分析；内层 optimizer 负责候选解搜索。这个分层很清楚，也方便迁移到不同领域。

### 3. 支持不同自动化等级

Co-pilot、Semi-pilot、Autopilot 三种模式让它比纯自动化叙事更可信。科学发现不是所有场景都适合完全自动。

### 4. 进行了跨领域验证

抗生素、纳米抗体、DNA、材料、化工流程五个任务覆盖了不同候选空间和评价方式，说明 SAGA 不是只为某一个任务手工定制的流程。

## 十、局限性和需要谨慎的地方

这篇论文很有启发，但也不能过度解读。

| 局限 | 说明 |
| --- | --- |
| 目标函数质量仍依赖工具和领域知识 | Implementer 生成的 scoring function 是否正确，需要专家和实验验证 |
| 实验验证成本高 | 抗生素和纳米抗体有湿实验结果，但规模仍是早期验证 |
| Agent 可能生成不可靠目标 | 如果 Analyzer 判断错，Planner 可能把搜索带偏 |
| LLM 代码生成存在风险 | scoring function 的实现需要 sandbox、测试和审计 |
| 多目标权重仍然复杂 | 目标越多，trade-off 越难解释 |
| 不能替代科学家 | 更合理的定位是增强专家，而不是自动完成发现全流程 |

尤其要注意一点：目标演化能力越强，越需要审计和可追溯。否则 Agent 不仅可能生成错误候选，还可能生成错误评价标准。

## 十一、对 Agent 系统设计的启发

SAGA 不只适用于科学发现。它对通用 Agent 系统也有启发。

| SAGA 组件 | 通用 Agent 中的对应能力 |
| --- | --- |
| Planner | 任务拆解、目标规划、策略调整 |
| Implementer | 工具生成、代码生成、评估器生成 |
| Optimizer | 候选方案搜索、执行器、仿真器 |
| Analyzer | 结果反思、失败归因、指标分析 |
| Objective Evolution | 自适应 reward、动态评价标准 |

如果把它迁移到工程 Agent，可以得到类似模式：

```text
写代码 Agent：
初始目标：通过测试
执行后发现：覆盖率不足、性能退化、异常分支没测
目标演化：增加 coverage、latency、memory、security checks
再执行：生成补充测试和优化补丁
```

或者迁移到 AI Infra：

```text
部署优化 Agent：
初始目标：降低平均延迟
执行后发现：P95 变差、GPU 利用率下降、成本上升
目标演化：加入 P95、吞吐、成本、错误率作为复合目标
再执行：调整 batch、cache、routing、replica 策略
```

所以，SAGA 的真正价值是提供了一种 Agent 自进化模板：**让 Agent 不只做任务，还能改进自己判断任务好坏的标准。**

## 十二、如果要复现或借鉴，可以怎么做

开源仓库显示，SAGA 包含核心框架、共享模块、DNA design、小分子药物设计实验、LLM 配置和 run logs。

仓库结构大致包括：

| 目录 | 作用 |
| --- | --- |
| `scileo_agent/` | SAGA 核心框架 |
| `modules/shared/` | Planner、Analyzer、Scorer Creator、Selector 等共享模块 |
| `modules/dna_design/` | DNA 序列设计相关模块 |
| `modules/small_molecule_drug_design/` | 小分子药物设计模块 |
| `llm_configs/` | 模型和凭证配置模板 |
| `exps/` | DNA 和抗生素设计实验入口 |
| `runs/` | 运行时生成日志和结果 |

如果自己做一个简化版本，可以先不碰复杂湿实验，而是选一个工程化任务：

1. 定义一个初始优化目标。
2. 让 Agent 生成候选方案。
3. 用 Analyzer 分析失败样本。
4. 让 Planner 提出新评价指标。
5. 让 Implementer 写出可执行 scorer。
6. 重新排序或优化候选方案。
7. 保存每轮 objective、score、候选和失败归因。

关键不是任务多复杂，而是要保留“目标如何变化”的 trace。

## 十三、总结

《Accelerating Scientific Discovery with Autonomous Goal-evolving Agents》这篇论文的核心信息可以压缩成一句话：

**真正强的科学发现 Agent，不应该只是优化人类给定的目标，而应该能在探索过程中发现目标本身的不完整，并主动演化新的评价标准。**

SAGA 的价值在于把科学发现里的一个隐性过程显式化了：科学家本来就会在看到实验结果后不断调整评价标准，只是过去这个过程高度依赖人工经验。SAGA 试图把这件事 Agent 化、模块化、可记录化。

对“模型自进化”这条线来说，它提供了一个很务实的方向：不一定先追求模型参数自更新，而是先让系统具备目标自修正、评估器自生成、失败模式自诊断和搜索策略自适应能力。这样的自进化更容易落地，也更接近真实科研和工程系统中的迭代方式。

## 参考资料

- arXiv 论文页面：https://arxiv.org/abs/2512.21782
- arXiv HTML 版本：https://arxiv.org/html/2512.21782
- SAGA GitHub 仓库：https://github.com/btyu/SAGA
- OpenReview 记录：https://openreview.net/
