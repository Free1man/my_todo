# Test configuration to run against the Dockerized FastAPI app.

import os
import subprocess
import time
from typing import Iterator
import socket
from contextlib import closing

import pytest
import logging
import requests

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)


def _get_free_port(host: str = "127.0.0.1") -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url() -> Iterator[str]:
    """Run tests against the Dockerized API at http://127.0.0.1:8000.

    This fixture brings up the Compose service, waits for /health, yields the URL,
    and stops the service after the test session.
    """
    port = _get_free_port()
    env = os.environ.copy()
    env["PORT"] = str(port)

    up_cmd = ["docker", "compose", "up", "-d", "--build", "--wait"]
    logger.info("[tests] Starting docker compose on PORT=%s: %s", port, " ".join(up_cmd))
    up_proc = subprocess.run(up_cmd, cwd=str(ROOT), env=env, capture_output=True, text=True)
    if up_proc.returncode != 0:
        raise RuntimeError(
            f"docker compose up failed:\nSTDOUT:\n{up_proc.stdout}\nSTDERR:\n{up_proc.stderr}"
        )

    url = f"http://127.0.0.1:{port}"

    try:
        yield url
    finally:
        subprocess.run(["docker", "compose", "stop", "api"], cwd=str(ROOT), check=False)


@pytest.fixture()
def http(base_url: str):
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    default_timeout = 5

    class Client:
        def __init__(self, base: str):
            self.base = base

        def register(self, username: str, password: str) -> requests.Response:
            return session.post(
                self.base + "/register",
                json={"username": username, "password": password},
                timeout=default_timeout,
            )

        def login(self, username: str, password: str) -> str:
            r = session.post(
                self.base + "/login",
                json={"username": username, "password": password},
                timeout=default_timeout,
            )
            r.raise_for_status()
            return r.json()["access_token"]

        def auth_headers(self, token: str):
            return {"Authorization": f"Bearer {token}"}

        def create_todo(self, token: str, text: str):
            r = session.post(
                self.base + "/todos",
                headers=self.auth_headers(token),
                json={"text": text},
                timeout=default_timeout,
            )
            r.raise_for_status()
            return r.json()

        def list_todos(self, token: str):
            r = session.get(
                self.base + "/todos",
                headers=self.auth_headers(token),
                timeout=default_timeout,
            )
            r.raise_for_status()
            return r.json()

        def finish_todo(self, token: str, todo_id: str):
            r = session.patch(
                self.base + f"/todos/{todo_id}",
                headers=self.auth_headers(token),
                json={"done": True},
                timeout=default_timeout,
            )
            r.raise_for_status()
            return r.json()

    return Client(base_url)
