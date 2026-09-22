from dataclasses import replace
from client.core.themes.standard import StandardTheme


PinkTheme = replace(
    StandardTheme,

    # ── Пастельные фоны ──
    BG_DIALOG="#fce4ec",             # Pink 50 — фон диалогов
    BG_DIALOG_ALT="#fdf2f7",         # фон MainWindow
    BG_CARD="#fff5f8",
    BG_CARD_ELEVATED="#fff9fb",  # ← НОВОЕ: чуть светлее, лёгкий розовый
    BG_INPUT="#ffffff",              # поля ввода — белые на пастели, читаемо
    BG_INPUT_READONLY="#f8e1e8",
    BG_SURFACE_SUBTLE="#fdf2f7",
    BG_SURFACE_HEADER="#f8bbd0",     # Pink 100 — заголовки

    # ── Текст: тёмный с розовым оттенком ──
    TEXT_PRIMARY="#4a2a35",
    TEXT_HEADING="#5c3642",
    TEXT_SECONDARY="#6b4550",
    TEXT_MUTED="#8a5f6a",
    TEXT_MUTED_ALT="#946b76",
    TEXT_TERTIARY="#b08894",
    TEXT_BLACK="#2b141c",
    TEXT_DARK_STRONG="#2b141c",
    TEXT_BODY="#3d1e28",

    # ── Границы: розовые ──
    BORDER_DEFAULT="#f8bbd0",
    BORDER_LIGHT="#fce4ec",
    BORDER_INPUT="#f48fb1",
    BORDER_HOVER="#ec407a",
    BORDER_FRAME_SOFT="#fce4ec",

    # ── Акцент: розовый ──
    ACCENT_PRIMARY="#e91e63",
    ACCENT_HOVER="#c2185b",
    ACCENT_PRESSED="#ad1457",
    ACCENT_HOVER_SOFT="#f06292",
    ACCENT_PRESSED_DEEP="#880e4f",
    ACCENT_SELECTION_BG="#fce4ec",

    # ── Шапка ──
    HEADER_BG="#e91e63",

    # ── Тексты «акцентные» ──
    TEXT_ACCENT_DARK="#c2185b",
    TEXT_ACCENT_DARK_STRONG="#880e4f",
    TEXT_ACCENT_SOFT="#f06292",

    # ── Границы «акцентные» ──
    BORDER_ACCENT_SOFT="#f8bbd0",

    # ── Кнопка «Редактировать» ──
    BTN_EDIT_BG="#fce4ec",
    BTN_EDIT_BORDER="#f8bbd0",
    BTN_EDIT_PRESSED_BG="#880e4f",

    # ── Чипы приоритета ──
    CHIP_BG="#f8e1e8",
    CHIP_TEXT="#6b4550",

    # ── Sidebar: тёмно-розовый hover ──
    SIDEBAR_HOVER_BG="#4a2630",
    SIDEBAR_HOVER_TEXT="#f8bbd0",

    # ── Меню ──
    MENU_BG="#fff5f8",

    # ── Прозрачность акцента ──
    ACCENT_PRIMARY_ALPHA_10="rgba(233, 30, 99, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(233, 30, 99, 0.2)",

    # ── Таблица (пастель) ──
    TABLE_BG="#fff5f8",              # фон ячеек
    TABLE_ROW_ALT="#fce4ec",         # Pink 50 — чётные строки
    TABLE_ROW_HOVER="#f8bbd0",       # Pink 100 — hover
    TABLE_GRID="#f8bbd0",            # сетка
    TABLE_HEADER_BG="#f8bbd0",       # Pink 100 — шапка (мягкая)
    TABLE_HEADER_TEXT="#4a2a35",     # тёмный текст на пастели
    TABLE_HEADER_HOVER_BG="#f48fb1", # Pink 200
    TABLE_HEADER_BORDER="#f48fb1",   # Pink 200
    TABLE_SELECTION_BG="#f8bbd0",
    TABLE_SELECTION_BG_ACTIVE="#f48fb1",
    TABLE_SELECTION_TEXT="#4a2a35",
    TABLE_ROW_ALT_ACCENT="#fdf2f7",
    TABLE_ROW_HOVER_ACCENT="#fce4ec",

    ICON_COLOR="#e91e63",
    ICON_PIN_COLOR="#e91e63",
)