"""Persistent local storage for an activated Cyber Club license.

The 20-character activation key is encrypted with Windows DPAPI (machine scope)
before it is written to HKLM. The installer deliberately does not delete this
registry key during uninstall. This preserves entitlement across app
uninstall/reinstall on the same Windows installation; it does not survive a
Windows reinstall, disk format, or motherboard/device replacement if the
server binds the entitlement to a different machine.
"""
from __future__ import annotations

import ctypes
import json
import sys
from ctypes import wintypes

REGISTRY_PATH = r"SOFTWARE\DjShrek\CyberClub\License"
REGISTRY_VALUE = "ProtectedEntitlement"
KEY_LENGTH = 20


class LicenseStorageError(RuntimeError):
    pass


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes):
    buffer = ctypes.create_string_buffer(data)
    return _DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def _dpapi(data: bytes, *, decrypt: bool) -> bytes:
    if sys.platform != "win32":
        raise LicenseStorageError("Хранение лицензии в реестре доступно только в Windows.")
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    source, source_buffer = _blob(data)
    destination = _DATA_BLOB()
    flags = 0x4  # CRYPTPROTECT_LOCAL_MACHINE
    description = wintypes.LPWSTR()
    if decrypt:
        ok = crypt.CryptUnprotectData(
            ctypes.byref(source), ctypes.byref(description), None, None, None,
            flags, ctypes.byref(destination)
        )
    else:
        ok = crypt.CryptProtectData(
            ctypes.byref(source), "DjShrek Cyber Club", None, None, None,
            flags, ctypes.byref(destination)
        )
    if not ok:
        raise LicenseStorageError(f"Windows DPAPI вернул ошибку {ctypes.get_last_error()}.")
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        kernel.LocalFree(destination.pbData)


def _registry():
    if sys.platform != "win32":
        raise LicenseStorageError("Реестр Windows доступен только в Windows.")
    import winreg
    return winreg


def save_entitlement(license_key: str, *, activated_at: str = "", expires_at: str = "",
                     machine_fingerprint: str = "") -> None:
    """Encrypt and persist an activated license key and non-secret metadata."""
    normalized = license_key.strip().upper()
    if len(normalized) != KEY_LENGTH or not normalized.isascii() or not normalized.isalnum():
        raise ValueError("Ключ лицензии должен содержать ровно 20 латинских букв/цифр.")
    payload = json.dumps({
        "key": normalized,
        "activated_at": activated_at,
        "expires_at": expires_at,
        "machine_fingerprint": machine_fingerprint,
        "schema": 1,
    }, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    protected = _dpapi(payload, decrypt=False)
    winreg = _registry()
    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, REGISTRY_PATH, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, REGISTRY_VALUE, 0, winreg.REG_BINARY, protected)


def load_entitlement() -> dict | None:
    """Read and decrypt the retained entitlement. Return None if not activated."""
    winreg = _registry()
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REGISTRY_PATH, 0, winreg.KEY_QUERY_VALUE) as key:
            protected, value_type = winreg.QueryValueEx(key, REGISTRY_VALUE)
    except FileNotFoundError:
        return None
    if value_type != winreg.REG_BINARY:
        raise LicenseStorageError("Формат записи лицензии в реестре повреждён.")
    try:
        payload = json.loads(_dpapi(bytes(protected), decrypt=True).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LicenseStorageError("Не удалось расшифровать данные лицензии.") from exc
    if payload.get("schema") != 1 or len(payload.get("key", "")) != KEY_LENGTH:
        raise LicenseStorageError("Сохранённая запись лицензии имеет неизвестный формат.")
    return payload


def clear_entitlement() -> None:
    """Explicit administrative revocation/cleanup only; installer does not call this."""
    winreg = _registry()
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REGISTRY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, REGISTRY_VALUE)
    except FileNotFoundError:
        return
