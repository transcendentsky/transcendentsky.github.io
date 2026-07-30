---
title: Evidence Tracing & Execution Provenance：让 AI Agent 和自动化系统可追踪、可复核、可治理
tags:
  - AI Agent
  - Observability
  - Provenance
  - Software Engineering
---

> 一句话总结：Evidence Tracing 关注“一个结论依据了哪些证据”，Execution Provenance 关注“一个结果是由谁、在什么环境、通过哪些步骤产生的”。前者回答 why，后者回答 how。对 AI Agent、自动化运维、代码生成、数据流水线和实验平台来说，这两者是从 demo 走向可信系统的关键基础设施。

![Evidence Tracing Flow](/assets/images/evidence-provenance/evidence-tracing-flow.svg)

<!--more-->

AI Agent 和自动化系统正在从“辅助生成内容”进入“执行真实任务”的阶段。

它们会读取文档、调用工具、运行命令、修改代码、查询数据库、提交工单、生成报告，甚至触发部署。系统能力变强以后，一个新问题会变得非常关键：

> 当系统给出一个结论，或者执行了一个动作，我们能不能知道它为什么这么做、依据是什么、过程是否可信、结果能不能复现？

这就是 Evidence Tracing 和 Execution Provenance 要解决的问题。

如果没有这两层能力，AI Agent 只能停留在 demo 阶段。它可能看起来很聪明，但一旦进入商业系统、企业内网、医疗金融、电力运维、代码发布等高责任场景，就会遇到几个硬问题：

1. 模型说“设备存在异常”，依据是什么？
2. Agent 修改了一段代码，是基于哪个 issue、哪个文件、哪个测试结果？
3. 自动化流水线生成了一个制品，它用了哪些依赖、配置和环境？
4. RAG 系统回答了一个问题，它引用了哪些文档版本？
5. 线上事故发生后，能不能回放当时的决策链路？
6. 审计人员能不能判断系统有没有越权读取数据？

本文把这两个概念拆开讲清楚，并给出工程落地方式。

## 一、先定义：Evidence 和 Provenance 不一样

这两个词经常被混用，但在系统设计里最好区分。

| 概念 | 关注点 | 回答的问题 |
| --- | --- | --- |
| Evidence Tracing | 证据链 | 这个结论依据了什么？ |
| Execution Provenance | 执行溯源 | 这个结果是怎么产生的？ |

更具体地说：

| 维度 | Evidence Tracing | Execution Provenance |
| --- | --- | --- |
| 核心对象 | claim、evidence、citation、observation | activity、agent、entity、environment |
| 典型问题 | “为什么判断为高风险？” | “谁在什么环境下执行了什么？” |
| 关注结果 | 决策可解释、结论可复核 | 过程可回放、制品可追溯 |
| 常见载体 | 引用、证据片段、检索结果、评测样例 | trace、日志、命令、输入输出、版本 digest |
| 适合场景 | RAG、问答、诊断、风控、报告生成 | CI/CD、Agent 执行、数据流水线、实验平台 |

一句话：

```text
Evidence Tracing 解决“凭什么”。
Execution Provenance 解决“怎么来的”。
```

## 二、为什么现在变得重要？

传统软件里，程序行为通常由开发者写死。只要输入相同、环境相同，结果相对稳定。

AI Agent 不同。

它的行为往往由多种因素共同决定：

1. 用户输入。
2. system prompt。
3. 检索到的上下文。
4. 模型版本。
5. sampling 参数。
6. 工具返回值。
7. 历史记忆。
8. 权限策略。
9. 环境状态。
10. 中间反思和规划步骤。

这意味着同一个表面问题背后可能有很多变量。

如果不记录证据和执行来源，就会出现典型问题：

| 问题 | 后果 |
| --- | --- |
| 只保存最终答案 | 无法复核模型是否引用正确 |
| 只保存日志文本 | 无法结构化查询和关联 |
| 只保存 trace | 不知道每个结论的证据 |
| 只保存 prompt | 不知道工具实际返回什么 |
| 不保存模型版本 | 无法复现结果 |
| 不保存环境和依赖 | 构建制品不可追溯 |
| 不保存权限上下文 | 无法判断是否越权 |

在高责任系统里，“模型答对了”不够，“系统能解释它为什么答对、错了以后能定位原因”才是工程底线。

## 三、Evidence Tracing 具体追什么？

Evidence Tracing 的核心对象是：

```text
Claim -> Evidence -> Source -> Confidence -> Decision
```

一个 claim 可以是：

1. “这台变压器可能存在局部放电风险。”
2. “这个 PR 没有破坏兼容性。”
3. “这份合同存在付款期限异常。”
4. “用户请求应该路由到退款流程。”
5. “模型 A 比模型 B 更适合当前任务。”

每个 claim 都应该能关联证据。

证据可以来自：

| 证据类型 | 示例 |
| --- | --- |
| 原始文档 | PDF、Markdown、网页、标准条文 |
| 数据记录 | 传感器数据、订单记录、交易流水 |
| 检索结果 | RAG top-k chunk、rerank 分数 |
| 工具返回 | API response、SQL 查询、命令输出 |
| 测试结果 | 单元测试、E2E 测试、评测报告 |
| 人工标注 | 审核意见、专家判断 |
| 历史案例 | 相似故障、历史工单 |

Evidence Tracing 不要求保存所有原始内容。更合理的方式是保存：

1. source id。
2. source version。
3. evidence span 或 chunk id。
4. evidence digest。
5. retrieval score。
6. 使用证据生成的 claim。
7. claim confidence。
8. 人工复核状态。

一个简单结构：

```json
{
  "claim_id": "claim_20260730_001",
  "claim": "该设备存在局部放电风险",
  "evidence": [
    {
      "source_type": "sensor_record",
      "source_id": "oil_chromatography_20260730",
      "source_version": "v3",
      "span": "C2H2=12.3ppm, H2=320ppm",
      "digest": "sha256:...",
      "score": 0.91
    },
    {
      "source_type": "standard_doc",
      "source_id": "dl_t_722",
      "chunk_id": "chunk_118",
      "score": 0.84
    }
  ],
  "confidence": 0.78,
  "decision": "建议人工复核并追加局放检测"
}
```

## 四、Execution Provenance 具体追什么？

Execution Provenance 更像执行账本。

它记录：

```text
Agent + Activity + Entity + Environment + Time + Policy + Output
```

这和 W3C PROV 的基本思想一致。PROV 家族把 provenance 建模为 entity、activity、agent 等对象之间的关系，用来表达“某个东西由哪些活动、实体和代理产生”。

在软件系统里，可以映射成：

| PROV 思路 | 工程对象 |
| --- | --- |
| Agent | 用户、服务账号、模型、流水线、Agent |
| Activity | 工具调用、命令执行、训练任务、构建任务 |
| Entity | 输入文件、输出报告、模型权重、构建制品 |
| wasGeneratedBy | 产物由哪个任务生成 |
| used | 任务用了哪些输入 |
| wasAssociatedWith | 任务由哪个主体发起 |

![Execution Provenance Model](/assets/images/evidence-provenance/provenance-model.svg)

一个 Agent 修改代码的 provenance 可以是：

```json
{
  "execution_id": "exec_20260730_001",
  "actor": {
    "type": "ai_agent",
    "name": "code-review-agent",
    "model": "claude-sonnet-4-5"
  },
  "trigger": {
    "type": "github_issue",
    "id": "issue_182",
    "user": "alice"
  },
  "activity": {
    "type": "code_edit",
    "repo": "payment-service",
    "commit_before": "a12c...",
    "commit_after": "b93f..."
  },
  "inputs": [
    {"path": "src/payment/refund.py", "digest": "sha256:..."},
    {"path": "tests/test_refund.py", "digest": "sha256:..."}
  ],
  "outputs": [
    {"path": "src/payment/refund.py", "digest": "sha256:..."}
  ],
  "commands": [
    {"cmd": "pytest tests/test_refund.py", "exit_code": 0}
  ],
  "policy": {
    "approval_required": true,
    "approved_by": "alice"
  },
  "environment": {
    "python": "3.11.9",
    "os": "ubuntu-22.04",
    "container": "sha256:..."
  }
}
```

这份记录的价值在于：几个月后你仍然可以回答这个改动怎么来的。

## 五、Trace、Log、Provenance 的关系

很多系统已经有日志和链路追踪。那 provenance 还需要单独做吗？

需要，但不要重复造轮子。

| 类型 | 主要用途 | 典型工具 |
| --- | --- | --- |
| Trace | 看一次请求经过哪些组件 | OpenTelemetry、Jaeger、Tempo |
| Log | 记录事件和错误细节 | ELK、Loki、CloudWatch |
| Metric | 看系统状态和趋势 | Prometheus、Grafana |
| Provenance | 解释结果和制品来源 | PROV、SLSA、in-toto、自定义元数据 |
| Evidence | 支撑结论可复核 | citation、chunk、digest、source version |

OpenTelemetry 官方把 traces、metrics、logs、baggage 作为主要 telemetry signals。它适合记录执行链路和上下文传播。

但 OpenTelemetry trace 默认不一定知道：

1. 某个结论引用了哪个文档 chunk。
2. 某个模型输出基于哪个 prompt template。
3. 某个制品使用了哪些依赖 digest。
4. 某个 Agent 决策是否经过人工审批。

所以更合理的方式是：

1. 用 OpenTelemetry 记录执行路径。
2. 用结构化日志记录关键事件。
3. 用 evidence/provenance schema 记录可复核事实。
4. 用 trace id 把它们关联起来。

## 六、在 AI Agent 系统里怎么落地？

一个 Agent 执行任务时，至少有这些阶段：

1. 接收任务。
2. 读取上下文。
3. 规划步骤。
4. 调用工具。
5. 观察结果。
6. 修改状态或文件。
7. 运行验证。
8. 输出结论。

每一步都应该记录证据和 provenance。

| 阶段 | Evidence | Provenance |
| --- | --- | --- |
| 接收任务 | 用户需求、issue、ticket | 请求 ID、用户 ID、时间 |
| 读取上下文 | 文件片段、文档 chunk | 文件版本、权限上下文 |
| 规划步骤 | 计划依据、风险判断 | 模型版本、prompt 版本 |
| 调用工具 | 工具返回值、错误码 | tool name、参数、耗时 |
| 修改文件 | diff、测试结果 | commit before/after、命令 |
| 输出结论 | 引用、置信度、限制 | run id、审批状态 |

关键原则：

1. 每次 Agent run 有唯一 `run_id`。
2. 每个 tool call 有唯一 `tool_call_id`。
3. 每个结论有 `claim_id`。
4. 每个 claim 关联 evidence。
5. 每个 output 关联 activity。
6. 每个 activity 记录 actor、policy、environment。

## 七、RAG 系统里的 Evidence Tracing

RAG 是最典型的 Evidence Tracing 场景。

一个可信 RAG 系统不能只返回答案，还应该返回：

1. 引用文档。
2. 文档版本。
3. chunk id。
4. 检索分数。
5. rerank 分数。
6. 最终 prompt 中实际使用了哪些 chunk。
7. 模型是否忠实于证据。

推荐记录：

```json
{
  "query_id": "q_001",
  "query": "保单等待期是多少天？",
  "retrieval": {
    "embedding_model": "bge-m3",
    "index_version": "policy_docs_v7",
    "top_k": 8
  },
  "evidence_used": [
    {
      "doc_id": "policy_a",
      "doc_version": "2026-06",
      "chunk_id": "chunk_42",
      "score": 0.88,
      "used_in_prompt": true
    }
  ],
  "answer": "该产品等待期为 90 天。",
  "faithfulness_check": "pass"
}
```

如果 RAG 答错了，这份记录能定位：

| 错误位置 | 可能原因 |
| --- | --- |
| 没检索到正确文档 | embedding 或索引问题 |
| 检索到了但没使用 | rerank 或 prompt 拼接问题 |
| 使用了正确证据但答错 | 模型生成问题 |
| 文档版本过旧 | 数据同步问题 |
| 引用了无权限文档 | 权限过滤问题 |

没有 evidence tracing，RAG 失败只能靠猜。

## 八、代码生成系统里的 Execution Provenance

代码生成和自动修复系统更需要 provenance。

因为它们会改变代码库。

每次自动修改至少记录：

| 字段 | 说明 |
| --- | --- |
| task id | issue、ticket、用户请求 |
| repo state | branch、commit、dirty state |
| model | 模型名、版本、参数 |
| prompt version | system prompt、工具描述版本 |
| files read | 读取了哪些文件 |
| files changed | 修改了哪些文件 |
| commands run | 测试、lint、build |
| approvals | 哪些操作经过确认 |
| output commit | 最终 commit 或 patch digest |

这能回答：

1. Agent 有没有读不该读的文件？
2. Agent 修改是基于哪个版本？
3. 测试是否真的运行过？
4. 失败命令有没有被忽略？
5. 最终 patch 是否被人工确认？
6. 上线事故能不能追到具体自动化 run？

## 九、数据流水线和模型训练里的 Provenance

数据和模型训练天然需要 provenance。

一个模型不是一个孤立文件，它来自：

1. 原始数据。
2. 清洗脚本。
3. 数据版本。
4. 训练代码。
5. 训练配置。
6. base model。
7. tokenizer。
8. 依赖版本。
9. 硬件环境。
10. 随机种子。

如果没有 provenance，你不知道模型能力变化来自哪里。

建议每次训练记录：

```json
{
  "model_artifact": "domain-lora-v3",
  "base_model": "Qwen2.5-7B-Instruct",
  "dataset_version": "sft_v12",
  "dataset_digest": "sha256:...",
  "training_code_commit": "abc123",
  "config_digest": "sha256:...",
  "framework": "xtuner",
  "metrics": {
    "eval_score": 0.82,
    "format_follow_rate": 0.96
  },
  "artifact_digest": "sha256:..."
}
```

这和 SLSA provenance 的理念相通：构建产物应该记录构建者、输入材料、参数、环境和元数据。软件供应链里这样做是为了防篡改和可验证；AI 模型训练里同样需要。

## 十、最小可用的数据模型

不要一上来设计复杂 ontology。实际落地可以从四张表开始。

### 1. executions

记录一次执行。

| 字段 | 说明 |
| --- | --- |
| execution_id | 全局唯一 ID |
| actor_id | 用户、服务或 Agent |
| task_type | code_edit、rag_answer、train_model |
| started_at / ended_at | 时间 |
| status | success、failed、cancelled |
| trace_id | OpenTelemetry trace id |
| model | 模型名称 |
| policy_version | 权限策略版本 |

### 2. activities

记录执行中的步骤。

| 字段 | 说明 |
| --- | --- |
| activity_id | 步骤 ID |
| execution_id | 所属执行 |
| type | tool_call、command、retrieval、decision |
| input_digest | 输入摘要 |
| output_digest | 输出摘要 |
| exit_code | 命令退出码 |
| latency_ms | 耗时 |

### 3. evidence_items

记录证据。

| 字段 | 说明 |
| --- | --- |
| evidence_id | 证据 ID |
| source_type | doc、log、db、api、file |
| source_id | 来源 ID |
| source_version | 来源版本 |
| span_ref | chunk、line range、row id |
| digest | 内容摘要 |
| score | 相关性或置信度 |

### 4. claims

记录结论。

| 字段 | 说明 |
| --- | --- |
| claim_id | 结论 ID |
| execution_id | 所属执行 |
| claim_text | 结论 |
| confidence | 置信度 |
| evidence_ids | 证据列表 |
| reviewer_status | pending、approved、rejected |

这套模型足以覆盖大多数 Agent、RAG、自动化执行和模型训练场景。

## 十一、完整性和防篡改

如果只是把记录写到普通日志里，审计价值有限。

关键记录应该具备：

1. 时间戳。
2. 不可变 ID。
3. 内容 digest。
4. append-only 存储。
5. 权限隔离。
6. 保留周期。
7. 必要时签名。

对高风险系统，可以做 hash chain：

```text
record_hash_n = sha256(record_n + record_hash_n-1)
```

这样可以发现中间记录被篡改。

对于构建制品、模型权重、发布包，可以记录：

1. artifact digest。
2. provenance file。
3. builder identity。
4. source commit。
5. build parameters。
6. signature。

这类机制和 in-toto、SLSA 的供应链安全思路一致。

## 十二、不要保存过多敏感内容

Evidence tracing 很容易走向另一个极端：什么都保存。

这会带来新风险：

1. 日志里出现密钥。
2. prompt 里包含客户数据。
3. evidence span 泄露隐私。
4. 审计系统变成新的敏感数据仓库。
5. 长期保存不符合合规要求。

正确策略是：

| 数据 | 建议 |
| --- | --- |
| 完整 prompt | 默认不长期保存，或脱敏加密 |
| 代码片段 | 保存引用和 digest，必要时短期留存 |
| 文档证据 | 保存 doc id、chunk id、version |
| API 返回 | 保存结构化摘要和 digest |
| 用户隐私 | 脱敏或不落盘 |
| 密钥 token | 永不记录 |

原则是：

> 保存能复核结论的最小充分证据，而不是把所有上下文永久归档。

## 十三、测试 Evidence 和 Provenance

这类能力也需要测试。

测试清单：

| 测试项 | 验证什么 |
| --- | --- |
| trace id 贯穿 | 一次请求能串起日志、trace、evidence |
| claim 有 evidence | 关键结论不能没有证据 |
| evidence 可解析 | source id、chunk id、version 有效 |
| digest 正确 | 内容摘要能校验 |
| 权限上下文存在 | 记录执行时的权限策略 |
| 失败也记录 | 异常路径不丢 provenance |
| 敏感信息过滤 | token、password 不进入日志 |
| replay 测试 | 能用记录复现关键执行 |
| 审计查询 | 能按用户、项目、模型、时间检索 |

尤其要测失败路径。

很多系统只在成功时记录完整信息，一旦工具超时、命令失败、权限拒绝，记录就断了。真正需要审计的往往正是这些异常场景。

## 十四、一个推荐落地路线

如果从零开始建设，不要一次做太复杂。

### 阶段一：结构化记录

目标：

1. 每次执行有 run/execution id。
2. 每个工具调用有 activity id。
3. 日志里有 trace id。
4. 关键输入输出有 digest。

### 阶段二：证据关联

目标：

1. RAG 答案记录 chunk id。
2. 诊断结论记录 evidence id。
3. 代码修改记录文件版本和测试结果。
4. 报告生成记录数据源版本。

### 阶段三：可查询审计

目标：

1. 按用户查执行。
2. 按模型查输出。
3. 按文档查引用。
4. 按制品查构建来源。
5. 按失败类型查异常。

### 阶段四：完整性保护

目标：

1. 关键记录 append-only。
2. 重要制品签名。
3. provenance 文件随制品发布。
4. 高风险操作保留审批链。

![Audit Loop](/assets/images/evidence-provenance/audit-loop.svg)

## 十五、总结

Evidence Tracing 和 Execution Provenance 不是为了让系统看起来更复杂，而是为了让系统在出错、争议、审计和复盘时仍然可解释。

它们分别回答：

| 问题 | 能力 |
| --- | --- |
| 这个结论依据什么？ | Evidence Tracing |
| 这个结果怎么产生？ | Execution Provenance |
| 哪个模型做的？ | Provenance |
| 用了哪些文档和数据？ | Evidence + Provenance |
| 是否越权？ | Provenance + Policy Context |
| 能否复现？ | Provenance + Artifact Digest |
| 是否可信？ | Evidence + Verification |

对 AI Agent 来说，这不是锦上添花，而是进入真实生产场景的前提。

一个系统如果只会输出答案，但不能解释证据；只会执行动作，但不能追溯来源；只会记录日志，但不能复核结论，那么它最多是一个有用 demo，还不是一个可治理的工程系统。

参考：

1. [W3C PROV Namespace](https://www.w3.org/ns/prov)
2. [W3C PROV-O: The PROV Ontology](https://www.w3.org/TR/prov-o/)
3. [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
4. [OpenTelemetry Signals](https://opentelemetry.io/docs/concepts/signals/)
5. [SLSA Provenance Specification](https://slsa.dev/spec/v1.0/provenance)
