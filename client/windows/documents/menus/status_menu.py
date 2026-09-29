from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction

from client.core.data.document_data import DocumentDataConfig
from client.windows.documents.menus.base_menu import BaseMenu


class StatusesMenu(BaseMenu):
    """Меню выбора статусов документов (фильтр на сервере).

    Пункты строятся из DocumentDataConfig.STATUS_MAPPING — коды совпадают
    с DocStatus сервера (under_review, partially_approved, approved, rejected)."""

    statusesChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_actions = {}  # код статуса -> QAction
        for code, label in DocumentDataConfig.STATUS_MAPPING.items():
            action = self.add_checkable_action(label)
            action.toggled.connect(lambda _checked: self.statusesChanged.emit())
            self._status_actions[code] = action

        self.addSeparator()
        self.clear_action = QAction("Сбросить фильтр статусов", self)
        self.addAction(self.clear_action)

    def get_checked_statuses(self) -> list[str]:
        """Возвращает КОДЫ выбранных статусов (для параметра status_filters)."""
        return [
            code for code, action in self._status_actions.items() if action.isChecked()
        ]

    def clear_selection(self):
        """Снимает все галочки; statusesChanged срабатывает один раз."""
        changed = False
        for action in self._status_actions.values():
            if action.isChecked():
                action.blockSignals(True)
                action.setChecked(False)
                action.blockSignals(False)
                changed = True
        if changed:
            self.statusesChanged.emit()

    def connect_clear_signal(self, slot):
        """Подключает обработчик к кнопке сброса."""
        self.clear_action.triggered.connect(slot)
