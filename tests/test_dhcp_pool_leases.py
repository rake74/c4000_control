from c4000_lib.features.dhcp import parse_pool_range, parse_leases

def test_parse_pool_range(fixtures):
    assert parse_pool_range(fixtures("pool.json")) == ("192.0.2.10", "192.0.2.200")

def test_parse_leases(fixtures):
    assert parse_leases(fixtures("leases.json")) == [
        {"mac": "02:00:00:00:00:09", "ip": "192.0.2.80"},
    ]
