---
title: EverOS + everos-mcp + Qwen3 Embedding/Reranker：一套自托管长期记忆部署攻略
tags:
  - EverOS
  - MCP
  - Qwen
  - AI Infra
  - RAG
---

> 一句话总结：EverOS 负责把对话变成可持续演化的 Markdown 记忆，Qwen3-Embedding-8B 负责向量化，Qwen3-Reranker-8B 负责对候选结果重排，`everos-mcp` 则把这套 HTTP 记忆服务接入 Claude Code、Cursor、Cline 等 MCP 客户端。本文按新版 `/api/v2` 接口整理一套可落地的自托管部署方案。

![EverOS、Qwen 检索服务与 everos-mcp 部署拓扑](/assets/images/everos-qwen-stack/overview.svg)

<!--more-->

这篇文章记录我实际采用的一套部署思路：

```text
MCP Client
    -> everos-mcp（stdio）
        -> EverOS（HTTP /api/v2）
            -> Qwen3-Embedding-8B
            -> Qwen3-Reranker-8B
            -> 一个 OpenAI-compatible Chat LLM
```

这里有一个容易混淆的点：**Embedding 和 Reranker 不能替代 EverOS 的 Chat LLM**。前者负责检索，后者负责候选重排；EverOS 在记忆提取、主题切换和部分反思流程中仍需要一个 chat-completions 模型。

本文以 Linux + NVIDIA GPU 为例，示例地址使用：

| 服务 | 示例地址 | 作用 |
| --- | --- | --- |
| EverOS | `http://EVEROS_HOST:5004` | 记忆 API |
| Embedding | `http://EVEROS_HOST:8101/v1` | 向量生成 |
| Reranker | `http://EVEROS_HOST:8102/v1` | 候选重排 |
| everos-mcp | MCP 客户端本地进程 | 把 MCP 工具转成 EverOS 请求 |

端口只是示例。真正重要的是：EverOS 能访问两个模型服务，MCP 能访问 EverOS，模型服务不要暴露到不必要的公网。

## 一、先理解新版 EverOS 的数据流

EverOS 当前的 Quickstart 把服务端记忆流程拆得很清楚：启动 HTTP server，调用 `/api/v2/memory/add` 写入消息，必要时调用 `/api/v2/memory/flush` 触发提取，再调用 `/api/v2/memory/search` 搜索。每一批消息通过 `session_id` 表示一个会话线程。

EverOS 的一个重要设计是：Markdown 是记忆的源数据，SQLite 和 LanceDB 是从 Markdown 派生出来的索引。这样做的好处是数据可读、可 diff、可备份；代价是写入成功和索引可检索之间可能存在短暂延迟。

新版接口路径以 `/api/v2` 为准。旧的 `/api/v1` 仍可能作为兼容别名存在，但新部署和新客户端应该使用 v2。

参考：

- [EverOS QUICKSTART](https://github.com/EverMind-AI/EverOS/blob/main/QUICKSTART.md)
- [EverOS repository](https://github.com/EverMind-AI/EverOS)
- [EverOS configuration example](https://github.com/EverMind-AI/EverOS/blob/main/config.example.toml)

## 二、硬件和目录规划

### 2.1 GPU 估算

Qwen3-Embedding-8B 和 Qwen3-Reranker-8B 都是 8B 级别模型，官方模型卡显示它们的上下文长度为 32K；Embedding-8B 的默认输出维度最高可到 4096。实际显存还要加上 CUDA、框架、KV/cache、batch 和并发开销。

一个比较稳妥的规划是：

| 方案 | 建议 |
| --- | --- |
| 两张 GPU | Embedding 与 Reranker 各占一张，最简单稳定 |
| 一张大显存 GPU | 两个服务分配不同显存比例，降低并发并观察 OOM |
| 显存较小 | 先用 Qwen3-Embedding-0.6B/4B 或较小 Reranker 验证链路 |
| 只有 CPU | 可以做功能验证，但不建议把 8B 模型作为常驻生产服务 |

不要把“模型权重大小”当成全部显存需求。首次部署先用低并发、短上下文、较小 batch 做健康检查，再逐步加压。

### 2.2 推荐目录

```text
/srv/everos/
  data/              # EverOS root，Markdown、SQLite、LanceDB
  config/            # 配置与 systemd 环境文件
  logs/

/srv/models/
  Qwen3-Embedding-8B/
  Qwen3-Reranker-8B/
```

EverOS 的 root 要单独备份。模型权重可以重新下载，Markdown 记忆和配置才是不可替代的数据。

## 三、部署 EverOS

### 3.1 安装 Python 和 EverOS

当前官方 Quickstart 要求 Python 3.12+。推荐用 `uv` 管理环境：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"

uv venv --python 3.12 /srv/everos/.venv
source /srv/everos/.venv/bin/activate
uv pip install everos
```

如果要跟踪源码：

```bash
git clone https://github.com/EverMind-AI/EverOS.git /srv/src/EverOS
cd /srv/src/EverOS
uv sync
```

### 3.2 初始化 EverOS root

把数据放到显式目录，避免服务启动目录变化后读到另一份配置：

```bash
mkdir -p /srv/everos/data
everos init --root /srv/everos/data
```

初始化后重点检查 `everos.toml`。最少需要配置三类 provider：

```toml
[llm]
model = "your-chat-model"
base_url = "https://your-openai-compatible-endpoint/v1"
api_key = "your-llm-key"

[embedding]
model = "Qwen/Qwen3-Embedding-8B"
base_url = "http://EVEROS_HOST:8101/v1"
api_key = "local-embedding"

[rerank]
model = "Qwen/Qwen3-Reranker-8B"
base_url = "http://EVEROS_HOST:8102/v1"
api_key = "local-rerank"
```

配置项名称以当前 EverOS 生成的配置为准；如果你使用的版本把 provider 写成 `provider = ...`，保留生成器给出的字段，只替换模型名、`base_url` 和 key。

### 3.3 设置文件句柄和绑定地址

EverOS 会同时访问很多 LanceDB segment 文件，官方 Quickstart 建议关注文件句柄上限。启动前检查：

```bash
ulimit -n
ulimit -n 4096
```

默认服务通常监听 `127.0.0.1:8000`。如果 MCP 与 EverOS 在同一台机器，这样就够了；如果 MCP 在另一台机器，需要让 EverOS 绑定内网地址，或者用 Nginx/Caddy 把内网端口转发到本机的 8000。

生产环境更推荐反向代理或 systemd 管理，而不是把开发服务器直接暴露到公网。示例 systemd 单元：

```ini
[Unit]
Description=EverOS memory server
After=network-online.target

[Service]
Type=simple
User=everos
WorkingDirectory=/srv/everos/data
Environment=EVEROS_CONFIG_FILE=/srv/everos/data/everos.toml
ExecStart=/srv/everos/.venv/bin/everos server start --root /srv/everos/data
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

启动并验证：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now everos
curl http://127.0.0.1:8000/health
```

预期健康检查返回 `{"status":"ok"}`。如果你要对外提供 `:5004`，让反向代理监听 `5004` 并转发到 `127.0.0.1:8000`，然后让 MCP 的 `EVERMEMOS_BASE_URL` 指向 `http://EVEROS_HOST:5004`。

## 四、部署 Qwen3-Embedding-8B

### 4.1 用 vLLM 提供 embedding API

Qwen 官方模型卡给出了 vLLM 的 embedding 用法，要求以 `task="embed"` 运行。在线服务可以按下面的方式启动：

```bash
uv pip install -U vllm

CUDA_VISIBLE_DEVICES=0 vllm serve Qwen/Qwen3-Embedding-8B \
  --task embed \
  --host 0.0.0.0 \
  --port 8101 \
  --served-model-name Qwen/Qwen3-Embedding-8B \
  --api-key local-embedding \
  --dtype bfloat16
```

如果显卡不适合 bfloat16，可以根据硬件改成 `--dtype float16`。首次运行会从 Hugging Face 下载权重；内网环境可以在有网机器预下载后，把模型目录挂载到服务机：

```bash
hf download Qwen/Qwen3-Embedding-8B \
  --local-dir /srv/models/Qwen3-Embedding-8B
```

然后把模型名替换成目录：

```bash
vllm serve /srv/models/Qwen3-Embedding-8B \
  --task embed \
  --host 0.0.0.0 \
  --port 8101 \
  --served-model-name Qwen/Qwen3-Embedding-8B \
  --api-key local-embedding
```

验证 OpenAI-compatible embeddings 接口：

```bash
curl http://127.0.0.1:8101/v1/embeddings \
  -H 'Authorization: Bearer local-embedding' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3-Embedding-8B",
    "input": ["EverOS stores long-term memory as Markdown."]
  }'
```

返回中应包含 `data[0].embedding`。一定要记录向量维度；切换模型或维度后，旧的 LanceDB 向量索引通常需要重建。

### 4.2 Query instruction 要保持一致

Qwen3-Embedding 支持 instruction-aware 检索。官方建议给 query 加一条任务说明，而文档侧不加同样的 instruction，例如：

```text
Instruct: Given a memory search query, retrieve memories that answer it
Query: 用户喜欢什么样的 graph memory？
```

是否使用 instruction、instruction 使用英文还是中文，应该在一开始固定下来，并在写入、查询、评测中保持一致。不要线上写入用一种模板、离线重建又换另一种模板，否则召回质量会发生难以解释的变化。

## 五、部署 Qwen3-Reranker-8B

Reranker 和 embedding 不一样：它接收 `(query, document)` 对，输出相关性分数。Qwen3-Reranker-8B 的官方模型卡使用 `yes/no` 二分类逻辑来得到相关性分数，默认任务 instruction 是：

```text
Given a web search query, retrieve relevant passages that answer the query
```

### 5.1 先确认 serving 框架版本

Qwen3-Reranker-8B 的在线部署对 serving 框架版本比较敏感。新版 vLLM 支持 pooling/score runner，但不同版本对模型架构转换、`hf_overrides` 和 `/v1/rerank` 的支持程度不同。可以先查看：

```bash
vllm --version
vllm serve --help | rg 'runner|task|rerank|score|pooling'
```

在支持 score/pooling 的 vLLM 版本中，启动命令通常类似：

```bash
CUDA_VISIBLE_DEVICES=1 vllm serve Qwen/Qwen3-Reranker-8B \
  --host 0.0.0.0 \
  --port 8102 \
  --runner pooling \
  --served-model-name Qwen/Qwen3-Reranker-8B \
  --api-key local-rerank \
  --hf-overrides '{"architectures":["Qwen3ForSequenceClassification"],"classifier_from_token":["no","yes"],"is_original_qwen3_reranker":true}'
```

如果你的 vLLM 版本不识别这些参数，不要硬套命令。可以升级 vLLM，或者使用 Transformers/Sentence Transformers 包一层内部 HTTP 服务。Qwen 官方模型卡已经提供了 `CrossEncoder("Qwen/Qwen3-Reranker-8B")` 的调用方式，关键是服务层要把请求转换成：

```json
{
  "model": "Qwen/Qwen3-Reranker-8B",
  "query": "用户喜欢什么样的 graph memory？",
  "documents": [
    "用户明确表示喜欢 EverOS 的 graph memory。",
    "用户正在配置一台 NAS。"
  ],
  "top_n": 2
}
```

返回至少要能表达：原文档索引、相关性分数和排序结果。EverOS 的 `[rerank]` 配置必须与这个服务实际暴露的协议一致；不要只改 `model` 名称就假定任意 `/v1/chat/completions` 服务可以充当 reranker。

### 5.2 rerank 健康检查

如果服务暴露标准 `/v1/rerank`，可以这样检查：

```bash
curl http://127.0.0.1:8102/v1/rerank \
  -H 'Authorization: Bearer local-rerank' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3-Reranker-8B",
    "query": "What does the user like?",
    "documents": [
      "The user likes graph memory.",
      "The user is configuring a database."
    ],
    "top_n": 2
  }'
```

重点观察两件事：相关文档的分数是否更高，以及返回 schema 是否正好符合 EverOS 当前版本的 rerank client。协议不一致时，EverOS 可能表现为“搜索有结果但重排失败”，而不是在启动阶段直接报错。

## 六、把本地模型写入 EverOS 配置

完成两个模型服务后，把 `everos.toml` 的 provider 指向内网地址：

```toml
[llm]
model = "your-chat-model"
base_url = "http://127.0.0.1:8001/v1"
api_key = "local-llm"

[embedding]
model = "Qwen/Qwen3-Embedding-8B"
base_url = "http://EVEROS_HOST:8101/v1"
api_key = "local-embedding"

[rerank]
model = "Qwen/Qwen3-Reranker-8B"
base_url = "http://EVEROS_HOST:8102/v1"
api_key = "local-rerank"
```

如果 EverOS 的当前版本把 rerank 服务配置成专用 `inference` URL，就按它生成的配置格式填写，例如：

```toml
[rerank]
provider = "local"
model = "Qwen/Qwen3-Reranker-8B"
base_url = "http://EVEROS_HOST:8102/v1/inference"
api_key = "local-rerank"
```

这里的原则比字段名更重要：

1. `[embedding]` 必须返回向量。
2. `[rerank]` 必须返回候选排序分数。
3. `[llm]` 必须能完成 chat completion。
4. 三个 endpoint 的网络连通性、鉴权方式和超时都要单独验证。

修改后重启 EverOS：

```bash
sudo systemctl restart everos
curl http://EVEROS_HOST:5004/health
```

## 七、部署 everos-mcp

`everos-mcp` 是 MCP stdio server，不需要额外开放一个 HTTP 端口。MCP 客户端启动它，它再通过 HTTP 调 EverOS。

源码安装：

```bash
git clone https://github.com/transcendentsky/everos-mcp.git
cd everos-mcp
uv sync
```

以 Claude Code/Cursor 一类客户端为例，配置：

```json
{
  "mcpServers": {
    "evermemos-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/everos-mcp",
        "evermemos-mcp"
      ],
      "env": {
        "EVERMEMOS_BASE_URL": "EVEROS_HOST",
        "EVERMEMOS_PORT": "5004",
        "EVERMEMOS_API_VERSION": "v2",
        "EVERMEMOS_USER_ID": "mcp-user"
      }
    }
  }
}
```

如果直接使用已发布包：

```json
{
  "mcpServers": {
    "evermemos-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["evermemos-mcp@latest"],
      "env": {
        "EVERMEMOS_BASE_URL": "EVEROS_HOST",
        "EVERMEMOS_PORT": "5004",
        "EVERMEMOS_API_VERSION": "v2"
      }
    }
  }
}
```

### 7.1 MCP 到 EverOS 的映射

| MCP 工具 | EverOS v2 请求 | 说明 |
| --- | --- | --- |
| `remember` | `/api/v2/memory/add` | `space_id` 转成 `session_id` |
| `remember(flush=true)` | `/api/v2/memory/flush` | 触发当前 session 提取 |
| `recall` | `/api/v2/memory/search` | MCP 的检索方式映射成 EverOS method |
| `fetch_history` | `/api/v2/memory/get` | 读取 `episode`/`profile` |
| `briefing` | 多次 `/api/v2/memory/get` | 组合启动上下文 |
| `request_status` | MCP 本地同步状态 | v2 没有旧 Cloud task endpoint |

MCP 空间推荐这样命名：

```text
coding:everos
coding:my-project
chat:preferences
study:retrieval
```

例如保存一条记忆：

```text
remember(
  space_id="coding:everos",
  content="everos 我很喜欢他的 graph memory",
  flush=true
)
```

## 八、端到端验证

### 8.1 先不经过 MCP，直接测 EverOS

```bash
TS=$(($(date +%s)*1000))

curl -X POST http://EVEROS_HOST:5004/api/v2/memory/add \
  -H 'Content-Type: application/json' \
  -d "{
    \"session_id\": \"demo-everos\",
    \"messages\": [
      {\"sender_id\": \"mcp-user\", \"role\": \"user\", \"timestamp\": $TS, \"content\": \"我很喜欢 EverOS 的 graph memory。\"}
    ]
  }"

curl -X POST http://EVEROS_HOST:5004/api/v2/memory/flush \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-everos"}'

curl -X POST http://EVEROS_HOST:5004/api/v2/memory/search \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "mcp-user",
    "query": "用户喜欢 EverOS 的什么？",
    "top_k": 5,
    "method": "hybrid",
    "filters": {"session_id": {"in": ["demo-everos"]}}
  }'
```

第一次搜索为空不一定是写入失败。先检查 Markdown 是否生成，再等待索引追上并重试。

### 8.2 再通过 MCP 验证

在客户端调用：

```text
remember(space_id="coding:everos", content="EverOS 的 graph memory 很有意思", flush=true)
recall(space_id="coding:everos", query="我对 EverOS graph memory 的看法")
fetch_history(space_id="coding:everos", memory_type="episodic_memory")
```

如果 `remember` 成功、`recall` 返回 `EXTERNAL_SERVICE_UNAVAILABLE`，优先检查 EverOS 的 `[llm]`、`[embedding]` 和 `[rerank]` provider，而不是先改 MCP 路径。

## 九、常见故障定位

| 现象 | 优先检查 |
| --- | --- |
| MCP 连接不上 EverOS | `EVERMEMOS_BASE_URL`、端口、防火墙、`/health` |
| `/api/v1` 能通，`/api/v2` 不通 | EverOS 版本过旧，升级或确认 v2 路径 |
| add 成功但 search 为空 | flush 是否执行、Markdown 是否生成、索引是否完成 |
| 搜索报余额/计费资源不足 | EverOS 的 chat/embedding/rerank provider 仍指向有余额限制的远端服务 |
| embedding 返回维度错误 | 更换模型后重建 LanceDB 索引，并统一 output dimension |
| rerank 400/422 | vLLM runner、`hf_overrides`、chat template 或响应协议不匹配 |
| `fetch_history` 有记录但 recall 没有 | search provider、instruction、top-k 或 hybrid 配置问题 |
| Qwen 8B 启动 OOM | 降低 batch/context/concurrency，分卡，或先用 0.6B/4B |
| systemd 启动后读不到配置 | `--root`、`WorkingDirectory`、`EVEROS_CONFIG_FILE` 不一致 |

有一个非常实用的排错顺序：

```text
/health
  -> embedding API
  -> rerank API
  -> EverOS add
  -> EverOS flush
  -> EverOS search
  -> MCP remember
  -> MCP recall
```

不要一上来就从 MCP 客户端排查。MCP 只是最上层的一层适配，先把下游每个 HTTP 接口单独打通，定位会快很多。

## 十、备份、升级与安全

### 10.1 备份

至少备份：

```text
/srv/everos/data/*.toml
/srv/everos/data/**/*.md
```

`.index/` 通常是派生索引，可以重建；Markdown、配置和用户空间映射要纳入备份。备份前先停止写入或采用一致性快照。

### 10.2 升级

升级顺序建议是：

1. 复制 EverOS root 做快照。
2. 固定当前 Python、EverOS、vLLM 和模型版本。
3. 在 staging root 做 add/flush/search 回归。
4. 再切换生产 systemd 服务。
5. 发现 schema 或索引不兼容时回滚，而不是现场删除数据。

### 10.3 安全

- EverOS、embedding、rerank 端口只绑定内网或 loopback。
- API key 放在环境文件或 secret manager，不要写进 Git。
- 反向代理启用 TLS、鉴权和访问日志。
- `everos-mcp` 只给 MCP 客户端暴露 stdio，不需要额外开放端口。
- 对 `memory/add`、`memory/search` 做限流，避免大批量文本拖垮 embedding/rerank GPU。

## 结语

这套系统真正的价值，不是单独部署了三个模型，而是把记忆链路拆成了可替换的服务：

```text
EverOS：记忆生命周期、Markdown、索引与检索编排
Embedding：把 query/document 放进向量空间
Reranker：在候选集内做更精细的相关性判断
Chat LLM：做记忆提取、总结和反思
everos-mcp：把 HTTP memory API 接到日常 AI 编程工具
```

先用小数据和低并发打通完整链路，再谈 8B 模型的吞吐、量化和多卡。能稳定完成“写入一条记忆，再把它检索回来”，比一开始堆满所有优化参数更重要。

## 参考资料

- [EverOS QUICKSTART](https://github.com/EverMind-AI/EverOS/blob/main/QUICKSTART.md)
- [EverOS 配置示例](https://github.com/EverMind-AI/EverOS/blob/main/config.example.toml)
- [EverOS GitHub](https://github.com/EverMind-AI/EverOS)
- [everos-mcp](https://github.com/transcendentsky/everos-mcp)
- [Qwen3-Embedding-8B 模型卡](https://huggingface.co/Qwen/Qwen3-Embedding-8B)
- [Qwen3-Reranker-8B 模型卡](https://huggingface.co/Qwen/Qwen3-Reranker-8B)
- [Qwen3 Embedding 论文](https://arxiv.org/abs/2506.05176)
- [Qwen 官方 vLLM 部署文档](https://github.com/QwenLM/Qwen3/blob/main/docs/source/deployment/vllm.md)
- [vLLM OpenAI-compatible server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)
