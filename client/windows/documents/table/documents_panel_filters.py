"""
Меню «Фильтр»/«Статусы» + диалог периода (PeriodDialog) + фильтр по тегам.
Все фильтры уходят на сервер через DocumentsPanelController.set_filters().

Вынесено из DocumentsPanel; после применения фильтров зовёт
panel._update_table(...) — единственная точка, которая реально трогает UI
таблицы, поэтому она остаётся в самой панели.
"""

from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QToolTip, QWidget, QSizePolicy

from client.windows.documents.menus.filter_menu import FilterMenu
from client.windows.documents.menus.status_menu import StatusesMenu
from client.windows.period_dialog import PeriodDialog

MAX_TAG_FILTERS = 5


def _text_on(bg: str) -> str:
    """Читаемый цвет текста для фона заданного цвета."""
    c = QColor(bg)
    if not c.isValid():
        return "#FFFFFF"
    luminance = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
    return "#1B232A" if luminance > 160 else "#FFFFFF"


class DocumentsFilterController:
    def __init__(self, panel):
        self.panel = panel
        self.filter_menu = None
        self.statuses_menu = None

        # Выбранные теги: [{"id", "name", "color"}], не больше MAX_TAG_FILTERS
        self.selected_tags: list[dict] = []
        self._tag_bar = None
        self._tag_row = None

        # Быстрые клики по нескольким пунктам меню склеиваем в один запрос
        self._timer = QTimer(panel)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._reload)

        if hasattr(panel, "filterBtn"):
            self.filter_menu = FilterMenu(panel)
            self.filter_menu.filterChanged.connect(self.schedule_reload)
            self.filter_menu.dateFilterRequested.connect(self._choose_date_range)
            panel.filterBtn.clicked.connect(self.show_filter_menu)

        if hasattr(panel, "statusesBtn"):
            self.statuses_menu = StatusesMenu(panel)
            self.statuses_menu.statusesChanged.connect(self.schedule_reload)
            panel.statusesBtn.clicked.connect(self.show_statuses_menu)
            self.statuses_menu.connect_clear_signal(self.statuses_menu.clear_selection)

        self._build_tag_bar()

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
            tag_ids=[t["id"] for t in self.selected_tags],
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

    # ---------- фильтр по тегам ----------

    def _build_tag_bar(self):
        """Контейнер чипов — в toolBar между «Статусы» и «Статистика»."""
        layout = getattr(self.panel, "toolBarLayout", None)
        anchor = getattr(self.panel, "statusesBtn", None)
        if layout is None or anchor is None:
            return

        self._tag_bar = QWidget(self.panel)
        self._tag_bar.setObjectName("tagFilterBar")
        # Ignored по ширине: при нехватке места чипы сжимаются, а не раздувают окно
        self._tag_bar.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        self._tag_row = QHBoxLayout(self._tag_bar)
        self._tag_row.setContentsMargins(0, 0, 0, 0)
        self._tag_row.setSpacing(6)
        self._tag_bar.hide()

        # Сразу после «Статусы» (перед растягивающимся спейсером);
        # stretch=1 отдаёт чипам всё свободное место панели
        layout.insertWidget(layout.indexOf(anchor) + 1, self._tag_bar, 1)

    def _make_chip(self, tag: dict) -> QPushButton:
        color = tag.get("color") or "#808080"
        text_color = _text_on(color)
        hover = QColor(color).darker(115).name()

        btn = QPushButton()
        label = btn.fontMetrics().elidedText(tag["name"], Qt.TextElideMode.ElideRight, 90)
        btn.setText(f"{label}  ✕")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(f"{tag['name']} — нажмите, чтобы снять фильтр")
        btn.setFixedHeight(24)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: {text_color};
                border: none;
                border-radius: 12px;
                padding: 0 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """)
        btn.clicked.connect(lambda _=False, tid=tag["id"]: self.remove_tag(tid))
        return btn

    def toggle_tag(self, tag: dict):
        """Клик по тегу в таблице: добавить в фильтр или снять, если уже выбран."""
        tag_id = tag.get("id")
        if tag_id is None:
            return
        if any(t["id"] == tag_id for t in self.selected_tags):
            self.remove_tag(tag_id)
            return
        if len(self.selected_tags) >= MAX_TAG_FILTERS:
            QToolTip.showText(QCursor.pos(), f"Можно выбрать не более {MAX_TAG_FILTERS} тегов")
            return
        self.selected_tags.append(
            {"id": tag_id, "name": tag.get("name", ""), "color": tag.get("color") or "#808080"}
        )
        self._rebuild_tag_chips()
        self.schedule_reload()

    def remove_tag(self, tag_id: int):
        self.selected_tags = [t for t in self.selected_tags if t["id"] != tag_id]
        self._rebuild_tag_chips()
        self.schedule_reload()

    def _rebuild_tag_chips(self):
        if self._tag_bar is None:
            return
        while self._tag_row.count():
            item = self._tag_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
        for tag in self.selected_tags:
            # AlignVCenter — чипы по центру строки, на одной линии с кнопками панели
            self._tag_row.addWidget(self._make_chip(tag), 0, Qt.AlignmentFlag.AlignVCenter)
        self._tag_row.addStretch(1)
        self._tag_bar.setVisible(bool(self.selected_tags))

