# client/core/table/managers/column/column_view_settings.py
"""
Локальное хранение видимости столбцов для конкретного «вида» таблицы.

Вид = тип документа + направление:
    все документы            -> type=all;direction=all
    направление              -> type=all;direction=internal
    тип внутри направления   -> type=5;direction=internal
Для каждого вида хранится список НАЗВАНИЙ скрытых столбцов (не индексов —
индексы сдвигаются между видами, например «Тип»/«Направление» есть только
в режиме «все»). Данные лежат в ~/.documents_app/settings.json.
"""

from client.core.settings.settings_manager import SettingsManager


class ColumnViewSettings:
    KEY = "column_visibility_by_view"

    def __init__(self):
        self._settings = SettingsManager()

    @staticmethod
    def make_key(type_id: int | None, direction: str | None) -> str:
        return f"type={type_id if type_id is not None else 'all'};direction={direction or 'all'}"

    def get_hidden(self, view_key: str) -> list[str]:
        data = self._settings.get(self.KEY, {}) or {}
        return list(data.get(view_key, []))

    def set_hidden(self, view_key: str, hidden: list[str]):
        data = dict(self._settings.get(self.KEY, {}) or {})
        if hidden:
            data[view_key] = list(hidden)
        else:
            data.pop(view_key, None)  # всё видно — запись не нужна
        self._settings.set(self.KEY, data)
