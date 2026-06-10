import pytest
from c4000_lib.features.dhcp import normalize_mac

@pytest.mark.parametrize("raw,expected", [
    ("AA:BB:CC:DD:EE:FF", "aa:bb:cc:dd:ee:ff"),
    ("aa-bb-cc-dd-ee-ff", "aa:bb:cc:dd:ee:ff"),
    ("AABBCCDDEEFF",      "aa:bb:cc:dd:ee:ff"),
    ("aa:bb:cc:dd:ee:ff", "aa:bb:cc:dd:ee:ff"),
])
def test_normalize_mac_valid(raw, expected):
    assert normalize_mac(raw) == expected

@pytest.mark.parametrize("bad", ["", "xyz", "AA:BB:CC", "GG:HH:II:JJ:KK:LL", "AABBCCDDEE"])
def test_normalize_mac_invalid(bad):
    with pytest.raises(ValueError):
        normalize_mac(bad)
