from app import i18n


def test_popular_languages_are_available():
    expected = {"ru", "en", "de", "fr", "es", "pt_BR", "it", "pl", "tr", "uk", "zh_CN", "ja"}
    assert expected.issubset(i18n.LANGUAGES)


def test_system_locale_maps_to_supported_language(monkeypatch):
    monkeypatch.setattr(i18n.QLocale, "system", lambda: type("Locale", (), {"name": lambda self: "de_DE"})())
    assert i18n.system_language() == "de"


def test_unknown_system_locale_falls_back_to_english(monkeypatch):
    monkeypatch.setattr(i18n.QLocale, "system", lambda: type("Locale", (), {"name": lambda self: "xx_YY"})())
    assert i18n.system_language() == "en"


def test_translation_and_russian_source():
    assert i18n.translate("en", "Центр управления") == "Control Center"
    assert i18n.translate("ru", "Центр управления") == "Центр управления"
