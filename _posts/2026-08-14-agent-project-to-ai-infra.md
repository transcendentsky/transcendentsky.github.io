---
title: 如何把一个 Agent 项目改造成 AI Infra 求职项目
tags:
  - AI Infra
  - Agent
  - LLMOps
  - Career
---

> 很多 Agent 项目停留在“能调用工具、能回答问题”的 demo 阶段。如果目标是找 AI Infra 相关工作，项目需要展示的重点就不只是 Agent 本身，而是模型服务、调度、可观测性、评估、部署、成本和可靠性。本文给一条改造路线：把一个 Agent 项目升级成可部署、可观测、可评估、可扩展的 Agent Runtime / LLM 应用基础设施项目。

![Agent project to AI infra architecture](/assets/images/agent-to-ai-infra/architecture.svg)

<!--more-->

## 一、先改定位：不要只说“我做了一个 Agent”

如果面试 AI Infra 岗位，项目定位最好从：

```text
我做了一个 Agent，可以调用工具完成任务。
```

升级成：

```text
我做了一套面向 Agent 应用的基础设施，支持多模型路由、本地推理、工具调用、RAG、执行追踪、评估体系、监控指标和容器化部署。
```

这两个表述的差别很大。前者像应用 demo，后者更像工程系统。

AI Infra 面试官真正关心的问题通常是：

| 关注点 | 面试官想看到什么 |
| --- | --- |
| 模型怎么接入 | 是否支持多模型、私有模型、OpenAI-compatible API |
| 服务怎么部署 | 是否有 Docker、环境变量、健康检查、启动文档 |
| 系统怎么观测 | 是否记录 trace、latency、token、错误率、工具调用链 |
| 效果怎么评估 | 是否有 eval cases、回归测试、指标对比 |
| 并发怎么处理 | 是否有异步任务、队列、worker、超时和重试 |
| 成本怎么控制 | 是否有 token 统计、缓存、模型路由、预算限制 |
| 安全怎么考虑 | API key、工具权限、审计日志、敏感信息处理 |

所以，项目要从“功能展示”转向“系统能力展示”。

## 二、整体目标：做成一个 Agent Infra Platform

可以把项目拆成下面几层。

| 模块 | 要体现的 AI Infra 能力 |
| --- | --- |
| Model Gateway | 多模型接入、模型路由、fallback、timeout、retry、token usage |
| Inference Backend | 支持 vLLM、Ollama、云模型、OpenAI-compatible API |
| Agent Runtime | planner、executor、tool calling、状态管理、任务生命周期 |
| RAG / Memory | 文档索引、向量库、检索、rerank、缓存、引用 |
| Evaluation | 任务成功率、工具选择准确率、检索命中率、延迟和成本 |
| Observability | trace、metrics、structured logs、run id、error code |
| Deployment | Docker Compose、环境变量、health check、启动脚本 |
| Security | API key 管理、工具权限、沙箱、审计日志 |
| Cost Control | token 预算、模型选择策略、缓存命中率 |

这不是要求一次性全部做完，而是让项目具备清晰的升级方向。第一版只要把 Model Gateway、vLLM 接入、Trace、Eval、Docker Compose 做扎实，就已经比普通 Agent demo 强很多。

## 三、第一优先级：增加 Model Gateway

Model Gateway 是最值得优先做的模块。它的作用是把所有模型调用收口，避免业务代码到处直接调用 OpenAI、DeepSeek、Qwen、Ollama 或 vLLM。

推荐链路：

```text
Agent -> Model Gateway -> OpenAI / DeepSeek / Qwen / vLLM / Ollama
```

Model Gateway 至少支持：

| 能力 | 说明 |
| --- | --- |
| 多模型配置 | 同一套 Agent 可以切换不同模型后端 |
| fallback | 主模型失败时切换备用模型 |
| timeout | 防止一次模型调用拖死整个任务 |
| retry | 网络抖动或 5xx 时自动重试 |
| streaming | 支持流式输出 |
| token usage | 记录 prompt tokens、completion tokens、总成本 |
| model routing | 简单任务走小模型，复杂任务走强模型 |
| OpenAI-compatible | 兼容 vLLM、Ollama、LiteLLM、各种私有网关 |

配置可以长这样：

```yaml
models:
  default: qwen-local
  providers:
    qwen-local:
      type: openai_compatible
      base_url: http://localhost:8000/v1
      model: qwen2.5-7b
      api_key: ${VLLM_API_KEY}
      timeout_seconds: 60
    deepseek:
      type: openai_compatible
      base_url: https://api.deepseek.com/v1
      model: deepseek-chat
      api_key: ${DEEPSEEK_API_KEY}
      timeout_seconds: 60
```

面试时这块很好讲，因为企业环境里很少允许业务代码直接散落调用不同模型供应商。统一网关是基础设施思维。

## 四、第二优先级：接入 vLLM / Ollama 本地推理

如果目标是 AI Infra，项目最好不要只依赖云 API。至少要支持一种本地或私有化推理后端。

推荐结构：

```text
Agent App -> OpenAI-compatible Client -> vLLM Server -> GPU
```

可以新增：

```text
docker-compose.vllm.yml
configs/model_gateway.yaml
docs/deploy-vllm.md
```

README 里写清楚：

1. 如何启动 vLLM。
2. 如何配置 `base_url`。
3. 如何切换云模型和本地模型。
4. 单卡部署的显存限制。
5. `max-model-len`、`gpu-memory-utilization`、并发参数怎么调。

示例：

```yaml
services:
  vllm:
    image: vllm/vllm-openai:latest
    container_name: agent-vllm
    restart: unless-stopped
    ipc: host
    ports:
      - "8000:8000"
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    command:
      - --model
      - Qwen/Qwen2.5-7B-Instruct
      - --served-model-name
      - qwen2.5-7b
      - --max-model-len
      - "8192"
      - --gpu-memory-utilization
      - "0.90"
```

这块可以让项目具备“私有模型服务化”的含金量。对 AI Infra 岗位来说，这是非常直接的信号。

## 五、第三优先级：增加 Execution Trace

普通 Agent 项目最大的问题是不可解释、不可排查。用户只看到最终回答，但不知道中间发生了什么。

你可以给每次 Agent 执行生成完整 trace：

```json
{
  "run_id": "run_20260814_001",
  "user_query": "分析这份设备故障记录",
  "started_at": "2026-08-14T10:00:00Z",
  "model_calls": [],
  "tool_calls": [],
  "retrievals": [],
  "latency_ms": 2381,
  "token_usage": {
    "prompt_tokens": 2048,
    "completion_tokens": 512,
    "total_tokens": 2560
  },
  "final_answer": "...",
  "error": null
}
```

Trace 至少记录：

| 数据 | 价值 |
| --- | --- |
| run_id | 串起一次完整执行 |
| user_query | 还原输入 |
| model_calls | 记录模型、prompt、latency、tokens、错误 |
| tool_calls | 记录工具名、参数、结果、耗时 |
| retrievals | 记录 query、topK、命中文档、score |
| final_answer | 对照最终输出 |
| error | 排查失败原因 |

如果能在 UI 或日志里展示：

```text
用户问题 -> 规划 -> 检索 -> 工具调用 -> 模型生成 -> 最终答案
```

项目会立刻从 demo 感变成工程系统。

## 六、第四优先级：构建评估系统

AI Infra 项目必须回答一个问题：**你怎么证明系统变好了？**

建议新增：

```text
eval/
  cases.jsonl
  run_eval.py
  reports/
```

每个 case 可以长这样：

```json
{
  "id": "case_001",
  "category": "rag",
  "query": "主变压器油温异常时应该先检查什么？",
  "expected_tool": "search_docs",
  "expected_keywords": ["油温", "负荷", "冷却系统"],
  "expected_doc_ids": ["transformer_ops_003"]
}
```

评估指标建议包括：

| 指标 | 说明 |
| --- | --- |
| task_success_rate | 任务是否完成 |
| tool_accuracy | 工具是否选对 |
| retrieval_hit_rate | RAG 是否命中正确文档 |
| answer_groundedness | 回答是否能被引用内容支持 |
| hallucination_rate | 是否编造 |
| avg_latency | 平均延迟 |
| p95_latency | P95 延迟 |
| avg_token_cost | 平均 token 成本 |

评估系统不一定一开始就非常复杂。第一版可以先做规则评估：关键词、工具名、文档命中、错误率、延迟统计。后续再加入 LLM-as-Judge。

这块的面试价值很高，因为它体现你不是凭感觉调 prompt，而是用指标做系统迭代。

## 七、第五优先级：任务队列和并发执行

如果 Agent 有长任务，建议不要让 HTTP 请求一直同步等待。可以做成：

```text
API Server -> Task Queue -> Agent Worker -> Tool / Model / DB
```

可选技术：

| 技术 | 适合场景 |
| --- | --- |
| Celery + Redis | Python 项目、传统异步任务 |
| RQ / Dramatiq | 简单后台任务 |
| Ray | 多进程、多 GPU、批量推理、Agent 并发 |
| asyncio + worker pool | 轻量服务，依赖较少 |

建议支持：

| 能力 | 说明 |
| --- | --- |
| submit task | 提交 Agent 任务 |
| task status | 查询 pending/running/succeeded/failed |
| cancel | 取消长任务 |
| retry | 失败重试 |
| timeout | 防止任务无限执行 |
| concurrency limit | 控制模型和工具并发 |
| dead letter | 记录最终失败任务 |

这样项目会显得更接近真实生产系统。

## 八、第六优先级：部署和运维能力

至少补齐这些文件和接口：

```text
Dockerfile
docker-compose.yml
.env.example
Makefile
/healthz
/metrics
docs/deployment.md
docs/observability.md
```

推荐服务结构：

```text
docker-compose.yml
  agent-api
  agent-worker
  redis
  postgres
  vector-db
  vllm
  prometheus
  grafana
```

即使不一次性全部实现，也可以先让 `agent-api`、`redis`、`postgres`、`vector-db` 跑起来，再逐步加 vLLM 和监控。

运维侧建议补：

| 能力 | 为什么重要 |
| --- | --- |
| health check | 部署平台需要判断服务是否存活 |
| metrics | 监控 QPS、延迟、错误率、token、工具调用 |
| structured logging | 方便用 run_id 排查问题 |
| config by env | 支持 dev/staging/prod 环境 |
| migration | 数据库 schema 可演进 |
| graceful shutdown | 不中断正在执行的任务 |

这些东西看起来普通，但正是 Infra 岗位最关心的工程底座。

## 九、安全和成本控制

Agent 项目还有两个容易被忽略的问题：工具权限和成本失控。

安全侧建议：

| 项目 | 建议 |
| --- | --- |
| API Key | 不写进代码，不进 Git，使用 `.env` 和 secret manager |
| 工具权限 | 每个工具定义允许动作和参数边界 |
| 文件访问 | 限制目录白名单，避免任意读写 |
| 网络访问 | 对外请求做 domain allowlist |
| 审计日志 | 记录谁在什么时候触发了什么工具 |
| Prompt 注入 | RAG 内容和用户输入要分区，工具调用前做确认 |

成本侧建议：

| 项目 | 建议 |
| --- | --- |
| token budget | 每次 run 设置最大 token 预算 |
| model routing | 简单任务走小模型，复杂任务走强模型 |
| cache | 对 embedding、检索、模型回答做可控缓存 |
| context limit | 限制 RAG 召回长度和历史对话轮数 |
| usage report | 按用户、任务类型、模型统计成本 |

这些不是锦上添花。真实 Agent 系统一旦开放给用户，最先爆的往往就是权限和成本。

## 十、README 应该怎么包装

README 不要只写“项目介绍”和“启动命令”。建议改成面向 AI Infra 招聘的结构。

```text
# Agent Infra Platform

## 项目定位
一个支持多模型路由、RAG、工具调用、任务队列、可观测性和评估体系的 Agent Runtime。

## 核心能力
- OpenAI-compatible Model Gateway
- vLLM / Ollama / Cloud LLM backend
- Agent execution tracing
- RAG pipeline
- Tool permission control
- Evaluation framework
- Docker Compose deployment
- Prometheus metrics

## 架构图

## 快速启动

## 部署本地 vLLM

## 运行评估

## 性能指标

## 未来优化
```

README 的目标不是把所有细节写满，而是让面试官 30 秒看懂：这是一个有工程深度的 AI Infra 项目。

## 十一、简历可以怎么写

可以把项目写成下面这种风格。

| 简历 bullet | 展示能力 |
| --- | --- |
| 设计并实现 Agent Runtime，支持多模型路由、工具调用、RAG 检索和异步任务执行 | Agent 系统设计 |
| 接入 vLLM 本地推理服务，提供 OpenAI-compatible API，支持云模型与私有模型无缝切换 | 推理部署 |
| 实现 Agent execution tracing，记录模型调用、工具调用、检索结果、token 消耗和延迟指标 | 可观测性 |
| 构建 Agent evaluation pipeline，支持任务成功率、工具选择准确率、检索命中率和延迟成本评估 | 评估体系 |
| 使用 Docker Compose 完成端到端部署，提供 health check、metrics 和生产环境配置模板 | 部署运维 |

更完整一点可以写：

```text
基于 FastAPI / LangChain / vLLM 构建 Agent Infra Platform，支持 OpenAI-compatible Model Gateway、多模型 fallback、RAG 检索、工具调用、异步任务队列和执行链路追踪；设计评估集和自动化 eval pipeline，统计任务成功率、检索命中率、工具选择准确率、P95 延迟和 token 成本；使用 Docker Compose 提供本地私有化部署方案，并接入 Prometheus metrics。
```

这比“实现一个基于大模型的智能体项目”强很多。

## 十二、推荐实施路线

![Agent to AI infra roadmap](/assets/images/agent-to-ai-infra/roadmap.svg)

建议按这个顺序做，不要一开始就同时改所有模块。

| 阶段 | 目标 | 交付物 |
| --- | --- | --- |
| 第 1 阶段 | 统一模型调用 | `ModelGateway`、模型配置、fallback、usage 统计 |
| 第 2 阶段 | 接入私有推理 | `docker-compose.vllm.yml`、OpenAI-compatible 配置 |
| 第 3 阶段 | 执行可追踪 | `run_id`、trace schema、trace viewer 或日志 |
| 第 4 阶段 | 效果可评估 | `eval/cases.jsonl`、`run_eval.py`、评估报告 |
| 第 5 阶段 | 服务可部署 | Dockerfile、Compose、healthz、metrics、env config |
| 第 6 阶段 | 求职可展示 | README、架构图、压测结果、简历 bullet、demo |

第一版做到第 4 阶段，就已经有足够多内容可以在面试里展开。第 5、6 阶段则负责把项目从“我自己能跑”变成“别人能看懂、能复现、能评价”。

## 十三、项目优化优先级

可以按下面这个优先级推进。

| 优先级 | 优化项 | 为什么重要 |
| --- | --- | --- |
| P0 | 统一配置管理 | 模型、向量库、API key、部署环境不能硬编码 |
| P0 | LLM 调用抽象 | 支持多模型和本地推理，是 AI Infra 基础 |
| P0 | Docker Compose | 面试官和协作者可以快速跑起来 |
| P1 | Trace 日志 | 展示 Agent 可观测性和排障能力 |
| P1 | Eval 测试集 | 展示系统化优化能力 |
| P1 | RAG 检索优化 | 展示 embedding、chunk、rerank、cache 能力 |
| P2 | 多 worker 并发 | 展示系统扩展能力 |
| P2 | Prometheus metrics | 展示生产运维意识 |
| P2 | CI/CD | 展示工程规范 |
| P3 | K8s / Helm | 如果目标岗位偏平台或云原生，再补充 |

这里的关键是 P0 和 P1。P2、P3 可以锦上添花，但不要在基础还不清楚时过早堆复杂度。

## 十四、面试时怎么讲这个项目

讲项目时建议按“问题、架构、取舍、指标、迭代”五步。

| 维度 | 讲法 |
| --- | --- |
| 问题 | 普通 Agent demo 难部署、难评估、难排障、难扩展 |
| 架构 | 通过 Runtime、Model Gateway、RAG、Eval、Trace、Deployment 拆层 |
| 取舍 | 单机优先、OpenAI-compatible 优先、先规则评估再 LLM Judge |
| 指标 | task success、retrieval hit、tool accuracy、latency、token cost |
| 迭代 | 通过 trace 和 eval 找问题，再调模型、检索、工具和 prompt |

不要只演示“它能回答什么”。要演示：

1. 一次任务的 trace 长什么样。
2. 失败任务怎么定位。
3. 模型怎么从云 API 切到 vLLM。
4. eval 跑完指标如何变化。
5. 服务如何用 Docker Compose 启动。

这才是 AI Infra 项目的面试表达方式。

## 十五、总结

如果你现在已经有一个 Agent 项目，不需要推倒重来。最有效的做法是给它补上基础设施能力：

1. Model Gateway：统一模型调用。
2. vLLM / Ollama：支持本地和私有化推理。
3. Execution Trace：让每次执行可解释、可排查。
4. Eval Pipeline：让优化有指标。
5. Docker Compose：让项目可部署、可复现。
6. Metrics / Logs：让服务可观测。
7. README / 简历包装：让外部人能理解你的工程能力。

把这些补齐之后，这个项目就不只是一个 Agent demo，而是一个能体现 AI Infra 能力的作品集项目。它能覆盖模型服务、Agent Runtime、RAG、评估、可观测性、部署和成本控制，正好对应当前 AI Infra 岗位最常见的面试关注点。
