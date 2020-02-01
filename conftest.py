"""Config file for extending pytest functionality to packages w/o native support."""
from testfixtures import LogCapture
import pytest


@pytest.fixture(autouse=True)
def capture():
    with LogCapture() as capture:
        yield capture
