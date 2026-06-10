from unittest.mock import MagicMock
from c4000_lib.features.dhcp import DHCPReservationFeature

def one(mac, ip):
    return {"Objects": [{"ObjName": "Device.DHCPv4.Server.Pool.1.StaticAddress.1.",
        "Param": [{"ParamName": "Chaddr", "ParamValue": mac},
                  {"ParamName": "Yiaddr", "ParamValue": ip},
                  {"ParamName": "Enable", "ParamValue": "true"}]}]}

def build(seq):
    control = MagicMock()
    control.get_request.side_effect = seq
    control.set_request.return_value = True
    feature = DHCPReservationFeature(control, MagicMock())
    feature._backup_or_abort = MagicMock(return_value=True)
    return feature, control

def test_unreserve_by_mac():
    feature, control = build([one("02:00:00:00:00:01", "192.0.2.50"),
                              {"Objects": []}])  # verify gone
    ok = feature.unreserve(mac="02:00:00:00:00:01")
    assert ok is True
    assert control.set_request.call_args[0][0]["Operation"] == "Del"

def test_unreserve_absent_is_ok():
    feature, control = build([{"Objects": []}])
    ok = feature.unreserve(ip="192.0.2.99")
    assert ok is True
    control.set_request.assert_not_called()

def test_unreserve_dry_run():
    feature, control = build([one("02:00:00:00:00:01", "192.0.2.50")])
    ok = feature.unreserve(mac="02:00:00:00:00:01", dry_run=True)
    assert ok is True
    control.set_request.assert_not_called()
