from pydantic import BaseModel, Field
from typing import List, Optional

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    rewrite: bool = False

class Candidate(BaseModel):
    faq_id: Optional[str] = None
    title: Optional[str] = None
    score: float = 0.0
    question: Optional[str] = None
    answer: Optional[str] = None

class AskResponse(BaseModel):
    hit: bool
    mode: str = "unknown"
    answer: Optional[str] = None
    message: Optional[str] = None
    confidence: float = 0.0
    sources: List[Candidate] = Field(default_factory=list)
    candidates: List[Candidate] = Field(default_factory=list)
