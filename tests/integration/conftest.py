import os
import subprocess
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
    """
    Provide a base URL to the API for integration tests.

    - When running outside a container, spin up the Docker Compose stack on a
      free host port and return the mapped URL (as before).
    - When running inside a container (for example, in a devcontainer or CI
      container), assume the API is already running and return a default URL.
      You can override the default via the BASE_URL environment variable.
    """
    default_env_url = os.getenv("BASE_URL")
    inside_container = os.path.exists("/.dockerenv")
    if default_env_url or inside_container:
        # Use provided BASE_URL or fall back to the standard API port.
        url = default_env_url or "http://127.0.0.1:8000"
        logger.info("[tests] Using existing API instance at %s", url)
        yield url
        return

    # Otherwise, spin up a fresh Docker Compose stack as before.
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
        subprocess.run(["docker", "compose", "stop", "api", "db"], cwd=str(ROOT), check=False)


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
