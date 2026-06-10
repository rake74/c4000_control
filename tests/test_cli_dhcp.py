import subprocess, sys

def run(*args):
    return subprocess.run([sys.executable, "c4000_control.py", *args],
                          capture_output=True, text=True)

def test_dhcp_help_lists_actions():
    out = run("dhcp", "--help")
    assert "reserve" in out.stdout and "unreserve" in out.stdout and "list" in out.stdout

def test_global_dry_run_flag_exists():
    out = run("--help")
    assert "--dry-run" in out.stdout
