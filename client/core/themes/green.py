from dataclasses import replace
from client.core.themes.standard import StandardTheme


GreenTheme = replace(
    StandardTheme,

    # ── Пастельные фоны ──
    BG_DIALOG="#e8f5e9",             # Green 50
    BG_DIALOG_ALT="#f1f8f2",
    BG_CARD="#f6fbf6",
    BG_CARD_ELEVATED="#f9fdf9",  # ← НОВОЕ
    BG_INPUT="#ffffff",
    BG_INPUT_READONLY="#e0efe1",
    BG_SURFACE_SUBTLE="#f1f8f2",
    BG_SURFACE_HEADER="#c8e6c9",     # Green 100

    # ── Текст: тёмный с зелёным оттенком ──
    TEXT_PRIMARY="#1e3a22",
    TEXT_HEADING="#2a4a2e",
    TEXT_SECONDARY="#3a5c3e",
    TEXT_MUTED="#5a7c5e",
    TEXT_MUTED_ALT="#6b8c6f",
    TEXT_TERTIARY="#8aab8e",
    TEXT_BLACK="#0d1e10",
    TEXT_DARK_STRONG="#0d1e10",
    TEXT_BODY="#1b3a1e",

    # ── Границы: зелёные ──
    BORDER_DEFAULT="#c8e6c9",
    BORDER_LIGHT="#e8f5e9",
    BORDER_INPUT="#a5d6a7",
    BORDER_HOVER="#4caf50",
    BORDER_FRAME_SOFT="#e8f5e9",

    # ── Акцент: зелёный ──
    ACCENT_PRIMARY="#2e7d32",
    ACCENT_HOVER="#1b5e20",
    ACCENT_PRESSED="#0d3d11",
    ACCENT_HOVER_SOFT="#4caf50",
    ACCENT_PRESSED_DEEP="#0d3d11",
    ACCENT_SELECTION_BG="#e8f5e9",

    # ── Шапка ──
    HEADER_BG="#2e7d32",

    # ── Тексты «акцентные» ──
    TEXT_ACCENT_DARK="#2e7d32",
    TEXT_ACCENT_DARK_STRONG="#1b5e20",
    TEXT_ACCENT_SOFT="#4caf50",

    # ── Границы «акцентные» ──
    BORDER_ACCENT_SOFT="#a5d6a7",

    # ── Кнопка «Редактировать» ──
    BTN_EDIT_BG="#e8f5e9",
    BTN_EDIT_BORDER="#a5d6a7",
    BTN_EDIT_PRESSED_BG="#0d3d11",

    # ── Чипы приоритета ──
    CHIP_BG="#e0efe1",
    CHIP_TEXT="#3a5c3e",

    # ── Sidebar ──
    SIDEBAR_HOVER_BG="#26402a",
    SIDEBAR_HOVER_TEXT="#a5d6a7",

    # ── Меню ──
    MENU_BG="#f6fbf6",

    # ── Прозрачность акцента ──
    ACCENT_PRIMARY_ALPHA_10="rgba(46, 125, 50, 0.1)",
    ACCENT_PRIMARY_ALPHA_20="rgba(46, 125, 50, 0.2)",

    # ── Таблица (пастель) ──
    TABLE_BG="#f6fbf6",              # фон ячеек
    TABLE_ROW_ALT="#e8f5e9",         # Green 50 — чётные строки
    TABLE_ROW_HOVER="#c8e6c9",       # Green 100 — hover
    TABLE_GRID="#c8e6c9",            # сетка
    TABLE_HEADER_BG="#c8e6c9",       # Green 100 — шапка (мягкая)
    TABLE_HEADER_TEXT="#1e3a22",     # тёмный текст на пастели
    TABLE_HEADER_HOVER_BG="#a5d6a7", # Green 200
    TABLE_HEADER_BORDER="#a5d6a7",   # Green 200
    TABLE_SELECTION_BG="#c8e6c9",
    TABLE_SELECTION_BG_ACTIVE="#a5d6a7",
    TABLE_SELECTION_TEXT="#1e3a22",
    TABLE_ROW_ALT_ACCENT="#f1f8f2",
    TABLE_ROW_HOVER_ACCENT="#e8f5e9",

    ICON_COLOR="#2e7d32",
    ICON_PIN_COLOR="#2e7d32",
)