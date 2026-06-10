#!/usr/bin/env python3
"""One-shot recon: dump candidate DHCP objects from a live C4000."""
import json, sys
from c4000_lib import utils
from c4000_lib.core import ModemControl, ModemError

CANDIDATES = [
    "Device.DHCPv4.Server.Pool.1.StaticAddress",
    "Device.DHCPv4.Server.Pool.1",
    "Device.DHCPv4.Server.Pool.1.Client",
    "Device.DHCPv4.Server.Pool",
    "Device.Hosts.Host",
]

def main():
    modem = sys.argv[1] if len(sys.argv) > 1 else utils.get_default_gateway()
    username, password = utils.load_credentials()
    control = ModemControl(modem, username, password, debug=True, min_interval=2.0)
    if not control.login():
        print("Login failed", file=sys.stderr); sys.exit(1)
    for obj in CANDIDATES:
        print(f"\n===== {obj} =====")
        try:
            print(json.dumps(control.get_request(obj), indent=2))
        except (ModemError, ValueError) as e:
            print(f"  ERROR: {e}")

if __name__ == "__main__":
    main()
