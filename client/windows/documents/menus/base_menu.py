from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu
from client.windows.documents.table.styles import TableStyles

class BaseMenu(QMenu):
    """Базовый класс для всех меню панели документов."""
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