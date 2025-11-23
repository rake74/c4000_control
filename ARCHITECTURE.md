# C4000 Control: Architecture Overview

This document outlines the architecture of the `c4000_control` tool. The project is intentionally structured as a top-level executable script that uses a dedicated library package. This provides a clean separation of concerns, making the tool easy to use, maintain, and extend.

## Project Structure

```
.
├── c4000_control.py           # Executable Entry Point
├── c4000_lib/                 # Library Package (all logic)
│   ├── __init__.py
│   ├── cli.py                 # 1. Command Layer
│   ├── core.py                # 2. Communication Layer (Browser Emulation)
│   ├── features/              # 3. Feature Logic Layer
│   │   ├── __init__.py
│   │   ├── config.py          #    - Backup & Restore
│   │   ├── device_listing.py  #    - Device Listing
│   │   └── url_blocking.py    #    - State Enforcement
│   └── utils.py               # 4. Utility Layer
├── .gitignore
├── ARCHITECTURE.md
├── README.md
└── requirements.txt
```

### Component Breakdown

#### The Executable: `c4000_control.py`

This is the public face of the tool and the only script the user needs to interact with directly. Its sole responsibility is to import the library package (`c4000_lib`) and execute the main application logic. This keeps the entry point simple and clean.

#### The Library Package: `c4000_lib/`

All of the tool's logic resides within this Python package.

##### 1. Command Layer (`cli.py`)

*   **Responsibility**: Defines and parses the entire command-line interface using `argparse`. It acts as the "brain" of the application.
*   **Function**: It interprets the user's commands and arguments, then orchestrates the necessary calls to the other layers. It passes critical safety parameters (like `min_interval`) down to the core layer.

##### 2. Communication Layer (`core.py`)

*   **Responsibility**: Handles all low-level communication, mimicking a human browser session to bypass firmware instability.
*   **Function**:
    *   **Browser Emulation**: Manages specific HTTP headers (`Origin`, `Referer`, `User-Agent`) and dynamically switches them based on the action (Login vs. Configuration) to pass the modem's CSRF security checks.
    *   **Traffic Control**: Enforces a global "Rate Limit" (default 2s) to prevent flooding the modem's CPU.
    *   **Write Safety**: Enforces a strict **7-second pause** after every `POST` (Write) operation to prevent database corruption.
    *   **Binary Handling**: Supports streaming file downloads (for backups) and multipart/form-data uploads (for restoring configurations).

##### 3. Feature Logic Layer (`features/`)

*   **Responsibility**: Implements "Desired State" logic and specific feature workflows.
*   **Function**: Each file defines a class for a specific feature area.
    *   **`url_blocking.py`**: Implements idempotent rule management. Checks existence before adding, verifies removal, and self-heals duplicate rules.
    *   **`config.py`**: Manages the Backup/Restore workflow. It handles file I/O, timestamp generation, and the specific multipart upload format required by the modem's restore endpoint.
    *   **`device_listing.py`**: Parses the modem's host table to resolve Names/IPs to MAC addresses.

##### 4. Utility Layer (`utils.py`)

*   **Responsibility**: Holds small, reusable helper functions that are independent of the core application logic.
*   **Function**: This is the location for functions like `load_credentials()` and `get_default_gateway()`.
