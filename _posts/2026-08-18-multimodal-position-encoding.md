---
title: 多模态大模型位置编码：从 1D RoPE 到 3D M-RoPE
tags:
  - Multimodal
  - Position Encoding
  - RoPE
  - MLLM
---

> 多模态大模型的位置编码，是一个看起来底层、实际非常影响能力上限的问题。文本是 1D 序列，图像是 2D 网格，视频是 3D 时空体，而 Transformer 最终看到的都是 token 序列。位置编码要解决的，就是把这些几何结构重新塞回注意力计算里，让模型知道“谁在谁旁边、谁在哪一帧、谁属于哪张图、谁和文本里的指代对应”。

![Multimodal position encoding landscape](/assets/images/multimodal-position-encoding/position-landscape.svg)

<!--more-->

## 一、为什么多模态更需要位置编码

Transformer 的自注意力本身对输入顺序不敏感。如果不给位置，下面两个序列在注意力层里没有天然差异：

```text
猫 在 桌子 上
桌子 在 猫 上
```

文本模型用位置编码解决顺序问题。但多模态大模型更复杂，因为它同时面对三种结构。

| 模态 | 原始结构 | token 化后 | 位置编码需要保留什么 |
| --- | --- | --- | --- |
| 文本 | 1D 序列 | word / subword tokens | 前后顺序、距离、长上下文外推 |
| 图像 | 2D 平面 | patch tokens | 行、列、局部邻接、空间比例 |
| 视频 | 3D 时空体 | frame patch tokens | 时间、行、列、运动连续性 |
| 多图输入 | 多个 2D 平面 | 多段 image tokens | 图像边界、图像编号、跨图关系 |
| 文档/图表 | 2D 布局 + 文本 | OCR/patch 混合 tokens | 版面、表格、坐标、阅读顺序 |

如果位置编码设计不好，多模态模型会出现很实际的问题：

1. 图像 patch 展平后，模型分不清“同行相邻”和“换行相邻”。
2. 高分辨率图像被切块后，不同块之间的全局位置丢失。
3. 多图输入时，模型混淆不同图片里的对象。
4. 视频中，模型理解静态画面可以，但时间顺序和动作关系弱。
5. 文档问答中，模型能识别文字，却难以利用表格行列和版面结构。

所以位置编码不是小细节，而是视觉理解、视频理解、文档理解、屏幕操作和多图推理的基础设施。

## 二、从文本位置编码开始

多模态位置编码基本都是从文本位置编码演化来的。

### 1. 绝对位置编码

早期 Transformer 使用 sinusoidal positional encoding：

```text
x_i = token_embedding_i + position_embedding_i
```

这种方式简单直观。位置向量直接加到 token 表示上，让模型知道第 `i` 个 token 在哪里。

后来很多模型使用 learned absolute position embedding，也就是每个位置学习一个向量。

| 方案 | 优点 | 问题 |
| --- | --- | --- |
| Sinusoidal | 不需要学习，能一定程度外推 | 设计固定，不一定最优 |
| Learned absolute | 简单，训练内效果好 | 超出训练长度时泛化弱 |
| ViT learned 2D/1D | 适合固定分辨率图像 | 分辨率变化时通常要插值 |

对多模态来说，绝对位置编码最大的麻烦是：视觉 token 数量经常变化。图像分辨率、长宽比、patch size、裁剪策略都会改变 token 网格大小。

### 2. 相对位置编码

相对位置编码不直接告诉模型“我在第 37 个位置”，而是告诉注意力：

```text
query_i 看 key_j 时，两者距离是多少
```

相对位置适合表示局部关系，尤其适合图像这种“邻近 patch 更相关”的结构。

### 3. RoPE：把位置写进 q/k 的旋转

RoPE，全称 Rotary Position Embedding，由 RoFormer 提出。它不是把位置向量加到 token embedding 上，而是在注意力的 query/key 上做旋转变换。

直观理解：

```text
q_i = rotate(q, position=i)
k_j = rotate(k, position=j)
q_i · k_j 中自然包含 i-j 的相对位置信息
```

RoPE 的优点是：

| 优点 | 说明 |
| --- | --- |
| 相对位置自然进入注意力 | q/k 点积中包含相对距离 |
| 适合 decoder-only LLM | LLaMA、Qwen 等大量模型使用 |
| 和长上下文扩展兼容 | 可结合 NTK scaling、YaRN、LongRoPE 等方法 |
| 容易推广到 2D/3D | 把不同轴的位置分别旋转 |

这也是为什么多模态模型常常从 RoPE 往 2D RoPE、M-RoPE 扩展。

### 4. ALiBi：把距离变成注意力 bias

ALiBi 不是 embedding，而是在 attention logits 上加一个和距离相关的线性 bias：

```text
attention_score(i, j) = q_i · k_j + bias(i, j)
```

它的优点是长上下文外推能力好、实现简单；但在当前主流多模态大模型里，视觉 2D/3D 位置建模更多还是围绕 RoPE、2D position embedding、factorized position embedding 展开。

## 三、图像位置编码：从 ViT 到任意分辨率

图像进入 Transformer 前通常会切成 patch。

```text
image: H x W x C
patch size: P x P
tokens: (H/P) x (W/P)
```

例如 224 x 224 图像，patch size 为 14，则得到 16 x 16 = 256 个视觉 token。

### 1. ViT 的固定网格问题

Vision Transformer 最初面向固定分辨率图像。每个 patch 有固定位置，训练和推理时通常使用同样的网格大小。

问题是，多模态大模型面对的图像不是固定的：

| 场景 | 挑战 |
| --- | --- |
| 手机截图 | 超长竖图，UI 元素密集 |
| 文档页面 | 高分辨率，文字很小 |
| 图表 | 坐标轴、图例、表格位置敏感 |
| 多图输入 | 每张图尺寸和比例都不同 |
| OCR/视觉混合 | 既要看文字，又要看空间布局 |

如果简单 resize 到固定分辨率，小字和细节会丢；如果保留高分辨率，视觉 token 数量会暴涨，位置编码也要支持动态网格。

### 2. 2D 绝对位置编码

最直接的方法是给每个 patch 一个二维位置：

```text
pos(h, w) = embedding_h[h] + embedding_w[w]
```

这叫 factorized 2D position embedding。它比把图像展平成 1D 更合理，因为行和列被分开建模。

| 方案 | 特点 |
| --- | --- |
| 1D learned position | 把所有 patch 展平成序列，简单但弱化二维结构 |
| 2D learned position | 直接建模 `(h, w)`，更贴近图像 |
| factorized 2D position | 分别学习 `h` 和 `w`，参数少，泛化更好 |
| fractional position | 用相对坐标 `h/H`、`w/W`，更适合任意分辨率 |

NaViT 的一个重要思想就是用 factorized / fractional positional embeddings 支持原生分辨率和任意长宽比，而不是所有图片都强行 resize 成同样大小。

### 3. 2D RoPE

2D RoPE 可以理解为把 RoPE 分别作用在高度和宽度两个轴上。

一种常见做法是把 head dimension 分成两部分：

```text
q = concat(q_h, q_w)
k = concat(k_h, k_w)

q_h/k_h 使用 h 位置旋转
q_w/k_w 使用 w 位置旋转
```

这样注意力点积里同时包含：

```text
height relative position: h_i - h_j
width relative position: w_i - w_j
```

Pixtral 这类模型就把 2D RoPE 作为支持任意图像尺寸的重要设计之一。

## 四、多模态序列：图像 token 到底放在哪里

多模态大模型通常有两种主流架构。

| 架构 | 典型形式 | 位置编码问题 |
| --- | --- | --- |
| Vision encoder + LLM | CLIP/SigLIP/ViT 编码图像，再接入 LLM | 视觉 encoder 和 LLM 的位置系统可能不同 |
| Unified decoder / early fusion | 文本、图像、视频 token 混进同一个 Transformer | 需要统一位置编码 |

很多 LLaVA 类模型采用第一种方式：

```text
image -> vision encoder -> projector -> LLM tokens
```

这时视觉 encoder 内部可能已经有自己的 2D position embedding。进入 LLM 后，视觉 token 又被当成一段“特殊文本 token”插入文本序列。

这带来一个问题：

```text
视觉 token 在图像里的二维位置
LLM 序列里的线性位置
二者不是同一件事
```

如果只依赖 LLM 的 1D 位置，模型知道 image token 在整个 prompt 的第几个位置，但未必清楚它在图像的哪一行哪一列。

因此，现代多模态模型通常需要显式保留视觉位置结构。

## 五、M-RoPE：文本、图像、视频的统一位置编码

Qwen2-VL 提出的 Multimodal Rotary Position Embedding，也就是 M-RoPE，是一个很好的代表。

它的核心思想是：

```text
把位置拆成三条轴：time, height, width
```

对于不同模态：

| 模态 | 位置 ID |
| --- | --- |
| 文本 | `(p, p, p)`，三个轴使用同一个 1D 位置 |
| 图像 | `(t0, h, w)`，时间固定，高度和宽度变化 |
| 视频 | `(t, h, w)`，时间、高度、宽度都变化 |

![M-RoPE and multimodal token flow](/assets/images/multimodal-position-encoding/mrope-flow.svg)

实现上，可以把 q/k 的通道维度分成三段：

```text
q = concat(q_t, q_h, q_w)
k = concat(k_t, k_h, k_w)

q_t/k_t 用 time 位置旋转
q_h/k_h 用 height 位置旋转
q_w/k_w 用 width 位置旋转
```

这样，同一个模型可以同时处理：

1. 纯文本：退化成 1D RoPE。
2. 单图：使用 2D 空间位置。
3. 视频：使用 3D 时空位置。
4. 图文混合：文本和视觉 token 使用同一套位置机制。

Qwen2-VL 官方博客明确提到，M-RoPE 通过把原始 rotary embedding 分解成时间、高度、宽度三部分，使 LLM 能同时捕获 1D 文本、2D 视觉和 3D 视频位置信息。

## 六、动态分辨率和 AnyRes：位置编码必须跟 token 策略一起看

位置编码不能单独看。图像怎么切、切多少 token、是否压缩、是否合并 patch，都会影响位置编码。

### 1. 动态分辨率

Qwen2-VL 支持 Naive Dynamic Resolution，也就是把任意分辨率图像映射成动态数量的视觉 token。

这比固定 resize 更接近人类视觉：

| 固定分辨率 | 动态分辨率 |
| --- | --- |
| 所有图像压到同一大小 | 根据图像尺寸产生不同 token 数 |
| 简单，吞吐稳定 | 更保留细节 |
| 小字和长图容易损失 | 对文档、截图、图表更友好 |
| 位置编码压力较小 | 位置编码必须支持变化网格 |

动态分辨率意味着位置编码必须能适配不同 `H x W` patch grid，不能只记住训练时固定位置。

### 2. AnyRes / Higher-AnyRes

LLaVA-NeXT 系列强调 AnyRes 和 Higher-AnyRes。核心思路是把高分辨率图像切成多个 grid 或 tile，再分别编码。

这样做能保留更多细节，但带来新的位置问题：

| 问题 | 说明 |
| --- | --- |
| tile 内位置 | patch 在当前 tile 中的位置 |
| tile 全局位置 | tile 在原图中的位置 |
| tile 顺序 | 多个 tile 展平后如何排序 |
| 细节和全局 | 高分辨率细节和低分辨率全局图如何融合 |
| token budget | token 越多，计算越贵 |

如果只有 tile 内部位置，而没有全局 tile 位置，模型可能看清局部细节，却不知道它在整张图的哪个区域。

## 七、多图输入和 interleaved 输入

多图输入会把问题再复杂一层。

```text
<image1> 这张图里的人在做什么？
<image2> 和第一张相比有什么变化？
```

此时位置编码需要表达三件事：

| 结构 | 作用 |
| --- | --- |
| image id | 区分第几张图 |
| 2D patch position | 图内空间位置 |
| text sequence position | 文本指代和图像出现顺序 |

LLaVA-NeXT 在 interleaved multi-image/video/3D 输入中讨论过两种格式：一种是把所有 image tokens 放在前面，再用 special token 在文本里引用；另一种是图像和文本按自然顺序交错。

两种方式的取舍：

| 方式 | 优点 | 问题 |
| --- | --- | --- |
| image tokens in front | 兼容单图模型，工程简单 | 文本里的指代和图像距离变远 |
| interleaved | 更接近真实对话和文档顺序 | 训练和位置管理更复杂 |

这说明多模态位置编码不只是数学公式，也是 prompt format、训练数据格式和模型架构共同决定的问题。

## 八、视频位置编码：时间轴不是“多几张图”

视频不能简单理解为多张图片。它多了一条时间轴。

位置编码至少要考虑：

| 维度 | 说明 |
| --- | --- |
| frame index | 第几帧 |
| temporal distance | 两个事件间隔多久 |
| spatial position | 每帧中的二维位置 |
| sampling rate | 每秒采样几帧 |
| clip boundary | 不同片段之间是否连续 |

如果把视频 frame patch 全部展平成一个长序列，用普通 1D RoPE，模型能知道 token 的线性顺序，但不容易区分：

```text
相邻 patch 是同一帧中空间相邻
还是下一帧中时间相邻
```

3D 位置编码或 M-RoPE 的价值就在这里：让时间、行、列三种关系分开进入注意力。

## 九、工程实现里常见的坑

### 1. 图像 resize 后位置不一致

训练时如果模型主要见固定尺寸图像，推理时突然给高分辨率长图，位置编码插值可能不稳定。

解决思路：

| 方法 | 说明 |
| --- | --- |
| 训练时引入多分辨率 | 让模型习惯不同网格 |
| 使用 factorized/fractional position | 减少对固定坐标组合的依赖 |
| 使用 2D RoPE/M-RoPE | 用相对关系增强泛化 |
| 限制最大 token 数 | 避免超出训练分布太远 |

### 2. patch merge 后坐标要同步更新

很多视觉 encoder 会做 patch merge 或 spatial merge，例如把 2x2 patch 合成一个视觉 token。

此时位置坐标不能还按原始 patch 处理，否则会出现语义错位。

正确做法是明确：

```text
合并前 grid size
合并后 grid size
每个新 token 对应原图哪个区域
```

### 3. 多图分隔符很重要

如果多个图像 token 连在一起，没有 image boundary token 或 image id，模型容易把不同图片混在一起。

Pixtral 文档里提到，处理器会把 `[IMG]` 替换成与图像高宽相关数量的图像 token，并用 `[IMG_BREAK]` 分隔行、用 `[IMG_END]` 分隔图像。这类 separator 本质上也是结构编码的一部分。

### 4. RoPE scaling 不能只看文本长度

多模态上下文长度往往主要被视觉 token 吃掉。

例如：

```text
文本：2k tokens
图片：4 张，每张 1k image tokens
总长度：6k tokens
```

如果只按文本长上下文调 RoPE scaling，视觉 token 的位置分布可能已经和训练时差很多。

### 5. 高分辨率图像的 token budget 是硬约束

位置编码可以支持任意分辨率，不代表模型应该吃任意多 token。

| token 数增加 | 后果 |
| --- | --- |
| 注意力计算上升 | prefill 更慢 |
| KV cache 增大 | 并发能力下降 |
| 图像细节更多 | 可能提升 OCR、文档、图表能力 |
| 噪声更多 | 也可能让模型注意力分散 |

所以位置编码、token pruning、patch merge、动态分辨率策略要一起设计。

## 十、主流方案对比

| 方案 | 适用场景 | 优点 | 局限 |
| --- | --- | --- | --- |
| 1D absolute position | 固定文本、早期 ViT | 简单 | 外推弱，图像二维结构弱 |
| 2D absolute position | 固定或少量图像分辨率 | 保留行列结构 | 分辨率变化要插值 |
| Factorized 2D position | 任意长宽比图像 | 参数少，泛化更好 | 仍需要训练覆盖合理坐标范围 |
| Fractional position | 原生分辨率、多比例 | 更适合外推 | 绝对尺度信息可能弱化 |
| 1D RoPE | LLM 文本 | 相对位置自然，适合 decoder | 图像直接展平会损失二维结构 |
| 2D RoPE | 图像 token | 保留二维相对关系 | 与文本统一还要额外设计 |
| M-RoPE | 图文视频统一模型 | 支持 1D/2D/3D 统一建模 | 实现复杂，位置 ID 管理要求高 |
| ALiBi | 长文本外推 | 简单，外推好 | 在多模态 2D/3D 场景不是主流核心方案 |
| Separator / boundary token | 多图、文档、interleaved | 显式表达结构边界 | 不能替代坐标编码 |

## 十一、面试或读论文时应该抓哪些点

如果你在读多模态大模型论文，看到位置编码部分，可以直接问这些问题：

| 问题 | 为什么重要 |
| --- | --- |
| 视觉 token 是固定数量还是动态数量？ | 决定是否需要任意分辨率位置编码 |
| 图像位置是 1D、2D 还是 M-RoPE？ | 决定空间关系建模能力 |
| 视频有没有独立时间轴？ | 决定是否真的建模运动和时序 |
| 多图如何区分 image id？ | 决定跨图推理是否稳定 |
| 高分辨率图像如何切 tile？ | 决定全局/局部信息是否丢失 |
| patch merge 后位置如何更新？ | 防止坐标和 token 语义错位 |
| RoPE scaling 怎么处理视觉 token？ | 决定长上下文和多图输入稳定性 |
| 训练数据是否覆盖多分辨率？ | 位置编码外推不能只靠公式 |

这些问题比只问“用了 RoPE 还是 learned embedding”更有价值。

## 十二、我对未来方向的判断

多模态位置编码接下来会继续往几个方向发展。

### 1. 更统一的时空位置编码

图像、视频、屏幕操作、机器人视觉，本质上都需要空间和时间。M-RoPE 这类 3D 位置编码会越来越常见。

### 2. 位置编码和动态 token 策略绑定

未来模型不会无限吃高分辨率 token，而是动态选择关键区域：

```text
低分辨率全局图
+ 高分辨率局部 crop
+ OCR / layout tokens
+ task-aware visual token selection
```

位置编码必须能表达这些 token 和原图之间的映射关系。

### 3. 文档和 GUI 会推动 layout-aware encoding

文档、表格、网页、手机屏幕不是普通自然图像。它们更依赖版面结构。未来会更多结合：

1. patch position
2. OCR bounding box
3. DOM/layout tree
4. reading order
5. interactive element id

### 4. 多模态长上下文会逼迫位置编码和 KV cache 一起优化

视觉 token 太多时，位置编码不是唯一问题。prefill、KV cache、attention sparsity、token dropping、cache compression 都会一起出现。

## 十三、总结

多模态大模型的位置编码，可以用一句话概括：

**它负责把文本的一维顺序、图像的二维空间、视频的三维时空，以及多图/文档/GUI 的结构边界，统一映射到 Transformer 能理解的注意力几何里。**

几个核心结论：

1. 纯 1D 位置编码适合文本，但不足以表达图像和视频的几何结构。
2. 图像需要 2D 位置，视频需要 3D 时空位置。
3. 动态分辨率和 AnyRes 会让位置编码从“固定表查表”变成“可泛化坐标函数”。
4. M-RoPE 的价值在于把文本、图像、视频统一到 time/height/width 三轴位置系统里。
5. 多图、文档和 GUI 场景还需要 separator、image id、layout 和 OCR 坐标等结构信息。
6. 位置编码必须和 token budget、patch merge、RoPE scaling、KV cache 和训练数据分布一起看。

真正强的多模态大模型，不只是看得见图像内容，还要知道内容在哪里、相互关系是什么、随时间如何变化，以及这些视觉结构如何和文本指令对齐。位置编码就是这件事的底层语法。

## 参考资料

- RoFormer: Enhanced Transformer with Rotary Position Embedding：https://arxiv.org/abs/2104.09864
- An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale：https://arxiv.org/abs/2010.11929
- NaViT: Patch n' Pack: NaViT, a Vision Transformer for any Aspect Ratio and Resolution：https://arxiv.org/abs/2307.06304
- Qwen2-VL 官方博客：https://qwenlm.github.io/blog/qwen2-vl/
- LLaVA-NeXT Higher-AnyRes 技术说明：https://llava-vl.github.io/blog/2024-05-25-llava-next-ablations/
- LLaVA-NeXT Interleave 技术说明：https://llava-vl.github.io/blog/2024-06-16-llava-next-interleave/
- Pixtral Transformers 文档：https://huggingface.co/docs/transformers/v4.47.0/model_doc/pixtral
- ALiBi: Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation：https://arxiv.org/abs/2108.12409
