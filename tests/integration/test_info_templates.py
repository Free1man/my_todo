# tests/integration/test_info_templates.py
import requests

def _get(url): r = requests.get(url, timeout=5); r.raise_for_status(); return r.json()
def _post(url, body): r = requests.post(url, json=body, timeout=5); r.raise_for_status(); return r.json()

def test_ruleset_tbs_info(base_url: str):
    info = _get(f"{base_url}/rulesets/tbs/info")
    assert info["ruleset"] == "tbs"
    mv_tpl = info["actions"]["move"]["template"]
    assert mv_tpl["type"] == "move" and "unit_id" in mv_tpl and "to" in mv_tpl

def test_ruleset_chess_info(base_url: str):
    info = _get(f"{base_url}/rulesets/chess/info")
    assert info["ruleset"] == "chess"
    mv_tpl = info["actions"]["move"]["template"]
    assert mv_tpl["type"] == "move" and "src" in mv_tpl and "dst" in mv_tpl

def test_session_info_examples_are_directly_usable(base_url: str):
    s = _post(f"{base_url}/sessions", {"ruleset": "tbs", "map": {"width": 3, "height": 3}})
    i = _get(f"{base_url}/sessions/{s['id']}/info")

    # use the move template, just fill an existing unit id
    sess = _get(f"{base_url}/sessions/{s['id']}")
    any_uid = next(iter(sess["state"]["units"].keys()))
    move = i["actions"]["move"]["template"]
    move["unit_id"] = any_uid
    move["to"] = {"x": 0, "y": 1}

    r = requests.post(f"{base_url}/sessions/{s['id']}/evaluate", json=move, timeout=5)
    assert r.status_code == 200
