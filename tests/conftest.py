import json
import os
import pytest

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

def load_fixture(name):
    """Load a captured modem JSON response from tests/fixtures/."""
    with open(os.path.join(FIXTURE_DIR, name), "r") as f:
        return json.load(f)

@pytest.fixture
def fixtures():
    return load_fixture
