from dataclasses import replace
from client.core.themes.standard import StandardTheme


LilacTheme = replace(
    StandardTheme,

    # ── Пастельные фоны (очень светлая сирень) ──
    BG_DIALOG="#ede7f6",             # Deep Purple 50
    BG_DIALOG_ALT="#f5f1fa",
    BG_CARD="#faf7fd",
    BG_CARD_ELEVATED="#fcfaff",
    BG_INPUT="#ffffff",
    BG_INPUT_READONLY="#e6def2",
    BG_SURFACE_SUBTLE="#f5f1fa",
    BG_SURFACE_HEADER="#d1c4e9",     # Deep Purple 100

    # ── Текст: тёмный с холодным сиреневым оттенком ──
    TEXT_PRIMARY="#2e2440",
    TEXT_HEADING="#3d3152",
    TEXT_SECONDARY="#4f4168",
    TEXT_MUTED="#6f5f88",
    TEXT_MUTED_ALT="#7d6d96",
    TEXT_TERTIARY="#9d8db5",
    TEXT_BLACK="#1a1228",
    TEXT_DARK_STRONG="#1a1228",
    TEXT_BODY="#251a35",

    # ── Границы: сиреневые ──
    BORDER_DEFAULT="#d1c4e9",
    BORDER_LIGHT="#ede7f6",
    BORDER_INPUT="#b39ddb",
    BORDER_HOVER="#9575cd",
    BORDER_FRAME_SOFT="#ede7f6",

    # ── Акцент: сиреневый (мягкий, холодный) ──
    ACCENT_PRIMARY="#9575cd",        # Deep Purple 300
    ACCENT_HOVER="#7e57c2",          # Deep Purple 400
    ACCENT_PRESSED="#673ab7",        # Deep Purple 500
    ACCENT_HOVER_SOFT="#b39ddb",     # Deep Purple 200
    ACCENT_PRESSED_DEEP="#5e35b1",   # Deep Purple 600
    ACCENT_SELECTION_BG="#ede7f6",

    # ── Шапка ──
    HEADER_BG="#9575cd",

    # ── Акцентные тексты ──
    TEXT_ACCENT_DARK="#7e57c2",
    TEXT_ACCENT_DARK_STRONG="#5e35b1",
    TEXT_ACCENT_SOFT="#b39ddb",

    BORDER_ACCENT_SOFT="#d1c4e9",

    # ── Кнопка «Редактировать» ──
    BTN_EDIT_BG="#ede7f6",
    BTN_EDIT_BORDER="#d1c4e9",
    BTN_EDIT_PRESSED_BG="#5e35b1",

    # ── Чипы ──
    CHIP_BG="#e6def2",
    CHIP_TEXT="#4f4168",

    # ── Sidebar ──
    SIDEBAR_HOVER_BG="#332a44",
    SIDEBAR_HOVER_TEXT="#d1c4e9",

    # ── Меню ──
    MENU_BG="#faf7fd",

    # ── Прозрачность акцента ──
    ACCENT_PRIMARY_ALPHA_10="rgba(149, 117, 205, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(149, 117, 205, 0.2)",

    # ── Таблица ──
    TABLE_BG="#faf7fd",
    TABLE_ROW_ALT="#ede7f6",
    TABLE_ROW_HOVER="#d1c4e9",
    TABLE_GRID="#d1c4e9",
    TABLE_HEADER_BG="#d1c4e9",
    TABLE_HEADER_TEXT="#2e2440",
    TABLE_HEADER_HOVER_BG="#b39ddb",
    TABLE_HEADER_BORDER="#b39ddb",
    TABLE_SELECTION_BG="#d1c4e9",
    TABLE_SELECTION_BG_ACTIVE="#b39ddb",
    TABLE_SELECTION_TEXT="#2e2440",
    TABLE_ROW_ALT_ACCENT="#f5f1fa",
    TABLE_ROW_HOVER_ACCENT="#ede7f6",

    ICON_COLOR="#9575cd",
    ICON_PIN_COLOR="#9575cd",
)