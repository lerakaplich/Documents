from dataclasses import replace
from client.core.themes.dark import DarkTheme


BlueDarkTheme = replace(
    DarkTheme,

    # ── Акцент: синий (на тёмном фоне — посветлее) ──
    ACCENT_PRIMARY="#42a5f5",
    ACCENT_HOVER="#2196f3",
    ACCENT_PRESSED="#1976d2",
    ACCENT_HOVER_SOFT="#64b5f6",
    ACCENT_PRESSED_DEEP="#1565c0",
    ACCENT_SELECTION_BG="#1a2a40",

    # ── Шапка ──
    HEADER_BG="#0d47a1",

    # ── Акцентные тексты ──
    TEXT_ACCENT_DARK="#64b5f6",
    TEXT_ACCENT_DARK_STRONG="#90caf9",
    TEXT_ACCENT_SOFT="#42a5f5",

    # ── Акцентные границы ──
    BORDER_ACCENT_SOFT="#2a4a6a",

    # ── Кнопка «Редактировать» ──
    BTN_EDIT_BG="#1a2a40",
    BTN_EDIT_BORDER="#2a4a6a",
    BTN_EDIT_PRESSED_BG="#0d47a1",

    # ── Чипы ──
    CHIP_BG="#1e2a3a",
    CHIP_TEXT="#90caf9",

    # ── Sidebar hover ──
    SIDEBAR_HOVER_BG="#1e3a5c",
    SIDEBAR_HOVER_TEXT="#90caf9",

    # ── Меню ──
    MENU_BG="#1a1f2a",

    # ── Прозрачность акцента ──
    ACCENT_PRIMARY_ALPHA_10="rgba(66, 165, 245, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(66, 165, 245, 0.2)",

    # ── Таблица: акцентные ряды ──
    TABLE_SELECTION_BG="#1a2a40",
    TABLE_SELECTION_BG_ACTIVE="#2a4a6a",
    TABLE_SELECTION_TEXT="#e8e8e8",
    TABLE_ROW_ALT_ACCENT="#1a2028",
    TABLE_ROW_HOVER_ACCENT="#1e2a3a",

    # ── Иконки ──
    ICON_COLOR="#42a5f5",
    ICON_PIN_COLOR="#ffffff",
)