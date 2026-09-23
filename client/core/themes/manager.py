import re
from dataclasses import asdict

from PyQt6.QtWidgets import QWidget, QApplication

from client.core.themes.tokens import BaseTheme
from client.core.themes.standard import StandardTheme
from client.core.utils.icon_manager import icon_manager

_PLACEHOLDER_RE = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")

# Имя property для хранения оригинального styleSheet с плейсхолдерами
_ORIG_PROP = "_theme_original_style"


class ThemeManager:
    def __init__(self) -> None:
        self._current: BaseTheme = StandardTheme

    @property
    def current(self) -> BaseTheme:
        return self._current

    def set_theme(self, theme: BaseTheme) -> None:
        self._current = theme

    def theme_dict(self) -> dict:
        d = asdict(self._current)

        from client.core.themes.icon_utils import icon_path
        icon_color = self._current.ICON_COLOR
        pin_color = self._current.ICON_PIN_COLOR

        # QSS-пути (используются в .ui как {ICON_*_PATH})
        d["ICON_ARROW_DOWN_PATH"]         = icon_path("down_arrow",   icon_color)
        d["ICON_ARROW_UP_PATH"]           = icon_path("up_arrow",     icon_color)
        d["ICON_CALENDAR_PATH"]           = icon_path("calendar_date", icon_color)
        d["ICON_PLUS_PATH"]               = icon_path("plus24_gold",  icon_color)
        d["ICON_PIN_PATH"]                = icon_path("pin",          pin_color)
        # ── Чекбоксы (новое) ──
        d["ICON_CHECKBOX_CHECKED_PATH"]   = icon_path("cb_checked",   icon_color)
        d["ICON_CHECKBOX_UNCHECKED_PATH"] = icon_path("cb_unchecked", icon_color)

        return d

    _ORIG_PROP = "_theme_original_style"

    def _apply_to_one(self, w, theme):
        ss = w.styleSheet()
        if not ss:
            return
        original = w.property(_ORIG_PROP)
        if original is None:
            original = ss
            w.setProperty(_ORIG_PROP, original)
        new_ss = _PLACEHOLDER_RE.sub(
            lambda m: theme.get(m.group(1), m.group(0)),
            original,  # ← всегда оригинал!
        )
        if new_ss != ss:
            w.setStyleSheet(new_ss)

    def apply_to_widget(self, widget) -> None:
        if not isinstance(widget, QWidget):
            print(
                f"[ThemeManager] apply_to_widget: ожидался QWidget, "
                f"получен {type(widget).__name__}. Пропускаем."
            )
            return

        theme = self.theme_dict()
        widgets = [widget, *widget.findChildren(QWidget)]
        for w in widgets:
            self._apply_to_one(w, theme)


_manager = ThemeManager()


def get_manager() -> ThemeManager:
    return _manager


def apply_theme_to_widget(widget) -> None:
    """Рекурсивно подставить цвета темы во все styleSheet виджета и потомков."""
    if not isinstance(widget, QWidget):
        print(
            f"[themes] apply_theme_to_widget: ожидался QWidget, "
            f"получен {type(widget).__name__}. Пропускаем."
        )
        return
    _manager.apply_to_widget(widget)


def apply_theme_to_all_windows() -> None:
    """Пройти по всем открытым окнам: подставить плейсхолдеры и вызвать
    reapply_theme() у виджетов, которые его определяют.
    Вызывать после set_theme()."""
    app = QApplication.instance()
    if app is None:
        return

    try:
        icon_manager.clear_cache()
    except Exception:
        pass

    for top in app.topLevelWidgets():
        # 1. Обычная подстановка {TOKEN} → hex в стилях из .ui
        apply_theme_to_widget(top)

        # 2. re-apply для виджетов с кодом, который строит стиль через f-строку
        for w in [top, *top.findChildren(QWidget)]:
            reapply = getattr(w, "reapply_theme", None)
            if callable(reapply):
                try:
                    reapply()
                except Exception as e:
                    print(f"[themes] reapply_theme error in {type(w).__name__}: {e}")


def get_menu_style() -> str:
    t = _manager.current
    return f"""
        QMenu {{
            background-color: {t.MENU_BG};
            border: 1px solid {t.MENU_BORDER};
            border-radius: 5px;
            padding: 5px;
            color: {t.MENU_TEXT};
        }}
        QMenu::item {{
            padding: 8px 25px 8px 15px;
            border-radius: 3px;
            font-size: 14px;
        }}
        QMenu::item:selected {{
            background-color: {t.ACCENT_SELECTION_BG};
        }}
        QMenu::separator {{
            height: 1px;
            background: {t.MENU_SEPARATOR};
            margin: 5px 10px;
        }}
    """


def get_message_box_style() -> str:
    t = _manager.current
    return f"""
        QMessageBox {{
            background-color: {t.BG_CARD};
            color: {t.TEXT_BLACK};
        }}
        QMessageBox QLabel {{
            color: {t.TEXT_BLACK};
            background-color: transparent;
        }}
        QMessageBox QPushButton {{
            color: {t.TEXT_BLACK};
        }}
    """

