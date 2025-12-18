import time
import requests
import statistics

# 目标地址 (Docker 启动后也是这个)
URL = "http://127.0.0.1:8000/ask"

# 测试集：覆盖 直通、AI润色、兜底 三种情况
TEST_CASES = [
    "年假怎么申请",             # 预期: Direct (极快)
    "忘记打卡怎么办",           # 预期: Direct
    "想请假带猫做绝育",         # 预期: LLM (根据事假/年假回答)
    "可以穿拖鞋上班吗",         # 预期: Fallback (没规定) 或 LLM
    "报销需要贴发票吗",         # 预期: Direct/LLM
    "VPN连不上",               # 预期: IT类
    "老板的电话是多少",         # 预期: Fallback (拒答)
    "加班有加班费吗"            # 预期: LLM
]

def run_smoke_test():
    print(f"开始冒烟测试 | Target: {URL}")
    print("-" * 75)
    print(f"{'Question':<20} | {'Mode':<8} | {'Conf':<6} | {'Time(s)':<7} | {'Answer Prefix'}")
    print("-" * 75)

    latencies = []
    success_count = 0

    for q in TEST_CASES:
        try:
            t0 = time.time()
            # 这里的 rewrite=False 模拟真实用户
            resp = requests.post(URL, json={"question": q, "rewrite": False}, timeout=60)
            elapsed = time.time() - t0
            latencies.append(elapsed)

            if resp.status_code == 200:
                data = resp.json()
                mode = data.get("mode", "err")
                conf = data.get("confidence", 0.0)
                # 优先取 answer，没有则取 message
                ans = data.get("answer") or data.get("message") or ""
                ans_preview = ans.replace("\n", "")[:20]
                
                success_count += 1
                print(f"{q[:18]:<20} | {mode:<8} | {conf:.2f}   | {elapsed:.2f}    | {ans_preview}...")
            else:
                print(f"{q:<20} | FAIL     | 0.00   | {elapsed:.2f}    | HTTP {resp.status_code}")

        except Exception as e:
            print(f"{q:<20} | ERROR    | 0.00   | 0.00    | {e}")

    print("-" * 75)
    if latencies:
        avg_t = statistics.mean(latencies)
        max_t = max(latencies)
        print(f"测试结束: 成功 {success_count}/{len(TEST_CASES)} | 平均耗时: {avg_t:.2f}s | 最大耗时: {max_t:.2f}s")

if __name__ == "__main__":
    run_smoke_test()