from __future__ import annotations

import os
import time
import uuid
from fastapi import APIRouter

from app.api.schemas import AskRequest, AskResponse, Candidate
from app.cache.redis_cache import cache_get, cache_set
from app.rag.retriever import retrieve, normalize_query
from app.rag.vectorstore import get_collection


router = APIRouter()


@router.get("/health")
def health():
    # 触发一次 collection 初始化（如果目录不存在/权限问题会暴露）
    _ = get_collection()
    return {"status": "ok"}


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    t0 = time.time()
    q = normalize_query(req.question)

    # 缓存（可用就用，不可用自动跳过）
    cache_key = f"ask:v1:{q}"
    cached = cache_get(cache_key)
    if cached:
        return AskResponse(**cached)

    topk = int(os.getenv("TOPK", "5"))
    threshold = float(os.getenv("THRESHOLD", "0.80"))

    hits = retrieve(q, topk=topk)
    candidates = [Candidate(faq_id=h["faq_id"], title=h["title"], score=h["score"]) for h in hits]

    # 最后兜底
    if not hits:
        resp = AskResponse(
            hit=False,
            message="未找到相关条目，建议联系 HR 或换一种问法。",
            confidence=0.0,
            candidates=candidates,
        )
        # 缓存空结果，防止缓存穿透
        cache_set(cache_key, resp.model_dump(), ttl=600)
        return resp

    best = hits[0]
    conf = float(best["score"])

    if conf >= threshold:
        resp = AskResponse(
            hit=True,
            answer=best["answer"],
            confidence=conf,
            faq_id=best["faq_id"],
            title=best["title"],
            candidates=candidates,
        )
    else:
        # 分数不够高，知识库里面没有
        resp = AskResponse(
            hit=False,
            message="未命中足够置信度的标准答案。建议参考候选问题或联系 HR。",
            confidence=conf,
            candidates=candidates,
        )

    # 缓存 1h
    cache_set(cache_key, resp.model_dump(), ttl=3600)
    return resp
