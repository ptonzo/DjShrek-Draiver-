from __future__ import annotations

import json
import platform
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
            ["pnputil.exe", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
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


def backup_driver_store(destination: str | Path) -> tuple[Path, int]:
    target = Path(destination).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise DriverBackupError("Выберите пустую папку: существующие файлы не будут перезаписаны.")
    target.mkdir(parents=True, exist_ok=True)
    _run_pnputil(["/export-driver", "*", str(target)])
    inf_files = list(target.rglob("*.inf"))
    if not inf_files:
        raise DriverBackupError("Экспорт завершился без INF-файлов. Резервная копия не подтверждена.")
    manifest = {
        "application": "DjShrek Draiver",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "driver_packages_exported": len(inf_files),
        "restore_command": "pnputil /add-driver <backup-folder>\\*.inf /subdirs /install",
        "note": "Копия пакетов драйверов; не является образом Windows и не гарантирует откат каждого устройства.",
    }
    (target / "djshrek-backup.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target, len(inf_files)


def restore_driver_store(source: str | Path) -> str:
    folder = Path(source).expanduser().resolve()
    if not folder.is_dir():
        raise DriverBackupError("Папка резервной копии не найдена.")
    if not list(folder.rglob("*.inf")):
        raise DriverBackupError("В выбранной папке не найдены INF-файлы драйверов.")
    output = _run_pnputil(["/add-driver", str(folder / "*.inf"), "/subdirs", "/install"])
    return output or "Команда восстановления драйверов выполнена."
