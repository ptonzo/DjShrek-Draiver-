from pathlib import Path
import subprocess

import pytest

from app import driver_backup


def test_backup_requires_inf_and_writes_manifest(tmp_path, monkeypatch):
    def fake_run(args, **kwargs):
        Path(args[-1], "sample.inf").write_text("[Version]", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "Export complete", "")
    monkeypatch.setattr(driver_backup.platform, "system", lambda: "Windows")
    monkeypatch.setattr(driver_backup.subprocess, "run", fake_run)
    folder, count = driver_backup.backup_driver_store(tmp_path / "backup")
    assert count == 1
    assert (folder / "djshrek-backup.json").exists()


def test_backup_rejects_nonempty_destination(tmp_path, monkeypatch):
    folder = tmp_path / "not-empty"
    folder.mkdir()
    (folder / "keep.txt").write_text("x")
    monkeypatch.setattr(driver_backup.platform, "system", lambda: "Windows")
    with pytest.raises(driver_backup.DriverBackupError, match="пустую папку"):
        driver_backup.backup_driver_store(folder)


def test_restore_requires_inf_file(tmp_path, monkeypatch):
    monkeypatch.setattr(driver_backup.platform, "system", lambda: "Windows")
    with pytest.raises(driver_backup.DriverBackupError, match="INF-файлы"):
        driver_backup.restore_driver_store(tmp_path)
