from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    rewrite: bool = False  # 预留给后面llm进行rewrite


class Candidate(BaseModel):
    faq_id: str
    title: str
    score: float


class AskResponse(BaseModel):
    hit: bool
    answer: Optional[str] = None
    message: Optional[str] = None
    confidence: float
    faq_id: Optional[str] = None
    title: Optional[str] = None
    candidates: List[Candidate] = []
