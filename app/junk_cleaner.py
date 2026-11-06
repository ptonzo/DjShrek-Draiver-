"""Conservative temporary-file cleanup for Windows.

Only files older than the configured retention period inside known temporary
folders are considered. The scanner never follows symlinks/reparse points and
never touches browser profiles, Downloads, Documents, or application data.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class JunkFile:
    path: str
    category: str
    size: int
    modified: float


@dataclass
class CleanupResult:
    deleted_files: int
    freed_bytes: int
    skipped_files: int
    errors: list[str]


def _temp_roots() -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    candidates = [
        ("Временные файлы пользователя", Path(tempfile.gettempdir())),
        ("Временные файлы Windows", Path(os.environ.get("WINDIR", r"C:\Windows")) / "Temp"),
    ]
    seen: set[str] = set()
    for label, path in candidates:
        try:
            resolved = str(path.resolve()).casefold()
        except OSError:
            continue
        if resolved not in seen and path.is_dir():
            seen.add(resolved)
            roots.append((label, path))
    return roots


def scan_junk_files(min_age_days: int = 7, max_files: int = 20000) -> list[JunkFile]:
    if sys.platform != "win32":
        raise OSError("Очистка временных файлов доступна только в Windows 10/11.")
    cutoff = time.time() - max(1, min_age_days) * 86400
    found: list[JunkFile] = []
    for category, root in _temp_roots():
        stack = [root]
        while stack and len(found) < max_files:
            folder = stack.pop()
            try:
                with os.scandir(folder) as entries:
                    for entry in entries:
                        if len(found) >= max_files:
                            break
                        try:
                            if entry.is_symlink():
                                continue
                            info = entry.stat(follow_symlinks=False)
                            if entry.is_dir(follow_symlinks=False):
                                # Avoid junctions/reparse points and stay inside temp roots.
                                if getattr(info, "st_file_attributes", 0) & 0x400:
                                    continue
                                stack.append(Path(entry.path))
                            elif entry.is_file(follow_symlinks=False) and info.st_mtime < cutoff:
                                found.append(JunkFile(entry.path, category, info.st_size, info.st_mtime))
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue
    return found


def clean_junk_files(files: list[JunkFile], min_age_days: int = 7) -> CleanupResult:
    if sys.platform != "win32":
        raise OSError("Очистка временных файлов доступна только в Windows.")
    cutoff = time.time() - max(1, min_age_days) * 86400
    allowed_roots = []
    for _, root in _temp_roots():
        try:
            allowed_roots.append(root.resolve())
        except OSError:
            pass
    deleted = freed = skipped = 0
    errors: list[str] = []
    for item in files:
        candidate = Path(item.path)
        try:
            resolved = candidate.resolve(strict=True)
            if not any(resolved == root or root in resolved.parents for root in allowed_roots):
                skipped += 1
                continue
            info = candidate.stat(follow_symlinks=False)
            if not candidate.is_file() or candidate.is_symlink() or info.st_mtime >= cutoff:
                skipped += 1
                continue
            # Avoid deleting a different file if the path changed after scanning.
            if info.st_size != item.size or info.st_mtime != item.modified:
                skipped += 1
                continue
            candidate.unlink()
            deleted += 1
            freed += info.st_size
        except PermissionError:
            skipped += 1
        except FileNotFoundError:
            skipped += 1
        except OSError as exc:
            skipped += 1
            if len(errors) < 20:
                errors.append(f"{candidate}: {exc}")
    return CleanupResult(deleted, freed, skipped, errors)
