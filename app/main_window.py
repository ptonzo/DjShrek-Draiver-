from __future__ import annotations

import sys
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView)
from app.export import export_devices_csv
from app.scanner import Device, ScanError, scan_devices


class ScanWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    def run(self):
        try:
            self.completed.emit(scan_devices())
        except ScanError as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    headers = ["Устройство", "Производитель", "Состояние", "Класс", "Версия драйвера", "Дата драйвера"]
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DjShrek Draiver")
        self.resize(1120, 700)
        self.devices: list[Device] = []
        self.worker = None
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("DjShrek Draiver")
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addWidget(QLabel("Проверка оборудования и установленных драйверов"))
        controls = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск устройства или производителя…")
        self.search.textChanged.connect(self.render_rows)
        self.scan_button = QPushButton("Сканировать компьютер")
        self.scan_button.clicked.connect(self.start_scan)
        self.export_button = QPushButton("Экспорт CSV")
        self.export_button.clicked.connect(self.export_csv)
        controls.addWidget(self.search, 1)
        controls.addWidget(self.scan_button)
        controls.addWidget(self.export_button)
        layout.addLayout(controls)
        self.table = QTableWidget(0, len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        self.status = QLabel("Готово. Нажмите «Сканировать компьютер».")
        layout.addWidget(self.status)
        self.setCentralWidget(root)
        self.setStyleSheet("QMainWindow{background:#101827} QWidget{color:#e8eef8;font-size:10pt} QLabel#title{font-size:25pt;font-weight:700;color:white} QLineEdit,QTableWidget{background:#172338;border:1px solid #2d405d;border-radius:7px;padding:8px;color:#f2f6fc} QHeaderView::section{background:#22334d;color:#e8eef8;padding:8px;border:0} QTableWidget{alternate-background-color:#1b2a41;gridline-color:#2b3d58} QPushButton{background:#2864d7;color:white;border:0;border-radius:7px;padding:10px 14px;font-weight:600} QPushButton:hover{background:#3978eb}")
    def start_scan(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self.scan_button.setEnabled(False)
        self.status.setText("Получение списка устройств Windows…")
        self.worker = ScanWorker(self)
        self.worker.completed.connect(self.on_scan_finished)
        self.worker.failed.connect(self.on_scan_failed)
        self.worker.finished.connect(lambda: self.scan_button.setEnabled(True))
        self.worker.start()
    def on_scan_finished(self, devices):
        self.devices = devices
        self.render_rows()
        self.status.setText(f"Найдено устройств: {len(devices)}. Установка драйверов не выполнялась.")
    def on_scan_failed(self, message):
        self.status.setText("Сканирование не завершено.")
        QMessageBox.warning(self, "Ошибка сканирования", message)
    def render_rows(self):
        query = self.search.text().casefold().strip()
        rows = [d for d in self.devices if not query or query in " ".join([d.name, d.manufacturer, d.class_name, d.status, d.driver_version]).casefold()]
        self.table.setRowCount(len(rows))
        for i, d in enumerate(rows):
            for j, value in enumerate([d.name, d.manufacturer, d.status, d.class_name, d.driver_version, d.driver_date]):
                item = QTableWidgetItem(value)
                item.setToolTip(d.device_id if j == 0 else value)
                if j == 2 and value.casefold() != "ok":
                    item.setForeground(Qt.GlobalColor.yellow)
                self.table.setItem(i, j, item)
    def export_csv(self):
        if not self.devices:
            QMessageBox.information(self, "Экспорт", "Сначала выполните сканирование.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Сохранить список устройств", "djshrek-devices.csv", "CSV (*.csv)")
        if not filename:
            return
        try:
            export_devices_csv(self.devices, filename)
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка экспорта", str(exc))
            return
        self.status.setText(f"Список сохранён: {filename}")


def main():
    if sys.platform != "win32":
        print("DjShrek Draiver предназначен для Windows 10/11.")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
