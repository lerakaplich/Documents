# client/windows/documents/menus/filter_menu.py
from datetime import date

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction

from client.windows.documents.menus.base_menu import BaseMenu


class FilterMenu(BaseMenu):
    """Меню фильтров документов.

    Группы:
      • «Мои документы» / «Все документы» — ровно один из двух → scope my/all;
      • «По дате…» — открывает диалог выбора периода (date_from / date_to).
    """

    filterChanged = pyqtSignal()  # изменился любой фильтр
    dateFilterRequested = pyqtSignal()  # нажали «По дате…» — панель откроет диалог

    def __init__(self, parent=None):
        super().__init__(parent)
        self._date_from: date | None = None
        self._date_to: date | None = None

        self.my_docs_action = self.add_checkable_action("Мои документы")
        self.all_docs_action = self.add_checkable_action("Все документы", checked=True)
        self.addSeparator()
        self.by_date_action = QAction("По дате…", self)
        self.addAction(self.by_date_action)
        # PeriodDialog не умеет «сбросить период», поэтому — отдельный пункт,
        # он виден только когда период задан
        self.reset_date_action = QAction("Сбросить период", self)
        self.reset_date_action.setVisible(False)
        self.addAction(self.reset_date_action)

        self.my_docs_action.toggled.connect(
            lambda c: self._on_pair_toggled(self.my_docs_action, self.all_docs_action, c)
        )
        self.all_docs_action.toggled.connect(
            lambda c: self._on_pair_toggled(self.all_docs_action, self.my_docs_action, c)
        )
        self.by_date_action.triggered.connect(lambda: self.dateFilterRequested.emit())
        self.reset_date_action.triggered.connect(self._on_reset_date)

    # ---------- внутреннее ----------

    @staticmethod
    def _set_silent(action: QAction, state: bool):
        action.blockSignals(True)
        action.setChecked(state)
        action.blockSignals(False)

    def _on_pair_toggled(self, changed: QAction, other: QAction, checked: bool):
        if checked:
            self._set_silent(other, False)
        else:
            # в группе «мои/все» нельзя снять единственный выбранный пункт
            self._set_silent(changed, True)
            return
        self.filterChanged.emit()

    def _on_reset_date(self):
        self.set_date_range(None, None)
        self.filterChanged.emit()

    def _update_date_text(self):
        if self._date_from and self._date_to:
            self.by_date_action.setText(f"По дате: {self._date_from:%d.%m.%Y} – {self._date_to:%d.%m.%Y}")
        else:
            self.by_date_action.setText("По дате…")
        self.reset_date_action.setVisible(bool(self._date_from and self._date_to))

    # ---------- публичное API ----------

    def get_date_range(self):
        """(date_from, date_to) как datetime.date или (None, None)."""
        return self._date_from, self._date_to

    def set_date_range(self, date_from: date | None, date_to: date | None):
        """Запоминает период и обновляет подпись пункта. Сигнал не шлёт —
        панель сама решает, когда перезагружать данные."""
        self._date_from, self._date_to = date_from, date_to
        self._update_date_text()

    def get_active_filters(self) -> dict:
        """Фильтры в виде, удобном для контроллера/сервера."""
        return {
            "scope": "my" if self.my_docs_action.isChecked() else "all",
            "date_from": self._date_from.isoformat() if self._date_from else None,
            "date_to": self._date_to.isoformat() if self._date_to else None,
        }

    def reset(self):
        """Сбрасывает фильтры к значениям по умолчанию (сигнал — один раз)."""
        self._set_silent(self.my_docs_action, False)
        self._set_silent(self.all_docs_action, True)
        self.set_date_range(None, None)
        self.filterChanged.emit()