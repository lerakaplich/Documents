from dataclasses import dataclass


@dataclass(frozen=True)
class BaseTheme:
    """Семантические цветовые токены приложения."""

    # ── Общие фоны ──
    BG_DIALOG: str
    BG_DIALOG_ALT: str
    BG_CARD: str
    BG_CARD_ELEVATED: str
    BG_INPUT: str
    BG_INPUT_READONLY: str
    BG_SURFACE_SUBTLE: str
    BG_SURFACE_HEADER: str

    # ── Фоны состояний ──
    BG_HOVER_LIGHT: str
    BG_PRESSED_LIGHT: str
    BG_HOVER_ACCENT_SOFT: str
    BG_HOVER_ALT: str
    BG_HOVER_ALT_DARK: str
    BG_PRESSED_CALENDAR: str

    # ── Текст ──
    TEXT_PRIMARY: str
    TEXT_ON_ACCENT: str
    TEXT_BLACK: str
    TEXT_HEADING: str
    TEXT_SECONDARY: str
    TEXT_MUTED: str
    TEXT_MUTED_ALT: str
    TEXT_TERTIARY: str
    TEXT_SUBTLE: str
    TEXT_DISABLED: str
    TEXT_DARK_STRONG: str
    TEXT_BODY: str
    TEXT_ACCENT_DARK: str
    TEXT_ACCENT_DARK_STRONG: str
    TEXT_ACCENT_SOFT: str
    TEXT_SUCCESS: str
    TEXT_DANGER: str
    TEXT_ERROR_DEEP: str

    # ── Границы ──
    BORDER_DEFAULT: str
    BORDER_LIGHT: str
    BORDER_INPUT: str
    BORDER_HOVER: str
    BORDER_FRAME_SOFT: str
    BORDER_ACCENT_SOFT: str
    BORDER_COMBO_SOFT: str
    BORDER_ERROR_SOFT: str

    # ── Акцент ──
    ACCENT_PRIMARY: str
    ACCENT_HOVER: str
    ACCENT_PRESSED: str
    ACCENT_HOVER_SOFT: str
    ACCENT_PRESSED_DEEP: str
    ACCENT_SELECTION_BG: str

    # ── Danger ──
    ACCENT_DANGER: str
    ACCENT_DANGER_HOVER: str
    ACCENT_DANGER_PRESSED: str
    ACCENT_REQUIRED: str

    # ── Ошибки ──
    BG_ERROR_SOFT: str

    # ── Шапка / brand ──
    HEADER_BG: str

    # ── Тёмная кнопка ──
    BTN_DARK_BG: str
    BTN_DARK_HOVER_BG: str
    BTN_DARK_PRESSED_BG: str

    # ── Вторичная кнопка ──
    BTN_SECONDARY_BG: str
    BTN_SECONDARY_HOVER_BG: str

    # ── Кнопка «Редактировать» ──
    BTN_EDIT_BG: str
    BTN_EDIT_BORDER: str
    BTN_EDIT_PRESSED_BG: str

    # ── Кнопка «Удалить» ──
    BTN_DELETE_BG: str
    BTN_DELETE_TEXT: str
    BTN_DELETE_BORDER: str
    BTN_DELETE_HOVER_BG: str
    BTN_DELETE_PRESSED_BG: str

    # ── Чипы приоритета ──
    CHIP_BG: str
    CHIP_TEXT: str
    CHIP_URGENT_BG: str
    CHIP_URGENT_TEXT: str
    CHIP_IMPORTANT_BG: str
    CHIP_IMPORTANT_TEXT: str

    # ── Разделители ──
    SEPARATOR_BG: str
    SEPARATOR_LINE: str

    # ── Контекстное меню ──
    MENU_BG: str
    MENU_BORDER: str
    MENU_TEXT: str
    MENU_SEPARATOR: str

    # ── Скроллбар ──
    SCROLLBAR_BG: str
    SCROLLBAR_HANDLE: str
    SCROLLBAR_HANDLE_HOVER: str
    SCROLLBAR_HANDLE_PRESSED: str
    SCROLLBAR_HANDLE_SOFT: str
    SCROLLBAR_HANDLE_SOFT_HOVER: str

    # ── Sidebar ──
    SIDEBAR_BG: str
    SIDEBAR_TEXT: str
    SIDEBAR_HOVER_BG: str
    SIDEBAR_HOVER_TEXT: str
    SIDEBAR_DIVIDER: str

    # ── Акцент с прозрачностью ──
    ACCENT_PRIMARY_ALPHA_10: str
    ACCENT_PRIMARY_ALPHA_20: str

    # ── Доп. границы ──
    BORDER_INPUT_SOFT: str

    # ── Серая кнопка ──
    BTN_GRAY_BG: str
    BTN_GRAY_HOVER_BG: str
    BTN_GRAY_PRESSED_BG: str

    # ── Акцент-кнопка (disabled) ──
    BTN_ACCENT_DISABLED_BG: str

    # ── Вторичная кнопка (pressed) ──
    BTN_SECONDARY_PRESSED_BG: str

    # ── Текст (тёплый приглушённый) ──
    TEXT_MUTED_WARM: str

    # ── Toolbar (тёмный) ──
    TOOLBAR_BG_DARK: str

    # ── Таблица ──
    TABLE_BG: str
    TABLE_ROW_ALT: str
    TABLE_ROW_HOVER: str
    TABLE_GRID: str
    TABLE_SELECTION_BG: str
    TABLE_SELECTION_BG_ACTIVE: str
    TABLE_SELECTION_TEXT: str
    TABLE_HEADER_BG: str
    TABLE_HEADER_TEXT: str
    TABLE_HEADER_HOVER_BG: str
    TABLE_HEADER_BORDER: str
    TABLE_ROW_ALT_ACCENT: str
    TABLE_ROW_HOVER_ACCENT: str

    # ── Нейтральная (toolbar) кнопка ──
    BTN_NEUTRAL_BG: str
    BTN_NEUTRAL_HOVER_BG: str
    BTN_NEUTRAL_PRESSED_BG: str

    # ── Иконки (перекрашиваются в рантайме) ──
    ICON_COLOR: str            # основной цвет (стрелки, календарь, +, чекбоксы)
    ICON_PIN_COLOR: str        # отдельно pin.svg — в тёмной он белый