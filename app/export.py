import csv
from pathlib import Path
from collections.abc import Iterable
from app.scanner import Device


def export_devices_csv(devices: Iterable[Device], destination: str | Path) -> None:
    with Path(destination).open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(["Устройство", "Производитель", "Состояние", "Класс", "ID оборудования", "Версия драйвера", "Дата драйвера"])
        for d in devices:
            writer.writerow([d.name, d.manufacturer, d.status, d.class_name, d.device_id, d.driver_version, d.driver_date])
