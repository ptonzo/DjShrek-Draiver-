from __future__ import annotations

import sys
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QIcon
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QHeaderView, QTabWidget, QGridLayout, QProgressBar, QFrame,
)
from app.export import export_devices_csv
from app.scanner import Device, ScanError, scan_devices
from app.windows_update import DriverUpdate, WindowsUpdateError, find_driver_updates, install_driver_update
from app.driver_backup import DriverBackupError, backup_driver_store, restore_driver_store
from app.telemetry import TelemetryError, collect_system_snapshot, SystemSnapshot


class ScanWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    def run(self):
        try:
            self.completed.emit(scan_devices())
        except ScanError as exc:
            self.failed.emit(str(exc))


class TelemetryWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    def run(self):
        try:
            self.completed.emit(collect_system_snapshot())
        except TelemetryError as exc:
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


class MetricCard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        self.heading = QLabel(title.upper())
        self.heading.setObjectName("metricHeading")
        self.value = QLabel("—")
        self.value.setObjectName("metricValue")
        self.detail = QLabel("Ожидание данных")
        self.detail.setObjectName("metricDetail")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        layout.addWidget(self.heading)
        layout.addWidget(self.value)
        layout.addWidget(self.bar)
        layout.addWidget(self.detail)

    def set_metric(self, value: str, percent: float | None, detail: str):
        self.value.setText(value)
        self.detail.setText(detail)
        if percent is None:
            self.bar.setRange(0, 1)
            self.bar.setValue(0)
            self.bar.setFormat("НЕТ ДАННЫХ")
        else:
            self.bar.setRange(0, 100)
            self.bar.setValue(max(0, min(100, int(percent))))
            self.bar.setFormat("%p%")


class MainWindow(QMainWindow):
    device_headers = ["Устройство", "Производитель", "Состояние", "Класс", "Версия драйвера", "Дата драйвера"]
    update_headers = ["Доступный драйвер", "Описание", "Загружен"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DjShrek Draiver — Cyber Club Edition")
        icon_path = Path(__file__).resolve().parent / "assets" / "DjShrek-Draiver.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1320, 860)
        self.devices: list[Device] = []
        self.updates: list[DriverUpdate] = []
        self.scan_worker = None
        self.telemetry_worker = None
        self.update_worker = None
        self.install_worker = None
        self._telemetry_busy = False

        root = QWidget()
        layout = QVBoxLayout(root)
        header = QHBoxLayout()
        brand = QVBoxLayout()
        title = QLabel("DjShrek Draiver")
        title.setObjectName("title")
        subtitle = QLabel("NEON GAMING  /  PC CONTROL CENTER")
        subtitle.setObjectName("subtitle")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand, 1)
        self.refresh_button = QPushButton("Обновить мониторинг")
        self.refresh_button.clicked.connect(self.refresh_telemetry)
        header.addWidget(self.refresh_button)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.build_dashboard_tab()
        self.build_devices_tab()
        self.build_updates_tab()

        self.status = QLabel("Инициализация мониторинга…")
        self.status.setObjectName("status")
        layout.addWidget(self.status)
        self.setCentralWidget(root)

        self.setStyleSheet("""
            QMainWindow { background: #080817; }
            QWidget { color: #f2edff; font-size: 10pt; }
            QLabel#title { font-size: 27pt; font-weight: 900; color: #ffffff; }
            QLabel#subtitle { color: #31e8ff; font-size: 9pt; font-weight: 900; letter-spacing: 2px; }
            QLabel#status { color: #d8d0ff; padding: 9px 12px; background: #17142c; border: 1px solid #6738a8; border-radius: 8px; }
            QLabel#hint { color: #b8afd6; padding: 8px 2px; }
            QLabel#metricHeading { color: #b8a7e8; font-size: 8pt; font-weight: 800; }
            QLabel#metricValue { color: #ffffff; font-size: 23pt; font-weight: 900; }
            QLabel#metricDetail { color: #c3b9df; font-size: 9pt; }
            QLabel#sectionTitle { color: #ff70df; font-size: 13pt; font-weight: 900; padding: 5px 0; }
            QFrame#metricCard, QFrame#infoCard { background: #151329; border: 1px solid #6636a6; border-radius: 11px; }
            QLineEdit, QTableWidget { background: #151329; border: 1px solid #50327e; border-radius: 8px; padding: 9px; color: #ffffff; selection-background-color: #7c35d8; }
            QLineEdit:focus { border: 1px solid #2de7ff; }
            QHeaderView::section { background: #24183d; color: #ffc5f3; padding: 10px; border: 0; border-bottom: 2px solid #ed36bd; font-weight: 800; }
            QTableWidget { alternate-background-color: #1d1834; gridline-color: #382653; }
            QPushButton { background: #7b35d8; color: #ffffff; border: 1px solid #b45cff; border-radius: 8px; padding: 11px 15px; font-weight: 900; }
            QPushButton:hover { background: #a23cff; border-color: #35eaff; }
            QPushButton:pressed { background: #5420a4; }
            QPushButton:disabled { background: #302846; color: #9185aa; border-color: #49365f; }
            QProgressBar { background: #29203d; border: 1px solid #563778; border-radius: 4px; height: 8px; color: #ffffff; }
            QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #27dfff,stop:1 #f13ac8); border-radius: 4px; }
            QTabWidget::pane { border: 1px solid #563778; border-radius: 10px; top: -1px; background: #100e20; }
            QTabBar::tab { background: #1a1630; color: #b7a9d8; padding: 12px 20px; margin-right: 4px; border-top-left-radius: 8px; border-top-right-radius: 8px; }
            QTabBar::tab:selected { background: #3a1e5d; color: #ffffff; border-bottom: 3px solid #2de7ff; }
            QTabBar::tab:hover { color: #ff8ee5; }
        """)

        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.setInterval(2500)
        self.telemetry_timer.timeout.connect(self.refresh_telemetry)
        self.telemetry_timer.start()
        QTimer.singleShot(250, self.refresh_telemetry)

    def build_dashboard_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(self.section_label("МОНИТОРИНГ В РЕАЛЬНОМ ВРЕМЕНИ"))
        grid = QGridLayout()
        self.cpu_card = MetricCard("Процессор · загрузка")
        self.memory_card = MetricCard("Оперативная память")
        self.disk_card = MetricCard("Системный диск")
        self.gpu_card = MetricCard("Видеокарта")
        for index, card in enumerate([self.cpu_card, self.memory_card, self.disk_card, self.gpu_card]):
            grid.addWidget(card, index // 2, index % 2)
        layout.addLayout(grid)

        layout.addWidget(self.section_label("ОБОРУДОВАНИЕ И СИСТЕМА"))
        info = QGridLayout()
        self.info_labels = {}
        fields = [
            ("cpu", "Процессор"), ("gpu", "Графика"),
            ("ram", "Память"), ("os", "Операционная система"),
            ("disk", "Системный накопитель"), ("uptime", "Время работы"),
            ("cpu_temp", "Температура ACPI"), ("gpu_temp", "Температура GPU"),
        ]
        for index, (key, caption) in enumerate(fields):
            card = QFrame()
            card.setObjectName("infoCard")
            card_layout = QVBoxLayout(card)
            label = QLabel(caption.upper())
            label.setObjectName("metricHeading")
            value = QLabel("Сбор данных…")
            value.setWordWrap(True)
            value.setObjectName("metricDetail")
            card_layout.addWidget(label)
            card_layout.addWidget(value)
            self.info_labels[key] = value
            info.addWidget(card, index // 2, index % 2)
        layout.addLayout(info)
        note = QLabel("Температуры отображаются только при наличии поддерживаемого датчика. Отсутствие показаний не означает нулевую температуру.")
        note.setObjectName("hint")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        self.tabs.addTab(tab, "Центр управления")

    @staticmethod
    def section_label(text: str):
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def build_devices_tab(self):
        device_tab = QWidget()
        device_layout = QVBoxLayout(device_tab)
        controls = QHBoxLayout()
        self.device_search = QLineEdit()
        self.device_search.setPlaceholderText("Поиск устройства или производителя…")
        self.device_search.textChanged.connect(self.render_devices)
        self.scan_button = QPushButton("Сканировать устройства")
        self.scan_button.clicked.connect(self.start_scan)
        self.export_button = QPushButton("Экспорт CSV")
        self.export_button.clicked.connect(self.export_csv)
        self.backup_button = QPushButton("Создать копию драйверов")
        self.backup_button.clicked.connect(self.create_driver_backup)
        self.restore_button = QPushButton("Восстановить из копии")
        self.restore_button.clicked.connect(self.restore_driver_backup)
        for widget in [self.device_search, self.scan_button, self.export_button, self.backup_button, self.restore_button]:
            controls.addWidget(widget, 1 if widget is self.device_search else 0)
        device_layout.addLayout(controls)
        self.device_table = QTableWidget(0, len(self.device_headers))
        self.device_table.setHorizontalHeaderLabels(self.device_headers)
        self.configure_table(self.device_table)
        device_layout.addWidget(self.device_table, 1)
        self.tabs.addTab(device_tab, "Устройства и драйверы")

    def build_updates_tab(self):
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

    @staticmethod
    def configure_table(table):
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def refresh_telemetry(self):
        if self._telemetry_busy or sys.platform != "win32":
            return
        self._telemetry_busy = True
        self.refresh_button.setEnabled(False)
        self.telemetry_worker = TelemetryWorker(self)
        self.telemetry_worker.completed.connect(self.on_telemetry_finished)
        self.telemetry_worker.failed.connect(self.on_telemetry_failed)
        self.telemetry_worker.finished.connect(self.on_telemetry_worker_finished)
        self.telemetry_worker.start()

    def on_telemetry_worker_finished(self):
        self._telemetry_busy = False
        self.refresh_button.setEnabled(True)

    def on_telemetry_finished(self, snapshot: SystemSnapshot):
        self.cpu_card.set_metric(f"{snapshot.cpu_percent:.0f}%", snapshot.cpu_percent, f"{snapshot.cpu_name}")
        self.memory_card.set_metric(f"{snapshot.memory_percent:.0f}%", snapshot.memory_percent,
                                    f"{snapshot.memory_used_gb:.1f} / {snapshot.memory_total_gb:.1f} GB")
        self.disk_card.set_metric(f"{snapshot.disk_percent:.0f}%", snapshot.disk_percent,
                                  f"{snapshot.disk_used_gb:.0f} / {snapshot.disk_total_gb:.0f} GB · {snapshot.disk_name}")
        self.gpu_card.set_metric(f"{snapshot.gpu_percent:.0f}%" if snapshot.gpu_percent is not None else "Н/Д",
                                 snapshot.gpu_percent, snapshot.gpu_name)
        values = {
            "cpu": snapshot.cpu_name,
            "gpu": snapshot.gpu_name,
            "ram": f"{snapshot.memory_total_gb:.1f} GB",
            "os": snapshot.os_name,
            "disk": snapshot.disk_name,
            "uptime": snapshot.uptime,
            "cpu_temp": f"{snapshot.cpu_temp_c:.0f} °C (ACPI)" if snapshot.cpu_temp_c is not None else "Нет доступного датчика",
            "gpu_temp": f"{snapshot.gpu_temp_c:.0f} °C" if snapshot.gpu_temp_c is not None else "Нет доступного датчика",
        }
        for key, value in values.items():
            self.info_labels[key].setText(value or "Не определено")
        self.status.setText(f"Мониторинг обновлён · {snapshot.timestamp} · обновление каждые 2,5 секунды")

    def on_telemetry_failed(self, message: str):
        self.status.setText("Мониторинг недоступен: " + message)

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

    def create_driver_backup(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите пустую папку для резервной копии")
        if not folder:
            return
        try:
            target, count = backup_driver_store(folder)
        except DriverBackupError as exc:
            QMessageBox.warning(self, "Резервная копия", str(exc))
            return
        self.status.setText(f"Экспортировано пакетов драйверов: {count}. Папка: {target}")
        QMessageBox.information(self, "Резервная копия", f"Скопировано пакетов драйверов: {count}\n\n{target}")

    def restore_driver_backup(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку резервной копии")
        if not folder:
            return
        answer = QMessageBox.warning(
            self, "Подтверждение восстановления",
            "Добавить драйверы из выбранной копии в Driver Store? Windows может заменить драйверы устройств.\n\n"
            "Рекомендуется закрыть программы и заранее создать точку восстановления Windows.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            message = restore_driver_store(folder)
        except DriverBackupError as exc:
            QMessageBox.warning(self, "Восстановление драйверов", str(exc))
            return
        self.status.setText("Команда восстановления выполнена. " + message[:300])
        QMessageBox.information(self, "Восстановление драйверов", message or "Команда восстановления выполнена.")

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
