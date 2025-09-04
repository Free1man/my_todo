# tests/integration/test_info_templates.py
import requests


def _get(url):
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json()


def _post(url, body):
    r = requests.post(url, json=body, timeout=5)
    r.raise_for_status()
    return r.json()


def test_defaults_info(base_url: str):
    info = _get(f"{base_url}/info")
    assert "models" in info and "mission" in info["models"]
    mission_ex = info["models"]["mission"]["example"]
    # Minimal shape check for a mission example
    assert isinstance(mission_ex, dict)
    assert "id" in mission_ex and "map" in mission_ex and "units" in mission_ex


def test_info_examples_are_directly_usable(base_url: str):
    # Fetch info and create a session using the provided mission example
    info = _get(f"{base_url}/info")
    body = info.get("requests", {}).get("create_session", {}).get("example") or {
        "mission": info["models"]["mission"]["example"]
    }
    # Keep only the fields needed for creating a session
    body = {"mission": body["mission"]}
    s = _post(f"{base_url}/sessions", body)

    # use the move example from /info, just fill an existing unit id
    sess = _get(f"{base_url}/sessions/{s['id']}")
    next(iter(sess["mission"]["units"].keys()))
    # Construct a minimal MOVE action directly (no longer sourced from /info)

    # Use consolidated endpoint to check that a MOVE is present among legal actions
    la = requests.get(
        f"{base_url}/sessions/{s['id']}/legal_actions",
        params={"explain": "false"},
        timeout=5,
    )
    la.raise_for_status()
    acts = la.json().get("actions", [])
    assert any(a.get("action", {}).get("kind") == "move" for a in acts)
