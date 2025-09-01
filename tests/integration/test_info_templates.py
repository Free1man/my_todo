# tests/integration/test_info_templates.py
import requests

def _get(url): r = requests.get(url, timeout=5); r.raise_for_status(); return r.json()
def _post(url, body): r = requests.post(url, json=body, timeout=5); r.raise_for_status(); return r.json()

def test_defaults_info(base_url: str):
    info = _get(f"{base_url}/info")
    mv_ex = info["actions"]["move"]["example"]
    assert mv_ex["kind"] == "MOVE" and "unit_id" in mv_ex and "to" in mv_ex

def test_info_examples_are_directly_usable(base_url: str):
    # Create a session using default demo mission
    s = _post(f"{base_url}/sessions", {})
    info = _get(f"{base_url}/info")

    # use the move example from /info, just fill an existing unit id
    sess = _get(f"{base_url}/sessions/{s['id']}")
    any_uid = next(iter(sess["mission"]["units"].keys()))
    move = info["actions"]["move"]["example"]
    move["unit_id"] = any_uid
    move["to"] = [0, 1]

    r = requests.post(f"{base_url}/sessions/{s['id']}/evaluate", json={"action": move}, timeout=5)
    assert r.status_code == 200
