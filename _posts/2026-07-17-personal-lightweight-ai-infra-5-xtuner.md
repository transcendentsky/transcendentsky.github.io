---
title: 个人轻量 AI Infra（五）：详细讲讲 XTuner
tags:
  - AI Infra
  - XTuner
  - LoRA
  - Fine-tuning
---

> 一句话总结：在个人轻量 AI Infra 里，XTuner 最适合扮演“微调层”的角色。Ray 负责调度训练任务，MLflow 负责记录实验和模型版本，vLLM/LMDeploy 负责推理服务，而 XTuner 负责把数据、基础模型和配置真正转化成 LoRA/QLoRA 产物。

![XTuner 在个人 AI Infra 中的位置](/assets/images/personal-ai-infra-xtuner/xtuner-role.svg)

<!--more-->

前面几篇讲了个人轻量 AI Infra 的几个核心组件：

1. Ray：调度层，负责任务队列、资源声明和并发。
2. MLflow：实验层，负责记录、对比、版本和复现。
3. vLLM/LMDeploy：推理层，负责把模型变成稳定 API。

这篇讲第五块：**XTuner**。

如果说 vLLM/LMDeploy 解决的是“模型怎么用起来”，那么 XTuner 解决的是“模型怎么被你自己的数据改造”。

很多个人玩家搭 AI Infra 的真正目标不是单纯跑一个开源模型，而是让模型更适合自己的任务：

1. 回答某个专业领域问题。
2. 遵循固定输出格式。
3. 学会某类工具调用。
4. 适配企业内部文档问答。
5. 提升某类意图识别、分类或生成质量。
6. 让 Agent 在固定流程里更稳定。

这些需求往往不能只靠 prompt 解决。Prompt 可以改变短期行为，但当你希望模型形成稳定偏好、固定格式、领域表达和任务习惯时，就需要微调。

XTuner 就是个人 AI Infra 里非常合适的微调工具。

## 一、XTuner 在个人 AI Infra 里的定位

XTuner 是 OpenMMLab/InternLM 生态里的 LLM 微调工具箱。官方文档把它定位成 All-IN-ONE toolbox for LLM，围绕大模型训练、微调、转换、聊天、评测、多模态和加速提供了一套工具链。

在个人轻量 AI Infra 里，它的位置很清楚：

| 你要做的事 | 更合适的工具 | XTuner 的角色 |
| --- | --- | --- |
| 任务调度 | Ray | 被 Ray 调用和排队 |
| 实验记录 | MLflow | 把训练参数、指标、产物写进去 |
| LoRA/QLoRA 微调 | XTuner | 核心训练执行者 |
| 数据版本 | Git/DVC/文件 hash | XTuner 消费数据 |
| 推理服务 | vLLM/LMDeploy | 使用 XTuner 产出的模型 |
| 评测 | OpenCompass/自定义 eval | 评估 XTuner 产物 |

一句话：**XTuner 不负责整个 AI Infra，它负责微调这条链路的训练部分。**

## 二、什么时候应该用 XTuner 微调？

不是所有问题都应该微调。

先看一个简单判断表：

| 需求 | 是否优先微调 | 更推荐的第一步 |
| --- | --- | --- |
| 模型不知道某些新知识 | 不一定 | RAG |
| 模型输出格式不稳定 | 可以考虑 | 先优化 prompt 和样例 |
| 模型领域表达不专业 | 可以考虑 | SFT |
| 模型要学固定分类体系 | 很适合 | SFT/LoRA |
| 模型要学工具调用格式 | 适合 | Agent 数据微调 |
| 模型推理能力不足 | 不一定 | 换更强 base model 或偏好优化 |
| 模型长文本事实不准 | 不一定 | RAG + 评测 |
| 模型在固定任务上差一点 | 很适合 | 小规模高质量 LoRA |

个人经验是：

1. **知识问题先 RAG**。
2. **格式问题先 prompt**。
3. **习惯问题和领域风格问题再微调**。
4. **稳定任务边界内的小模型增强，非常适合 LoRA/QLoRA**。

例如，你做一个电力设备智能体，模型需要稳定识别“故障诊断、状态评估、检修建议、资料检索、指标解释”等意图。这个时候 SFT 微调就很有价值。

但如果只是让模型知道某份新标准的内容，RAG 往往更合适。

## 三、LoRA、QLoRA 和全参微调怎么选？

个人工作站上，通常不建议一开始做全参微调。

| 方法 | 特点 | 适合场景 |
| --- | --- | --- |
| LoRA | 只训练低秩 adapter，显存较省 | 个人最常用 |
| QLoRA | base model 量化加载，再训练 LoRA | 显存更紧时 |
| 全参微调 | 更新全部参数，成本高 | 数据多、算力强、目标明确 |
| 指令微调 SFT | 用问答/对话数据学行为 | 领域问答、格式遵循 |
| 预训练继续训练 | 用大规模文本继续建模 | 领域语料很多时 |

个人建议：

1. 7B/14B 模型：优先 LoRA 或 QLoRA。
2. 32B 模型：优先 QLoRA 或更小 batch。
3. 数据少于几千条：别急着拉大 rank，先提升数据质量。
4. 任务非常格式化：小 LoRA 往往就够。
5. 任务涉及复杂推理：微调未必能补，可能要换 base model。

LoRA 的核心参数：

| 参数 | 含义 | 经验 |
| --- | --- | --- |
| rank/r | adapter 容量 | 8/16/32 常见 |
| alpha | 缩放系数 | 通常和 rank 配合 |
| dropout | 防过拟合 | 小数据可适当加 |
| target modules | 训练哪些线性层 | 常见 q_proj/k_proj/v_proj/o_proj 等 |
| learning rate | 学习率 | 太大容易格式崩 |
| max length | 序列长度 | 影响显存和训练速度 |

## 四、XTuner 的典型工作流

XTuner 的使用方式很适合个人项目，因为它强调配置驱动。

典型流程：

1. 查看已有配置。
2. 复制一个相近配置。
3. 修改模型路径、数据路径、训练参数。
4. 启动训练。
5. 把 `.pth` 转成 Hugging Face 格式。
6. 合并 LoRA。
7. 聊天或部署验证。

![XTuner 微调工作流](/assets/images/personal-ai-infra-xtuner/xtuner-workflow.svg)

常用命令大概是：

```bash
xtuner list-cfg
xtuner copy-cfg internlm2_7b_qlora_colorist_e5 .
xtuner train internlm2_7b_qlora_colorist_e5_copy.py
```

训练完成后，XTuner 官方 quickstart 里也展示了类似的转换和合并流程：

```bash
xtuner convert pth_to_hf CONFIG.py \
  work_dirs/your_run/iter_xxx.pth \
  work_dirs/your_run/iter_xxx_hf
```

再合并：

```bash
xtuner convert merge BASE_MODEL_PATH \
  work_dirs/your_run/iter_xxx_hf \
  work_dirs/your_run/merged \
  --max-shard-size 2GB
```

这条链路很重要，因为 XTuner 训练过程中得到的 `.pth` 通常不是完整模型，而是训练更新的部分参数。你需要先转 HF，再根据部署方式选择是否 merge。

## 五、安装和环境准备

常见安装：

```bash
pip install -U xtuner
```

如果需要完整能力，可以参考官方文档安装更多依赖。个人机器上先检查这些：

```bash
nvidia-smi
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
xtuner --help
```

建议环境：

| 项目 | 建议 |
| --- | --- |
| Python | 使用独立 conda/venv |
| CUDA | 和 PyTorch 匹配 |
| 模型缓存 | 统一放到 `models/base/` |
| 数据目录 | 统一放到 `data/sft/` |
| 输出目录 | 统一放到 `work_dirs/` |
| 实验记录 | 接 MLflow |

个人工作站最怕环境混乱。XTuner、vLLM、LMDeploy、PyTorch、CUDA 版本之间可能有依赖差异，所以最好给训练和推理分别建环境：

```text
envs/
  train-xtuner/
  serve-vllm/
  serve-lmdeploy/
```

不一定物理上这么建，但思路上要分清：训练环境和推理环境可以不同。

## 六、数据格式：微调质量的真正核心

微调不是“把数据丢进去就行”。数据质量决定上限。

一个 SFT 样本通常包含：

1. system：角色和约束。
2. user：用户问题或任务输入。
3. assistant：期望输出。

可以是这样的 JSONL：

```json
{"messages":[{"role":"system","content":"你是电力设备诊断助手。"},{"role":"user","content":"油色谱中乙炔升高通常意味着什么？"},{"role":"assistant","content":"乙炔升高通常提示可能存在高能放电故障，需要结合氢气、甲烷、乙烯等组分以及三比值法综合判断。"}]}
```

数据要注意：

| 问题 | 后果 |
| --- | --- |
| assistant 答案太随意 | 模型学到不稳定风格 |
| 输出格式不统一 | 部署后 JSON/表格容易崩 |
| system prompt 混乱 | 角色边界不稳定 |
| 训练集和评测集混在一起 | 指标虚高 |
| 低质量数据太多 | 小模型被带偏 |
| 只放简单样例 | 困难问题仍然不会 |

高质量微调数据应该具备：

1. 任务边界清晰。
2. 输入分布贴近真实使用。
3. 输出风格一致。
4. 复杂样例和边界样例足够。
5. 有拒答、澄清、异常输入样例。
6. 有明确评测集。

个人项目里，先做 300-1000 条高质量数据，往往比堆 5 万条脏数据更有效。

## 七、配置文件应该重点看什么？

XTuner 是配置驱动，所以读懂配置很重要。

一个训练配置里，最应该关注这些部分：

| 配置项 | 你要检查什么 |
| --- | --- |
| model | base model 路径、trust_remote_code、dtype |
| tokenizer | tokenizer 路径、特殊 token |
| dataset | 数据路径、map_fn、template、max_length |
| dataloader | batch size、num workers、shuffle |
| optimizer | learning rate、weight decay |
| scheduler | warmup、总步数、衰减策略 |
| lora | rank、alpha、dropout、target modules |
| hooks | checkpoint、日志、评测、HF 保存 |
| deepspeed | ZeRO stage、offload、bf16/fp16 |
| work_dir | 输出目录 |

个人最常改的是：

1. 模型路径。
2. 数据路径。
3. prompt template。
4. max_length。
5. batch size / accumulation。
6. learning rate。
7. LoRA rank。
8. checkpoint 保存间隔。

不要一次改太多。建议每轮只改 1-2 个关键变量，否则你无法判断效果变化来自哪里。

## 八、单卡训练怎么设？

单卡个人机器上，核心是显存。

建议从保守配置开始：

| 显存 | 推荐尝试 |
| --- | --- |
| 16GB | 7B QLoRA，小 batch，短 max_length |
| 24GB | 7B LoRA/QLoRA，14B QLoRA 视情况 |
| 32GB | 7B/14B LoRA，32B QLoRA 需要谨慎 |
| 48GB | 14B 更舒服，32B QLoRA 可尝试 |

常见降显存手段：

1. 降低 `max_length`。
2. 降低 per-device batch size。
3. 使用 gradient accumulation。
4. 使用 QLoRA。
5. 开 Flash Attention。
6. 开 gradient checkpointing。
7. 使用 DeepSpeed ZeRO。

但是降显存也有代价：

| 方法 | 代价 |
| --- | --- |
| 降 max_length | 长样本信息被截断 |
| 降 batch size | 训练不稳定，速度慢 |
| accumulation | 增加训练时间 |
| QLoRA | 训练和部署链路更复杂 |
| checkpointing | 省显存但更慢 |

个人建议先把训练跑稳，再追求速度。

## 九、怎么和 MLflow 配合？

XTuner 本身负责训练，但实验记录应该交给 MLflow。

最简单方式是用外层脚本包住 `xtuner train`：

```python
import subprocess
import mlflow

config_path = "configs/qwen_lora.py"
work_dir = "work_dirs/qwen_lora_001"

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("xtuner-sft")

with mlflow.start_run(run_name="qwen-lora-001"):
    mlflow.log_param("trainer", "xtuner")
    mlflow.log_param("config", config_path)
    mlflow.log_param("work_dir", work_dir)
    mlflow.log_param("base_model", "Qwen/Qwen2.5-7B-Instruct")
    mlflow.log_param("dataset_version", "sft_v1")

    subprocess.run(
        ["xtuner", "train", config_path, "--work-dir", work_dir],
        check=True,
    )

    mlflow.log_artifact(config_path, artifact_path="configs")
    mlflow.log_artifacts(work_dir, artifact_path="work_dir")
```

训练完成后，把转换和合并产物也记录：

```python
mlflow.log_artifacts("work_dirs/qwen_lora_001/iter_1000_hf", artifact_path="adapter_hf")
mlflow.log_artifacts("work_dirs/qwen_lora_001/merged", artifact_path="merged_model_manifest")
mlflow.set_tag("model_stage", "candidate")
```

注意：完整 merged model 很大，不一定适合全部塞进 MLflow artifact。个人可以记录 manifest、配置、路径、hash，而不是复制所有权重。

## 十、怎么和 Ray 配合？

Ray 负责调度，XTuner 负责训练。最稳的方式仍然是 Ray task 调用 XTuner CLI。

```python
import ray
import subprocess

ray.init(address="auto")

@ray.remote(num_gpus=1, num_cpus=4)
def run_xtuner(config_path, work_dir):
    subprocess.run(
        ["xtuner", "train", config_path, "--work-dir", work_dir],
        check=True,
    )
    return {"config": config_path, "work_dir": work_dir}

ref = run_xtuner.remote("configs/qwen_lora.py", "work_dirs/qwen_lora_001")
result = ray.get(ref)
```

如果你要跑多个配置，Ray 可以排队：

```python
jobs = [
    ("configs/qwen_lora_rank8.py", "work_dirs/rank8"),
    ("configs/qwen_lora_rank16.py", "work_dirs/rank16"),
]

refs = [run_xtuner.remote(cfg, wd) for cfg, wd in jobs]
results = ray.get(refs)
```

但注意：如果你只有一张 GPU，不要真的让多个训练同时跑。Ray 的 `num_gpus=1` 会让它们排队，这正是你需要的。

## 十一、训练后怎么部署？

XTuner 训练后通常有三类产物：

| 产物 | 含义 | 是否可直接部署 |
| --- | --- | --- |
| `.pth` | XTuner checkpoint | 通常不能直接给 vLLM/LMDeploy |
| HF adapter | 转换后的 LoRA adapter | 视推理框架支持 |
| merged model | 合并后的完整模型 | 最容易部署 |

个人项目初期建议优先 merged model。

流程：

```bash
xtuner convert pth_to_hf CONFIG.py \
  work_dirs/run/iter_1000.pth \
  work_dirs/run/iter_1000_hf

xtuner convert merge BASE_MODEL_PATH \
  work_dirs/run/iter_1000_hf \
  work_dirs/run/merged \
  --max-shard-size 2GB
```

然后用 vLLM：

```bash
vllm serve work_dirs/run/merged \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --api-key local-token
```

或者 LMDeploy：

```bash
lmdeploy serve api_server work_dirs/run/merged \
  --server-name 0.0.0.0 \
  --server-port 23333
```

部署前一定做 smoke test：

1. 模型能不能启动。
2. tokenizer 是否正常。
3. chat template 是否正确。
4. 训练任务的典型问题是否改善。
5. 通用能力是否明显退化。

## 十二、评测比训练更重要

微调最容易产生幻觉：训练 loss 下降，看起来很美，但真实效果不一定变好。

每次 XTuner 微调后至少做三类评测：

| 评测 | 目的 |
| --- | --- |
| 训练任务评测 | 是否学会目标任务 |
| 通用能力回归 | 是否严重退化 |
| bad case 人工检查 | 是否有危险输出或格式崩坏 |

指标可以包括：

1. 格式遵循率。
2. 分类准确率。
3. 领域问答通过率。
4. 拒答正确率。
5. JSON 解析成功率。
6. RAG 引用准确率。
7. Agent 工具调用成功率。

对于个人项目，强烈建议保存 `bad_cases.jsonl`：

```json
{"id":"case_001","question":"...","prediction":"...","expected":"...","error_type":"format_error"}
```

这些 bad cases 是下一轮数据构造的核心。

## 十三、数据迭代闭环

XTuner 真正的价值不在于跑一次训练，而在于形成迭代闭环：

1. 收集真实问题。
2. 标注高质量答案。
3. 构造训练集和评测集。
4. 用 XTuner 微调。
5. 用 MLflow 记录。
6. 用 vLLM/LMDeploy 部署。
7. RAG/Agent 实际调用。
8. 收集 bad cases。
9. 回到下一轮数据。

![XTuner 与个人 AI Infra 闭环](/assets/images/personal-ai-infra-xtuner/xtuner-loop.svg)

如果没有这个闭环，微调很容易变成一次性实验。

## 十四、常见坑

| 坑 | 表现 | 建议 |
| --- | --- | --- |
| 数据质量差 | loss 降了但回答变差 | 先清洗数据 |
| 训练集太小但 rank 很大 | 过拟合 | 降 rank，加评测 |
| max_length 过短 | 长样本被截断 | 统计 token 长度 |
| 学习率过大 | 输出格式漂移 | 从保守 LR 开始 |
| prompt template 不一致 | 训练和推理行为不同 | 训练/推理模板统一 |
| 只看训练 loss | 误判效果 | 必须跑 eval 和 bad cases |
| 产物没转换 | 推理框架无法加载 | pth_to_hf 后再 merge |
| adapter 版本混乱 | 部署错模型 | MLflow 记录 run/version |
| 一次改太多参数 | 无法归因 | 每轮只改关键变量 |

其中最关键的是：训练模板和推理模板必须一致。

你训练时用一种 system/user/assistant 格式，部署时换了另一套 chat template，效果很可能明显变差。

## 十五、推荐目录结构

个人 XTuner 项目可以这样组织：

```text
ai-infra/
  data/
    sft/
      v1/
        train.jsonl
        eval.jsonl
        dataset_card.md
  configs/
    xtuner/
      qwen_lora_v1.py
      qwen_lora_v2.py
  work_dirs/
    qwen_lora_v1/
    qwen_lora_v2/
  models/
    base/
    adapters/
    merged/
  reports/
    eval/
    bad_cases/
  scripts/
    train_xtuner.py
    convert_merge.py
    eval_model.py
```

每个数据版本都要有一个 `dataset_card.md`，写清楚：

1. 数据来源。
2. 样本数量。
3. 任务定义。
4. 输出格式。
5. 清洗规则。
6. 评测集划分。
7. 已知问题。

这比你未来靠记忆恢复上下文可靠得多。

## 十六、一个推荐的个人微调流程

我建议个人用户按这个顺序来：

1. 先用 prompt/RAG 验证任务是否真的需要微调。
2. 准备 300-1000 条高质量 SFT 数据。
3. 单独留出 eval 集，不参与训练。
4. 找一个最接近的 XTuner config。
5. 复制配置并最小修改。
6. 用 QLoRA/LoRA 跑通第一版。
7. 转 HF adapter，必要时 merge。
8. 用 vLLM/LMDeploy 做本地服务。
9. 跑业务评测和 bad cases。
10. 用 MLflow 记录配置、指标、产物路径。
11. 收集失败样例，迭代数据。

这个流程看起来慢，但它能避免“训练了很多次，最后不知道哪个好”的混乱。

## 十七、总结：XTuner 是个人 AI Infra 的可控微调入口

个人轻量 AI Infra 不是把所有工具堆在一起，而是让每个工具负责自己的边界：

| 组件 | 角色 |
| --- | --- |
| Ray | 调度训练、评测、批量任务 |
| MLflow | 记录实验、产物、指标、版本 |
| XTuner | 执行 LoRA/QLoRA/SFT 微调 |
| vLLM/LMDeploy | 部署微调后的模型 |
| RAG/Agent | 消费模型能力并产生反馈 |

XTuner 的价值在于，它让个人用户可以用相对轻量的方式，把开源大模型改造成更适合自己任务的模型。

但要记住：微调不是魔法。真正决定效果的是数据质量、任务定义、评测体系和迭代闭环。

如果你已经有了 Ray、MLflow 和 vLLM/LMDeploy，那么 XTuner 就是把“模型能力改造”接入个人 AI Infra 的关键一环。

这就是个人轻量 AI Infra 的第五块拼图：微调层。

参考：

1. [XTuner 官方文档](https://xtuner.readthedocs.io/en/docs/)
2. [XTuner Quickstart 官方文档](https://xtuner.readthedocs.io/en/docs/get_started/quickstart.html)
3. [XTuner GitHub Releases](https://github.com/InternLM/xtuner/releases)
