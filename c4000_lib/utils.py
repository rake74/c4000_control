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

import os
import getpass
import socket
import sys

try:
    import netifaces
except ImportError:
    netifaces = None

FALLBACK_MODEM_IP = "192.168.0.1"

def get_default_gateway():
    """Tries to find the default gateway, with smart fallbacks."""
    if netifaces:
        try:
            gws = netifaces.gateways()
            return gws['default'][netifaces.AF_INET][0]
        except (KeyError, IndexError):
            pass
    try:
        host_ip = socket.gethostbyname(socket.gethostname())
        if host_ip and not host_ip.startswith("127."):
            ip_parts = host_ip.split('.')
            gateway_ip = '.'.join(ip_parts[:3] + ['1'])
            print(f"Warning: Could not determine default gateway. Guessing based on host IP: {gateway_ip}", file=sys.stderr)
            return gateway_ip
    except socket.gaierror:
        pass
    print(f"Warning: All gateway detection methods failed. Using hardcoded fallback: {FALLBACK_MODEM_IP}", file=sys.stderr)
    return FALLBACK_MODEM_IP

def load_credentials(creds_file="c4000_control.creds"):
    """Loads credentials from ENV, a file, or prompts the user."""
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    if username and password:
        print("Using credentials from environment variables.")
        return username, password
    if os.path.exists(creds_file):
        print(f"Reading credentials from {creds_file}...")
        creds = {}
        with open(creds_file, 'r') as f:
            for line in f:
                if line.strip() and not line.strip().startswith('#'):
                    try:
                        key, value = line.split('=', 1)
                        creds[key.strip().upper()] = value.strip()
                    except ValueError:
                        continue
        username, password = creds.get("USERNAME"), creds.get("PASSWORD")
        if username and password:
            return username, password
    print("No credentials found in environment or file.")
    username = input("Enter modem admin username: ")
    password = getpass.getpass("Enter modem admin password: ")
    return username, password
