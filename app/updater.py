from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

OWNER = "ptonzo"
REPOSITORY = "DjShrek-Draiver-"
API_URL = f"https://api.github.com/repos/{OWNER}/{REPOSITORY}/releases/latest"
USER_AGENT = "DjShrek-Draiver-Updater"
ASSET_NAME = "DjShrek-Draiver-Portable-Windows-x64.zip"


class UpdateError(RuntimeError):
    pass


def current_version() -> str:
    try:
        from app.version import VERSION
        return VERSION
    except Exception:
        return os.environ.get("DJSHREK_VERSION", "0.2.0")


def _version_tuple(value: str) -> tuple[int, ...]:
    cleaned = value.strip().lstrip("vV").split("-", 1)[0]
    try:
        return tuple(int(part) for part in cleaned.split("."))
    except ValueError as exc:
        raise UpdateError(f"Неподдерживаемый номер версии: {value}") from exc


def check_latest_release(timeout: int = 12) -> dict | None:
    request = urllib.request.Request(
        API_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            release = json.loads(response.read(2_000_000).decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise UpdateError(f"Не удалось проверить обновления: {exc}") from exc
    if release.get("draft") or release.get("prerelease"):
        return None
    tag = str(release.get("tag_name", ""))
    if not tag or _version_tuple(tag) <= _version_tuple(current_version()):
        return None
    asset = next((a for a in release.get("assets", []) if a.get("name") == ASSET_NAME), None)
    if not asset or not asset.get("browser_download_url"):
        raise UpdateError("В новом релизе отсутствует проверенный архив приложения.")
    return {
        "version": tag.lstrip("vV"),
        "notes": str(release.get("body", ""))[:4000],
        "download_url": asset["browser_download_url"],
        "size": int(asset.get("size", 0)),
    }


def download_and_schedule(update: dict, install_dir: str | None = None) -> None:
    if not getattr(sys, "frozen", False):
        raise UpdateError("Самообновление доступно только в установленной Windows-версии.")
    target_dir = Path(install_dir or Path(sys.executable).parent).resolve()
    if not target_dir.exists() or target_dir == Path(sys.executable).anchor:
        raise UpdateError("Папка установки недоступна для обновления.")
    temp_dir = Path(tempfile.mkdtemp(prefix="djshrek-update-"))
    archive = temp_dir / "update.zip"
    request = urllib.request.Request(update["download_url"], headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        if update.get("size") and archive.stat().st_size != update["size"]:
            raise UpdateError("Размер загруженного архива не совпадает с опубликованным.")
        with zipfile.ZipFile(archive) as zf:
            bad = zf.testzip()
            if bad:
                raise UpdateError(f"Архив обновления повреждён: {bad}")
            names = zf.namelist()
            if not names or any(Path(n).is_absolute() or ".." in Path(n).parts for n in names):
                raise UpdateError("Архив содержит небезопасные пути.")
            zf.extractall(temp_dir / "payload")
    except (urllib.error.URLError, TimeoutError, OSError, zipfile.BadZipFile) as exc:
        raise UpdateError(f"Не удалось загрузить или проверить обновление: {exc}") from exc

    payload = temp_dir / "payload"
    # Release archive must contain the PyInstaller onedir payload at its root.
    exe_candidates = list(payload.rglob("DjShrek-Draiver Cyber Club.exe"))
    if len(exe_candidates) != 1:
        raise UpdateError("В архиве не найден единственный исполняемый файл программы.")
    source_dir = exe_candidates[0].parent
    helper = temp_dir / "apply_update.ps1"
    script = r'''
param([string]$Source, [string]$Target, [int]$PidToWait, [string]$Exe)
$ErrorActionPreference = "Stop"
try {
  Wait-Process -Id $PidToWait -Timeout 90 -ErrorAction SilentlyContinue
  if (Get-Process -Id $PidToWait -ErrorAction SilentlyContinue) { throw "Application did not exit" }
  Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $Target -Recurse -Force
  }
  Start-Process -FilePath (Join-Path $Target $Exe) -WorkingDirectory $Target
} catch {
  Add-Content -LiteralPath (Join-Path $env:TEMP "DjShrek-update-error.log") -Value $_
}
'''
    helper.write_text(script, encoding="utf-8")
    exe_name = Path(sys.executable).name
    command = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(helper), "-Source", str(source_dir), "-Target", str(target_dir),
        "-PidToWait", str(os.getpid()), "-Exe", exe_name,
    ]
    subprocess.Popen(command, creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0), close_fds=True)
