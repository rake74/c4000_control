# C4000 Control: Architecture Overview

This document outlines the architecture of the `c4000_control` tool. The project is intentionally structured as a top-level executable script that uses a dedicated library package. This provides a clean separation of concerns, making the tool easy to use, maintain, and extend.

## Project Structure

```
.
├── c4000_control.py        # Executable Entry Point
├── c4000_lib/              # Library Package (all logic)
│   ├── __init__.py
│   ├── cli.py              # 1. Command Layer
│   ├── core.py             # 2. Communication Layer (Browser Emulation)
│   ├── features/           # 3. Feature Logic Layer (State Enforcement)
│   │   ├── __init__.py
│   │   ├── device_listing.py
│   │   └── url_blocking.py
│   └── utils.py            # 4. Utility Layer
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
    *   **Write Safety**: Enforces a strict **7-second pause** after every `POST` (Write) operation. This allows the modem's slow flash storage to commit changes before the next request, preventing database corruption.
    *   **Smart Retries**: Automatically retries safe `GET` requests if the network hiccups, but **fails fast** on `POST` requests to prevent duplicate rules ("Double Post" bugs).

##### 3. Feature Logic Layer (`features/`)

*   **Responsibility**: Implements "Desired State" logic rather than simple command execution. **This is where the robustness lives.**
*   **Function**: Each file (e.g., `url_blocking.py`) defines a class for a specific feature.
    *   **Idempotency**: Instead of simply "Adding" a rule, it checks if the rule exists first. If it does, it does nothing.
    *   **Verification**: After applying a change, it queries the modem again to verify the change was actually accepted.
    *   **Self-Healing**: It can detect and remove duplicate rules caused by previous firmware glitches.
    *   **Ghost Rule Protection**: In bulk operations (like `remove-all`), it tracks rules that refuse to be deleted and skips them to prevent infinite loops.

##### 4. Utility Layer (`utils.py`)

*   **Responsibility**: Holds small, reusable helper functions that are independent of the core application logic.
*   **Function**: This is the location for functions like `load_credentials()` and `get_default_gateway()`.
