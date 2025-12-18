
# 智能制度问答系统（Hybrid RAG）— 交付说明 SUBMISSION

> 交付目标：提供一个可运行的 HR 制度问答原型，支持单轮问答、多入口调用、低延迟直通 + LLM 增强，具备基础缓存、错误处理、可观测性与可部署性。

---

## 0. 现状与范围说明（重要）
本项目采用 **Hybrid RAG** 路线：
- **Direct（直通）**：当检索置信度高时，直接返回知识库预设答案（低延迟、零幻觉）
- **LLM（增强）**：当问题更口语化/需要润色时，检索 TopK 作为上下文，调用外部 LLM 综合回答（拟人、覆盖更广）
- **Fallback（兜底）**：当相关性较低，返回友好提示并建议咨询 HR

 性能指标说明：
- Direct 路径可对齐 ≤500ms 的目标（本机/单节点可测）
- LLM 路径受外部 API 延迟与网络影响，通常无法保证 ≤500ms；本项目通过 **缓存、超时、降级策略** 保证稳定性，并在文档中给出上线优化方向。

---

## 1. 系统架构与核心模块
### 1.1 模块拆解
- API 服务：FastAPI 提供 `/ask`、`/health`（如有）等接口
- 检索模块：Embedding + VectorStore 检索 TopK
- 生成模块：LLMGenerator（OpenAI-compatible HTTP / 外部 API）
- 缓存模块：Redis 缓存热点问答结果（减少重复检索/LLM 调用）
- 观测模块：日志记录（建议包含 mode/confidence/cache_hit/latency）

### 1.2 请求流程（Mermaid）
```mermaid
flowchart LR
  U[User Question] --> A[POST /ask]
  A --> C{Redis Cache hit?}
  C -- yes --> R1[Return cached result]
  C -- no --> V[Vector Retrieve TopK]
  V --> S{best_score >= DIRECT_THRESHOLD and rewrite=false?}
  S -- yes --> D[Direct Answer from KB]
  S -- no --> T{best_score >= MIN_THRESHOLD?}
  T -- yes --> L[LLM with Top docs context]
  T -- no --> F[Fallback message]
  D --> O[Response]
  L --> O
  F --> O
````

---

## 2. 数据集与索引

### 2.1 数据文件

* `faq.csv`：知识库（FAQ 标准问答）
* `queries.csv`：评测集（query -> faq_id 的映射，用于检索准确率评估）

（可选增强）如需更真实，可在 `queries.csv` 中加入更多口语化改写 query，提高评测可靠性。

---

## 3. 本地运行（开发模式）

### 3.1 启动服务

```bash
uvicorn app.main:app --reload --port 8000
```

### 3.2 Swagger / OpenAPI

<img src="/Users/eridani/Library/Application Support/typora-user-images/截屏2025-12-18 下午5.02.07.png" alt="截屏2025-12-18 下午5.02.07" style="zoom:20%;" />

---

## 4. 功能演示（建议截图/终端输出）

### 4.1 Direct 示例（高置信度直通）

```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"年假怎么申请","rewrite":false}'
```

✅ 预期：`mode="direct"`（若现在仍走 llm，可把 DIRECT_THRESHOLD 调到略低于你的 best_score，并清缓存）

<img src="/Users/eridani/Library/Application Support/typora-user-images/截屏2025-12-18 下午4.39.35.png" alt="截屏2025-12-18 下午4.39.35" style="zoom:50%;" />】

### 4.2 LLM 示例（口语化/综合回答）

```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"家里狗狗病了想请假带它看病，流程是啥","rewrite":false}'
```

✅ 预期：`mode="llm"`，答案包含引用标注（如 `[引用: 资料1]`），并返回 sources/candidates

<img src="/Users/eridani/Library/Application Support/typora-user-images/截屏2025-12-18 下午4.40.36.png" alt="截屏2025-12-18 下午4.40.36" style="zoom:50%;" />

### 4.3 Fallback 示例（知识库未覆盖）

```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"老板的私人手机号是多少","rewrite":false}'
```

✅ 预期：`mode="fallback"` + 友好提示（不编造）

<img src="/Users/eridani/Library/Application Support/typora-user-images/截屏2025-12-18 下午4.41.51.png" alt="截屏2025-12-18 下午4.41.51" style="zoom:50%;" />

---

## 5. 评估：检索准确率（Top-1 / Top-3）

### 5.1 数据清洗与切分（7:3）

运行脚本（如果你已写好并可运行）：

```bash
python scripts/prepare_dataset.py --faq <PATH_TO_FAQ_CSV> --queries <PATH_TO_QUERIES_CSV>
```

![截屏2025-12-18 下午4.45.52](/Users/eridani/Library/Application Support/typora-user-images/截屏2025-12-18 下午4.45.52.png)

### 5.2 检索评测

运行脚本：

```bash
python scripts/evaluate_retrieval.py
```

或（如果你的脚本支持参数）：

```bash
python scripts/evaluate_retrieval.py --test_csv reports/queries_test.csv --topk 3
```

<img src="/Users/eridani/Library/Application Support/typora-user-images/截屏2025-12-18 下午4.46.35.png" alt="截屏2025-12-18 下午4.46.35" style="zoom:50%;" />

* 截图：终端输出（Top-1 Accuracy、Top-3 Accuracy、Latency(avg/p95)）
* 附件文件：`reports/eval_summary.json`、`reports/badcases.csv`

---

## 6. 压测与稳定性（并发）

建议采用「温和并发」模拟内部系统场景，避免单机把外部 LLM 打爆导致误判。

运行（可选其一）：

* 冒烟测试：

```bash
python scripts/smoke_test.py
```

* 并发压测：

```bash
python scripts/benchmark_locust_mock.py
```

<img src="/Users/eridani/Library/Application Support/typora-user-images/截屏2025-12-18 下午4.49.08.png" alt="截屏2025-12-18 下午4.49.08" style="zoom:50%;" />

<img src="/Users/eridani/Movies/录屏/截屏2025-12-18 下午4.55.53.png" alt="截屏2025-12-18 下午4.55.53" style="zoom:50%;" />

---

## 7. 工程化部署（Docker Compose 一键启动）

本项目提供 `docker-compose.yml`，包含 API 与 Redis，并通过 `.env` 注入配置；Redis 配有 `healthcheck`。

### 7.1 启动

```bash
docker compose up -d --build
docker compose ps
```

<img src="/Users/eridani/Library/Application Support/typora-user-images/截屏2025-12-18 下午4.52.55.png" alt="截屏2025-12-18 下午4.52.55" style="zoom:50%;" />

---

## 8. 后续可优化方向

* 性能：embedding 模型量化/onnx、批处理、向量检索索引参数调优
* 并发：uvicorn workers、多进程部署、队列化 LLM 请求、限流熔断
* 评测：引入更真实的同义改写测试集 + badcase 迭代闭环
* 生产：Nginx 反代与多副本负载均衡、灰度发布、可观测性（Prometheus/Grafana）

