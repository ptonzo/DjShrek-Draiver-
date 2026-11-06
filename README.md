# DjShrek Draiver

Windows 10/11 x64 utility for device inventory, live PC monitoring and controlled driver updates.

**Current status:** Neon Gaming Control Center dashboard is merged into `main`. The Windows x64 single-file installer is built by GitHub Actions. It must still be smoke-tested on physical Windows 10/11 hardware; sensor availability depends on hardware, drivers and firmware.

## Features

- Neon Gaming graphite interface with neon-green accents.
- Live dashboard: CPU load, RAM use, C: drive usage, detected CPU/GPU, installed RAM, Windows build and system uptime.
- Background telemetry refresh every 2.5 seconds without blocking the UI.
- NVIDIA GPU load and temperature through `nvidia-smi` when available.
- ACPI thermal-zone reading only when exposed by firmware; unavailable sensors are not fabricated.
- Hardware inventory through Windows CIM.
- Search and CSV export.
- Driver update discovery through the built-in Windows Update Agent (driver category only).
- Explicit per-update installation confirmation.
- Export of installed third-party driver packages with `pnputil`.
- User-confirmed restore of exported packages with `pnputil`.
- No third-party driver bundles or unofficial driver download mirrors.

## Requirements

- Windows 10 or Windows 11, 64-bit.
- Python 3.11+ for source/developer run.
- PowerShell and Windows Update service.
- NVIDIA telemetry requires compatible NVIDIA drivers and `nvidia-smi`; other GPU vendors may not expose utilization/temperature through this version.

## Run from source

```powershell
py -3.11 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m app
```

## Install on a Windows PC

The distributable is a single file: `DjShrek-Draiver-Setup.exe` (Windows 10/11 x64). Run it, approve the Windows UAC administrator prompt, choose whether to create a desktop shortcut, and click Install. The installer copies the application, creates Start menu/uninstall entries, and can launch the program at the end. Python is not required on the target PC.

Download the artifact named `DjShrek-Draiver-Setup-Windows-x64` from the latest successful **Build Windows installer** run in the Actions tab. The artifact is a ZIP wrapper containing the single setup EXE; artifacts expire after 30 days.

## Safety and limitations

1. Updates are discovered from the Windows Update Agent, not third-party driver sites.
2. Installation requires selecting one update and confirming it.
3. Windows Update handles package acquisition and installation.
4. Use **Создать копию драйверов** before changing drivers. Choose an empty folder with enough free space; Windows may require running the app as Administrator.
5. **Восстановить из копии** re-adds packages from the selected backup using `pnputil /add-driver`. It is not a guaranteed rollback: Windows selects compatible packages and may not restore every previous device state. Create a Windows restore point separately before changes.
6. Driver export/restore commands are explicit user actions; the app does not silently change drivers during inventory.
7. Temperature and GPU telemetry availability varies by device, driver and firmware. Unsupported values are shown as unavailable.
8. The installer is not digitally signed yet; Windows SmartScreen may display a warning.
9. Commercial activation, billing, device limits and a license server are not implemented.

## Roadmap

- [x] Windows device inventory
- [x] Search and CSV export
- [x] Windows Update driver discovery
- [x] Explicit installation confirmation for one selected update
- [x] Driver package export and user-confirmed restore workflow
- [x] Neon Gaming live monitoring dashboard
- [ ] Independent package signature/provenance report
- [ ] Automated restore-point creation and verified rollback
- [ ] Signed installer and release pipeline
- [ ] Commercial license server and activation UI
- [ ] Physical Windows 10/11 hardware test matrix

Not affiliated with Microsoft or hardware manufacturers.
