# DjShrek Draiver

Windows 10/11 x64 utility for device inventory and safe driver-update guidance.

**Prototype status:** read-only device inventory. This initial version does not install, replace, or silently download drivers.

## Run

Requires Windows 10/11 x64 and Python 3.11+.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app
```

## Build EXE

```powershell
pip install -r requirements-dev.txt
pyinstaller --noconfirm --clean --windowed --name "DjShrek Draiver" --collect-all PySide6 run.py
```

## Safety

- Read-only hardware inventory in this prototype.
- Future driver updates must match exact hardware IDs and Windows version.
- Prefer Windows Update and official OEM/vendor sources.
- Verify package signatures and provenance.
- Require explicit user confirmation and provide rollback before installing.

## Licensing

The source code in this repository is licensed under MIT (see LICENSE). This does not grant rights to redistribute third-party drivers. Commercial activation, subscriptions and device limits are not implemented yet.

## Roadmap

- [x] Device inventory prototype
- [x] Search and CSV export
- [ ] Windows Update integration with user confirmation
- [ ] Vendor catalogue and signature verification
- [ ] Backup and rollback
- [ ] Signed installer and releases
- [ ] Commercial license service

Not affiliated with Microsoft or hardware manufacturers.