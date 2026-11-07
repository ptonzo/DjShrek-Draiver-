from __future__ import annotations

import html
import json
import os
import platform
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

CATALOG_URL = "https://www.catalog.update.microsoft.com/Search.aspx"
USER_AGENT = "DjShrek-Draiver/1.0 (Windows driver catalog client)"


class DriverCatalogError(RuntimeError):
    pass


def _request(url: str, data: bytes | None = None, timeout: int = 30) -> str:
    request = urllib.request.Request(
        url, data=data,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json,*/*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except Exception as exc:
        raise DriverCatalogError(f"Не удалось получить данные каталога драйверов: {exc}") from exc


def _catalog_search(hardware_id: str) -> list[dict[str, str]]:
    query = urllib.parse.urlencode({"q": hardware_id}).encode("utf-8")
    page = _request(CATALOG_URL, query)
    # Catalog rows expose update identity in the onclick download/details controls.
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', page, flags=re.I | re.S)
    found: list[dict[str, str]] = []
    for row in rows:
        plain = html.unescape(re.sub(r'<[^>]+>', ' ', row))
        plain = re.sub(r'\\s+', ' ', plain).strip()
        match = re.search(r"downloadDialog\\.aspx\\?[^'\" ]*updateID=([0-9a-fA-F-]{36})", row, re.I)
        if not match:
            match = re.search(r"updateID\\s*[:=]\\s*['\"]([0-9a-fA-F-]{36})", row, re.I)
        if not match or not plain:
            continue
        found.append({"UpdateId": match.group(1), "Title": plain[:500]})
    return found


def _download_urls(update_id: str) -> list[str]:
    url = "https://www.catalog.update.microsoft.com/DownloadDialog.aspx?" + urllib.parse.urlencode({"updateID": update_id})
    page = _request(url)
    urls = re.findall(r"https?://[^\\\"'<> ]+\\.(?:cab|zip)(?:\\?[^\\\"'<> ]*)?", html.unescape(page), re.I)
    return list(dict.fromkeys(urls))


def _hardware_match(candidate_ids: list[str], device_id: str) -> bool:
    device = (device_id or "").strip().casefold()
    if not device:
        return False
    for raw_id in candidate_ids:
        candidate = str(raw_id or "").strip().casefold()
        if candidate and device.startswith(candidate):
            if len(device) == len(candidate) or device[len(candidate)] in {"&", "\\\\"}:
                return True
    return False


def search_driver_updates(devices: list[Any]) -> list[dict[str, Any]]:
    """Search the public web catalog directly; does not use Windows Update Agent/service."""
    if platform.system() != "Windows":
        raise DriverCatalogError("Поиск пакетов драйверов доступен в Windows 10/11.")
    ids = list(dict.fromkeys(
        str(getattr(device, "device_id", "")).strip()
        for device in devices if str(getattr(device, "device_id", "")).strip()
    ))
    results: dict[str, dict[str, Any]] = {}
    for hardware_id in ids:
        for offer in _catalog_search(hardware_id):
            offer_id = offer["UpdateId"]
            offer["MatchedDevices"] = []
            offer["MatchedDeviceIds"] = []
            offer["HardwareIds"] = [hardware_id]
            for device in devices:
                if _hardware_match([hardware_id], getattr(device, "device_id", "")):
                    offer["MatchedDevices"].append(device.name)
                    offer["MatchedDeviceIds"].append(device.device_id)
            results[offer_id] = offer
    return list(results.values())


def install_driver_updates(updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Download catalog CAB/ZIP files over HTTPS, unpack INF packages and install via pnputil."""
    if platform.system() != "Windows":
        raise DriverCatalogError("Установка драйверов доступна только в Windows 10/11.")
    if not updates:
        raise DriverCatalogError("Не выбраны драйверы для установки.")
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="DjShrekDrivers-") as temp:
        root = Path(temp)
        for index, update in enumerate(updates, start=1):
            update_id = str(update.get("UpdateId", ""))
            if not re.fullmatch(r"[0-9a-fA-F-]{36}", update_id):
                raise DriverCatalogError("Каталог вернул некорректный идентификатор пакета.")
            urls = _download_urls(update_id)
            if not urls:
                raise DriverCatalogError(f"Для пакета «{update.get('Title', update_id)}» каталог не предоставил прямую ссылку на CAB/ZIP.")
            package_dir = root / str(index)
            package_dir.mkdir()
            downloaded = []
            for n, url in enumerate(urls, start=1):
                suffix = ".zip" if ".zip" in url.lower() else ".cab"
                package = package_dir / f"package-{n}{suffix}"
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                try:
                    with urllib.request.urlopen(request, timeout=120) as response, package.open("wb") as target:
                        while chunk := response.read(1024 * 1024):
                            target.write(chunk)
                except Exception as exc:
                    raise DriverCatalogError(f"Не удалось скачать пакет драйвера: {exc}") from exc
                downloaded.append(package)
            extracted = package_dir / "extracted"
            extracted.mkdir()
            for package in downloaded:
                if package.suffix.lower() == ".zip":
                    try:
                        with zipfile.ZipFile(package) as archive:
                            archive.extractall(extracted)
                    except (OSError, zipfile.BadZipFile) as exc:
                        raise DriverCatalogError(f"Повреждён ZIP-пакет: {exc}") from exc
                else:
                    command = ["expand.exe", "-F:*", str(package), str(extracted)]
                    proc = subprocess.run(command, capture_output=True, text=True, timeout=180)
                    if proc.returncode:
                        raise DriverCatalogError(proc.stderr.strip() or "Не удалось распаковать CAB-пакет.")
            inf_files = list(extracted.rglob("*.inf"))
            if not inf_files:
                raise DriverCatalogError(f"В пакете «{update.get('Title', update_id)}» не найден INF-файл драйвера.")
            for inf in inf_files:
                proc = subprocess.run(
                    ["pnputil.exe", "/add-driver", str(inf), "/install"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
                )
                if proc.returncode:
                    raise DriverCatalogError(proc.stderr.strip() or f"pnputil не смог установить {inf.name}.")
            results.append({"Title": update.get("Title", update_id), "ResultCode": 2,
                             "HResult": 0, "RebootRequired": "restart" in (proc.stdout + proc.stderr).lower()})
    return results
