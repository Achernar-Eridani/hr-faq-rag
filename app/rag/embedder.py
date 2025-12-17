from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_embedder(model_name: Optional[str] = None) -> SentenceTransformer:
    # 第一次运行会自动下载模型到本地缓存 (~100MB)
    name = model_name or os.getenv("EMBED_MODEL", "BAAI/bge-small-zh-v1.5")
    return SentenceTransformer(name)


def embed_texts(texts: List[str], model_name: Optional[str] = None, batch_size: int = 32) -> List[List[float]]:
    model = get_embedder(model_name)
    vecs = model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,  # 归一化，这对 Cosine 相似度至关重要
        show_progress_bar=True,
    )
    # Chroma 需要 list 格式
    return vecs.astype(np.float32).tolist()