---
title: 个人轻量 AI Infra（六）：配套工具篇
tags:
  - AI Infra
  - RAG
  - Monitoring
  - Developer Tools
---

> 一句话总结：Ray、MLflow、XTuner、vLLM/LMDeploy 是个人 AI Infra 的主干；Chroma/FAISS、Prometheus/Grafana、Jupyter、Ollama 则是配套工具层。它们不一定最显眼，但决定你的系统能不能顺手开发、稳定运行、快速试错和持续迭代。

![个人 AI Infra 配套工具总览](/assets/images/personal-ai-infra-tools/tools-overview.svg)

<!--more-->

这个系列前面几篇已经讲完了主干组件：

1. Ray：调度任务和资源。
2. MLflow：记录实验和模型资产。
3. LMDeploy/vLLM：提供高性能推理服务。
4. XTuner：执行 LoRA/QLoRA 微调。

这篇讲最后一层：**配套工具**。

所谓配套工具，不是说它们不重要，而是说它们通常不站在系统主链路的中心，却会显著影响你的日常效率。

个人 AI Infra 里最常见的配套工具包括：

| 工具 | 主要用途 |
| --- | --- |
| Chroma | 本地 RAG 向量库，适合快速开发 |
| FAISS | 高性能向量索引，适合自己控制检索逻辑 |
| Prometheus | 指标采集和时序存储 |
| Grafana | 监控看板和可视化 |
| Jupyter | 数据处理、实验分析、原型开发 |
| Ollama | 快速拉起本地模型，验证 prompt 和 demo |

如果把个人 AI Infra 比作一台工作站，主干工具让它“能训练、能推理、能记录”，配套工具则让它“好用、可观察、可迭代”。

## 一、配套工具层的定位

配套工具层解决四类问题：

| 问题 | 推荐工具 |
| --- | --- |
| 本地知识库怎么检索？ | Chroma / FAISS |
| GPU、显存、服务延迟怎么看？ | Prometheus / Grafana |
| 实验原型怎么快速验证？ | Jupyter |
| 小模型和 prompt 怎么快速试？ | Ollama |

它们和前面几篇的关系是：

| 主干组件 | 配套工具怎么补充 |
| --- | --- |
| Ray | Ray 调任务，Jupyter/Ray Dashboard 看结果和调试 |
| MLflow | MLflow 记实验，Jupyter 做分析和报表 |
| vLLM/LMDeploy | 推理服务跑模型，Prometheus/Grafana 看性能 |
| XTuner | XTuner 训练模型，MLflow/Jupyter 分析 loss 和 bad cases |
| RAG/Agent | Chroma/FAISS 提供检索记忆，Ollama 快速试 prompt |

个人 AI Infra 的关键不是工具越多越好，而是每个工具只做自己擅长的事。

## 二、Chroma：快速搭本地 RAG 的向量库

Chroma 是一个偏应用友好的向量数据库，适合快速构建本地 RAG。

它的优点：

1. 上手简单。
2. Python API 友好。
3. 支持本地持久化。
4. 适合 notebook、demo、个人知识库。
5. 元数据过滤比较方便。

安装：

```bash
pip install -U chromadb
```

一个最小例子：

```python
import chromadb

client = chromadb.PersistentClient(path="./rag_store/chroma")
collection = client.get_or_create_collection("personal_ai_docs")

collection.add(
    ids=["doc_001", "doc_002"],
    documents=[
        "Ray 适合做个人 AI Infra 的任务调度层。",
        "MLflow 适合记录实验、模型版本和评测结果。",
    ],
    metadatas=[
        {"source": "ray_post", "version": "v1"},
        {"source": "mlflow_post", "version": "v1"},
    ],
)

result = collection.query(
    query_texts=["个人 AI Infra 里谁负责实验记录？"],
    n_results=2,
)

print(result)
```

Chroma 适合这些场景：

| 场景 | 是否适合 |
| --- | --- |
| 个人知识库 | 很适合 |
| RAG demo | 很适合 |
| Notebook 里快速试检索 | 很适合 |
| 小团队内部文档问答 | 可以 |
| 超大规模向量检索 | 需要谨慎 |

个人建议：如果你刚开始做 RAG，先用 Chroma。它能让你把文档切分、embedding、检索、prompt 拼接这条链路快速跑起来。

## 三、FAISS：高性能向量索引库

FAISS 是 Meta AI 开源的向量相似度搜索库。它更像一个高性能索引引擎，而不是完整向量数据库。

它的优点：

1. 检索性能强。
2. 索引类型丰富。
3. 可控性高。
4. 适合自己封装 RAG 检索逻辑。
5. 本地运行很轻。

安装：

```bash
pip install -U faiss-cpu
```

如果需要 GPU 版本，要根据你的 CUDA/PyTorch/平台选择合适安装方式。

最小例子：

```python
import numpy as np
import faiss

dim = 768
vectors = np.random.random((1000, dim)).astype("float32")

index = faiss.IndexFlatL2(dim)
index.add(vectors)

query = np.random.random((1, dim)).astype("float32")
distances, ids = index.search(query, k=5)

print(ids)
print(distances)
```

FAISS 本身不帮你管理文档、元数据、权限和 API。你通常需要自己维护：

```text
faiss.index
metadata.jsonl
chunks.jsonl
manifest.json
```

一个推荐 manifest：

```json
{
  "index_version": "rag_index_v3",
  "embedding_model": "bge-m3",
  "dim": 1024,
  "chunk_size": 800,
  "chunk_overlap": 120,
  "doc_count": 1284,
  "created_at": "2026-07-18"
}
```

Chroma 和 FAISS 怎么选？

| 需求 | 推荐 |
| --- | --- |
| 快速做 RAG demo | Chroma |
| 希望少写工程代码 | Chroma |
| 需要强元数据过滤 | Chroma |
| 想精细控制索引 | FAISS |
| 需要高性能本地检索 | FAISS |
| 想自己管理文件和版本 | FAISS |

![RAG 向量库链路](/assets/images/personal-ai-infra-tools/rag-vector-flow.svg)

## 四、RAG 索引应该怎么接 MLflow？

无论用 Chroma 还是 FAISS，都要记录索引版本。

RAG 最难排查的问题之一是：模型没变，prompt 没变，但答案变差了。最后发现是文档更新、切分规则、embedding 模型或检索参数变了。

每次构建索引，建议记录：

| 项目 | 示例 |
| --- | --- |
| 文档来源 | `docs/power_transformer/` |
| 文档数量 | `1284` |
| chunk size | `800` |
| chunk overlap | `120` |
| embedding model | `bge-m3` |
| vector store | `chroma` / `faiss` |
| top-k | `8` |
| reranker | `bge-reranker-v2` |
| recall@k | `0.84` |
| index path | `rag_store/faiss/v3` |

示例：

```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("rag-index")

with mlflow.start_run(run_name="docs-index-v3"):
    mlflow.log_params({
        "vector_store": "faiss",
        "embedding_model": "bge-m3",
        "chunk_size": 800,
        "chunk_overlap": 120,
        "doc_count": 1284,
        "index_path": "rag_store/faiss/v3",
    })
    mlflow.log_metric("recall_at_5", 0.84)
    mlflow.log_artifact("rag_store/faiss/v3/manifest.json", artifact_path="index")
    mlflow.log_artifact("reports/rag_bad_cases.md", artifact_path="reports")
```

这能把 RAG 从“玄学问答”变成可迭代系统。

## 五、Prometheus：采集指标

Prometheus 是监控里的指标采集和时序数据库。它负责定时 scrape 各种 exporter 暴露出来的 metrics。

在个人 AI Infra 里，你可以用它采集：

1. GPU 显存。
2. GPU 利用率。
3. GPU 温度和功耗。
4. vLLM/LMDeploy 服务指标。
5. 系统 CPU、内存、磁盘。
6. 自定义 Python 服务指标。

GPU 监控常用 NVIDIA DCGM Exporter。典型链路是：

```text
NVIDIA GPU
  -> DCGM Exporter
  -> Prometheus
  -> Grafana
```

Prometheus 配置片段：

```yaml
scrape_configs:
  - job_name: "dcgm"
    static_configs:
      - targets: ["localhost:9400"]

  - job_name: "llm-serving"
    static_configs:
      - targets: ["localhost:8000"]
```

个人机器上不必一开始上很复杂的监控。最低配也要做到：

1. 能看到显存是否接近上限。
2. 能看到 GPU 利用率。
3. 能看到服务是否还活着。
4. 能看到请求延迟和错误率。

## 六、Grafana：把指标变成看板

Grafana 负责把 Prometheus 的指标可视化。

建议至少做三个 dashboard：

| Dashboard | 看什么 |
| --- | --- |
| GPU Overview | 显存、利用率、温度、功耗 |
| LLM Serving | 请求数、错误率、延迟、tokens/s |
| Training Jobs | 训练 loss、GPU 使用、任务状态 |

个人推理服务最应该看的指标：

| 指标 | 含义 |
| --- | --- |
| GPU memory used | 是否快 OOM |
| GPU utilization | 是否吃满 |
| P95 latency | 用户体感 |
| TTFT | 首 token 延迟 |
| tokens/s | 生成吞吐 |
| request error rate | 稳定性 |
| queue time | 是否排队严重 |

训练时最应该看的指标：

| 指标 | 含义 |
| --- | --- |
| train loss | 是否正常下降 |
| learning rate | scheduler 是否正确 |
| GPU memory | 显存是否稳定 |
| step time | 是否有数据加载瓶颈 |
| checkpoint time | 保存是否拖慢训练 |

Grafana 的价值不是让页面好看，而是让你第一眼知道系统哪里不对。

## 七、Jupyter：个人 AI Infra 的实验工作台

Jupyter 对个人 AI Infra 非常重要。它不是生产服务，但它是你快速理解数据、分析结果、构造样例的地方。

适合在 Jupyter 里做：

1. 查看训练数据分布。
2. 统计 token 长度。
3. 检查 bad cases。
4. 试 prompt。
5. 调 RAG 检索参数。
6. 画 MLflow run 对比图。
7. 分析推理延迟。
8. 快速调用本地 OpenAI API。

启动：

```bash
pip install -U jupyterlab
jupyter lab --ip 0.0.0.0 --port 8888
```

调用本地推理服务：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="local-token",
)

response = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=[{"role": "user", "content": "解释一下个人 AI Infra 的配套工具层。"}],
    temperature=0.2,
)

print(response.choices[0].message.content)
```

建议把 notebook 分层：

```text
notebooks/
  data_inspection/
  prompt_lab/
  rag_eval/
  mlflow_analysis/
  serving_benchmark/
```

不要让 notebook 变成生产脚本。Notebook 适合探索，稳定逻辑要沉淀到 `scripts/`。

## 八、Ollama：快速试模型和 prompt

Ollama 适合做快速模型测试。它的优势是：

1. 安装和启动简单。
2. 拉模型方便。
3. 本地 API 简洁。
4. 适合 prompt demo、快速验证、小模型尝试。
5. 不需要一开始配置复杂推理服务。

常用命令：

```bash
ollama pull qwen2.5:7b
ollama run qwen2.5:7b
```

本地 API 示例：

```bash
curl http://localhost:11434/api/generate \
  -d '{
    "model": "qwen2.5:7b",
    "prompt": "用三句话解释 RAG。",
    "stream": false
  }'
```

Python 调用：

```python
import requests

resp = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen2.5:7b",
        "prompt": "解释一下 Chroma 和 FAISS 的区别。",
        "stream": False,
    },
    timeout=120,
)

print(resp.json()["response"])
```

Ollama 适合：

| 场景 | 是否适合 |
| --- | --- |
| 快速试 prompt | 很适合 |
| 小模型 demo | 很适合 |
| 本地知识库原型 | 可以 |
| 高并发生产推理 | 不优先 |
| 精细控制 KV cache 和吞吐 | 不优先 |
| 和 vLLM/LMDeploy 做性能对照 | 可以 |

我的建议是：Ollama 用来“快试”，vLLM/LMDeploy 用来“正式服务”。

## 九、一个推荐的配套工具目录

可以这样组织：

```text
ai-infra/
  rag_store/
    chroma/
    faiss/
  monitoring/
    prometheus/
      prometheus.yml
    grafana/
      dashboards/
  notebooks/
    prompt_lab/
    rag_eval/
    serving_benchmark/
  scripts/
    build_index.py
    eval_rag.py
    benchmark_serving.py
  reports/
    rag/
    monitoring/
    benchmark/
```

每个工具都要留下配置：

| 工具 | 建议保存 |
| --- | --- |
| Chroma | collection 名称、persist path、embedding 模型 |
| FAISS | index 文件、metadata、manifest |
| Prometheus | `prometheus.yml` |
| Grafana | dashboard JSON |
| Jupyter | notebook 和稳定脚本 |
| Ollama | 模型名、tag、测试 prompt |

配置比命令更重要。你未来能不能复现，取决于这些配置有没有留下来。

## 十、怎么和前五篇形成完整闭环？

完整个人 AI Infra 可以这样跑：

1. Jupyter 里检查数据、试 prompt。
2. Chroma/FAISS 构建 RAG 索引。
3. XTuner 用高质量数据微调模型。
4. MLflow 记录训练、索引、评测和部署。
5. vLLM/LMDeploy 启动正式推理服务。
6. Ray 调度批量评测、数据生成、Agent 实验。
7. Prometheus/Grafana 监控 GPU 和服务指标。
8. Ollama 快速试新模型或 prompt 方案。
9. 收集 bad cases，回到数据和 prompt 迭代。

![开发与监控闭环](/assets/images/personal-ai-infra-tools/monitor-dev-loop.svg)

这个闭环的关键是：**每个实验都要能留下痕迹，每个服务都要能被观察，每个失败样例都要能回到下一轮改进。**

## 十一、常见坑

| 坑 | 表现 | 建议 |
| --- | --- | --- |
| 向量库不记版本 | RAG 效果变差却不知道原因 | 记录 index manifest |
| Chroma/FAISS 混用无规范 | 检索结果不可比较 | 固定 eval 集和参数 |
| Prometheus 只装不用 | 指标没人看 | 做最小 dashboard |
| Grafana 面板太花 | 看不出核心问题 | 只放关键指标 |
| Notebook 堆成垃圾场 | 无法复现实验 | 稳定逻辑迁移到 scripts |
| Ollama 当生产服务 | 并发和监控不够 | 正式服务用 vLLM/LMDeploy |
| 只监控 GPU | 不知道质量变差 | 同时记录 bad cases |
| 只看平均延迟 | 用户仍觉得慢 | 看 P95/P99 |

配套工具最容易犯的错是：装了很多，但没有形成流程。

工具本身没有价值，进入闭环后才有价值。

## 十二、总结：配套工具让个人 AI Infra 从“能跑”变成“好用”

这个系列里，我把个人轻量 AI Infra 拆成几层：

| 层次 | 工具 | 作用 |
| --- | --- | --- |
| 调度层 | Ray | 任务队列、资源声明、并发 |
| 实验层 | MLflow | 实验记录、产物、模型版本 |
| 推理层 | vLLM/LMDeploy | 高性能 OpenAI 兼容 API |
| 微调层 | XTuner | LoRA/QLoRA/SFT 微调 |
| 配套工具层 | Chroma/FAISS、Prometheus/Grafana、Jupyter、Ollama | RAG、监控、开发、快速试验 |

最后这一层的价值，是让系统进入日常可用状态：

1. Chroma/FAISS 让模型有可检索知识库。
2. Prometheus/Grafana 让训练和推理状态可见。
3. Jupyter 让数据分析和实验原型更快。
4. Ollama 让模型和 prompt 测试更轻。

个人 AI Infra 不需要一开始就像企业平台那样复杂。真正好的个人工作站，应该是：

1. 架构足够轻。
2. 模块边界清楚。
3. 训练、推理、RAG、监控都能跑。
4. 每次实验都有记录。
5. 每个问题都能被定位。
6. 每个 bad case 都能进入下一轮改进。

这就是个人轻量 AI Infra 系列的最后一块拼图：配套工具层。

参考：

1. [Chroma 官方文档](https://docs.trychroma.com/)
2. [FAISS GitHub](https://github.com/facebookresearch/faiss)
3. [Prometheus 官方文档](https://prometheus.io/docs/introduction/overview/)
4. [Grafana 官方文档](https://grafana.com/docs/)
5. [NVIDIA DCGM Exporter](https://github.com/NVIDIA/dcgm-exporter)
6. [Ollama API 文档](https://github.com/ollama/ollama/blob/main/docs/api.md)
