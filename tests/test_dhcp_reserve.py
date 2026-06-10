from unittest.mock import MagicMock
from c4000_lib.features.dhcp import DHCPReservationFeature

EMPTY = {"Objects": []}
POOL = {"Objects": [{"ObjName": "Device.DHCPv4.Server.Pool.1.",
        "Param": [{"ParamName": "MinAddress", "ParamValue": "192.0.2.10"},
                  {"ParamName": "MaxAddress", "ParamValue": "192.0.2.200"}]}]}
LEASES = {"Objects": []}

def add_fixture(mac, ip):
    return {"Objects": [{"ObjName": "Device.DHCPv4.Server.Pool.1.StaticAddress.1.",
        "Param": [{"ParamName": "Chaddr", "ParamValue": mac},
                  {"ParamName": "Yiaddr", "ParamValue": ip},
                  {"ParamName": "Enable", "ParamValue": "true"}]}]}

def build(get_sequence):
    control = MagicMock()
    control.get_request.side_effect = get_sequence
    control.set_request.return_value = True
    feature = DHCPReservationFeature(control, MagicMock())
    feature._backup_or_abort = MagicMock(return_value=True)  # isolate from real backup
    return feature, control

def test_reserve_dry_run_writes_nothing():
    feature, control = build([EMPTY, POOL, LEASES])   # reads: reservations, pool, leases
    ok = feature.reserve("02:00:00:00:00:01", "192.0.2.50", dry_run=True)
    assert ok is True
    control.set_request.assert_not_called()
    feature._backup_or_abort.assert_not_called()

def test_reserve_add_then_verify():
    feature, control = build([
        EMPTY, POOL, LEASES,                                  # pre-write reads
        add_fixture("02:00:00:00:00:01", "192.0.2.50"),       # post-write verify read
    ])
    ok = feature.reserve("02:00:00:00:00:01", "192.0.2.50")
    assert ok is True
    assert control.set_request.call_count == 1
    payload = control.set_request.call_args[0][0]
    assert payload["Operation"] == "Add" and payload["Yiaddr"] == "192.0.2.50"

def test_reserve_aborts_on_failed_backup():
    feature, control = build([EMPTY, POOL, LEASES])
    feature._backup_or_abort = MagicMock(return_value=False)
    ok = feature.reserve("02:00:00:00:00:01", "192.0.2.50")
    assert ok is False
    control.set_request.assert_not_called()

def test_reserve_conflict_refuses():
    existing = add_fixture("02:00:00:00:00:09", "192.0.2.50")
    feature, control = build([existing, POOL, LEASES])
    ok = feature.reserve("02:00:00:00:00:01", "192.0.2.50")
    assert ok is False
    control.set_request.assert_not_called()

def test_reserve_add_failure_has_nothing_to_roll_back():
    feature, control = build([EMPTY, POOL, LEASES, EMPTY])  # post-write read still empty
    ok = feature.reserve("02:00:00:00:00:01", "192.0.2.50")
    assert ok is False
    ops = [c.args[0]["Operation"] for c in control.set_request.call_args_list]
    assert ops == ["Add"]

def test_reserve_modify_rolls_back_on_verify_fail():
    existing = add_fixture("02:00:00:00:00:01", "192.0.2.50")
    feature, control = build([existing, POOL, LEASES, existing])  # post-write read still .50
    ok = feature.reserve("02:00:00:00:00:01", "192.0.2.60")
    assert ok is False
    calls = control.set_request.call_args_list
    ops = [c.args[0]["Operation"] for c in calls]
    assert ops == ["Modify", "Modify"]
    assert calls[1].args[0]["Yiaddr"] == "192.0.2.50"  # prior IP restored

def test_reserve_modify_rollback_warns_when_instance_gone():
    existing = add_fixture("02:00:00:00:00:01", "192.0.2.50")
    feature, control = build([existing, POOL, LEASES, EMPTY])  # instance vanished post-write
    ok = feature.reserve("02:00:00:00:00:01", "192.0.2.60")
    assert ok is False
    ops = [c.args[0]["Operation"] for c in control.set_request.call_args_list]
    assert ops == ["Modify"]   # forward modify only; no rollback write to a vanished index
