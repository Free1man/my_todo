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
import logging
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
logger = logging.getLogger(__name__)


def _get_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    # By default, stream to repo ./data so files update during tests.
    # Override with TEST_DATA_DIR or set to 'tmp' to isolate per-session.
    env_data_dir = os.environ.get("TEST_DATA_DIR")
    if env_data_dir == "tmp":
        tmp_data = tmp_path_factory.mktemp("data")
        logger.info("[tests] Using temporary DATA_DIR (isolated): %s", tmp_data)
    elif env_data_dir:
        tmp_data = Path(env_data_dir)
        logger.info("[tests] Using DATA_DIR from TEST_DATA_DIR: %s", tmp_data)
    else:
        tmp_data = DATA_DIR
        logger.info("[tests] Using repo DATA_DIR by default: %s", tmp_data)

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
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    logger.info("[tests] Started uvicorn (pid=%s) with DATA_DIR=%s", proc.pid, env["DATA_DIR"])

    # Wait for health endpoint
    url = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            r = requests.get(url + "/health", timeout=1.0)
            if r.status_code == 200:
                break
        except Exception:
            pass
        # If process died early, surface logs
        if proc.poll() is not None:
            out, err = proc.communicate(timeout=2)
            raise RuntimeError(f"Server exited early (code={proc.returncode}). STDOUT:\n{out}\nSTDERR:\n{err}")
        time.sleep(0.25)
    else:
        try:
            out, err = proc.communicate(timeout=2)
        except Exception:
            out, err = ("", "")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        raise RuntimeError(f"Server did not start in time. STDOUT:\n{out}\nSTDERR:\n{err}")

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
