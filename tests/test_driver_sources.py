from app.driver_sources import source_for_device
from app.scanner import Device


def test_intel_device_maps_to_official_intel_assistant():
    device = Device(
        name="Intel(R) UHD Graphics",
        manufacturer="Intel Corporation",
        status="OK",
        class_name="Display",
        device_id="PCI\\VEN_8086",
        driver_version="31.0.101.2111",
        driver_date="2024-01-01",
        driver_provider="Intel Corporation",
        inf_name="oem1.inf",
    )
    source = source_for_device(device)
    assert source is not None
    assert source.name == "Intel Driver & Support Assistant"
    assert source.url.startswith("https://www.intel.com/")


def test_unknown_vendor_has_no_guessed_source():
    device = Device(
        name="Mystery controller",
        manufacturer="Unknown Vendor",
        status="OK",
        class_name="System",
        device_id="ROOT\\UNKNOWN",
        driver_version="1.0",
        driver_date="2024-01-01",
    )
    assert source_for_device(device) is None


from app import driver_catalog
from app.driver_catalog import DriverCatalogError, _hardware_match
import pytest


def test_hardware_id_matching_requires_component_boundary():
    assert _hardware_match([r"PCI\\VEN_10DE&DEV_2484"], r"PCI\\VEN_10DE&DEV_2484&SUBSYS_0000")
    assert not _hardware_match([r"PCI\\VEN_10DE&DEV_248"], r"PCI\\VEN_10DE&DEV_2484")
    assert not _hardware_match([""], r"PCI\\VEN_10DE")


def test_catalog_html_extracts_update_identity(monkeypatch):
    update_id = "12345678-1234-1234-1234-123456789abc"
    page = f'<table><tr><td>Graphics Driver</td><a href="DownloadDialog.aspx?updateID={update_id}&amp;foo=1">Download</a></tr></table>'
    monkeypatch.setattr(driver_catalog, "_request", lambda *args, **kwargs: page)
    rows = driver_catalog._catalog_search(r"PCI\\VEN_10DE")
    assert rows == [{"UpdateId": update_id, "Title": "Graphics Driver Download", "Version": "", "Date": ""}]


def test_search_does_not_require_windows_update_agent(monkeypatch):
    class Device:
        device_id = r"PCI\\VEN_10DE&DEV_2484"
        name = "GPU"
    monkeypatch.setattr(driver_catalog.platform, "system", lambda: "Windows")
    monkeypatch.setattr(driver_catalog, "_catalog_search", lambda hardware_id: [
        {"UpdateId": "12345678-1234-1234-1234-123456789abc", "Title": "GPU driver"}
    ])
    found = driver_catalog.search_driver_updates([Device()])
    assert found[0]["MatchedDevices"] == ["GPU"]


def test_non_windows_search_fails_with_clear_message(monkeypatch):
    monkeypatch.setattr(driver_catalog.platform, "system", lambda: "Linux")
    with pytest.raises(DriverCatalogError, match="Windows 10/11"):
        driver_catalog.search_driver_updates([])
