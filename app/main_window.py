from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSettings
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QHeaderView, QTabWidget, QGridLayout, QProgressBar, QFrame, QPlainTextEdit, QComboBox,
)
from app.export import export_devices_csv
from app.scanner import Device, ScanError, scan_devices
from app.driver_backup import DriverBackupError, backup_driver_store, backup_selected_driver_packages, restore_driver_store
from app.driver_catalog import DriverCatalogError, search_driver_updates, install_driver_updates
from app.telemetry import TelemetryError, collect_system_snapshot, SystemSnapshot
from app.driver_sources import source_for_device, open_official_source
from app.vendor_utilities import detect_vendor_utilities, open_vendor_scan_page, scan_dell_updates
from app.i18n import LANGUAGES, system_language, translate
from app.updater import check_latest_release, download_and_schedule, UpdateError
from app.registry_checker import RegistryFinding, scan_registry, repair_stale_startup_entry
from app.junk_cleaner import JunkFile, scan_junk_files, clean_junk_files, CleanupResult


class ScanWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    def run(self):
        try:
            self.completed.emit(scan_devices())
        except ScanError as exc:
            self.failed.emit(str(exc))


class CatalogSearchWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    def __init__(self, devices, parent=None):
        super().__init__(parent)
        self.devices = devices
    def run(self):
        try:
            self.completed.emit(search_driver_updates(self.devices))
        except DriverCatalogError as exc:
            self.failed.emit(str(exc))


class DriverInstallWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    def __init__(self, updates, parent=None):
        super().__init__(parent)
        self.updates = updates
    def run(self):
        try:
            self.completed.emit(install_driver_updates(self.updates))
        except DriverCatalogError as exc:
            self.failed.emit(str(exc))


class RegistryScanWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            self.completed.emit(scan_registry())
        except OSError as exc:
            self.failed.emit(str(exc))


class TelemetryWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    def run(self):
        try:
            self.completed.emit(collect_system_snapshot())
        except TelemetryError as exc:
            self.failed.emit(str(exc))


class DellScanWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, executable: str, parent=None):
        super().__init__(parent)
        self.executable = executable

    def run(self):
        try:
            self.completed.emit(scan_dell_updates(self.executable))
        except RuntimeError as exc:
            self.failed.emit(str(exc))


class UpdateCheckWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            self.completed.emit(check_latest_release())
        except UpdateError as exc:
            self.failed.emit(str(exc))


class JunkScanWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            self.completed.emit(scan_junk_files())
        except OSError as exc:
            self.failed.emit(str(exc))


class JunkCleanWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, files: list[JunkFile], parent=None):
        super().__init__(parent)
        self.files = files

    def run(self):
        try:
            self.completed.emit(clean_junk_files(self.files))
        except OSError as exc:
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
        self.settings_store = QSettings("DjShrek", "CyberClub")
        self.language = self.settings_store.value("language", system_language(), type=str)
        if self.language not in LANGUAGES:
            self.language = system_language()
        self.setWindowTitle("DjShrek Draiver")
        self.resize(1320, 860)
        self.devices: list[Device] = []
        self.updates: list[DriverUpdate] = []
        self.scan_worker = None
        self.telemetry_worker = None
        self.update_worker = None
        self.install_worker = None
        self._telemetry_busy = False
        self.update_check_worker = None
        self.pending_app_update = None

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
        layout.addLayout(header)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.build_dashboard_tab()
        self.build_devices_tab()
        self.build_updates_tab()
        self.build_registry_tab()
        self.build_junk_tab()
        self.build_settings_tab()

        self.status = QLabel("Инициализация мониторинга…")
        self.status.setObjectName("status")
        layout.addWidget(self.status)
        self.setCentralWidget(root)
        self.apply_language()

        self.apply_theme()

        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.setInterval(2500)
        self.telemetry_timer.timeout.connect(self.refresh_telemetry)
        self.telemetry_timer.start()
        QTimer.singleShot(250, self.refresh_telemetry)
        QTimer.singleShot(1800, self.check_application_updates)

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
        layout.addWidget(self.section_label("ЖУРНАЛ СОБЫТИЙ"))
        self.event_log = QPlainTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMaximumHeight(112)
        self.event_log.appendPlainText("Панель управления запущена.")
        layout.addWidget(self.event_log)
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
        self.update_search_button = QPushButton("Проверить наличие обновлений драйверов")
        self.update_search_button.clicked.connect(self.start_update_search)
        self.vendor_tools_button = QPushButton("Проверить утилиты Intel / AMD / Dell")
        self.vendor_tools_button.clicked.connect(self.check_vendor_utilities)
        update_controls.addWidget(self.update_search_button, 2)
        update_controls.addWidget(self.vendor_tools_button, 1)
        update_layout.addLayout(update_controls)
        selection_controls = QHBoxLayout()
        self.select_all_updates_button = QPushButton("Выделить все")
        self.select_all_updates_button.clicked.connect(self.select_all_update_rows)
        selection_controls.addWidget(self.select_all_updates_button)
        self.update_install_button = QPushButton("Создать резервную копию и обновить выбранные")
        self.update_install_button.clicked.connect(self.update_selected_drivers)
        selection_controls.addWidget(self.update_install_button)
        update_layout.addLayout(selection_controls)
        self.update_table = QTableWidget(0, 5)
        self.update_table.setHorizontalHeaderLabels([
            "Выбрать", "Устройство", "Доступный драйвер", "Версия", "Дата"
        ])
        self.configure_table(self.update_table)
        update_layout.addWidget(self.update_table, 1)
        note = QLabel(
            "Поиск совместимых драйверов выполняется через службу Microsoft Update Catalog. "
            "Обычное автоматическое обновление Windows не включается. Выбранные текущие пакеты "
            "сначала экспортируются в резервную копию, затем выбранные предложения загружаются "
            "и устанавливаются средствами Microsoft Update Agent."
        )
        note.setWordWrap(True)
        note.setObjectName("hint")
        update_layout.addWidget(note)
        self.tabs.addTab(update_tab, "Обновления драйверов")

    def build_registry_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(self.section_label("ДИАГНОСТИКА РЕЕСТРА WINDOWS"))
        note = QLabel(
            "Проверяются записи автозапуска Run и RunOnce (HKCU/HKLM). "
            "Сканирование не изменяет реестр. Автоматическое исправление доступно "
            "только для записи, указывающей на отсутствующий EXE-файл; перед удалением "
            "создаётся .reg резервная копия. Остальные подозрительные записи требуют ручной проверки."
        )
        note.setWordWrap(True)
        note.setObjectName("hint")
        layout.addWidget(note)
        controls = QHBoxLayout()
        self.registry_scan_button = QPushButton("Проверить реестр")
        self.registry_scan_button.clicked.connect(self.start_registry_scan)
        self.registry_fix_button = QPushButton("Исправить выбранную ошибку")
        self.registry_fix_button.setEnabled(False)
        self.registry_fix_button.clicked.connect(self.fix_selected_registry_finding)
        controls.addWidget(self.registry_scan_button)
        controls.addWidget(self.registry_fix_button)
        layout.addLayout(controls)
        self.registry_table = QTableWidget(0, 5)
        self.registry_table.setHorizontalHeaderLabels(["Статус", "Раздел", "Имя записи", "Данные", "Результат проверки"])
        self.configure_table(self.registry_table)
        self.registry_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.registry_table.itemSelectionChanged.connect(self.on_registry_selection_changed)
        layout.addWidget(self.registry_table, 1)
        self.registry_findings: list[RegistryFinding] = []
        self.tabs.addTab(tab, "Проверка реестра")

    def start_registry_scan(self):
        if sys.platform != "win32":
            QMessageBox.information(self, "Проверка реестра", "Функция доступна только в Windows 10/11.")
            return
        if getattr(self, "registry_worker", None) is not None and self.registry_worker.isRunning():
            return
        self.registry_scan_button.setEnabled(False)
        self.registry_fix_button.setEnabled(False)
        self.registry_table.setRowCount(0)
        self.status.setText("Проверка записей автозапуска Windows…")
        self.registry_worker = RegistryScanWorker(self)
        self.registry_worker.completed.connect(self.on_registry_scan_finished)
        self.registry_worker.failed.connect(self.on_registry_scan_failed)
        self.registry_worker.finished.connect(lambda: self.registry_scan_button.setEnabled(True))
        self.registry_worker.start()

    def on_registry_scan_finished(self, findings):
        self.registry_findings = findings
        self.render_registry_findings()
        errors = sum(1 for item in findings if item.severity == "Ошибка")
        self.status.setText(
            f"Проверка завершена. Проверено разделов автозапуска: 4. Замечаний: {len(findings)}, "
            f"подтверждённых ошибок: {errors}. Реестр не изменялся."
        )
        self.event_log.appendPlainText(
            f"Проверка реестра: замечаний {len(findings)}, ошибок {errors}; изменений не выполнялось."
        )

    def on_registry_scan_failed(self, message):
        self.status.setText("Проверка реестра не завершена.")
        QMessageBox.warning(self, "Проверка реестра", message)

    def render_registry_findings(self):
        self.registry_table.setRowCount(len(self.registry_findings))
        for row, finding in enumerate(self.registry_findings):
            values = [
                finding.severity,
                finding.hive + "\\" + finding.subkey,
                finding.value_name or "—",
                finding.value_data or "—",
                finding.issue,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.registry_table.setItem(row, col, item)
        self.registry_table.resizeRowsToContents()
        if not self.registry_findings:
            self.registry_table.setRowCount(1)
            self.registry_table.setItem(0, 0, QTableWidgetItem("OK"))
            self.registry_table.setItem(0, 4, QTableWidgetItem("Подозрительных записей автозапуска не обнаружено."))

    def on_registry_selection_changed(self):
        row = self.registry_table.currentRow()
        can_fix = 0 <= row < len(self.registry_findings) and self.registry_findings[row].repairable
        self.registry_fix_button.setEnabled(bool(can_fix))

    def fix_selected_registry_finding(self):
        row = self.registry_table.currentRow()
        if not (0 <= row < len(self.registry_findings)):
            return
        finding = self.registry_findings[row]
        if not finding.repairable:
            QMessageBox.information(self, "Исправление", "Для этой записи автоматическое исправление не поддерживается.")
            return
        answer = QMessageBox.warning(
            self, "Подтверждение исправления",
            f"Программа обнаружила отсутствующий файл автозапуска. Удалить только эту запись?\n\n"
            f"Раздел: {finding.hive}\\{finding.subkey}\n"
            f"Имя: {finding.value_name}\nДанные: {finding.value_data}\n\n"
            "Перед изменением будет экспортирована резервная копия раздела реестра.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            backup = repair_stale_startup_entry(finding)
        except (OSError, RuntimeError, ValueError) as exc:
            QMessageBox.critical(self, "Исправление реестра", str(exc))
            return
        QMessageBox.information(self, "Исправление выполнено", f"Запись удалена. Резервная копия:\n{backup}")
        self.start_registry_scan()

    def build_junk_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(self.section_label("БЫСТРАЯ ПРОВЕРКА ВРЕМЕННЫХ ФАЙЛОВ"))
        note = QLabel(
            "Проверяются только временные папки Windows и текущего пользователя. "
            "В список попадают файлы старше 7 дней. Загрузки, документы, фотографии, "
            "корзина, кэш браузеров и личные данные не затрагиваются. Заблокированные "
            "Windows файлы будут пропущены."
        )
        note.setWordWrap(True)
        note.setObjectName("hint")
        layout.addWidget(note)
        controls = QHBoxLayout()
        self.junk_scan_button = QPushButton("Быстрая проверка")
        self.junk_scan_button.clicked.connect(self.start_junk_scan)
        self.junk_clean_button = QPushButton("Очистить выбранное")
        self.junk_clean_button.setEnabled(False)
        self.junk_clean_button.clicked.connect(self.confirm_junk_cleanup)
        controls.addWidget(self.junk_scan_button)
        controls.addWidget(self.junk_clean_button)
        layout.addLayout(controls)
        self.junk_summary = QLabel("Проверка ещё не запускалась.")
        self.junk_summary.setObjectName("metricDetail")
        layout.addWidget(self.junk_summary)
        self.junk_table = QTableWidget(0, 3)
        self.junk_table.setHorizontalHeaderLabels(["Выбрать", "Категория", "Объём"])
        self.configure_table(self.junk_table)
        self.junk_table.setColumnWidth(0, 90)
        self.junk_table.setColumnWidth(1, 420)
        layout.addWidget(self.junk_table, 1)
        self.junk_files: list[JunkFile] = []
        self.junk_categories: dict[str, list[JunkFile]] = {}
        self.junk_table.itemChanged.connect(self.on_junk_selection_changed)
        self.tabs.addTab(tab, "Очистка компьютера")

    @staticmethod
    def format_bytes(value: int) -> str:
        amount = float(value)
        for unit in ("Б", "КБ", "МБ", "ГБ"):
            if amount < 1024 or unit == "ГБ":
                return f"{amount:.1f} {unit}"
            amount /= 1024
        return f"{amount:.1f} ГБ"

    def start_junk_scan(self):
        if sys.platform != "win32":
            QMessageBox.information(self, "Очистка компьютера", "Функция доступна только в Windows 10/11.")
            return
        if getattr(self, "junk_scan_worker", None) is not None and self.junk_scan_worker.isRunning():
            return
        self.junk_scan_button.setEnabled(False)
        self.junk_clean_button.setEnabled(False)
        self.junk_summary.setText("Идёт проверка временных папок…")
        self.junk_scan_worker = JunkScanWorker(self)
        self.junk_scan_worker.completed.connect(self.on_junk_scan_finished)
        self.junk_scan_worker.failed.connect(self.on_junk_scan_failed)
        self.junk_scan_worker.finished.connect(lambda: self.junk_scan_button.setEnabled(True))
        self.junk_scan_worker.start()

    def on_junk_scan_finished(self, files):
        self.junk_files = files
        self.junk_categories = {}
        for item in files:
            self.junk_categories.setdefault(item.category, []).append(item)
        self.junk_table.blockSignals(True)
        self.junk_table.setRowCount(len(self.junk_categories))
        for row, (category, items) in enumerate(self.junk_categories.items()):
            size = sum(item.size for item in items)
            choice = QTableWidgetItem("Выбрать")
            choice.setFlags(choice.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            choice.setCheckState(Qt.CheckState.Checked)
            self.junk_table.setItem(row, 0, choice)
            self.junk_table.setItem(row, 1, QTableWidgetItem(category))
            self.junk_table.setItem(row, 2, QTableWidgetItem(
                f"{self.format_bytes(size)} · {len(items)} файлов"
            ))
        self.junk_table.blockSignals(False)
        total = sum(item.size for item in files)
        self.junk_summary.setText(
            f"Найдено: {len(files)} файлов · потенциально освобождаемо: {self.format_bytes(total)}. "
            "Отметьте категории для очистки."
        )
        self.junk_clean_button.setEnabled(bool(files))
        self.status.setText("Проверка временных файлов завершена. Ничего не удалено.")

    def on_junk_scan_failed(self, message):
        self.junk_summary.setText("Проверка не завершена.")
        QMessageBox.warning(self, "Проверка временных файлов", message)

    def on_junk_selection_changed(self, item):
        if item.column() == 0:
            selected = self.selected_junk_files()
            self.junk_clean_button.setEnabled(bool(selected))

    def selected_junk_files(self):
        selected_categories = set()
        for row, category in enumerate(self.junk_categories):
            item = self.junk_table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected_categories.add(category)
        return [file for file in self.junk_files if file.category in selected_categories]

    def confirm_junk_cleanup(self):
        files = self.selected_junk_files()
        if not files:
            QMessageBox.information(self, "Очистка", "Выберите хотя бы одну категорию.")
            return
        amount = sum(item.size for item in files)
        answer = QMessageBox.warning(
            self, "Подтверждение очистки",
            f"Удалить {len(files)} временных файлов? Потенциально освободится {self.format_bytes(amount)}.\n\n"
            "Будут пропущены занятые, изменившиеся и недоступные файлы. Личные папки не затрагиваются.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.junk_clean_button.setEnabled(False)
        self.junk_scan_button.setEnabled(False)
        self.junk_summary.setText("Выполняется очистка…")
        self.junk_clean_worker = JunkCleanWorker(files, self)
        self.junk_clean_worker.completed.connect(self.on_junk_clean_finished)
        self.junk_clean_worker.failed.connect(self.on_junk_clean_failed)
        self.junk_clean_worker.finished.connect(lambda: self.junk_scan_button.setEnabled(True))
        self.junk_clean_worker.start()

    def on_junk_clean_finished(self, result: CleanupResult):
        self.junk_summary.setText(
            f"Удалено: {result.deleted_files} файлов · освобождено: {self.format_bytes(result.freed_bytes)} · "
            f"пропущено: {result.skipped_files}"
        )
        self.event_log.appendPlainText(
            f"Очистка временных файлов: удалено {result.deleted_files}, освобождено {self.format_bytes(result.freed_bytes)}, "
            f"пропущено {result.skipped_files}."
        )
        if result.errors:
            QMessageBox.warning(self, "Очистка завершена с замечаниями", "\n".join(result.errors[:10]))
        self.start_junk_scan()

    def on_junk_clean_failed(self, message):
        self.junk_clean_button.setEnabled(True)
        QMessageBox.warning(self, "Очистка", message)

    def build_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(self.section_label("Настройки"))
        language_row = QHBoxLayout()
        language_label = QLabel("Язык интерфейса")
        self.language_combo = QComboBox()
        for code, native_name in LANGUAGES.items():
            self.language_combo.addItem(native_name, code)
        index = self.language_combo.findData(self.language)
        self.language_combo.setCurrentIndex(max(0, index))
        self.language_combo.currentIndexChanged.connect(self.change_language)
        language_row.addWidget(language_label)
        language_row.addWidget(self.language_combo, 1)
        layout.addLayout(language_row)

        theme_row = QHBoxLayout()
        theme_label = QLabel("Внешний вид интерфейса")
        self.theme_combo = QComboBox()
        for theme_id, theme_name, *_ in self.THEMES:
            self.theme_combo.addItem(f"№{theme_id} — {theme_name}", theme_id)
        selected_theme = self.settings_store.value("theme", "1", type=str)
        if selected_theme not in {item[0] for item in self.THEMES}:
            selected_theme = "1"
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(selected_theme)))
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        theme_row.addWidget(theme_label)
        theme_row.addWidget(self.theme_combo, 1)
        layout.addLayout(theme_row)
        hint = QLabel("Язык и оформление применяются сразу. При первой установке используется интерфейс №1 — Игровой Neon Gaming. Выбранное оформление сохраняется для следующих запусков.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        self.tabs.addTab(tab, "Настройки")

    def change_theme(self, index):
        theme_id = self.theme_combo.itemData(index)
        if theme_id not in {item[0] for item in self.THEMES}:
            return
        self.settings_store.setValue("theme", theme_id)
        self.apply_theme(theme_id)

    THEMES = [
        ("1", "Игровой Neon Gaming", "#070812", "#f2f0ff", "#7444c8", "#00e5ff", "#101326", "#1b1c36"),
        ("2", "Современный Glass / Windows 11", "#eaf3ff", "#14233b", "#1769d2", "#37a4ff", "#ffffff", "#dceaff"),
        ("3", "Минималистичный Pro", "#101820", "#e7f0f5", "#287a49", "#75d69a", "#17232d", "#263943"),
        ("4", "Техно / Инженерный", "#080b0f", "#f3eee5", "#d87916", "#ffae35", "#151a20", "#292f36"),
        ("5", "Тёмный профессиональный", "#071426", "#e8f2ff", "#087fc4", "#36c6ff", "#10233a", "#1a3450"),
        ("6", "RGB Gaming", "#080910", "#f7f4ff", "#b32bda", "#27e6c1", "#141326", "#29213d"),
        ("7", "Классический удобный", "#e8edf4", "#182333", "#16803b", "#55b86a", "#ffffff", "#d7e0eb"),
        ("8", "Светлый / Чистый", "#f4f7fb", "#18263a", "#1265c8", "#2d9be8", "#ffffff", "#e6edf6"),
        ("9", "Киберпанк", "#10051b", "#ffeaff", "#ed25c8", "#00eaff", "#210d2d", "#3b1648"),
        ("10", "HUD / Мониторинг + драйверы", "#041319", "#dcfbff", "#008d9c", "#00e5ff", "#0b2229", "#143a43")
    ]

    def apply_theme(self, theme_id=None):
        theme_id = str(theme_id or self.settings_store.value("theme", "1", type=str))
        selected = next((item for item in self.THEMES if item[0] == theme_id), self.THEMES[0])
        _, _, bg, fg, accent, highlight, panel, header = selected
        light = theme_id in {"2", "7", "8"}
        muted = "#50627a" if light else "#a7b7d7"
        border = "#b8cce5" if light else accent
        self.setStyleSheet(f"""
            QMainWindow {{ background: {bg}; }}
            QWidget {{ color: {fg}; font-size: 10pt; }}
            QLabel#title {{ font-size: 27pt; font-weight: 900; color: {fg}; }}
            QLabel#subtitle {{ color: {highlight}; font-size: 9pt; font-weight: 900; letter-spacing: 2px; }}
            QLabel#status {{ color: {fg}; padding: 9px 12px; background: {panel}; border: 1px solid {border}; border-radius: 8px; }}
            QLabel#hint {{ color: {muted}; padding: 8px 2px; }}
            QLabel#metricHeading {{ color: {accent}; font-size: 8pt; font-weight: 900; }}
            QLabel#metricValue {{ color: {fg}; font-size: 23pt; font-weight: 900; }}
            QLabel#metricDetail {{ color: {muted}; font-size: 9pt; }}
            QLabel#sectionTitle {{ color: {fg}; font-size: 13pt; font-weight: 900; padding: 5px 0; }}
            QFrame#metricCard, QFrame#infoCard {{ background: {panel}; border: 1px solid {border}; border-radius: 11px; }}
            QLineEdit, QTableWidget, QPlainTextEdit, QComboBox {{ background: {panel}; border: 1px solid {border}; border-radius: 8px; padding: 9px; color: {fg}; selection-background-color: {accent}; }}
            QComboBox QAbstractItemView {{ background: {panel}; color: {fg}; selection-background-color: {accent}; selection-color: #ffffff; border: 1px solid {border}; outline: 0; }}
            QMessageBox {{ background: {panel}; }}
            QMessageBox QLabel {{ color: {fg}; min-width: 360px; }}
            QLineEdit:focus, QComboBox:focus {{ border: 1px solid {highlight}; }}
            QHeaderView::section {{ background: {header}; color: {fg}; padding: 10px; border: 0; border-bottom: 1px solid {accent}; font-weight: 800; }}
            QTableWidget {{ alternate-background-color: {header}; gridline-color: {border}; }}
            QPushButton {{ background: {accent}; color: #ffffff; border: 1px solid {highlight}; border-radius: 8px; padding: 11px 15px; font-weight: 900; }}
            QPushButton:hover {{ background: {highlight}; border-color: {highlight}; color: #ffffff; }}
            QPushButton:pressed {{ background: {accent}; }}
            QPushButton:disabled {{ background: {header}; color: {muted}; border-color: {border}; }}
            QProgressBar {{ background: {header}; border: 0; border-radius: 4px; height: 8px; }}
            QProgressBar::chunk {{ background: {highlight}; border-radius: 4px; }}
            QTabWidget::pane {{ border: 1px solid {border}; border-radius: 10px; top: -1px; background: {panel}; }}
            QTabBar::tab {{ background: {header}; color: {muted}; padding: 12px 20px; margin-right: 4px; border-top-left-radius: 8px; border-top-right-radius: 8px; }}
            QTabBar::tab:selected {{ background: {accent}; color: #ffffff; border-bottom: 3px solid {highlight}; }}
            QTabBar::tab:hover {{ color: {highlight}; }}
        """)

    def change_language(self, index):
        code = self.language_combo.itemData(index)
        if code not in LANGUAGES:
            return
        self.language = code
        self.settings_store.setValue("language", code)
        self.apply_language()

    def apply_language(self):
        for widget in self.findChildren(QLabel) + self.findChildren(QPushButton):
            if widget.property("_i18n_source") is None:
                widget.setProperty("_i18n_source", widget.text())
            widget.setText(translate(self.language, widget.property("_i18n_source")))
        for widget in self.findChildren(QLineEdit):
            if widget.property("_i18n_placeholder") is None:
                widget.setProperty("_i18n_placeholder", widget.placeholderText())
            widget.setPlaceholderText(translate(self.language, widget.property("_i18n_placeholder")))
        tab_sources = self.tabs.property("_i18n_tabs")
        if tab_sources is None:
            tab_sources = [self.tabs.tabText(i) for i in range(self.tabs.count())]
            self.tabs.setProperty("_i18n_tabs", tab_sources)
        for i, source in enumerate(tab_sources):
            self.tabs.setTabText(i, translate(self.language, source))
        table_headers = [
            (self.device_table, self.device_headers),
            (self.update_table, ["Выбрать", "Устройство", "Доступный драйвер", "Версия", "Дата"]),
        ]
        for table, headers in table_headers:
            for col, source in enumerate(headers):
                item = table.horizontalHeaderItem(col)
                if item:
                    item.setText(translate(self.language, source))
        if hasattr(self, "language_combo"):
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(self.language)))
            self.language_combo.blockSignals(False)

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
        self.telemetry_worker = TelemetryWorker(self)
        self.telemetry_worker.completed.connect(self.on_telemetry_finished)
        self.telemetry_worker.failed.connect(self.on_telemetry_failed)
        self.telemetry_worker.finished.connect(self.on_telemetry_worker_finished)
        self.telemetry_worker.start()

    def on_telemetry_worker_finished(self):
        self._telemetry_busy = False

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
            QMessageBox.information(self, "Драйверы", "Каталог драйверов доступен только в Windows 10/11.")
            return
        if self.update_worker is not None and self.update_worker.isRunning():
            return
        self.update_search_button.setEnabled(False)
        self.status.setText("Сканирование устройств и поиск совместимых драйверов в Microsoft Update Catalog…")
        self.update_worker = ScanWorker(self)
        self.update_worker.completed.connect(self.on_devices_for_catalog)
        self.update_worker.failed.connect(self.on_update_error)
        self.update_worker.finished.connect(lambda: self.update_search_button.setEnabled(True))
        self.update_worker.start()

    def on_devices_for_catalog(self, devices):
        self.devices = devices
        self.render_devices()
        self.status.setText("Устройства найдены. Запрос каталога Microsoft Update…")
        self.catalog_worker = CatalogSearchWorker(devices, self)
        self.catalog_worker.completed.connect(self.on_catalog_updates_found)
        self.catalog_worker.failed.connect(self.on_update_error)
        self.catalog_worker.start()

    def on_catalog_updates_found(self, updates):
        self.available_driver_updates = updates
        self.update_table.setRowCount(len(updates))
        for row, update in enumerate(updates):
            choice = QTableWidgetItem()
            choice.setFlags(choice.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            choice.setCheckState(Qt.CheckState.Unchecked)
            choice.setData(Qt.ItemDataRole.UserRole, update)
            self.update_table.setItem(row, 0, choice)
            values = [
                ", ".join(update.get("MatchedDevices", [])),
                update.get("Title", "Драйвер Microsoft"),
                update.get("Version") or "Версия не указана",
                update.get("Date") or "Дата не указана",
            ]
            for col, value in enumerate(values, start=1):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.update_table.setItem(row, col, item)
        self.update_table.resizeRowsToContents()
        self.status.setText(f"Каталог Microsoft Update: найдено совместимых предложений драйверов — {len(updates)}. Обычный Windows Update не запускался.")
        if not updates:
            QMessageBox.information(self, "Проверка драйверов", "В каталоге Microsoft не найдено новых предложений, точно совпадающих с идентификаторами оборудования. Установленные драйверы не изменялись.")

    def select_all_update_rows(self):
        for row in range(self.update_table.rowCount()):
            item = self.update_table.item(row, 0)
            if item is not None:
                item.setCheckState(Qt.CheckState.Checked)

    def update_selected_drivers(self):
        selected = []
        for row in range(self.update_table.rowCount()):
            item = self.update_table.item(row, 0)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                update = item.data(Qt.ItemDataRole.UserRole)
                if update:
                    selected.append(update)
        if not selected:
            QMessageBox.information(self, "Обновление драйверов", "Сначала отметьте драйверы для обновления.")
            return
        inf_names = []
        for update in selected:
            for device_id in update.get("MatchedDeviceIds", []):
                device = next((d for d in self.devices if d.device_id == device_id), None)
                if device and device.inf_name:
                    inf_names.append(device.inf_name)
        if not inf_names:
            QMessageBox.warning(self, "Обновление драйверов", "Windows не предоставила INF-имена текущих выбранных драйверов. Без подтверждённой резервной копии установка отменена.")
            return
        backup_root = Path.home() / "AppData" / "Local" / "DjShrek" / "DriverBackups"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup_folder = backup_root / datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            backup_folder.mkdir()
            backup_selected_driver_packages(sorted(set(inf_names)), backup_folder)
        except (DriverBackupError, OSError) as exc:
            QMessageBox.critical(self, "Резервная копия", f"Не удалось сохранить выбранные драйверы. Установка отменена.\n\n{exc}")
            return
        self.status.setText(f"Резервная копия выбранных драйверов создана: {backup_folder}. Загрузка и установка…")
        self.update_install_button.setEnabled(False)
        self.install_worker = DriverInstallWorker(selected, self)
        self.install_worker.completed.connect(self.on_driver_install_finished)
        self.install_worker.failed.connect(self.on_driver_install_failed)
        self.install_worker.finished.connect(lambda: self.update_install_button.setEnabled(True))
        self.install_worker.start()

    def on_driver_install_finished(self, results):
        success = sum(1 for result in results if result.get("ResultCode") == 2)
        reboot = any(result.get("RebootRequired") for result in results)
        self.status.setText(f"Установка завершена: успешно — {success} из {len(results)}. " + ("Требуется перезагрузка Windows." if reboot else "Перезагрузка не запрошена."))
        details = "\n".join(f"{item.get('Title', 'Драйвер')}: код {item.get('ResultCode')}, HRESULT {item.get('HResult')}" for item in results)
        QMessageBox.information(self, "Результат обновления драйверов", details or "Windows вернула пустой отчёт.")
        self.start_update_search()

    def on_driver_install_failed(self, message):
        self.status.setText("Обновление драйверов не завершено.")
        QMessageBox.critical(self, "Ошибка обновления драйверов", message)

    def on_update_error(self, message):
        self.status.setText("Проверка каталога драйверов не завершена.")
        QMessageBox.warning(self, "Проверка драйверов", message)


    def check_application_updates(self):
        """Check GitHub Releases without blocking the interface."""
        if getattr(self, "update_check_worker", None) is not None and self.update_check_worker.isRunning():
            return
        self.update_check_worker = UpdateCheckWorker(self)
        self.update_check_worker.completed.connect(self.on_application_update_checked)
        self.update_check_worker.failed.connect(self.on_application_update_check_failed)
        self.update_check_worker.start()

    def on_application_update_checked(self, update):
        if not update:
            return
        version = update.get("version", "новая версия")
        notes = update.get("notes", "").strip()
        message = f"Доступна версия {version}.\n\n{notes}\n\nЗагрузить и установить обновление?"
        answer = QMessageBox.question(
            self, "Обновление DjShrek Draiver", message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            download_and_schedule(update)
            QMessageBox.information(
                self, "Обновление подготовлено",
                "Пакет обновления загружен и проверен. Программа закроется для установки.",
            )
            QApplication.quit()
        except UpdateError as exc:
            QMessageBox.warning(self, "Не удалось обновить программу", str(exc))

    def on_application_update_check_failed(self, message):
        # A failed optional update check must not interrupt normal program use.
        self.status.setText(f"Автопроверка обновления программы недоступна: {message}")

    def check_vendor_utilities(self):
        if sys.platform != "win32":
            QMessageBox.information(self, "Официальные утилиты", "Проверка доступна только в Windows 10/11.")
            return
        utilities = detect_vendor_utilities()
        installed = [item for item in utilities if item.installed]
        missing = [item for item in utilities if not item.installed]
        messages = []
        for item in installed:
            messages.append(f"✓ {item.name}: обнаружена")
        for item in missing:
            answer = QMessageBox.question(
                self, "Официальная утилита не найдена",
                f"{item.name} не обнаружена. Открыть официальный сайт производителя для загрузки и установки?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Yes:
                open_vendor_scan_page(item.key)
                messages.append(f"Открыт официальный сайт: {item.name}")
            else:
                messages.append(f"Пропущено: {item.name}")
        for item in installed:
            if item.key in ("intel", "amd"):
                open_vendor_scan_page(item.key)
                messages.append(f"Открыт официальный сканер: {item.name}")
            elif item.key == "dell":
                if item.executable:
                    self.status.setText("Запуск официального сканирования Dell Command | Update…")
                    self.vendor_tools_button.setEnabled(False)
                    self.dell_scan_worker = DellScanWorker(item.executable, self)
                    self.dell_scan_worker.completed.connect(self.on_dell_scan_finished)
                    self.dell_scan_worker.failed.connect(self.on_dell_scan_failed)
                    self.dell_scan_worker.finished.connect(lambda: self.vendor_tools_button.setEnabled(True))
                    self.dell_scan_worker.start()
                else:
                    QMessageBox.information(
                        self, "Dell Command | Update",
                        "Утилита Dell обнаружена, но dcu-cli.exe не найден. Откройте Dell Command | Update вручную или выполните переустановку с официального сайта."
                    )
        if messages:
            self.event_log.appendPlainText("\\n".join(messages))
        if not any(item.key == "dell" and item.installed and item.executable for item in installed):
            self.status.setText("Проверка OEM-утилит завершена. Intel/AMD открывают официальные страницы проверки; отсутствующие утилиты предложено загрузить.")

    def on_dell_scan_finished(self, updates):
        self.update_table.setRowCount(len(updates))
        for row, update in enumerate(updates):
            values = [
                update.get("title", "Обновление Dell"),
                "Dell",
                update.get("version") or "См. отчёт Dell",
                update.get("date") or "Не указана",
                "Dell Command | Update",
                "Официальный CLI: проверено",
            ]
            for col, value in enumerate(values):
                self.update_table.setItem(row, col, QTableWidgetItem(value))
        self.update_table.resizeRowsToContents()
        self.status.setText(
            f"Dell Command | Update завершил проверку. Записей в отчёте: {len(updates)}. "
            "Применение обновлений не запускалось."
        )
        self.event_log.appendPlainText(f"Dell Command | Update: найдено записей отчёта — {len(updates)}.")

    def on_dell_scan_failed(self, message):
        self.status.setText("Сканирование Dell Command | Update не завершено.")
        QMessageBox.warning(self, "Dell Command | Update", message)


def main():
    if sys.platform != "win32":
        print("DjShrek Draiver предназначен для Windows 10/11.")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
