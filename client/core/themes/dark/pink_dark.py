from dataclasses import replace
from client.core.themes.dark.dark import DarkTheme


PinkDarkTheme = replace(
    DarkTheme,

    ACCENT_PRIMARY="#f06292",
    ACCENT_HOVER="#ec407a",
    ACCENT_PRESSED="#e91e63",
    ACCENT_HOVER_SOFT="#f48fb1",
    ACCENT_PRESSED_DEEP="#c2185b",
    ACCENT_SELECTION_BG="#2e1a24",

    HEADER_BG="#ad1457",

    TEXT_ACCENT_DARK="#f48fb1",
    TEXT_ACCENT_DARK_STRONG="#f8bbd0",
    TEXT_ACCENT_SOFT="#f06292",

    BORDER_ACCENT_SOFT="#4a2a38",

    BTN_EDIT_BG="#2e1a24",
    BTN_EDIT_BORDER="#4a2a38",
    BTN_EDIT_PRESSED_BG="#c2185b",

    CHIP_BG="#2e1e26",
    CHIP_TEXT="#f8bbd0",

    SIDEBAR_HOVER_BG="#4a2630",
    SIDEBAR_HOVER_TEXT="#f8bbd0",

    MENU_BG="#1f1a1d",

    ACCENT_PRIMARY_ALPHA_10="rgba(240, 98, 146, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(240, 98, 146, 0.2)",

    TABLE_SELECTION_BG="#2e1a24",
    TABLE_SELECTION_BG_ACTIVE="#4a2a38",
    TABLE_SELECTION_TEXT="#e8e8e8",
    TABLE_ROW_ALT_ACCENT="#1f1a1d",
    TABLE_ROW_HOVER_ACCENT="#2e1e26",

    ICON_COLOR="#f06292",
    ICON_PIN_COLOR="#ffffff",
)