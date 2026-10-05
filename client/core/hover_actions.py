# client/core/hover_actions.py
"""Иконки «Редактировать» / «Удалить» на карточках: видны только при наведении.

Использование в любой карточке, где в .ui есть кнопки editBtn и deleteBtn:

    from client.core.hover_actions import setup_hover_actions
    ...
    loadUi(ui_path, self)
    apply_theme_to_widget(self)
    setup_hover_actions(self)      # <- одна строка
"""

from PyQt6.QtCore import QEvent, QObject, QSize
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QPushButton, QWidget

from client.core.themes import T

ICON_SIZE = 30
EDIT_ICON = "✎"
DELETE_ICON = "🗑"


def tok(name: str, default: str) -> str:
    """Токен темы с запасным значением, если такого поля нет в T."""
    return getattr(T, name, default)


def style_icon_button(btn: QPushButton, icon: str, tooltip: str, danger: bool = False) -> None:
    """Превращает текстовую кнопку в компактную иконку."""
    btn.setText(icon)
    btn.setToolTip(tooltip)
    btn.setFixedSize(QSize(ICON_SIZE, ICON_SIZE))
    btn.setFont(QFont("Segoe UI Symbol", 12))

    muted = tok("TEXT_MUTED_ALT", "#9a9a9a")
    hover_bg = tok("TEXT_DANGER", "#e5534b") if danger else tok("ACCENT_PRIMARY", "#e0397f")
    hover_fg = tok("TEXT_ON_ACCENT", "#ffffff")

    btn.setStyleSheet(
        f"""
        QPushButton {{
            background-color: transparent;
            color: {muted};
            border: none;
            border-radius: 6px;
        }}
        QPushButton:hover {{
            background-color: {hover_bg};
            color: {hover_fg};
        }}
        QPushButton:pressed {{
            background-color: {hover_bg};
        }}
        """
    )


class _HoverFilter(QObject):
    """Показывает кнопки, пока курсор над карточкой."""

    def __init__(self, card: QWidget, effects: list):
        super().__init__(card)
        self._effects = effects
        card.installEventFilter(self)
        self.set_visible(False)

    def set_visible(self, visible: bool) -> None:
        for fx in self._effects:
            fx.setOpacity(1.0 if visible else 0.0)

    def eventFilter(self, obj, event):
        t = event.type()
        if t == QEvent.Type.Enter:
            self.set_visible(True)
        elif t == QEvent.Type.Leave:
            self.set_visible(False)
        return False


def setup_hover_actions(card: QWidget) -> None:
    """Заменяет текстовые кнопки editBtn/deleteBtn иконками, видимыми при наведении.

    Кнопки остаются в layout, поэтому карточка не «прыгает» при наведении.
    Сигналы и обработчики кнопок не меняются.
    """
    edit_btn = getattr(card, "editBtn", None)
    delete_btn = getattr(card, "deleteBtn", None)

    effects = []
    for btn, icon, tip, danger in (
        (edit_btn, EDIT_ICON, "Редактировать", False),
        (delete_btn, DELETE_ICON, "Удалить", True),
    ):
        if btn is None:
            continue
        style_icon_button(btn, icon, tip, danger)
        fx = QGraphicsOpacityEffect(btn)
        btn.setGraphicsEffect(fx)
        effects.append(fx)

    if effects:
        card._hover_actions = _HoverFilter(card, effects)
