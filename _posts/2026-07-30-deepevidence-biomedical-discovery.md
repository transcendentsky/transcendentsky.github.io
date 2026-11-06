---
title: DeepEvidence：用深度知识图谱研究加速生物医学发现
tags:
  - AI Agent
  - Biomedical AI
  - Knowledge Graph
  - Deep Research
---

> 原论文题目：**DeepEvidence: Empowering Biomedical Discovery with Deep Knowledge Graph Research**。这篇工作提出了一个面向生物医学知识图谱的 deep research agent，通过广度优先研究、深度优先研究和动态 evidence graph，把异构生物医学知识库、文献和临床试验证据组织成可追踪、可复核的研究过程。

![DeepEvidence architecture](/assets/images/deepevidence/architecture.svg)

<!--more-->

## 一、论文基本信息

这篇论文有两个需要区分的题名。

| 项目 | 信息 |
| --- | --- |
| arXiv 题名 | **DeepEvidence: Empowering Biomedical Discovery with Deep Knowledge Graph Research** |
| Nature Machine Intelligence 正式版题名 | **Empowering biomedical evidence exploration and synthesis with deep knowledge graph research** |
| arXiv 编号 | arXiv:2601.11560 |
| arXiv 提交时间 | 2025 年 12 月 23 日 |
| 正式发表 | Nature Machine Intelligence, volume 8, pages 1142-1156, 2026 |
| 发表日期 | 2026 年 7 月 2 日 |
| DOI | 10.1038/s42256-026-01266-0 |
| 代码 | https://github.com/RyanWangZf/BioDSA/tree/main/biodsa/agents/deepevidence |
| 数据集 | https://huggingface.co/datasets/zifeng-ai/DeepEvidence |

作者与单位如下。

| 作者 | 单位 |
| --- | --- |
| Zifeng Wang | Keiji AI, Seattle, WA, USA |
| Zheng Chen | Institute of Scientific and Industrial Research, Osaka University, Osaka, Japan |
| Ziwei Yang | Bioinformatics Center, Institute for Chemical Research, Kyoto University, Kyoto, Japan |
| Xuan Wang | Institute of Scientific and Industrial Research, Osaka University, Osaka, Japan |
| Qiao Jin | Division of Intramural Research, National Library of Medicine, National Institutes of Health, Bethesda, MD, USA |
| Yifan Peng | Department of Population Health Sciences, Weill Cornell Medicine, New York, NY, USA |
| Zhiyong Lu | Division of Intramural Research, National Library of Medicine, National Institutes of Health, Bethesda, MD, USA |
| Jimeng Sun | Keiji AI, Seattle, WA, USA; School of Computing and Data Science, University of Illinois Urbana-Champaign, Urbana, IL, USA |

通讯作者为 Zifeng Wang 和 Jimeng Sun。

## 二、这篇论文要解决什么问题？

生物医学研究依赖大量知识源：

1. 文献数据库。
2. 药物数据库。
3. 基因和蛋白数据库。
4. 通路和功能注释。
5. 疾病和表型知识库。
6. 临床试验数据库。
7. FDA、OpenTargets、ChEMBL、KEGG、Gene Ontology 等专业资源。

这些知识源很有价值，但问题也很明确：

| 难点 | 具体表现 |
| --- | --- |
| 异构性强 | 每个数据库 schema、API、实体命名都不同 |
| 更新频繁 | 文献、临床试验、药物信息持续变化 |
| 跨库对齐困难 | 同一个药物、基因、疾病在不同库里名称和 ID 不一致 |
| 推理链路长 | 很多问题需要多跳关系和证据综合 |
| 人工成本高 | 专家需要反复查库、查文献、整合证据 |

通用 Deep Research Agent 通常主要依赖互联网文本和网页搜索。DeepEvidence 的出发点不同：它认为生物医学发现不能只靠文本搜索，必须深入结构化知识图谱，在不同 KG 之间追踪实体、关系和证据。

## 三、DeepEvidence 的核心思想

DeepEvidence 是一个面向异构生物医学知识图谱的 AI-agent framework。

它的核心不是让 LLM 直接回答医学问题，而是让 Agent 有策略地探索多个知识图谱和文献资源，再把探索过程组织成 evidence graph。

系统有三个关键组件：

| 组件 | 作用 |
| --- | --- |
| Orchestrator | 负责理解问题、规划研究路径、调度子 Agent |
| BFRS Agent | Breadth-First ReSearch，广度探索多个 KG，发现候选实体和桥接关系 |
| DFRS Agent | Depth-First ReSearch，沿关键实体做多跳证据追踪和深层推理 |
| Evidence Graph | 增量记录实体、关系、观察和支持证据 |
| Execution Sandbox | 支持 Agent 编写和运行程序，批量调用 API、抽取和分析数据 |

论文的一个关键贡献是把“图探索策略”嵌入到 deep research agent 中。

这比普通 RAG 更进一步：

```text
普通 RAG：检索文档 -> 拼 prompt -> 生成答案
DeepEvidence：规划研究策略 -> 跨 KG 搜索实体 -> 多跳追踪证据 -> 构建 evidence graph -> 合成答案
```

## 四、BFRS 和 DFRS：为什么需要两种研究策略？

DeepEvidence 提出两个互补策略：BFRS 和 DFRS。

![BFRS and DFRS strategies](/assets/images/deepevidence/bfrs-dfrs.svg)

### BFRS：Breadth-First ReSearch

BFRS 负责“先把面铺开”。

它会围绕一个疾病、药物、基因或通路，在多个知识图谱中做广度搜索，快速找到候选实体和一跳关系。

例如针对一个疾病问题，BFRS 可能同时查询：

1. disease-drug graph。
2. gene-disease graph。
3. pathway annotation。
4. clinical trial records。
5. FDA drug references。

它的价值是提高覆盖面，避免 Agent 过早陷入某条局部路径。

### DFRS：Depth-First ReSearch

DFRS 负责“沿关键线索深入”。

当 BFRS 找到重要实体后，DFRS 会沿这些实体做多跳探索：

1. 某个基因和疾病之间是否有机制关系？
2. 这个靶点是否在相关通路里？
3. 是否有药物作用于这个靶点？
4. 临床试验中是否验证过相关机制？
5. 文献引用链是否支持这个结论？

它的价值是构建更深的证据链，而不是停留在表层检索。

论文中特别强调，这里的 BFRS/DFRS 不是传统图算法里的固定 BFS/DFS。它们是 Agent 选择研究步骤的策略：Agent 会根据问题、证据和当前 evidence graph 动态决定下一步查什么。

## 五、Evidence Graph：这篇论文最值得关注的设计

DeepEvidence 的内部 evidence graph 很关键。

它不是简单的聊天历史，也不是一堆检索结果列表，而是一个逐步构建的研究记忆：

| 内容 | 作用 |
| --- | --- |
| 关键实体 | 疾病、药物、基因、蛋白、通路、试验 |
| 实体关系 | drug-target、gene-disease、pathway involvement |
| 证据来源 | 文献、KG API、临床试验、FDA 资料 |
| 中间观察 | Agent 在研究过程中得到的发现 |
| 支撑链路 | 哪些证据支持哪个结论 |

这个设计解决了 deep research 中一个核心问题：研究过程必须可追踪。

如果 Agent 只输出最终答案，很难判断它是不是幻觉、是不是漏掉重要证据、是不是引用了错误数据库。Evidence graph 让中间实体、关系、证据和结论变成可检查对象。

这也和近期 AI Agent 工程里的两个方向高度一致：

1. Evidence Tracing：结论必须能回到证据。
2. Execution Provenance：结果必须能回到执行过程。

## 六、系统使用了哪些生物医学知识源？

论文中提到 DeepEvidence 集成了多类生物医学资源，包括但不限于：

| 类型 | 示例 |
| --- | --- |
| 文献和出版物 | PubTator、PubMed Knowledge Graph |
| 通路和功能注释 | KEGG、Gene Ontology |
| 靶点和疾病关联 | OpenTargets |
| 化学和药物注释 | ChEMBL、BioThings |
| 药物监管信息 | OpenFDA |
| 临床试验 | Clinical trial records |

DeepEvidence 的价值不只是“能调很多 API”，而是把这些 API 组织成统一的实体搜索、数据获取和证据抽取接口。

这对生物医学特别重要。因为同一个研究问题往往必须跨越多个层次：

```text
Disease -> Gene -> Pathway -> Drug -> Trial -> Evidence
```

单一知识库很难覆盖完整链路。

## 七、评测结果：DeepEvidence 好在哪里？

论文首先在四个开放 benchmark 上比较了 DeepEvidence 和通用 LLM/生物医学 Agent。

| Benchmark | DeepEvidence 表现 |
| --- | --- |
| HLE-Medicine | 40.0% |
| LabBench-LitQA2 | 80.0% |
| SuperGPQA-Medicine-Hard | 47.1% |
| TrialPanorama-EvidenceQA | 96.0% |

论文报告 DeepEvidence 在这些 benchmark 上超过了多个强基线，包括 GPT-5、Sonnet-4.5、Biomni 和 ToolUniverse 等。

更重要的是，作者还构建了面向生物医学发现生命周期的任务。

![Biomedical discovery lifecycle tasks](/assets/images/deepevidence/biomedical-lifecycle.svg)

这些任务覆盖：

1. 药物发现。
2. 临床前实验。
3. 临床试验开发。
4. 循证医学。

## 八、各阶段任务如何体现 DeepEvidence 的价值？

### 1. 药物发现：target identification

目标识别任务要求 Agent 根据疾病背景，综合基因、通路、 biomarker 和既往研究证据，识别有潜力的治疗或诊断靶点。

论文中 DeepEvidence 达到 68% accuracy，高于 Biomni、ToolUniverse 和通用 LLM 基线。

这类任务需要跨库对齐和机制推理。只查几篇文献很容易漏掉关键靶点，而只查一个 KG 又可能证据不足。

### 2. 临床前实验：mechanistic reasoning

临床前任务包括：

1. 通路级机制解释。
2. 药物机制和 biomarker 解读。
3. transcriptomic 或 phosphoproteomic 数据解释。
4. 代谢通量响应预测。

论文显示 DeepEvidence 在机制推理和 in vivo metabolic flux response 任务中都明显优于基线。

原因是它能把通路、靶点、实验观察和文献证据组织到同一条证据链里。

### 3. 临床试验开发：sample size、regimen、surrogate endpoint

临床试验设计需要查历史研究、药物组合、安全性、剂量限制毒性、治疗周期、替代终点等信息。

论文设计了三个任务：

| 任务 | 目标 |
| --- | --- |
| sample size estimation | 推断合理样本量 |
| drug regimen design | 选择给药和剂量递增策略 |
| surrogate endpoint discovery | 判断候选替代终点是否有机制支持 |

DeepEvidence 在这些任务上的优势来自系统化证据搜索，而不是直接凭模型记忆猜答案。

### 4. 循证医学：evidence gap detection

循证医学需要不断更新系统综述和临床证据。新的随机对照试验可能改变既有结论，因此发现 evidence gap 很重要。

论文中的 EBM 任务要求 Agent 找出原系统综述中尚未纳入、但应该被纳入的新临床试验。

DeepEvidence 的 gap detection rate 达到 90.0%，高于 Biomni、ToolUniverse 和 PubMed-search LLM。

这个结果很能体现 evidence graph 的价值：Agent 不是只搜索关键词，而是围绕疾病、治疗类别、突变人群、纳入标准和引用网络重建证据景观。

## 九、为什么普通 Agent 做不好？

论文对比了 Biomni、ToolUniverse 等通用生物医学 Agent。它们也有很多工具，但表现不如 DeepEvidence。

核心原因包括：

| 问题 | 影响 |
| --- | --- |
| 工具多但缺少研究策略 | 容易工具选择错误 |
| 搜索较浅 | 只做少量查询就回答 |
| 缺少 evidence graph | 中间发现难以组织和复用 |
| 跨库桥接不足 | 很难从疾病跳到基因、药物、试验 |
| 证据综合弱 | 难以把异构证据变成机制解释 |

这说明在专业科研场景里，“给 LLM 一堆工具”是不够的。

真正有效的 agent 需要：

1. 领域化工具接口。
2. 明确研究策略。
3. 中间证据结构。
4. 可追踪推理过程。
5. 面向任务的 benchmark。

## 十、这篇论文对 AI Agent 设计的启发

DeepEvidence 的意义不只在生物医学。

它给所有专业领域 Agent 一个很清楚的设计范式：

```text
领域知识源
  -> 统一工具接口
  -> 研究策略
  -> 中间证据结构
  -> 证据合成
  -> 可追踪输出
```

这比“LLM + 搜索 API + prompt”更接近可用的科研系统。

对电力、金融、法律、工业运维等领域，也可以迁移同样思路：

| 生物医学 DeepEvidence | 其他领域对应物 |
| --- | --- |
| biomedical KG | 行业知识图谱 |
| PubMed / trials | 行业文档 / 案例库 |
| BFRS | 广泛搜索候选实体 |
| DFRS | 沿关键实体深挖证据 |
| evidence graph | 可复核证据链 |
| execution sandbox | 可控工具执行环境 |

## 十一、局限性

论文也指出了一些限制。

第一，知识源覆盖仍然不完整。生物医学知识库非常多，DeepEvidence 当前集成的只是其中一部分。

第二，系统依赖相对稳定、结构化、API 质量较高的知识库。真实企业或实验室内部知识图谱往往存在缺失值、不一致 schema 和接口不稳定问题。

第三，BFRS/DFRS 虽然比普通浅层搜索强，但未必是最优研究策略。未来可能需要 Agent 自动学习更好的探索策略。

第四，目前主要关注文本和结构化知识，尚未充分扩展到影像、结构生物学、蛋白组学等多模态数据。

第五，DeepEvidence 在许多任务上还没有达到专家水平。它更适合作为加速证据探索和辅助研究的系统，而不是替代专家判断。

## 十二、我的判断

我认为这篇论文最有价值的地方，不是某一个 benchmark 分数，而是它把 biomedical deep research agent 的工程结构讲清楚了。

它至少给出三个重要判断：

1. 专业领域 Agent 不能只依赖互联网文本，需要领域知识图谱和专业工具。
2. 工具数量不是关键，研究策略和证据组织才是关键。
3. Evidence graph 是科研 Agent 从“会搜索”走向“可验证研究”的关键中间结构。

这和我之前写的 Evidence Tracing & Execution Provenance 是同一条技术主线：未来真正能进入生产和科研核心流程的 Agent，必须不仅能回答，还要能说明证据；不仅能执行，还要能追踪过程。

DeepEvidence 展示的不是一个简单问答系统，而是一个“能在生物医学知识网络中开展结构化研究”的 agent 架构。

## 参考链接

1. [arXiv: DeepEvidence: Empowering Biomedical Discovery with Deep Knowledge Graph Research](https://arxiv.org/abs/2601.11560)
2. [Nature Machine Intelligence: Empowering biomedical evidence exploration and synthesis with deep knowledge graph research](https://www.nature.com/articles/s42256-026-01266-0)
3. [Hugging Face Dataset: zifeng-ai/DeepEvidence](https://huggingface.co/datasets/zifeng-ai/DeepEvidence)
4. [GitHub Code: BioDSA DeepEvidence](https://github.com/RyanWangZf/BioDSA/tree/main/biodsa/agents/deepevidence)
