---
title: Claude Science 的工作流：科研智能体如何协同工作
tags:
  - AI for Science
  - Agent
  - Claude
---

Claude Science 的工作流可以理解成一个 **“总控 Agent + 专家 Agent + 工具/数据库/代码环境 + 审核与溯源”** 的科研工作台。

它不是简单地问答，而是把科研任务拆成可执行流程。

<!--more-->

## 一、整体工作流

大概是这样：

```
用户提出科研目标    
↓
Generalist coordinating agent 理解任务、拆解计划    ↓选择 specialist / skill / connector    ↓读取本地文件、数据库、论文、实验记录    
↓
生成并运行 Python / R / shell / pipeline    
↓
产出图表、表格、模型结果、报告    
↓
保存 artifacts + provenance    
↓
Reviewer agent 检查引用、计算、图表和代码一致性    
↓
用户审阅、追问、修改、复跑
```

官方文档的描述是：用户用自然语言描述研究任务，Claude 会写并运行 Python、R 或 shell 代码，在 sandbox 中执行，读取用户授权的文件夹，通过 connector 拉取科学数据库数据，并把结果保存成带完整 provenance 的版本化 artifacts。还有 background reviewer 用来检查 Claude 的说法是否和实际运行结果一致。[![](https://www.google.com/s2/favicons?domain=https://claude.com&sz=128)Claude](https://claude.com/docs/claude-science/overview?utm_source=chatgpt.com)

---

## 二、关键角色分工

### 1）Generalist coordinating agent：总控协调者

这是入口。用户不是直接指定每一步，而是说一个目标，例如：

> 帮我分析这批单细胞数据，完成 QC、聚类、UMAP、细胞类型初步注释，并生成报告。

总控 Agent 会做几件事：

```
理解任务目标↓判断任务类型：单细胞 / 蛋白结构 / 化学信息学 / 文献综述 / 基因组分析↓选择合适的 specialist 或 skill↓决定需要哪些数据、工具、数据库和代码环境↓执行或调度执行
```

Anthropic 官方说，用户会和一个 generalist coordinating agent 交互，它有 60+ curated skills 和 connectors，覆盖 genomics、single-cell、proteomics、structural biology、cheminformatics 等方向，并且可以拉起其他 specialist agents，也可以使用用户自己创建的 specialist agents。[![](https://www.google.com/s2/favicons?domain=https://www.anthropic.com&sz=128)Anthropic](https://www.anthropic.com/news/claude-science-ai-workbench?utm_source=chatgpt.com)

---

### 2）Specialist agents：领域专家执行者

这些是具体干活的专家 Agent，比如：

```
single-cell specialistgenomics specialistproteomics specialiststructural biology specialistcheminformatics specialist
```

它们更像是“带工具链的领域分析员”。例如 single-cell specialist 可能会调用 Scanpy、scvi-tools、10x Genomics 相关工具；structural biology specialist 可能会调用蛋白结构预测、结构渲染或 OpenFold/Boltz 一类模型。

Claude Science 官方页面提到，它会为每个 specialist 管理计算环境，并保存每个结果的完整 provenance；内置的分析 specialist 包括 genomics、single-cell、proteomics、structural biology、cheminformatics 等。[![](https://www.google.com/s2/favicons?domain=https://claude.com&sz=128)Claude](https://claude.com/product/claude-science?utm_source=chatgpt.com)

---

### 3）Skills：可复用流程

Skill 可以理解为一套“标准化科研操作流程”。例如：

```
single-cell-rna-qcnextflow-developmentscvi-toolsscientific-problem-selectioninstrument-data-to-allotrope
```

这些不是简单 prompt，而是包含说明、脚本、资源、执行规范的流程包。Anthropic 的 life-sciences marketplace 说明，MCP servers 负责连接外部服务，Skills 负责提供特定领域的工作流和分析能力。[![](https://www.google.com/s2/favicons?domain=https://github.com&sz=128)GitHub](https://github.com/anthropics/life-sciences?utm_source=chatgpt.com)

比如 `single-cell-rna-qc` 这个 skill 的功能是对 `.h5ad` 或 `.h5` 单细胞 RNA-seq 数据做质量控制，使用 scverse 最佳实践、MAD-based filtering 和综合可视化。[![](https://www.google.com/s2/favicons?domain=https://github.com&sz=128)GitHub](https://github.com/anthropics/life-sciences/blob/main/single-cell-rna-qc/SKILL.md?utm_source=chatgpt.com)

---

### 4）Connectors / MCP：连接外部数据与工具

Claude Science 的工作流依赖外部连接器，包括：

```
PubMed：文献检索Wiley Scholar Gateway：同行评审文献Benchling：实验记录、notebook、实验数据BioRender：科学图示Synapse：科研数据共享与分析10x Genomics：单细胞和空间组学分析Databricks / Snowflake：大规模数据处理
```

Anthropic 介绍 Claude for Life Sciences 时提到，这些 connectors 让 Claude 能直接访问科研平台和工具，例如 PubMed、Benchling、BioRender、Synapse.org、10x Genomics 等。[![](https://www.google.com/s2/favicons?domain=https://www.anthropic.com&sz=128)Anthropic](https://www.anthropic.com/news/claude-for-life-sciences?utm_source=chatgpt.com)

所以它的工作流核心不是“Claude 自己什么都知道”，而是：

```
Claude 判断要做什么↓通过 connector 找数据 / 找文献 / 调工具↓通过代码环境执行分析↓通过 provenance 记录过程
```

---

## 三、以“单细胞 RNA-seq 分析”为例

一个典型工作流可能是：

```
1. 用户上传 raw_feature_matrix.h5 或 h5ad 文件2. Claude 判断这是 single-cell RNA-seq 任务3. 调用 single-cell-rna-qc skill4. 检查数据格式、样本信息、基因数量、细胞数量5. 执行 QC：   - 计算 n_genes_by_counts   - total_counts   - pct_counts_mt   - doublet 检查   - MAD-based filtering6. 生成可视化：   - QC violin plot   - UMAP   - clustering   - marker gene heatmap7. 输出文件：   - filtered h5ad   - metrics.csv   - QC report.html   - 图表8. reviewer 检查：   - 图表是否由代码生成   - 数字是否能追溯到数据   - 报告结论是否过度解释9. 用户修改阈值或追问：   - “线粒体比例阈值改成 15% 重跑”   - “帮我比较不同 cluster 的 marker”   - “生成论文 Methods 部分”
```

这个例子很能体现 Claude Science 的本质：**它不是一次性回答，而是围绕数据反复执行、修改、复现。**

---

## 四、它和普通 Claude / ChatGPT 的区别

普通 Claude 更像：

```
用户问问题↓模型回答
```

Claude Science 更像：

```
用户给科研目标↓模型拆任务↓调专业技能↓调数据库↓写代码↓运行代码↓生成结果↓记录 provenance↓审核结果↓支持复跑
```

所以它更接近：

```
科研版 Claude Code+ Jupyter Notebook+ MCP 工具连接+ 领域专家 Agent+ 可复现 artifact 管理+ reviewer 检查机制
```

Anthropic 也把 Claude Science 类比为可以在本地 macOS/Linux、远程机器、SSH 或 HPC login node 上使用的工作环境，类似科研人员已有的计算环境，而不是单纯网页聊天。[![](https://www.google.com/s2/favicons?domain=https://www.anthropic.com&sz=128)Anthropic](https://www.anthropic.com/news/claude-science-ai-workbench?utm_source=chatgpt.com)

---

## 五、我认为它真正重要的工作流思想

对你做医疗 AI / 自动科研 Agent 很有启发。它不是追求“一个超级智能体自动发现科学”，而是采用比较务实的结构：

```
自然语言任务入口↓任务规划↓领域 skill 选择↓数据和工具连接↓代码执行↓结果 artifact 化↓provenance 追踪↓reviewer 审核↓人类专家确认
```

这套模式可以迁移到医学影像科研助手：

```
医生提出临床科研问题↓Agent 帮忙转成研究假设↓检索 PubMed / 指南 / 既往文献↓连接病例库、影像库、报告库↓筛选队列↓调用分割/检测/分类模型↓做统计分析↓生成表格、图、Methods、Results↓检查数据来源、统计代码、引用和结论↓医生确认后迭代
```

一句话概括：**Claude Science 的工作流不是“模型直接给答案”，而是“总控 Agent 把科研任务拆成一系列可执行、可追踪、可复跑、可审核的工具链流程”。**
