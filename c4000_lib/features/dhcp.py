# MIT License
#
# Copyright (c) [Year] [Your Name or Handle]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# DHCP static-reservation management for the CenturyLink C4000.
# Schema confirmed against a live device on 2026-06-10; see
# docs/superpowers/specs/2026-06-10-discovery-findings.md.

import ipaddress
import re
import sys

from ..core import ModemError

# --- Discovery-confirmed schema ---
STATIC_ADDRESS_OBJECT = "Device.DHCPv4.Server.Pool.1.StaticAddress"  # parent of .{i} instances
PARAM_MAC     = "Chaddr"   # reservation MAC field
PARAM_IP      = "Yiaddr"   # reservation IP field
PARAM_ENABLE  = "Enable"
PARAM_NAME    = "X_GWS_HostName"   # read-only: shown in `dhcp list`; never written (add/modify payloads omit it)

SUPPORTS_MODIFY = True     # device accepts Operation=Modify on a StaticAddress instance

POOL_OBJECT     = "Device.DHCPv4.Server.Pool.1"   # holds MinAddress/MaxAddress/IPRouters
POOL_MIN_PARAM  = "MinAddress"
POOL_MAX_PARAM  = "MaxAddress"
POOL_GATEWAY_PARAM = "IPRouters"

LEASE_OBJECT    = "Device.DHCPv4.Server.Pool.1.Client"  # active leases (.{i} instances)
LEASE_MAC_PARAM = "Chaddr"        # on Client.{i}.
LEASE_IP_PARAM  = "IPAddress"     # nested on Client.{i}.IPv4Address.{j}.

_HEX12 = re.compile(r"^[0-9a-f]{12}$")

def normalize_mac(raw):
    """Return MAC as lowercase colon-separated. Raise ValueError if not 12 hex digits."""
    if raw is None:
        raise ValueError("MAC is empty")
    stripped = re.sub(r"[^0-9a-fA-F]", "", raw).lower()
    if not _HEX12.match(stripped):
        raise ValueError(f"Invalid MAC address: {raw!r}")
    return ":".join(stripped[i:i+2] for i in range(0, 12, 2))

def _params(item):
    """Return {ParamName: ParamValue} for one Objects[] entry."""
    return {p.get("ParamName"): p.get("ParamValue") for p in item.get("Param", [])}

def parse_reservations(raw):
    """Parse a StaticAddress get_request response into reservation dicts."""
    out = []
    for item in raw.get("Objects", []):
        name = item.get("ObjName", "")
        if "StaticAddress." not in name:
            continue
        parts = name.rstrip(".").split(".")
        index = parts[-1]
        if not index.isdigit():
            continue
        p = _params(item)
        if p.get(PARAM_MAC) is None and p.get(PARAM_IP) is None:
            continue
        out.append({
            "index": index,
            "mac": normalize_mac(p[PARAM_MAC]) if p.get(PARAM_MAC) else "",
            "ip": p.get(PARAM_IP, ""),
            "name": p.get(PARAM_NAME) if PARAM_NAME else None,
            "enabled": str(p.get(PARAM_ENABLE, "")).lower() in ("true", "1"),
        })
    return out

def parse_pool_range(raw):
    """Return (min_ip, max_ip) strings for the DHCP pool."""
    for item in raw.get("Objects", []):
        p = _params(item)
        if POOL_MIN_PARAM in p and POOL_MAX_PARAM in p:
            return p[POOL_MIN_PARAM], p[POOL_MAX_PARAM]
    return None, None

def parse_leases(raw):
    """Return [{'mac','ip'}] for active leases.
    The C4000 nests the lease IP under Client.{n}.IPv4Address.{m}, so the MAC
    (on Client.{n}.) and IP (on the nested object) are correlated by client index n."""
    macs, ips = {}, {}
    for item in raw.get("Objects", []):
        m = re.match(r".*\.Client\.(\d+)\.(IPv4Address\.\d+\.)?$", item.get("ObjName", ""))
        if not m:
            continue
        cidx, is_nested = m.group(1), m.group(2)
        p = _params(item)
        if is_nested:
            if p.get(LEASE_IP_PARAM):
                ips[cidx] = p[LEASE_IP_PARAM]
        elif p.get(LEASE_MAC_PARAM):
            macs[cidx] = p[LEASE_MAC_PARAM]
    return [{"mac": normalize_mac(mac), "ip": ips[cidx]}
            for cidx, mac in macs.items() if cidx in ips]

def validate_request(mac, ip, pool_range, gateway, leases):
    """Return (ok, error). Validates syntax, pool membership, gateway, lease conflicts."""
    try:
        norm_mac = normalize_mac(mac)
    except ValueError as e:
        return False, str(e)
    try:
        addr = ipaddress.IPv4Address(ip)
    except (ipaddress.AddressValueError, ValueError):
        return False, f"Invalid IP address: {ip!r}"
    if gateway and addr == ipaddress.IPv4Address(gateway):
        return False, f"IP {ip} is the gateway address."
    pmin, pmax = pool_range
    if pmin and pmax:
        if not (ipaddress.IPv4Address(pmin) <= addr <= ipaddress.IPv4Address(pmax)):
            return False, f"IP {ip} is outside the DHCP pool {pmin}-{pmax}."
    for lease in leases:
        if lease["ip"] == ip and lease["mac"] != norm_mac:
            return False, f"IP {ip} is in use by another device ({lease['mac']})."
    return True, None

def decide_action(reservations, mac, ip):
    """Return (action, target). action in {noop, add, modify, conflict}.
    Resolves by MAC; refuses if the IP belongs to a different MAC."""
    norm_mac = normalize_mac(mac)
    by_mac = {r["mac"]: r for r in reservations}
    by_ip = {r["ip"]: r for r in reservations}
    ip_owner = by_ip.get(ip)
    if ip_owner and ip_owner["mac"] != norm_mac:
        return "conflict", ip_owner
    if norm_mac in by_mac:
        current = by_mac[norm_mac]
        if current["ip"] == ip and current["enabled"]:
            return "noop", current
        return "modify", current
    return "add", None


def _add_payload(mac, ip):
    return {"Object": STATIC_ADDRESS_OBJECT, "Operation": "Add",
            PARAM_MAC: mac, PARAM_IP: ip, PARAM_ENABLE: "true"}

def _modify_payload(index, ip):
    return {"Object": f"{STATIC_ADDRESS_OBJECT}.{index}.", "Operation": "Modify", PARAM_IP: ip, PARAM_ENABLE: "true"}

def _del_payload(index):
    return {"Object": f"{STATIC_ADDRESS_OBJECT}.{index}.", "Operation": "Del"}

def parse_gateway(raw):
    """Return the LAN gateway IP (IPRouters) from the pool object, or None."""
    for item in raw.get("Objects", []):
        p = _params(item)
        if POOL_GATEWAY_PARAM in p:
            return p[POOL_GATEWAY_PARAM]
    return None


class DHCPReservationFeature:
    """Manage DHCP static reservations on a C4000."""

    def __init__(self, control, device_feature):
        self.control = control
        self.device_feature = device_feature

    def get_reservations(self):
        raw = self.control.get_request(STATIC_ADDRESS_OBJECT)
        return parse_reservations(raw)

    def get_pool_range(self):
        return parse_pool_range(self.control.get_request(POOL_OBJECT))

    def get_active_leases(self):
        return parse_leases(self.control.get_request(LEASE_OBJECT))

    def list_reservations(self, debug=False):
        try:
            res = self.get_reservations()
        except (ModemError, ValueError) as e:
            print(f"Failed to list reservations: {e}", file=sys.stderr)
            return
        if not res:
            print("No DHCP reservations are configured.")
            return
        print(f"{'IP':<16} {'MAC':<18} {'Name'}")
        print(f"{'-'*16} {'-'*18} {'-'*10}")
        for r in res:
            print(f"{r['ip']:<16} {r['mac']:<18} {r['name'] or ''}")

    def _backup_or_abort(self, do_backup):
        if not do_backup:
            return True
        from .config import ConfigFeature
        path = ConfigFeature(self.control).backup()
        if not path:
            print("Aborting: configuration backup did not complete.", file=sys.stderr)
            return False
        return True

    def reserve(self, mac, ip, dry_run=False, backup=True):
        try:
            norm_mac = normalize_mac(mac)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return False
        try:
            reservations = self.get_reservations()
            pool_raw = self.control.get_request(POOL_OBJECT)
            pool = parse_pool_range(pool_raw)
            gateway = parse_gateway(pool_raw)
            leases = self.get_active_leases()
        except (ModemError, ValueError) as e:
            print(f"Error reading modem state: {e}", file=sys.stderr)
            return False

        valid, err = validate_request(norm_mac, ip, pool, gateway, leases)
        if not valid:
            print(f"Refused: {err}", file=sys.stderr)
            return False

        action, target = decide_action(reservations, norm_mac, ip)
        if action == "noop":
            print(f"OK: {norm_mac} is already reserved to {ip}.")
            return True
        if action == "conflict":
            print(f"Refused: {ip} is already reserved to {target['mac']}.", file=sys.stderr)
            return False

        if action == "add":
            payload, prior = _add_payload(norm_mac, ip), None
        else:  # modify
            payload, prior = _modify_payload(target["index"], ip), target

        if dry_run:
            print(f"[dry-run] would send: {payload}")
            return True

        if not self._backup_or_abort(backup):
            return False

        self.control.set_request(payload)
        after = self.get_reservations()   # single post-write read used for verify AND rollback
        if any(r["mac"] == norm_mac and r["ip"] == ip for r in after):
            print(f"OK: reserved {norm_mac} -> {ip}.")
            return True

        print("Write did not verify; attempting rollback.", file=sys.stderr)
        if action == "modify":
            # re-resolve from the post-write read; never trust a stale index
            cur = next((r for r in after if r["mac"] == norm_mac), None)
            if cur:
                self.control.set_request(_modify_payload(cur["index"], prior["ip"]))
            else:
                print(f"WARNING: {norm_mac} not found after a failed write; could not restore "
                      f"its prior IP {prior['ip']}.", file=sys.stderr)
        else:  # add: delete any partial entry that landed for this MAC (none if the add simply failed)
            partial = next((r for r in after if r["mac"] == norm_mac), None)
            if partial:
                self.control.set_request(_del_payload(partial["index"]))
        # set_request cannot report write failure on this device, so advise an explicit re-check
        print(f"Reservation for {norm_mac} may be in an inconsistent state; "
              f"verify with 'dhcp list'.", file=sys.stderr)
        return False

    def unreserve(self, mac=None, ip=None, dry_run=False, backup=True):
        if not mac and not ip:
            print("Error: specify --mac or --ip.", file=sys.stderr)
            return False
        norm_mac = normalize_mac(mac) if mac else None
        try:
            reservations = self.get_reservations()
        except (ModemError, ValueError) as e:
            print(f"Error reading modem state: {e}", file=sys.stderr)
            return False
        target = next((r for r in reservations
                       if (norm_mac and r["mac"] == norm_mac) or (ip and r["ip"] == ip)), None)
        if not target:
            print("OK: no matching reservation (nothing to remove).")
            return True
        payload = _del_payload(target["index"])
        if dry_run:
            print(f"[dry-run] would send: {payload}")
            return True
        if not self._backup_or_abort(backup):
            return False
        self.control.set_request(payload)
        still = next((r for r in self.get_reservations() if r["mac"] == target["mac"]), None)
        if still is None:
            print(f"OK: removed reservation for {target['mac']} ({target['ip']}).")
            return True
        print("Removal did not verify.", file=sys.stderr)
        return False
