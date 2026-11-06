---
title: 个人 AI Infra 搭建方案：Ray + MLflow + LMDeploy/vLLM 的轻量全栈
tags:
  - AI Infra
  - Ray
  - MLflow
  - vLLM
  - LMDeploy
---

> 一句话总结：个人 AI Infra 不一定要上 Kubernetes。对 90% 个人玩家和单机工作站来说，Ray + MLflow + LMDeploy/vLLM + XTuner 已经能覆盖调度、实验、微调、推理、RAG 和监控的完整闭环。

![个人 AI Infra 轻量全栈](/assets/images/personal-ai-infra/stack-overview.svg)

<!--more-->

很多人一提到 AI infra，脑子里马上出现 Kubernetes、Kubeflow、Argo、Istio、复杂 CI/CD 和一堆云原生组件。

这些东西在企业集群里当然有价值，但对个人玩家、独立开发者、小团队和单机工作站来说，直接上 K8s 往往是“把问题变复杂”。你真正需要的不是一套宏大的平台，而是一套能在一台机器上稳定完成以下事情的轻量系统：

1. 同时管理微调、推理、RAG、评测、Agent 实验这些任务。
2. 记录每次训练的数据、参数、指标和 LoRA 权重。
3. 快速启动 OpenAI 兼容 API，给本地应用、Agent 和 RAG 使用。
4. 尽量吃满 GPU，但不要让训练和服务互相抢资源。
5. 能看见 GPU 显存、吞吐、延迟和任务状态。
6. 出问题时能快速重启、回滚、复现实验。

所以我更推荐一种“轻量全能首选”方案：

```text
Ray + MLflow + LMDeploy / vLLM + XTuner + Chroma / FAISS + Prometheus / Grafana + Jupyter + Ollama
```

它的核心思想是：**不用 K8s，先把个人 AI 工作站跑顺。**

## 一、为什么个人 AI Infra 不建议一开始上 K8s？

Kubernetes 的优势是多租户、大规模、弹性调度、服务治理和云原生生态。但个人 AI 工作站的主要矛盾通常不是“如何管理 100 台机器”，而是：

| 个人玩家真实问题 | K8s 是否必要 |
| --- | --- |
| 单机 1-2 张 GPU 怎么分配给训练和推理？ | 不必要，Ray 更轻 |
| 每次 LoRA 微调结果怎么记录？ | MLflow 足够 |
| 怎么快速启动 OpenAI API？ | vLLM/LMDeploy 直接解决 |
| 怎么做 RAG demo？ | Chroma/FAISS 足够 |
| 怎么看显存和 GPU 利用率？ | Prometheus/Grafana 足够 |
| 怎么快速试模型？ | Ollama 足够 |

K8s 的运维成本并不低。你要处理镜像、Pod、PVC、Ingress、GPU Operator、权限、网络、日志、监控、服务发现。对单机用户来说，这些复杂度很容易压过 AI 本身。

个人 AI Infra 的第一原则应该是：

> 能用进程解决的，不急着上容器编排；能用 Ray 管理的，不急着上 K8s；能用 MLflow 记录的，不急着上 Kubeflow。

## 二、整套架构：每个组件负责什么？

这套方案的分工很清楚。

| 模块 | 推荐组件 | 负责什么 |
| --- | --- | --- |
| 算力调度 | Ray | 单机任务队列、GPU/CPU 资源分配、多进程隔离、Actor 管理 |
| 实验管理 | MLflow | 训练参数、指标、权重、数据版本、模型仓库 |
| 高性能推理 | LMDeploy / vLLM | OpenAI 兼容 API、KV Cache、长上下文、量化推理 |
| 微调套件 | XTuner | Qwen/Llama/InternLM 的 LoRA、QLoRA、全参微调 |
| 向量检索 | Chroma / FAISS | 本地 RAG 文档索引和向量检索 |
| 监控 | Prometheus + Grafana | GPU、显存、服务延迟、吞吐和系统资源 |
| 开发环境 | Jupyter | 数据处理、实验调试、原型开发 |
| 快速测试 | Ollama | 快速拉起小模型，验证 prompt 和本地 demo |

这套组合的好处是模块化。每个组件都能独立替换：

| 如果你更喜欢 | 可以替换为 |
| --- | --- |
| 不用 LMDeploy | 用 vLLM |
| 不用 vLLM | 用 LMDeploy 或 llama.cpp server |
| 不用 Chroma | 用 FAISS、Milvus Lite、Qdrant |
| 不用 XTuner | 用 LLaMA-Factory、Axolotl |
| 不用 Grafana | 先用 `nvidia-smi` 和 Ray Dashboard |

个人 infra 最怕“平台大而全，但每个环节都不好改”。模块化能让你先跑起来，再逐步升级。

## 三、Ray：个人工作站的调度底座

![Ray 在个人 AI Infra 里的角色](/assets/images/personal-ai-infra/resource-scheduler.svg)

Ray 在这套方案里不是训练框架，也不是推理框架。它的角色是**任务调度底座**。

你可以把 Ray 理解成单机 AI 工作站上的“轻量任务操作系统”：

| Ray 能力 | 在个人 AI Infra 里的用途 |
| --- | --- |
| 资源声明 | 指定任务需要多少 CPU、GPU、内存 |
| 任务队列 | 微调、评测、批量推理排队执行 |
| Actor | 常驻推理服务、Agent worker、数据处理 worker |
| 并发控制 | 避免多个任务同时把显存打爆 |
| Dashboard | 查看任务状态、资源占用和失败信息 |

典型场景是：

1. 一个 vLLM/LMDeploy API 服务常驻，占用部分 GPU。
2. 一个 XTuner LoRA 微调任务排队运行，占用大部分 GPU。
3. 一个批量推理任务等待空闲时执行。
4. 多个 Agent 实验任务使用 CPU 和少量 GPU。

没有调度层时，你很容易手动开几个进程，然后显存 OOM。Ray 至少可以让任务按资源声明排队，降低互相抢占的概率。

Ray 尤其适合个人玩家的原因是：

| 优点 | 说明 |
| --- | --- |
| 安装轻 | 不需要 K8s 集群 |
| 单机友好 | 本机就能启动 head node |
| Python 原生 | 适合训练脚本、Agent、数据处理 |
| 任务模型简单 | `remote task` 和 `Actor` 容易理解 |
| 可扩展 | 以后多机也能扩展 Ray cluster |

## 四、MLflow：替代笨重实验平台的轻量 MLOps

个人微调最容易乱的地方，是实验记录。

你今天调了学习率，明天换了数据，后天换了 LoRA rank。跑了十几次以后，可能已经不知道哪个权重对应哪次实验。

MLflow 解决的就是这个问题。

| MLflow 功能 | 用途 |
| --- | --- |
| Experiment | 按项目组织实验 |
| Run | 每次训练对应一次 run |
| Params | 记录学习率、batch size、LoRA rank、模型名 |
| Metrics | 记录 loss、eval score、tokens/s |
| Artifacts | 保存 LoRA 权重、日志、配置文件 |
| Model Registry | 管理可部署模型版本 |

对个人 AI Infra 来说，MLflow 最重要的是三件事：

1. **一键复现**：知道某个好结果用了哪份数据、哪个配置、哪个 checkpoint。
2. **LoRA 版本管理**：不同任务、不同数据、不同 base model 的 adapter 不混乱。
3. **训练可视化**：loss、eval 指标、吞吐和训练时长能看见。

如果不想搭复杂数据库，MLflow 可以先用本地文件存储；如果后面实验变多，再接 SQLite/PostgreSQL 和对象存储。

一个简单目录可以这样设计：

```text
ai-infra/
  data/
    raw/
    processed/
    rag_docs/
  models/
    base/
    adapters/
    merged/
  experiments/
    mlruns/
  serving/
    configs/
    logs/
  notebooks/
  scripts/
```

## 五、LMDeploy / vLLM：本地高性能推理核心

微调完模型之后，要能服务起来。

LMDeploy 和 vLLM 都是高性能 LLM 推理框架，适合做本地 OpenAI 兼容 API。你的 RAG、Agent、Web UI、脚本都可以像调用 OpenAI API 一样调用本地模型。

| 能力 | 作用 |
| --- | --- |
| OpenAI 兼容 API | 本地应用不用改太多代码 |
| KV Cache 管理 | 长上下文和多轮对话更高效 |
| Continuous Batching | 多请求并发时提高吞吐 |
| 量化推理 | 降低显存占用 |
| 多模型服务 | 按需加载不同模型或 adapter |
| Streaming | 支持流式输出 |

LMDeploy 和 vLLM 怎么选？

| 场景 | 更推荐 |
| --- | --- |
| 你主要用 InternLM/书生生态 | LMDeploy |
| 你想要社区生态和 OpenAI API 兼容体验 | vLLM |
| 你关注 TurboMind、量化和国产模型适配 | LMDeploy |
| 你关注并发、batching、服务生态 | vLLM |

实际个人使用里，不必纠结“只能选一个”。完全可以两个都装：

1. vLLM 做通用 OpenAI API 服务。
2. LMDeploy 做特定模型、高性能量化或长上下文实验。
3. Ollama 做快速试模型和 prompt 原型。

## 六、XTuner：轻量微调主力

XTuner 适合做中文生态和开源大模型的轻量微调，尤其是 Qwen、Llama、InternLM 等模型。

个人工作站常见微调策略：

| 策略 | 适合场景 |
| --- | --- |
| LoRA | 最常用，显存友好，训练快 |
| QLoRA | 显存更紧张时使用 |
| 全参数微调 | 数据量大、资源足够时使用 |
| Merge Adapter | 部署前把 LoRA 合并进 base model |

按 32GB 显存级别的单卡工作站，大致可以这样规划：

| 模型规模 | 推荐玩法 |
| --- | --- |
| 7B | LoRA/QLoRA 都比较轻松 |
| 14B | LoRA 可行，注意 batch 和上下文长度 |
| 32B | 量化微调或更激进的显存优化 |
| 70B | 个人单卡不建议硬上，考虑云端或多卡 |

微调的关键不是“跑起来”，而是形成闭环：

1. 数据清洗。
2. XTuner 训练。
3. MLflow 记录参数和权重。
4. 合并或加载 adapter。
5. LMDeploy/vLLM 起服务。
6. 自己的评测集回归。
7. 错误样本回流下一轮。

![个人 AI Infra 工作流闭环](/assets/images/personal-ai-infra/workflow-loop.svg)

## 七、Chroma / FAISS：本地 RAG 的最低可用配置

个人 AI Infra 里，RAG 是非常值得优先搭的能力。

因为很多场景不需要微调模型，只需要让模型读你的私有文档：

| 场景 | RAG 价值 |
| --- | --- |
| 个人知识库 | 查自己的笔记、PDF、网页收藏 |
| 项目文档问答 | 问代码仓库、接口文档、设计文档 |
| 论文助手 | 查论文摘要、方法、实验设置 |
| Agent 工具说明 | 让 Agent 理解本地工具和流程 |

Chroma 和 FAISS 都适合个人本地 RAG：

| 工具 | 特点 |
| --- | --- |
| Chroma | 上手简单，自带持久化和元数据 |
| FAISS | 检索性能强，适合自己控制索引 |

RAG 的基本链路：

```text
文档解析 → chunk 切分 → embedding → 向量索引 → query 检索 → rerank → prompt → LLM 回答
```

个人项目里，最容易忽略的是文档清洗和 chunk 策略。不是把 PDF 一股脑塞进向量库就叫 RAG。要注意：

1. 表格和代码块不要切烂。
2. chunk 不要太短，否则缺上下文。
3. chunk 不要太长，否则检索不准。
4. 每个 chunk 保留来源、标题、页码等元数据。
5. 回答时尽量带引用。

## 八、Prometheus + Grafana：先看见，再优化

个人玩家也需要监控。

最少要看这些指标：

| 指标 | 为什么重要 |
| --- | --- |
| GPU 利用率 | 看算力是否被吃满 |
| 显存占用 | 判断能不能同时跑服务和训练 |
| GPU 温度 | 防止长时间训练降频 |
| 推理 QPS | 看服务吞吐 |
| 请求延迟 | 看本地 API 是否可用 |
| token/s | 判断推理速度 |
| 训练 loss | 看训练是否正常收敛 |
| 磁盘空间 | checkpoint 和模型很容易塞满硬盘 |

Prometheus + Grafana 对个人来说不算重。你可以先接：

1. `nvidia-smi` exporter 或 DCGM exporter。
2. Ray Dashboard。
3. vLLM/LMDeploy 服务日志。
4. MLflow 训练指标。

先把显存、利用率、温度、延迟看清楚，再谈优化。

## 九、Ollama：快速试模型，不做主力服务

Ollama 很适合做快速模型测试：

1. 拉一个小模型。
2. 快速验证 prompt。
3. 做本地 demo。
4. 比较不同模型基本回答风格。

但如果你要做高并发 API、长上下文、多模型服务、严肃评测或生产化 Agent 后端，LMDeploy/vLLM 更适合作为主力推理服务。

我的建议是：

| 用途 | 推荐 |
| --- | --- |
| 快速试模型 | Ollama |
| 本地 RAG demo | Ollama 或 vLLM |
| Agent 后端 | vLLM / LMDeploy |
| 多请求并发 | vLLM / LMDeploy |
| 微调后模型部署 | LMDeploy / vLLM |

## 十、推荐启动顺序

为了少踩坑，可以按这个顺序搭：

| 阶段 | 目标 |
| --- | --- |
| 1 | 装 CUDA、驱动、Python 环境，确认 GPU 可用 |
| 2 | 安装 Ollama，快速验证机器能跑模型 |
| 3 | 安装 vLLM 或 LMDeploy，启动 OpenAI 兼容 API |
| 4 | 安装 MLflow，记录一次最小实验 |
| 5 | 安装 XTuner，跑一个小 LoRA 微调 |
| 6 | 把 LoRA 权重登记到 MLflow |
| 7 | 用 vLLM/LMDeploy 加载微调模型或合并模型 |
| 8 | 接入 Chroma/FAISS，做一个本地 RAG demo |
| 9 | 启动 Ray，把训练、批量推理、Agent 任务纳入调度 |
| 10 | 接 Prometheus/Grafana，看 GPU 和服务指标 |

很多人会一开始就把所有组件都装上，最后不知道哪里坏了。更稳的方式是每次只增加一个模块，每一步都留一个可运行状态。

## 十一、一台 5090 工作站可以怎么分配资源？

如果你的目标是类似 5090 Blackwell 级别的个人工作站，可以把它看成一个“小型 AI 实验室”。

典型资源分配：

| 任务 | 建议策略 |
| --- | --- |
| 常驻推理服务 | 量化模型 + vLLM/LMDeploy，限制最大并发和上下文 |
| LoRA 微调 | 使用 Ray 排队，在服务低峰运行 |
| 批量推理 | 作为 Ray job，空闲时生成数据或跑评测 |
| RAG 索引 | CPU/NVMe 为主，避免和训练抢 GPU |
| Agent 实验 | 多进程 CPU + 少量模型调用，交给 Ray 管理 |
| 监控 | 常驻轻量服务 |

关键是不要幻想单卡同时满负载跑所有东西。更现实的方式是：

1. 推理服务常驻，但限制上下文和并发。
2. 微调任务排队运行，必要时暂停 API 服务。
3. 批量推理放到夜间。
4. RAG 索引尽量走 CPU。
5. 所有任务都记录到 MLflow 或日志里。

## 十二、一个最小可用目录和服务规划

目录建议：

```text
~/ai-infra/
  data/
    sft/
    preference/
    rag_docs/
    eval/
  models/
    base/
    adapters/
    merged/
  mlruns/
  ray/
    jobs/
  serving/
    vllm/
    lmdeploy/
  rag/
    chroma/
    faiss/
  notebooks/
  logs/
```

服务建议：

| 服务 | 默认端口 | 说明 |
| --- | --- | --- |
| Ray Dashboard | 8265 | 查看任务和资源 |
| MLflow UI | 5000 | 查看实验 |
| vLLM API | 8000 | OpenAI 兼容推理 |
| LMDeploy API | 23333 | 可选推理服务 |
| Grafana | 3000 | 监控面板 |
| Prometheus | 9090 | 指标采集 |
| Jupyter | 8888 | 开发调试 |

端口可以自己调整，但建议固定下来，写进 `.env` 或 `README`，否则时间久了会乱。

## 十三、各组件最小使用教程

下面给一个偏“个人工作站”的最小使用教程。命令只是示例，真实环境里要按你的 CUDA、Python、模型路径和显卡情况调整。

### 1. Ray：启动本机调度器

Ray 的第一步是启动本机 head node。

```bash
ray start --head --dashboard-host=0.0.0.0
```

启动后打开：

```text
http://localhost:8265
```

就能看到 Ray Dashboard。

最小任务示例：

```python
import ray

ray.init(address="auto")

@ray.remote(num_cpus=2, num_gpus=0.25)
def run_batch_infer(task_id):
    return f"task {task_id} done"

refs = [run_batch_infer.remote(i) for i in range(4)]
print(ray.get(refs))
```

Ray 的用法要点：

| 用法 | 说明 |
| --- | --- |
| `@ray.remote` | 把普通 Python 函数变成可调度任务 |
| `num_gpus=0.25` | 声明任务最多使用四分之一张 GPU |
| Actor | 适合常驻服务，如 Agent worker、模型 worker |
| Ray Dashboard | 看任务状态、资源占用和错误日志 |

个人场景里，Ray 最适合管三类任务：

1. 批量推理。
2. 数据处理。
3. 微调任务排队。

### 2. MLflow：记录一次实验

先启动 MLflow UI：

```bash
mlflow ui --host 0.0.0.0 --port 5000 --backend-store-uri ./mlruns
```

打开：

```text
http://localhost:5000
```

最小记录示例：

```python
import mlflow

mlflow.set_experiment("qwen-lora-demo")

with mlflow.start_run():
    mlflow.log_param("base_model", "Qwen2.5-7B-Instruct")
    mlflow.log_param("lora_rank", 16)
    mlflow.log_param("learning_rate", 2e-4)
    mlflow.log_metric("train_loss", 1.23)
    mlflow.log_artifact("configs/xtuner_lora.py")
```

如果训练产出了 LoRA 权重，可以这样登记：

```python
mlflow.log_artifacts("work_dirs/qwen_lora/adapter", artifact_path="lora_adapter")
```

MLflow 的建议用法：

| 内容 | 放进 MLflow 的位置 |
| --- | --- |
| 学习率、batch size、LoRA rank | Params |
| loss、eval score、tokens/s | Metrics |
| 训练配置、日志、adapter 权重 | Artifacts |
| 可部署模型版本 | Model Registry |

一句话：每跑一次训练，都应该有一个 MLflow run。

### 3. vLLM：启动 OpenAI 兼容 API

vLLM 最适合快速把本地模型变成 API 服务。

示例：

```bash
vllm serve /data/models/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --served-model-name qwen-local \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.85
```

调用方式：

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-local",
    "messages": [
      {"role": "user", "content": "解释一下 KV Cache 是什么"}
    ],
    "temperature": 0.7
  }'
```

Python 调用可以复用 OpenAI SDK：

```python
from openai import OpenAI

client = OpenAI(
    api_key="EMPTY",
    base_url="http://localhost:8000/v1",
)

resp = client.chat.completions.create(
    model="qwen-local",
    messages=[{"role": "user", "content": "写一个 AI infra 学习路线"}],
)

print(resp.choices[0].message.content)
```

vLLM 重点参数：

| 参数 | 作用 |
| --- | --- |
| `--max-model-len` | 控制最大上下文，影响 KV Cache 显存 |
| `--gpu-memory-utilization` | 控制 vLLM 可用显存比例 |
| `--served-model-name` | API 中使用的模型名 |
| `--tensor-parallel-size` | 多卡切分模型时使用 |

### 4. LMDeploy：启动另一个推理服务选择

LMDeploy 也可以启动 OpenAI 兼容服务，适合书生生态和一些高性能量化场景。

示例：

```bash
lmdeploy serve api_server /data/models/internlm2_5-7b-chat \
  --server-name 0.0.0.0 \
  --server-port 23333 \
  --model-name internlm-local
```

调用方式类似：

```bash
curl http://localhost:23333/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "internlm-local",
    "messages": [
      {"role": "user", "content": "用三句话解释 Ray 的作用"}
    ]
  }'
```

建议：

| 场景 | 选择 |
| --- | --- |
| 通用 OpenAI API 服务 | vLLM |
| InternLM / LMDeploy 生态模型 | LMDeploy |
| 想比较吞吐和显存 | 两个都测一遍 |
| 快速试 prompt | Ollama 更快 |

### 5. XTuner：跑一次 LoRA 微调

XTuner 的典型流程是：

```text
准备数据 → 选择配置 → 启动训练 → 导出 LoRA → 合并或部署
```

最小目录：

```text
data/sft/train.jsonl
configs/qwen_lora.py
work_dirs/qwen_lora/
```

训练示例：

```bash
xtuner train configs/qwen_lora.py --work-dir work_dirs/qwen_lora
```

如果要把训练过程记录到 MLflow，可以在训练脚本外层做一层包装：

```python
import subprocess
import mlflow

mlflow.set_experiment("xtuner-qwen-lora")

with mlflow.start_run():
    mlflow.log_param("config", "configs/qwen_lora.py")
    mlflow.log_param("base_model", "Qwen2.5-7B-Instruct")

    subprocess.run([
        "xtuner", "train",
        "configs/qwen_lora.py",
        "--work-dir", "work_dirs/qwen_lora"
    ], check=True)

    mlflow.log_artifacts("work_dirs/qwen_lora", artifact_path="xtuner_output")
```

XTuner 使用建议：

| 场景 | 建议 |
| --- | --- |
| 第一次跑 | 用小数据集确认链路 |
| 显存不够 | 降 batch、降 max length、用 QLoRA |
| 效果不稳 | 先检查数据质量，不要急着调参 |
| 准备部署 | 保存 adapter，并记录 base model 版本 |

### 6. Chroma / FAISS：搭一个最小 RAG

如果想快速做本地 RAG，Chroma 最省事。

最小示例：

```python
import chromadb

client = chromadb.PersistentClient(path="./rag/chroma")
collection = client.get_or_create_collection("personal_docs")

collection.add(
    documents=[
        "Ray 负责单机任务调度和资源管理。",
        "MLflow 用来记录实验参数、指标和模型产物。",
        "vLLM 可以启动 OpenAI 兼容 API 服务。"
    ],
    ids=["doc1", "doc2", "doc3"],
)

result = collection.query(
    query_texts=["MLflow 是干什么的？"],
    n_results=2,
)

print(result)
```

真实项目里要补上 embedding 模型、chunk 切分和元数据：

| 环节 | 建议 |
| --- | --- |
| 文档解析 | Markdown、PDF、网页分开处理 |
| chunk | 500-1000 中文字左右先试 |
| metadata | 保存文件名、标题、页码、URL |
| rerank | 质量不够时再加 reranker |
| 引用 | 回答里带来源，方便排查幻觉 |

### 7. Prometheus + Grafana：看 GPU 和服务状态

最小监控可以先从 GPU 开始。

如果你使用 DCGM exporter，可以让 Prometheus 抓取 GPU 指标；Grafana 负责展示面板。

你至少应该看：

| 面板 | 作用 |
| --- | --- |
| GPU 利用率 | 判断是否吃满算力 |
| 显存占用 | 判断是否会 OOM |
| GPU 温度 | 判断是否降频 |
| 推理请求数 | 看 API 是否有流量 |
| 请求延迟 | 看服务是否卡顿 |
| token/s | 看模型生成速度 |

个人最小版本也可以先不用完整 Prometheus，直接从这些开始：

```bash
nvidia-smi -l 1
```

再逐步升级到 Grafana 面板。

### 8. Ollama：快速试模型

Ollama 适合做第一步模型体验。

```bash
ollama pull qwen2.5:7b
ollama run qwen2.5:7b
```

也可以启动本地 API：

```bash
ollama serve
```

Ollama 的定位：

| 适合 | 不适合 |
| --- | --- |
| 快速试模型 | 高并发生产服务 |
| 快速试 prompt | 严格吞吐优化 |
| 本地 demo | 大规模评测 |
| 小模型体验 | 多租户服务治理 |

我的建议是：Ollama 用来“试”，vLLM/LMDeploy 用来“服务”。

### 9. Jupyter：个人实验入口

Jupyter 适合做数据处理、RAG 调试、评测分析。

启动：

```bash
jupyter lab --ip=0.0.0.0 --port=8888
```

建议 notebook 分三类：

| Notebook 类型 | 示例 |
| --- | --- |
| 数据处理 | 清洗 SFT 数据、切分文档 |
| 实验分析 | 读取 MLflow 指标、画 loss 曲线 |
| RAG 调试 | 查看检索结果、调 chunk 和 prompt |

不要把长期服务写在 notebook 里。Notebook 适合探索，真正稳定后再沉淀成脚本。

### 10. 最小闭环怎么串起来？

最小闭环可以按下面走：

```text
1. Ollama 试模型和 prompt
2. 准备一份 SFT 数据
3. XTuner 跑 LoRA
4. MLflow 记录参数、指标和 adapter
5. vLLM/LMDeploy 启动本地 API
6. Chroma/FAISS 接 RAG
7. Ray 管批量推理和评测任务
8. Prometheus/Grafana 看资源
9. 错误样本回流到下一轮数据
```

这就是个人 AI Infra 的最小可用系统。

## 十四、这套方案的优缺点

优点：

| 优点 | 说明 |
| --- | --- |
| 轻量 | 不需要 K8s，部署快 |
| 模块化 | 每个组件可以单独替换 |
| 成本低 | 适合单机和个人工作站 |
| 覆盖完整 | 微调、实验、推理、RAG、监控都有 |
| Python 友好 | Ray、MLflow、XTuner 都适合研究和开发 |

缺点：

| 缺点 | 说明 |
| --- | --- |
| 不适合大规模多租户 | 团队大了还是要考虑 K8s 或平台化 |
| 权限隔离弱 | 个人使用没问题，企业环境不够 |
| 高可用不足 | 单机挂了服务就挂 |
| 服务治理简单 | 灰度、流量治理、自动扩缩容有限 |
| 需要自己约定规范 | 目录、端口、模型版本都要自律 |

所以这套方案的定位非常明确：**个人和小团队的高性价比 AI Infra，而不是企业级云原生平台。**

## 十五、总结：先跑顺个人闭环，再谈平台化

个人 AI Infra 的目标不是“看起来像大厂平台”，而是让你每天的 AI 工作流更顺：

1. 想试模型，Ollama 快速验证。
2. 想做服务，vLLM/LMDeploy 拉起 API。
3. 想做微调，XTuner 跑 LoRA。
4. 想记录实验，MLflow 管参数、指标和权重。
5. 想做 RAG，Chroma/FAISS 建索引。
6. 想调度任务，Ray 管并发和 GPU。
7. 想看资源，Prometheus/Grafana 看显存、温度、延迟。

这一套跑通以后，你就拥有了一个真正可迭代的个人 AI 工作站。

等到未来你有多机、多用户、多团队协作、多环境发布和权限治理需求，再把其中一部分迁移到 Kubernetes、Kubeflow 或企业级平台也不迟。先把自己的闭环跑顺，才是最高性价比的第一步。
