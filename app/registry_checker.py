"""Conservative Windows Registry diagnostics for stale startup entries.

The scanner is read-only. The only automatic repair supported is removing a
Run/RunOnce value whose executable target is confirmed missing, after exporting
the containing registry key to a .reg backup.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import winreg
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RegistryFinding:
    hive: str
    subkey: str
    value_name: str
    value_data: str
    issue: str
    severity: str = "Предупреждение"
    repairable: bool = False


_STARTUP_KEYS = (
    ("HKCU", winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"),
    ("HKCU", winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce"),
    ("HKLM", winreg.HKEY_LOCAL_MACHINE, r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"),
    ("HKLM", winreg.HKEY_LOCAL_MACHINE, r"Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce"),
)


def _command_executable(command: str) -> str | None:
    text = os.path.expandvars(command.strip())
    if not text:
        return None
    if text.startswith('"'):
        end = text.find('"', 1)
        return text[1:end] if end > 1 else None
    # Unquoted paths may contain spaces. Find the shortest prefix ending in .exe.
    match = re.match(r"(.+?\\.exe)(?:\\s|$)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.split()[0] if text.split() else None


def scan_registry() -> list[RegistryFinding]:
    if sys.platform != "win32":
        raise OSError("Проверка реестра доступна только в Windows 10/11.")
    findings: list[RegistryFinding] = []
    for hive_name, hive, subkey in _STARTUP_KEYS:
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
                index = 0
                while True:
                    try:
                        value_name, value_data, _ = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    index += 1
                    if not isinstance(value_data, str):
                        continue
                    target = _command_executable(value_data)
                    if not target:
                        findings.append(RegistryFinding(
                            hive_name, subkey, value_name, value_data,
                            "Не удалось определить исполняемый файл; автоматическое исправление запрещено."
                        ))
                        continue
                    expanded = os.path.expandvars(target.strip().strip('"'))
                    # Shell built-ins, protocol handlers and environment-based commands
                    # are intentionally not classified as broken executable paths.
                    if expanded.startswith(("\\\\", "shell:", "ms-settings:", "http:", "https:")):
                        continue
                    if not os.path.isabs(expanded):
                        findings.append(RegistryFinding(
                            hive_name, subkey, value_name, value_data,
                            "Путь запуска относительный или не распознан; требуется ручная проверка."
                        ))
                        continue
                    if not Path(expanded).is_file():
                        findings.append(RegistryFinding(
                            hive_name, subkey, value_name, value_data,
                            f"Файл автозапуска не найден: {expanded}",
                            "Ошибка", True
                        ))
        except FileNotFoundError:
            continue
        except PermissionError:
            findings.append(RegistryFinding(
                hive_name, subkey, "", "",
                "Нет доступа для чтения раздела; запустите программу с правами администратора для полной проверки."
            ))
        except OSError as exc:
            findings.append(RegistryFinding(
                hive_name, subkey, "", "", f"Не удалось прочитать раздел: {exc}"
            ))
    return findings


def repair_stale_startup_entry(finding: RegistryFinding) -> str:
    """Backup a Run key then delete one confirmed-stale value."""
    if sys.platform != "win32":
        raise OSError("Исправление доступно только в Windows.")
    if not finding.repairable or finding.hive not in ("HKCU", "HKLM"):
        raise ValueError("Эта запись не поддерживает автоматическое исправление.")
    hive = winreg.HKEY_CURRENT_USER if finding.hive == "HKCU" else winreg.HKEY_LOCAL_MACHINE
    # Only allow the four explicitly audited startup keys.
    if (finding.hive, finding.subkey) not in {
        (name, path) for name, _, path in _STARTUP_KEYS
    }:
        raise ValueError("Раздел реестра не входит в список безопасного исправления.")
    backup_dir = Path(tempfile.gettempdir()) / "DjShrek-Registry-Backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", finding.value_name)[:48] or "startup"
    backup_file = backup_dir / f"registry-{finding.hive}-{safe_name}.reg"
    root = "HKEY_CURRENT_USER" if finding.hive == "HKCU" else "HKEY_LOCAL_MACHINE"
    full_key = root + "\\\\" + finding.subkey
    result = subprocess.run(
        ["reg.exe", "export", full_key, str(backup_file), "/y"],
        capture_output=True, text=True, check=False
    )
    if result.returncode != 0 or not backup_file.is_file():
        raise OSError("Не удалось создать резервную копию реестра: " + (result.stderr or result.stdout))
    access = winreg.KEY_SET_VALUE
    with winreg.OpenKey(hive, finding.subkey, 0, access) as key:
        # Confirm the value has not changed since the scan.
        current, _ = winreg.QueryValueEx(key, finding.value_name)
        if current != finding.value_data:
            raise RuntimeError("Запись изменилась после проверки. Выполните сканирование повторно.")
        winreg.DeleteValue(key, finding.value_name)
    return str(backup_file)
