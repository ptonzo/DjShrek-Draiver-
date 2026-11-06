# DjShrek-Draiver Cyber Club

Windows 10/11 x64 PC control center for hardware inventory, live monitoring and driver-source discovery.

## Interface

- DjShrek Neon Gaming visual base: near-black graphite, RGB violet/cyan accents, gaming-style tabs and controls.
- Control Center dashboard: CPU, RAM, system disk, GPU, OS, uptime and available thermal sensors.
- Event log and background monitoring refresh.
- Device inventory with manufacturer, signed driver provider, version, date and INF package.
- Cyrillic device names are read through UTF-8 PowerShell output.

## Driver inventory and official sources

The driver page has a single **Проверить наличие обновлений драйверов** action. It reads the installed signed-driver inventory and displays the installed version/date and a link to the matching manufacturer's official support source.

Windows Update Agent is not used by the driver page. The app does not silently download packages from mirrors or install unknown driver files.

Important: vendor driver catalogs and update utilities differ. This version links to official tools/catalogs (Intel DSA, NVIDIA, AMD and OEM support sites). It does not yet perform universal in-app version comparison or unattended installation from every vendor; the manufacturer's own utility confirms compatibility and runs its signed installer. This is deliberate: a generic installer must not guess driver compatibility or install packages from unofficial sources.

Official sources currently mapped:
- Intel Driver & Support Assistant: https://www.intel.com/content/www/us/en/support/detect.html
- NVIDIA Driver Downloads: https://www.nvidia.com/Download/index.aspx
- AMD Drivers & Support: https://www.amd.com/en/support/download/drivers.html
- Dell: https://www.dell.com/support/home/en-us?app=drivers
- Lenovo: https://pcsupport.lenovo.com/
- HP: https://support.hp.com/drivers
- ASUS: https://www.asus.com/support/download-center/
- Acer: https://www.acer.com/us-en/support/drivers-and-manuals
- MSI: https://www.msi.com/support/download

## Other functions

- Search and CSV export of detected devices.
- Export installed driver packages using Windows `pnputil`.
- User-confirmed restore workflow for exported packages.
- NVIDIA load/temperature via `nvidia-smi`, if installed.
- ACPI temperature only when firmware exposes a supported sensor; unavailable values are never fabricated.

### Registry diagnostics and cleanup

- **Проверка реестра** currently scans the Windows Run/RunOnce startup locations in HKCU and HKLM. The scan is read-only. Automatic repair is limited to a confirmed missing executable in the current user's startup entries (HKCU); a .reg backup is exported before the selected value is removed. Machine-wide HKLM findings are report-only because repair requires elevation.
- **Очистка компьютера** scans the current user's temporary directory and Windows Temp for files older than seven days. The user reviews the categories and confirms cleanup. Files that are locked, changed since the scan, inaccessible, symbolic links, or reparse points are skipped.
- Personal folders, Downloads, browser profiles, cookies, saved passwords, documents and photos are not scanned or deleted. This is a conservative temporary-file cleanup, not a full disk optimizer.

## Build and test

Requirements: Windows 10/11 x64, Python 3.12 for CI/development.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest -q
python run.py
```

GitHub Actions builds the Windows installer. The artifact is named `DjShrek-Draiver-Setup-Windows-x64` and contains `DjShrek-Draiver-Setup.exe`.

## Known limitations

- Universal automatic driver version lookup and unattended in-app installation across every OEM is not implemented yet. Only official vendor catalog/utility links are provided.
- Physical validation is required on Windows 10 and Windows 11 hardware.
- Temperature and GPU telemetry availability depends on hardware, firmware and drivers.
- The installer is not code-signed yet; SmartScreen may show a warning.
- Commercial license activation and SBP payment are not connected to the desktop app.

Not affiliated with Microsoft or hardware manufacturers.
