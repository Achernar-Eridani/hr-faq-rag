from __future__ import annotations

import os
import json
from fastapi import APIRouter

from app.api.schemas import AskRequest, AskResponse, Candidate
from app.cache.redis_cache import cache_get, cache_set
from app.rag.retriever import retrieve, normalize_query
from app.rag.vectorstore import get_collection
from app.rag.generator import llm_generator  

router = APIRouter()

@router.get("/health")
def health():
    _ = get_collection()
    return {"status": "ok"}

@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    q = normalize_query(req.question)
    
    # --- 1. 缓存层 (Key 包含策略版本) ---
    cache_key = f"ask:v3:{q}:{req.rewrite}"
    cached = cache_get(cache_key)
    if cached:
        return AskResponse(**cached)

    # --- 2. 检索层 (Retrieve) ---
    topk = int(os.getenv("TOPK", "5"))
    hits = retrieve(q, topk=topk)
    
    # 转换为 Schema 对象
    candidates = [
        Candidate(
            faq_id=h.get("faq_id"),
            title=h.get("title"),
            score=h.get("score", 0.0),
            question=h.get("question"),
            answer=h.get("answer")
        ) 
        for h in hits
    ]

    best_score = candidates[0].score if candidates else 0.0
    
    # --- 3. 策略路由层 (Router) ---
    
    # 阈值配置 
    DIRECT_THRESHOLD = float(os.getenv("DIRECT_THRESHOLD", "0.83"))
    MIN_THRESHOLD = float(os.getenv("MIN_THRESHOLD", "0.40"))
    GAP_THRESHOLD = float(os.getenv("GAP_THRESHOLD", "0.02"))

    best = candidates[0] if candidates else None
    second = candidates[1] if candidates and len(candidates) > 1 else None
    gap_ok = (second is None) or ((best.score - second.score) >= GAP_THRESHOLD)
    
    # 场景 A: 命中率极高 & 用户没强制 AI -> 直通模式 (Direct)
    if candidates and best.score >= DIRECT_THRESHOLD and gap_ok and not req.rewrite:
        best = candidates[0]
        resp = AskResponse(
            hit=True,
            mode="direct",
            answer=best.answer,  # 直接用预设答案
            confidence=best_score,
            sources=[best],      # 来源就是这一条
            candidates=candidates,
            message="由知识库精确命中"
        )
        # 缓存 1 小时
        cache_set(cache_key, resp.model_dump(), ttl=3600)
        return resp

    # 场景 B: 命中率尚可 OR 强制润色 -> AI 增强模式 (RAG)
    if candidates and best_score >= MIN_THRESHOLD:
        # 取 Top 3 给 AI 参考
        context_docs = hits[:3]
        
        # 调用 DeepSeek 生成
        # 这里会耗时 2-5s，前端需 loading
        ai_answer = llm_generator.generate(q, context_docs)
        
        resp = AskResponse(
            hit=True,
            mode="llm",
            answer=ai_answer,
            confidence=best_score,
            sources=candidates[:3], # 来源是前3条
            candidates=candidates,
            message="由 AI 综合知识库回答"
        )
        # AI 结果缓存 2 小时 (省钱)
        cache_set(cache_key, resp.model_dump(), ttl=7200)
        return resp

    # 场景 C: 没查到 -> 兜底模式 (Fallback)
    resp = AskResponse(
        hit=False,
        mode="fallback",
        answer=None,
        message="抱歉，知识库中未找到相关规定，建议联系 HRBP 或 IT 支持。",
        confidence=best_score,
        sources=[],
        candidates=candidates
    )
    # 没查到的结果缓存短一点 (10分钟)，方便你随时加数据测试
    cache_set(cache_key, resp.model_dump(), ttl=600)
    return resp