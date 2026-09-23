from client.core.themes.lilac import LilacTheme
from client.core.themes.lilac_dark import LilacDarkTheme
from client.core.themes.tokens import BaseTheme
from client.core.themes.standard import StandardTheme
from client.core.themes.dark import DarkTheme
from client.core.themes.blue import BlueTheme
from client.core.themes.blue_dark import BlueDarkTheme
from client.core.themes.green import GreenTheme
from client.core.themes.green_dark import GreenDarkTheme
from client.core.themes.pink import PinkTheme
from client.core.themes.pink_dark import PinkDarkTheme
from client.core.themes.orange import OrangeTheme
from client.core.themes.orange_dark import OrangeDarkTheme
from client.core.themes.tiffany import TiffanyTheme
from client.core.themes.tiffany_dark import TiffanyDarkTheme
from client.core.themes.manager import (
    ThemeManager,
    apply_theme_to_widget,
    apply_theme_to_all_windows,
    get_manager,
    get_menu_style,
    get_message_box_style,
)

# Текущая активная тема
T: BaseTheme = StandardTheme


def set_theme(theme: BaseTheme) -> None:
    global T
    T = theme
    get_manager().set_theme(theme)


# Реестр тем: ключ → (класс темы, отображаемое имя)
AVAILABLE_THEMES = {
    "standard":     (StandardTheme,     "Стандартная"),
    "dark":         (DarkTheme,         "Тёмная"),
    "blue":         (BlueTheme,         "Синяя — светлая"),
    "blue_dark":    (BlueDarkTheme,     "Синяя — тёмная"),
    "green":        (GreenTheme,        "Зелёная — светлая"),
    "green_dark":   (GreenDarkTheme,    "Зелёная — тёмная"),
    "pink":         (PinkTheme,         "Розовая — светлая"),
    "pink_dark":    (PinkDarkTheme,     "Розовая — тёмная"),
    "orange":       (OrangeTheme,       "Оранжевая — светлая"),
    "orange_dark":  (OrangeDarkTheme,   "Оранжевая — тёмная"),
    "tiffany":      (TiffanyTheme,      "Тиффани — светлая"),
    "tiffany_dark": (TiffanyDarkTheme,  "Тиффани — тёмная"),
    "lilac":        (LilacTheme,        "Лиловая — светлая"),
    "lilac_dark":   (LilacDarkTheme,    "Лиловая — тёмная"),
}


def get_theme_by_key(key: str) -> BaseTheme:
    entry = AVAILABLE_THEMES.get(key)
    return entry[0] if entry else StandardTheme


__all__ = [
    "BaseTheme",
    "StandardTheme",
    "DarkTheme",
    "BlueTheme", "BlueDarkTheme",
    "GreenTheme", "GreenDarkTheme",
    "PinkTheme", "PinkDarkTheme",
    "OrangeTheme", "OrangeDarkTheme",
    "TiffanyTheme", "TiffanyDarkTheme",
    "LilacTheme", "LilacDarkTheme",
    "ThemeManager",
    "apply_theme_to_widget",
    "apply_theme_to_all_windows",
    "get_manager",
    "set_theme",
    "get_theme_by_key",
    "AVAILABLE_THEMES",
    "T",
    "get_menu_style",
    "get_message_box_style",
]