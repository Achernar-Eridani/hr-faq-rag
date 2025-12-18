import time
import concurrent.futures
import requests
import statistics
import random
import json

URL = "http://127.0.0.1:8000/ask"
CONCURRENT_USERS = 10
TOTAL_REQUESTS = 50

DIRECT_QUERIES = [
    ("年假怎么申请", False),
    ("忘记打卡怎么办", False),
    ("报销流程是什么", False),
    ("VPN连不上", False),
    ("电脑密码忘了", False),
]
LLM_QUERIES = [
    ("带狗看病怎么弄", False),
    ("加班费怎么算", True),  # 强制 llm
]

def pick_query():
    if random.random() < 0.85:
        return random.choice(DIRECT_QUERIES)
    return random.choice(LLM_QUERIES)

MAX_ERROR_SAMPLES = 5
_error_samples = 0

session = requests.Session()

def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return None

def send_request(i, timeout_s=60):
    global _error_samples

    # 模拟用户思考时间，避免瞬时洪峰
    time.sleep(random.uniform(0.05, 0.25))

    q, rewrite = pick_query()
    payload = {"question": q, "rewrite": rewrite}

    t0 = time.time()
    try:
        resp = session.post(URL, json=payload, timeout=timeout_s)
        latency = (time.time() - t0) * 1000

        data = safe_json(resp)
        mode = data.get("mode", "unknown") if data else "non_json"

        if resp.status_code != 200:
            if _error_samples < MAX_ERROR_SAMPLES:
                print(f"\n[HTTP_ERROR] status={resp.status_code} body={resp.text[:200]}")
                _error_samples += 1

        return {
            "status": resp.status_code,
            "latency": latency,
            "mode": mode,
        }

    except Exception as e:
        if _error_samples < MAX_ERROR_SAMPLES:
            print(f"\n[EXCEPTION] {repr(e)}")
            _error_samples += 1
        return {"status": "error", "latency": 0, "mode": "error"}

def warmup():
    # 让模型加载、向量库/缓存热起来
    for q, rewrite in (DIRECT_QUERIES + LLM_QUERIES):
        try:
            session.post(URL, json={"question": q, "rewrite": rewrite}, timeout=60)
        except Exception:
            pass

def run_benchmark():
    print(f"开始优化版并发测试: {CONCURRENT_USERS} 并发 | 总请求 {TOTAL_REQUESTS}")
    print("Warmup...")
    warmup()
    print("正在模拟真实用户行为...")
    print("-" * 60)

    results = []
    start_global = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        futures = [executor.submit(send_request, i) for i in range(TOTAL_REQUESTS)]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            print(".", end="", flush=True)
            results.append(res)

    total_time = time.time() - start_global
    print("\n" + "-" * 60)

    success = [r for r in results if r["status"] == 200]
    error_count = len(results) - len(success)

    direct_latencies = [r["latency"] for r in success if r["mode"] == "direct"]
    llm_latencies = [r["latency"] for r in success if r["mode"] == "llm"]

    print("测试报告 Summary:")
    print(f"并发用户: {CONCURRENT_USERS} | 总请求: {len(results)}")
    print(f"错误率:   {error_count/len(results):.2%} (目标 <= 1%)")
    print(f"RPS:      {len(success)/total_time:.2f}")

    if direct_latencies:
        avg_d = statistics.mean(direct_latencies)
        # 简单稳妥的 p95（避免 quantiles 小样本不稳定）
        p95_d = sorted(direct_latencies)[max(0, int(len(direct_latencies)*0.95)-1)]
        print("直通模式 (Direct Mode) - 核心指标:")
        print(f"  Avg: {avg_d:.2f} ms")
        print(f"  P95: {p95_d:.2f} ms {'✅ 达标' if p95_d < 500 else '⚠️ 偏高'}")

    if llm_latencies:
        print("增强模式 (LLM Mode):")
        print(f"  Avg: {statistics.mean(llm_latencies):.2f} ms (依赖外部API)")

if __name__ == "__main__":
    run_benchmark()
