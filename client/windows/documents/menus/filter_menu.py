# client/windows/documents/table/menus/filter_menu.py
from PyQt6.QtCore import pyqtSignal
from client.windows.documents.menus.base_menu import BaseMenu

class FilterMenu(BaseMenu):
    """Меню фильтров документов."""
    filterChanged = pyqtSignal()  # сигнал при любом изменении фильтра

    def __init__(self, parent=None):
        super().__init__(parent)
        self.unread_action = self.add_checkable_action("Непрочитанные")
        self.read_action = self.add_checkable_action("Прочитанные")
        self.addSeparator()
        self.my_docs_action = self.add_checkable_action("Мои документы")
        self.all_docs_action = self.add_checkable_action("Все документы", checked=True)
        self.addSeparator()
        self.by_date_action = self.add_checkable_action("По дате (сначала новые)")

        # Подключаем сигнал при каждом переключении
        for action in [self.unread_action, self.read_action,
                       self.my_docs_action, self.all_docs_action,
                       self.by_date_action]:
            action.toggled.connect(self.filterChanged.emit)

    def get_active_filters(self) -> dict:
        """Возвращает словарь состояний всех фильтров."""
        return {
            "unread": self.unread_action.isChecked(),
            "read": self.read_action.isChecked(),
            "my_docs": self.my_docs_action.isChecked(),
            "all_docs": self.all_docs_action.isChecked(),
            "by_date_desc": self.by_date_action.isChecked()
        }

    def reset(self):
        """Сбрасывает фильтры к значениям по умолчанию."""
        self.unread_action.setChecked(False)
        self.read_action.setChecked(False)
        self.my_docs_action.setChecked(False)
        self.all_docs_action.setChecked(True)
        self.by_date_action.setChecked(False)