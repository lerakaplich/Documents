from dataclasses import replace
from client.core.themes.standard import StandardTheme


BlueTheme = replace(
    StandardTheme,

    # ── Пастельные фоны: очень светлый голубой ──
    BG_DIALOG="#e1f5fe",  # Light Blue 50
    BG_DIALOG_ALT="#f0faff",
    BG_CARD="#f5fcff",
    BG_CARD_ELEVATED="#faffff",
    BG_INPUT="#ffffff",
    BG_INPUT_READONLY="#d4eefa",
    BG_SURFACE_SUBTLE="#f0faff",
    BG_SURFACE_HEADER="#b3e5fc",  # Light Blue 100

    # ── Текст: тёмный с холодным голубым подтоном ──
    TEXT_PRIMARY="#0d2b3e",
    TEXT_HEADING="#123a52",
    TEXT_SECONDARY="#1f4d69",
    TEXT_MUTED="#3f6d87",
    TEXT_MUTED_ALT="#4d7d98",
    TEXT_TERTIARY="#6f9fb8",
    TEXT_BLACK="#05192a",
    TEXT_DARK_STRONG="#05192a",
    TEXT_BODY="#0d2b3e",

    # ── Границы: голубые ──
    BORDER_DEFAULT="#b3e5fc",
    BORDER_LIGHT="#e1f5fe",
    BORDER_INPUT="#81d4fa",  # Light Blue 200
    BORDER_HOVER="#29b6f6",  # Light Blue 400
    BORDER_FRAME_SOFT="#e1f5fe",

    # ── Акцент: небесно-голубой ──
    ACCENT_PRIMARY="#29b6f6",  # Light Blue 400
    ACCENT_HOVER="#03a9f4",  # Light Blue 500
    ACCENT_PRESSED="#0288d1",  # Light Blue 600
    ACCENT_HOVER_SOFT="#4fc3f7",  # Light Blue 300
    ACCENT_PRESSED_DEEP="#01579b",  # Light Blue 900
    ACCENT_SELECTION_BG="#e1f5fe",

    # ── Шапка ──
    HEADER_BG="#29b6f6",

    # ── Акцентные тексты ──
    TEXT_ACCENT_DARK="#0288d1",
    TEXT_ACCENT_DARK_STRONG="#01579b",
    TEXT_ACCENT_SOFT="#4fc3f7",

    BORDER_ACCENT_SOFT="#b3e5fc",

    # ── Кнопка «Редактировать» ──
    BTN_EDIT_BG="#e1f5fe",
    BTN_EDIT_BORDER="#81d4fa",
    BTN_EDIT_PRESSED_BG="#0288d1",

    # ── Чипы ──
    CHIP_BG="#d4eefa",
    CHIP_TEXT="#1f4d69",

    # ── Sidebar ──
    SIDEBAR_HOVER_BG="#1a3d52",
    SIDEBAR_HOVER_TEXT="#81d4fa",

    # ── Меню ──
    MENU_BG="#f5fcff",

    # ── Прозрачность акцента ──
    ACCENT_PRIMARY_ALPHA_10="rgba(41, 182, 246, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(41, 182, 246, 0.2)",

    # ── Таблица ──
    TABLE_BG="#f5fcff",
    TABLE_ROW_ALT="#e1f5fe",
    TABLE_ROW_HOVER="#b3e5fc",
    TABLE_GRID="#b3e5fc",
    TABLE_HEADER_BG="#b3e5fc",
    TABLE_HEADER_TEXT="#0d2b3e",
    TABLE_HEADER_HOVER_BG="#81d4fa",
    TABLE_HEADER_BORDER="#81d4fa",
    TABLE_SELECTION_BG="#b3e5fc",
    TABLE_SELECTION_BG_ACTIVE="#81d4fa",
    TABLE_SELECTION_TEXT="#0d2b3e",
    TABLE_ROW_ALT_ACCENT="#f0faff",
    TABLE_ROW_HOVER_ACCENT="#e1f5fe",

    ICON_COLOR="#29b6f6",
    ICON_PIN_COLOR="#29b6f6",
)