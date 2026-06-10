# Project Contributors

This project is a collaboration between a human developer and an AI assistant.

*   **Chris Jacobs/rake74** - Project Lead
    *   Provided initial concept, `curl` commands, and project goals.
    *   Directed all feature development and architectural changes.
    *   Performed all testing, debugging, and validation.

*   **Google's Gemini** - AI Programming Assistant
    *   Generated initial Python code from specifications.
    *   Performed iterative refactoring based on feedback.
    *   Provided documentation, architectural patterns, and license text.

*   **Anthropic's Claude** - AI Programming Assistant
    *   Implemented the DHCP static-reservation feature (`dhcp list`, `dhcp reserve`, `dhcp unreserve`).
    *   Added global `--dry-run` flag and per-write rollback safety.
    *   Updated `ConfigFeature.backup()` to return the saved filepath for abort-on-failure semantics.
    *   Wrote the supporting test suite and documentation.
