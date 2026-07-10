from client.windows.documents.menus.base_menu import BaseMenu


class ColumnsMenu(BaseMenu):
    """Меню для включения/отключения колонок таблицы."""
    def __init__(self, columns: list[str] = None, parent=None):
        super().__init__(parent)
        self._actions = {}
        default_columns = [
            "ID", "Номер документа", "Тема", "Тип",
            "Дата", "Статус", "Отправитель", "Хэштеги"
        ]
        self.populate(columns if columns is not None else default_columns)

    def populate(self, columns: list[str]):
        """Заполняет меню указанными колонками (все отмечены по умолчанию)."""
        self.clear()
        self._actions.clear()
        for col in columns:
            action = self.add_checkable_action(col, checked=True)
            self._actions[col] = action

    def get_checked_columns(self) -> list[str]:
        """Возвращает имена отмеченных колонок."""
        return [col for col, action in self._actions.items() if action.isChecked()]

    def set_column_checked(self, column: str, checked: bool):
        """Программно установить состояние колонки."""
        if column in self._actions:
            self._actions[column].setChecked(checked)