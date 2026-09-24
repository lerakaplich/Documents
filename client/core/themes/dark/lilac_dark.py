from dataclasses import replace
from client.core.themes.dark.dark import DarkTheme


LilacDarkTheme = replace(
    DarkTheme,

    # ── Акцент: сиреневый (на тёмном фоне — светлее и мягче) ──
    ACCENT_PRIMARY="#b39ddb",        # Deep Purple 200
    ACCENT_HOVER="#9575cd",          # Deep Purple 300
    ACCENT_PRESSED="#7e57c2",        # Deep Purple 400
    ACCENT_HOVER_SOFT="#d1c4e9",     # Deep Purple 100
    ACCENT_PRESSED_DEEP="#673ab7",   # Deep Purple 500
    ACCENT_SELECTION_BG="#241a33",

    # ── Шапка ──
    HEADER_BG="#5e35b1",

    # ── Акцентные тексты ──
    TEXT_ACCENT_DARK="#d1c4e9",
    TEXT_ACCENT_DARK_STRONG="#ede7f6",
    TEXT_ACCENT_SOFT="#b39ddb",

    # ── Акцентные границы ──
    BORDER_ACCENT_SOFT="#3d2e55",

    # ── Кнопка «Редактировать» ──
    BTN_EDIT_BG="#241a33",
    BTN_EDIT_BORDER="#3d2e55",
    BTN_EDIT_PRESSED_BG="#5e35b1",

    # ── Чипы ──
    CHIP_BG="#251e30",
    CHIP_TEXT="#d1c4e9",

    # ── Sidebar hover ──
    SIDEBAR_HOVER_BG="#332a44",
    SIDEBAR_HOVER_TEXT="#d1c4e9",

    # ── Меню ──
    MENU_BG="#171422",

    # ── Прозрачность акцента ──
    ACCENT_PRIMARY_ALPHA_10="rgba(179, 157, 219, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(179, 157, 219, 0.2)",

    # ── Таблица ──
    TABLE_SELECTION_BG="#241a33",
    TABLE_SELECTION_BG_ACTIVE="#3d2e55",
    TABLE_SELECTION_TEXT="#e8e8e8",
    TABLE_ROW_ALT_ACCENT="#171422",
    TABLE_ROW_HOVER_ACCENT="#251e30",

    # ── Иконки ──
    ICON_COLOR="#b39ddb",
    ICON_PIN_COLOR="#ffffff",
)