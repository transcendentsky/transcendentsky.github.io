---
title: vLLM 部署攻略：从单卡启动到生产服务
tags:
  - vLLM
  - LLM Inference
  - AI Infra
  - Deployment
---

> vLLM 是当前开源大模型推理部署里非常关键的一块基础设施。它的价值不只是“能把模型跑起来”，而是通过 PagedAttention、连续批处理、KV Cache 管理、OpenAI 兼容 API、多 GPU 并行和监控接口，把大模型变成可被业务系统调用的高吞吐服务。本文给一份面向个人开发者和小团队的部署攻略：先单机跑通，再理解参数，再进入生产化。

![vLLM deployment architecture](/assets/images/vllm-deployment-guide/architecture.svg)

<!--more-->

## 一、什么时候应该用 vLLM

如果只是本地试模型、低频聊天，Ollama 或 llama.cpp 更轻。如果目标是对外提供 OpenAI 兼容接口、支撑 RAG/Agent 后端、做批量推理或提高 GPU 利用率，vLLM 更合适。

| 场景 | 是否适合 vLLM | 原因 |
| --- | --- | --- |
| 本地随便试模型 | 一般 | Ollama 更简单 |
| 企业 RAG 后端 | 适合 | OpenAI 兼容 API，便于接 LangChain、LlamaIndex、Dify、MaxKB |
| Agent 工具调用后端 | 适合 | 支持流式输出、Chat Completions、服务化调用 |
| 高并发推理服务 | 很适合 | 连续批处理和 KV Cache 管理能提高吞吐 |
| 批量离线生成 | 适合 | Python API 和批处理能力可直接集成任务系统 |
| 端侧 CPU 推理 | 不适合 | llama.cpp 更合适 |

一句话判断：**只要你要把本地或私有模型包装成稳定 API 服务，vLLM 就值得优先评估。**

## 二、vLLM 的部署形态

vLLM 主要有三种使用方式。

| 方式 | 命令入口 | 适合场景 |
| --- | --- | --- |
| Python 离线推理 | `from vllm import LLM` | 批量生成、评测、数据合成 |
| OpenAI 兼容服务 | `vllm serve` | 在线 API 服务、RAG/Agent 后端 |
| Docker 服务 | `vllm/vllm-openai` | 生产部署、隔离环境、快速迁移 |

本文重点讲在线服务和 Docker 部署，因为这是商业系统里最常见的形态。

## 三、部署前准备

### 1. 硬件和系统

生产环境优先选择 Linux + NVIDIA GPU。官方文档也提供 AMD ROCm、Intel XPU、Apple Silicon 等镜像或路径，但主流生产实践仍以 NVIDIA CUDA 为主。

最低要确认：

```bash
nvidia-smi
docker --version
docker compose version
```

如果使用 Docker，还需要 NVIDIA Container Toolkit：

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

这条命令能看到 GPU，说明 Docker 容器里可以访问显卡。

### 2. 显存估算

部署前先估算模型权重和 KV Cache。

| 模型规模 | BF16/FP16 权重大致显存 | 常见部署建议 |
| --- | --- | --- |
| 7B / 8B | 14-16GB | 24GB 单卡可跑，适合个人和小团队 |
| 14B | 28-32GB | 40GB/48GB 单卡更稳，24GB 需量化或压上下文 |
| 32B | 64GB 左右 | 80GB 单卡或多卡张量并行 |
| 70B | 140GB 左右 | 多卡 TP，通常 2-4 张 80GB 起步 |

这只是权重显存，不包含 KV Cache、CUDA Graph、运行时缓存和并发请求。长上下文和高并发会显著增加 KV Cache 占用。

## 四、方式一：直接用 pip 安装

适合本地开发和调试。

```bash
conda create -n vllm python=3.12 -y
conda activate vllm
pip install vllm
```

安装后启动一个小模型：

```bash
vllm serve Qwen/Qwen2.5-1.5B-Instruct \
  --host 0.0.0.0 \
  --port 8000
```

测试接口：

```bash
curl http://127.0.0.1:8000/v1/models
```

Chat Completions 测试：

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-1.5B-Instruct",
    "messages": [
      {"role": "user", "content": "用三句话解释 vLLM 的核心价值"}
    ],
    "temperature": 0.7
  }'
```

如果这一步能成功，说明模型加载、服务端口和 OpenAI 兼容接口都已经跑通。

## 五、方式二：Docker 快速部署

官方 Docker 镜像是生产部署的推荐入口之一，镜像名是：

```text
vllm/vllm-openai
```

最小启动命令：

```bash
docker run --runtime nvidia --gpus all \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --env "HF_TOKEN=$HF_TOKEN" \
  -p 8000:8000 \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2.5-1.5B-Instruct
```

几个参数必须理解：

| 参数 | 作用 |
| --- | --- |
| `--gpus all` | 让容器访问所有 GPU |
| `-v ~/.cache/huggingface:/root/.cache/huggingface` | 复用 Hugging Face 模型缓存，避免重复下载 |
| `--env HF_TOKEN=$HF_TOKEN` | 访问需要授权的模型 |
| `-p 8000:8000` | 暴露 OpenAI 兼容 API 服务 |
| `--ipc=host` | 让 PyTorch 多进程共享内存更稳定 |
| `--model` | 指定加载的模型 |

官方文档也说明，可以用 `--ipc=host` 或 `--shm-size` 解决容器共享内存问题。生产环境里这个点很重要，否则模型加载或多进程运行可能出现不稳定。

## 六、推荐 docker-compose 配置

单机生产环境建议不要手写一长串 `docker run`。可以使用 Compose 管理端口、缓存目录、环境变量和重启策略。

```yaml
services:
  vllm:
    image: vllm/vllm-openai:latest
    container_name: vllm-qwen
    restart: unless-stopped
    ipc: host
    ports:
      - "8000:8000"
    environment:
      HF_TOKEN: ${HF_TOKEN}
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
      - vllm-cache:/root/.cache/vllm
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    command:
      - --model
      - Qwen/Qwen2.5-7B-Instruct
      - --host
      - 0.0.0.0
      - --port
      - "8000"
      - --served-model-name
      - qwen2.5-7b
      - --gpu-memory-utilization
      - "0.90"
      - --max-model-len
      - "8192"

volumes:
  vllm-cache:
```

启动：

```bash
docker compose up -d
docker logs -f vllm-qwen
```

测试：

```bash
curl http://127.0.0.1:8000/v1/models
```

业务系统里就可以把它当成 OpenAI 兼容服务：

```text
base_url = http://你的服务器:8000/v1
model    = qwen2.5-7b
api_key  = 可选，看你是否启用鉴权
```

## 七、关键启动参数

部署 vLLM 时，最常调的是这些参数。

| 参数 | 作用 | 建议 |
| --- | --- | --- |
| `--served-model-name` | 对外暴露的模型名 | 不要直接暴露长 HF 路径，给业务系统一个稳定名称 |
| `--max-model-len` | 最大上下文长度 | 不要盲目开到模型上限，长上下文会吃 KV Cache |
| `--gpu-memory-utilization` | vLLM 可使用的 GPU 显存比例 | 默认约 0.92；生产可从 0.85-0.92 试 |
| `--kv-cache-memory-bytes` | 手动指定 KV Cache 显存 | 需要精细控制显存时使用，会覆盖 `gpu-memory-utilization` 的推断 |
| `--tensor-parallel-size` | 张量并行 GPU 数 | 单机多卡部署大模型时使用 |
| `--pipeline-parallel-size` | 流水线并行大小 | 跨节点或超大模型时考虑 |
| `--quantization` | 量化方式 | 使用 AWQ、GPTQ、FP8 等量化模型时指定或由模型配置识别 |
| `--api-key` | API 鉴权 | 对外服务必须启用，内网也建议加 |
| `--enable-per-request-metrics` | 单请求指标 | 调试 SLA 和计费有用，高并发要评估 CPU 开销 |

一个更接近生产的启动示例：

```bash
vllm serve Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --served-model-name qwen2.5-7b \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --api-key "$VLLM_API_KEY"
```

调用时带上鉴权：

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer $VLLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-7b",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

## 八、多 GPU 部署

如果模型单卡放不下，先考虑张量并行。

单机 4 卡：

```bash
vllm serve meta-llama/Llama-3.1-70B-Instruct \
  --tensor-parallel-size 4 \
  --host 0.0.0.0 \
  --port 8000
```

Docker：

```bash
docker run --runtime nvidia --gpus all \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --env "HF_TOKEN=$HF_TOKEN" \
  -p 8000:8000 \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-3.1-70B-Instruct \
  --tensor-parallel-size 4
```

多机部署时可以使用 Ray 或 multiprocessing。官方文档建议多节点环境保持相同的模型路径和 Python 包环境，容器镜像是更稳的做法。

一个典型多节点思路：

| 部署方式 | 适用场景 | 说明 |
| --- | --- | --- |
| 单机单卡 | 7B/8B/小模型 | 最简单，先用它打通链路 |
| 单机多卡 TP | 32B/70B | 常见大模型部署方式 |
| 多机 TP/PP + Ray | 单机显存不够或超大模型 | 环境一致性、网络和 NCCL 是关键 |
| 多副本 + 网关 | 高并发生产服务 | 每个副本加载一份模型，通过网关负载均衡 |

实践建议：**能单机解决就不要先上多机。** 多机问题通常不在 vLLM 本身，而在镜像一致性、网络、NCCL、驱动、模型缓存和运维复杂度。

## 九、请求生命周期和性能瓶颈

理解 vLLM 的请求链路，有助于定位性能问题。

![vLLM request lifecycle](/assets/images/vllm-deployment-guide/request-flow.svg)

一次请求大致分为：

1. API Server 接收 OpenAI 兼容请求。
2. CPU 执行 tokenizer、chat template、请求校验。
3. GPU 执行 prefill，处理输入 prompt 并建立 KV Cache。
4. GPU 执行 decode，逐 token 生成输出。
5. API Server 流式或一次性返回结果。
6. `/metrics` 暴露吞吐、延迟、队列、KV Cache 等指标。

常见瓶颈如下。

| 现象 | 可能瓶颈 | 处理方式 |
| --- | --- | --- |
| 首 token 很慢 | prompt 太长、prefill 压力大 | 降低上下文、做 prompt 缓存、控制 RAG 注入长度 |
| 输出 tokens/s 低 | GPU 利用率不足或批处理不充分 | 增加并发、调整批处理、检查 CPU 调度 |
| 高并发排队严重 | KV Cache 不够或单副本容量不足 | 降低 `max-model-len`，增加副本或显存 |
| GPU 显存 OOM | 权重 + KV Cache 超预算 | 降低 `gpu-memory-utilization`、上下文、并发，或使用量化 |
| GPU 利用率低但延迟高 | CPU tokenization / 调度瓶颈 | 增加 CPU 核数，减少过长模板和流式开销 |
| 服务偶发卡顿 | 模型首次编译、缓存未复用 | 挂载 `VLLM_CACHE_ROOT`，预热模型 |

## 十、监控和压测

vLLM 的 OpenAI 兼容服务提供 `/metrics` 端点，适合接 Prometheus。

```bash
curl http://127.0.0.1:8000/metrics
```

生产监控至少看这些指标维度：

| 指标 | 含义 |
| --- | --- |
| QPS | 每秒请求数 |
| input tokens/s | 输入吞吐，主要影响 prefill |
| output tokens/s | 输出吞吐，主要影响 decode |
| TTFT | Time To First Token，首 token 延迟 |
| TPOT | Time Per Output Token，单 token 输出延迟 |
| P95/P99 latency | 高分位延迟 |
| GPU utilization | GPU 利用率 |
| GPU memory | 显存占用 |
| KV Cache usage | KV Cache 是否接近上限 |
| queue time | 请求排队时间 |

压测时不要只看单个请求延迟。大模型服务的核心是并发下的延迟和吞吐平衡。

一个简单压测方法：

1. 准备短 prompt、中 prompt、长 prompt 三类请求。
2. 分别测试并发 1、4、8、16、32。
3. 记录 TTFT、总延迟、输出 tokens/s、错误率和显存。
4. 找到 SLA 可接受的最大并发。

## 十一、与 RAG / Agent 框架集成

vLLM 的一个核心优势是 OpenAI API 兼容，因此大部分框架只需要改 `base_url` 和 `model`。

### 1. OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
)

resp = client.chat.completions.create(
    model="qwen2.5-7b",
    messages=[
        {"role": "user", "content": "解释一下 KV Cache 为什么影响并发容量"}
    ],
)

print(resp.choices[0].message.content)
```

如果启动 vLLM 时配置了 `--api-key`，这里的 `api_key` 要换成真实值。

### 2. Dify / MaxKB / LlamaIndex / LangChain

一般配置：

| 配置项 | 值 |
| --- | --- |
| Provider | OpenAI Compatible |
| Base URL | `http://vllm-server:8000/v1` |
| Model | `--served-model-name` 配置的名称 |
| API Key | vLLM 的 `--api-key` 或占位值 |
| Streaming | 建议开启 |

注意：RAG 框架注入的上下文越长，prefill 越慢，KV Cache 压力越大。生产环境要限制召回片段数、单片段长度和历史对话轮数。

## 十二、生产环境部署建议

### 1. 不要裸奔公网

vLLM 自带 API 服务，但生产环境建议放在网关后面。

推荐结构：

```text
Client -> API Gateway / Nginx -> vLLM Server -> GPU
```

网关负责：

| 能力 | 原因 |
| --- | --- |
| HTTPS | 避免明文传输 |
| 鉴权 | 防止服务被滥用 |
| 限流 | 防止单用户打满 GPU |
| 请求大小限制 | 避免超长 prompt 拖垮服务 |
| 日志审计 | 追踪问题和成本 |
| 超时控制 | 防止连接长期占用 |

### 2. 单模型单服务，复杂需求用网关聚合

官方 quickstart 提到，OpenAI 兼容服务默认一次托管一个模型。实践中也建议每个 vLLM 实例只加载一个主模型。多模型路由交给上层网关或模型路由服务。

这样做的好处：

| 做法 | 好处 |
| --- | --- |
| 一个实例一个模型 | 资源边界清楚，故障影响小 |
| 多副本同模型 | 易于水平扩展和灰度 |
| 网关做模型路由 | 业务系统无需关心后端实例 |
| 指标按模型区分 | 成本和 SLA 更容易统计 |

### 3. 配置预热

模型服务启动后，建议先执行几次预热请求。

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-7b",
    "messages": [{"role": "user", "content": "hello"}],
    "max_tokens": 16
  }'
```

预热可以减少首次请求触发编译、加载或缓存初始化导致的异常延迟。

### 4. 持久化缓存

Docker 部署时建议至少挂载：

| 缓存 | 作用 |
| --- | --- |
| Hugging Face cache | 保存模型权重，避免每次拉取 |
| vLLM cache | 保存编译缓存，降低容器重建后的冷启动成本 |

官方 Docker 文档也提到，除了模型权重缓存，还可以把 `VLLM_CACHE_ROOT` 对应目录持久化，复用 torch.compile、Triton 等编译产物。

## 十三、故障排查清单

| 问题 | 排查命令 | 处理 |
| --- | --- | --- |
| 容器看不到 GPU | `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` | 安装或修复 NVIDIA Container Toolkit |
| 模型下载失败 | `docker logs vllm-qwen` | 检查网络、HF_TOKEN、模型授权 |
| 启动 OOM | `nvidia-smi` | 降低 `max-model-len`、`gpu-memory-utilization`，换量化模型 |
| 请求 401 | 查看启动参数 | 检查 `--api-key` 和 Authorization header |
| 请求模型名不存在 | `curl /v1/models` | 使用 `--served-model-name` 暴露的名称 |
| 首次请求很慢 | 查看日志和 GPU 利用率 | 预热、持久化编译缓存 |
| 多卡启动失败 | `NCCL_DEBUG=INFO` | 检查卡数、驱动、NCCL、容器网络 |
| RAG 响应慢 | 记录 prompt token 数 | 减少召回片段和历史对话 |

## 十四、推荐部署路径

如果你是个人或小团队，可以按这个顺序推进。

| 阶段 | 目标 | 动作 |
| --- | --- | --- |
| 第 1 阶段 | 单机跑通 | Docker 启动 1.5B 或 7B 模型 |
| 第 2 阶段 | 接入应用 | 用 OpenAI SDK、Dify、MaxKB 或 LangChain 调用 |
| 第 3 阶段 | 参数稳定 | 固定 `served-model-name`、`max-model-len`、显存比例 |
| 第 4 阶段 | 监控压测 | 接 `/metrics`，做并发和长上下文压测 |
| 第 5 阶段 | 安全上线 | 网关、HTTPS、鉴权、限流、日志 |
| 第 6 阶段 | 扩展容量 | 多副本、多 GPU TP 或更大模型 |

我建议第一版不要追求“大模型 + 长上下文 + 高并发”同时满足。先选一个 7B/8B Instruct 模型，把 API、RAG、监控、压测、权限跑完整，再决定是否换 32B/70B 或多卡。

## 十五、总结

vLLM 部署的核心不是把命令跑起来，而是把模型服务变成稳定、可观测、可扩展的基础设施。

最关键的几条经验：

1. 单机单模型先跑通，再考虑多卡和多副本。
2. `max-model-len` 不要盲目开到最大，长上下文会直接消耗 KV Cache。
3. 生产环境必须有网关、鉴权、限流和监控。
4. RAG/Agent 场景要控制 prompt 长度，否则推理服务会被 prefill 拖慢。
5. Docker 部署要持久化模型缓存和 vLLM 编译缓存。
6. 评估服务能力时同时看 TTFT、TPOT、吞吐、P95/P99 延迟和错误率。

如果只是个人测试，`docker run + Qwen 7B` 就够了；如果要支撑业务系统，vLLM 应该被纳入完整 AI Infra：模型缓存、API 网关、监控告警、压测基线、容量规划和升级流程都要一起设计。

## 参考资料

- vLLM 官方文档：https://docs.vllm.ai/
- vLLM Docker 部署文档：https://docs.vllm.ai/en/latest/deployment/docker/
- vLLM Quickstart：https://docs.vllm.ai/en/latest/getting_started/quickstart/
- vLLM CLI `serve` 参数：https://docs.vllm.ai/en/latest/cli/serve/
- vLLM 并行与扩展文档：https://github.com/vllm-project/vllm/blob/main/docs/serving/parallelism_scaling.md
- vLLM 监控指标文档：https://docs.vllm.ai/en/latest/usage/metrics/
