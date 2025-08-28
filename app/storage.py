from __future__ import annotations
import csv
import os
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime, timezone
from filelock import FileLock

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data")).resolve()
USERS_CSV = DATA_DIR / "users.csv"
TODOS_CSV = DATA_DIR / "todos.csv"

USERS_LOCK = FileLock(str(USERS_CSV) + ".lock")
TODOS_LOCK = FileLock(str(TODOS_CSV) + ".lock")

CSV_USER_HEADERS = ["username", "password_hash"]
CSV_TODO_HEADERS = ["id", "owner", "text", "done", "created_at"]


def _ensure_csv_headers(path: Path, headers: List[str], lock: FileLock) -> None:
    """Ensure CSV file exists and has a header row matching headers.

    If the file doesn't exist or is empty, create it with header.
    If it exists but the first row isn't the expected header, rewrite the file
    by prepending the header and keeping existing rows as-is.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock:
        if not path.exists() or path.stat().st_size == 0:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
            return

        # Check first row
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            first = next(reader, None)

        if first is None:
            # Empty file (size > 0 but no rows?) — just write header
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
            return

        # If header already matches, nothing to do
        if [c.strip() for c in first] == headers:
            return

        # Otherwise, rewrite file: prepend header then existing rows unchanged
        with open(path, "r", newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            # If the original first row was actually a header with wrong names,
            # we still keep all rows to avoid data loss.
            for row in rows:
                writer.writerow(row)

def init_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_csv_headers(USERS_CSV, CSV_USER_HEADERS, USERS_LOCK)
    _ensure_csv_headers(TODOS_CSV, CSV_TODO_HEADERS, TODOS_LOCK)

def load_users() -> Dict[str, str]:
    users: Dict[str, str] = {}
    if not USERS_CSV.exists():
        return users
    with USERS_LOCK, open(USERS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            users[row["username"]] = row["password_hash"]
    return users

def save_user(username: str, password_hash: str) -> None:
    with USERS_LOCK, open(USERS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_USER_HEADERS)
        writer.writerow({"username": username, "password_hash": password_hash})

def list_todos(owner: str) -> List[dict]:
    items: List[dict] = []
    if not TODOS_CSV.exists():
        return items
    with TODOS_LOCK, open(TODOS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["owner"] == owner:
                items.append({
                    "id": row["id"],
                    "owner": row["owner"],
                    "text": row["text"],
                    "done": row["done"].lower() == "true",
                    "created_at": datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(timezone.utc),
                })
    return items

def add_todo(owner: str, text: str) -> dict:
    item = {
        "id": str(uuid4()),
        "owner": owner,
        "text": text,
        "done": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with TODOS_LOCK, open(TODOS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_TODO_HEADERS)
        writer.writerow(item)
    # Convert created_at string to datetime for API response
    item["created_at"] = datetime.fromisoformat(item["created_at"])
    return item

def _rewrite_todos(rows: List[dict]) -> None:
    with TODOS_LOCK, open(TODOS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_TODO_HEADERS)
        writer.writeheader()
        for r in rows:
            row = r.copy()
            if isinstance(row.get("created_at"), datetime):
                row["created_at"] = row["created_at"].isoformat()
            writer.writerow(row)

def update_todo(owner: str, todo_id: str, *, done: Optional[bool]=None, text: Optional[str]=None) -> Optional[dict]:
    """Update a todo in a read-modify-write critical section.

    We hold TODOS_LOCK across both read and write to avoid races under
    concurrent updates that could otherwise cause lost updates or intermittent
    misses.
    """
    target: Optional[dict] = None
    with TODOS_LOCK:
        # Read current rows
        current = []
        if not TODOS_CSV.exists():
            return None
        with open(TODOS_CSV, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["id"] == todo_id and row["owner"] == owner:
                    target = {
                        "id": row["id"],
                        "owner": row["owner"],
                        "text": text if text is not None else row["text"],
                        "done": (done if done is not None else (row["done"].lower() == "true")),
                        "created_at": row.get("created_at") or datetime.now(timezone.utc).isoformat(),
                    }
                    current.append(target.copy())
                else:
                    current.append(row)

        if not target:
            return None

        # Write back while still holding the lock
        with open(TODOS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_TODO_HEADERS)
            writer.writeheader()
            for r in current:
                row = r.copy()
                if isinstance(row.get("created_at"), datetime):
                    row["created_at"] = row["created_at"].isoformat()
                writer.writerow(row)

    # Convert for API response (outside lock)
    target["created_at"] = (
        datetime.fromisoformat(target["created_at"]) if isinstance(target["created_at"], str) else target["created_at"]
    )
    return target

def delete_todo(owner: str, todo_id: str) -> bool:
    removed = False
    current = []
    with TODOS_LOCK, open(TODOS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["id"] == todo_id and row["owner"] == owner:
                removed = True
                continue
            current.append(row)
    if removed:
        _rewrite_todos(current)
    return removed
