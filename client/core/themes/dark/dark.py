from dataclasses import replace
from client.core.themes.standard import StandardTheme


DarkTheme = replace(
    StandardTheme,

    # ── Фоны ──
    BG_DIALOG="#1e1e1e",
    BG_DIALOG_ALT="#252525",
    BG_CARD="#2a2a2a",
    BG_CARD_ELEVATED="#333333",  # ← НОВОЕ: в тёмной «светлее» = ближе к серому
    BG_INPUT="#333333",
    BG_INPUT_READONLY="#3a3a3a",
    BG_SURFACE_SUBTLE="#262626",
    BG_SURFACE_HEADER="#262626",

    # ── Фоны состояний ──
    BG_HOVER_LIGHT="#3a3a3a",
    BG_PRESSED_LIGHT="#4a4a4a",
    BG_HOVER_ACCENT_SOFT="#3a3226",
    BG_HOVER_ALT="#333333",
    BG_HOVER_ALT_DARK="#424242",
    BG_PRESSED_CALENDAR="#555555",

    # ── Текст ──
    TEXT_PRIMARY="#e0e0e0",
    TEXT_ON_ACCENT="#ffffff",
    TEXT_BLACK="#e0e0e0",
    TEXT_HEADING="#cccccc",
    TEXT_SECONDARY="#b0b0b0",
    TEXT_MUTED="#a0a0a0",
    TEXT_MUTED_ALT="#909090",
    TEXT_TERTIARY="#808080",
    TEXT_SUBTLE="#707070",
    TEXT_DISABLED="#505050",
    TEXT_DARK_STRONG="#e8e8e8",
    TEXT_BODY="#c8c8c8",
    TEXT_ACCENT_DARK="#ccab6e",       # акцент читается и в тёмной
    TEXT_ACCENT_DARK_STRONG="#d4b878",
    TEXT_ACCENT_SOFT="#998664",
    TEXT_SUCCESS="#4caf50",
    TEXT_DANGER="#ef5350",
    TEXT_ERROR_DEEP="#ff5252",

    # ── Границы ──
    BORDER_DEFAULT="#404040",
    BORDER_LIGHT="#454545",
    BORDER_INPUT="#505050",
    BORDER_HOVER="#707070",
    BORDER_FRAME_SOFT="#3a3a3a",
    BORDER_ACCENT_SOFT="#5a4a36",
    BORDER_COMBO_SOFT="#454545",
    BORDER_ERROR_SOFT="#7a3a3a",

    # ── Акцент (золотой остаётся) ──
    ACCENT_PRIMARY="#ccab6e",
    ACCENT_HOVER="#b8945a",
    ACCENT_PRESSED="#a07d4a",
    ACCENT_HOVER_SOFT="#998664",
    ACCENT_PRESSED_DEEP="#7A6A50",
    ACCENT_SELECTION_BG="#3a3226",   # вместо #e3f2fd

    # ── Danger ──
    ACCENT_DANGER="#d22730",
    ACCENT_DANGER_HOVER="#862633",
    ACCENT_DANGER_PRESSED="#6a1e29",
    ACCENT_REQUIRED="#ef5350",

    # ── Ошибки ──
    BG_ERROR_SOFT="#3a2020",

    # ── Шапка / brand ──
    HEADER_BG="#a01f26",             # тёмно-красный, чтобы не резало глаза

    # ── Тёмная кнопка (теперь светлая, т.к. на тёмном фоне) ──
    BTN_DARK_BG="#3a3a3a",
    BTN_DARK_HOVER_BG="#4a4a4a",
    BTN_DARK_PRESSED_BG="#555555",

    # ── Вторичная кнопка ──
    BTN_SECONDARY_BG="#333333",
    BTN_SECONDARY_HOVER_BG="#404040",
    BTN_SECONDARY_PRESSED_BG="#4a4a4a",

    # ── Кнопки edit/delete ──
    BTN_EDIT_BG="#3a3226",
    BTN_EDIT_BORDER="#5a4a36",
    BTN_EDIT_PRESSED_BG="#7A6A50",

    BTN_DELETE_BG="#3a2020",
    BTN_DELETE_TEXT="#ef5350",
    BTN_DELETE_BORDER="#7a3a3a",
    BTN_DELETE_HOVER_BG="#ef5350",
    BTN_DELETE_PRESSED_BG="#c53030",

    # ── Чипы ──
    CHIP_BG="#3a3a3a",
    CHIP_TEXT="#b0b0b0",
    CHIP_URGENT_BG="#4a2020",
    CHIP_URGENT_TEXT="#ef5350",
    CHIP_IMPORTANT_BG="#4a3a20",
    CHIP_IMPORTANT_TEXT="#ffb74d",

    # ── Меню ──
    MENU_BG="#2a2a2a",
    MENU_BORDER="#505050",
    MENU_TEXT="#e0e0e0",
    MENU_SEPARATOR="#404040",

    # ── Скроллбар ──
    SCROLLBAR_BG="#1e1e1e",
    SCROLLBAR_HANDLE="#505050",
    SCROLLBAR_HANDLE_HOVER="#707070",
    SCROLLBAR_HANDLE_PRESSED="#909090",
    SCROLLBAR_HANDLE_SOFT="#505050",
    SCROLLBAR_HANDLE_SOFT_HOVER="#707070",

    # ── Sidebar (и так тёмный — не трогаем) ──
    SIDEBAR_BG="#141414",
    SIDEBAR_TEXT="#e0e0e0",
    SIDEBAR_HOVER_BG="#2a2a2a",
    SIDEBAR_HOVER_TEXT="#DDB87A",
    SIDEBAR_DIVIDER="#2a2a2a",

    # ── Разделители ──
    SEPARATOR_BG="#404040",
    SEPARATOR_LINE="#404040",

    # ── Toolbar ──
    TOOLBAR_BG_DARK="#1a1a1a",

    # ── Таблица ──
    TABLE_BG="#2a2a2a",
    TABLE_ROW_ALT="#2f2f2f",
    TABLE_ROW_HOVER="#3a3a3a",
    TABLE_GRID="#404040",
    TABLE_SELECTION_BG="#3a3226",
    TABLE_SELECTION_BG_ACTIVE="#4a3f30",
    TABLE_SELECTION_TEXT="#e8e8e8",
    TABLE_HEADER_BG="#1a1a1a",
    TABLE_HEADER_TEXT="#e0e0e0",
    TABLE_HEADER_HOVER_BG="#2a2a2a",
    TABLE_HEADER_BORDER="#404040",
    TABLE_ROW_ALT_ACCENT="#2f2a25",
    TABLE_ROW_HOVER_ACCENT="#3a3226",

    # ── Нейтральная кнопка ──
    BTN_NEUTRAL_BG="#4a4a4a",
    BTN_NEUTRAL_HOVER_BG="#5a5a5a",
    BTN_NEUTRAL_PRESSED_BG="#3a3a3a",

    ICON_COLOR="#ccab6e",
    ICON_PIN_COLOR="#ffffff",    # ← pin белый
)