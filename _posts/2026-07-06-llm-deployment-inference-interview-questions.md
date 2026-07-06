---
title: 大模型部署与推理面试题整理：核心问题与难点
tags:
  - LLM
  - 推理
  - 部署
  - 面试
  - AI
---

# 大模型部署与推理面试题整理：核心问题与难点

这篇整理面向大模型部署、推理加速和在线服务相关岗位面试，重点放在核心问题和重要难点：显存、KV Cache、prefill/decode、并发调度、量化、张量并行、吞吐延迟、服务稳定性和线上排障。

如果只记一条主线：

> 大模型推理优化的本质，是在显存、算力、带宽、延迟、吞吐和输出质量之间做系统权衡。

<!--more-->

---

## 一、推理基础与整体架构

### 1. 大模型部署和普通深度学习模型部署最大的区别是什么？

**答案：**

普通模型部署通常是固定输入、固定输出或短输出，推理过程一次前向基本结束。大模型部署是自回归生成，输出 token 需要一个一个生成，每生成一个 token 都要再次调用模型。

核心区别包括：

- 推理是多步生成，不是单次前向。
- 输入和输出长度变化很大。
- KV Cache 占用大量显存。
- 并发请求之间长度差异明显，调度复杂。
- 首 token 延迟和持续生成速度都很重要。
- 成本不仅取决于请求数，还取决于 token 数。

因此大模型部署更像一个“动态序列生成系统”，不是简单模型服务。

---

### 2. 大模型推理服务的典型架构是什么？

**答案：**

典型架构包括：

```text
客户端 / API Gateway
↓
鉴权、限流、路由
↓
Prompt 构造 / RAG / 工具调用
↓
推理调度器
↓
模型推理引擎
↓
流式输出 / 后处理 / 安全过滤
↓
日志、监控、计费、反馈收集
```

其中推理引擎负责模型加载、KV Cache 管理、batching、并行计算和 token 生成。线上系统还要考虑多模型路由、灰度发布、容灾、配额和成本控制。

---

### 3. LLM 推理为什么通常分成 prefill 和 decode 两个阶段？

**答案：**

prefill 阶段处理完整输入 prompt，一次性计算所有输入 token 的 hidden states，并建立 KV Cache。decode 阶段每次只输入上一步生成的新 token，利用 KV Cache 生成下一个 token。

区别：

- prefill：计算密集，适合并行，受 prompt 长度影响大。
- decode：每步生成一个 token，强依赖 KV Cache，通常更受显存带宽和调度影响。

面试中常见追问是：为什么长 prompt 会影响首 token 延迟？因为首 token 之前必须完成 prefill。

---

### 4. 什么是 TTFT 和 TPOT？

**答案：**

TTFT 是 Time To First Token，首 token 延迟，表示用户发起请求到收到第一个 token 的时间。它主要受排队、prompt 处理、prefill 计算和调度影响。

TPOT 是 Time Per Output Token，每个输出 token 的平均生成时间，反映 decode 阶段速度。它决定流式输出是否顺滑。

常见指标还有：

- latency：总响应时间。
- throughput：单位时间处理 token 数或请求数。
- QPS：每秒请求数。
- tokens/s：每秒生成 token 数。
- p95/p99 latency：尾延迟。

---

### 5. 为什么大模型服务既要看请求吞吐，也要看 token 吞吐？

**答案：**

因为不同请求的输入长度和输出长度差异很大。一个请求可能只生成 20 个 token，也可能生成 2000 个 token。只看 QPS 会误判系统负载。

更合理的指标包括：

- input tokens/s
- output tokens/s
- total tokens/s
- average input length
- average output length
- active sequences
- KV Cache usage

大模型计费和资源消耗通常更接近 token 维度。

---

## 二、KV Cache 与显存

### 6. 什么是 KV Cache？为什么它重要？

**答案：**

Transformer attention 中，每一层都会计算 Key 和 Value。自回归生成时，历史 token 的 K/V 不会变化，因此可以缓存起来，下一步只计算新 token 的 Query，并复用历史 K/V。

KV Cache 的作用：

- 避免重复计算历史 token。
- 显著加速 decode。
- 支持长上下文生成。

但它的代价是显存占用很大，而且随着 batch size、序列长度、层数、hidden size 增长而增长。

---

### 7. KV Cache 显存大概怎么估算？

**答案：**

粗略估算：

```text
KV Cache ≈ batch_size × seq_len × num_layers × 2(K,V) × num_kv_heads × head_dim × bytes_per_element
```

如果使用 MHA，num_kv_heads 等于 num_attention_heads。如果使用 MQA/GQA，num_kv_heads 更少，KV Cache 会明显降低。

这个公式常被用来解释：为什么长上下文和高并发会迅速吃满显存。

---

### 8. 为什么长上下文会显著增加推理成本？

**答案：**

长上下文影响两个阶段：

- prefill 阶段：输入 token 越多，attention 计算越重。
- decode 阶段：每生成一个 token 都要 attend 到更长历史，KV Cache 占用也更大。

长上下文还会降低 batch 调度效率，因为不同请求长度差异更大，容易出现显存碎片和尾延迟。

---

### 9. MHA、MQA、GQA 对推理有什么影响？

**答案：**

MHA 是 Multi-Head Attention，每个 attention head 都有独立 K/V。MQA 是 Multi-Query Attention，多个 Q head 共享一组 K/V。GQA 是 Grouped-Query Attention，多个 Q head 分组共享 K/V。

推理影响：

- MHA：表达能力强，但 KV Cache 大。
- MQA：KV Cache 小，decode 更省显存和带宽。
- GQA：在效果和推理效率之间折中。

现代大模型常使用 GQA 来降低推理成本。

---

### 10. KV Cache 为什么会造成显存碎片？

**答案：**

线上请求长度不一致，有的短、有的长，有的提前结束，有的继续生成。如果用连续内存为每个请求分配 KV Cache，请求完成后会留下大小不一的空洞，导致显存碎片。

显存碎片会让系统明明还有空闲显存，却无法为新请求分配连续空间。

vLLM 的 PagedAttention 就是为了解决这类问题。

---

### 11. PagedAttention 的核心思想是什么？

**答案：**

PagedAttention 借鉴操作系统分页思想，把 KV Cache 切成固定大小的 block，而不是为每个请求分配一整块连续内存。

优势：

- 降低 KV Cache 内存碎片。
- 更灵活地管理不同长度请求。
- 支持更高并发。
- 对 beam search、parallel sampling 等场景更友好。

核心理解：它不是改变模型计算逻辑，而是优化 KV Cache 的内存管理方式。

---

### 12. KV Cache 可以量化吗？

**答案：**

可以。KV Cache 量化可以降低显存占用和显存带宽压力，例如将 FP16/BF16 KV Cache 压到 INT8 或更低精度。

风险是可能影响生成质量，尤其是长上下文、复杂推理和精确复制任务。是否使用 KV Cache 量化需要根据任务评估。

适合场景：

- 高并发服务。
- 长上下文场景。
- 对质量轻微下降可接受。
- 显存是瓶颈。

---

## 三、Batching 与调度

### 13. 大模型推理中的 batching 为什么复杂？

**答案：**

传统模型 batching 通常把相同形状输入组成 batch。大模型请求长度不同、输出长度未知、到达时间不同，而且 decode 是逐 token 进行。

复杂点：

- prompt 长度不同。
- 生成长度不同。
- 有的请求先结束，有的还在生成。
- 新请求不断到达。
- batch 中每个序列的 decode step 不同。

因此需要动态 batching、continuous batching 或 iteration-level scheduling。

---

### 14. 什么是 dynamic batching？

**答案：**

dynamic batching 是在短时间窗口内收集多个请求组成 batch 一起推理，提高 GPU 利用率。

优点：

- 提高吞吐。
- 降低单位 token 成本。

缺点：

- 需要等待窗口，可能增加延迟。
- 对长短不一请求效率有限。

大模型服务通常会进一步使用 continuous batching。

---

### 15. 什么是 continuous batching？

**答案：**

continuous batching 是在每个 decode iteration 动态维护 batch。已经完成的请求可以退出，新请求可以加入，而不是等整个 batch 全部结束。

优势：

- 提高 GPU 利用率。
- 减少短请求被长请求拖住的问题。
- 更适合流式生成。

它是现代 LLM serving engine 的关键能力之一。

---

### 16. 为什么短请求会被长请求拖慢？

**答案：**

如果调度策略把多个请求固定在同一个 batch 中，batch 要等长输出请求生成完才释放。短请求虽然早就完成，但资源和调度仍受长请求影响。

continuous batching 可以让短请求完成后立即退出 batch，提高整体效率。

---

### 17. prefill 和 decode 应该混合调度吗？

**答案：**

这是一个重要难点。prefill 计算密集，decode 更像小步反复执行，二者资源特征不同。混合调度可以提高 GPU 利用率，但也可能让长 prompt prefill 阻塞正在 decode 的请求，导致流式输出卡顿。

常见策略：

- 限制每轮 prefill token 数。
- 将 prefill 和 decode 分离调度。
- 使用 chunked prefill。
- 根据延迟目标调整优先级。

目标是在 TTFT 和 TPOT 之间平衡。

---

### 18. 什么是 chunked prefill？

**答案：**

chunked prefill 是把长 prompt 的 prefill 拆成多个小块执行，而不是一次性处理完整 prompt。

好处：

- 避免长 prompt 长时间占用 GPU。
- 降低对 decode 请求的阻塞。
- 改善流式输出稳定性。

代价是调度更复杂，可能略增加总计算开销。

---

### 19. 如何设计请求调度优先级？

**答案：**

要结合业务目标。常见维度：

- 请求等待时间。
- 用户等级或 SLA。
- prompt 长度。
- 预计输出长度。
- 是否是流式请求。
- 是否已经进入 decode。
- 当前 KV Cache 占用。

一个常见原则是：已经在 decode 的请求要保持稳定输出，不能频繁被长 prefill 打断，否则用户会感觉卡顿。

---

### 20. 如何处理队列拥塞？

**答案：**

队列拥塞说明请求到达速度超过服务能力。可采取：

- 限流和排队超时。
- 降级到小模型。
- 缩短 max tokens。
- 限制长 prompt。
- 优先保障高优先级请求。
- 增加副本或扩容 GPU。
- 返回明确的 retry-after。

不要无限排队，否则 p99 延迟会爆炸，用户体验更差。

---

## 四、量化与压缩

### 21. 为什么量化能加速或省资源？

**答案：**

量化把模型权重或激活从 FP16/BF16 转成 INT8、INT4 等低精度表示。

收益：

- 减少模型权重显存。
- 降低显存带宽压力。
- 可能提升吞吐。
- 让更大模型装进有限 GPU。

但是否加速取决于硬件和 kernel 支持。如果没有高效 INT4/INT8 kernel，只是省显存，不一定显著加速。

---

### 22. Weight-only quantization 是什么？

**答案：**

Weight-only quantization 只量化模型权重，激活通常仍用 FP16/BF16。它实现相对简单，常用于 LLM 推理。

优点：

- 显存占用下降明显。
- 对模型质量影响相对可控。

缺点：

- 激活和 KV Cache 仍占显存。
- 加速依赖高效 kernel。

---

### 23. INT8 和 INT4 量化怎么选？

**答案：**

INT8 通常质量更稳，INT4 压缩更强但质量风险更高。

选择时考虑：

- 模型大小。
- 显存约束。
- 任务对精度敏感程度。
- 是否有校准数据。
- 推理框架是否支持高效 kernel。

如果是客服、摘要、通用问答，INT4 可能可接受；如果是代码、数学、严肃领域问答，需要更谨慎评估。

---

### 24. GPTQ、AWQ、SmoothQuant 分别是什么思路？

**答案：**

GPTQ 是一种后训练量化方法，利用近似二阶信息逐层量化权重，尽量减少量化误差。AWQ 关注激活感知权重量化，保护重要通道以降低质量损失。SmoothQuant 通过在权重和激活之间平滑缩放，将激活异常值压力转移到权重上，更适合 W8A8 量化。

面试回答不需要背细节，但要说明：

- GPTQ/AWQ 常用于 weight-only 低比特量化。
- SmoothQuant 更关注权重和激活同时量化。
- 量化方案要结合硬件和推理框架选择。

---

### 25. 量化后模型效果变差怎么排查？

**答案：**

排查方向：

- 是否使用了合适的校准数据。
- 是否量化了敏感层，例如 embedding、lm_head。
- group size 是否过大。
- 是否使用了不适合该模型结构的量化方法。
- tokenizer 和 prompt template 是否一致。
- 评估任务是否对精度敏感。

可尝试：

- 从 INT4 回退到 INT8。
- 排除部分层不量化。
- 更换 AWQ/GPTQ 等方法。
- 增加校准数据质量。

---

### 26. 量化和 LoRA adapter 部署有什么关系？

**答案：**

常见情况是 base model 量化，LoRA adapter 保持 FP16/BF16。推理时要确认框架支持量化 base + adapter。如果要 merge LoRA，再量化一次可能更稳定，但会失去动态切换 adapter 的便利。

部署选择：

- 多 adapter：量化 base + 动态加载 adapter。
- 单任务模型：merge 后整体量化。

两种方式都要重新做质量评估。

---

## 五、并行与多 GPU 部署

### 27. 为什么大模型部署需要多 GPU？

**答案：**

原因主要有：

- 单卡显存装不下模型权重。
- KV Cache 和 batch 占用显存大。
- 单卡吞吐不足。
- 长上下文和高并发需要更多资源。

多 GPU 不是免费提升。通信成本、并行策略和负载均衡会成为新瓶颈。

---

### 28. Tensor Parallelism 是什么？

**答案：**

Tensor Parallelism 是把模型内部的大矩阵计算切分到多张 GPU 上。例如把 attention 或 MLP 的线性层按列或按行拆分，每张卡计算一部分，然后通信合并结果。

适合：

- 单层矩阵很大。
- 模型单卡放不下。
- 需要降低单卡计算压力。

代价是每层都可能需要通信，GPU 间带宽很重要。

---

### 29. Pipeline Parallelism 是什么？

**答案：**

Pipeline Parallelism 是把不同 Transformer layers 分到不同 GPU 上，数据按流水线经过各段。

优点：

- 可以部署超大模型。
- 每张卡只保存部分层。

缺点：

- 自回归 decode batch 较小时流水线效率差。
- 容易产生 pipeline bubble。
- 延迟可能增加。

在线推理中，Tensor Parallelism 通常更常见，Pipeline Parallelism 要看模型规模和场景。

---

### 30. Data Parallelism 在推理中怎么用？

**答案：**

推理中的 Data Parallelism 通常是复制多个完整模型副本，每个副本处理不同请求。它适合模型单卡或单节点能放下，但需要提高整体 QPS 的场景。

优点：

- 简单稳定。
- 扩容方便。

缺点：

- 每个副本都要占完整模型显存。
- 不能解决单副本模型放不下的问题。

---

### 31. Expert Parallelism 是什么？

**答案：**

Expert Parallelism 常用于 MoE 模型。MoE 模型有多个专家，每个 token 只路由到部分专家。Expert Parallelism 将不同专家分布到不同 GPU 上。

难点：

- token routing 会带来通信。
- 专家负载可能不均衡。
- batch 小时 GPU 利用率可能低。
- 线上调度复杂。

MoE 推理的关键不是只看总参数，而要看 active parameters 和通信效率。

---

### 32. 多 GPU 推理瓶颈通常在哪里？

**答案：**

常见瓶颈：

- GPU 间通信带宽。
- all-reduce / all-gather 延迟。
- KV Cache 分布和访问。
- batch 太小导致利用率低。
- CPU 调度或数据拷贝。
- 网络 IO 和流式输出。

如果 Tensor Parallelism 扩到更多卡但吞吐没有线性提升，通常是通信开销抵消了计算收益。

---

## 六、推理引擎与加速框架

### 33. vLLM 的核心优势是什么？

**答案：**

vLLM 的核心优势是高吞吐 LLM serving，代表性能力包括 PagedAttention、continuous batching、OpenAI-compatible API、多模型支持等。

它特别适合在线服务中大量并发请求、长度变化明显、需要高吞吐的场景。

面试回答重点：vLLM 的关键不是“能跑模型”，而是通过 KV Cache 管理和调度提升 serving 效率。

---

### 34. TensorRT-LLM 的优势是什么？

**答案：**

TensorRT-LLM 更偏 NVIDIA GPU 上的深度优化推理，包括 kernel fusion、量化、Tensor Parallelism、FP8/INT8/INT4 支持、图优化等。

适合：

- 对极致性能要求高。
- NVIDIA 生态。
- 模型和部署形态相对固定。
- 能接受编译和工程复杂度。

它通常比通用框架更需要工程调优。

---

### 35. TGI、vLLM、TensorRT-LLM 怎么选？

**答案：**

可以这样回答：

- vLLM：通用高吞吐 serving，易用性和性能平衡好。
- TGI：Hugging Face 生态友好，部署开源模型方便。
- TensorRT-LLM：追求 NVIDIA GPU 极致性能，工程复杂度更高。

选择依据：

- 模型结构是否支持。
- 是否需要高并发。
- 是否需要量化。
- 硬件类型。
- 团队工程能力。
- 是否需要快速迭代。

---

### 36. 为什么 kernel fusion 能加速？

**答案：**

GPU 计算中，很多小算子会频繁读写显存并产生 kernel launch 开销。kernel fusion 把多个操作合并成一个 kernel，减少中间结果写回和 launch 次数。

收益：

- 降低显存读写。
- 降低 kernel launch overhead。
- 提高 GPU 利用率。

在 LLM 中，LayerNorm、activation、linear、attention 等都可能受益于 fused kernels。

---

### 37. FlashAttention 为什么能提升 attention 性能？

**答案：**

FlashAttention 通过 IO-aware 设计减少 HBM 读写，分块计算 attention，避免显式保存完整 attention matrix。

优势：

- 降低显存占用。
- 提高 attention 计算效率。
- 对长序列尤其有价值。

它不是改变 attention 数学结果，而是改变计算组织方式。

---

### 38. speculative decoding 是什么？

**答案：**

speculative decoding 使用一个小模型先快速生成多个候选 token，再由大模型验证这些 token。如果候选被接受，就可以一次推进多个 token，从而减少大模型调用次数。

关键点：

- 小模型要足够快。
- 小模型输出要和大模型分布接近。
- 接受率决定加速效果。
- 最终分布可以保持与大模型一致。

适合 decode 阶段瓶颈明显的场景。

---

### 39. speculative decoding 为什么不一定总能加速？

**答案：**

原因包括：

- 小模型候选接受率低。
- 小模型本身也占资源。
- 验证过程带来额外开销。
- batch serving 中调度更复杂。
- 任务输出不确定性高，候选难命中。

如果接受率低，反而可能变慢。

---

### 40. Prefix Cache / Prompt Cache 是什么？

**答案：**

Prefix Cache 是缓存相同 prompt 前缀的 KV Cache。例如多个请求共享相同 system prompt、工具说明或长文档前缀，就可以复用前缀计算结果。

适合：

- 固定 system prompt。
- 多轮对话中复用历史前缀。
- RAG 中重复文档上下文。
- Agent 工具说明很长。

限制是前缀必须完全一致或可安全复用，否则容易错用上下文。

---

## 七、延迟、吞吐与成本优化

### 41. 如何降低 TTFT？

**答案：**

可以从这些方向优化：

- 减少 prompt 长度。
- 使用 prompt cache。
- 优化 prefill batch。
- 使用更快模型或量化模型。
- 降低排队时间。
- 进行请求路由和负载均衡。
- 使用 chunked prefill 避免长 prompt 阻塞。
- 将 RAG 检索和 prompt 构造优化到毫秒级。

TTFT 不只取决于模型，还取决于网关、检索、排队和调度。

---

### 42. 如何提升输出 token 速度？

**答案：**

主要优化 decode 阶段：

- 使用高效推理引擎。
- 开启 continuous batching。
- 使用 KV Cache。
- 使用 GQA/MQA 模型。
- 量化权重或 KV Cache。
- 使用 Tensor Parallelism。
- 尝试 speculative decoding。
- 优化采样 kernel。

如果瓶颈是显存带宽，单纯增加算力不一定有效。

---

### 43. 如何提升吞吐但不显著增加延迟？

**答案：**

需要平衡 batching 和排队：

- 设置合理 batching window。
- 使用 continuous batching。
- 按请求长度分桶。
- 对长请求做单独队列。
- 限制最大输出长度。
- 监控 p95/p99 延迟，而不是只看平均值。
- 根据 SLA 做优先级调度。

吞吐优化不能只看 tokens/s，还要看用户可感知延迟。

---

### 44. 为什么 temperature 会影响服务稳定性？

**答案：**

temperature 影响生成随机性。temperature 较高时，模型可能输出更长、更发散、更难预测的内容，导致输出 token 数变多，服务成本和延迟上升。

在生产环境中，需要限制：

- max tokens。
- stop sequences。
- temperature 范围。
- top_p/top_k 范围。
- 用户自定义采样参数权限。

否则用户可以通过参数造成资源消耗异常。

---

### 45. max tokens 为什么是重要的服务参数？

**答案：**

max tokens 直接限制最大输出长度，影响：

- 单请求成本。
- GPU 占用时间。
- 队列等待。
- p99 延迟。
- 用户体验。

没有 max tokens 限制，少量超长输出请求就可能拖垮服务。

---

### 46. 如何做长短请求隔离？

**答案：**

可以按 prompt length、max tokens、预计总 tokens 分队列或分模型副本。

策略：

- 短请求走低延迟队列。
- 长请求走批处理或低优先级队列。
- 超长上下文走专用实例。
- 不同 SLA 用户分层调度。

这样可以避免少量长请求显著影响短请求 p99 延迟。

---

### 47. 如何估算大模型服务成本？

**答案：**

要从 token 和资源两个维度估算：

```text
成本 ≈ GPU 单位时间成本 × 服务运行时间 / 有效 token 吞吐
```

还要考虑：

- 输入 token 和输出 token 比例。
- 平均并发。
- 峰值流量。
- GPU 利用率。
- 模型副本数量。
- KV Cache 显存限制。
- 冗余和容灾。

单位成本通常用“每百万 token 成本”更直观。

---

### 48. 为什么 GPU 利用率高不一定代表服务好？

**答案：**

GPU 利用率高可能意味着吞吐高，也可能意味着排队严重、请求长时间等待。服务质量还要看：

- TTFT。
- TPOT。
- p95/p99 latency。
- timeout rate。
- queue length。
- 用户取消率。

如果 GPU 一直满载但 p99 延迟爆炸，说明系统已经过载。

---

## 八、流式输出与 API 服务

### 49. 为什么大模型服务常用流式输出？

**答案：**

因为完整生成可能耗时较长，流式输出可以让用户更早看到内容，降低感知延迟。

优点：

- 改善用户体验。
- 降低等待焦虑。
- 支持边生成边展示。

缺点：

- 服务端连接保持时间更长。
- 网关和客户端要处理 SSE/WebSocket。
- 中途错误和取消更复杂。

---

### 50. SSE 和 WebSocket 在 LLM 场景怎么选？

**答案：**

SSE 适合服务端单向持续推送 token，实现简单，和 HTTP 生态兼容好。WebSocket 适合双向交互、复杂实时协议、多路事件。

多数 Chat Completion 流式输出用 SSE 就够了。Agent、多人协作、实时控制类场景可能更适合 WebSocket。

---

### 51. 用户取消请求后服务端要做什么？

**答案：**

服务端要及时停止生成并释放资源：

- 取消 decode。
- 释放 KV Cache。
- 从调度队列移除。
- 关闭流式连接。
- 记录取消原因。

如果客户端断开但服务端继续生成，会浪费 GPU 资源。

---

### 52. 如何保证 API 兼容 OpenAI 格式？

**答案：**

要实现兼容的请求和响应 schema，包括：

- `/v1/chat/completions`
- messages 格式。
- model、temperature、top_p、max_tokens。
- stream 模式。
- usage token 统计。
- finish_reason。
- error 格式。

兼容 API 的好处是生态工具可直接接入，但内部仍要做参数校验和安全限制。

---

### 53. usage token 统计为什么重要？

**答案：**

usage 统计用于计费、限流、成本分析和容量规划。需要准确统计：

- prompt_tokens。
- completion_tokens。
- total_tokens。

如果使用 RAG、工具调用、多轮上下文拼接，也要统计最终送入模型的真实 tokens，而不是只统计用户原始输入。

---

## 九、RAG、工具调用与推理链路

### 54. RAG 会给推理部署带来哪些额外问题？

**答案：**

RAG 增加了模型前的检索和 prompt 构造链路。

额外问题：

- 检索延迟增加 TTFT。
- 检索结果长度增加 prefill 成本。
- 文档过多导致上下文拥挤。
- 检索失败会导致生成错误。
- 引用和来源需要后处理校验。

优化方向包括检索缓存、rerank 优化、上下文压缩和引用校验。

---

### 55. Agent 工具调用为什么会增加部署复杂度？

**答案：**

工具调用把一次模型请求变成多轮模型和外部系统交互：

```text
模型判断调用工具
↓
执行工具
↓
工具结果返回模型
↓
模型继续生成
```

复杂点：

- 延迟不可控。
- 工具失败要重试或降级。
- 工具参数要校验。
- 多轮调用会增加 token 成本。
- 安全边界更复杂。

---

### 56. Function Calling 是推理能力还是工程协议？

**答案：**

两者都有。模型需要具备生成结构化 tool call 的能力，这是模型行为；服务端需要解析、执行、校验和回填工具结果，这是工程协议。

可靠工具调用不能只靠模型，需要：

- schema 约束。
- 参数校验。
- 权限控制。
- 工具超时和重试。
- 调用日志。
- 安全审计。

---

### 57. 如何降低 Agent 推理成本？

**答案：**

可以从以下方向：

- 减少工具说明长度。
- 使用 prompt cache。
- 用小模型做简单路由。
- 限制最大工具调用轮数。
- 对工具结果做摘要压缩。
- 缓存常见工具结果。
- 对无需大模型的步骤用规则执行。

Agent 成本常常不是单次模型调用，而是多轮调用累积。

---

## 十、稳定性、安全与线上排障

### 58. 大模型线上服务最重要的监控指标有哪些？

**答案：**

核心指标：

- QPS。
- input/output tokens/s。
- TTFT、TPOT、p95/p99 latency。
- queue length。
- GPU utilization。
- GPU memory usage。
- KV Cache usage。
- timeout rate。
- error rate。
- request cancel rate。
- OOM 次数。

业务指标：

- 用户满意度。
- 解决率。
- 人工接管率。
- 安全拦截率。
- 幻觉投诉率。

---

### 59. 线上 OOM 常见原因有哪些？

**答案：**

常见原因：

- batch size 过大。
- max context length 设置过高。
- 输出长度过长。
- KV Cache 占用超过预期。
- 突发长请求。
- 显存碎片。
- 多模型共卡互相挤占。
- adapter 或量化配置加载异常。

排查时要看 OOM 前的 active sequences、max seq len、KV Cache usage、batch token 数和显存曲线。

---

### 60. 如何处理线上 OOM？

**答案：**

短期措施：

- 降低 max batch tokens。
- 降低 max model len。
- 限制 max output tokens。
- 拒绝超长请求。
- 重启异常实例。
- 将长请求路由到专用实例。

长期措施：

- 使用 PagedAttention。
- KV Cache 量化。
- 更合理的调度策略。
- 容量规划和压测。
- 更细的监控和预警。

---

### 61. p99 延迟突然升高怎么排查？

**答案：**

按链路排查：

1. 网关是否排队或限流。
2. RAG/工具调用是否变慢。
3. prompt 长度是否变长。
4. 推理队列是否堆积。
5. 是否出现大量长输出请求。
6. GPU 显存和 KV Cache 是否接近上限。
7. 是否有某个模型副本异常。
8. 网络或流式连接是否异常。

要区分 TTFT 升高还是 TPOT 变慢。TTFT 多与排队/prefill 有关，TPOT 多与 decode/GPU/KV Cache 有关。

---

### 62. 为什么模型服务会出现吞吐下降但 GPU 利用率不低？

**答案：**

可能原因：

- batch 中长短请求混杂，调度效率低。
- decode 阶段显存带宽成为瓶颈。
- GPU 忙于低效小 batch。
- CPU 调度或 tokenizer 成为瓶颈。
- 网络流式输出阻塞。
- 跨卡通信开销大。

GPU utilization 不等于有效 token throughput，需要结合 tokens/s 和队列情况判断。

---

### 63. tokenizer 会成为推理瓶颈吗？

**答案：**

会，尤其在高 QPS、短请求或 CPU 资源不足时。tokenization 和 detokenization 都在模型前后链路中，可能成为瓶颈。

优化方式：

- tokenizer 并行化。
- 缓存常见 prompt tokenization。
- 避免重复 tokenize system prompt。
- 将 tokenizer 服务资源和 GPU 服务分开监控。

---

### 64. 如何做大模型服务灰度发布？

**答案：**

灰度发布要控制风险：

- 新模型先离线评估。
- 小流量灰度。
- 按用户、租户或请求类型路由。
- 监控质量、延迟、错误率和成本。
- 支持快速回滚。
- 保留旧模型对照组。

灰度不只看系统指标，还要看业务质量指标。

---

### 65. 如何设计回滚机制？

**答案：**

需要能够快速回到旧模型和旧配置：

- 模型版本不可覆盖。
- tokenizer、prompt template、adapter 一起版本化。
- 路由层支持切回旧版本。
- 配置中心支持回滚。
- 新模型输出日志可追踪。
- 评估和上线记录可查。

大模型服务中，prompt template 变更也可能造成事故，所以也要纳入回滚。

---

### 66. 大模型服务有哪些安全风险？

**答案：**

常见风险：

- Prompt injection。
- 敏感信息泄露。
- 越权工具调用。
- 生成违法违规内容。
- 模型输出幻觉导致决策风险。
- 训练或日志中泄露隐私。
- 用户构造超长输入消耗资源。

安全措施包括输入过滤、输出审核、权限控制、工具沙箱、日志脱敏、限流和红队测试。

---

### 67. 如何防止恶意用户拖垮推理服务？

**答案：**

措施：

- 按用户限流。
- 限制 prompt tokens 和 max output tokens。
- 限制并发连接数。
- 限制采样参数范围。
- 设置请求超时。
- 对异常 token 消耗做熔断。
- 对免费用户和付费用户分层。

资源保护是 LLM 服务的基础能力。

---

## 十一、模型选择与容量规划

### 68. 如何选择部署 7B、14B、32B 还是更大模型？

**答案：**

要综合效果和成本：

- 任务复杂度。
- 延迟要求。
- 并发规模。
- GPU 预算。
- 上下文长度。
- 是否可以通过 RAG 或工具补能力。
- 是否需要多语言、代码、推理能力。

小模型适合高频简单任务，大模型适合复杂推理和高价值请求。很多系统会用路由策略：简单请求走小模型，复杂请求走大模型。

---

### 69. 如何做模型路由？

**答案：**

模型路由可以根据请求复杂度、用户等级、任务类型和成本目标选择不同模型。

策略：

- 规则路由：按任务类型固定选择。
- 分类器路由：判断难度或领域。
- 小模型先答，失败再升级大模型。
- 根据 SLA 选择低延迟或高质量模型。

模型路由要避免过度复杂，否则排障困难。

---

### 70. 容量规划怎么做？

**答案：**

需要先估算流量画像：

- 峰值 QPS。
- 平均输入 tokens。
- 平均输出 tokens。
- p95 输入和输出长度。
- 并发连接数。
- SLA 延迟目标。

然后压测不同配置下的 tokens/s、TTFT、TPOT 和显存使用，计算需要多少模型副本和 GPU。容量规划必须使用接近真实流量的请求分布，不能只用固定短 prompt 压测。

---

### 71. 为什么压测要使用真实 token 分布？

**答案：**

因为 LLM 性能高度依赖输入和输出长度。如果压测只用短 prompt，会高估吞吐、低估显存和延迟。如果只用固定长度，也看不出调度碎片和长尾问题。

真实压测应包含：

- 短请求。
- 长 prompt。
- 长输出。
- 多轮对话。
- RAG 上下文。
- 流式取消。
- 峰值突发。

---

### 72. 如何判断是扩容 GPU 还是优化系统？

**答案：**

如果系统已经高效利用 GPU，且瓶颈是计算资源，扩容有效。如果瓶颈是调度、KV Cache 管理、prompt 过长、tokenizer、RAG 延迟或网络，盲目加 GPU 收益有限。

判断方式：

- 看 GPU utilization 和 tokens/s。
- 看 queue length。
- 看 TTFT/TPOT 分解。
- 看 KV Cache usage。
- 看 CPU 和网络。
- 做 profile。

先定位瓶颈，再决定扩容还是优化。

---

## 十二、综合场景题

### 73. 如果用户反馈首字很慢，你会怎么排查？

**答案：**

首字慢对应 TTFT 高。我会拆链路：

1. 网关排队是否高。
2. 鉴权、限流、路由是否耗时。
3. RAG 检索是否慢。
4. prompt 是否过长。
5. prefill batch 是否被长请求阻塞。
6. 是否有大量冷启动或模型切换。
7. GPU 是否满载。

优化方向包括 prompt cache、缩短上下文、优化 RAG、chunked prefill、长短请求隔离和扩容。

---

### 74. 如果流式输出一顿一顿的，你会怎么排查？

**答案：**

这通常对应 TPOT 不稳定。

排查：

- decode 是否被长 prefill 打断。
- continuous batching 是否正常。
- GPU 是否周期性满载。
- KV Cache 是否接近上限。
- 网络/SSE 是否阻塞。
- 客户端渲染是否慢。
- 是否有 GC 或 CPU 调度抖动。

优化方向是稳定 decode 调度，限制长 prefill，改善 batch 策略，优化流式链路。

---

### 75. 如果要把一个 70B 模型部署到线上，你会考虑什么？

**答案：**

我会从以下方面设计：

- 权重显存：是否需要多 GPU、量化、Tensor Parallelism。
- KV Cache：目标上下文长度和并发下是否装得下。
- 推理引擎：vLLM、TensorRT-LLM 或其他框架。
- 并行策略：TP 大小、是否跨节点。
- SLA：TTFT、TPOT、p95/p99。
- 调度：continuous batching、长短请求隔离。
- 成本：单位百万 token 成本。
- 稳定性：监控、限流、回滚、灰度。
- 安全：输入输出过滤和权限控制。

70B 部署难点不只是模型能否加载，而是能否在目标成本和 SLA 下稳定服务。

---

### 76. 如果线上成本太高，你会怎么优化？

**答案：**

先分解成本来源：

- 输入 token 是否过长。
- 输出 token 是否过长。
- 是否大量简单请求使用了大模型。
- GPU 利用率是否低。
- 是否存在低效 batch。
- RAG 上下文是否冗余。

优化方案：

- prompt 压缩。
- 限制 max tokens。
- 小模型路由。
- 量化。
- continuous batching。
- cache 常见前缀和检索结果。
- 对简单任务使用规则或传统模型。

---

### 77. 如果模型输出质量好但延迟不达标，你会怎么取舍？

**答案：**

可以分层解决：

- 高价值请求继续用大模型。
- 普通请求走小模型或量化模型。
- 使用流式输出降低感知延迟。
- 优化 prompt 长度。
- 用 RAG 压缩上下文。
- 增加推理副本。
- 使用 speculative decoding 或更高效引擎。

最终要看业务 SLA。如果实时性比极致质量更重要，就要接受模型变小或量化带来的轻微质量损失。

---

### 78. 如何向面试官总结 LLM 推理优化？

**答案：**

可以这样说：

> LLM 推理优化不是单点优化，而是围绕 prefill、decode、KV Cache、batch 调度、量化、并行和服务治理做系统工程。核心目标是在质量可接受的前提下，同时控制 TTFT、TPOT、吞吐、显存和成本。

这句话能覆盖技术本质和工程目标。

---

## 十三、速记清单

- 首 token 慢：看 TTFT、prefill、排队、RAG、prompt 长度。
- 输出卡顿：看 TPOT、decode 调度、KV Cache、流式链路。
- 显存爆：看权重、KV Cache、batch tokens、max context。
- 吞吐低：看 batching、GPU 利用率、tokenizer、通信。
- 成本高：看 token 长度、模型路由、量化、缓存。
- 质量掉：看量化误差、prompt template、采样参数、模型版本。
- 服务稳：限流、超时、监控、灰度、回滚、日志缺一不可。

