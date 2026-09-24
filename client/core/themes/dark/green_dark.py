from dataclasses import replace
from client.core.themes.dark.dark import DarkTheme


GreenDarkTheme = replace(
    DarkTheme,

    ACCENT_PRIMARY="#66bb6a",
    ACCENT_HOVER="#4caf50",
    ACCENT_PRESSED="#388e3c",
    ACCENT_HOVER_SOFT="#81c784",
    ACCENT_PRESSED_DEEP="#2e7d32",
    ACCENT_SELECTION_BG="#1a2e1c",

    HEADER_BG="#1b5e20",

    TEXT_ACCENT_DARK="#81c784",
    TEXT_ACCENT_DARK_STRONG="#a5d6a7",
    TEXT_ACCENT_SOFT="#66bb6a",

    BORDER_ACCENT_SOFT="#2a4a2c",

    BTN_EDIT_BG="#1a2e1c",
    BTN_EDIT_BORDER="#2a4a2c",
    BTN_EDIT_PRESSED_BG="#1b5e20",

    CHIP_BG="#1e2e1e",
    CHIP_TEXT="#a5d6a7",

    SIDEBAR_HOVER_BG="#26402a",
    SIDEBAR_HOVER_TEXT="#a5d6a7",

    MENU_BG="#1a1f1a",

    ACCENT_PRIMARY_ALPHA_10="rgba(102, 187, 106, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(102, 187, 106, 0.2)",

    TABLE_SELECTION_BG="#1a2e1c",
    TABLE_SELECTION_BG_ACTIVE="#2a4a2c",
    TABLE_SELECTION_TEXT="#e8e8e8",
    TABLE_ROW_ALT_ACCENT="#1a201a",
    TABLE_ROW_HOVER_ACCENT="#1e2e1e",

    ICON_COLOR="#66bb6a",
    ICON_PIN_COLOR="#ffffff",
)