from __future__ import annotations

import sys
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QHeaderView, QTabWidget,
)
from app.export import export_devices_csv
from app.scanner import Device, ScanError, scan_devices
from app.windows_update import DriverUpdate, WindowsUpdateError, find_driver_updates, install_driver_update


class ScanWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    def run(self):
        try:
            self.completed.emit(scan_devices())
        except ScanError as exc:
            self.failed.emit(str(exc))


class UpdateSearchWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    def run(self):
        try:
            self.completed.emit(find_driver_updates())
        except WindowsUpdateError as exc:
            self.failed.emit(str(exc))


class InstallWorker(QThread):
    completed = Signal(str)
    failed = Signal(str)
    def __init__(self, update: DriverUpdate, parent=None):
        super().__init__(parent)
        self.update_item = update
    def run(self):
        try:
            self.completed.emit(install_driver_update(self.update_item.update_id, self.update_item.revision))
        except WindowsUpdateError as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    device_headers = ["Устройство", "Производитель", "Состояние", "Класс", "Версия драйвера", "Дата драйвера"]
    update_headers = ["Доступный драйвер", "Описание", "Загружен"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DjShrek Draiver")
        self.resize(1180, 760)
        self.devices: list[Device] = []
        self.updates: list[DriverUpdate] = []
        self.scan_worker = None
        self.update_worker = None
        self.install_worker = None
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("DjShrek Draiver")
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addWidget(QLabel("Управление устройствами и обновлениями драйверов Windows"))
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        device_tab = QWidget()
        device_layout = QVBoxLayout(device_tab)
        controls = QHBoxLayout()
        self.device_search = QLineEdit()
        self.device_search.setPlaceholderText("Поиск устройства или производителя…")
        self.device_search.textChanged.connect(self.render_devices)
        self.scan_button = QPushButton("Сканировать компьютер")
        self.scan_button.clicked.connect(self.start_scan)
        self.export_button = QPushButton("Экспорт CSV")
        self.export_button.clicked.connect(self.export_csv)
        controls.addWidget(self.device_search, 1)
        controls.addWidget(self.scan_button)
        controls.addWidget(self.export_button)
        device_layout.addLayout(controls)
        self.device_table = QTableWidget(0, len(self.device_headers))
        self.device_table.setHorizontalHeaderLabels(self.device_headers)
        self.configure_table(self.device_table)
        device_layout.addWidget(self.device_table, 1)
        self.tabs.addTab(device_tab, "Мои устройства")

        update_tab = QWidget()
        update_layout = QVBoxLayout(update_tab)
        update_controls = QHBoxLayout()
        self.update_search_button = QPushButton("Проверить обновления Windows")
        self.update_search_button.clicked.connect(self.start_update_search)
        self.install_button = QPushButton("Установить выбранный драйвер")
        self.install_button.clicked.connect(self.install_selected)
        self.install_button.setEnabled(False)
        update_controls.addWidget(self.update_search_button)
        update_controls.addWidget(self.install_button)
        update_layout.addLayout(update_controls)
        self.update_table = QTableWidget(0, len(self.update_headers))
        self.update_table.setHorizontalHeaderLabels(self.update_headers)
        self.configure_table(self.update_table)
        self.update_table.itemSelectionChanged.connect(self.on_update_selection)
        update_layout.addWidget(self.update_table, 1)
        note = QLabel("Обновления поступают через Windows Update. Установка запускается только после выбора и подтверждения.")
        note.setWordWrap(True)
        note.setObjectName("hint")
        update_layout.addWidget(note)
        self.tabs.addTab(update_tab, "Обновления драйверов")

        self.status = QLabel("Готово. Выполните сканирование устройств или проверку обновлений.")
        self.status.setObjectName("status")
        layout.addWidget(self.status)
        self.setCentralWidget(root)
        self.setStyleSheet("""
            QMainWindow { background: #101827; }
            QWidget { color: #e8eef8; font-size: 10pt; }
            QLabel#title { font-size: 25pt; font-weight: 700; color: white; }
            QLabel#status, QLabel#hint { color: #9fb0c8; padding: 6px 0; }
            QLineEdit, QTableWidget { background: #172338; border: 1px solid #2d405d; border-radius: 7px; padding: 8px; color: #f2f6fc; }
            QHeaderView::section { background: #22334d; color: #e8eef8; padding: 8px; border: 0; }
            QTableWidget { alternate-background-color: #1b2a41; gridline-color: #2b3d58; }
            QPushButton { background: #2864d7; color: white; border: 0; border-radius: 7px; padding: 10px 14px; font-weight: 600; }
            QPushButton:hover { background: #3978eb; }
            QPushButton:disabled { background: #45536a; color: #aab5c4; }
            QTabBar::tab { background: #1b2a41; padding: 10px 18px; }
            QTabBar::tab:selected { background: #2864d7; }
        """)

    @staticmethod
    def configure_table(table):
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def start_scan(self):
        if self.scan_worker is not None and self.scan_worker.isRunning():
            return
        self.scan_button.setEnabled(False)
        self.status.setText("Получение списка устройств Windows…")
        self.scan_worker = ScanWorker(self)
        self.scan_worker.completed.connect(self.on_scan_finished)
        self.scan_worker.failed.connect(self.on_scan_failed)
        self.scan_worker.finished.connect(lambda: self.scan_button.setEnabled(True))
        self.scan_worker.start()

    def on_scan_finished(self, devices):
        self.devices = devices
        self.render_devices()
        self.status.setText(f"Найдено устройств: {len(devices)}. Установка не выполнялась.")

    def on_scan_failed(self, message):
        self.status.setText("Сканирование не завершено.")
        QMessageBox.warning(self, "Ошибка сканирования", message)

    def render_devices(self):
        query = self.device_search.text().casefold().strip()
        rows = [d for d in self.devices if not query or query in " ".join(
            [d.name, d.manufacturer, d.class_name, d.status, d.driver_version]
        ).casefold()]
        self.device_table.setRowCount(len(rows))
        for i, d in enumerate(rows):
            values = [d.name, d.manufacturer, d.status, d.class_name, d.driver_version, d.driver_date]
            for j, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(d.device_id if j == 0 else value)
                if j == 2 and value.casefold() != "ok":
                    item.setForeground(Qt.GlobalColor.yellow)
                self.device_table.setItem(i, j, item)

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

    def start_update_search(self):
        if sys.platform != "win32":
            QMessageBox.information(self, "Windows Update", "Проверка доступна только в Windows 10/11.")
            return
        if self.update_worker is not None and self.update_worker.isRunning():
            return
        self.update_search_button.setEnabled(False)
        self.install_button.setEnabled(False)
        self.status.setText("Поиск драйверов через Windows Update…")
        self.update_worker = UpdateSearchWorker(self)
        self.update_worker.completed.connect(self.on_updates_found)
        self.update_worker.failed.connect(self.on_update_error)
        self.update_worker.finished.connect(lambda: self.update_search_button.setEnabled(True))
        self.update_worker.start()

    def on_updates_found(self, updates):
        self.updates = updates
        self.update_table.setRowCount(len(updates))
        for row, update in enumerate(updates):
            for col, value in enumerate([update.title, update.description, "Да" if update.downloaded else "Нет"]):
                self.update_table.setItem(row, col, QTableWidgetItem(value))
        self.status.setText(f"Windows Update обнаружил драйверов: {len(updates)}.")
        if not updates:
            QMessageBox.information(self, "Обновления драйверов", "Доступные обновления драйверов не найдены.")

    def on_update_selection(self):
        self.install_button.setEnabled(self.update_table.currentRow() >= 0 and bool(self.updates))

    def install_selected(self):
        row = self.update_table.currentRow()
        if row < 0 or row >= len(self.updates):
            return
        update = self.updates[row]
        answer = QMessageBox.warning(
            self, "Подтверждение установки",
            "Установить драйвер через Windows Update?\n\n" + update.title +
            "\n\nЗакройте важные программы. Некоторым обновлениям потребуется перезагрузка.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.install_button.setEnabled(False)
        self.update_search_button.setEnabled(False)
        self.status.setText("Загрузка и установка: " + update.title)
        self.install_worker = InstallWorker(update, self)
        self.install_worker.completed.connect(self.on_install_finished)
        self.install_worker.failed.connect(self.on_update_error)
        self.install_worker.finished.connect(lambda: self.update_search_button.setEnabled(True))
        self.install_worker.start()

    def on_install_finished(self, message):
        self.status.setText(message)
        QMessageBox.information(self, "Windows Update", message)
        self.start_update_search()

    def on_update_error(self, message):
        self.status.setText("Операция Windows Update не завершена.")
        QMessageBox.warning(self, "Windows Update", message)


def main():
    if sys.platform != "win32":
        print("DjShrek Draiver предназначен для Windows 10/11.")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
