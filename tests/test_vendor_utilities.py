import subprocess

from app import vendor_utilities as vu


def test_non_windows_returns_official_vendor_entries(monkeypatch):
    monkeypatch.setattr(vu.sys, "platform", "linux")
    items = vu.detect_vendor_utilities()
    assert [item.key for item in items] == ["intel", "amd", "dell"]
    assert all(item.installed is False for item in items)
    assert all(item.url.startswith("https://") for item in items)


def test_unknown_vendor_key_does_not_open_browser(monkeypatch):
    called = []
    monkeypatch.setattr(vu.webbrowser, "open", lambda *a, **k: called.append(a) or True)
    assert vu.open_vendor_scan_page("unknown") is False
    assert called == []


def test_open_vendor_page_uses_only_official_https(monkeypatch):
    opened = []
    monkeypatch.setattr(vu.webbrowser, "open", lambda url, new=0: opened.append(url) or True)
    assert vu.open_vendor_scan_page("intel") is True
    assert opened == [vu.OFFICIAL_URLS["intel"]]


def test_dell_scan_parses_report_without_installing_updates(tmp_path, monkeypatch):
    executable = tmp_path / "dcu-cli.exe"
    executable.write_bytes(b"test")
    report = tmp_path / "DjShrek-Dell-Updates.xml"
    monkeypatch.setattr(vu.tempfile, "gettempdir", lambda: str(tmp_path))

    def fake_run(args, **kwargs):
        assert args[1] == "/scan"
        assert any(str(report) in arg for arg in args)
        report.write_text(
            "<Updates><Update><Name>Intel Chipset Driver</Name>"
            "<Version>10.1.2</Version><ReleaseDate>2026-10-01</ReleaseDate>"
            "</Update></Updates>", encoding="utf-8"
        )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(vu.subprocess, "run", fake_run)
    rows = vu.scan_dell_updates(str(executable))
    assert rows == [{
        "title": "Intel Chipset Driver",
        "version": "10.1.2",
        "date": "2026-10-01",
    }]
