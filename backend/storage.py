from __future__ import annotations
from typing import Generic, TypeVar, Dict, List, Optional

T = TypeVar("T")

class Storage(Generic[T]):
    def get(self, key: str) -> Optional[T]:
        raise NotImplementedError
    def save(self, value: T) -> None:
        raise NotImplementedError
    def delete(self, key: str) -> None:
        raise NotImplementedError
    def list_all(self) -> List[T]:
        raise NotImplementedError

class InMemoryStorage(Storage[T]):
    def __init__(self):
        self._data: Dict[str, T] = {}
    def get(self, key: str) -> Optional[T]:
        return self._data.get(key)
    def save(self, value: T) -> None:
        self._data[getattr(value, "id")] = value
    def delete(self, key: str) -> None:
        self._data.pop(key, None)
    def list_all(self) -> List[T]:
        return list(self._data.values())
