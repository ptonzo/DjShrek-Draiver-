from __future__ import annotations

import sys

import pytest

from app.registry_checker import _command_executable, scan_registry
from app.junk_cleaner import scan_junk_files, clean_junk_files, JunkFile


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ('"C:\\Program Files\\Vendor\\agent.exe" --background', "C:\\Program Files\\Vendor\\agent.exe"),
        ("C:\\Tools\\agent.exe /silent", "C:\\Tools\\agent.exe"),
        ("", None),
    ],
)
def test_command_executable(command, expected):
    assert _command_executable(command) == expected


def test_registry_scan_is_windows_only():
    if sys.platform == "win32":
        pytest.skip("This assertion is for non-Windows test hosts.")
    with pytest.raises(OSError, match="Windows"):
        scan_registry()


def test_junk_scan_is_windows_only():
    if sys.platform == "win32":
        pytest.skip("This assertion is for non-Windows test hosts.")
    with pytest.raises(OSError, match="Windows"):
        scan_junk_files()


def test_junk_cleanup_is_windows_only():
    if sys.platform == "win32":
        pytest.skip("This assertion is for non-Windows test hosts.")
    with pytest.raises(OSError, match="Windows"):
        clean_junk_files([])
