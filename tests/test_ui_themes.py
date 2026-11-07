import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


def _app():
    return QApplication.instance() or QApplication([])


def test_first_run_defaults_to_neon_gaming(tmp_path):
    _app()
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    settings = QSettings("DjShrek", "CyberClub")
    settings.clear()
    window = MainWindow()
    try:
        assert window.theme_combo.currentData() == "1"
        assert len(window.THEMES) == 10
    finally:
        window.close()
        settings.clear()


def test_all_ten_themes_can_be_selected_and_persisted(tmp_path):
    _app()
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    settings = QSettings("DjShrek", "CyberClub")
    settings.clear()
    window = MainWindow()
    try:
        assert window.theme_combo.count() == 10
        for index in range(window.theme_combo.count()):
            window.theme_combo.setCurrentIndex(index)
            theme_id = window.theme_combo.itemData(index)
            assert settings.value("theme", type=str) == theme_id
            assert window.styleSheet()
    finally:
        window.close()
        settings.clear()
