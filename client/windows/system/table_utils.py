# client/windows/system/table_utils.py
"""Общие помощники для таблиц вкладки «Система».

ResizableColumns:
  * все столбцы тянутся мышью, столбцы можно переставлять перетаскиванием заголовка;
  * ширина и порядок столбцов запоминаются в SettingsManager (отдельно для каждой таблицы);
  * ПКМ по заголовку — «Сбросить ширину и порядок столбцов».
"""

from PyQt6.QtCore import QEvent, QObject, QTimer
from PyQt6.QtWidgets import QHeaderView, QTableWidget

from client.core.settings.settings_keys import SettingsKeys
from client.core.settings.settings_manager import SettingsManager
from client.core.utils.context_menu import attach_context_menu

SORT_ASC = " ▲"
SORT_DESC = " ▼"

MAX_COLUMN_WIDTH = 2000


class ResizableColumns(QObject):
    """Делает все столбцы изменяемыми мышью и запоминает раскладку.

    Начальные ширины считаются пропорционально `weights` от ширины таблицы,
    последний (визуально) столбец тянется на остаток. Как только пользователь
    потянул границу столбца или раскладка восстановлена из настроек, автоподгонка
    отключается и ширины больше не трогаются.

    `settings_key` — имя таблицы в настройках (например "system_employees");
    значения лежат в тех же ключах, что и у таблицы документов
    (column_widths_<key>, column_order_<key>). Без ключа раскладка не сохраняется.
    """

    SAVE_DELAY_MS = 400

    def __init__(
        self,
        table: QTableWidget,
        weights: list[int],
        settings_key: str | None = None,
        min_width: int = 70,
        movable: bool = True,
    ):
        super().__init__(table)
        self.table = table
        self.weights = weights
        self.settings_key = settings_key
        self._manual = False
        self._busy = False

        h = table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        h.setMinimumSectionSize(min_width)
        h.setStretchLastSection(True)
        h.setCascadingSectionResizes(False)
        h.setSectionsMovable(movable)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(self.SAVE_DELAY_MS)
        self._save_timer.timeout.connect(self._save)

        self._restore()

        h.sectionResized.connect(self._on_section_resized)
        h.sectionMoved.connect(self._on_section_moved)
        table.viewport().installEventFilter(self)

        # ПКМ по заголовку (политика CustomContextMenu ставится внутри attach_context_menu)
        attach_context_menu(h, self._header_menu_items)

        QTimer.singleShot(0, self.fit)

    # ==================== РАСКЛАДКА ПО УМОЛЧАНИЮ ====================

    def fit(self):
        """Расставить ширины по весам (если пользователь ещё не менял их сам)."""
        if self._manual:
            return
        width = self.table.viewport().width()
        if width <= 0:
            return
        h = self.table.horizontalHeader()
        count = self.table.columnCount()
        total = sum(self.weights[:count]) or 1
        self._busy = True
        try:
            for visual in range(count - 1):  # последний столбец тянется сам
                col = h.logicalIndex(visual)
                weight = self.weights[col] if col < len(self.weights) else 100
                self.table.setColumnWidth(col, max(h.minimumSectionSize(), int(width * weight / total)))
        finally:
            self._busy = False

    def reset_layout(self):
        """Вернуть порядок и ширины по умолчанию и забыть сохранённые."""
        h = self.table.horizontalHeader()
        self._busy = True
        try:
            for visual in range(self.table.columnCount()):
                h.moveSection(h.visualIndex(visual), visual)
        finally:
            self._busy = False
        self._save_timer.stop()
        self._forget()
        self._manual = False
        self.fit()

    # ==================== СОХРАНЕНИЕ / ВОССТАНОВЛЕНИЕ ====================

    def _restore(self):
        if not self.settings_key:
            return
        settings = SettingsManager()
        h = self.table.horizontalHeader()
        count = self.table.columnCount()

        # порядок: список логических индексов в визуальном порядке
        order = settings.get_column_order(self.settings_key)
        if isinstance(order, list) and sorted(order) == list(range(count)):
            self._busy = True
            try:
                for visual, logical in enumerate(order):
                    h.moveSection(h.visualIndex(logical), visual)
            finally:
                self._busy = False

        # ширины: {"0": 290, "1": 190, ...}
        widths = settings.get_column_widths(self.settings_key)
        if not isinstance(widths, dict):
            return
        restored = False
        self._busy = True
        try:
            for visual in range(count - 1):  # последний столбец тянется сам
                logical = h.logicalIndex(visual)
                value = widths.get(str(logical))
                if isinstance(value, int) and h.minimumSectionSize() <= value <= MAX_COLUMN_WIDTH:
                    self.table.setColumnWidth(logical, value)
                    restored = True
        finally:
            self._busy = False
        if restored:
            self._manual = True  # дальше ширины ведёт пользователь

    def _save(self):
        if not self.settings_key:
            return
        h = self.table.horizontalHeader()
        count = self.table.columnCount()
        settings = SettingsManager()
        settings.set_column_widths({str(i): self.table.columnWidth(i) for i in range(count)}, self.settings_key)
        settings.set_column_order([h.logicalIndex(v) for v in range(count)], self.settings_key)

    def _forget(self):
        if not self.settings_key:
            return
        settings = SettingsManager()
        for base in (SettingsKeys.COLUMN_WIDTHS, SettingsKeys.COLUMN_ORDER):
            settings.remove(SettingsKeys.get_type_key(base, self.settings_key))

    # ==================== СОБЫТИЯ ====================

    def _on_section_resized(self, index: int, _old: int, _new: int):
        h = self.table.horizontalHeader()
        # последний столбец тянется сам — это не действие пользователя
        if self._busy or h.visualIndex(index) == self.table.columnCount() - 1:
            return
        self._manual = True
        self._save_timer.start()

    def _on_section_moved(self, _logical: int, _old_visual: int, _new_visual: int):
        if self._busy:
            return
        self._save_timer.start()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize and obj is self.table.viewport():
            self.fit()
        return False

    def _header_menu_items(self, _pos):
        return [("Сбросить ширину и порядок столбцов", self.reset_layout)]


def header_label(title: str, col: int, sort_col: int, ascending: bool) -> str:
    """Подпись заголовка со стрелкой сортировки у активного столбца."""
    if col != sort_col:
        return title
    return title + (SORT_ASC if ascending else SORT_DESC)
