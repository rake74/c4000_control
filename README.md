# C4000 Control: CenturyLink Modem Management CLI

`c4000_control` is a command-line interface (CLI) tool written in Python to manage the URL/website blocking functionality, query devices, and handle configuration backups on CenturyLink C4000 series modems. It was developed and tested on a **C4000BZ** model.

This script provides a robust, scriptable alternative to the modem's Web UI. It mimics a browser session (headers, timing, and origin checks) to bypass the firmware's flakiness and enforces strict timing to prevent database corruption.

## Features

*   **Robust Rule Management**:
    *   **Idempotent Operations**: "Add" commands verify existence first. "Remove" commands verify deletion.
    *   **Self-Healing**: Automatically detects and cleans up duplicate rules caused by firmware glitches.
    *   **Ghost Rule Protection**: Detects stuck rules that cannot be deleted and skips them to prevent infinite loops.
*   **Configuration Management**:
    *   **Backup**: Download the current modem configuration to a timestamped local file.
    *   **Restore**: Upload a backup file to restore settings (automatically handles the required reboot).
    *   **Versioning**: Automatically names backups with Model, Serial, and Timestamp.
*   **Browser Emulation**: Sends exact `Origin` and `Referer` headers to prevent the modem from dropping connections (Anti-CSRF/security checks).
*   **Flexible Targets**:
    *   Manage rules by **Hostname**, **IP Address**, or **MAC Address**.
    *   Apply rules to **all devices** or specific targets.
*   **Batch Operations**: Add/Remove multiple rules via command line flags or text files.

---

## Disclaimer

This is an unofficial, third-party tool developed without the involvement, endorsement, or knowledge of CenturyLink. It is provided "as is" without warranty of any kind. **The author is not responsible for any damage, disruption of service, or other issues that may arise from its use. You use this tool at your own risk.**

The CenturyLink and C4000 names are trademarks of their respective owners. This project uses these names for identification and compatibility purposes only and makes no claim to the intellectual property of CenturyLink or its hardware/software vendors.

**It is highly advised you backup your current config before using this tool; during development author had to reset the modem and reconfigure it by hand at least once.**

### Note on Speed
This script is intentionally "slow." The C4000 modem uses slow flash storage. To prevent database corruption and connection drops, this tool enforces:
1.  A **rate limit** (default 2s) between all requests.
2.  A **7-second pause** after every write operation to ensure the data is committed to the modem's memory.

---

## Requirements

*   Python 3.6+
*   `pip` (Python package installer)
*   The `requests` and `netifaces` Python libraries.

---

## Installation & Setup

1.  **Download Files**:
    Place `c4000_control.py`, the `c4000_lib` directory, and `requirements.txt` in a folder.

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Make Executable** (Linux/macOS):
    ```bash
    chmod +x c4000_control.py
    ```

4.  **Set Up Credentials**:
    Create `c4000_control.creds`:
    ```ini
    USERNAME = admin
    PASSWORD = your_modem_password
    ```

---

## Usage

### Global Options
*   `--modem <IP>`: The IP address of your modem.
*   `--debug`: Enables verbose output (shows HTTP headers and raw JSON).
*   `--wait`: Pauses the script before exiting.
*   `--delay <Seconds>`: Set the minimum interval between requests (Rate Limit). Default is **2.0s**. *Note: Write operations always pause for an additional 7s regardless of this setting.*

### Device Commands (`device`)

#### **`device list`**
Displays all known devices on the local network.
```bash
./c4000_control.py device list
```

### Configuration Commands (`config`)

#### **`config list`**
List all local backup files sorted by date.
```bash
./c4000_control.py config list
```

#### **`config backup`**
Downloads the current configuration. Files are saved to the `config-backups/` directory with a filename format of `DB-<Model><Serial>_<Timestamp>.tar.gz`.
```bash
./c4000_control.py config backup
```

#### **`config restore`**
Restores a configuration file.
```bash
# Restore the newest available backup (default)
./c4000_control.py config restore

# Restore a specific file
./c4000_control.py config restore config-backups/DB-C4000BZ...tar.gz
```
*Warning: This operation will overwrite current settings and automatically reboot the modem.*

### DHCP Reservations (`dhcp`)

#### **`dhcp list`**
Displays all configured static DHCP reservations (MAC → IP).
```bash
./c4000_control.py dhcp list
```

#### **`dhcp reserve`**
Assigns a static IP to a device by MAC address. The operation is idempotent: if the MAC already has a reservation it is updated in place; if the requested MAC/IP pair already exists, it is a no-op.
```bash
# Reserve by MAC address
./c4000_control.py dhcp reserve --mac AA:BB:CC:DD:EE:FF --ip 192.168.0.50

# Reserve using a known hostname (resolves to its MAC via the device table)
./c4000_control.py dhcp reserve --device my-camera --ip 192.168.0.50

# Preview a change without writing anything
./c4000_control.py --dry-run dhcp reserve --mac AA:BB:CC:DD:EE:FF --ip 192.168.0.50
```

#### **`dhcp unreserve`**
Removes a static reservation, matched by MAC or IP.
```bash
./c4000_control.py dhcp unreserve --ip 192.168.0.50
./c4000_control.py dhcp unreserve --mac AA:BB:CC:DD:EE:FF
```

**Safety notes**:
*   A full-config backup is taken automatically before each write. Skip it with `--no-backup`.
*   The write is verified immediately after; if it does not confirm, an automatic rollback is attempted.
*   **Lease behaviour**: on this firmware, adding or updating a reservation does not force the device off its current DHCP lease. The device will keep its existing IP until the lease renews or the modem reboots.

---

### URL Blocking Commands (`url`)

#### **`url list`**
Displays all active URL blocking rules.
```bash
./c4000_control.py url list
```

#### **`url add`**
Safe, idempotent addition of rules. If a rule already exists, it is skipped.
```bash
# Add a single rule
./c4000_control.py url add --device DESKTOP-child --block youtube.com

# Add a batch of rules from a file
./c4000_control.py url add --rules-file rules_to_add.txt
```

#### **`url remove`**
Removes rules by matching the device and the blocked URL.
```bash
# Remove a single rule
./c4000_control.py url remove --device DESKTOP-child --block youtube.com

# Remove a batch of rules
./c4000_control.py url remove --rules-file rules_to_remove.txt
```

#### **`url remove-id`**
Removes a specific rule by its numeric ID (useful for cleaning up manually).
```bash
./c4000_control.py url remove-id 3
```

#### **`url remove-all`**
Safely wipes all URL blocking rules.
```bash
./c4000_control.py url remove-all
```
*Note: If the modem refuses to delete a specific rule (a "ghost rule"), the script will detect it, log a warning, and proceed to remove the remaining rules.*

---

## Building a Standalone Binary

You can compile this tool into a single executable file (no Python installation required for the end user).

### Using GitHub Actions (Cross-Platform)
This repository includes a workflow to automatically build binaries for **Windows** and **Linux**.
1.  Push a tag starting with `v` (e.g., `v1.0.0`).
2.  Go to the "Releases" page on GitHub to download the artifacts.

### Using PyInstaller (Local Build)
To build a binary for your current OS:
1.  Install PyInstaller:
    ```bash
    pip install pyinstaller
    ```
2.  Build:
    ```bash
    pyinstaller --onefile --name c4000-tool c4000_control.py
    ```
3.  The executable will be in `dist/`.

---

## Rules File Format

The `--rules-file` argument uses a simple CSV format: `device,url`.
```
# Comments are allowed
DESKTOP-child,youtube.com
192.168.0.50,tiktok.com
all,malware-site.com
```
