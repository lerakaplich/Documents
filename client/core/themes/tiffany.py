from dataclasses import replace
from client.core.themes.standard import StandardTheme


TiffanyTheme = replace(
    StandardTheme,

    # ── Пастельные фоны ──
    BG_DIALOG="#e0f7f6",
    BG_DIALOG_ALT="#f0fbfa",
    BG_CARD="#f5fdfc",
    BG_CARD_ELEVATED="#fafffe",
    BG_INPUT="#ffffff",
    BG_INPUT_READONLY="#cceeec",
    BG_SURFACE_SUBTLE="#f0fbfa",
    BG_SURFACE_HEADER="#b2ebe8",

    # ── Текст: тёмный с бирюзовым оттенком ──
    TEXT_PRIMARY="#0a3a38",
    TEXT_HEADING="#134a48",
    TEXT_SECONDARY="#1a5c5a",
    TEXT_MUTED="#3a7c7a",
    TEXT_MUTED_ALT="#4a8c8a",
    TEXT_TERTIARY="#6aacaa",
    TEXT_BLACK="#051e1d",
    TEXT_DARK_STRONG="#051e1d",
    TEXT_BODY="#0f3a38",

    # ── Границы ──
    BORDER_DEFAULT="#b2ebe8",
    BORDER_LIGHT="#e0f7f6",
    BORDER_INPUT="#80d8d4",
    BORDER_HOVER="#0abab5",
    BORDER_FRAME_SOFT="#e0f7f6",

    # ── Акцент: тиффани ──
    ACCENT_PRIMARY="#0abab5",
    ACCENT_HOVER="#089490",
    ACCENT_PRESSED="#067470",
    ACCENT_HOVER_SOFT="#4fd4d0",
    ACCENT_PRESSED_DEEP="#067470",
    ACCENT_SELECTION_BG="#e0f7f6",

    # ── Шапка ──
    HEADER_BG="#0abab5",

    # ── Акцентные тексты ──
    TEXT_ACCENT_DARK="#0abab5",
    TEXT_ACCENT_DARK_STRONG="#067470",
    TEXT_ACCENT_SOFT="#4fd4d0",

    BORDER_ACCENT_SOFT="#80d8d4",

    # ── Кнопка «Редактировать» ──
    BTN_EDIT_BG="#e0f7f6",
    BTN_EDIT_BORDER="#80d8d4",
    BTN_EDIT_PRESSED_BG="#067470",

    # ── Чипы ──
    CHIP_BG="#cceeec",
    CHIP_TEXT="#1a5c5a",

    # ── Sidebar ──
    SIDEBAR_HOVER_BG="#0a3a38",
    SIDEBAR_HOVER_TEXT="#80d8d4",

    # ── Меню ──
    MENU_BG="#f5fdfc",

    # ── Прозрачность акцента ──
    ACCENT_PRIMARY_ALPHA_10="rgba(10, 186, 181, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(10, 186, 181, 0.2)",

    # ── Таблица ──
    TABLE_BG="#f5fdfc",
    TABLE_ROW_ALT="#e0f7f6",
    TABLE_ROW_HOVER="#b2ebe8",
    TABLE_GRID="#b2ebe8",
    TABLE_HEADER_BG="#b2ebe8",
    TABLE_HEADER_TEXT="#0a3a38",
    TABLE_HEADER_HOVER_BG="#80d8d4",
    TABLE_HEADER_BORDER="#80d8d4",
    TABLE_SELECTION_BG="#b2ebe8",
    TABLE_SELECTION_BG_ACTIVE="#80d8d4",
    TABLE_SELECTION_TEXT="#0a3a38",
    TABLE_ROW_ALT_ACCENT="#f0fbfa",
    TABLE_ROW_HOVER_ACCENT="#e0f7f6",

    ICON_COLOR="#0abab5",
    ICON_PIN_COLOR="#0abab5",
)