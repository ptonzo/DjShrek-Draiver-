from __future__ import annotations

import base64
import json
import subprocess
from dataclasses import dataclass


@dataclass(slots=True)
class DriverUpdate:
    title: str
    description: str
    update_id: str
    revision: int
    downloaded: bool


class WindowsUpdateError(RuntimeError):
    pass


def _run(script: str, timeout: int = 180) -> str:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError as exc:
        raise WindowsUpdateError("PowerShell не найден. Функция доступна только в Windows.") from exc
    except subprocess.TimeoutExpired as exc:
        raise WindowsUpdateError("Операция Windows Update превысила время ожидания.") from exc
    except OSError as exc:
        raise WindowsUpdateError(f"Не удалось запустить Windows Update: {exc}") from exc
    if result.returncode:
        raise WindowsUpdateError(result.stderr.strip() or "Ошибка Windows Update.")
    return result.stdout.strip()


def find_driver_updates() -> list[DriverUpdate]:
    script = r"""
$ErrorActionPreference = 'Stop'
try {
  $session = New-Object -ComObject Microsoft.Update.Session
  $searcher = $session.CreateUpdateSearcher()
  $result = $searcher.Search("IsInstalled=0 and Type='Driver' and IsHidden=0")
  $items = @()
  for ($i = 0; $i -lt $result.Updates.Count; $i++) {
    $u = $result.Updates.Item($i)
    $items += [pscustomobject]@{
      Title = [string]$u.Title
      Description = [string]$u.Description
      UpdateId = [string]$u.Identity.UpdateID
      Revision = [int]$u.Identity.RevisionNumber
      IsDownloaded = [bool]$u.IsDownloaded
    }
  }
  ConvertTo-Json -InputObject @($items) -Depth 4 -Compress
} catch {
  [Console]::Error.WriteLine($_.Exception.Message)
  exit 1
}
"""
    raw = _run(script)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WindowsUpdateError("Windows Update вернул данные в неизвестном формате.") from exc
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise WindowsUpdateError("Некорректный ответ Windows Update.")
    return [
        DriverUpdate(
            title=str(row.get("Title") or "Драйвер"),
            description=str(row.get("Description") or ""),
            update_id=str(row.get("UpdateId") or ""),
            revision=int(row.get("Revision") or 0),
            downloaded=bool(row.get("IsDownloaded", False)),
        )
        for row in data if isinstance(row, dict) and row.get("UpdateId")
    ]


def install_driver_update(update_id: str, revision: int) -> str:
    if not update_id or len(update_id) > 100 or any(c not in "0123456789abcdefABCDEF-" for c in update_id):
        raise WindowsUpdateError("Некорректный идентификатор обновления.")
    if revision < 0:
        raise WindowsUpdateError("Некорректная ревизия обновления.")
    payload = base64.b64encode(json.dumps(
        {"UpdateId": update_id, "Revision": revision}
    ).encode("utf-8")).decode("ascii")
    script = r"""
$ErrorActionPreference = 'Stop'
try {
  $request = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('PAYLOAD')) | ConvertFrom-Json
  $session = New-Object -ComObject Microsoft.Update.Session
  $searcher = $session.CreateUpdateSearcher()
  $result = $searcher.Search("IsInstalled=0 and Type='Driver' and IsHidden=0")
  $selected = New-Object -ComObject Microsoft.Update.UpdateColl
  for ($i = 0; $i -lt $result.Updates.Count; $i++) {
    $u = $result.Updates.Item($i)
    if ($u.Identity.UpdateID -eq $request.UpdateId -and [int]$u.Identity.RevisionNumber -eq [int]$request.Revision) {
      if (-not $u.EulaAccepted) { $u.AcceptEula() }
      [void]$selected.Add($u)
      break
    }
  }
  if ($selected.Count -ne 1) { throw 'Обновление больше не найдено. Выполните повторную проверку.' }
  $downloader = $session.CreateUpdateDownloader()
  $downloader.Updates = $selected
  $download = $downloader.Download()
  if ($download.ResultCode -ne 2 -and $download.ResultCode -ne 3) { throw "Загрузка не завершена. Код: $($download.ResultCode)" }
  $installer = $session.CreateUpdateInstaller()
  $installer.Updates = $selected
  $install = $installer.Install()
  [pscustomobject]@{ ResultCode = [int]$install.ResultCode; RebootRequired = [bool]$install.RebootRequired } | ConvertTo-Json -Compress
} catch {
  [Console]::Error.WriteLine($_.Exception.Message)
  exit 1
}
""".replace("PAYLOAD", payload)
    raw = _run(script, timeout=900)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WindowsUpdateError("Не удалось прочитать результат установки.") from exc
    code = int(result.get("ResultCode", -1))
    if code not in (2, 3):
        raise WindowsUpdateError(f"Windows Update сообщил об ошибке. Код: {code}")
    return "Драйвер установлен." + (" Требуется перезагрузка Windows." if result.get("RebootRequired") else "")
