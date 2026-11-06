from __future__ import annotations

from PySide6.QtCore import QLocale

LANGUAGES = {
    "ru": "Русский",
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "pt_BR": "Português (Brasil)",
    "it": "Italiano",
    "pl": "Polski",
    "tr": "Türkçe",
    "uk": "Українська",
    "zh_CN": "简体中文",
    "ja": "日本語",
}

# Core navigation and controls are translated locally; device names remain
# exactly as reported by Windows and are never translated.
T = {
"en": {
"DjShrek-Draiver Cyber Club":"DjShrek-Draiver Cyber Club",
"Центр управления":"Control Center","Устройства и драйверы":"Devices & Drivers",
"Обновления драйверов":"Driver Updates","Настройки":"Settings",
"Обновить мониторинг":"Refresh Monitoring","МОНИТОРИНГ В РЕАЛЬНОМ ВРЕМЕНИ":"REAL-TIME MONITORING",
"ОБОРУДОВАНИЕ И СИСТЕМА":"HARDWARE & SYSTEM","ЖУРНАЛ СОБЫТИЙ":"EVENT LOG",
"Процессор · загрузка":"CPU Usage","Оперативная память":"Memory","Системный диск":"System Disk","Видеокарта":"Graphics",
"Сканировать устройства":"Scan Devices","Экспорт CSV":"Export CSV","Создать копию драйверов":"Back Up Drivers",
"Восстановить из копии":"Restore Backup","Поиск устройства или производителя…":"Search device or manufacturer…",
"Проверить наличие обновлений драйверов":"Check for Driver Updates",
"Проверить утилиты Intel / AMD / Dell":"Check Intel / AMD / Dell Utilities",
"Устройство":"Device","Производитель":"Manufacturer","Состояние":"Status","Класс":"Class",
"Версия драйвера":"Driver Version","Дата драйвера":"Driver Date","Официальный источник":"Official Source",
"Переход":"Open","Открыть официальный сайт":"Open Official Website",
"Панель управления запущена.":"Control panel started.",
"Язык интерфейса":"Interface language","Изменение языка применяется сразу.":"Language changes apply immediately.",
},
"de": {"Центр управления":"Systemsteuerung","Устройства и драйверы":"Geräte und Treiber","Обновления драйверов":"Treiberaktualisierungen","Настройки":"Einstellungen","Обновить мониторинг":"Überwachung aktualisieren","Сканировать устройства":"Geräte scannen","Экспорт CSV":"CSV exportieren","Создать копию драйверов":"Treiber sichern","Восстановить из копии":"Sicherung wiederherstellen","Проверить наличие обновлений драйверов":"Nach Treiberupdates suchen","Проверить утилиты Intel / AMD / Dell":"Intel-/AMD-/Dell-Tools prüfen","Язык интерфейса":"Oberflächensprache","Изменение языка применяется сразу.":"Sprachänderungen werden sofort übernommen."},
"fr": {"Центр управления":"Centre de contrôle","Устройства и драйверы":"Périphériques et pilotes","Обновления драйверов":"Mises à jour des pilotes","Настройки":"Paramètres","Обновить мониторинг":"Actualiser la surveillance","Сканировать устройства":"Analyser les périphériques","Экспорт CSV":"Exporter CSV","Создать копию драйверов":"Sauvegarder les pilotes","Восстановить из копии":"Restaurer la sauvegarde","Проверить наличие обновлений драйверов":"Rechercher des mises à jour","Проверить утилиты Intel / AMD / Dell":"Vérifier les outils Intel / AMD / Dell","Язык интерфейса":"Langue de l’interface","Изменение языка применяется сразу.":"Le changement de langue est immédiat."},
"es": {"Центр управления":"Centro de control","Устройства и драйверы":"Dispositivos y controladores","Обновления драйверов":"Actualizaciones de controladores","Настройки":"Configuración","Обновить мониторинг":"Actualizar monitorización","Сканировать устройства":"Buscar dispositivos","Экспорт CSV":"Exportar CSV","Создать копию драйверов":"Respaldar controladores","Восстановить из копии":"Restaurar copia","Проверить наличие обновлений драйверов":"Buscar actualizaciones de controladores","Проверить утилиты Intel / AMD / Dell":"Comprobar utilidades Intel / AMD / Dell","Язык интерфейса":"Idioma de la interfaz","Изменение языка применяется сразу.":"El cambio de idioma se aplica inmediatamente."},
"pt_BR": {"Центр управления":"Central de controle","Устройства и драйверы":"Dispositivos e drivers","Обновления драйверов":"Atualizações de drivers","Настройки":"Configurações","Обновить мониторинг":"Atualizar monitoramento","Сканировать устройства":"Verificar dispositivos","Экспорт CSV":"Exportar CSV","Создать копию драйверов":"Fazer backup dos drivers","Восстановить из копии":"Restaurar backup","Проверить наличие обновлений драйверов":"Verificar atualizações de drivers","Проверить утилиты Intel / AMD / Dell":"Verificar utilitários Intel / AMD / Dell","Язык интерфейса":"Idioma da interface","Изменение языка применяется сразу.":"A alteração de idioma é aplicada imediatamente."},
"it": {"Центр управления":"Centro di controllo","Устройства и драйверы":"Dispositivi e driver","Обновления драйверов":"Aggiornamenti driver","Настройки":"Impostazioni","Обновить мониторинг":"Aggiorna monitoraggio","Сканировать устройства":"Scansiona dispositivi","Экспорт CSV":"Esporta CSV","Создать копию драйверов":"Backup driver","Восстановить из копии":"Ripristina backup","Проверить наличие обновлений драйверов":"Cerca aggiornamenti driver","Проверить утилиты Intel / AMD / Dell":"Controlla utilità Intel / AMD / Dell","Язык интерфейса":"Lingua dell’interfaccia","Изменение языка применяется сразу.":"La lingua cambia immediatamente."},
"pl": {"Центр управления":"Centrum sterowania","Устройства и драйверы":"Urządzenia i sterowniki","Обновления драйверов":"Aktualizacje sterowników","Настройки":"Ustawienia","Обновить мониторинг":"Odśwież monitoring","Сканировать устройства":"Skanuj urządzenia","Экспорт CSV":"Eksportuj CSV","Создать копию драйверов":"Utwórz kopię sterowników","Восстановить из копии":"Przywróć kopię","Проверить наличие обновлений драйверов":"Sprawdź aktualizacje sterowników","Проверить утилиты Intel / AMD / Dell":"Sprawdź narzędzia Intel / AMD / Dell","Язык интерфейса":"Język interfejsu","Изменение языка применяется сразу.":"Zmiana języka działa natychmiast."},
"tr": {"Центр управления":"Kontrol Merkezi","Устройства и драйверы":"Aygıtlar ve Sürücüler","Обновления драйверов":"Sürücü Güncellemeleri","Настройки":"Ayarlar","Обновить мониторинг":"İzlemeyi Yenile","Сканировать устройства":"Aygıtları Tara","Экспорт CSV":"CSV Dışa Aktar","Создать копию драйверов":"Sürücüleri Yedekle","Восстановить из копии":"Yedekten Geri Yükle","Проверить наличие обновлений драйверов":"Sürücü Güncellemelerini Denetle","Проверить утилиты Intel / AMD / Dell":"Intel / AMD / Dell Araçlarını Denetle","Язык интерфейса":"Arayüz Dili","Изменение языка применяется сразу.":"Dil değişikliği hemen uygulanır."},
"uk": {"Центр управления":"Центр керування","Устройства и драйверы":"Пристрої та драйвери","Обновления драйверов":"Оновлення драйверів","Настройки":"Налаштування","Обновить мониторинг":"Оновити моніторинг","Сканировать устройства":"Сканувати пристрої","Экспорт CSV":"Експорт CSV","Создать копию драйверов":"Створити резервну копію драйверів","Восстановить из копии":"Відновити з копії","Проверить наличие обновлений драйверов":"Перевірити оновлення драйверів","Проверить утилиты Intel / AMD / Dell":"Перевірити утиліти Intel / AMD / Dell","Язык интерфейса":"Мова інтерфейсу","Изменение языка применяется сразу.":"Зміна мови застосовується одразу."},
"zh_CN": {"Центр управления":"控制中心","Устройства и драйверы":"设备和驱动程序","Обновления драйверов":"驱动程序更新","Настройки":"设置","Обновить мониторинг":"刷新监控","Сканировать устройства":"扫描设备","Экспорт CSV":"导出 CSV","Создать копию драйверов":"备份驱动程序","Восстановить из копии":"恢复备份","Проверить наличие обновлений драйверов":"检查驱动程序更新","Проверить утилиты Intel / AMD / Dell":"检查 Intel / AMD / Dell 工具","Язык интерфейса":"界面语言","Изменение языка применяется сразу.":"语言更改立即生效。"},
"ja": {"Центр управления":"コントロールセンター","Устройства и драйверы":"デバイスとドライバー","Обновления драйверов":"ドライバーの更新","Настройки":"設定","Обновить мониторинг":"モニターを更新","Сканировать устройства":"デバイスをスキャン","Экспорт CSV":"CSV をエクスポート","Создать копию драйверов":"ドライバーをバックアップ","Восстановить из копии":"バックアップから復元","Проверить наличие обновлений драйверов":"ドライバーの更新を確認","Проверить утилиты Intel / AMD / Dell":"Intel / AMD / Dell ユーティリティを確認","Язык интерфейса":"インターフェース言語","Изменение языка применяется сразу.":"言語の変更はすぐに反映されます。"},
}


def system_language() -> str:
    name = QLocale.system().name()
    if name.startswith("pt_BR"):
        return "pt_BR"
    prefix = name.split("_", 1)[0]
    return prefix if prefix in LANGUAGES else "en"


def translate(language: str, source: str) -> str:
    if language == "ru":
        return source
    return T.get(language, T["en"]).get(source, T["en"].get(source, source))
