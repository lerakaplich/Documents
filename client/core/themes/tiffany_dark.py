from dataclasses import replace
from client.core.themes.dark import DarkTheme


TiffanyDarkTheme = replace(
    DarkTheme,

    ACCENT_PRIMARY="#26d0cb",
    ACCENT_HOVER="#0abab5",
    ACCENT_PRESSED="#089490",
    ACCENT_HOVER_SOFT="#4fd4d0",
    ACCENT_PRESSED_DEEP="#067470",
    ACCENT_SELECTION_BG="#0e2a29",

    HEADER_BG="#067470",

    TEXT_ACCENT_DARK="#4fd4d0",
    TEXT_ACCENT_DARK_STRONG="#80d8d4",
    TEXT_ACCENT_SOFT="#26d0cb",

    BORDER_ACCENT_SOFT="#1a4a48",

    BTN_EDIT_BG="#0e2a29",
    BTN_EDIT_BORDER="#1a4a48",
    BTN_EDIT_PRESSED_BG="#067470",

    CHIP_BG="#122a29",
    CHIP_TEXT="#80d8d4",

    SIDEBAR_HOVER_BG="#0a3a38",
    SIDEBAR_HOVER_TEXT="#80d8d4",

    MENU_BG="#0e1a19",

    ACCENT_PRIMARY_ALPHA_10="rgba(38, 208, 203, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(38, 208, 203, 0.2)",

    TABLE_SELECTION_BG="#0e2a29",
    TABLE_SELECTION_BG_ACTIVE="#1a4a48",
    TABLE_SELECTION_TEXT="#e8e8e8",
    TABLE_ROW_ALT_ACCENT="#0e1a19",
    TABLE_ROW_HOVER_ACCENT="#122a29",

    ICON_COLOR="#26d0cb",
    ICON_PIN_COLOR="#ffffff",
)