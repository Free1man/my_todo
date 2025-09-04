import json
import logging
import os
import socket
import subprocess
import time
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
# Project root (docker-compose.yml is located here)
PROJECT_ROOT = ROOT.parent

# Cache config: store API url and timestamp to enable reuse across runs
CACHE_FILE = PROJECT_ROOT / ".api_url_cache.json"
CACHE_TTL_SECONDS = int(os.getenv("API_CACHE_TTL_SECONDS", "600"))  # default 10 minutes
logger = logging.getLogger(__name__)


def _get_free_port(host: str = "127.0.0.1") -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def _load_cache():
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.debug("[tests] Failed to read cache %s: %s", CACHE_FILE, e)
    return None


def _save_cache(url: str):
    try:
        payload = {"url": url, "timestamp": time.time()}
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        logger.info("[tests] Cached API instance at %s -> %s", url, CACHE_FILE)
    except Exception as e:
        logger.debug("[tests] Failed to write cache %s: %s", CACHE_FILE, e)


def _is_healthy(url: str, attempts: int = 3, delay: float = 1.0) -> bool:
    import requests  # local import to avoid issues if requests isn't needed

    for i in range(attempts):
        try:
            r = requests.get(f"{url}/health", timeout=5)
            if r.status_code == 200:
                return True
        except Exception as e:
            logger.debug(
                "[tests] Health probe failed (attempt %s/%s): %s", i + 1, attempts, e
            )
        time.sleep(delay)
    return False


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

    # Otherwise, attempt to reuse a cached API instance; refresh if stale (> TTL) or unhealthy.
    cache = _load_cache()
    now = time.time()
    if cache and isinstance(cache, dict):
        cached_url = cache.get("url")
        ts = float(cache.get("timestamp", 0))
        if cached_url and (now - ts) <= CACHE_TTL_SECONDS:
            logger.info(
                "[tests] Reusing cached API instance at %s (age=%.1fs)",
                cached_url,
                now - ts,
            )
            if _is_healthy(cached_url):
                yield cached_url
                return
            else:
                logger.info("[tests] Cached API instance unhealthy, refreshing...")

    # Start or refresh the Docker Compose stack
    # Stop existing stack if any, to allow port remap and rebuild
    subprocess.run(
        ["docker", "compose", "stop", "api", "redis"],
        cwd=str(PROJECT_ROOT),
        check=False,
    )

    port = _get_free_port()
    env = os.environ.copy()
    env["PORT"] = str(port)
    up_cmd = ["docker", "compose", "up", "-d", "--build", "--wait"]
    logger.info(
        "[tests] Starting docker compose on PORT=%s: %s", port, " ".join(up_cmd)
    )
    up_proc = subprocess.run(
        up_cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if up_proc.returncode != 0:
        raise RuntimeError(
            f"docker compose up failed:\nSTDOUT:\n{up_proc.stdout}\nSTDERR:\n{up_proc.stderr}"
        )
    url = f"http://127.0.0.1:{port}"

    # Wait for API to be healthy
    logger.info("[tests] Waiting for API health check...")
    for attempt in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                logger.info(
                    f"[tests] Health check passed (attempt {attempt + 1}): {health_data}"
                )
                break
        except Exception as e:
            logger.debug(f"[tests] Health check attempt {attempt + 1} failed: {e}")
        time.sleep(1)
    else:
        raise RuntimeError("API health check failed after 30 seconds")

    # Persist cache for reuse in the next run and yield the URL. Do not stop containers here.
    _save_cache(url)
    yield url


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
