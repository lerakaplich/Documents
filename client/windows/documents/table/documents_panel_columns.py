"""
Управление видимостью столбцов таблицы документов: меню «Столбцы» +
локальное сохранение раскладки по виду «тип + направление» (ColumnViewSettings).

Вынесено из DocumentsPanel, чтобы не раздувать один файл. Инстанс привязан
к конкретной DocumentsPanel через `panel` и обращается к её виджетам
(panel.columnsBtn, panel.documents_table) напрямую — никакого отдельного
состояния сверх ColumnViewSettings не хранит.
"""

from client.core.table.managers.column.column_view_settings import ColumnViewSettings
from client.windows.documents.menus.column_menu import ColumnsMenu

# Служебные столбцы: всегда скрыты и не показываются в меню «Столбцы»
ALWAYS_HIDDEN = {"ID"}

class DocumentsColumnController:
    def __init__(self, panel):
        self.panel = panel
        self.settings = ColumnViewSettings()
        self.menu = None

        if hasattr(panel, "columnsBtn"):
            self.menu = ColumnsMenu(parent=panel)
            self.menu.columnToggled.connect(self._on_toggled)
            self.menu.resetRequested.connect(self._on_reset)
            panel.columnsBtn.clicked.connect(self.show_menu)

    def show_menu(self):
        if self.menu is None:
            return
        btn = self.panel.columnsBtn
        self.menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    # ---------- ключ вида ----------

    def _view_key(self) -> str:
        c = self.panel.controller
        if c.current_view_mode == "archive":
            return "archive"  # ← отдельный ключ для настроек архива
        return ColumnViewSettings.make_key(c.current_type_id, c.current_direction)

    def _column_names(self) -> list:
        table = self.panel.documents_table.tableWidget
        names = []
        for c in range(table.columnCount()):
            item = table.horizontalHeaderItem(c)
            names.append(item.text() if item else f"Колонка {c + 1}")
        return names

    # ---------- публичное API, вызывается из DocumentsPanel ----------

    def apply_layout(self):
        """Применяет сохранённую видимость столбцов текущего вида и обновляет меню.
        Вызывается после каждой перестройки таблицы; выставляет видимость ВСЕХ
        столбцов явно, поэтому состояние прошлого вида не «протекает»."""
        table = self.panel.documents_table.tableWidget
        names = self._column_names()
        user_names = [n for n in names if n not in ALWAYS_HIDDEN]

        hidden = (set(self.settings.get_hidden(self._view_key())) & set(names)) - ALWAYS_HIDDEN
        if user_names and len(hidden) >= len(user_names):
            hidden = set()  # нельзя скрыть всё

        for col, name in enumerate(names):
            table.setColumnHidden(col, name in hidden or name in ALWAYS_HIDDEN)

        if self.menu is not None:
            self.menu.populate(user_names, hidden)

    def _save_hidden(self):
        table = self.panel.documents_table.tableWidget
        names = self._column_names()
        hidden = [names[c] for c in range(len(names)) if table.isColumnHidden(c) and names[c] not in ALWAYS_HIDDEN]
        self.settings.set_hidden(self._view_key(), hidden)

    def _on_toggled(self, name: str, visible: bool):
        table = self.panel.documents_table.tableWidget
        names = self._column_names()
        if name not in names:
            return
        col = names.index(name)

        if not visible:
            visible_count = sum(1 for c in range(len(names)) if not table.isColumnHidden(c))
            if visible_count <= 1:  # последний видимый столбец скрыть нельзя
                self.menu.set_column_checked_silent(name, True)
                return

        table.setColumnHidden(col, not visible)
        self._save_hidden()

    def _on_reset(self):
        self.settings.set_hidden(self._view_key(), [])
        self.apply_layout()
