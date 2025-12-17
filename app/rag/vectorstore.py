from __future__ import annotations

import os
from functools import lru_cache

import chromadb

# 变成单例模式，确保只初始化一次链接，第二次调用只会返回存好的对象
@lru_cache(maxsize=1)
def get_collection():
    chroma_dir = os.getenv("CHROMA_DIR", "./vectorstore")
    col_name = os.getenv("CHROMA_COLLECTION", "hr_faq")
    client = chromadb.PersistentClient(path=chroma_dir)
    # cosine space：distance = 1 - cos_sim
    return client.get_or_create_collection(name=col_name, metadata={"hnsw:space": "cosine"})
