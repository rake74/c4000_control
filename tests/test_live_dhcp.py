import os
import pytest
from c4000_lib import utils
from c4000_lib.core import ModemControl
from c4000_lib.features.device_listing import DeviceListingFeature
from c4000_lib.features.dhcp import DHCPReservationFeature

pytestmark = pytest.mark.skipif(os.getenv("C4000_LIVE_TEST") != "1",
                                reason="set C4000_LIVE_TEST=1 to run against a real modem")

THROWAWAY_MAC = "02:00:00:00:00:7e"

@pytest.fixture
def feature():
    modem = os.getenv("C4000_MODEM") or utils.get_default_gateway()
    user, pw = utils.load_credentials()
    control = ModemControl(modem, user, pw, debug=True, min_interval=2.0)
    assert control.login()
    return DHCPReservationFeature(control, DeviceListingFeature(control))

def test_reserve_change_and_remove(feature):
    ip1 = os.environ["C4000_TEST_IP1"]   # two free in-pool IPs supplied by the operator
    ip2 = os.environ["C4000_TEST_IP2"]
    try:
        assert feature.reserve(THROWAWAY_MAC, ip1) is True
        assert feature.reserve(THROWAWAY_MAC, ip2) is True   # in-place change
        assert any(r["ip"] == ip2 for r in feature.get_reservations())
    finally:
        feature.unreserve(mac=THROWAWAY_MAC)
    assert not any(r["mac"] == THROWAWAY_MAC for r in feature.get_reservations())
