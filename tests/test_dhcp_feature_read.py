from unittest.mock import MagicMock
from c4000_lib.features.dhcp import DHCPReservationFeature


def make_feature(static_raw):
    control = MagicMock()
    control.get_request.return_value = static_raw
    device_feature = MagicMock()
    return DHCPReservationFeature(control, device_feature), control


def test_get_reservations(fixtures):
    feature, _ = make_feature(fixtures("static_address.json"))
    res = feature.get_reservations()
    assert [r["ip"] for r in res] == ["192.0.2.50", "192.0.2.51"]
