from __future__ import annotations
import os
import time
from typing import Optional, List
from redis import Redis
from pydantic import TypeAdapter
from .models.tbs import TBSSession  # adjust import if needed

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "50"))
EVICT_ON_GET = os.getenv("EVICT_ON_GET", "true").lower() != "false"

r = Redis.from_url(REDIS_URL, decode_responses=True)

INDEX = "sess:index"  # sorted-set: member=sid, score=last touch (unix seconds)


def _k(sid: str) -> str:
    return f"sess:{sid}"


def _touch(sid: str) -> None:
    # update "last used" timestamp
    r.zadd(INDEX, {sid: time.time()})


def _enforce_cap() -> None:
    # if over cap, evict the least-recently-used sessions
    count = r.zcard(INDEX)
    if count <= MAX_SESSIONS:
        return
    n_evict = count - MAX_SESSIONS
    # ZPOPMIN with count returns [(sid, score), ...] oldest first
    evicted = r.zpopmin(INDEX, n_evict)
    if not evicted:
        return
    pipe = r.pipeline()
    for sid, _ in evicted:
        pipe.delete(_k(sid))
    pipe.execute()


def save(sess: TBSSession) -> None:
    # write payload
    r.set(_k(sess.id), sess.model_dump_json())
    # index/update recency and enforce cap
    _touch(sess.id)
    _enforce_cap()


def get(sid: str) -> Optional[TBSSession]:
    raw = r.get(_k(sid))
    if raw is None:
        # cleanup stale index entry if it exists
        r.zrem(INDEX, sid)
        return None
    if EVICT_ON_GET:
        _touch(sid)  # makes policy LRU
        _enforce_cap()  # optional; cheap and keeps things tidy
    return TypeAdapter(TBSSession).validate_json(raw)


def delete(sid: str) -> bool:
    pipe = r.pipeline()
    pipe.delete(_k(sid))
    pipe.zrem(INDEX, sid)
    res = pipe.execute()
    # res[0] is DEL result (0/1)
    return bool(res and res[0])


def list_all() -> List[TBSSession]:
    sids = r.zrevrange(INDEX, 0, -1)
    if not sids:
        return []
    raw_sessions = r.mget([_k(sid) for sid in sids])
    sessions = []
    stale_sids = []
    for i, raw in enumerate(raw_sessions):
        if raw:
            sessions.append(TypeAdapter(TBSSession).validate_json(raw))
        else:
            stale_sids.append(sids[i])

    if stale_sids:
        r.zrem(INDEX, *stale_sids)

    return sessions
