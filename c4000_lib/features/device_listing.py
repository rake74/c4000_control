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
import sys
from ..core import ModemError

class DeviceListingFeature:
    """Handles the logic for listing devices on the network."""
    def __init__(self, control):
        self.control = control

    def get_all(self):
        """
        Fetches and parses all known devices.
        Returns: (list of devices, raw_data)
        Raises: ModemError on failure.
        """
        self.control._log("Querying modem for known devices...")
        raw_data = self.control.get_request('Device.Hosts.Host')

        devices = []
        for item in raw_data.get('Objects', []):
            device_info = {}
            for param in item.get('Param', []):
                if param.get('ParamName') in ['HostName', 'IPAddress', 'PhysAddress']:
                    device_info[param['ParamName']] = param.get('ParamValue', '')
            if device_info.get('PhysAddress'):
                devices.append(device_info)

        self.control._log(f"Found {len(devices)} actual devices.")
        return devices, raw_data

    def list_devices(self, debug=False):
        """Prints a formatted list of devices."""
        try:
            devices, raw_data = self.get_all()
            if debug:
                print("--- Raw Modem Response ---", file=sys.stderr)
                print(json.dumps(raw_data, indent=2), file=sys.stderr)
                print("--- End Raw Response ---\n", file=sys.stderr)

            if devices:
                print(f"{'Hostname':<30} {'IP Address':<18} {'MAC Address':<20}")
                print(f"{'-'*30} {'-'*18} {'-'*20}")
                for dev in devices:
                    print(f"{dev.get('HostName', 'N/A'):<30} {dev.get('IPAddress', 'N/A'):<18} {dev.get('PhysAddress', 'N/A'):<20}")
            else:
                print("No devices found on the network map.")
        except ModemError as e:
            print(f"Error retrieving device list: {e}", file=sys.stderr)
