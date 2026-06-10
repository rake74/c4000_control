from unittest.mock import MagicMock
from c4000_lib.utils import resolve_device_to_mac

DEVICES = [
    {"PhysAddress": "AA:BB:CC:DD:EE:01", "IPAddress": "192.0.2.50", "HostName": "camera-one"},
    {"PhysAddress": "AA:BB:CC:DD:EE:02", "IPAddress": "192.0.2.51", "HostName": "camera-two"},
]

def df():
    d = MagicMock()
    d.get_all.return_value = (DEVICES, None)
    return d

def test_resolve_by_hostname():
    assert resolve_device_to_mac(df(), "camera-two") == "AA:BB:CC:DD:EE:02"

def test_resolve_by_ip():
    assert resolve_device_to_mac(df(), "192.0.2.50") == "AA:BB:CC:DD:EE:01"

def test_resolve_by_mac_case_insensitive():
    assert resolve_device_to_mac(df(), "aa:bb:cc:dd:ee:01") == "AA:BB:CC:DD:EE:01"

def test_resolve_unknown_returns_none():
    assert resolve_device_to_mac(df(), "nope") is None
