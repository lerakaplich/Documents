from PyQt6.QtCore import pyqtSignal

from client.windows.documents.menus.base_menu import BaseMenu


class ColumnsMenu(BaseMenu):
    """Меню для включения/отключения колонок таблицы.

    Список колонок задаёт панель документов (populate) при каждой смене
    вида — набор колонок зависит от типа/направления."""

    columnToggled = pyqtSignal(str, bool)  # (название колонки, показана ли)
    resetRequested = pyqtSignal()  # «Показать все столбцы»

    def __init__(self, columns: list[str] = None, parent=None):
        super().__init__(parent)
        self._actions = {}
        self.populate(columns or [], set())

    def populate(self, names, hidden):
        """
        Перестроить список колонок в меню.
        Старые QAction не удаляем вручную — self.clear() сам корректно
        удалит C++-объекты экшенов, поэтому RuntimeError:
        wrapped C/C++ object of type QAction has been deleted не возникает.
        """
        # 1. Полностью очищаем меню (Qt сам удалит старые QAction)
        self.clear()

        # 2. Пересоздаём словарь экшенов
        self._actions = {}

        # 3. Создаём новые экшены
        for name in names:
            action = self.addAction(name)
            action.setCheckable(True)
            action.setChecked(name not in hidden)
            action.toggled.connect(
                lambda checked, n=name: self.columnToggled.emit(n, checked)
            )
            self._actions[name] = action

    def get_checked_columns(self) -> list[str]:
        """Возвращает имена отмеченных колонок."""
        return [col for col, action in self._actions.items() if action.isChecked()]

    def set_column_checked(self, column: str, checked: bool):
        """Программно установить состояние колонки (сигнал сработает)."""
        if column in self._actions:
            self._actions[column].setChecked(checked)

    def set_column_checked_silent(self, column: str, checked: bool):
        """То же, но без сигнала columnToggled."""
        action = self._actions.get(column)
        if action is not None:
            action.blockSignals(True)
            action.setChecked(checked)
            action.blockSignals(False)
