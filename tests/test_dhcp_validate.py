from c4000_lib.features.dhcp import validate_request

POOL = ("192.0.2.10", "192.0.2.200")
GATEWAY = "192.0.2.1"
LEASES = [{"mac": "02:00:00:00:00:09", "ip": "192.0.2.80"}]

def ok(mac, ip):
    return validate_request(mac, ip, POOL, GATEWAY, LEASES)

def test_valid_request():
    assert ok("02:00:00:00:00:01", "192.0.2.50") == (True, None)

def test_bad_mac():
    good, err = ok("nope", "192.0.2.50")
    assert good is False and "MAC" in err

def test_bad_ip():
    good, err = ok("02:00:00:00:00:01", "999.1.1.1")
    assert good is False and "IP" in err

def test_out_of_pool():
    good, err = ok("02:00:00:00:00:01", "192.0.2.5")
    assert good is False and "pool" in err.lower()

def test_is_gateway():
    good, err = ok("02:00:00:00:00:01", "192.0.2.1")
    assert good is False and "gateway" in err.lower()

def test_ip_leased_to_other_mac():
    good, err = ok("02:00:00:00:00:01", "192.0.2.80")
    assert good is False and "in use" in err.lower()

def test_ip_leased_to_same_mac_is_ok():
    assert ok("02:00:00:00:00:09", "192.0.2.80") == (True, None)

def test_empty_pool_range_skips_bound_check():
    # when pool range is unknown (None, None), the in-pool check is skipped, not an error
    good, err = validate_request("02:00:00:00:00:01", "192.0.2.50", (None, None), GATEWAY, LEASES)
    assert good is True and err is None
