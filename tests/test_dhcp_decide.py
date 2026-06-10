from c4000_lib.features.dhcp import decide_action

R = [
    {"index": "1", "mac": "02:00:00:00:00:01", "ip": "192.0.2.50", "name": None, "enabled": True},
    {"index": "2", "mac": "02:00:00:00:00:02", "ip": "192.0.2.51", "name": None, "enabled": True},
]

def test_noop_when_already_correct():
    action, target = decide_action(R, "02:00:00:00:00:01", "192.0.2.50")
    assert action == "noop" and target["index"] == "1"

def test_add_when_absent():
    action, target = decide_action(R, "02:00:00:00:00:03", "192.0.2.52")
    assert action == "add" and target is None

def test_modify_when_mac_present_different_ip():
    action, target = decide_action(R, "02:00:00:00:00:01", "192.0.2.60")
    assert action == "modify" and target["index"] == "1"

def test_conflict_when_ip_held_by_other_mac():
    action, target = decide_action(R, "02:00:00:00:00:03", "192.0.2.50")
    assert action == "conflict" and target["mac"] == "02:00:00:00:00:01"

def test_modify_blocked_by_conflict():
    action, target = decide_action(R, "02:00:00:00:00:01", "192.0.2.51")
    assert action == "conflict" and target["mac"] == "02:00:00:00:00:02"

def test_disabled_same_ip_is_modify_not_noop():
    R2 = [{"index": "1", "mac": "02:00:00:00:00:01", "ip": "192.0.2.50", "name": None, "enabled": False}]
    action, target = decide_action(R2, "02:00:00:00:00:01", "192.0.2.50")
    assert action == "modify" and target["index"] == "1"
