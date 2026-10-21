# client/windows/documents/table/create/document_dialog_type_fields.py
"""
Поля диалога документа в зависимости от конфига типа (types.fields):
показ/скрытие виджетов, раскладка ячеек, подгонка высоты окна
"""

import json

from client.windows.documents.table.create.document_dialog_constants import (
    ALWAYS_VISIBLE,
    CELL_ROWS,
    FIELD_ALIASES,
    HEADER_BLOCKS,
    ROW_LAYOUTS,
    SIMPLE_FIELDS,
)


class TypeFieldsMixin:
    def _current_type_fields(self) -> dict | None:
        """types.fields выбранного типа (dict или JSON-строка) либо None."""
        if not hasattr(self, "type_box"):
            return None
        type_id = self.type_box.currentData()
        if type_id is None:
            return None
        for t in self.document_types_data:
            if t.get("id") == type_id:
                fields = t.get("fields")
                if isinstance(fields, str):
                    try:
                        fields = json.loads(fields)
                    except ValueError:
                        return None
                return fields if isinstance(fields, dict) else None
        return None

    def _field_enabled(self, key: str) -> bool:
        """Поле показывается, если тип его включает. Конфиг типа хранит только
        включённые поля (или явные false), поэтому отсутствие ключа = поле выключено.
        Пустой конфиг (тип не выбран или не настроен) — показываем всё.
        Обязательные поля (ALWAYS_VISIBLE) показываются всегда."""
        if key in ALWAYS_VISIBLE:
            return True
        if not self._active_fields:
            return True
        return any(bool(self._active_fields.get(k)) for k in FIELD_ALIASES.get(key, (key,)))

    def _apply_type_fields(self, *_):
        root = self.layout()
        if root is None:
            return
        self._active_fields = self._current_type_fields() or {}

        # Эталон снимаем один раз, пока ничего не скрыто (включая type_box/direction_box)
        if self._base_height is None:
            self.ensurePolished()
            root.invalidate()
            root.activate()
            self._full_min_height = root.minimumSize().height()
            self._base_height = max(self.height(), self._full_min_height)

        def set_visible(names, flag):
            for name in names:
                w = getattr(self, name, None)
                if w is not None:
                    w.setVisible(flag)

        for key, names in SIMPLE_FIELDS.items():
            set_visible(names, self._field_enabled(key))

        for row in CELL_ROWS:
            for key, _layout_name, names in row:
                set_visible(names, self._field_enabled(key))

        for label_name, keys in HEADER_BLOCKS.items():
            set_visible((label_name,), any(self._field_enabled(k) for k in keys))

        # Тип и направление заданы вкладкой — эти поля не показываем;
        # если скрыты оба, заголовок «Основные реквизиты» тоже не нужен
        set_visible(("type_box",), not self._type_pinned)
        set_visible(("direction_box",), not self._direction_pinned)
        set_visible(("labelBasic",), not (self._type_pinned and self._direction_pinned))

        self._arrange_cell_rows()
        self._fit_height()

    def _arrange_cell_rows(self):
        """Раскладывает видимые ячейки по двум строкам; если в каждой строке
        осталось по одной ячейке — сливает их в одну строку."""
        hboxes = [getattr(self, n, None) for n in ROW_LAYOUTS]
        if any(h is None for h in hboxes):
            return  # fallback-UI без этих layout'ов

        for hbox in hboxes:
            while hbox.count():
                hbox.takeAt(0)  # parent у вынутого layout'а сбрасывается

        rows = []
        for row in CELL_ROWS:
            cells = [getattr(self, layout_name) for key, layout_name, _ in row if self._field_enabled(key)]
            if cells:
                rows.append(cells)

        if len(rows) == 2 and len(rows[0]) == 1 and len(rows[1]) == 1:
            rows = [[rows[0][0], rows[1][0]]]

        for hbox, cells in zip(hboxes, rows):
            for cell in cells:
                hbox.addLayout(cell)

    def _fit_height(self):
        """Уменьшает высоту окна ровно на высоту скрытых блоков + их отступы."""
        root = self.layout()
        root.invalidate()
        root.activate()  # у top-level окна это же обновляет minimumSize
        new_min = root.minimumSize().height()
        freed = max(0, self._full_min_height - new_min)
        target = max(new_min, self._base_height - freed)
        if self.height() != target:
            self.resize(self.width(), target)