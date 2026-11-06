from __future__ import annotations

from dataclasses import dataclass
import webbrowser


@dataclass(frozen=True, slots=True)
class OfficialSource:
    name: str
    url: str
    method: str


# Only manufacturer-owned support pages and their official update utilities.
OFFICIAL_SOURCES = (
    ("intel", OfficialSource("Intel Driver & Support Assistant",
        "https://www.intel.com/content/www/us/en/support/detect.html",
        "Официальный сканер Intel; поиск и установка выполняются в утилите Intel DSA.")),
    ("nvidia", OfficialSource("NVIDIA Driver Downloads",
        "https://www.nvidia.com/Download/index.aspx",
        "Официальный каталог NVIDIA; выберите модель видеокарты и версию Windows.")),
    ("amd", OfficialSource("AMD Drivers & Support",
        "https://www.amd.com/en/support/download/drivers.html",
        "Официальный автоопределитель AMD и каталог драйверов.")),
    ("dell", OfficialSource("Dell Drivers & Downloads",
        "https://www.dell.com/support/home/en-us?app=drivers",
        "Официальный каталог Dell; для автообновления используйте Dell Command | Update.")),
    ("lenovo", OfficialSource("Lenovo Support",
        "https://pcsupport.lenovo.com/",
        "Официальный Lenovo System Update / каталог поддержки.")),
    ("hewlett-packard", OfficialSource("HP Software and Driver Downloads",
        "https://support.hp.com/drivers",
        "Официальный каталог HP и HP Image Assistant для поддерживаемых систем.")),
    ("hp", OfficialSource("HP Software and Driver Downloads",
        "https://support.hp.com/drivers",
        "Официальный каталог HP и HP Image Assistant для поддерживаемых систем.")),
    ("asus", OfficialSource("ASUS Download Center",
        "https://www.asus.com/support/download-center/",
        "Официальный каталог ASUS; подберите точную модель устройства.")),
    ("acer", OfficialSource("Acer Drivers & Manuals",
        "https://www.acer.com/us-en/support/drivers-and-manuals",
        "Официальный каталог Acer; подберите точную модель устройства.")),
    ("micro-star", OfficialSource("MSI Support",
        "https://www.msi.com/support/download",
        "Официальный каталог MSI; подберите точную модель устройства.")),
    ("msi", OfficialSource("MSI Support",
        "https://www.msi.com/support/download",
        "Официальный каталог MSI; подберите точную модель устройства.")),
)


def source_for_device(device) -> OfficialSource | None:
    text = " ".join((getattr(device, "manufacturer", ""),
                     getattr(device, "driver_provider", ""),
                     getattr(device, "name", ""))).casefold()
    # Prefer the actual signed driver provider where available.
    for token, source in OFFICIAL_SOURCES:
        if token in text:
            return source
    return None


def open_official_source(url: str) -> bool:
    if not url.startswith("https://"):
        return False
    return bool(webbrowser.open(url, new=2))
