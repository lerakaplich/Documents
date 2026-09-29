# client/windows/documents/menus/filter_menu.py
from datetime import date
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction

from client.windows.documents.menus.base_menu import BaseMenu


class FilterMenu(BaseMenu):
    """Меню фильтров документов.

    Группы:
      • «Только прочитанные» / «Только непрочитанные» — взаимоисключающие,
        можно снять обе (тогда показываются все) → is_completed True/False/None;
      • «Мои документы» / «Все документы» — ровно один из двух → scope my/all;
      • «По дате…» — открывает диалог выбора периода (date_from / date_to).
    """

    filterChanged = pyqtSignal()          # изменился любой фильтр
    dateFilterRequested = pyqtSignal()    # нажали «По дате…» — панель откроет диалог

    def __init__(self, parent=None):
        super().__init__(parent)
        self._date_from: Optional[date] = None
        self._date_to: Optional[date] = None

        self.only_read_action = self.add_checkable_action("Только прочитанные")
        self.only_unread_action = self.add_checkable_action("Только непрочитанные")
        self.addSeparator()
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

        self.only_read_action.toggled.connect(
            lambda c: self._on_pair_toggled(self.only_read_action, self.only_unread_action, c, must_keep_one=False))
        self.only_unread_action.toggled.connect(
            lambda c: self._on_pair_toggled(self.only_unread_action, self.only_read_action, c, must_keep_one=False))
        self.my_docs_action.toggled.connect(
            lambda c: self._on_pair_toggled(self.my_docs_action, self.all_docs_action, c, must_keep_one=True))
        self.all_docs_action.toggled.connect(
            lambda c: self._on_pair_toggled(self.all_docs_action, self.my_docs_action, c, must_keep_one=True))
        self.by_date_action.triggered.connect(lambda: self.dateFilterRequested.emit())
        self.reset_date_action.triggered.connect(self._on_reset_date)

    # ---------- внутреннее ----------

    @staticmethod
    def _set_silent(action: QAction, state: bool):
        action.blockSignals(True)
        action.setChecked(state)
        action.blockSignals(False)

    def _on_pair_toggled(self, changed: QAction, other: QAction, checked: bool, must_keep_one: bool):
        if checked:
            self._set_silent(other, False)
        elif must_keep_one:
            # в группе «мои/все» нельзя снять единственный выбранный пункт
            self._set_silent(changed, True)
            return
        self.filterChanged.emit()

    def _on_reset_date(self):
        self.set_date_range(None, None)
        self.filterChanged.emit()

    def _update_date_text(self):
        if self._date_from and self._date_to:
            self.by_date_action.setText(
                f"По дате: {self._date_from:%d.%m.%Y} – {self._date_to:%d.%m.%Y}"
            )
        else:
            self.by_date_action.setText("По дате…")
        self.reset_date_action.setVisible(bool(self._date_from and self._date_to))

    # ---------- публичное API ----------

    def get_date_range(self):
        """(date_from, date_to) как datetime.date или (None, None)."""
        return self._date_from, self._date_to

    def set_date_range(self, date_from: Optional[date], date_to: Optional[date]):
        """Запоминает период и обновляет подпись пункта. Сигнал не шлёт —
        панель сама решает, когда перезагружать данные."""
        self._date_from, self._date_to = date_from, date_to
        self._update_date_text()

    def get_active_filters(self) -> dict:
        """Фильтры в виде, удобном для контроллера/сервера."""
        if self.only_read_action.isChecked():
            is_completed = True
        elif self.only_unread_action.isChecked():
            is_completed = False
        else:
            is_completed = None

        return {
            "scope": "my" if self.my_docs_action.isChecked() else "all",
            "is_completed": is_completed,
            "date_from": self._date_from.isoformat() if self._date_from else None,
            "date_to": self._date_to.isoformat() if self._date_to else None,
        }

    def reset(self):
        """Сбрасывает фильтры к значениям по умолчанию (сигнал — один раз)."""
        self._set_silent(self.only_read_action, False)
        self._set_silent(self.only_unread_action, False)
        self._set_silent(self.my_docs_action, False)
        self._set_silent(self.all_docs_action, True)
        self.set_date_range(None, None)
        self.filterChanged.emit()