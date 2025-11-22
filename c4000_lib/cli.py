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

import argparse
import sys
import os
import traceback

from . import utils
from .core import ModemControl, ModemError
from .features.device_listing import DeviceListingFeature
from .features.url_blocking import URLBlockingFeature

def parse_rules_from_file(filename):
    """Parses a device,url file and returns a list of tuples."""
    rules = []
    if not os.path.exists(filename):
        print(f"Error: Rules file not found at '{filename}'", file=sys.stderr)
        return None
    with open(filename, 'r') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'): continue
            try:
                device, url = [item.strip() for item in line.split(',', 1)]
                rules.append((device, url))
            except ValueError:
                print(f"Warning: Skipping malformed line #{i} in '{filename}': {line}", file=sys.stderr)
    return rules

def main():
    """The main entry point for the CLI application."""
    parser = argparse.ArgumentParser(
        description="A CLI tool to control and query a C4000-series modem.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--modem", default=utils.get_default_gateway(), help="IP address of the modem. Defaults to your default gateway.")
    parser.add_argument("--debug", action="store_true", help="Enable detailed debug output.")
    parser.add_argument("--wait", action="store_true", help="Wait for user input before exiting.")
    parser.add_argument("--delay", type=float, default=2.0, help="Minimum interval between modem requests. Default: 2.0.")

    feature_subparsers = parser.add_subparsers(dest="feature", required=True, help="Feature to interact with.")

    parser_device = feature_subparsers.add_parser("device", help="Commands for listing network devices.")
    device_action_parsers = parser_device.add_subparsers(dest="action", required=True, help="Action for the 'device' feature.")
    device_action_parsers.add_parser("list", help="List all known devices on the network.")

    parser_url = feature_subparsers.add_parser("url", help="Commands for managing URL blocking rules.")
    url_action_parsers = parser_url.add_subparsers(dest="action", required=True, help="Action for the 'url' feature.")

    url_action_parsers.add_parser("list", help="List all currently active URL blocking rules.")

    parser_add = url_action_parsers.add_parser("add", help="Add new URL blocking rules.")
    add_group = parser_add.add_mutually_exclusive_group(required=True)
    add_group.add_argument("--device", help="Target device. Can be Hostname, IP, MAC, or 'all'.")
    add_group.add_argument("--rules-file", help="A file containing 'device,url' rules to add.")
    parser_add.add_argument("--block", action="append", help="URL to block (comma-separated or use flag multiple times).")

    parser_remove = url_action_parsers.add_parser("remove", help="Remove rules by matching device and URL.")
    remove_group = parser_remove.add_mutually_exclusive_group(required=True)
    remove_group.add_argument("--device", help="Target device. Can be Hostname, IP, MAC, or 'all'.")
    remove_group.add_argument("--rules-file", help="A file containing 'device,url' rules to remove.")
    parser_remove.add_argument("--block", action="append", help="URL to unblock (comma-separated or use flag multiple times).")

    parser_remove_id = url_action_parsers.add_parser("remove-id", help="Remove a specific rule by its ID number.")
    parser_remove_id.add_argument("rule_id", type=int, help="The numeric ID of the rule to remove (from url list).")

    url_action_parsers.add_parser("remove-all", help="Remove ALL URL blocking rules from the modem.")

    args = parser.parse_args()

    username, password = utils.load_credentials()
    if not (username and password):
        print("Username and password cannot be empty.", file=sys.stderr)
        sys.exit(1)

    # Pass the user's delay preference as the minimum safety interval
    control = ModemControl(args.modem, username, password, debug=args.debug, min_interval=args.delay)

    if not control.login():
        sys.exit(1)

    print("-" * 30)

    device_feature = DeviceListingFeature(control)
    url_feature = URLBlockingFeature(control, device_feature)

    try:
        if args.feature == 'device':
            if args.action == 'list':
                device_feature.list_devices(debug=args.debug)

        elif args.feature == 'url':
            if args.action == 'list':
                url_feature.list_rules(debug=args.debug)
            elif args.action == 'add':
                rules = []
                if args.rules_file:
                    rules = parse_rules_from_file(args.rules_file)
                    if rules is None: sys.exit(1)
                else:
                    if not args.block: print("Error: --block must be specified with --device.", file=sys.stderr); sys.exit(1)
                    domains = [d.strip() for item in args.block for d in item.split(',')]
                    rules = [(args.device, domain) for domain in domains]
                url_feature.add(rules)
            elif args.action == 'remove':
                rules = []
                if args.rules_file:
                    rules = parse_rules_from_file(args.rules_file)
                    if rules is None: sys.exit(1)
                else:
                    if not args.block: print("Error: --block must be specified with --device.", file=sys.stderr); sys.exit(1)
                    domains = [d.strip() for item in args.block for d in item.split(',')]
                    rules = [(args.device, domain) for domain in domains]
                url_feature.remove(rules)
            elif args.action == 'remove-id':
                url_feature.remove_by_id(args.rule_id)
            elif args.action == 'remove-all':
                url_feature.remove_all()

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        if args.debug:
            traceback.print_exc()

    print("-" * 30 + "\nScript finished.")
    if args.wait:
        input("Press Enter to exit...")
