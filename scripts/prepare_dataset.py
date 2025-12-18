import argparse, os, random
import pandas as pd

def pick_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--faq", default="datasets/faq.csv")
    ap.add_argument("--queries", default="datasets/queries.csv")

    ap.add_argument("--out_dir", default="reports")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--test_ratio", type=float, default=0.3)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    faq = pd.read_csv(args.faq)
    faq_id_col = pick_col(faq, ["faq_id","id","FAQ_ID"])
    if not faq_id_col:
        raise SystemExit(f"faq.csv 找不到 faq_id 列，现有列：{list(faq.columns)}")
    faq_ids = set(faq[faq_id_col].astype(str))

    qdf = pd.read_csv(args.queries)
    query_col = pick_col(qdf, ["query","question","q"])
    qid_col   = pick_col(qdf, ["faq_id","id","FAQ_ID"])
    if not query_col or not qid_col:
        raise SystemExit(f"queries.csv 需要 query/faq_id 两列，现有列：{list(qdf.columns)}")

    qdf = qdf.dropna(subset=[query_col, qid_col]).copy()
    qdf[query_col] = qdf[query_col].astype(str).str.strip()
    qdf[qid_col]   = qdf[qid_col].astype(str).str.strip()
    qdf = qdf[qdf[query_col] != ""]
    qdf = qdf.drop_duplicates(subset=[query_col], keep="first")
    qdf = qdf[qdf[qid_col].isin(faq_ids)]  # 只保留 faq.csv 里存在的 id

    rows = list(qdf[[query_col, qid_col]].itertuples(index=False, name=None))
    random.seed(args.seed)
    random.shuffle(rows)

    n = len(rows)
    n_test = int(n * args.test_ratio)
    test = rows[:n_test]
    train = rows[n_test:]

    pd.DataFrame(train, columns=["query","faq_id"]).to_csv(os.path.join(args.out_dir, "queries_train.csv"), index=False)
    pd.DataFrame(test,  columns=["query","faq_id"]).to_csv(os.path.join(args.out_dir, "queries_test.csv"), index=False)

    print(f"[OK] total={n} train={len(train)} test={len(test)}")
    print(f"[OUT] {args.out_dir}/queries_train.csv")
    print(f"[OUT] {args.out_dir}/queries_test.csv")

if __name__ == "__main__":
    main()
