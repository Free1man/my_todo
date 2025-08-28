from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uuid

from .db import get_db, init_db
from .models import User, Todo


def init_storage() -> None:
    # Create tables
    init_db()


def load_users(db: Session) -> Dict[str, str]:
    rows = db.execute(select(User.username, User.password_hash)).all()
    return {u: h for (u, h) in rows}


def save_user(db: Session, username: str, password_hash: str) -> None:
    db.add(User(username=username, password_hash=password_hash))
    db.commit()


def add_user_if_absent(db: Session, username: str, password_hash: str) -> bool:
    try:
        db.add(User(username=username, password_hash=password_hash))
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def get_user_password_hash(db: Session, username: str) -> Optional[str]:
    row = db.execute(select(User.password_hash).where(User.username == username)).first()
    return row[0] if row else None


def list_todos(db: Session, owner: str) -> List[dict]:
    items = (
        db.query(Todo)
        .filter(Todo.owner_username == owner)
        .order_by(Todo.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(i.id),
            "owner": i.owner_username,
            "text": i.text,
            "done": i.done,
            "created_at": i.created_at,
        }
        for i in items
    ]


def add_todo(db: Session, owner: str, text: str) -> dict:
    item = Todo(owner_username=owner, text=text, done=False)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "id": str(item.id),
        "owner": item.owner_username,
        "text": item.text,
        "done": item.done,
        "created_at": item.created_at,
    }


def update_todo(db: Session, owner: str, todo_id: str, *, done: Optional[bool] = None, text: Optional[str] = None) -> Optional[dict]:
    try:
        tid = uuid.UUID(todo_id)
    except ValueError:
        return None
    obj = db.get(Todo, tid)
    if not obj or obj.owner_username != owner:
        return None
    if done is not None:
        obj.done = done
    if text is not None:
        obj.text = text
    db.commit()
    db.refresh(obj)
    return {
        "id": str(obj.id),
        "owner": obj.owner_username,
        "text": obj.text,
        "done": obj.done,
        "created_at": obj.created_at,
    }


def delete_todo(db: Session, owner: str, todo_id: str) -> bool:
    try:
        tid = uuid.UUID(todo_id)
    except ValueError:
        return False
    obj = db.get(Todo, tid)
    if not obj or obj.owner_username != owner:
        return False
    db.delete(obj)
    db.commit()
    return True
