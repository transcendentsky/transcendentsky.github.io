---
title: 个人轻量 AI Infra（二）：详细讲讲 Ray
tags:
  - AI Infra
  - Ray
  - MLOps
  - Agent
---

> 一句话总结：在个人 AI Infra 里，Ray 最适合扮演“轻量任务调度层”：它不替代 XTuner、vLLM、MLflow，而是把训练、推理、RAG、评测和 Agent 任务按资源约束组织起来。

![Ray 的几个核心概念](/assets/images/personal-ai-infra-ray/ray-concepts.svg)

<!--more-->

上一篇聊了个人轻量 AI Infra 的整体方案：Ray + MLflow + LMDeploy/vLLM + XTuner + Chroma/FAISS + Prometheus/Grafana + Jupyter + Ollama。

这篇单独讲 Ray。

很多人第一次接触 Ray，会把它理解成“分布式计算框架”。这个理解没错，但对个人 AI Infra 来说，Ray 的价值不一定是“分布式到很多机器”，而是：**哪怕只有一台工作站，它也能帮你把任务调度、资源声明、并发隔离和后台执行这几件事管起来。**

如果你只有一张或两张 GPU，Ray 仍然有用。因为个人工作站也会同时跑很多任务：

1. vLLM 或 LMDeploy 常驻推理服务。
2. XTuner 跑 LoRA 微调。
3. 批量推理生成数据。
4. 跑一套评测集。
5. RAG 构建 embedding 索引。
6. Agent 多 worker 并发调用工具。
7. 定时清洗数据、整理日志、生成报告。

没有调度层时，这些任务很容易互相抢资源，最常见的结果就是显存爆掉、服务卡死、训练中断、日志找不到。

Ray 要解决的，就是把这些“零散 Python 脚本”组织成一个可观察、可调度、可并发的工作流。

## 一、Ray 在个人 AI Infra 里的定位

先说清楚：Ray 不是训练框架，不是推理框架，也不是实验管理平台。

| 你要做的事 | 更合适的工具 | Ray 的角色 |
| --- | --- | --- |
| LoRA 微调 | XTuner / LLaMA-Factory / Axolotl | 提交任务、分配 GPU、排队 |
| 高性能推理 | vLLM / LMDeploy | 管常驻服务或批量推理 worker |
| 实验记录 | MLflow | 在任务里记录参数、指标、产物 |
| RAG 检索 | Chroma / FAISS / Qdrant | 并发处理文档、批量 embedding |
| Agent 实验 | LangGraph / 自写 Agent / CrewAI | 调度多个 worker、隔离资源 |
| 数据处理 | Pandas / Polars / PyArrow | 并行清洗、切分、转换 |

Ray 最适合管这几个问题：

1. 任务什么时候跑。
2. 每个任务用多少 CPU/GPU。
3. 多个任务如何并发。
4. 常驻服务如何保持状态。
5. 大对象如何在任务之间传递。
6. 失败任务如何重试或定位。

一句话：**Ray 管“调度和并发”，专业框架管“训练和推理”。**

## 二、Ray 的核心概念

Ray 的概念不多，但很关键。

| 概念 | 解释 | 个人 AI 场景 |
| --- | --- | --- |
| Driver | 提交任务的主 Python 进程 | 你的脚本、Notebook、CLI |
| Task | 无状态远程函数 | 批量推理、数据清洗、评测 |
| Actor | 有状态远程对象 | 模型 worker、Agent worker、服务管理器 |
| Object Store | Ray 的共享对象存储 | 放大数据、模型结果、中间对象 |
| Scheduler | 资源调度器 | 按 CPU/GPU 把任务排到合适 worker |
| Resource | CPU、GPU、自定义资源 | 避免多个任务同时抢 GPU |
| Dashboard | 可视化面板 | 看任务、资源、错误日志 |

理解 Ray 最重要的是区分 Task 和 Actor。

| 类型 | 特点 | 适合 |
| --- | --- | --- |
| Task | 执行完就结束，无状态 | 数据处理、批量推理、评测 |
| Actor | 常驻，有状态，可以多次调用 | 加载模型、维护 Agent 状态、长连接服务 |

例如，你要批量处理 1000 个文档，用 Task；你要加载一次 embedding 模型，然后反复给文档算向量，用 Actor。

## 三、安装和启动 Ray

最小安装：

```bash
pip install -U "ray[default]"
```

启动本机 Ray：

```bash
ray start --head --dashboard-host=0.0.0.0
```

打开 Dashboard：

```text
http://localhost:8265
```

如果只在 Python 脚本里临时使用，也可以不手动 `ray start`，直接：

```python
import ray

ray.init()
```

如果已经启动了 Ray head，则连接它：

```python
import ray

ray.init(address="auto")
```

停止 Ray：

```bash
ray stop
```

个人工作站建议：

| 场景 | 推荐方式 |
| --- | --- |
| 临时脚本 | `ray.init()` |
| 长期使用 | `ray start --head` |
| 多个项目共享 | 固定 Dashboard、日志和临时目录 |
| 调试问题 | 看 Ray Dashboard 和 worker 日志 |

## 四、最小 Task 示例：并行跑批量推理

Ray 最简单的用法，是把一个 Python 函数变成 remote task。

```python
import ray
import time

ray.init(address="auto")

@ray.remote(num_cpus=1)
def process_item(i: int):
    time.sleep(1)
    return {"id": i, "result": i * i}

refs = [process_item.remote(i) for i in range(10)]
results = ray.get(refs)
print(results)
```

这里发生了几件事：

1. `@ray.remote` 把函数注册成 Ray task。
2. `process_item.remote(i)` 提交任务，不会立即阻塞。
3. Ray 根据资源情况并发执行。
4. `ray.get(refs)` 等待结果返回。

如果把它换成批量推理：

```python
@ray.remote(num_cpus=2, num_gpus=0.25)
def run_infer_batch(batch):
    # 这里可以调用本地 vLLM API，或者加载一个小模型做推理
    outputs = []
    for item in batch:
        outputs.append({"input": item, "output": f"answer for {item}"})
    return outputs
```

注意 `num_gpus=0.25` 只是资源声明，不等于 Ray 自动帮你做显存隔离。它的作用是调度层面避免同时安排太多 GPU 任务。真正的显存控制，还要靠模型框架参数，比如 vLLM 的 `gpu_memory_utilization`，以及你自己的并发策略。

## 五、Actor 示例：常驻模型 Worker

如果每个 task 都重新加载模型，速度会非常慢。Actor 适合这种“加载一次，多次调用”的场景。

```python
import ray

ray.init(address="auto")

@ray.remote(num_cpus=2, num_gpus=0.5)
class ModelWorker:
    def __init__(self, model_name: str):
        self.model_name = model_name
        # 真实场景里在这里加载模型
        print(f"load model: {model_name}")

    def generate(self, prompt: str):
        return f"[{self.model_name}] answer: {prompt}"

worker = ModelWorker.remote("qwen-local")

ref1 = worker.generate.remote("解释一下 Ray Actor")
ref2 = worker.generate.remote("Ray 和 vLLM 怎么配合？")

print(ray.get([ref1, ref2]))
```

Actor 适合：

| 场景 | 为什么适合 Actor |
| --- | --- |
| 模型推理 worker | 模型只加载一次 |
| Agent worker | 保留工具、状态、记忆 |
| 数据库连接池 | 保留连接 |
| RAG embedding worker | embedding 模型常驻 |
| 任务管理器 | 维护队列和状态 |

个人 AI Infra 里，Actor 是非常重要的概念。很多服务都可以写成 Actor，而不是一堆散乱后台进程。

## 六、GPU 资源声明：别让任务互相打爆显存

Ray 支持在 task 或 actor 上声明资源：

```python
@ray.remote(num_cpus=4, num_gpus=1)
def train_lora(config_path):
    ...
```

或者：

```python
@ray.remote(num_cpus=2, num_gpus=0.25)
class InferenceWorker:
    ...
```

个人工作站可以这样规划：

| 任务 | Ray 资源声明 | 说明 |
| --- | --- | --- |
| XTuner LoRA 微调 | `num_gpus=1` | 独占 GPU，避免干扰 |
| 小模型批量推理 | `num_gpus=0.25` | 多任务并发，但注意显存 |
| Embedding 文档 | `num_gpus=0.25` 或 CPU | 看 embedding 模型大小 |
| RAG 文档切分 | `num_gpus=0` | CPU 任务 |
| Agent 工具调用 | `num_gpus=0` | 多数工具调用不需要 GPU |
| vLLM 服务 | 常驻外部进程或 Actor | 通常单独管理显存 |

需要强调：Ray 的 `num_gpus` 更像“调度配额”，不是强安全沙箱。它不会自动阻止你的代码申请更多显存。

因此要配合：

1. `CUDA_VISIBLE_DEVICES`。
2. vLLM/LMDeploy 的显存限制参数。
3. 任务排队策略。
4. 监控显存峰值。
5. 必要时不要让训练和推理同时跑。

![个人工作站上的 Ray 调度](/assets/images/personal-ai-infra-ray/ray-workstation-scheduler.svg)

## 七、Ray + XTuner：把微调变成可排队任务

XTuner 本身负责微调，Ray 负责提交和排队。

一个简单包装：

```python
import ray
import subprocess

ray.init(address="auto")

@ray.remote(num_cpus=8, num_gpus=1)
def run_xtuner_train(config_path: str, work_dir: str):
    cmd = [
        "xtuner", "train",
        config_path,
        "--work-dir", work_dir,
    ]
    subprocess.run(cmd, check=True)
    return {"config": config_path, "work_dir": work_dir}

ref = run_xtuner_train.remote(
    "configs/qwen_lora.py",
    "work_dirs/qwen_lora_run_001",
)

print(ray.get(ref))
```

这样做的好处：

1. 微调任务进入 Ray Dashboard。
2. Ray 知道它需要 1 张 GPU。
3. 其他声明 GPU 的任务会按资源排队。
4. 失败时你能看到任务日志。

如果你要同时跑多个小实验，可以提交多个 Ray task，让它们排队执行，而不是手动开多个终端。

## 八、Ray + MLflow：每个任务自动记录实验

Ray 任务里可以直接调用 MLflow。

```python
import ray
import mlflow
import subprocess

ray.init(address="auto")

@ray.remote(num_cpus=8, num_gpus=1)
def train_with_mlflow(config_path, work_dir, base_model, lora_rank):
    mlflow.set_tracking_uri("http://localhost:5000")
    mlflow.set_experiment("personal-ai-infra-ray")

    with mlflow.start_run():
        mlflow.log_param("config", config_path)
        mlflow.log_param("base_model", base_model)
        mlflow.log_param("lora_rank", lora_rank)

        subprocess.run([
            "xtuner", "train",
            config_path,
            "--work-dir", work_dir,
        ], check=True)

        mlflow.log_artifacts(work_dir, artifact_path="xtuner_output")
        return {"status": "ok", "work_dir": work_dir}
```

这样你的训练任务一旦跑完，MLflow 里就会有：

1. 参数。
2. 训练输出。
3. LoRA 权重。
4. 日志。
5. 可追溯的 run id。

个人工作站最怕实验乱，Ray + MLflow 可以把“任务执行”和“实验记录”自然串起来。

## 九、Ray + vLLM/LMDeploy：两种配合方式

Ray 和推理服务有两种配合方式。

### 方式一：推理服务作为外部常驻进程

先启动 vLLM：

```bash
vllm serve /data/models/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --served-model-name qwen-local \
  --gpu-memory-utilization 0.75
```

Ray task 只负责调用 API：

```python
import ray
from openai import OpenAI

ray.init(address="auto")

@ray.remote(num_cpus=1)
def ask_model(prompt: str):
    client = OpenAI(api_key="EMPTY", base_url="http://localhost:8000/v1")
    resp = client.chat.completions.create(
        model="qwen-local",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content

refs = [ask_model.remote(f"问题 {i}") for i in range(20)]
answers = ray.get(refs)
```

这种方式最稳。vLLM/LMDeploy 自己管理模型和显存，Ray 管调用并发。

### 方式二：推理 worker 写成 Ray Actor

适合小模型或自定义推理逻辑：

```python
@ray.remote(num_cpus=2, num_gpus=0.5)
class LocalLLMActor:
    def __init__(self):
        # 加载小模型
        pass

    def generate(self, prompt):
        return "answer"
```

个人建议：

| 场景 | 推荐 |
| --- | --- |
| 大模型服务 | 外部 vLLM/LMDeploy 进程 |
| 小模型 worker | Ray Actor |
| 批量调用本地 API | Ray Tasks |
| Agent 多 worker | Ray Actors + API 调用 |

不要强行把 vLLM 整个塞进 Ray Actor。除非你明确知道自己在处理什么，否则外部服务更简单、更稳定。

## 十、Ray + RAG：并行处理文档和 embedding

RAG 里最适合 Ray 的部分，是批量文档处理：

1. PDF/Markdown 解析。
2. chunk 切分。
3. embedding 计算。
4. 写入 Chroma/FAISS。

示例：

```python
import ray

ray.init(address="auto")

@ray.remote(num_cpus=2)
def parse_doc(path):
    text = open(path, "r", encoding="utf-8").read()
    chunks = [text[i:i+800] for i in range(0, len(text), 800)]
    return [{"path": path, "text": c} for c in chunks]

paths = ["docs/a.md", "docs/b.md", "docs/c.md"]
chunk_lists = ray.get([parse_doc.remote(p) for p in paths])
chunks = [c for item in chunk_lists for c in item]
```

如果 embedding 模型比较大，可以用 Actor 常驻：

```python
@ray.remote(num_cpus=4, num_gpus=0.25)
class EmbeddingWorker:
    def __init__(self):
        # 加载 embedding 模型
        pass

    def embed(self, texts):
        # 返回向量
        return [[0.0] * 768 for _ in texts]
```

这样就不用每个 task 重复加载 embedding 模型。

## 十一、Ray + Agent：多智能体并发实验

Agent 实验天然适合 Ray。

因为一个 Agent 系统里可能有多个 worker：

| Worker | 作用 |
| --- | --- |
| Planner | 拆解任务 |
| Researcher | 搜索和阅读 |
| Coder | 写代码 |
| Evaluator | 评测结果 |
| Tool Worker | 调用本地工具 |

可以把每个 worker 做成 Actor：

```python
@ray.remote(num_cpus=1)
class AgentWorker:
    def __init__(self, role):
        self.role = role

    def run(self, task):
        return f"{self.role} handled {task}"

planner = AgentWorker.remote("planner")
coder = AgentWorker.remote("coder")

plan = ray.get(planner.run.remote("搭一个 RAG demo"))
code = ray.get(coder.run.remote(plan))
print(code)
```

Ray 在 Agent 里的价值：

1. 并发执行多个工具任务。
2. 隔离不同 worker 的状态。
3. 控制 CPU/GPU 资源。
4. 把长任务放后台。
5. 通过 Dashboard 观察失败点。

如果你做多智能体研究或本地 Agent 平台，Ray 比手写 `multiprocessing` 更舒服。

## 十二、Ray Dashboard 看什么？

Ray Dashboard 是个人使用里非常重要的工具。

重点看：

| 页面 | 看什么 |
| --- | --- |
| Jobs | 当前有哪些任务，是否失败 |
| Actors | 哪些 Actor 常驻，是否重启 |
| Cluster | CPU/GPU/RAM 使用情况 |
| Logs | worker 日志和异常 |
| Timeline | 任务耗时和排队情况 |

排查问题时常见路径：

1. 任务没跑：看资源是不是不够。
2. 任务卡住：看 worker 日志。
3. GPU 不动：看任务是否真的申请了 GPU。
4. OOM：看显存和任务并发。
5. 任务排队太久：看资源声明是否过大。

不要只盯终端输出，Dashboard 会让你对本机 AI 工作负载有全局视角。

## 十三、个人使用 Ray 的几个坑

| 坑 | 说明 | 建议 |
| --- | --- | --- |
| 以为 `num_gpus` 是显存硬隔离 | Ray 只做调度声明，不限制代码实际申请显存 | 配合框架显存参数 |
| 每个 task 都加载大模型 | 启动慢、显存爆 | 用 Actor 或外部推理服务 |
| Object Store 放超大对象 | 内存压力大 | 大文件放磁盘，只传路径 |
| task 粒度太小 | 调度开销超过计算收益 | 合并成 batch |
| task 粒度太大 | 并行度上不去 | 切成合理 batch |
| 忘记看日志 | 出错不知道原因 | 用 Dashboard 查 worker logs |
| 和 vLLM 显存抢占 | 两边都以为自己有 GPU | 推理服务限制显存，训练排队 |

个人经验是：Ray 初期不要设计太复杂。先把三件事跑顺：

1. 批量任务。
2. 常驻 Actor。
3. GPU 资源声明。

这三件事熟了，再考虑复杂 DAG、多机集群和生产部署。

## 十四、一个推荐的 Ray 使用模式

对个人 AI Infra，我建议 Ray 的使用模式是：

```text
Ray 负责：
  - 数据处理任务
  - 批量推理任务
  - 微调任务排队
  - Agent worker 并发
  - 后台评测任务

Ray 不负责：
  - 替代 vLLM 的高性能 serving
  - 替代 MLflow 的实验记录
  - 替代 XTuner 的训练细节
  - 替代 Prometheus 的长期监控
```

![Ray 如何串起个人 AI Infra](/assets/images/personal-ai-infra-ray/ray-stack-integration.svg)

一个合理的本地工作流是：

1. Ray task 清洗数据。
2. Ray task 提交 XTuner 微调。
3. 任务内部写 MLflow。
4. 训练产物进入 models/adapters。
5. vLLM/LMDeploy 启动服务。
6. Ray task 批量评测新模型。
7. Ray Actor 跑 Agent 实验。
8. 错误样本回流下一轮。

这就是 Ray 在个人 AI Infra 里的真正价值：它把零散任务串成闭环。

## 十五、总结：Ray 是个人 AI 工作站的轻量调度大脑

个人轻量 AI Infra 不需要一开始就追求企业级平台。

如果你只有一台机器，Ray 已经能帮你解决很多实际问题：

1. 多个 Python 任务怎么并发。
2. GPU 任务怎么排队。
3. 常驻 worker 怎么管理。
4. 批量推理怎么扩展。
5. Agent worker 怎么隔离。
6. 任务失败怎么观察。

它的边界也要清楚：Ray 不是万能平台。它最适合做调度和并发，不适合替代专业训练框架、推理框架和监控系统。

用好 Ray 的关键，不是把所有东西都塞进 Ray，而是让 Ray 站在中间，把 XTuner、MLflow、vLLM/LMDeploy、RAG 和 Agent 这些模块有节奏地调度起来。

这就是个人轻量 AI Infra 的第二块拼图。
