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

import json
import time
import sys
from urllib.parse import unquote
from ..core import ModemError

MAX_RETRIES = 3

class URLBlockingFeature:
    """Handles all logic for URL blocking rules using state enforcement."""
    def __init__(self, control, device_feature):
        self.control = control
        self.device_feature = device_feature

    def get_rules(self):
        """
        Fetches and parses all URL filtering rules.
        Returns: (list of rules, raw_data)
        Raises: ModemError if fetching fails.
        """
        self.control._log("Querying modem for current rules...")
        raw_data = self.control.get_request('Device.Firewall.X_LANTIQ_COM_URLFilter')

        rules_list = []
        for item in raw_data.get('Objects', []):
            if "Rule" in item.get('ObjName', ''):
                try:
                    rule_num = item['ObjName'].split('.')[-2]
                    rule_info = {'rule_num': rule_num}
                    for param in item.get('Param', []):
                        if param.get('ParamName') == 'URL':
                            # Normalize URL for comparison
                            raw_url = unquote(param.get('ParamValue', ''))
                            clean_url = raw_url.replace('http://', '').replace('\\', '')
                            rule_info['url'] = clean_url
                        elif param.get('ParamName') == 'MACAddress':
                            rule_info['mac'] = param.get('ParamValue', '')

                    if rule_info.get('url'):
                        rules_list.append(rule_info)
                except (IndexError, KeyError):
                    continue

        self.control._log(f"Parsed {len(rules_list)} rules.")
        return rules_list, raw_data

    def _resolve_device_to_mac(self, device_identifier):
        if device_identifier.lower() == 'all':
            return ""

        devices, _ = self.device_feature.get_all() # May raise ModemError

        identifier_lower = device_identifier.lower()
        for device in devices:
            mac = device.get('PhysAddress', '')
            ip = device.get('IPAddress', '')
            name = device.get('HostName', '')
            if (mac and mac.lower() == identifier_lower) or \
               (ip and ip.lower() == identifier_lower) or \
               (name and name.lower() == identifier_lower):
                return mac

        print(f"Error: Could not find any device matching '{device_identifier}'.", file=sys.stderr)
        return None

    def list_rules(self, debug=False):
        """Prints a formatted list of URL blocking rules."""
        try:
            rules_list, raw_data = self.get_rules()
            devices, _ = self.device_feature.get_all()
            device_lookup = {dev['PhysAddress']: dev for dev in devices if dev.get('PhysAddress')} if devices else {}

            if debug:
                print("--- Raw Modem Response ---", file=sys.stderr)
                print(json.dumps(raw_data, indent=2), file=sys.stderr)
                print("--- End Raw Response ---\n", file=sys.stderr)

            if rules_list:
                print(f"{'Rule #':<8} {'Applied To':<40} {'Blocked URL'}")
                print(f"{'-'*8} {'-'*40} {'-'*20}")
                for rule in rules_list:
                    mac = rule.get('mac')
                    device_str = "Unknown"
                    if not mac:
                        device_str = "All LAN Devices"
                    elif mac in device_lookup:
                        dev = device_lookup[mac]
                        device_str = f"{dev.get('HostName', 'N/A')} ({dev.get('IPAddress', 'N/A')})"
                    else:
                        device_str = mac
                    print(f"{rule['rule_num']:<8} {device_str:<40} {rule['url']}")
            else:
                print("No URL filtering rules are currently configured.")
        except ModemError as e:
            print(f"Failed to list rules: {e}", file=sys.stderr)

    def _ensure_rule_state(self, domain, mac_address, desired_state):
        """
        Idempotent function to ensure a rule exists or is removed.
        desired_state: 'present' or 'absent'
        """
        action_desc = "ADD" if desired_state == 'present' else "REMOVE"
        target_desc = f"'{domain}'"

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # 1. Get Current State
                rules, _ = self.get_rules()

                # Find matching rules (could be multiple due to previous errors)
                matching_rules = [r for r in rules if r['url'] == domain and r.get('mac') == mac_address]

                # 2. Check if action is needed
                if desired_state == 'present':
                    if len(matching_rules) == 1:
                        msg = "OK: Rule already exists." if attempt == 1 else "Success: Rule verified present after retry."
                        print(f"{msg}")
                        return True
                    elif len(matching_rules) > 1:
                        print(f"Notice: Found {len(matching_rules)} duplicate rules for {target_desc}. Cleaning up...")
                        # Remove all but the first one
                        for rule in matching_rules[1:]:
                            self.remove_by_id(rule['rule_num'])
                        return True

                elif desired_state == 'absent':
                    if not matching_rules:
                        msg = "OK: Rule is not present." if attempt == 1 else "Success: Rule verified removed after retry."
                        print(f"{msg}")
                        return True

                # 3. Perform Action
                print(f"Attempting to {action_desc} rule {target_desc} (Attempt {attempt})...")

                if desired_state == 'present':
                    payload = {
                        'Object': 'Device.Firewall.X_LANTIQ_COM_URLFilter.Rule',
                        'Operation': 'Add',
                        'URL': f"http://{domain}",
                        'MACAddress': mac_address
                    }
                    self.control.set_request(payload)
                else:
                    # For removal, take the FIRST match and delete it.
                    # If duplicates exist, the outer loop/verification will catch them on the next pass.
                    rule_id = matching_rules[0]['rule_num']
                    self.remove_by_id(rule_id)

            except ModemError as e:
                print(f"Modem error during {action_desc}: {e}", file=sys.stderr)
                time.sleep(2.0) # Extra backoff

        print(f"FAILURE: Could not {action_desc} rule {target_desc} after {MAX_RETRIES} attempts.", file=sys.stderr)
        return False

    def add(self, rules_to_add, **kwargs):
        """Iterates through rules and ensures they exist."""
        unique_device_ids = {device_id for device_id, domain in rules_to_add}
        mac_cache = {}

        try:
            for uid in unique_device_ids:
                mac = self._resolve_device_to_mac(uid)
                if mac is not None:
                    mac_cache[uid] = mac
        except ModemError as e:
            print(f"Fatal error resolving devices: {e}", file=sys.stderr)
            return

        for device_id, domain in rules_to_add:
            mac_address = mac_cache.get(device_id)
            if mac_address is None:
                print(f"Skipping rule for unresolved device '{device_id}'.")
                continue

            self._ensure_rule_state(domain, mac_address, 'present')

    def remove(self, rules_to_remove, **kwargs):
        """Iterates through rules and ensures they are removed."""
        unique_device_ids = {device_id for device_id, domain in rules_to_remove}
        mac_cache = {}

        try:
            for uid in unique_device_ids:
                mac = self._resolve_device_to_mac(uid)
                if mac is not None:
                    mac_cache[uid] = mac
        except ModemError as e:
            print(f"Fatal error resolving devices: {e}", file=sys.stderr)
            return

        for device_id, domain in rules_to_remove:
            mac_address = mac_cache.get(device_id)
            if mac_address is None:
                print(f"Skipping rule removal for unresolved device '{device_id}'.")
                continue

            self._ensure_rule_state(domain, mac_address, 'absent')

    def remove_by_id(self, rule_id, **kwargs):
        """
        Removes a single rule by its ID number and verifies removal.
        Returns True if successful, False if failed (Ghost Rule).
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Verify existence first
                rules, _ = self.get_rules()
                target_rule = next((r for r in rules if r['rule_num'] == str(rule_id)), None)

                if not target_rule:
                    print(f"Rule #{rule_id} is gone.")
                    return True

                print(f"Sending request to REMOVE Rule #{rule_id} (Attempt {attempt})...")
                payload = {'Object': f"Device.Firewall.X_LANTIQ_COM_URLFilter.Rule.{rule_id}.", 'Operation': 'Del'}
                self.control.set_request(payload)

            except ModemError as e:
                print(f"Error removing rule #{rule_id}: {e}", file=sys.stderr)

        print(f"Failed to verify removal of Rule #{rule_id} after multiple attempts.", file=sys.stderr)
        return False

    def remove_all(self, **kwargs):
        """Removes all URL blocking rules safely, skipping stuck rules."""
        stuck_rules = set()

        try:
            while True:
                rules_list, _ = self.get_rules()

                # Filter out known stuck rules so we don't loop infinitely
                actionable_rules = [r for r in rules_list if r['rule_num'] not in stuck_rules]

                if not actionable_rules:
                    if stuck_rules:
                        print(f"Warning: {len(stuck_rules)} ghost rules could not be removed and were skipped.")
                        print(f"Stuck Rule IDs: {stuck_rules}")
                    else:
                        print("No rules remaining.")
                    break

                print(f"Remaining rules: {len(actionable_rules)}. Processing next batch...")

                # Take the first actionable rule
                rule = actionable_rules[0]
                rule_id = rule['rule_num']

                print(f"Targeting Rule #{rule_id} ({rule.get('url', 'Unknown')})...")

                success = self.remove_by_id(rule_id)

                if not success:
                    print(f"Marking Rule #{rule_id} as stuck/ghost. Skipping.")
                    stuck_rules.add(rule_id)
                else:
                    # Allow a slight breather between successful deletes
                    time.sleep(1.0)

            print("Remove all operation complete.")
        except ModemError as e:
            print(f"Error during bulk removal: {e}", file=sys.stderr)
