from functools import lru_cache

import chromadb

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    settings = get_settings()
    return chromadb.PersistentClient(path=settings.chroma_path)
