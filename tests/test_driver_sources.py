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
