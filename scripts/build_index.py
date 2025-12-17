import argparse
import os, sys
# 工作目录添加到Python路径
sys.path.append(os.getcwd())
from typing import List, Dict, Any

import pandas as pd
from dotenv import load_dotenv
import chromadb

from app.rag.embedder import embed_texts


def build_rows(df: pd.DataFrame) -> tuple[List[str], List[str], List[Dict[str, Any]]]:
    ids: List[str] = []
    docs: List[str] = []
    metas: List[Dict[str, Any]] = []

    for _, r in df.iterrows():
        faq_id = str(r["faq_id"]).strip()
        title = str(r["title"]).strip()
        question = str(r["question"]).strip()
        answer = str(r["answer"]).strip()
        tags = str(r.get("tags", "")).strip()

        # 核心策略：索引内容 = 标题 + 问题
        # 这样用户搜“年假”或“怎么休年假”都能匹配上        
        doc = f"{title}\n{question}".strip()

        ids.append(faq_id)
        docs.append(doc)
        metas.append(
            {
                "faq_id": faq_id,
                "title": title,
                "question": question,
                "answer": answer,
                "tags": tags,
            }
        )

    return ids, docs, metas


def get_collection(chroma_dir: str, name: str, reset: bool):
    # Chroma 会在目录下生成 sqlite3 文件
    client = chromadb.PersistentClient(path=chroma_dir)

    if reset:
        try:
            client.delete_collection(name=name)
            print(f"[OK] Deleted existing collection: {name}")
        except Exception:
            pass

    # 用 cosine 距离（返回 distance=1-cos_sim）
    col = client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
    return col


def main():
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--faq", default="datasets/faq.csv")
    ap.add_argument("--reset", action="store_true", help="delete and rebuild collection")
    ap.add_argument("--query", default=None, help="run a test query after indexing")
    ap.add_argument("--topk", type=int, default=int(os.getenv("TOPK", "5")))
    ap.add_argument("--batch_size", type=int, default=32)
    args = ap.parse_args()

    chroma_dir = os.getenv("CHROMA_DIR", "./vectorstore")
    col_name = os.getenv("CHROMA_COLLECTION", "hr_faq")

    df = pd.read_csv(args.faq)
    assert {"faq_id", "title", "question", "answer"}.issubset(df.columns), "faq.csv missing required columns"

    ids, docs, metas = build_rows(df)

    print(f"[INFO] Loading FAQ rows: {len(ids)}")
    print(f"[INFO] Chroma dir: {chroma_dir}, collection: {col_name}")

    col = get_collection(chroma_dir, col_name, reset=args.reset)

    # 生成 embeddings
    embeddings = embed_texts(docs, batch_size=args.batch_size)

    # 写入（upsert 可以重复跑）
    col.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
    print(f"[OK] Upserted {len(ids)} docs into Chroma collection: {col_name}")

    # 跑一个查询看看 topK
    if args.query:
        q = args.query.strip()
        q_emb = embed_texts([q], batch_size=1)[0]

        res = col.query(
            query_embeddings=[q_emb],
            n_results=args.topk,
            include=["distances", "metadatas", "documents"],
        )

        print("\n=== QUERY ===")
        print(q)
        print("\n=== TOPK ===")
        for i in range(args.topk):
            meta = res["metadatas"][0][i]
            dist = res["distances"][0][i]
            sim = 1.0 - float(dist)  # cosine similarity（因为我们选了 cosine space）
            print(f"{i+1}. {meta['faq_id']}  sim={sim:.4f}  title={meta['title']}")
            print(f"   Q: {meta['question']}")
        print()

    print("[DONE]")


if __name__ == "__main__":
    main()
