from PyQt6.QtGui import QAction

from .base_menu import BaseMenu

class StatusesMenu(BaseMenu):
    """Меню выбора статусов документов."""
    STATUSES = ["Черновик", "На рассмотрении", "На подписи", "Подписан", "Завершен"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_actions = {}
        for status in self.STATUSES:
            action = self.add_checkable_action(status)
            self._status_actions[status] = action

        self.addSeparator()
        self.clear_action = QAction("Сбросить фильтр статусов", self)
        self.addAction(self.clear_action)

    def get_checked_statuses(self) -> list[str]:
        """Возвращает список выбранных статусов."""
        return [status for status, action in self._status_actions.items() if action.isChecked()]

    def clear_selection(self):
        """Снимает все галочки."""
        for action in self._status_actions.values():
            action.setChecked(False)

    def connect_clear_signal(self, slot):
        """Подключает обработчик к кнопке сброса."""
        self.clear_action.triggered.connect(slot)