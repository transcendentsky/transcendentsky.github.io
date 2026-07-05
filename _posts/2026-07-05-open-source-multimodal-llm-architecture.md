---
title: 现在主流开源多模态大模型的架构是怎样的？
tags:
  - AI
  - 多模态大模型
  - 模型架构
---

过去两年，多模态大模型从“给语言模型接一个视觉模块”迅速演进到“原生处理图像、视频、音频、文档和工具操作”的统一系统。以 Qwen、DeepSeek、InternVL、LLaVA-OneVision 等开源或开放权重模型为代表，主流架构已经形成了几条清晰路线。

<!--more-->

## 一、最经典的三段式：视觉编码器 + 连接器 + LLM

最常见的视觉语言模型架构可以概括为：

```text
图像/视频 -> Vision Encoder -> Projector / Merger -> LLM -> 文本输出
文本 ------------------------------^
```

这里的核心思想很直接：图像不能直接喂给语言模型，所以先用 ViT、CLIP、SigLIP、DFN-ViT 等视觉编码器把图像切成 patch token，再用一个投影层、MLP 或 resampler 把视觉特征映射到语言模型的 embedding 维度，最后把视觉 token 和文本 token 一起送入 LLM。

早期的 LLaVA 就是这个路线：CLIP ViT 负责看图，MLP projector 负责对齐，Vicuna/LLaMA 负责语言理解和回答。今天很多强模型仍然保留这个骨架，只是每个部件都变强了：视觉编码器支持更高分辨率，连接器能压缩 token，LLM 变成 Qwen、DeepSeekMoE、InternLM 等更强基座。

## 二、Qwen 路线：原生动态分辨率 + 多模态 RoPE

Qwen-VL 系列是当前开源多模态架构里非常有代表性的一支。

以 [Qwen2.5-VL 技术报告](https://arxiv.org/abs/2502.13923) 为例，它仍然由三部分组成：Qwen2.5 LLM、重新设计的 ViT 视觉编码器，以及 MLP-based Vision-Language Merger。不同点在于，Qwen 不再简单地把图像缩放到固定尺寸，而是采用原生动态分辨率：不同尺寸的图片会产生不同长度的视觉 token，尽量保留原图比例和细节。

Qwen2.5-VL 的视觉编码器使用 14x14 patch，加入 2D RoPE、window attention、RMSNorm、SwiGLU 等设计。为了控制计算量，它不是所有层都做全局注意力，而是大多数层使用窗口注意力，只在少数层做 full attention。视觉 token 进入 LLM 前，还会通过 merger 把相邻 patch 特征合并压缩，降低长图、文档和视频带来的 token 成本。

Qwen 的另一个关键设计是 MRoPE，也就是 Multimodal Rotary Position Embedding。普通文本 RoPE 只有一维位置，而图片和视频天然有高度、宽度、时间三个维度。Qwen 把位置编码拆成 temporal、height、width 三部分，让模型知道某个视觉 token 在画面哪里、视频第几帧、时间上对应什么位置。Qwen2.5-VL 进一步把视频时间对齐到绝对时间，增强长视频和事件定位能力。

到 [Qwen3-VL](https://arxiv.org/abs/2511.21631)，这条路线继续升级：支持 256K 级别的长上下文，模型家族同时包含 dense 和 MoE 版本，并引入 interleaved-MRoPE、DeepStack 多层 ViT 特征融合，以及更明确的视频时间对齐。这说明 Qwen 的重点不是只做“看图问答”，而是把图像、视频、文档、GUI 操作和长上下文都统一进一个 token 流里。

## 三、DeepSeek-VL2 路线：动态切图 + MoE 语言骨干

DeepSeek 的多模态路线更强调效率和 MoE。

[DeepSeek-VL2](https://arxiv.org/abs/2412.10302) 的整体结构也是视觉编码器加语言模型，但它有两个鲜明特征：第一是动态 tiling 视觉编码，第二是 DeepSeekMoE 语言骨干。

动态 tiling 可以理解为：面对高分辨率、不同长宽比的图片，模型不只是粗暴缩放，而是把图像切成适合编码的 tile，让局部细节保留下来。这对 OCR、表格、图表、文档理解尤其重要。

语言侧，DeepSeek-VL2 使用 DeepSeekMoE，并结合 Multi-head Latent Attention，把 KV cache 压缩到 latent vectors，以提升推理吞吐。它公开的版本包括 Tiny、Small 和标准版，激活参数分别约为 1.0B、2.8B、4.5B。这里的重点是“总参数可以很大，但每个 token 只激活部分专家”，从而在成本和能力之间取得平衡。

这也是今天大模型架构的一个大趋势：多模态输入越来越长，图片、视频、文档会制造大量 token；如果语言骨干仍然是纯 dense Transformer，推理成本会很快变高。因此 MoE、KV cache 压缩、token 压缩、窗口注意力等技术会越来越重要。

## 四、Janus 路线：理解和生成解耦，但共享 Transformer

DeepSeek 还有另一条很有意思的路线：Janus / Janus-Pro。

传统视觉语言模型主要做理解：输入图像，输出文本。但 Janus 想同时做图像理解和图像生成。问题是，理解和生成需要的视觉表示并不一样：理解任务更需要语义抽象，生成任务更需要细粒度视觉细节。把两者塞进同一个视觉编码器，容易互相妨碍。

所以 [Janus](https://arxiv.org/abs/2410.13848) 的核心是“解耦视觉编码”：理解和生成使用不同的视觉编码路径，但后面共享一个统一的自回归 Transformer。[Janus-Pro](https://arxiv.org/abs/2501.17811) 则在训练策略、数据规模和模型规模上继续扩展，提升图像理解和文生图指令跟随能力。

这代表了另一类多模态模型：不只是“图片进、文字出”，而是“多模态进、多模态出”。Qwen2.5-Omni 也属于这个大方向，只是它重点放在文本、图像、视频、音频输入，以及文本和语音流式输出上。其 [技术报告](https://arxiv.org/abs/2503.20215) 提出的 Thinker-Talker 架构，把文本思考和语音生成拆开，避免两种输出互相干扰。

## 五、主流架构正在收敛到几个共识

第一，多模态模型本质上仍然以 Transformer/LLM 为中心。视觉、音频、视频最终都会被编码成 token 或 embedding，再进入语言模型的上下文窗口。

第二，视觉编码器越来越“原生”。早期模型常把图像缩放到固定尺寸，现在 Qwen、DeepSeek、InternVL 等都在强调动态分辨率、动态切图、窗口注意力和高分辨率文档理解。

第三，位置编码变得非常关键。图像有二维空间，视频有时间，文档有版面结构。如果位置编码只沿用文本的一维序列，模型会丢失空间和时间关系。MRoPE、TMRoPE、V2PE 等设计，本质上都在解决这个问题。

第四，token 压缩会成为核心工程能力。多模态输入非常“耗 token”：一页 PDF、一段长视频、一张高分辨率截图，都可能产生大量视觉 token。因此 merger、resampler、dynamic tiling、window attention、MoE、latent attention 都是在控制计算成本。

第五，模型正在从 VLM 走向 Omni。下一代开源多模态模型不再满足于“看图聊天”，而是要理解图片、视频、音频、文档、屏幕，并能输出文本、语音、图像，甚至操作工具和软件界面。

## 结语

如果用一句话概括现在主流开源多模态大模型的架构，那就是：

```text
把各种模态编码成 token，用更聪明的位置编码保留空间和时间结构，再交给强大的 LLM / MoE Transformer 统一推理。
```

Qwen 代表了“动态分辨率 + 多模态位置编码 + 长上下文统一理解”的路线；DeepSeek-VL2 代表了“动态切图 + MoE + 高效推理”的路线；Janus 则展示了“理解与生成统一，但视觉编码解耦”的方向。它们共同指向一个趋势：未来的大模型不会再区分“语言模型”“视觉模型”“语音模型”，而会变成一个能在多种模态之间自由读写和推理的统一智能系统。
