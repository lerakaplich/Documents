from client.core.themes.light.lilac import LilacTheme
from client.core.themes.dark.lilac_dark import LilacDarkTheme
from client.core.themes.tokens import BaseTheme
from client.core.themes.standard import StandardTheme
from client.core.themes.dark.dark import DarkTheme
from client.core.themes.light.blue import BlueTheme
from client.core.themes.dark.blue_dark import BlueDarkTheme
from client.core.themes.light.green import GreenTheme
from client.core.themes.dark.green_dark import GreenDarkTheme
from client.core.themes.light.pink import PinkTheme
from client.core.themes.dark.pink_dark import PinkDarkTheme
from client.core.themes.light.orange import OrangeTheme
from client.core.themes.dark.orange_dark import OrangeDarkTheme
from client.core.themes.light.tiffany import TiffanyTheme
from client.core.themes.dark.tiffany_dark import TiffanyDarkTheme
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
# Палитры: ключ → (светлая тема, тёмная тема, отображаемое имя)
AVAILABLE_PALETTES = {
    "standard": (StandardTheme, DarkTheme,        "Стандартная"),
    "blue":     (BlueTheme,     BlueDarkTheme,    "Синяя"),
    "green":    (GreenTheme,    GreenDarkTheme,   "Зелёная"),
    "pink":     (PinkTheme,     PinkDarkTheme,    "Розовая"),
    "orange":   (OrangeTheme,   OrangeDarkTheme,  "Оранжевая"),
    "tiffany":  (TiffanyTheme,  TiffanyDarkTheme, "Тиффани"),
    "lilac":    (LilacTheme,    LilacDarkTheme,   "Сиреневая"),
}

AVAILABLE_MODES = {
    "light": "Светлая",
    "dark":  "Тёмная",
}


def resolve_theme_key(palette: str, mode: str) -> str:
    """
    Собирает ключ темы из (palette, mode).
    ('standard','light') → 'standard'
    ('standard','dark')  → 'dark'
    ('pink','light')     → 'pink'
    ('pink','dark')      → 'pink_dark'
    """
    if palette == "standard":
        return "standard" if mode == "light" else "dark"
    return palette if mode == "light" else f"{palette}_dark"


def get_theme(palette: str, mode: str) -> BaseTheme:
    entry = AVAILABLE_PALETTES.get(palette)
    if not entry:
        return StandardTheme
    light, dark, _ = entry
    return light if mode == "light" else dark


def get_palette_and_mode(theme_key: str) -> tuple[str, str]:
    """Обратная операция: ключ темы → (palette, mode)."""
    if theme_key == "standard":
        return "standard", "light"
    if theme_key == "dark":
        return "standard", "dark"
    if theme_key.endswith("_dark"):
        return theme_key[:-5], "dark"
    return theme_key, "light"

def apply_saved_theme() -> str:
    """
    Читает сохранённую тему из SettingsManager и применяет её.
    Возвращает ключ темы (напр. 'pink_dark') — пригодится для setCurrent в UI.
    """
    from client.core.settings.settings_manager import SettingsManager
    palette, mode = SettingsManager().get_theme()
    theme = get_theme(palette, mode)
    set_theme(theme)
    apply_theme_to_all_windows()
    return resolve_theme_key(palette, mode)


__all__ = [
    "BaseTheme",
    "StandardTheme", "DarkTheme",
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
    "AVAILABLE_PALETTES",
    "AVAILABLE_MODES",
    "resolve_theme_key",
    "get_theme",
    "get_palette_and_mode",
    "T",
    "get_menu_style",
    "get_message_box_style",
]