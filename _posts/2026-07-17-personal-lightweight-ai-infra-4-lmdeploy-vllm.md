---
title: 个人轻量 AI Infra（四）：详细讲讲 LMDeploy 和 vLLM
tags:
  - AI Infra
  - vLLM
  - LMDeploy
  - LLM Inference
---

> 一句话总结：在个人轻量 AI Infra 里，LMDeploy 和 vLLM 是“推理服务层”的核心组件。它们负责把本地模型变成稳定、可并发、OpenAI 兼容的 API，让 RAG、Agent、Web 应用和批量评测都能用同一套接口调用模型。

![个人 AI Infra 的推理服务层](/assets/images/personal-ai-infra-serving/serving-layer.svg)

<!--more-->

前面几篇已经把个人 AI Infra 的几块拼图讲了一遍：

1. 第一篇讲整体方案：Ray + MLflow + LMDeploy/vLLM + XTuner + Chroma/FAISS + 监控。
2. 第二篇讲 Ray：它是任务调度和资源编排层。
3. 第三篇讲 MLflow：它是实验记录和模型资产层。

这篇讲第四块：**推理服务层**。

推理服务层要解决的问题很直接：你已经有了一个 base model，或者通过 XTuner 微调出了一个 LoRA/merged model，接下来怎么让它稳定地提供服务？

最朴素的办法是写一个 Python 脚本，加载 Hugging Face 模型，然后用 FastAPI 包一层。但很快你会遇到很多问题：

1. 多个请求同时进来时怎么 batch？
2. KV Cache 怎么分配和复用？
3. 首 token 延迟为什么这么高？
4. 长上下文为什么显存突然爆掉？
5. 多轮对话越来越慢怎么办？
6. LoRA 模型要不要合并？
7. 要不要量化？量化后质量会不会掉？
8. RAG 和 Agent 都要调同一个模型，接口怎么统一？
9. 怎么统计吞吐、延迟、显存、失败请求？

LMDeploy 和 vLLM 要解决的就是这些问题。

它们不是训练框架，也不是实验平台，而是把模型变成高性能在线服务的推理框架。

## 一、推理服务层在个人 AI Infra 里的定位

推理服务层夹在模型资产和上层应用之间。

| 层次 | 代表工具 | 负责什么 |
| --- | --- | --- |
| 模型资产层 | MLflow / 本地模型目录 | 记录模型来源、权重、配置、评测 |
| 推理服务层 | vLLM / LMDeploy | 加载模型、管理 KV Cache、提供 API |
| 调度层 | Ray | 批量请求、评测任务、服务进程管理 |
| 应用层 | RAG / Agent / Web / Notebook | 调用模型完成业务任务 |
| 监控层 | Prometheus / Grafana / logs | 看延迟、吞吐、显存、错误 |

推理服务层最重要的目标不是“能跑”，而是：

1. **稳定**：长时间运行不频繁 OOM。
2. **高吞吐**：多个请求能合并调度。
3. **低延迟**：首 token 和后续 token 都足够快。
4. **接口统一**：最好兼容 OpenAI API。
5. **可调参**：显存占用、上下文长度、并发、量化可控。
6. **可观测**：能看到请求、错误、性能指标。

个人工作站上尤其要关注显存。因为你可能只有一张 24GB、32GB 或 48GB 的卡，既想跑模型服务，又想跑微调、RAG embedding、批量评测和 Agent 实验。

## 二、vLLM 和 LMDeploy 分别是什么？

### vLLM

vLLM 是一个高性能 LLM 推理和服务框架。它的核心优势是：

1. OpenAI 兼容服务做得成熟。
2. Python 生态友好。
3. 社区模型支持广。
4. PagedAttention/KV Cache 管理能力强。
5. 支持 prefix caching、LoRA、量化、分布式推理等能力。
6. 很适合作为 RAG、Agent、本地应用的通用后端。

vLLM 官方文档里，OpenAI-compatible server 可以通过 `vllm serve` 启动，并使用 OpenAI Python client 以 `base_url="http://localhost:8000/v1"` 的方式调用。

### LMDeploy

LMDeploy 是 OpenMMLab 体系里的 LLM 压缩、部署和服务工具。它的核心优势是：

1. TurboMind 推理后端。
2. persistent batch / continuous batching。
3. blocked KV cache。
4. dynamic split & fuse。
5. tensor parallelism。
6. AWQ/GPTQ、KV Cache int4/int8 等量化能力。
7. 对 InternLM/Qwen/VLM 等场景比较友好。

LMDeploy 官方文档强调它支持 OpenAI 兼容服务，可以用 `lmdeploy serve api_server` 启动，并通过 `/v1/chat/completions`、`/v1/completions`、`/v1/models` 等接口访问。

简单说：

| 工具 | 可以怎么理解 |
| --- | --- |
| vLLM | 通用、生态强、OpenAI API 友好、上手快 |
| LMDeploy | 部署和压缩能力强，TurboMind/量化/KV cache 优化突出 |

![vLLM 与 LMDeploy 对比](/assets/images/personal-ai-infra-serving/vllm-lmdeploy-compare.svg)

## 三、个人玩家应该怎么选？

不要把这个问题变成信仰之争。个人 AI Infra 最重要的是快速跑通、稳定迭代、能定位问题。

我建议：

| 场景 | 优先选择 |
| --- | --- |
| 第一次搭本地 OpenAI 兼容 API | vLLM |
| RAG/Agent 后端，依赖 OpenAI client | vLLM |
| 想快速支持更多 Hugging Face 模型 | vLLM |
| 对 InternLM/Qwen 生态和 TurboMind 更熟 | LMDeploy |
| 强调 AWQ/GPTQ/KV cache 量化组合 | LMDeploy |
| 显存紧张，希望尝试 KV int4/int8 | LMDeploy |
| 做 VLM 部署并参考 OpenMMLab 文档 | LMDeploy |
| 需要对比吞吐、延迟、显存 | 两个都测 |

我的个人建议是：

1. **先用 vLLM 跑通通用 API**。
2. **再用 LMDeploy 做量化、吞吐和显存优化对照**。
3. **最后以实际压测结果决定常驻服务**。

不要只看网上 benchmark。你的显卡、模型、上下文长度、并发模式、prompt 长度、输出长度都会影响结果。

## 四、安装方式

### vLLM

常见安装：

```bash
pip install -U vllm
```

如果你的 CUDA、PyTorch、驱动版本比较特殊，建议参考 vLLM 官方安装文档选择对应 wheel 或 Docker 镜像。

### LMDeploy

常见安装：

```bash
pip install -U lmdeploy
```

如果要用特定 GPU、量化能力或 Docker，也建议参考 LMDeploy 官方安装文档。

个人工作站上，安装前先确认：

```bash
nvidia-smi
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

如果 PyTorch 都没有正确识别 GPU，推理框架一定也会出问题。

## 五、用 vLLM 启动 OpenAI 兼容 API

最小启动命令：

```bash
vllm serve Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --api-key local-token
```

调用方式：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="local-token",
)

response = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "用三句话解释 KV Cache。"},
    ],
    temperature=0.3,
)

print(response.choices[0].message.content)
```

常用参数：

| 参数 | 作用 | 个人建议 |
| --- | --- | --- |
| `--host` | 监听地址 | 本机外部访问用 `0.0.0.0` |
| `--port` | 服务端口 | 默认 8000，可按模型区分 |
| `--dtype` | 权重和激活 dtype | 通常先用 `auto` |
| `--gpu-memory-utilization` | 当前实例可用 GPU 显存比例 | 单服务可 0.85-0.9，多服务要降低 |
| `--max-model-len` | 最大上下文长度 | 不要盲目拉满 |
| `--tensor-parallel-size` | 张量并行 GPU 数 | 多卡大模型使用 |
| `--kv-cache-dtype` | KV cache dtype | 显存紧张可研究 fp8 |
| `--enable-prefix-caching` | 前缀缓存 | RAG/固定 system prompt 场景可尝试 |

例如限制显存和上下文：

```bash
vllm serve Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --gpu-memory-utilization 0.82 \
  --max-model-len 8192 \
  --api-key local-token
```

这里的重点是：**不要迷信最大上下文**。

很多模型标称支持很长上下文，但你的显存不一定支持高并发长上下文。个人机器上更实用的策略是：

1. 默认上下文设得保守一点。
2. RAG 控制 chunk 数和 prompt 长度。
3. 长文本任务单独起服务或降低并发。
4. 压测时覆盖短请求和长请求。

## 六、用 LMDeploy 启动 OpenAI 兼容 API

最小启动命令：

```bash
lmdeploy serve api_server Qwen/Qwen2.5-7B-Instruct \
  --server-name 0.0.0.0 \
  --server-port 23333
```

调用方式同样可以用 OpenAI client：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:23333/v1",
    api_key="local-token",
)

model_name = client.models.list().data[0].id

response = client.chat.completions.create(
    model=model_name,
    messages=[
        {"role": "user", "content": "解释一下连续批处理为什么能提升吞吐。"},
    ],
    temperature=0.3,
)

print(response.choices[0].message.content)
```

常用参数：

| 参数 | 作用 | 个人建议 |
| --- | --- | --- |
| `--server-name` | 监听地址 | 本机外部访问用 `0.0.0.0` |
| `--server-port` | 服务端口 | 默认常用 23333 |
| `--tp` | tensor parallel | 多卡部署大模型 |
| `--session-len` | 最大会话长度 | 控制上下文和显存 |
| `--cache-max-entry-count` | KV cache 占用 GPU 显存比例 | OOM 时优先调低 |
| `--backend` | 推理后端 | 常见是 `turbomind` 或 `pytorch` |

例如：

```bash
lmdeploy serve api_server Qwen/Qwen2.5-7B-Instruct \
  --server-name 0.0.0.0 \
  --server-port 23333 \
  --session-len 8192 \
  --cache-max-entry-count 0.7
```

LMDeploy 文档里也提到，如果服务端 OOM，可以降低 `cache_max_entry_count` 相关配置。个人机器上这个参数非常重要，因为它直接关系到 KV cache 能占多少显存。

## 七、OpenAI 兼容接口为什么重要？

个人 AI Infra 里，我非常建议统一成 OpenAI 兼容接口。

原因很简单：

| 上层组件 | 好处 |
| --- | --- |
| RAG | LangChain/LlamaIndex/自写代码都容易接 |
| Agent | 工具调用、chat completion 接口统一 |
| Notebook | 快速切换本地模型和云模型 |
| Web 应用 | 后端只改 base_url |
| 批量评测 | 同一套脚本可测多个服务 |
| 线上回滚 | 替换服务地址或模型名即可 |

一个统一配置可以这样写：

```bash
export OPENAI_BASE_URL=http://localhost:8000/v1
export OPENAI_API_KEY=local-token
export OPENAI_MODEL=Qwen/Qwen2.5-7B-Instruct
```

Python 里：

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.environ["OPENAI_BASE_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
)

def chat(prompt: str) -> str:
    response = client.chat.completions.create(
        model=os.environ["OPENAI_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content
```

这样你的 RAG、Agent、评测脚本都不用关心底层是 vLLM 还是 LMDeploy。

## 八、理解几个核心性能指标

推理服务不要只看“感觉快不快”。至少要看这些指标。

| 指标 | 含义 | 为什么重要 |
| --- | --- | --- |
| TTFT | Time To First Token，首 token 时间 | 影响交互体感 |
| TPOT | Time Per Output Token，后续 token 间隔 | 影响生成速度 |
| tokens/s | 每秒生成 token 数 | 吞吐核心指标 |
| request/s | 每秒完成请求数 | 服务承载能力 |
| P50/P95/P99 latency | 延迟分位数 | 看尾延迟 |
| GPU memory | 显存占用 | 决定模型和并发上限 |
| GPU utilization | GPU 利用率 | 判断是否吃满 |
| KV cache usage | KV cache 使用情况 | 长上下文和并发瓶颈 |
| error rate | 请求失败率 | 稳定性指标 |

个人项目里，我建议最少记录：

1. P50/P95 延迟。
2. 平均 tokens/s。
3. 显存峰值。
4. 并发数。
5. 输入/输出 token 长度分布。
6. OOM 和 timeout 次数。

否则你很难判断一次优化到底有没有用。

## 九、KV Cache：推理服务的显存核心

大模型推理分两段：

1. **Prefill**：处理输入 prompt，生成 KV cache。
2. **Decode**：逐 token 生成输出，复用 KV cache。

KV Cache 的好处是避免每生成一个 token 都重新计算整个上下文。但代价是占显存。

上下文越长、并发越高、层数越多、hidden size 越大，KV cache 就越大。

可以粗略理解为：

```text
KV Cache 显存 ~= batch_size * seq_len * num_layers * hidden_dim * dtype_size * 2
```

这里的 `2` 是 K 和 V。

这就是为什么：

1. 7B 模型短上下文很轻松。
2. 7B 模型长上下文 + 高并发也会 OOM。
3. 32B 模型即使能加载权重，也不一定能承受高并发。
4. KV cache 量化能提升并发和吞吐，但要评估质量损失。

vLLM 和 LMDeploy 都围绕 KV cache 做了大量优化。区别在于调参方式和实现路径不同。

## 十、量化：先问目标，再选方案

量化不是越低越好。个人部署前先问自己：

1. 我是权重放不下，还是 KV cache 放不下？
2. 我更在乎吞吐，还是回答质量？
3. 模型是通用聊天，还是专业领域问答？
4. 是否需要长上下文？
5. 是否要跑多并发？

常见量化对象：

| 量化对象 | 解决什么问题 | 风险 |
| --- | --- | --- |
| 权重量化 | 降低模型权重显存 | 可能影响质量 |
| KV cache 量化 | 提升长上下文和并发能力 | 可能影响长文本质量 |
| 激活量化 | 提升推理效率 | 工程复杂度更高 |

LMDeploy 官方文档提到，它支持在线 KV cache int4/int8 量化，int8 通常更稳，int4 更激进。vLLM 也支持多种量化方式和 KV cache dtype 配置，例如 fp8 KV cache。

个人建议：

| 目标 | 推荐尝试 |
| --- | --- |
| 先稳定跑通 | BF16/FP16，不量化 |
| 权重放不下 | AWQ/GPTQ/FP8 等权重量化 |
| 并发上不去 | KV cache 量化或降低上下文 |
| 质量敏感 | 先做评测再量化 |
| RAG 场景 | 特别关注引用准确率和长上下文质量 |

不要只看速度。量化后一定要跑业务评测集。

## 十一、长上下文：不是参数越大越好

很多人看到 `--max-model-len` 或 `--session-len`，第一反应是拉满。

这通常不是好主意。

长上下文的代价包括：

1. prefill 更慢。
2. KV cache 更大。
3. 并发能力下降。
4. 尾延迟上升。
5. RAG 输入噪声增加。

个人工作站更建议按业务分层：

| 场景 | 建议上下文 |
| --- | --- |
| 普通聊天 | 4K-8K |
| RAG 问答 | 8K-16K |
| 长文总结 | 16K-32K，单独服务 |
| 代码仓库分析 | 按任务拆分，不要盲目全塞 |
| Agent 工具调用 | 控制 memory 和 trace 摘要 |

如果你确实需要长上下文，先压测这三种请求：

1. 短输入短输出。
2. 长输入短输出。
3. 长输入长输出。

很多服务在第一种请求下表现很好，但在第二种和第三种下延迟非常难看。

## 十二、LoRA 推理：合并还是动态加载？

个人微调常见产物是 LoRA adapter。部署时有两条路：

| 方式 | 优点 | 缺点 |
| --- | --- | --- |
| 合并 LoRA 到 base model | 推理简单、性能稳定 | 每个 adapter 都要生成 merged model |
| 动态加载 LoRA | 多任务切换灵活 | 需要框架支持，调试复杂 |

个人 AI Infra 初期，我建议：

1. 重要模型先 merge。
2. 每个 merged model 作为一个明确版本记录到 MLflow。
3. 用 vLLM/LMDeploy 启动 merged model。
4. 后续多 LoRA 场景再考虑动态 adapter。

原因很简单：个人项目最怕变量太多。

如果你同时调 base model、LoRA adapter、prompt、推理框架、量化配置，一旦效果变差，很难定位。

先用 merged model 把链路跑稳，再逐步引入动态 LoRA。

## 十三、和 MLflow 怎么接？

第三篇讲过，MLflow 是实验账本。推理服务也应该记录。

每次部署都应该有一个 run：

```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("local-llm-serving")

with mlflow.start_run(run_name="serve-qwen-vllm-7b-v1"):
    mlflow.log_params({
        "engine": "vllm",
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "port": 8000,
        "dtype": "auto",
        "gpu_memory_utilization": 0.82,
        "max_model_len": 8192,
    })
    mlflow.log_metric("p95_latency_ms", 920)
    mlflow.log_metric("tokens_per_second", 128)
    mlflow.log_metric("peak_gpu_memory_gb", 19.6)
    mlflow.set_tag("stage", "local-production")
```

对于 LMDeploy：

```python
with mlflow.start_run(run_name="serve-qwen-lmdeploy-7b-v1"):
    mlflow.log_params({
        "engine": "lmdeploy",
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "port": 23333,
        "session_len": 8192,
        "cache_max_entry_count": 0.7,
    })
```

这样以后你知道：

1. 哪个模型被部署过。
2. 用哪个引擎部署。
3. 用了什么上下文长度和显存配置。
4. 压测指标是什么。
5. 线上出问题时回滚到哪个版本。

## 十四、和 Ray 怎么接？

Ray 不一定要直接包住 vLLM/LMDeploy 的内部引擎。个人项目里更稳的方式是：

1. vLLM/LMDeploy 作为独立服务常驻。
2. Ray tasks 负责批量请求、评测、数据生成。
3. Ray actors 可以管理多个 API endpoint 的状态。

例如批量评测：

```python
import ray
from openai import OpenAI

ray.init(address="auto")

@ray.remote
def eval_one(sample):
    client = OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="local-token",
    )
    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-7B-Instruct",
        messages=[{"role": "user", "content": sample["question"]}],
        temperature=0.0,
    )
    answer = response.choices[0].message.content
    return {"id": sample["id"], "answer": answer}

results = ray.get([eval_one.remote(s) for s in samples])
```

注意：不要让 Ray 并发数无限大。

推理服务有自己的队列和显存上限。Ray 只是发请求，如果并发太高，会造成 timeout、排队过长、甚至服务崩溃。

可以用分批提交：

```python
batch_size = 32
all_results = []

for i in range(0, len(samples), batch_size):
    refs = [eval_one.remote(s) for s in samples[i:i + batch_size]]
    all_results.extend(ray.get(refs))
```

## 十五、和 RAG/Agent 怎么接？

RAG 和 Agent 最需要的是统一接口和稳定延迟。

一个典型 RAG 调用链：

```text
用户问题
  -> query rewrite
  -> embedding
  -> vector search
  -> rerank
  -> prompt assemble
  -> vLLM/LMDeploy OpenAI API
  -> answer + citations
```

推理服务层要保证：

1. 模型名稳定。
2. base_url 稳定。
3. 超时设置合理。
4. temperature 可控。
5. prompt 长度受控。
6. 错误可以重试。

Agent 场景还要注意：

| 问题 | 建议 |
| --- | --- |
| 多轮工具调用 token 增长 | 定期摘要 memory |
| 工具输出过长 | 截断或结构化 |
| 模型输出格式不稳定 | 使用 structured output 或严格 prompt |
| 并发 agent 太多 | 限制 Ray 并发和 API 队列 |
| latency 波动大 | 记录 P95/P99 而不是只看平均值 |

推理服务不是孤立组件。它的稳定性会直接影响 RAG 和 Agent 的稳定性。

## 十六、压测怎么做？

上线前至少做三类压测。

### 1. 单请求质量测试

看模型是否能正常回答，chat template 是否正确：

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer local-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "hello"}],
    "temperature": 0.2
  }'
```

### 2. 并发短请求

模拟聊天、Agent 工具规划、小问题问答。

关注：

1. request/s。
2. TTFT。
3. P95 latency。
4. 错误率。

### 3. 长上下文请求

模拟 RAG、长文总结、多轮对话。

关注：

1. 显存峰值。
2. KV cache 是否吃紧。
3. timeout 是否增加。
4. 输出质量是否下降。

可以先写一个简单 Python 压测脚本，不必一开始上复杂工具：

```python
import time
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="local-token")

def call_one(i):
    start = time.time()
    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-7B-Instruct",
        messages=[{"role": "user", "content": f"解释一下 KV Cache，编号 {i}"}],
        temperature=0.2,
    )
    return time.time() - start, response.choices[0].message.content

with ThreadPoolExecutor(max_workers=16) as pool:
    results = list(pool.map(call_one, range(100)))

latencies = [x[0] for x in results]
print("avg", sum(latencies) / len(latencies))
print("max", max(latencies))
```

后续再接 Prometheus/Grafana，把指标可视化。

## 十七、监控哪些东西？

推理服务至少要看三层指标。

### 服务层

| 指标 | 说明 |
| --- | --- |
| 请求数 | 服务是否被调用 |
| 错误率 | 是否有 500/timeout/OOM |
| P95/P99 延迟 | 用户真实体感 |
| tokens/s | 生成吞吐 |
| queue time | 请求是否排队严重 |

### GPU 层

| 指标 | 说明 |
| --- | --- |
| 显存占用 | 是否接近 OOM |
| GPU utilization | 是否吃满 |
| power draw | 功耗和散热 |
| temperature | 温度稳定性 |

### 质量层

| 指标 | 说明 |
| --- | --- |
| bad case 数量 | 输出质量问题 |
| 格式错误率 | JSON/工具调用是否稳定 |
| RAG 引用准确率 | 是否胡乱引用 |
| Agent 成功率 | 任务完成情况 |

个人机器上可以先用：

```bash
nvidia-smi -l 1
```

再逐步接入 Prometheus/Grafana。不要一开始为了监控把整套系统搞得很重。

## 十八、常见坑

| 坑 | 表现 | 建议 |
| --- | --- | --- |
| `max_model_len` 设太大 | 服务启动慢、显存紧、并发低 | 按业务设，不要盲目拉满 |
| 并发压太高 | timeout、排队、OOM | Ray 批量提交要限流 |
| 只看平均延迟 | 用户仍觉得卡 | 看 P95/P99 和 TTFT |
| 忽略 prompt 长度 | RAG 上线后突然慢 | 记录输入 token 分布 |
| 量化后不评测 | 速度快但答案差 | 跑业务 eval 和 bad cases |
| LoRA 版本混乱 | 部署错 adapter | 用 MLflow 记录 run 和版本 |
| 模型名不稳定 | 上层应用切换困难 | 统一 served model name |
| API key 缺失 | 局域网内任何人可访问 | 至少设置本地 token |
| 与训练任务抢显存 | 推理服务突然 OOM | Ray 资源规划 + 显存比例控制 |

最常见的教训是：**推理问题往往不是模型本身的问题，而是上下文、并发、显存和队列一起作用的结果。**

## 十九、推荐的个人工作站部署模式

如果你是单机个人玩家，我建议先这样搭：

```text
ai-infra/
  models/
    base/
    merged/
    adapters/
  serving/
    vllm/
      start_qwen_7b.sh
      logs/
    lmdeploy/
      start_qwen_7b.sh
      logs/
  configs/
    serving/
  reports/
    benchmark/
```

一个 vLLM 启动脚本：

```bash
#!/usr/bin/env bash
set -euo pipefail

MODEL="Qwen/Qwen2.5-7B-Instruct"

vllm serve "${MODEL}" \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --gpu-memory-utilization 0.82 \
  --max-model-len 8192 \
  --api-key local-token
```

一个 LMDeploy 启动脚本：

```bash
#!/usr/bin/env bash
set -euo pipefail

MODEL="Qwen/Qwen2.5-7B-Instruct"

lmdeploy serve api_server "${MODEL}" \
  --server-name 0.0.0.0 \
  --server-port 23333 \
  --session-len 8192 \
  --cache-max-entry-count 0.7
```

启动顺序：

1. 先启动 MLflow。
2. 启动 vLLM 或 LMDeploy。
3. 用 curl/OpenAI client 做 smoke test。
4. 跑小规模压测。
5. 把部署参数和压测结果写入 MLflow。
6. 再接 RAG/Agent。

![个人推理服务闭环](/assets/images/personal-ai-infra-serving/serving-feedback-loop.svg)

## 二十、什么时候该从 vLLM 切到 LMDeploy？

可以用几个判断标准：

| 信号 | 可能动作 |
| --- | --- |
| vLLM 已经稳定跑通，但显存吃紧 | 尝试 LMDeploy KV cache quant |
| 需要 AWQ/GPTQ 部署链路 | 尝试 LMDeploy |
| 使用 InternLM/OpenMMLab 生态模型 | 优先试 LMDeploy |
| 需要更强 OpenAI API 生态兼容 | 继续用 vLLM |
| 需要快速跟进社区新模型 | 继续用 vLLM |
| 两者都能跑 | 用真实业务压测决定 |

不要为了“换框架”而换框架。切换应该有明确目标：

1. 降低显存。
2. 提升吞吐。
3. 降低尾延迟。
4. 支持某个模型或量化格式。
5. 简化部署和维护。

## 二十一、总结：推理服务层是个人 AI Infra 的在线入口

Ray 让任务跑起来，MLflow 让结果留下来，而 LMDeploy/vLLM 让模型真正被用起来。

对个人 AI Infra 来说，推理服务层不是一个简单的“启动模型”步骤，而是一个持续优化的系统：

1. 选模型。
2. 选推理引擎。
3. 设上下文和显存参数。
4. 接 OpenAI 兼容 API。
5. 跑压测和业务评测。
6. 记录到 MLflow。
7. 接入 RAG/Agent。
8. 监控延迟、吞吐、显存和 bad cases。
9. 必要时回滚或切换引擎。

个人建议的默认路径是：

```text
先用 vLLM 跑通 OpenAI API
  -> 用 MLflow 记录部署和压测
  -> 用 Ray 做批量评测和数据生成
  -> 如果显存/吞吐不满意，再引入 LMDeploy 对比
  -> 最后按真实业务指标决定常驻服务
```

这就是个人轻量 AI Infra 的第四块拼图：推理服务层。

参考：

1. [vLLM OpenAI-Compatible Server 官方文档](https://docs.vllm.ai/en/v0.8.5/serving/openai_compatible_server.html)
2. [LMDeploy OpenAI Compatible Server 官方文档](https://lmdeploy.readthedocs.io/en/stable/llm/api_server.html)
3. [LMDeploy KV Cache Quantization 官方文档](https://lmdeploy.readthedocs.io/en/stable/quantization/kv_quant.html)
