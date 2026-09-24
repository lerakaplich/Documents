from dataclasses import replace
from client.core.themes.dark.dark import DarkTheme


BlueDarkTheme = replace(
    DarkTheme,

    # ── Акцент: небесно-голубой (в тёмной — посветлее) ──
    ACCENT_PRIMARY="#4fc3f7",  # Light Blue 300
    ACCENT_HOVER="#29b6f6",  # Light Blue 400
    ACCENT_PRESSED="#03a9f4",  # Light Blue 500
    ACCENT_HOVER_SOFT="#81d4fa",  # Light Blue 200
    ACCENT_PRESSED_DEEP="#0288d1",  # Light Blue 600
    ACCENT_SELECTION_BG="#0e2a3d",

    # ── Шапка ──
    HEADER_BG="#01579b",

    # ── Акцентные тексты ──
    TEXT_ACCENT_DARK="#81d4fa",
    TEXT_ACCENT_DARK_STRONG="#b3e5fc",
    TEXT_ACCENT_SOFT="#4fc3f7",

    # ── Акцентные границы ──
    BORDER_ACCENT_SOFT="#1c4a66",

    # ── Кнопка «Редактировать» ──
    BTN_EDIT_BG="#0e2a3d",
    BTN_EDIT_BORDER="#1c4a66",
    BTN_EDIT_PRESSED_BG="#01579b",

    # ── Чипы ──
    CHIP_BG="#122c3e",
    CHIP_TEXT="#b3e5fc",

    # ── Sidebar hover ──
    SIDEBAR_HOVER_BG="#1a3d52",
    SIDEBAR_HOVER_TEXT="#81d4fa",

    # ── Меню ──
    MENU_BG="#0e1a24",

    # ── Прозрачность акцента ──
    ACCENT_PRIMARY_ALPHA_10="rgba(79, 195, 247, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(79, 195, 247, 0.2)",

    # ── Таблица ──
    TABLE_SELECTION_BG="#0e2a3d",
    TABLE_SELECTION_BG_ACTIVE="#1c4a66",
    TABLE_SELECTION_TEXT="#e8e8e8",
    TABLE_ROW_ALT_ACCENT="#0e1a24",
    TABLE_ROW_HOVER_ACCENT="#122c3e",

    # ── Иконки ──
    ICON_COLOR="#4fc3f7",
    ICON_PIN_COLOR="#ffffff",
)