from __future__ import annotations

import base64
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
    driver_provider: str = ""
    inf_name: str = ""

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
            driver_provider=str(row.get("DriverProvider") or ""),
            inf_name=str(row.get("InfName") or ""),
        )


# EncodedCommand prevents locale/code-page corruption of Cyrillic device names.
SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$driverMap = @{}
Get-CimInstance Win32_PnPSignedDriver | ForEach-Object {
    if ($_.DeviceID) { $driverMap[[string]$_.DeviceID] = $_ }
}
$items = Get-CimInstance Win32_PnPEntity | ForEach-Object {
    $id = [string]$_.PNPDeviceID
    $drv = $driverMap[$id]
    $date = ''
    if ($drv -and $drv.DriverDate) { $date = ([datetime]$drv.DriverDate).ToString('yyyy-MM-dd') }
    [pscustomobject]@{
        Name = [string]$_.Name
        Manufacturer = [string]$_.Manufacturer
        Status = [string]$_.Status
        PNPClass = [string]$_.PNPClass
        PNPDeviceID = $id
        DriverVersion = if ($drv) { [string]$drv.DriverVersion } else { '' }
        DriverDate = $date
        DriverProvider = if ($drv) { [string]$drv.DriverProviderName } else { '' }
        InfName = if ($drv) { [string]$drv.InfName } else { '' }
    }
}
ConvertTo-Json -InputObject @($items) -Depth 4 -Compress
"""


class ScanError(RuntimeError):
    pass


def scan_devices(timeout_seconds: int = 45) -> list[Device]:
    encoded_script = base64.b64encode(SCRIPT.encode("utf-16le")).decode("ascii")
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
             "-EncodedCommand", encoded_script],
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
    devices = [Device.from_mapping(row) for row in parsed if isinstance(row, dict)]
    return sorted(devices, key=lambda device: device.name.casefold())
