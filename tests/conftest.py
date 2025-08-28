# Test configuration to spin up the FastAPI app with a real uvicorn server
# and provide helper fixtures.

import os
import sys
import socket
import subprocess
import time
from contextlib import closing
from pathlib import Path
from typing import Iterator

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def _get_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    # Isolate data dir per test session to avoid polluting repo files
    tmp_data = tmp_path_factory.mktemp("data")

    env = os.environ.copy()
    env["DATA_DIR"] = str(tmp_data)
    env.setdefault("SECRET_KEY", "test-secret")

    port = _get_free_port()

    # Start uvicorn pointing to our app module
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env)

    # Wait for health endpoint
    url = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            r = requests.get(url + "/health", timeout=1.0)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.25)
    else:
        proc.terminate()
        proc.wait(timeout=5)
        raise RuntimeError("Server did not start in time")

    try:
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture()
def http(base_url: str):
    class Client:
        def __init__(self, base: str):
            self.base = base

        def register(self, username: str, password: str) -> requests.Response:
            return requests.post(
                self.base + "/register",
                json={"username": username, "password": password},
                timeout=5,
            )

        def login(self, username: str, password: str) -> str:
            r = requests.post(
                self.base + "/login",
                json={"username": username, "password": password},
                timeout=5,
            )
            r.raise_for_status()
            return r.json()["access_token"]

        def auth_headers(self, token: str):
            return {"Authorization": f"Bearer {token}"}

        def create_todo(self, token: str, text: str):
            r = requests.post(
                self.base + "/todos",
                headers=self.auth_headers(token),
                json={"text": text},
                timeout=5,
            )
            r.raise_for_status()
            return r.json()

        def list_todos(self, token: str):
            r = requests.get(
                self.base + "/todos",
                headers=self.auth_headers(token),
                timeout=5,
            )
            r.raise_for_status()
            return r.json()

        def finish_todo(self, token: str, todo_id: str):
            r = requests.patch(
                self.base + f"/todos/{todo_id}",
                headers=self.auth_headers(token),
                json={"done": True},
                timeout=5,
            )
            r.raise_for_status()
            return r.json()

    return Client(base_url)
