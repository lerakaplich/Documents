from dataclasses import replace
from client.core.themes.standard import StandardTheme


BlueTheme = replace(
    StandardTheme,

    # ── Пастельные фоны ──
    BG_DIALOG="#e3f2fd",             # Blue 50
    BG_DIALOG_ALT="#f0f7ff",
    BG_CARD="#f5faff",
    BG_CARD_ELEVATED="#f9fcff",  # ← НОВОЕ
    BG_INPUT="#ffffff",
    BG_INPUT_READONLY="#dcecf8",
    BG_SURFACE_SUBTLE="#f0f7ff",
    BG_SURFACE_HEADER="#bbdefb",     # Blue 100

    # ── Текст: тёмный с синим оттенком ──
    TEXT_PRIMARY="#14274a",
    TEXT_HEADING="#1e3560",
    TEXT_SECONDARY="#2e4672",
    TEXT_MUTED="#4a628c",
    TEXT_MUTED_ALT="#5b739c",
    TEXT_TERTIARY="#7a92bb",
    TEXT_BLACK="#0a1428",
    TEXT_DARK_STRONG="#0a1428",
    TEXT_BODY="#14274a",

    # ── Границы: синие ──
    BORDER_DEFAULT="#bbdefb",
    BORDER_LIGHT="#e3f2fd",
    BORDER_INPUT="#90caf9",
    BORDER_HOVER="#2196f3",
    BORDER_FRAME_SOFT="#e3f2fd",

    # ── Акцент: синий ──
    ACCENT_PRIMARY="#1976d2",
    ACCENT_HOVER="#1565c0",
    ACCENT_PRESSED="#0d47a1",
    ACCENT_HOVER_SOFT="#42a5f5",
    ACCENT_PRESSED_DEEP="#0d47a1",
    ACCENT_SELECTION_BG="#e3f2fd",

    # ── Шапка ──
    HEADER_BG="#1976d2",

    # ── Тексты «акцентные» ──
    TEXT_ACCENT_DARK="#1976d2",
    TEXT_ACCENT_DARK_STRONG="#0d47a1",
    TEXT_ACCENT_SOFT="#42a5f5",

    # ── Границы «акцентные» ──
    BORDER_ACCENT_SOFT="#bbdefb",

    # ── Кнопка «Редактировать» ──
    BTN_EDIT_BG="#e3f2fd",
    BTN_EDIT_BORDER="#90caf9",
    BTN_EDIT_PRESSED_BG="#0d47a1",

    # ── Чипы приоритета ──
    CHIP_BG="#dcecf8",
    CHIP_TEXT="#2e4672",

    # ── Sidebar ──
    SIDEBAR_HOVER_BG="#1e3a5c",
    SIDEBAR_HOVER_TEXT="#90caf9",

    # ── Меню ──
    MENU_BG="#f5faff",

    # ── Прозрачность акцента ──
    ACCENT_PRIMARY_ALPHA_10="rgba(25, 118, 210, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(25, 118, 210, 0.2)",

    # ── Таблица (пастель) ──
    TABLE_BG="#f5faff",              # фон ячеек
    TABLE_ROW_ALT="#e3f2fd",         # Blue 50 — чётные строки
    TABLE_ROW_HOVER="#bbdefb",       # Blue 100 — hover
    TABLE_GRID="#bbdefb",            # сетка
    TABLE_HEADER_BG="#bbdefb",       # Blue 100 — шапка (мягкая)
    TABLE_HEADER_TEXT="#14274a",     # тёмный текст на пастели
    TABLE_HEADER_HOVER_BG="#90caf9", # Blue 200
    TABLE_HEADER_BORDER="#90caf9",   # Blue 200
    TABLE_SELECTION_BG="#bbdefb",
    TABLE_SELECTION_BG_ACTIVE="#90caf9",
    TABLE_SELECTION_TEXT="#14274a",
    TABLE_ROW_ALT_ACCENT="#f0f7ff",
    TABLE_ROW_HOVER_ACCENT="#e3f2fd",

    ICON_COLOR="#1976d2",
    ICON_PIN_COLOR="#1976d2",
)