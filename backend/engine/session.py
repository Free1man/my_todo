from __future__ import annotations
from typing import Any, Dict
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class Session(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    ruleset: str
    scheduler: str
    state: Dict[str, Any]
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
