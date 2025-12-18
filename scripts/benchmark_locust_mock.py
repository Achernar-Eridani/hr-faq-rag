import time
import concurrent.futures
import requests
import statistics
import random

URL = "http://127.0.0.1:8000/ask"
CONCURRENT_USERS = 10  
TOTAL_REQUESTS = 50    

QUERIES = [
    ("年假怎么申请", False),      # Direct
    ("忘记打卡怎么办", False),    # Direct
    ("报销流程是什么", False),    # Direct
    ("VPN连不上", False),        # Direct
    ("电脑密码忘了", False),      # Direct
    ("带狗看病怎么弄", False),    # LLM
    ("加班费怎么算", True)        # LLM
]

def send_request(i):
    # 模拟用户思考时间 (0.1s - 0.5s)，避免瞬时流量洪峰
    time.sleep(random.uniform(0.1, 0.5))
    
    q, rewrite = random.choice(QUERIES)
    payload = {"question": q, "rewrite": rewrite}
    
    t0 = time.time()
    try:
        resp = requests.post(URL, json=payload, timeout=30)
        latency = (time.time() - t0) * 1000 # ms
        
        return {
            "status": resp.status_code,
            "latency": latency,
            "mode": resp.json().get("mode", "unknown")
        }
    except Exception as e:
        return {"status": "error", "latency": 0, "mode": "error"}

def run_benchmark():
    print(f"开始优化版并发测试: {CONCURRENT_USERS} 并发 | 总请求 {TOTAL_REQUESTS}")
    print("正在模拟真实用户行为...")
    print("-" * 60)
    
    results = []
    start_global = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        futures = [executor.submit(send_request, i) for i in range(TOTAL_REQUESTS)]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            # 实时打印一点进度
            print(f".", end="", flush=True)
            results.append(res)
            
    total_time = time.time() - start_global
    print("\n" + "-" * 60)
    
    # 统计
    success = [r for r in results if r['status'] == 200]
    error_count = len(results) - len(success)
    
    direct_latencies = [r['latency'] for r in success if r['mode'] == 'direct']
    llm_latencies = [r['latency'] for r in success if r['mode'] == 'llm']
    
    print(f"测试报告 Summary:")
    print(f"并发用户: {CONCURRENT_USERS} | 总请求: {len(results)}")
    print(f"错误率:   {error_count/len(results):.2%} (目标 <= 1%)")
    print(f"RPS:      {len(success)/total_time:.2f}")
    
    if direct_latencies:
        avg_d = statistics.mean(direct_latencies)
        p95_d = statistics.quantiles(direct_latencies, n=20)[18]
        print(f"直通模式 (Direct Mode) - 核心指标:")
        print(f"  Avg: {avg_d:.2f} ms")
        print(f"  P95: {p95_d:.2f} ms {'✅ 达标' if p95_d < 500 else '⚠️ 偏高'}")
        
    if llm_latencies:
        print(f"增强模式 (LLM Mode):")
        print(f"  Avg: {statistics.mean(llm_latencies):.2f} ms (依赖外部API)")

if __name__ == "__main__":
    run_benchmark()