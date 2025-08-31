from __future__ import annotations
import os
import asyncio
from typing import Dict, Optional, Protocol

from backend.engine.session import Session

try:
    # Optional: pip install "redis>=5"
    import redis.asyncio as redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore


class SessionStore(Protocol):
    async def get(self, sid: str) -> Optional[Session]: ...
    async def set(self, s: Session) -> None: ...
    async def delete(self, sid: str) -> None: ...
    async def all(self) -> Dict[str, Session]: ...


class MemorySessionStore:
    """In-process store with an asyncio.Lock for safety within a single worker."""
    def __init__(self) -> None:
        self._data: Dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def get(self, sid: str) -> Optional[Session]:
        async with self._lock:
            return self._data.get(sid)

    async def set(self, s: Session) -> None:
        async with self._lock:
            self._data[s.id] = s

    async def delete(self, sid: str) -> None:
        async with self._lock:
            self._data.pop(sid, None)

    async def all(self) -> Dict[str, Session]:
        async with self._lock:
            return dict(self._data)


class RedisSessionStore:
    """Cross-worker store using Redis. Set REDIS_URL to enable."""
    def __init__(self, url: str) -> None:
        if not redis:
            raise RuntimeError('redis is not installed. Add "redis>=5" to requirements.')
        self._r = redis.from_url(url, encoding="utf-8", decode_responses=True)
        self._prefix = "tbs:sessions:"

    def _key(self, sid: str) -> str:
        return f"{self._prefix}{sid}"

    async def get(self, sid: str) -> Optional[Session]:
        data = await self._r.get(self._key(sid))
        return Session.model_validate_json(data) if data else None

    async def set(self, s: Session) -> None:
        await self._r.set(self._key(s.id), s.model_dump_json())

    async def delete(self, sid: str) -> None:
        await self._r.delete(self._key(sid))

    async def all(self) -> Dict[str, Session]:
        keys = await self._r.keys(f"{self._prefix}*")
        out: Dict[str, Session] = {}
        for k in keys:
            data = await self._r.get(k)
            if data:
                s = Session.model_validate_json(data)
                out[s.id] = s
        return out


REDIS_URL = os.getenv("REDIS_URL")
store: SessionStore = RedisSessionStore(REDIS_URL) if REDIS_URL else MemorySessionStore()

# Convenience helpers (import these in app.py)
async def save_session(s: Session) -> None:
    await store.set(s)

async def get_session(sid: str) -> Optional[Session]:
    return await store.get(sid)

async def delete_session(sid: str) -> None:
    await store.delete(sid)
