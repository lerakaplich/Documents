# client/core/utils/context_menu.py
"""Единое контекстное меню для таблиц и деревьев (документы, «Система»).

Стиль меню берётся в ОДНОМ месте — menu_style(). Чтобы таблица документов и вкладка
«Система» выглядели одинаково, достаточно поправить эту функцию.
"""

from collections.abc import Callable

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QMenu, QWidget

from client.core.themes import get_menu_style

SEPARATOR = None  # пункт-разделитель в списке items

# пункт меню: (текст, обработчик) или (текст, обработчик, включён)
MenuItem = tuple | None


def menu_style() -> str:
    """Стиль QMenu. !!!!!!!!!!!заменить на стиль меню таблицы документов."""
    return get_menu_style()


def build_menu(parent: QWidget, items: list[MenuItem]) -> QMenu:
    menu = QMenu(parent)
    menu.setStyleSheet(menu_style())
    for item in items:
        if item is SEPARATOR:
            menu.addSeparator()
            continue
        text, callback, *rest = item
        action = menu.addAction(text)
        action.setEnabled(rest[0] if rest else True)
        action.triggered.connect(lambda _checked=False, cb=callback: cb())
    return menu


def show_context_menu(parent: QWidget, global_pos: QPoint, items: list[MenuItem]):
    if items:
        build_menu(parent, items).exec(global_pos)


def show_menu_above(anchor: QWidget, items: list[MenuItem]):
    """Меню над кнопкой (например, плавающей «+»), выровнено по её правому краю."""
    if not items:
        return
    menu = build_menu(anchor, items)
    size = menu.sizeHint()
    top_right = anchor.mapToGlobal(anchor.rect().topRight())
    menu.exec(QPoint(top_right.x() - size.width(), top_right.y() - size.height() - 8))


def attach_context_menu(view: QWidget, items_for: Callable[[QPoint], list[MenuItem] | None]):
    """Вешает меню по правой кнопке на таблицу / дерево / заголовок.

    items_for(pos) получает позицию клика (в координатах viewport) и возвращает
    список пунктов; None или пустой список — меню не показывается.
    """
    view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    # у QAbstractScrollArea позиция приходит в координатах viewport, у заголовка — в своих
    target = view.viewport() if hasattr(view, "viewport") else view

    def _show(pos: QPoint):
        items = items_for(pos)
        if items:
            show_context_menu(view, target.mapToGlobal(pos), items)

    view.customContextMenuRequested.connect(_show)
