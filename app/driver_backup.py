from __future__ import annotations

import json
import platform
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

class DriverBackupError(RuntimeError):
    pass

def _run_pnputil(args: list[str], timeout: int = 1800) -> str:
    if platform.system() != "Windows":
        raise DriverBackupError("Резервное копирование и восстановление доступны только в Windows.")
    try:
        result = subprocess.run(
            ["pnputil.exe", *args], capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError as exc:
        raise DriverBackupError("Утилита pnputil.exe не найдена.") from exc
    except subprocess.TimeoutExpired as exc:
        raise DriverBackupError("Операция с драйверами превысила время ожидания.") from exc
    except OSError as exc:
        raise DriverBackupError(f"Не удалось запустить pnputil.exe: {exc}") from exc
    output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    if result.returncode != 0:
        raise DriverBackupError(output or f"pnputil завершился с кодом {result.returncode}.")
    return output

def _write_manifest(target: Path, count: int, note: str) -> None:
    manifest = {
        "application": "DjShrek Draiver",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "driver_packages_exported": count,
        "note": note,
    }
    (target / "djshrek-backup.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def backup_driver_store(destination: str | Path) -> tuple[Path, int]:
    target = Path(destination).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise DriverBackupError("Выберите пустую папку: существующие файлы не будут перезаписаны.")
    target.mkdir(parents=True, exist_ok=True)
    _run_pnputil(["/export-driver", "*", str(target)])
    inf_files = list(target.rglob("*.inf"))
    if not inf_files:
        raise DriverBackupError("Экспорт завершился без INF-файлов. Резервная копия не подтверждена.")
    _write_manifest(target, len(inf_files), "Экспорт всех сторонних пакетов из Driver Store.")
    return target, len(inf_files)

def backup_selected_driver_packages(inf_names: list[str], destination: str | Path) -> tuple[Path, int]:
    target = Path(destination).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise DriverBackupError("Папка резервной копии должна быть пустой.")
    safe_names = sorted(set(inf_names))
    if not safe_names or any(not re.fullmatch(r"oem\d+\.inf", name, re.IGNORECASE) for name in safe_names):
        raise DriverBackupError("Список выбранных INF-файлов пуст или содержит недопустимые имена.")
    target.mkdir(parents=True, exist_ok=True)
    exported = 0
    for index, inf_name in enumerate(safe_names, start=1):
        package_dir = target / f"package-{index:03d}"
        package_dir.mkdir()
        _run_pnputil(["/export-driver", inf_name, str(package_dir)])
        if not list(package_dir.rglob("*.inf")):
            raise DriverBackupError(f"Windows не экспортировала выбранный пакет {inf_name}. Установка отменена.")
        exported += 1
    _write_manifest(target, exported, "Экспортированы только выбранные текущие пакеты драйверов.")
    return target, exported

def restore_driver_store(source: str | Path) -> str:
    folder = Path(source).expanduser().resolve()
    if not folder.is_dir():
        raise DriverBackupError("Папка резервной копии не найдена.")
    if not list(folder.rglob("*.inf")):
        raise DriverBackupError("В выбранной папке не найдены INF-файлы драйверов.")
    output = _run_pnputil(["/add-driver", str(folder / "*.inf"), "/subdirs", "/install"])
    return output or "Команда восстановления драйверов выполнена."
