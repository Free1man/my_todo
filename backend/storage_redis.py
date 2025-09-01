from __future__ import annotations
from typing import Generic, TypeVar, Optional, List, Type
from pydantic import BaseModel
import redis

from .storage import Storage

T = TypeVar("T", bound=BaseModel)

class RedisStorage(Storage[T], Generic[T]):
    """
    JSON-over-Redis storage using keys like: <prefix>:<id>
    """
    def __init__(
        self,
        client: "redis.Redis",
        model_cls: Type[T],
        key_prefix: str = "tbs:session",
        ttl_seconds: Optional[int] = None,
    ):
        self.client = client
        self.model_cls = model_cls
        self.key_prefix = key_prefix.rstrip(":")
        self.ttl_seconds = ttl_seconds

    def _key(self, id_: str) -> str:
        return f"{self.key_prefix}:{id_}"

    def get(self, key: str) -> Optional[T]:
        raw = self.client.get(self._key(key))
        if raw is None:
            return None
        return self.model_cls.model_validate_json(raw)

    def save(self, value: T) -> None:
        id_ = getattr(value, "id")
        data = value.model_dump_json()
        k = self._key(id_)
        if self.ttl_seconds:
            self.client.setex(k, self.ttl_seconds, data)
        else:
            self.client.set(k, data)

    def delete(self, key: str) -> None:
        self.client.delete(self._key(key))

    def list_all(self) -> List[T]:
        out: List[T] = []
        cursor = 0
        pattern = f"{self.key_prefix}:*"
        while True:
            cursor, keys = self.client.scan(cursor=cursor, match=pattern, count=200)
            if keys:
                vals = self.client.mget(keys)
                for v in vals:
                    if v:
                        out.append(self.model_cls.model_validate_json(v))
            if cursor == 0:
                break
        return out
