# DjShrek Draiver

Windows 10/11 x64 utility for device inventory and controlled driver updates.

**Current status:** early prototype. It inventories Plug and Play devices and can query/install selected driver-class updates offered by the Windows Update Agent. Installation always requires explicit user confirmation.

## Features

- Russian-language PySide6 desktop interface.
- Hardware inventory through Windows CIM.
- Search and CSV export.
- Driver update discovery through the built-in Windows Update Agent (driver category only).
- Explicit per-update installation confirmation.
- No third-party driver bundles or unofficial driver download mirrors.

## Requirements

- Windows 10 or Windows 11, 64-bit.
- Python 3.11+.
- PowerShell and Windows Update service.

## Run

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m app
```

## Build EXE

```powershell
pip install -r requirements-dev.txt
pyinstaller --noconfirm --clean --windowed --name "DjShrek Draiver" --collect-all PySide6 run.py
```

## Safety

1. Updates are discovered from the Windows Update Agent, not third-party driver sites.
2. Installation requires selecting one update and confirming it.
3. Windows Update handles package acquisition and installation.
4. Back up important data before driver changes; some updates require restart.
5. Independent package-signature reporting, restore/rollback UI and hardware compatibility scoring are not implemented yet.

## Licensing

The source code is licensed under MIT; see LICENSE. This does not grant rights to redistribute third-party driver packages. Commercial activation, billing, device limits and a license server are **not implemented**. Do not market this prototype as a commercially licensed release yet.

## Roadmap

- [x] Windows device inventory
- [x] Search and CSV export
- [x] Windows Update driver discovery
- [x] Explicit installation confirmation for one selected update
- [ ] Independent package signature/provenance report
- [ ] Restore point, driver backup and rollback workflow
- [ ] Signed installer and release pipeline
- [ ] Commercial license server and activation UI
- [ ] Windows 10/11 hardware test matrix

Not affiliated with Microsoft or hardware manufacturers.
