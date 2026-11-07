from types import SimpleNamespace

from app import driver_catalog


def test_hardware_match_requires_exact_prefix():
    assert driver_catalog._hardware_match(
        [r"PCI\\VEN_1234&DEV_5678"], r"PCI\\VEN_1234&DEV_5678&SUBSYS_0001\\4&ABC"
    )
    assert not driver_catalog._hardware_match(
        [r"PCI\\VEN_1234&DEV_567"], r"PCI\\VEN_1234&DEV_5678&SUBSYS_0001\\4&ABC"
    )


def test_search_keeps_only_hardware_id_matches(monkeypatch):
    device = SimpleNamespace(name="Test GPU", device_id=r"PCI\\VEN_1234&DEV_5678\\1")
    monkeypatch.setattr(driver_catalog.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        driver_catalog,
        "_catalog_search",
        lambda hardware_id: [
            {"UpdateId": "12345678-1234-1234-1234-123456789abc", "Title": "GPU Driver"}
        ],
    )

    results = driver_catalog.search_driver_updates([device])

    assert len(results) == 1
    assert results[0]["MatchedDevices"] == ["Test GPU"]
    assert results[0]["MatchedDeviceIds"] == [device.device_id]


def test_search_deduplicates_catalog_offers(monkeypatch):
    devices = [
        SimpleNamespace(name="GPU A", device_id=r"PCI\\VEN_1234&DEV_5678\\1"),
        SimpleNamespace(name="GPU B", device_id=r"PCI\\VEN_1234&DEV_5678\\2"),
    ]
    monkeypatch.setattr(driver_catalog.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        driver_catalog,
        "_catalog_search",
        lambda hardware_id: [
            {"UpdateId": "12345678-1234-1234-1234-123456789abc", "Title": "GPU Driver"}
        ],
    )

    results = driver_catalog.search_driver_updates(devices)

    assert len(results) == 1
    assert results[0]["MatchedDevices"] == ["GPU A", "GPU B"]


def test_install_rejects_empty_list(monkeypatch):
    monkeypatch.setattr(driver_catalog.platform, "system", lambda: "Windows")
    try:
        driver_catalog.install_driver_updates([])
    except driver_catalog.DriverCatalogError as exc:
        assert "Не выбраны" in str(exc)
    else:
        raise AssertionError("empty selection must be rejected")
