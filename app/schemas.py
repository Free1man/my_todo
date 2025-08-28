from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TodoCreate(BaseModel):
    text: str = Field(min_length=1, max_length=500)

class TodoUpdate(BaseModel):
    done: Optional[bool] = None
    text: Optional[str] = Field(default=None, min_length=1, max_length=500)

class Todo(BaseModel):
    id: str
    owner: str
    text: str
    done: bool
    created_at: datetime
