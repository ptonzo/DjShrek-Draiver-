from __future__ import annotations

import json
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime

import psutil


@dataclass(slots=True)
class SystemSnapshot:
    timestamp: str
    cpu_name: str
    cpu_percent: float
    memory_total_gb: float
    memory_used_gb: float
    memory_percent: float
    disk_name: str
    disk_total_gb: float
    disk_used_gb: float
    disk_percent: float
    gpu_name: str
    gpu_percent: float | None
    cpu_temp_c: float | None
    gpu_temp_c: float | None
    os_name: str
    uptime: str


class TelemetryError(RuntimeError):
    pass


def _powershell_hardware() -> dict:
    script = r"""
$ErrorActionPreference = 'Stop'
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name
$gpu = Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name
$os = Get-CimInstance Win32_OperatingSystem | Select-Object -First 1
$thermal = @()
try {
  $thermal = @(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction Stop |
    ForEach-Object { [math]::Round(($_.CurrentTemperature / 10) - 273.15, 1) })
} catch {}
[pscustomobject]@{
  Cpu = [string]$cpu
  Gpu = @($gpu)
  Os = "$($os.Caption) (сборка $($os.BuildNumber))"
  Thermal = @($thermal)
} | ConvertTo-Json -Depth 4 -Compress
"""
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if result.returncode or not result.stdout.strip():
        return {}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _nvidia_metrics() -> tuple[str | None, float | None, float | None]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None, None, None
    try:
        result = subprocess.run(
            [executable, "--query-gpu=name,utilization.gpu,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=8, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, None, None
    if result.returncode or not result.stdout.strip():
        return None, None, None
    fields = [part.strip() for part in result.stdout.splitlines()[0].split(",")]
    if len(fields) < 3:
        return None, None, None
    try:
        return fields[0], float(fields[1]), float(fields[2])
    except ValueError:
        return fields[0], None, None


def collect_system_snapshot() -> SystemSnapshot:
    if platform.system() != "Windows":
        raise TelemetryError("Аппаратный мониторинг доступен в Windows 10/11.")
    try:
        cpu_percent = float(psutil.cpu_percent(interval=0.15))
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        boot_time = psutil.boot_time()
    except (OSError, RuntimeError) as exc:
        raise TelemetryError(f"Не удалось получить системные показатели: {exc}") from exc

    hardware = _powershell_hardware()
    gpu_name, gpu_percent, gpu_temp = _nvidia_metrics()
    gpu_names = hardware.get("Gpu") or []
    if isinstance(gpu_names, str):
        gpu_names = [gpu_names]
    if not gpu_name:
        gpu_name = str(gpu_names[0]) if gpu_names else "Не определена"
    thermal = hardware.get("Thermal") or []
    if isinstance(thermal, (int, float)):
        thermal = [thermal]
    cpu_temp = None
    valid_temps = [float(value) for value in thermal if isinstance(value, (int, float)) and 0 < float(value) < 120]
    if valid_temps:
        cpu_temp = max(valid_temps)

    uptime_seconds = max(0, int(time.time() - boot_time))
    hours, remainder = divmod(uptime_seconds, 3600)
    days, hours = divmod(hours, 24)
    uptime = f"{days} дн. {hours} ч." if days else f"{hours} ч. {remainder // 60} мин."
    disk_partitions = [p for p in psutil.disk_partitions(all=False) if p.mountpoint.upper() == "C:\\"]
    disk_name = disk_partitions[0].device if disk_partitions else "Диск C:"
    return SystemSnapshot(
        timestamp=datetime.now().strftime("%H:%M:%S"),
        cpu_name=str(hardware.get("Cpu") or platform.processor() or "Не определён"),
        cpu_percent=cpu_percent,
        memory_total_gb=memory.total / (1024 ** 3),
        memory_used_gb=memory.used / (1024 ** 3),
        memory_percent=float(memory.percent),
        disk_name=disk_name,
        disk_total_gb=disk.total / (1024 ** 3),
        disk_used_gb=disk.used / (1024 ** 3),
        disk_percent=float(disk.percent),
        gpu_name=gpu_name,
        gpu_percent=gpu_percent,
        cpu_temp_c=cpu_temp,
        gpu_temp_c=gpu_temp,
        os_name=str(hardware.get("Os") or platform.platform()),
        uptime=uptime,
    )
