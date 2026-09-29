"""
Меню «Фильтр»/«Статусы» + диалог периода (PeriodDialog). Все фильтры
уходят на сервер через DocumentsPanelController.set_filters().

Вынесено из DocumentsPanel; после применения фильтров зовёт
panel._update_table(...) — единственная точка, которая реально трогает UI
таблицы, поэтому она остаётся в самой панели.
"""
from PyQt6.QtCore import QTimer, QDate

from client.windows.documents.menus.filter_menu import FilterMenu
from client.windows.documents.menus.status_menu import StatusesMenu
from client.windows.period_dialog import PeriodDialog


class DocumentsFilterController:

    def __init__(self, panel):
        self.panel = panel
        self.filter_menu = None
        self.statuses_menu = None

        # Быстрые клики по нескольким пунктам меню склеиваем в один запрос
        self._timer = QTimer(panel)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._reload)

        if hasattr(panel, 'filterBtn'):
            self.filter_menu = FilterMenu(panel)
            self.filter_menu.filterChanged.connect(self.schedule_reload)
            self.filter_menu.dateFilterRequested.connect(self._choose_date_range)
            panel.filterBtn.clicked.connect(self.show_filter_menu)

        if hasattr(panel, 'statusesBtn'):
            self.statuses_menu = StatusesMenu(panel)
            self.statuses_menu.statusesChanged.connect(self.schedule_reload)
            panel.statusesBtn.clicked.connect(self.show_statuses_menu)
            self.statuses_menu.connect_clear_signal(self.statuses_menu.clear_selection)

    def show_filter_menu(self):
        btn = self.panel.filterBtn
        self.filter_menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def show_statuses_menu(self):
        btn = self.panel.statusesBtn
        self.statuses_menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def schedule_reload(self):
        self._timer.start()

    def _reload(self):
        f = self.filter_menu.get_active_filters() if self.filter_menu else {}
        statuses = self.statuses_menu.get_checked_statuses() if self.statuses_menu else []
        documents, title, view_mode, doc_type = self.panel.controller.set_filters(
            scope=f.get("scope", "all"),
            is_completed=f.get("is_completed"),
            status_filters=statuses,
            date_from=f.get("date_from"),
            date_to=f.get("date_to"),
        )
        self.panel._update_table(documents, doc_type, title, view_mode)

    def _choose_date_range(self):
        """«По дате…» — общий диалог выбора периода (PeriodDialog), по дате создания."""
        cur_from, cur_to = self.filter_menu.get_date_range()
        start = QDate(cur_from.year, cur_from.month, cur_from.day) if cur_from else None
        end = QDate(cur_to.year, cur_to.month, cur_to.day) if cur_to else None

        dialog = PeriodDialog(parent=self.panel, start_date=start, end_date=end)
        dialog.period_selected.connect(self._on_period_selected)
        dialog.exec()

    def _on_period_selected(self, period: dict):
        self.filter_menu.set_date_range(period["start_date_python"], period["end_date_python"])
        self.schedule_reload()