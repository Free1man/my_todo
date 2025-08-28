import random
import string
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

import pytest
import logging


logger = logging.getLogger(__name__)


def random_username(prefix: str = "user") -> str:
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}_{suffix}"


@pytest.mark.timeout(120)
def test_create_and_finish_randomized(http):
    total_users = 10
    todos_per_user = 100
    max_workers = min(32, total_users)

    user_names = [random_username("u") for _ in range(total_users)]

    results: Dict[str, Dict[str, List[str]]] = {}

    logger.info(
        "Starting concurrency test: users=%d, todos_per_user=%d, max_workers=%d",
        total_users,
        todos_per_user,
        max_workers,
    )

    def run_user_flow(username: str):
        password = "password123"
        # Register; it's fine if already exists (repeat runs)
        r = http.register(username, password)
        if r.status_code not in (201, 400):
            r.raise_for_status()
        created_user = r.status_code == 201
        token = http.login(username, password)

        created_ids: List[str] = []
        unfinished: List[str] = []
        finished: List[str] = []

        creates_remaining = todos_per_user
        finishes_remaining = todos_per_user

        # Choose a number of steps >= 2 * todos to allow random interleaving
        steps = 2 * todos_per_user
        for _ in range(steps):
            # Decide action: prefer create until quota hit, otherwise finish
            if creates_remaining > 0 and (not unfinished or random.random() < 0.6):
                # create
                text = f"todo for {username} #{todos_per_user - creates_remaining + 1}"
                item = http.create_todo(token, text)
                created_ids.append(item["id"])
                unfinished.append(item["id"])
                creates_remaining -= 1
            elif finishes_remaining > 0 and unfinished:
                # finish random unfinished
                tidx = random.randrange(0, len(unfinished))
                todo_id = unfinished.pop(tidx)
                item = http.finish_todo(token, todo_id)
                assert item["done"] is True
                finished.append(todo_id)
                finishes_remaining -= 1

            # small jitter to vary interleavings
            if random.random() < 0.5:
                time.sleep(random.uniform(0, 0.01))

        # If anything left unfinished due to randomness, finish them now
        while unfinished:
            todo_id = unfinished.pop()
            item = http.finish_todo(token, todo_id)
            assert item["done"] is True
            finished.append(todo_id)

        # Verify from the API
        items = http.list_todos(token)
        assert len(items) >= todos_per_user
        done_items = [i for i in items if i["done"]]
        # Some older runs might exist for same user; ensure the latest batch is done
        # We check that at least `todos_per_user` latest created items are done.
        # Sort by created_at descending and take our batch size
        items_sorted = sorted(items, key=lambda x: x["created_at"], reverse=True)
        recent = items_sorted[:todos_per_user]
        assert all(i["done"] for i in recent)

        return {
            "created": created_ids,
            "finished": finished,
            "created_user": created_user,
        }

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(run_user_flow, name): name for name in user_names}
        total_users_created = 0
        total_todos_created = 0
        total_completed = 0
        for fut in as_completed(futures):
            name = futures[fut]
            res = fut.result()
            results[name] = res
            total_users_created += 1 if res.get("created_user") else 0
            total_todos_created += len(res["created"])
            total_completed += len(res["finished"])
            logger.info(
                "User %s done: created=%d, completed=%d | progress users=%d/%d, total_created=%d, total_completed=%d",
                name,
                len(res["created"]),
                len(res["finished"]),
                len(results),
                total_users,
                total_todos_created,
                total_completed,
            )

    # Basic sanity across users
    assert len(results) == total_users
    for name, res in results.items():
        assert len(res["created"]) == todos_per_user
        assert len(res["finished"]) == todos_per_user

    # Summary logging
    total_created = sum(len(r["created"]) for r in results.values())
    total_finished = sum(len(r["finished"]) for r in results.values())
    total_users_created = sum(1 for r in results.values() if r.get("created_user"))
    logger.info(
        "Summary: users_created=%d/%d, todos_created=%d, todos_completed=%d",
        total_users_created,
        total_users,
        total_created,
        total_finished,
    )
