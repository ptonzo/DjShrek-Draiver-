from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import webbrowser
try:
    import winreg
except ImportError:  # Non-Windows test runners
    winreg = None


@dataclass(frozen=True, slots=True)
class VendorUtility:
    key: str
    name: str
    url: str
    installed: bool
    executable: str = ""


OFFICIAL_URLS = {
    "intel": "https://www.intel.com/content/www/us/en/support/detect.htm",
    "amd": "https://www.amd.com/en/support/download/drivers.html",
    "dell": "https://www.dell.com/support/home/en-us?app=drivers",
}


def _installed_app_names() -> list[str]:
    if sys.platform != "win32" or winreg is None:
        return []
    names: list[str] = []
    locations = (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"),
    )
    for hive, key_path in locations:
        try:
            with winreg.OpenKey(hive, key_path) as root:
                count = winreg.QueryInfoKey(root)[0]
                for index in range(count):
                    try:
                        subkey_name = winreg.EnumKey(root, index)
                        with winreg.OpenKey(root, subkey_name) as subkey:
                            display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            if display_name:
                                names.append(str(display_name))
                    except OSError:
                        continue
        except OSError:
            continue
    return names


def _find_dell_cli() -> str:
    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\\Program Files")) / "Dell" / "CommandUpdate" / "dcu-cli.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)")) / "Dell" / "CommandUpdate" / "dcu-cli.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return ""


def detect_vendor_utilities() -> list[VendorUtility]:
    """Detect installed OEM utilities without downloading or running installers."""
    if sys.platform != "win32" or winreg is None:
        return [
            VendorUtility("intel", "Intel Driver & Support Assistant", OFFICIAL_URLS["intel"], False),
            VendorUtility("amd", "AMD Auto-Detect / AMD Software", OFFICIAL_URLS["amd"], False),
            VendorUtility("dell", "Dell Command | Update", OFFICIAL_URLS["dell"], False),
        ]
    names = [name.casefold() for name in _installed_app_names()]
    try:
        intel_service = subprocess.run(
            ["sc.exe", "query", "DSAService"], capture_output=True, timeout=8,
            check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        intel_service = False
    intel_installed = intel_service or any("intel driver & support assistant" in n for n in names)
    amd_path = Path(os.environ.get("ProgramFiles", r"C:\\Program Files")) / "AMD" / "CIM" / "Bin64" / "AMDInstallManager.exe"
    amd_installed = amd_path.is_file() or any(
        ("amd software" in n or "amd auto-detect" in n or "amd radeon software" in n)
        for n in names
    )
    dell_cli = _find_dell_cli()
    dell_installed = bool(dell_cli) or any("dell command | update" in n or "dell command update" in n for n in names)
    return [
        VendorUtility("intel", "Intel Driver & Support Assistant", OFFICIAL_URLS["intel"], intel_installed),
        VendorUtility("amd", "AMD Auto-Detect / AMD Software", OFFICIAL_URLS["amd"], amd_installed, str(amd_path) if amd_installed and amd_path.is_file() else ""),
        VendorUtility("dell", "Dell Command | Update", OFFICIAL_URLS["dell"], dell_installed, dell_cli),
    ]


def open_vendor_scan_page(key: str) -> bool:
    url = OFFICIAL_URLS.get(key)
    if not url or not url.startswith("https://"):
        return False
    return bool(webbrowser.open(url, new=2))


def scan_dell_updates(executable: str, timeout_seconds: int = 300) -> list[dict[str, str]]:
    """Run Dell Command | Update's supported scan/report CLI; never applies updates."""
    if not executable or not Path(executable).is_file():
        raise RuntimeError("Dell Command | Update CLI не найден.")
    report_path = Path(tempfile.gettempdir()) / "DjShrek-Dell-Updates.xml"
    try:
        report_path.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        result = subprocess.run(
            [executable, "/scan", f"-report={report_path}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout_seconds, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Сканирование Dell Command | Update превысило время ожидания.") from exc
    except OSError as exc:
        raise RuntimeError(f"Не удалось запустить Dell Command | Update: {exc}") from exc
    if result.returncode not in (0, 1):
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or f"Dell Command | Update завершился с кодом {result.returncode}.")
    if not report_path.is_file():
        return []
    try:
        root = ET.parse(report_path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise RuntimeError("Dell Command | Update создал отчёт, но XML не удалось прочитать.") from exc
    updates: list[dict[str, str]] = []
    for node in root.iter():
        values = {child.tag.split("}")[-1].casefold(): (child.text or "").strip() for child in list(node)}
        if not values:
            continue
        title = next((values[k] for k in ("name", "title", "package_name", "packagename") if values.get(k)), "")
        version = next((values[k] for k in ("version", "package_version", "packageversion") if values.get(k)), "")
        date = next((values[k] for k in ("release_date", "releasedate", "date") if values.get(k)), "")
        if title:
            updates.append({"title": title, "version": version, "date": date})
    return updates
