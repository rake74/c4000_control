# C4000 Control: CenturyLink Modem Management CLI

`c4000_control` is a command-line interface (CLI) tool written in Python to manage the URL/website blocking functionality and query devices on CenturyLink C4000 series modems. It was developed and tested on a **C4000BZ** model.

This script provides a robust, scriptable alternative to the modem's Web UI. It mimics a browser session (headers, timing, and origin checks) to bypass the firmware's flakiness and enforces strict timing to prevent database corruption.

## Features

*   **Robust Rule Management**:
    *   **Idempotent Operations**: "Add" commands verify existence first. "Remove" commands verify deletion.
    *   **Self-Healing**: Automatically detects and cleans up duplicate rules caused by firmware glitches.
    *   **Ghost Rule Protection**: Detects stuck rules that cannot be deleted and skips them to prevent infinite loops.
*   **Browser Emulation**: Sends exact `Origin` and `Referer` headers to prevent the modem from dropping connections (Anti-CSRF/security checks).
*   **Flexible Targets**:
    *   Manage rules by **Hostname**, **IP Address**, or **MAC Address**.
    *   Apply rules to **all devices** or specific targets.
*   **Batch Operations**: Add/Remove multiple rules via command line flags or text files.
*   **Smart Configuration**: Automatic gateway detection and secure credential handling.

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

## Rules File Format

The `--rules-file` argument uses a simple CSV format: `device,url`.
```
# Comments are allowed
DESKTOP-child,youtube.com
192.168.0.50,tiktok.com
all,malware-site.com
```
