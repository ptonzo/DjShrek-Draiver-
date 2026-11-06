from app.export import export_devices_csv
from app.scanner import Device


def test_export_writes_headers_and_device(tmp_path):
    target = tmp_path / "devices.csv"
    device = Device("Test adapter", "Example", "OK", "Net", "ROOT_TEST", "1.2.3", "2026-01-01")
    export_devices_csv([device], target)
    content = target.read_text(encoding="utf-8-sig")
    assert "Устройство" in content
    assert "Test adapter" in content
    assert "1.2.3" in content
