from __future__ import annotations

import json
import platform
import subprocess
from typing import Any

MICROSOFT_UPDATE_SERVICE_ID = "7971f918-a847-4430-9279-4a52d1efe18d"


class DriverCatalogError(RuntimeError):
    pass


_SEARCH_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$serviceId = '7971f918-a847-4430-9279-4a52d1efe18d'
$manager = New-Object -ComObject Microsoft.Update.ServiceManager
$registered = @($manager.Services | ForEach-Object { [string]$_.ServiceID })
if ($serviceId -notin $registered) { [void]$manager.AddService2($serviceId, 3, $null) }
$session = New-Object -ComObject Microsoft.Update.Session
$searcher = $session.CreateUpdateSearcher()
$searcher.ServerSelection = 3
$searcher.ServiceID = $serviceId
$result = $searcher.Search("IsInstalled=0 and Type='Driver' and IsHidden=0")
$rows = @()
foreach ($u in $result.Updates) {
  $ids = @()
  $version = ''
  $date = ''
  $model = ''
  $manufacturer = ''
  try { $ids = @($u.DriverHardwareID) } catch {}
  try { $version = [string]$u.DriverVersion } catch {}
  try { $date = ([datetime]$u.DriverVerDate).ToString('yyyy-MM-dd') } catch {}
  try { $model = [string]$u.DriverModel } catch {}
  try { $manufacturer = [string]$u.DriverManufacturer } catch {}
  $rows += [pscustomobject]@{
    UpdateId = [string]$u.Identity.UpdateID
    Revision = [int]$u.Identity.RevisionNumber
    Title = [string]$u.Title
    Description = [string]$u.Description
    HardwareIds = $ids
    Version = $version
    Date = $date
    Model = $model
    Manufacturer = $manufacturer
    EulaAccepted = [bool]$u.EulaAccepted
    IsDownloaded = [bool]$u.IsDownloaded
  }
}
ConvertTo-Json -InputObject @($rows) -Depth 6 -Compress
"""


_INSTALL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$ids = ConvertFrom-Json -InputObject $env:DJSHREK_UPDATE_IDS
$serviceId = '7971f918-a847-4430-9279-4a52d1efe18d'
$manager = New-Object -ComObject Microsoft.Update.ServiceManager
$registered = @($manager.Services | ForEach-Object { [string]$_.ServiceID })
if ($serviceId -notin $registered) { [void]$manager.AddService2($serviceId, 3, $null) }
$session = New-Object -ComObject Microsoft.Update.Session
$searcher = $session.CreateUpdateSearcher()
$searcher.ServerSelection = 3
$searcher.ServiceID = $serviceId
$available = $searcher.Search("IsInstalled=0 and Type='Driver' and IsHidden=0")
$collection = New-Object -ComObject Microsoft.Update.UpdateColl
foreach ($identity in $ids) {
  $found = $false
  foreach ($u in $available.Updates) {
    if ([string]$u.Identity.UpdateID -eq [string]$identity.UpdateId -and
        [int]$u.Identity.RevisionNumber -eq [int]$identity.Revision) {
      if (-not $u.EulaAccepted) { $u.AcceptEula() }
      [void]$collection.Add($u)
      $found = $true
      break
    }
  }
  if (-not $found) { throw "Обновление больше не доступно: $($identity.UpdateId)" }
}
if ($collection.Count -eq 0) { throw 'Не выбраны обновления.' }
$downloader = $session.CreateUpdateDownloader()
$downloader.Updates = $collection
$downloadResult = $downloader.Download()
if ($downloadResult.ResultCode -notin 2,3) { throw "Загрузка не завершена. Код: $($downloadResult.ResultCode)" }
for ($i = 0; $i -lt $collection.Count; $i++) {
  if (-not $collection.Item($i).IsDownloaded) { throw "Пакет не загружен: $($collection.Item($i).Title)" }
}
$installer = $session.CreateUpdateInstaller()
$installer.Updates = $collection
$installer.ForceQuiet = $true
$installResult = $installer.Install()
$results = @()
for ($i = 0; $i -lt $collection.Count; $i++) {
  $item = $installResult.GetUpdateResult($i)
  $results += [pscustomobject]@{
    Title = [string]$collection.Item($i).Title
    ResultCode = [int]$item.ResultCode
    HResult = [int]$item.HResult
    RebootRequired = [bool]$item.RebootRequired
  }
}
ConvertTo-Json -InputObject @($results) -Depth 4 -Compress
"""


def _run_powershell(script: str, timeout: int = 1800, env: dict[str, str] | None = None) -> str:
    if platform.system() != "Windows":
        raise DriverCatalogError("Каталог драйверов доступен только в Windows 10/11.")
    import base64
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DriverCatalogError(f"Не удалось выполнить операцию с каталогом драйверов: {exc}") from exc
    if result.returncode:
        raise DriverCatalogError(result.stderr.strip() or result.stdout.strip() or "Ошибка службы каталога драйверов.")
    return result.stdout.strip()


def _hardware_match(candidate_ids: list[str], device_id: str) -> bool:
    """Match a complete PnP hardware-ID component, not an arbitrary text prefix."""
    device = (device_id or "").strip().casefold()
    if not device:
        return False
    for raw_id in candidate_ids:
        candidate = str(raw_id or "").strip().casefold()
        if not candidate or not device.startswith(candidate):
            continue
        if len(device) == len(candidate) or device[len(candidate)] in {"&", "\\"}:
            return True
    return False


def search_driver_updates(devices: list[Any]) -> list[dict[str, Any]]:
    """Find Microsoft Update driver offers and retain only exact PnP hardware-ID matches."""
    raw = _run_powershell(_SEARCH_SCRIPT, timeout=900)
    if not raw:
        return []
    try:
        candidates = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DriverCatalogError("Каталог вернул данные в неизвестном формате.") from exc
    if isinstance(candidates, dict):
        candidates = [candidates]
    results = []
    for candidate in candidates:
        hardware_ids = candidate.get("HardwareIds") or []
        if isinstance(hardware_ids, str):
            hardware_ids = [hardware_ids]
        matches = [
            device for device in devices
            if _hardware_match(hardware_ids, getattr(device, "device_id", ""))
        ]
        if not matches:
            continue
        candidate["MatchedDevices"] = [device.name for device in matches]
        candidate["MatchedDeviceIds"] = [device.device_id for device in matches]
        results.append(candidate)
    return results


def install_driver_updates(updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not updates:
        raise DriverCatalogError("Не выбраны обновления драйверов.")
    identities = [{"UpdateId": item["UpdateId"], "Revision": int(item["Revision"])} for item in updates]
    env = dict(__import__("os").environ)
    env["DJSHREK_UPDATE_IDS"] = json.dumps(identities)
    raw = _run_powershell(_INSTALL_SCRIPT, timeout=3600, env=env)
    if not raw:
        return []
    try:
        results = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DriverCatalogError("Windows вернула некорректный отчёт установки.") from exc
    return results if isinstance(results, list) else [results]
