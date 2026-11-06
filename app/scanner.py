from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Device:
    name: str
    manufacturer: str
    status: str
    class_name: str
    device_id: str
    driver_version: str
    driver_date: str

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "Device":
        return cls(
            name=str(row.get("Name") or "Неизвестное устройство"),
            manufacturer=str(row.get("Manufacturer") or ""),
            status=str(row.get("Status") or ""),
            class_name=str(row.get("PNPClass") or ""),
            device_id=str(row.get("PNPDeviceID") or ""),
            driver_version=str(row.get("DriverVersion") or ""),
            driver_date=str(row.get("DriverDate") or ""),
        )


SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$items = Get-CimInstance Win32_PnPEntity | Select-Object Name, Manufacturer, Status, PNPClass, PNPDeviceID, DriverVersion, DriverDate
ConvertTo-Json -InputObject @($items) -Depth 4 -Compress
"""


class ScanError(RuntimeError):
    pass


def scan_devices(timeout_seconds: int = 45) -> list[Device]:
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", SCRIPT],
            check=False, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout_seconds,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError as exc:
        raise ScanError("PowerShell не найден. Запустите программу в Windows.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ScanError("Сканирование превысило допустимое время ожидания.") from exc
    except OSError as exc:
        raise ScanError(f"Не удалось запустить PowerShell: {exc}") from exc
    if result.returncode != 0:
        raise ScanError(result.stderr.strip() or "Ошибка получения списка устройств.")
    if not result.stdout.strip():
        return []
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ScanError("Windows вернула данные устройств в неожиданном формате.") from exc
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        raise ScanError("Некорректный формат списка устройств.")
    return sorted((Device.from_mapping(x) for x in parsed if isinstance(x, dict)), key=lambda x: x.name.casefold())
