from types import SimpleNamespace

from app import driver_catalog


def test_hardware_match_requires_exact_prefix():
    assert driver_catalog._hardware_match(
        [r"PCI\VEN_1234&DEV_5678"], r"PCI\VEN_1234&DEV_5678&SUBSYS_0001\4&ABC"
    )
    assert not driver_catalog._hardware_match(
        [r"PCI\VEN_1234&DEV_567"], r"PCI\VEN_1234&DEV_5678&SUBSYS_0001\4&ABC"
    )


def test_search_keeps_only_hardware_id_matches(monkeypatch):
    device = SimpleNamespace(name="Test GPU", device_id=r"PCI\VEN_1234&DEV_5678\1")
    monkeypatch.setattr(driver_catalog, "_run_powershell", lambda *a, **k:
        '[{"UpdateId":"abc","Revision":1,"Title":"GPU Driver","HardwareIds":["PCI\\\\VEN_1234&DEV_5678"],"Version":"2.0"}]')
    results = driver_catalog.search_driver_updates([device])
    assert len(results) == 1
    assert results[0]["MatchedDevices"] == ["Test GPU"]


def test_install_rejects_empty_list():
    try:
        driver_catalog.install_driver_updates([])
    except driver_catalog.DriverCatalogError as exc:
        assert "Не выбраны" in str(exc)
    else:
        raise AssertionError("empty selection must be rejected")
