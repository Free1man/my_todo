import requests


def test_tbs_basic_flow(base_url: str):
    # Create a TBS session
    r = requests.post(f"{base_url}/sessions", json={"ruleset": "tbs"}, timeout=5)
    r.raise_for_status()
    sess = r.json()

    sid = sess["id"]
    state = sess["state"]
    active = state["turn_order"][state["active_index"]]
    u = state["units"][active]
    # Try a move evaluate
    to = {"x": u["pos"]["x"], "y": u["pos"]["y"] + 1}
    r = requests.post(f"{base_url}/sessions/{sid}/evaluate", json={"type":"move", "unit_id": active, "to": to}, timeout=5)
    r.raise_for_status()
    ex = r.json()
    assert ex["ok"]

    # Apply the move
    r = requests.post(f"{base_url}/sessions/{sid}/action", json={"type":"move", "unit_id": active, "to": to}, timeout=5)
    r.raise_for_status()
    sess = r.json()
    assert sess["state"]["units"][active]["pos"] == to
