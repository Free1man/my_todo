from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from datetime import timedelta

from .schemas import RegisterRequest, LoginRequest, TokenResponse, TodoCreate, TodoUpdate, Todo
from .security import verify_password, get_password_hash, create_access_token, decode_token
from . import storage

app = FastAPI(title="Tiny TODO API", version="0.1.0")
auth_scheme = HTTPBearer()

def get_current_username(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)) -> str:
    token = credentials.credentials
    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing subject")
        return username
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")

@app.on_event("startup")
def _startup():
    storage.init_storage()

@app.get("/health") 
def health():
    return {"status": "ok"}

@app.post("/register", status_code=201)
def register(body: RegisterRequest):
    users = storage.load_users()
    if body.username in users:
        raise HTTPException(status_code=400, detail="Username already exists")
    password_hash = get_password_hash(body.password)
    storage.save_user(body.username, password_hash)
    return {"message": "registered"}

@app.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    users = storage.load_users()
    password_hash = users.get(body.username)
    if not password_hash or not verify_password(body.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(body.username, expires_delta=timedelta(minutes=60))
    return TokenResponse(access_token=token)

@app.get("/todos", response_model=List[Todo])
def list_my_todos(username: str = Depends(get_current_username)):
    rows = storage.list_todos(username)
    # Serialize to pydantic models
    return [Todo(**r) for r in rows]

@app.post("/todos", response_model=Todo, status_code=201)
def create_todo(body: TodoCreate, username: str = Depends(get_current_username)):
    item = storage.add_todo(username, body.text)
    return Todo(**item)

@app.patch("/todos/{todo_id}", response_model=Todo)
def patch_todo(todo_id: str, body: TodoUpdate, username: str = Depends(get_current_username)):
    updated = storage.update_todo(username, todo_id, done=body.done, text=body.text)
    if not updated:
        raise HTTPException(status_code=404, detail="Todo not found")
    return Todo(**updated)

@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: str, username: str = Depends(get_current_username)):
    ok = storage.delete_todo(username, todo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Todo not found")
    return None


# Serve static UI (placed last so API routes take priority)
app.mount('/', StaticFiles(directory=Path(__file__).parent / 'static', html=True), name='static')
