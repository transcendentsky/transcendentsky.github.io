---
title: 个人轻量 AI Infra（三）：详细讲讲 MLflow
tags:
  - AI Infra
  - MLflow
  - MLOps
  - LLM
---

> 一句话总结：在个人轻量 AI Infra 里，MLflow 最适合扮演“实验账本 + 模型资产仓库”的角色。Ray 负责把任务调度起来，XTuner 负责微调，vLLM/LMDeploy 负责推理，而 MLflow 负责把每一次训练、评测、权重、配置、Prompt、Trace 和部署版本留下来。

![MLflow 在个人 AI Infra 中的角色](/assets/images/personal-ai-infra-mlflow/mlflow-role.svg)

<!--more-->

上一篇讲 Ray 时，我把 Ray 定位为个人 AI 工作站的轻量调度大脑：它关心任务怎么排队、资源怎么声明、多个训练/推理/Agent 任务如何并发。

这篇讲 MLflow。

如果说 Ray 解决的是“任务怎么跑”，那么 MLflow 解决的是另一个更容易被低估的问题：**跑完以后，结果怎么留下来。**

个人做大模型实验，很容易陷入一种混乱状态：

1. 今天跑了一个 LoRA，效果不错，但忘了数据版本。
2. 明天调了学习率，loss 更低，但评测集表现反而差。
3. 后天换了 prompt template，感觉回答更稳，但没有样例对比。
4. 过了一周，目录里堆了十几个 `checkpoint-final`、`adapter_model`、`output_v2`。
5. 真要部署时，已经分不清哪个权重对应哪个实验。

MLflow 要解决的不是“训练更快”，而是“结果可追踪、可复现、可比较、可发布”。

这对个人 AI Infra 非常关键。因为个人工作站算力有限，每次实验都很贵。你不能像大厂一样无限堆机器试错，所以每一次实验都应该留下足够多的信息，方便你判断：这次实验是否有效，是否值得继续，是否可以部署。

## 一、MLflow 在个人 AI Infra 里的定位

先把边界说清楚：MLflow 不是调度器，不是训练框架，也不是推理框架。

| 你要做的事 | 更合适的工具 | MLflow 的角色 |
| --- | --- | --- |
| 任务排队和 GPU 调度 | Ray | 记录任务参数、状态、结果 |
| LoRA/QLoRA 微调 | XTuner / LLaMA-Factory / Axolotl | 记录配置、loss、权重、数据版本 |
| 高性能推理 | vLLM / LMDeploy | 记录部署模型、评测结果、延迟指标 |
| RAG 文档处理 | Chroma / FAISS / Qdrant | 记录索引版本、embedding 模型、召回评测 |
| Agent 实验 | LangGraph / 自写 Agent / CrewAI | 记录 trace、工具调用、失败样例 |
| 模型发布 | FastAPI / vLLM server / LMDeploy server | 管理模型版本和回滚依据 |

在个人轻量 AI Infra 里，MLflow 的核心定位是：

1. **实验记录**：每次训练和评测都对应一个 run。
2. **指标对比**：loss、accuracy、pass rate、latency、tokens/s 都能横向比较。
3. **产物管理**：LoRA adapter、配置文件、评测报告、样例输出都能保存。
4. **模型版本**：把“可部署模型”从一堆 checkpoint 里明确挑出来。
5. **复现线索**：数据版本、代码版本、base model、prompt template 都有记录。
6. **GenAI 观测**：LLM 调用链路、工具调用、RAG trace、Agent 失败过程能被追踪。

一句话：**Ray 是调度层，MLflow 是记账层。**

## 二、为什么个人玩家更需要 MLflow？

很多人以为 MLOps 是团队或企业才需要的东西，个人不需要。这其实刚好反过来。

企业有平台、有流程、有同事 review、有线上监控、有专门的人管理模型资产。个人玩家往往只有一个目录、一个 notebook、一个终端和一堆临时命名。

越是个人实验，越容易乱。

| 常见混乱 | 后果 | MLflow 怎么帮你 |
| --- | --- | --- |
| 权重文件夹随便命名 | 好模型找不到 | run 和 artifact 对应起来 |
| 只看训练 loss | 模型实际效果不确定 | 同时记录 eval 指标和样例 |
| 数据经常改 | 不知道提升来自哪里 | 记录数据路径、hash、版本 |
| prompt template 改来改去 | RAG/Agent 效果不可复现 | 保存 prompt 文件和 trace |
| 多个模型都叫 final | 部署时靠感觉 | 用 Model Registry 管版本 |
| 失败实验直接删 | 重复踩坑 | 用 tags/notes 记录失败原因 |

个人 AI Infra 的一个重要原则是：

> 不要相信记忆，要相信记录。

尤其是大模型微调和 Agent 实验，很多改动看起来很小，但影响很大：

1. system prompt 多一句话。
2. 数据清洗规则改一个过滤条件。
3. LoRA rank 从 8 改到 16。
4. max length 从 4096 改到 8192。
5. 评测集多加了几十条困难样例。
6. 推理 temperature 从 0.7 改到 0.2。

这些东西如果不记录，过几天就会变成“玄学调参”。

## 三、MLflow 的几个核心概念

MLflow 的概念不算复杂，但要用好，必须把它们映射到自己的 AI 工作流里。

| 概念 | 解释 | 个人 AI 场景 |
| --- | --- | --- |
| Experiment | 一组相关实验 | 一个项目、一个模型方向、一个任务 |
| Run | 一次具体执行 | 一次微调、一次评测、一次 RAG 索引构建 |
| Params | 固定参数 | base model、learning rate、LoRA rank、数据路径 |
| Metrics | 可比较指标 | loss、eval score、tokens/s、latency、win rate |
| Artifacts | 文件产物 | adapter、config、日志、评测报告、样例输出 |
| Tags | 元信息 | 任务名、代码版本、数据版本、是否可部署 |
| Tracking Server | 追踪服务 | 本地或远程 MLflow UI/API |
| Artifact Store | 产物存储 | 本地目录、NAS、S3/MinIO |
| Model Registry | 模型仓库 | 管理候选模型、生产模型、回滚版本 |
| Trace | 调用链路 | LLM/RAG/Agent 的请求、工具调用、输出 |

最重要的是 Run。

你可以把一次 run 理解成一个实验档案袋。这个档案袋里至少应该放：

1. 我用了哪个 base model。
2. 我用了哪份数据。
3. 我用了哪些训练参数。
4. 我跑出了哪些指标。
5. 我保存了哪些权重和日志。
6. 我用什么评测脚本评测。
7. 我认为这次实验的结论是什么。

![MLflow 实验追踪闭环](/assets/images/personal-ai-infra-mlflow/mlflow-tracking-loop.svg)

## 四、安装与最小启动方式

最小安装：

```bash
pip install -U mlflow
```

如果你只是在本地试用，可以直接启动 UI：

```bash
mlflow ui --host 0.0.0.0 --port 5000
```

浏览器打开：

```text
http://localhost:5000
```

默认情况下，MLflow 会在当前目录生成 `mlruns/`。这适合快速试用，但不适合长期管理。

我更建议为个人 AI Infra 单独建一个工作目录：

```text
~/ai-infra/
  data/
  models/
  experiments/
    mlruns/
  artifacts/
  scripts/
  notebooks/
```

然后启动：

```bash
cd ~/ai-infra
mlflow server \
  --host 0.0.0.0 \
  --port 5000 \
  --backend-store-uri sqlite:///experiments/mlflow.db \
  --default-artifact-root ./artifacts
```

这里有两个关键路径：

| 参数 | 含义 |
| --- | --- |
| `backend-store-uri` | 存 experiment、run、params、metrics 等元数据 |
| `default-artifact-root` | 存模型权重、报告、图片、配置等文件产物 |

个人单机初期用 SQLite + 本地 artifacts 就够了。后面实验变多，可以升级为 PostgreSQL + MinIO/S3。

## 五、第一次记录实验

先看一个最小例子：

```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("llm-sft-demo")

with mlflow.start_run(run_name="qwen-lora-rank8"):
    mlflow.log_param("base_model", "Qwen/Qwen2.5-7B-Instruct")
    mlflow.log_param("lora_rank", 8)
    mlflow.log_param("learning_rate", 2e-4)
    mlflow.log_param("dataset", "data/sft/v1.jsonl")

    mlflow.log_metric("train_loss", 1.82, step=100)
    mlflow.log_metric("eval_score", 0.71)

    mlflow.log_artifact("configs/train_lora.yaml", artifact_path="configs")
    mlflow.log_artifact("reports/eval_report.json", artifact_path="reports")
```

这段代码做了几件事：

1. 指向本地 MLflow server。
2. 创建或选择一个 experiment。
3. 开启一次 run。
4. 记录参数。
5. 记录指标。
6. 保存配置和评测报告。

这就已经比“训练完以后把日志留在终端里”强很多。

但真正用于大模型微调时，我们还需要记录更多信息。

## 六、一次 LLM 微调应该记录什么？

以 LoRA 微调为例，我建议每次 run 至少记录这些字段。

| 类别 | 推荐记录项 | 为什么重要 |
| --- | --- | --- |
| Base Model | 模型名、版本、下载路径 | 同一个任务换 base model 影响巨大 |
| 数据 | 数据路径、样本数、hash、清洗脚本版本 | 方便判断效果提升来自数据还是参数 |
| LoRA 参数 | rank、alpha、dropout、target modules | 决定 adapter 容量和训练稳定性 |
| 训练参数 | learning rate、batch size、epoch、max length | 复现实验的核心 |
| 硬件信息 | GPU 型号、显存、CUDA、torch 版本 | 性能和 OOM 问题需要这些信息 |
| 指标 | train loss、eval loss、任务分数、tokens/s | 用来横向比较 |
| 产物 | adapter、tokenizer、训练配置、日志 | 部署和回滚需要 |
| 评测样例 | 输入、模型输出、参考答案、错误类型 | 大模型效果不能只看一个数字 |
| 结论 | 成功/失败、下一步、人工备注 | 防止重复踩坑 |

一个更实用的记录方式：

```python
import json
import mlflow
from pathlib import Path

def log_lora_run(config: dict, metrics: dict, output_dir: str):
    mlflow.set_tracking_uri("http://localhost:5000")
    mlflow.set_experiment("qwen-domain-lora")

    with mlflow.start_run(run_name=config["run_name"]):
        mlflow.log_params({
            "base_model": config["base_model"],
            "dataset": config["dataset"],
            "dataset_version": config["dataset_version"],
            "lora_rank": config["lora_rank"],
            "lora_alpha": config["lora_alpha"],
            "learning_rate": config["learning_rate"],
            "max_length": config["max_length"],
            "epochs": config["epochs"],
        })

        for name, value in metrics.items():
            mlflow.log_metric(name, value)

        output = Path(output_dir)
        mlflow.log_artifact(output / "train_config.yaml", artifact_path="configs")
        mlflow.log_artifact(output / "eval_report.json", artifact_path="reports")
        mlflow.log_artifacts(output / "adapter", artifact_path="adapter")

        mlflow.set_tags({
            "task": "domain_sft",
            "stage": "candidate",
            "owner": "personal-workstation",
        })
```

这里有一个关键习惯：**不要只保存最终权重，也要保存训练配置和评测报告。**

因为权重本身并不能告诉你它从哪里来。

## 七、怎么和 XTuner 配合？

XTuner 是训练工具，MLflow 是记录工具。两者配合时不要强行把 XTuner 改得很复杂。

最简单的方式是：用一个外层 Python 脚本包住训练命令。

```python
import subprocess
import mlflow

config_path = "configs/qwen_lora.py"
work_dir = "work_dirs/qwen_lora_run_001"

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("xtuner-lora")

with mlflow.start_run(run_name="qwen-lora-run-001"):
    mlflow.log_param("trainer", "xtuner")
    mlflow.log_param("config", config_path)
    mlflow.log_param("work_dir", work_dir)

    subprocess.run(
        ["xtuner", "train", config_path, "--work-dir", work_dir],
        check=True,
    )

    mlflow.log_artifact(config_path, artifact_path="configs")
    mlflow.log_artifacts(work_dir, artifact_path="xtuner_work_dir")
```

这不是最优雅的方式，但很稳。

如果你愿意进一步做工程化，可以让训练脚本在每个 epoch 后调用 `mlflow.log_metric`，这样 UI 里能看到完整曲线：

```python
mlflow.log_metric("train_loss", loss, step=global_step)
mlflow.log_metric("learning_rate", lr, step=global_step)
mlflow.log_metric("tokens_per_second", tps, step=global_step)
```

对个人项目来说，先做到这三件事就够了：

1. 每次 XTuner 训练都自动创建一个 MLflow run。
2. 每次 run 都保存 config、日志、adapter 和 eval report。
3. 每次 run 都记录可比较指标。

## 八、怎么和 Ray 配合？

Ray 和 MLflow 的关系非常自然：

1. Ray 负责提交和调度任务。
2. 任务内部用 MLflow 记录实验。

例如，用 Ray 并发跑多个超参组合：

```python
import ray
import mlflow

ray.init(address="auto")

@ray.remote(num_gpus=1)
def train_one(config):
    mlflow.set_tracking_uri("http://localhost:5000")
    mlflow.set_experiment("ray-hparam-search")

    with mlflow.start_run(run_name=config["name"]):
        mlflow.log_params(config)

        # 这里调用真实训练逻辑
        result = run_training(config)

        mlflow.log_metric("eval_score", result["eval_score"])
        mlflow.log_metric("train_loss", result["train_loss"])
        mlflow.log_artifacts(result["output_dir"], artifact_path="outputs")

        return result

configs = [
    {"name": "rank8-lr2e-4", "lora_rank": 8, "learning_rate": 2e-4},
    {"name": "rank16-lr1e-4", "lora_rank": 16, "learning_rate": 1e-4},
]

refs = [train_one.remote(cfg) for cfg in configs]
results = ray.get(refs)
```

这里要注意一个细节：每个 Ray task 都是独立进程，所以需要在 task 内部设置 tracking URI 和 experiment。

不要只在 driver 里设置一次就以为所有 worker 都知道。

![MLflow 与个人 AI Infra 组件集成](/assets/images/personal-ai-infra-mlflow/mlflow-stack.svg)

## 九、Model Registry：别让“最终版”变成玄学

个人项目里最常见的模型命名事故是：

```text
final/
final_v2/
final_real/
final_best/
final_best_new/
final_best_new2/
```

这不是玩笑。只要实验多一点，几乎必然会发生。

MLflow Model Registry 的价值是把“某个 run 的产物”提升为“一个明确的模型版本”。

你可以设计这样的阶段：

| 阶段 | 含义 |
| --- | --- |
| `candidate` | 候选模型，刚训练完 |
| `validated` | 通过离线评测 |
| `staging` | 准备部署到本地 API 测试 |
| `production` | 当前默认使用模型 |
| `archived` | 不再使用，但保留记录 |

一个简化流程：

1. 训练完成，保存 adapter 到 MLflow artifacts。
2. 评测通过后，把 run 标记为 `candidate`。
3. 人工查看样例和指标。
4. 决定注册为模型版本。
5. 部署时从 registry 读取当前 production 版本。
6. 如果线上效果不好，回滚到上一个版本。

个人工作站不一定要一开始就用很复杂的 registry 流程，但至少应该做到：

1. 哪个 run 是当前推荐版本。
2. 哪个 adapter 被部署过。
3. 部署前通过了哪些评测。
4. 为什么替换上一版。

这些信息用 tags 也可以先做起来：

```python
mlflow.set_tags({
    "model_stage": "candidate",
    "deploy_target": "local-vllm",
    "eval_passed": "true",
    "notes": "domain QA score improved, but math cases still weak",
})
```

## 十、LLM 评测：不要只看 loss

传统机器学习里，loss 和 accuracy 往往能说明很多问题。但大模型不一样。

一个 SFT 模型的 loss 下降，不代表回答更好；一个 RAG 系统的召回率提高，不代表最终答案更可信；一个 Agent 能完成 demo，不代表它在异常路径上稳定。

所以 MLflow 里应该记录两类评测：

1. **数值指标**：方便横向比较。
2. **样例报告**：方便人工判断。

推荐指标：

| 场景 | 指标 |
| --- | --- |
| SFT 微调 | eval loss、任务准确率、格式遵循率、拒答率 |
| 偏好优化 | win rate、chosen/rejected margin |
| RAG | recall@k、answer faithfulness、citation accuracy |
| 推理服务 | tokens/s、TTFT、TPOT、P95 latency |
| Agent | task success rate、tool error rate、平均步数、失败类型 |

推荐产物：

| 产物 | 内容 |
| --- | --- |
| `eval_report.json` | 总体指标、分任务指标 |
| `bad_cases.jsonl` | 失败样例 |
| `sample_outputs.md` | 人类可读的模型输出 |
| `latency_report.csv` | 延迟统计 |
| `confusion_tags.csv` | 错误类型分布 |

一个简单记录方式：

```python
mlflow.log_metric("format_follow_rate", 0.93)
mlflow.log_metric("answer_pass_rate", 0.78)
mlflow.log_metric("p95_latency_ms", 842)

mlflow.log_artifact("reports/sample_outputs.md", artifact_path="eval")
mlflow.log_artifact("reports/bad_cases.jsonl", artifact_path="eval")
```

大模型评测最好不要只留下一个分数。你需要看到模型到底怎么错。

## 十一、GenAI Tracing：RAG 和 Agent 更需要链路记录

MLflow 现在已经不只是传统训练实验工具，它也在覆盖 GenAI 场景，比如 tracing、evaluation、prompt 和应用观测。

这对个人 AI Infra 很重要，因为 RAG 和 Agent 的问题通常不是一个简单的 loss 能解释的。

例如一个 RAG 答错了，可能有很多原因：

1. 用户问题改写错了。
2. embedding 模型不合适。
3. 检索 top-k 太小。
4. reranker 排错了。
5. prompt 没约束引用来源。
6. LLM 幻觉补全。
7. 工具调用返回了旧数据。

如果没有 trace，你只会看到“最终答案错了”。但你不知道错在哪里。

一个 trace 至少应该帮你看到：

| 阶段 | 需要记录 |
| --- | --- |
| 输入 | 原始 query、用户上下文 |
| 改写 | rewritten query、意图分类 |
| 检索 | top-k 文档、score、chunk id |
| 重排 | rerank score、最终上下文 |
| 生成 | prompt、模型名、temperature、输出 |
| 工具 | tool name、参数、返回、耗时 |
| 结果 | 最终答案、引用、人工评分 |

即使不用完整 tracing API，你也可以先用 artifacts 保存链路：

```python
import json
import mlflow

trace = {
    "query": query,
    "rewritten_query": rewritten_query,
    "retrieved_docs": retrieved_docs,
    "prompt": prompt,
    "answer": answer,
    "latency_ms": latency_ms,
}

with open("trace.json", "w", encoding="utf-8") as f:
    json.dump(trace, f, ensure_ascii=False, indent=2)

mlflow.log_artifact("trace.json", artifact_path="traces")
```

这已经能解决很多定位问题。

## 十二、Prompt 也应该版本化

很多个人项目会严格保存模型权重，却随手改 prompt。

这是一个大坑。

对于 RAG、Agent、医疗问答、代码生成等应用，prompt template 往往就是系统行为的一部分。你改了 prompt，本质上就是改了模型应用。

建议每次 run 记录：

1. system prompt。
2. user prompt template。
3. few-shot examples。
4. output schema。
5. tool description。
6. decoding 参数。

可以这样保存：

```python
mlflow.log_param("prompt_version", "qa_prompt_v3")
mlflow.log_param("temperature", 0.2)
mlflow.log_param("top_p", 0.9)
mlflow.log_artifact("prompts/qa_prompt_v3.md", artifact_path="prompts")
```

如果一个模型线上效果变差，别只怀疑权重。很多时候是 prompt、检索配置或工具描述变了。

## 十三、数据版本怎么记录？

MLflow 本身可以记录参数和 artifacts，但数据版本管理要结合你的实际习惯。

个人项目里可以先用三种简单方法：

| 方法 | 做法 | 适合 |
| --- | --- | --- |
| 路径版本 | `data/sft/v1/train.jsonl` | 小项目 |
| 文件 hash | 记录 sha256/md5 | 防止文件被偷偷覆盖 |
| DVC/Git LFS | 数据独立版本化 | 数据较多或多人协作 |

最轻量的 hash 记录：

```python
import hashlib
import mlflow

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

dataset_path = "data/sft/v1/train.jsonl"
mlflow.log_param("dataset_path", dataset_path)
mlflow.log_param("dataset_sha256", file_sha256(dataset_path))
```

这样即使文件名没变，你也知道内容有没有变。

## 十四、推荐目录结构

个人轻量 AI Infra 可以这样组织：

```text
ai-infra/
  data/
    raw/
    processed/
    sft/
    eval/
    rag_docs/
  models/
    base/
    adapters/
    merged/
  experiments/
    mlflow.db
    mlruns/
  artifacts/
  configs/
    train/
    serving/
    eval/
  prompts/
  reports/
  scripts/
    train/
    eval/
    serve/
    rag/
  notebooks/
```

对应关系：

| 目录 | 作用 |
| --- | --- |
| `data/` | 原始数据、处理后数据、评测集 |
| `models/base/` | 本地 base model |
| `models/adapters/` | LoRA adapter 的本地缓存 |
| `models/merged/` | 合并后的模型 |
| `experiments/` | MLflow 元数据 |
| `artifacts/` | MLflow 产物 |
| `configs/` | 训练、推理、评测配置 |
| `prompts/` | prompt template |
| `reports/` | 评测报告和可读总结 |
| `scripts/` | 可复现脚本 |

一个原则：**模型产物可以很大，但元数据必须清楚。**

## 十五、个人工作站的 MLflow 启动脚本

可以写一个 `start_mlflow.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="${HOME}/ai-infra"
mkdir -p "${ROOT}/experiments" "${ROOT}/artifacts"

cd "${ROOT}"

mlflow server \
  --host 0.0.0.0 \
  --port 5000 \
  --backend-store-uri sqlite:///${ROOT}/experiments/mlflow.db \
  --default-artifact-root "${ROOT}/artifacts"
```

然后：

```bash
chmod +x start_mlflow.sh
./start_mlflow.sh
```

如果你希望它常驻，可以用 `tmux`：

```bash
tmux new -s mlflow
./start_mlflow.sh
```

或者用 `systemd`、`launchd`、`supervisor` 管起来。个人机器上不必一开始就复杂，先让它稳定跑起来。

## 十六、与 vLLM/LMDeploy 的配合方式

MLflow 不负责高性能推理，但它可以记录每次部署和评测。

例如你用 vLLM 启动一个 OpenAI 兼容 API：

```bash
python -m vllm.entrypoints.openai.api_server \
  --model /models/merged/qwen-domain-v3 \
  --served-model-name qwen-domain-v3 \
  --port 8000
```

此时 MLflow 应该记录：

| 项目 | 示例 |
| --- | --- |
| `served_model_name` | `qwen-domain-v3` |
| `base_model` | `Qwen2.5-7B-Instruct` |
| `adapter_run_id` | 对应训练 run |
| `engine` | `vllm` |
| `max_model_len` | `8192` |
| `dtype` | `bfloat16` |
| `quantization` | `none/int8/fp8` |
| `eval_score` | 部署前评测 |
| `p95_latency_ms` | 压测指标 |

一个部署记录 run：

```python
import mlflow

mlflow.set_experiment("local-serving")

with mlflow.start_run(run_name="deploy-qwen-domain-v3"):
    mlflow.log_params({
        "engine": "vllm",
        "served_model_name": "qwen-domain-v3",
        "model_path": "/models/merged/qwen-domain-v3",
        "port": 8000,
        "max_model_len": 8192,
        "dtype": "bfloat16",
    })
    mlflow.log_metric("p95_latency_ms", 760)
    mlflow.log_metric("tokens_per_second", 142)
    mlflow.set_tag("deploy_stage", "local-production")
```

这样你以后就知道：某一天本地 API 到底部署了哪个模型、用什么参数启动、性能怎样。

## 十七、与 RAG 的配合方式

RAG 里最容易变乱的不是模型，而是索引。

你应该记录：

| 类别 | 记录项 |
| --- | --- |
| 文档 | 文档来源、更新时间、数量 |
| 切分 | chunk size、overlap、splitter |
| Embedding | embedding 模型、维度、归一化方式 |
| 向量库 | Chroma/FAISS/Qdrant、索引路径 |
| 检索 | top-k、score threshold、reranker |
| 评测 | recall@k、命中率、答案忠实度 |

示例：

```python
mlflow.set_experiment("rag-index")

with mlflow.start_run(run_name="power-docs-index-v4"):
    mlflow.log_params({
        "doc_source": "docs/power_transformer",
        "doc_count": 1284,
        "chunk_size": 800,
        "chunk_overlap": 120,
        "embedding_model": "bge-m3",
        "vector_store": "faiss",
        "top_k": 8,
    })
    mlflow.log_metric("recall_at_5", 0.84)
    mlflow.log_metric("answer_faithfulness", 0.79)
    mlflow.log_artifact("reports/rag_eval.md", artifact_path="reports")
    mlflow.log_artifact("indexes/faiss_manifest.json", artifact_path="index")
```

RAG 的索引版本必须可追踪，否则你会遇到一种很难定位的问题：模型没变，prompt 没变，但回答突然变差。最后发现是索引构建时文档切分变了。

## 十八、与 Agent 实验的配合方式

Agent 实验更应该用 MLflow，因为 Agent 的失败往往不是一个点，而是一条链。

建议记录：

| 类别 | 记录项 |
| --- | --- |
| Agent 配置 | planner、executor、memory、工具列表 |
| LLM 配置 | 模型名、temperature、max tokens |
| 工具调用 | tool name、参数、返回、耗时 |
| 任务结果 | success/fail、步数、失败原因 |
| Trace | 每一步 action、observation、thought |
| 成本 | token 数、调用次数、总耗时 |

一个简单的 Agent run：

```python
mlflow.set_experiment("agent-eval")

with mlflow.start_run(run_name="tool-agent-v2"):
    mlflow.log_params({
        "planner_model": "qwen-domain-v3",
        "max_steps": 8,
        "tools": "search,calculator,db_query",
        "memory": "summary_memory",
    })

    result = run_agent_eval()

    mlflow.log_metric("success_rate", result["success_rate"])
    mlflow.log_metric("avg_steps", result["avg_steps"])
    mlflow.log_metric("tool_error_rate", result["tool_error_rate"])
    mlflow.log_artifact("reports/agent_traces.jsonl", artifact_path="traces")
    mlflow.log_artifact("reports/agent_bad_cases.md", artifact_path="reports")
```

对 Agent 来说，`bad_cases.md` 往往比总分更有价值。因为你需要知道失败是因为工具不可用、规划错误、检索错误，还是模型输出格式不稳定。

## 十九、一个推荐的个人 MLflow 工作流

我建议把个人 AI Infra 的 MLflow 工作流设计成这样：

1. 每个项目一个 experiment。
2. 每次训练、评测、部署、索引构建都是一个 run。
3. 每个 run 记录 params、metrics、artifacts、tags。
4. 训练 run 保存 adapter 和 config。
5. 评测 run 保存报告和 bad cases。
6. 部署 run 保存 engine 参数和压测指标。
7. RAG run 保存索引 manifest 和检索评测。
8. Agent run 保存 trace 和失败分类。
9. 通过 tags 标记候选模型和生产模型。
10. 定期清理大 artifact，但不要删元数据。

一条完整链路可能是：

```text
数据清洗 run
  -> LoRA 训练 run
  -> 离线评测 run
  -> 模型注册 / 标记 candidate
  -> vLLM 部署 run
  -> RAG / Agent 集成评测 run
  -> 标记 production
```

这样一来，你的网站 demo、本地 API、Agent 项目里使用的模型，不再是一个模糊的文件夹，而是一个有来源、有指标、有评测、有版本的资产。

## 二十、几个容易踩的坑

| 坑 | 表现 | 建议 |
| --- | --- | --- |
| 只记录 loss | 训练曲线好看，但模型不好用 | 同时记录任务指标和样例输出 |
| artifact 太大 | MLflow 目录膨胀很快 | adapter 保存，base model 不重复保存 |
| run 命名随意 | UI 里难以搜索 | run name 包含模型、数据、关键参数 |
| 不记录数据版本 | 结果无法复现 | 记录路径、样本数、hash |
| 不记录 prompt | RAG/Agent 行为变化无法解释 | prompt 文件作为 artifact |
| 把 MLflow 当数据库乱塞 | 查询和维护困难 | 大对象放 artifact，关键字段放 params/tags |
| 本地路径写死 | 换机器就断 | 使用统一根目录和相对路径 |
| 只保留成功实验 | 失败经验丢失 | 失败 run 也保留，并写 failure_reason |

我个人最建议养成的习惯是：失败实验也记录。

失败实验不是垃圾。它们是你避免重复浪费 GPU 时间的证据。

## 二十一、个人轻量 AI Infra 中 MLflow 的边界

MLflow 很有用，但也不要把它神化。

它不适合做这些事：

1. 不替代 Ray 做调度。
2. 不替代 XTuner 做训练。
3. 不替代 vLLM/LMDeploy 做推理。
4. 不替代 Prometheus/Grafana 做系统级监控。
5. 不替代 DVC/Git LFS 做大规模数据版本管理。
6. 不替代 Weights & Biases 的某些团队协作体验。

MLflow 最适合做的是：

1. 记录实验。
2. 比较实验。
3. 保存产物。
4. 管理模型版本。
5. 帮你复现结果。
6. 帮你解释“为什么这个模型被部署”。

个人项目不要追求一开始就平台化。先让每次实验都有记录，已经是巨大提升。

## 二十二、总结：MLflow 是个人 AI 工作站的实验账本

个人轻量 AI Infra 的核心不是堆很多工具，而是让每个工具站在正确的位置上：

| 层次 | 工具 | 作用 |
| --- | --- | --- |
| 调度层 | Ray | 管任务、资源、并发 |
| 实验层 | MLflow | 管记录、产物、模型版本 |
| 训练层 | XTuner | 管 LoRA/QLoRA 微调 |
| 推理层 | vLLM/LMDeploy | 管高性能服务 |
| 检索层 | Chroma/FAISS | 管向量索引 |
| 监控层 | Prometheus/Grafana | 管系统指标 |

MLflow 在这里是“账本”。它不负责让模型更聪明，也不负责让推理更快，但它负责回答几个非常重要的问题：

1. 这个模型从哪里来？
2. 它用什么数据训练？
3. 它比上一版好在哪里？
4. 它通过了哪些评测？
5. 它部署时用了什么参数？
6. 出问题后能不能回滚？

如果你已经用 Ray 把任务跑起来，那么下一步就应该用 MLflow 把结果留下来。

这就是个人轻量 AI Infra 的第三块拼图。

参考：

1. [MLflow Tracking 官方文档](https://mlflow.org/docs/latest/ml/tracking/)
2. [MLflow Model Registry 官方文档](https://mlflow.org/docs/latest/ml/model-registry/)
3. [MLflow GenAI 官方文档](https://mlflow.org/docs/latest/genai/)
