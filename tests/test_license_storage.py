import pytest

from app import license_storage as storage


def test_rejects_invalid_license_key_before_touching_windows():
    with pytest.raises(ValueError):
        storage.save_entitlement("SHORT")


def test_registry_location_is_machine_wide_and_stable():
    assert storage.REGISTRY_PATH == r"SOFTWARE\DjShrek\CyberClub\License"
    assert storage.REGISTRY_VALUE == "ProtectedEntitlement"


def test_non_windows_registry_access_fails_clearly(monkeypatch):
    monkeypatch.setattr(storage.sys, "platform", "linux")
    with pytest.raises(storage.LicenseStorageError, match="Windows"):
        storage.load_entitlement()


def test_non_windows_dpapi_fails_clearly(monkeypatch):
    monkeypatch.setattr(storage.sys, "platform", "linux")
    with pytest.raises(storage.LicenseStorageError, match="Windows"):
        storage._dpapi(b"test", decrypt=False)
