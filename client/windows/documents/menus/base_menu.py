from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu

from client.windows.documents.table.styles import TableStyles


class BaseMenu(QMenu):
    """Базовый класс для всех меню панели документов."""

    # Клик по пункту с галочкой не закрывает меню — удобно, когда нужно
    # отметить несколько столбцов/статусов подряд.
    keep_open_on_check = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(TableStyles.get_menu_style())

    def add_checkable_action(self, text: str, checked: bool = False) -> QAction:
        """Добавляет пункт с галочкой и возвращает его."""
        action = QAction(text, self)
        action.setCheckable(True)
        action.setChecked(checked)
        self.addAction(action)
        return action

    def mouseReleaseEvent(self, event):
        if self.keep_open_on_check:
            action = self.actionAt(event.pos())
            if action is not None and action.isCheckable() and action.isEnabled():
                action.trigger()  # переключает галочку, меню остаётся открытым
                return
        super().mouseReleaseEvent(event)

    def showEvent(self, event):
        """Переприменяем стиль при каждом показе — берём актуальную тему."""
        from client.core.themes import get_menu_style

        self.setStyleSheet(get_menu_style())
        super().showEvent(event)

    def reapply_theme(self):
        from client.core.themes import get_menu_style

        self.setStyleSheet(get_menu_style())
