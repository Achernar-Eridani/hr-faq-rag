from __future__ import annotations

import os
from typing import Any, Dict, List

from app.rag.embedder import embed_texts
from app.rag.vectorstore import get_collection

# 标准化查询，去除首尾空格和中间空格
def normalize_query(q: str) -> str:
    return " ".join((q or "").strip().split())


def retrieve(query: str, topk: int | None = None) -> List[Dict[str, Any]]:
    q = normalize_query(query)
    if not q:
        return [] 

    k = topk or int(os.getenv("TOPK", "5"))
    col = get_collection()

    # 问题转成向量
    q_emb = embed_texts([q], batch_size=1)[0]
    # 搜索topk
    res = col.query(
        query_embeddings=[q_emb],
        n_results=k,
        include=["distances", "metadatas"],
    )

    out: List[Dict[str, Any]] = []
    # Chroma 返回的结构是 List[List]，需要解包
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]

    for meta, dist in zip(metas, dists):
        sim = 1.0 - float(dist)  # 存cosine 需要相似度
        out.append(
            {
                "faq_id": meta.get("faq_id"),
                "title": meta.get("title"),
                "question": meta.get("question"),
                "answer": meta.get("answer"),
                "tags": meta.get("tags", ""),
                "score": sim,
            }
        )

    return out
