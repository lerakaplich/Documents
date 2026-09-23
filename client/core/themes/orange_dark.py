from dataclasses import replace
from client.core.themes.dark import DarkTheme


OrangeDarkTheme = replace(
    DarkTheme,

    ACCENT_PRIMARY="#ff9800",
    ACCENT_HOVER="#fb8c00",
    ACCENT_PRESSED="#ef6c00",
    ACCENT_HOVER_SOFT="#ffb74d",
    ACCENT_PRESSED_DEEP="#e65100",
    ACCENT_SELECTION_BG="#2e1f0e",

    HEADER_BG="#bf360c",

    TEXT_ACCENT_DARK="#ffb74d",
    TEXT_ACCENT_DARK_STRONG="#ffcc80",
    TEXT_ACCENT_SOFT="#ff9800",

    BORDER_ACCENT_SOFT="#4a3018",

    BTN_EDIT_BG="#2e1f0e",
    BTN_EDIT_BORDER="#4a3018",
    BTN_EDIT_PRESSED_BG="#e65100",

    CHIP_BG="#2e2215",
    CHIP_TEXT="#ffcc80",

    SIDEBAR_HOVER_BG="#4a2e15",
    SIDEBAR_HOVER_TEXT="#ffcc80",

    MENU_BG="#1f1a12",

    ACCENT_PRIMARY_ALPHA_10="rgba(255, 152, 0, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(255, 152, 0, 0.2)",

    TABLE_SELECTION_BG="#2e1f0e",
    TABLE_SELECTION_BG_ACTIVE="#4a3018",
    TABLE_SELECTION_TEXT="#e8e8e8",
    TABLE_ROW_ALT_ACCENT="#1f1a12",
    TABLE_ROW_HOVER_ACCENT="#2e2215",

    ICON_COLOR="#ff9800",
    ICON_PIN_COLOR="#ffffff",
)