from c4000_lib.features.dhcp import parse_reservations

def test_parse_reservations(fixtures):
    raw = fixtures("static_address.json")
    res = parse_reservations(raw)
    assert res == [
        {"index": "1", "mac": "02:00:00:00:00:01", "ip": "192.0.2.50", "name": "camera-one", "enabled": True},
        {"index": "2", "mac": "02:00:00:00:00:02", "ip": "192.0.2.51", "name": "camera-two", "enabled": True},
    ]

def test_parse_reservations_empty():
    assert parse_reservations({"Objects": []}) == []
