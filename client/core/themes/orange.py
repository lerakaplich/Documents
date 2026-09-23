from dataclasses import replace
from client.core.themes.standard import StandardTheme


OrangeTheme = replace(
    StandardTheme,

    # ── Пастельные фоны ──
    BG_DIALOG="#fff3e0",             # Orange 50
    BG_DIALOG_ALT="#fff8f0",
    BG_CARD="#fffaf3",
    BG_CARD_ELEVATED="#fffcf7",
    BG_INPUT="#ffffff",
    BG_INPUT_READONLY="#fae5cc",
    BG_SURFACE_SUBTLE="#fff8f0",
    BG_SURFACE_HEADER="#ffe0b2",     # Orange 100

    # ── Текст: тёмный с оранжевым оттенком ──
    TEXT_PRIMARY="#4a2a10",
    TEXT_HEADING="#5c3515",
    TEXT_SECONDARY="#6b4518",
    TEXT_MUTED="#8a5f20",
    TEXT_MUTED_ALT="#946b28",
    TEXT_TERTIARY="#b08840",
    TEXT_BLACK="#2b1806",
    TEXT_DARK_STRONG="#2b1806",
    TEXT_BODY="#3d2210",

    # ── Границы ──
    BORDER_DEFAULT="#ffe0b2",
    BORDER_LIGHT="#fff3e0",
    BORDER_INPUT="#ffcc80",
    BORDER_HOVER="#fb8c00",
    BORDER_FRAME_SOFT="#fff3e0",

    # ── Акцент: оранжевый ──
    ACCENT_PRIMARY="#ef6c00",
    ACCENT_HOVER="#e65100",
    ACCENT_PRESSED="#bf360c",
    ACCENT_HOVER_SOFT="#fb8c00",
    ACCENT_PRESSED_DEEP="#bf360c",
    ACCENT_SELECTION_BG="#fff3e0",

    # ── Шапка ──
    HEADER_BG="#ef6c00",

    # ── Акцентные тексты ──
    TEXT_ACCENT_DARK="#ef6c00",
    TEXT_ACCENT_DARK_STRONG="#bf360c",
    TEXT_ACCENT_SOFT="#fb8c00",

    BORDER_ACCENT_SOFT="#ffcc80",

    # ── Кнопка «Редактировать» ──
    BTN_EDIT_BG="#fff3e0",
    BTN_EDIT_BORDER="#ffcc80",
    BTN_EDIT_PRESSED_BG="#bf360c",

    # ── Чипы ──
    CHIP_BG="#fae5cc",
    CHIP_TEXT="#6b4518",

    # ── Sidebar ──
    SIDEBAR_HOVER_BG="#4a2e15",
    SIDEBAR_HOVER_TEXT="#ffcc80",

    # ── Меню ──
    MENU_BG="#fffaf3",

    # ── Прозрачность акцента ──
    ACCENT_PRIMARY_ALPHA_10="rgba(239, 108, 0, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(239, 108, 0, 0.2)",

    # ── Таблица ──
    TABLE_BG="#fffaf3",
    TABLE_ROW_ALT="#fff3e0",
    TABLE_ROW_HOVER="#ffe0b2",
    TABLE_GRID="#ffe0b2",
    TABLE_HEADER_BG="#ffe0b2",
    TABLE_HEADER_TEXT="#4a2a10",
    TABLE_HEADER_HOVER_BG="#ffcc80",
    TABLE_HEADER_BORDER="#ffcc80",
    TABLE_SELECTION_BG="#ffe0b2",
    TABLE_SELECTION_BG_ACTIVE="#ffcc80",
    TABLE_SELECTION_TEXT="#4a2a10",
    TABLE_ROW_ALT_ACCENT="#fff8f0",
    TABLE_ROW_HOVER_ACCENT="#fff3e0",

    ICON_COLOR="#ef6c00",
    ICON_PIN_COLOR="#ef6c00",
)