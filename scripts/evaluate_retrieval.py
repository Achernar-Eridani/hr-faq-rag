import os, sys, time, json, argparse
import pandas as pd

sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv()

from app.rag.vectorstore import get_collection
from app.rag.retriever import retrieve

def p95(xs):
    xs = sorted(xs)
    if not xs: return 0.0
    i = max(0, min(len(xs)-1, int(len(xs)*0.95)-1))
    return xs[i]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test_csv", default="reports/queries_test.csv")
    ap.add_argument("--topk", type=int, default=3)
    ap.add_argument("--out_dir", default="reports")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    df = pd.read_csv(args.test_csv).dropna(subset=["query","faq_id"])
    queries = df["query"].astype(str).tolist()
    true_ids = df["faq_id"].astype(str).tolist()

    get_collection()

    top1_ok = 0
    top3_ok = 0
    lat_ms = []
    bad = []

    for q, t in zip(queries, true_ids):
        t0 = time.perf_counter()
        hits = retrieve(q, topk=args.topk)
        lat_ms.append((time.perf_counter() - t0)*1000)

        pred_ids = [str(h.get("faq_id")) for h in hits if h and h.get("faq_id") is not None]
        pred1 = pred_ids[0] if pred_ids else "None"

        if pred1 == t: top1_ok += 1
        if t in pred_ids: top3_ok += 1

        if pred1 != t:
            bad.append({
                "query": q,
                "true_faq_id": t,
                "pred_topk": ",".join(pred_ids),
                "top1_score": hits[0].get("score") if hits else None,
                "top1_title": hits[0].get("title") if hits else None,
            })

    n = len(queries)
    summary = {
        "test_size": n,
        "top1_accuracy": top1_ok / n if n else 0,
        "top3_accuracy": top3_ok / n if n else 0,
        "latency_ms_avg": sum(lat_ms)/len(lat_ms) if lat_ms else 0,
        "latency_ms_p95": p95(lat_ms),
        "latency_ms_max": max(lat_ms) if lat_ms else 0,
        "badcase_count": len(bad),
    }

    with open(os.path.join(args.out_dir, "eval_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    pd.DataFrame(bad).to_csv(os.path.join(args.out_dir, "badcases.csv"), index=False)

    print("=== Retrieval Eval Summary ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"[OUT] {args.out_dir}/eval_summary.json")
    print(f"[OUT] {args.out_dir}/badcases.csv")

if __name__ == "__main__":
    main()
