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
import sys
import glob
import datetime
import time
from ..core import ModemError

BACKUP_DIR = "config-backups"

class ConfigFeature:
    """Handles configuration Backup, Restore, and Listing operations."""
    def __init__(self, control):
        self.control = control

    def _get_modem_identity(self):
        """
        Fetches Model Name and Serial Number to construct standard filenames.
        Returns: (model_name, serial_number)
        """
        try:
            # Query DeviceInfo for identity
            data = self.control.get_request('Device.DeviceInfo')
            model = "C4000"
            serial = "Unknown"

            for item in data.get('Objects', []):
                for param in item.get('Param', []):
                    if param['ParamName'] == 'ModelName':
                        model = param['ParamValue']
                    elif param['ParamName'] == 'SerialNumber':
                        serial = param['ParamValue']
            return model, serial
        except Exception:
            self.control._log("Could not fetch identity. Using defaults.")
            return "C4000", "Generic"

    def list_backups(self):
        """Lists available backup files, sorted by date (newest last)."""
        if not os.path.exists(BACKUP_DIR):
            print(f"No backup directory found at './{BACKUP_DIR}'.")
            return

        search_path = os.path.join(BACKUP_DIR, "*.tar.gz")
        files = glob.glob(search_path)

        if not files:
            print(f"No configuration backups found in '{BACKUP_DIR}/'.")
            return

        # Sort by modification time (Oldest -> Newest)
        files.sort(key=os.path.getmtime)

        print(f"{'Created (Local Time)':<22} {'Size':<10} {'Filename'}")
        print(f"{'-'*22} {'-'*10} {'-'*30}")

        for filepath in files:
            stat = os.stat(filepath)
            ts = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

            # Convert size to readable format
            size_bytes = stat.st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024*1024):.1f} MB"

            filename = os.path.basename(filepath)
            print(f"{ts:<22} {size_str:<10} {filename}")

    def backup(self):
        """Downloads the current configuration to a local file."""
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            print(f"Created backup directory: {BACKUP_DIR}/")

        print("Requesting configuration backup from modem...")

        # Prepare the request
        payload = {'Action': 'BackUp'}
        referer = 'utilities_configurationsave.html'

        try:
            response = self.control.send_download(payload, referer)

            # Generate Filename
            # Default format: DB-<Model><Serial>_<Timestamp>.tar.gz
            model, serial = self._get_modem_identity()
            timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            filename = f"DB-{model}{serial}_{timestamp}.tar.gz"

            # Check if server suggested a filename in Content-Disposition
            if "Content-Disposition" in response.headers:
                cd = response.headers["Content-Disposition"]
                if "filename=" in cd:
                    server_filename = cd.split("filename=")[1].strip('"')
                    if server_filename:
                        filename = server_filename

            filepath = os.path.join(BACKUP_DIR, filename)

            print(f"Downloading to '{filepath}'...")
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"Success: Backup saved to {filepath}")

        except ModemError as e:
            print(f"Backup failed: {e}", file=sys.stderr)

    def restore(self, filename=None):
        """Restores a configuration file, defaulting to the newest."""

        # 1. Resolve Filename
        target_file = filename
        if not target_file:
            # Find newest in backup dir
            search_path = os.path.join(BACKUP_DIR, "*.tar.gz")
            files = glob.glob(search_path)
            if not files:
                print(f"Error: No backup files found in {BACKUP_DIR}/", file=sys.stderr)
                return
            # Sort by modification time, newest first (max)
            target_file = max(files, key=os.path.getmtime)
            print(f"No filename specified. Defaulting to newest: {os.path.basename(target_file)}")

        if not os.path.exists(target_file):
            print(f"Error: File '{target_file}' not found.", file=sys.stderr)
            return

        # 2. Confirmation
        print("\nWARNING: Restoring a configuration will overwrite current settings and REBOOT the modem.")
        confirm = input(f"Are you sure you want to restore '{target_file}'? (y/N): ")
        if confirm.lower() != 'y':
            print("Restore cancelled.")
            return

        # 3. Upload
        print("Uploading configuration...")
        try:
            # Correct parameters derived from Chrome DevTools trace
            params = {
                'Object': 'Device.X_LANTIQ_COM_Upgrade.Upgrade.4',
                'Operation': 'Modify',
                'State': 'UPG_REQ',
                'FileType': 'VENDOR_CFG'
            }

            referer = 'utilities_configurationsave.html'
            endpoint = 'cgi_set'

            # We open the file in binary mode.
            # We assume the form field name is 'file' (standard for this endpoint type)
            with open(target_file, 'rb') as f:
                files = {'file': (os.path.basename(target_file), f, 'application/x-gzip')}

                self.control.send_upload(files, referer, params=params, endpoint=endpoint)

            print("Success: Configuration uploaded.")
            print("The modem should be rebooting now. Please wait 2-3 minutes before reconnecting.")

        except ModemError as e:
            print(f"Restore failed: {e}", file=sys.stderr)
