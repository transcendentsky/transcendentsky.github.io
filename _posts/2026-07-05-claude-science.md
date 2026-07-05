---
title: Claude Science 工作流整理
tags:
  - AI for Science
  - Agent
  - Claude
---

# Claude Science 工作流整理

## 1. 总体理解

Claude Science 可以理解为一个面向科研任务的 **“总控 Agent + 专家 Agent + 工具/数据库/代码环境 + 审核与溯源”** 的科研工作台。

它不是简单的问答工具，而是把科研任务拆成一系列可执行、可追踪、可复跑、可审核的流程。

<!--more-->

---

## 2. 整体工作流

```text
用户提出科研目标
    ↓
Generalist coordinating agent 理解任务、拆解计划
    ↓
选择 specialist / skill / connector
    ↓
读取本地文件、数据库、论文、实验记录
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

核心思想是：  
**不是让模型直接给答案，而是让模型围绕科研目标组织工具链、执行分析、保存过程、接受复核。**

---

## 3. 关键角色分工

### 3.1 Generalist Coordinating Agent：总控协调者

这是用户交互的入口。用户通常不需要指定每一步，只需要提出科研目标。

例如：

> 帮我分析这批单细胞数据，完成 QC、聚类、UMAP、细胞类型初步注释，并生成报告。

总控 Agent 负责：

```text
理解任务目标
↓
判断任务类型：单细胞 / 蛋白结构 / 化学信息学 / 文献综述 / 基因组分析
↓
选择合适的 specialist 或 skill
↓
决定需要哪些数据、工具、数据库和代码环境
↓
执行或调度执行
```

它相当于科研流程中的“项目经理 + 技术调度器”。

---

### 3.2 Specialist Agents：领域专家执行者

Specialist agents 是具体执行任务的领域专家 Agent。

可能包括：

```text
single-cell specialist
genomics specialist
proteomics specialist
structural biology specialist
cheminformatics specialist
```

这些 specialist 更像是“带工具链的领域分析员”。  
例如：

- single-cell specialist 可能会调用 Scanpy、scvi-tools、10x Genomics 相关工具；
- structural biology specialist 可能会调用蛋白结构预测、结构渲染、OpenFold/Boltz 等模型；
- cheminformatics specialist 可能会调用分子表示、性质预测、分子筛选等工具。

它们的价值在于：  
**不同科研任务不再由同一个通用 Agent 硬做，而是由更贴近领域工具链的 specialist 执行。**

---

### 3.3 Skills：可复用科研流程

Skill 可以理解为一套标准化、可复用的科研操作流程。

例如：

```text
single-cell-rna-qc
nextflow-development
scvi-tools
scientific-problem-selection
instrument-data-to-allotrope
```

Skill 不是简单 prompt，而是可能包含：

- 任务说明；
- 执行步骤；
- 脚本；
- 工具调用方式；
- 资源文件；
- 结果检查规范；
- 领域最佳实践。

例如 `single-cell-rna-qc` 这类 skill 可能负责：

```text
读取单细胞数据
↓
计算 QC 指标
↓
执行过滤
↓
生成可视化
↓
输出 filtered h5ad / metrics.csv / report.html
```

Skill 的意义在于：  
**把科研中的常见流程沉淀成可复用模块，而不是每次都从零规划。**

---

### 3.4 Connectors / MCP：连接外部数据与工具

Claude Science 的工作流依赖外部连接器，用来访问科研数据库、实验平台和计算工具。

典型连接对象包括：

```text
PubMed：文献检索
Wiley Scholar Gateway：同行评审文献
Benchling：实验记录、notebook、实验数据
BioRender：科学图示
Synapse：科研数据共享与分析
10x Genomics：单细胞和空间组学分析
Databricks / Snowflake：大规模数据处理
```

因此它的核心不是“Claude 自己什么都知道”，而是：

```text
Claude 判断要做什么
↓
通过 connector 找数据 / 找文献 / 调工具
↓
通过代码环境执行分析
↓
通过 provenance 记录过程
```

这也是科研 Agent 真正落地的关键：  
**大模型负责理解、规划和调度；外部系统负责提供数据、工具和执行能力。**

---

## 4. 以单细胞 RNA-seq 分析为例

一个典型 Claude Science 工作流可能如下：

```text
1. 用户上传 raw_feature_matrix.h5 或 h5ad 文件

2. Claude 判断这是 single-cell RNA-seq 任务

3. 调用 single-cell-rna-qc skill

4. 检查数据格式、样本信息、基因数量、细胞数量

5. 执行 QC：
   - 计算 n_genes_by_counts
   - total_counts
   - pct_counts_mt
   - doublet 检查
   - MAD-based filtering

6. 生成可视化：
   - QC violin plot
   - UMAP
   - clustering
   - marker gene heatmap

7. 输出文件：
   - filtered h5ad
   - metrics.csv
   - QC report.html
   - 图表

8. reviewer 检查：
   - 图表是否由代码生成
   - 数字是否能追溯到数据
   - 报告结论是否过度解释

9. 用户修改阈值或追问：
   - “线粒体比例阈值改成 15% 重跑”
   - “帮我比较不同 cluster 的 marker”
   - “生成论文 Methods 部分”
```

这个例子体现了 Claude Science 的核心特征：

> 它不是一次性回答，而是围绕真实科研数据不断执行、修改、复现和解释。

---

## 5. 与普通 Claude / ChatGPT 的区别

### 5.1 普通问答模式

```text
用户问问题
↓
模型回答
```

这种模式适合解释概念、写作、总结和讨论。

---

### 5.2 Claude Science 模式

```text
用户给科研目标
↓
模型拆任务
↓
调专业技能
↓
调数据库
↓
写代码
↓
运行代码
↓
生成结果
↓
记录 provenance
↓
审核结果
↓
支持复跑
```

它更接近：

```text
科研版 Claude Code
+ Jupyter Notebook
+ MCP 工具连接
+ 领域专家 Agent
+ 可复现 artifact 管理
+ reviewer 检查机制
```

所以 Claude Science 的关键变化是：

| 维度 | 普通大模型问答 | Claude Science |
|---|---|---|
| 输入 | 问题 / 指令 | 科研目标 / 数据 / 文件 |
| 输出 | 文本回答 | 图表、代码、报告、文件、分析结果 |
| 执行方式 | 主要靠模型生成 | 模型 + 工具 + 代码环境 |
| 可靠性 | 依赖模型本身 | 依赖执行结果、溯源和审核 |
| 复现性 | 较弱 | 强调 provenance 和 artifacts |
| 适用场景 | 泛知识问答 | 真实科研流程 |

---

## 6. 它真正重要的工作流思想

Claude Science 的重点不是“一个超级智能体自动发现科学”，而是采用更务实的科研工作流结构：

```text
自然语言任务入口
↓
任务规划
↓
领域 skill 选择
↓
数据和工具连接
↓
代码执行
↓
结果 artifact 化
↓
provenance 追踪
↓
reviewer 审核
↓
人类专家确认
```

这套结构的核心价值在于：

1. **把科研任务流程化**  
   从“模型回答问题”转变为“模型组织科研流程”。

2. **把领域经验模块化**  
   用 skill 沉淀标准流程和最佳实践。

3. **把外部工具系统化**  
   通过 connector / MCP 接入数据库、平台、模型和代码环境。

4. **把结果可追溯化**  
   每一步产生的代码、参数、数据来源和结果都可记录。

5. **把人类专家放在审核环节**  
   Agent 负责加速流程，人类负责科学判断和最终确认。

---

## 7. 对医疗 AI / 自动科研 Agent 的启发

Claude Science 的工作流可以迁移到医学影像科研助手。

例如：

```text
医生提出临床科研问题
↓
Agent 帮忙转成研究假设
↓
检索 PubMed / 指南 / 既往文献
↓
连接病例库、影像库、报告库
↓
筛选队列
↓
调用分割 / 检测 / 分类模型
↓
做统计分析
↓
生成表格、图、Methods、Results
↓
检查数据来源、统计代码、引用和结论
↓
医生确认后迭代
```

如果面向医疗影像，可以进一步细化为：

```text
临床问题提出
↓
研究设计生成
↓
纳排标准制定
↓
病例队列筛选
↓
DICOM / PACS / 报告解析
↓
影像分割、检测、分类模型调用
↓
影像组学 / 深度特征提取
↓
统计分析与可视化
↓
论文草稿生成
↓
专家审核与复跑
```

---

## 8. 可借鉴的产品架构

如果设计一个类似 Claude Science 的医学科研工作台，可以采用以下架构：

```text
用户层
- 医生
- 研究生
- 科研秘书
- PI
- 临床研究团队

交互层
- 自然语言任务入口
- 研究目标澄清
- 流程状态展示
- 人工审核节点

总控 Agent 层
- 任务理解
- 研究设计规划
- specialist 选择
- 工具调度
- 结果整合

Specialist Agent 层
- 文献综述 Agent
- 队列筛选 Agent
- 医学影像分析 Agent
- 统计分析 Agent
- 论文写作 Agent
- 合规审查 Agent

Skill 层
- PubMed 检索 skill
- 临床研究方案 skill
- DICOM 解析 skill
- 影像分割 skill
- 生存分析 skill
- ROC / AUC 统计 skill
- 论文 Methods 写作 skill

Connector 层
- PubMed
- 医院 HIS / LIS / EMR
- PACS
- 数据库
- Python / R
- 影像模型服务
- 文献管理工具

Artifact 层
- 代码
- 图表
- 表格
- 统计结果
- 论文草稿
- 审核记录
- provenance
```

---

## 9. 一句话总结

Claude Science 的工作流不是“模型直接给答案”，而是：

> **总控 Agent 把科研任务拆成一系列可执行、可追踪、可复跑、可审核的工具链流程。**

它真正值得借鉴的是：  
**专业工具连接 + 可复用技能 + 可追溯流程 + 领域数据接入 + 人类专家审核。**
