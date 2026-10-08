# client/windows/system/structure/structure_page.py

import logging
import os
import sys
from typing import Any

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidgetItem,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt6.uic import loadUi

from client.core.config import config
from client.core.http_client import HttpClient
from client.core.state.app_state import AppState
from client.core.themes import T, apply_theme_to_widget
from client.core.utils.context_menu import SEPARATOR, attach_context_menu, show_menu_above
from client.services.org_service import get_org_service
from client.windows.animations.animated_notification import NotificationManager
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.system.common import badge_style, normalize_employee
from client.windows.system.system_actions import SystemActions
from client.windows.system.system_utils import PATH_SEP, org_label, to_tree, work_phone
from client.windows.system.table_utils import ResizableColumns, header_label

logger = logging.getLogger(__name__)

ID_ROLE = Qt.ItemDataRole.UserRole
EMP_HEADERS = ["ФИО", "Должность", "Отдел", "Рабочий телефон"]
EMP_SETTINGS_KEY = "system_structure_employees"  # ключ раскладки (ширина/порядок столбцов) в настройках


class _LeaveFilter(QObject):
    """Прячет кнопки узла, когда курсор ушёл с дерева."""

    def __init__(self, page):
        super().__init__(page)
        self.page = page

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Leave:
            vp = self.page.treeWidget.viewport()
            if not vp.rect().contains(vp.mapFromGlobal(QCursor.pos())):
                self.page._hide_node_actions()
        return False


class StructurePage(QWidget):
    """Страница структуры: организации и подразделения слева, карточка узла и сотрудники справа.

    Данные грузятся через OrgService:
      - организации        -> get_all_organizations()   (сразу)
      - подразделения      -> get_org_structure(org_id) (при первом раскрытии организации)
      - сотрудники         -> get_org_employees(org_id) (при выборе узла, кэшируются)
    """

    data_loaded = pyqtSignal()
    structure_changed = pyqtSignal()  # отдел / тип / организация / сотрудник изменены

    def __init__(self, parent=None, http_client: HttpClient | None = None):
        super().__init__(parent)

        # Используем переданный HttpClient или создаем новый
        if http_client is None:
            app_state = AppState()
            if app_state.http_client:
                self.http_client = app_state.http_client
            else:
                self.http_client = HttpClient(config.base_url)
        else:
            self.http_client = http_client

        self.org_service = get_org_service(self.http_client)

        # Данные
        self.organizations: list[dict[str, Any]] = []
        self._nodes: dict[str, dict[str, Any]] = {}  # key -> узел ("o:<id>" / "d:<id>")
        self._items: dict[str, QTreeWidgetItem] = {}
        self._structure_loaded: set[int] = set()
        self._employees_cache: dict[int, list[dict[str, Any]]] = {}

        # Состояние
        self.is_loading = False
        self._hover_key = ""
        self._emp_sort_col = 0  # сортировка таблицы сотрудников кликом по заголовку
        self._emp_sort_asc = True
        self._rows_count = 0
        self._detail_rows: list[dict[str, Any]] = []  # строки таблицы сотрудников выбранного узла

        # Инициализация
        self.init_ui()
        self.setup_connections()

        # Создаем менеджер уведомлений
        self.notification_manager = NotificationManager(self, max_visible=3)

        # Действия (диалоги + сервисы)
        self.system_actions = SystemActions(self, self.http_client)
        self.system_actions.message.connect(self._on_action_message)
        self.system_actions.structure_changed.connect(self._on_changed)
        self.system_actions.employees_changed.connect(self._on_changed)

        # Загружаем данные
        QTimer.singleShot(100, self.load_data)

    def init_ui(self):
        """Инициализация UI из файла"""
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)
            apply_theme_to_widget(self)

        self._setup_tree()
        self._setup_node_actions()
        self._setup_employees_table()

        self.typeBadge.setStyleSheet(badge_style("neutral"))
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([320, 680])

        # Создаем плавающую кнопку
        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self._show_add_menu)

        # Подключаемся к скроллу
        self.scrollArea.verticalScrollBar().valueChanged.connect(self.on_scroll)

        # Скрываем кнопку сброса при старте
        self.btnResetFilters.hide()
        self.scrollArea.hide()

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, "..", "..", "..", "ui", "system", "structure", "structure_page.ui")
        return os.path.normpath(ui_path)

    def setup_connections(self):
        """Настройка сигналов"""
        self.searchEdit.textChanged.connect(self.on_search_changed)
        self.btnResetFilters.clicked.connect(self.reset_all_filters)
        self.btnExpand.clicked.connect(self.expand_all)
        self.btnCollapse.clicked.connect(self.treeWidget.collapseAll)

    # ==================== УВЕДОМЛЕНИЯ ====================

    def show_success_notification(self, message: str):
        """Показать уведомление об успехе"""
        self.notification_manager.show_notification(f"✅ {message}", duration=2500)

    def show_error_notification(self, message: str):
        """Показать уведомление об ошибке"""
        self.notification_manager.show_notification(f"❌ {message}", duration=3000)

    def show_info_notification(self, message: str):
        """Показать информационное уведомление"""
        self.notification_manager.show_notification(f"ℹ️ {message}", duration=2500)

    # ==================== ЗАГРУЗКА ДАННЫХ ====================

    def load_data(self, notify: bool = True):
        """Загрузить организации из API и построить корни дерева"""
        if self.is_loading:
            return

        self.is_loading = True

        try:
            self.organizations = self.org_service.get_all_organizations()
            self._structure_loaded.clear()
            self._employees_cache.clear()

            self.is_loading = False
            self.update_display()
            self.data_loaded.emit()

            if notify and self.organizations:
                self.show_success_notification(f"Загружено организаций: {len(self.organizations)}")

        except Exception as e:
            self.is_loading = False

            logger.exception(f"Ошибка загрузки структуры: {e}")

            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось загрузить структуру")

    def _ensure_structure(self, org_key: str):
        """Подгрузить подразделения организации при первом обращении"""
        node = self._nodes.get(org_key)
        if not node or node["kind"] != "org" or node["id"] in self._structure_loaded:
            return

        org_id = node["id"]
        try:
            raw = self.org_service.get_org_structure(org_id)
        except Exception as e:
            logger.exception(f"Ошибка загрузки структуры организации {org_id}: {e}")
            self.show_error_notification("Не удалось загрузить подразделения")
            return

        self._structure_loaded.add(org_id)

        org_item = self._items[org_key]
        while org_item.childCount():  # убираем заглушку «…»
            org_item.takeChild(0)

        self._add_children(org_item, org_key, org_id, self._to_tree(raw), depth=1)

    _to_tree = staticmethod(to_tree)  # понимает вложенный (children) и плоский (parent_id) ответ API

    def _add_children(self, parent_item, parent_key, org_id, tree_items, depth):
        for raw in tree_items:
            key = f"d:{raw['id']}"
            children = raw.get("children") or raw.get("departments") or []
            self._nodes[key] = {
                "key": key,
                "kind": "dep",
                "id": raw["id"],
                "org_id": org_id,
                "parent": parent_key,
                "depth": depth,
                "name": raw.get("name", "Без названия"),
                "raw": raw,
                "children": [f"d:{c['id']}" for c in children],
            }
            item = QTreeWidgetItem(parent_item, [self._nodes[key]["name"]])
            item.setData(0, ID_ROLE, key)
            item.setToolTip(0, self._nodes[key]["name"])
            self._items[key] = item
            self._add_children(item, key, org_id, children, depth + 1)
            item.setExpanded(True)

    # ==================== ДЕРЕВО ====================

    def _setup_tree(self):
        t = self.treeWidget
        t.setMouseTracking(True)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        t.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        t.currentItemChanged.connect(lambda cur, _prev: self._show_detail(cur.data(0, ID_ROLE) if cur else ""))
        t.itemExpanded.connect(lambda item: self._ensure_structure(item.data(0, ID_ROLE)))
        t.itemEntered.connect(lambda item, _col: self._show_node_actions(item))
        t.verticalScrollBar().valueChanged.connect(lambda _v: self._hide_node_actions())
        self._leave_filter = _LeaveFilter(self)
        t.viewport().installEventFilter(self._leave_filter)
        attach_context_menu(t, self._tree_menu_items)

    def _setup_node_actions(self):
        """Плавающая панель ＋ ✎ ✕ — появляется у узла под курсором."""
        self.nodeActions = QWidget(self.treeWidget.viewport())
        lay = QHBoxLayout(self.nodeActions)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        def make(text, tip, hover_bg, hover_fg, slot):
            btn = QPushButton(text)
            btn.setFixedSize(24, 24)
            btn.setToolTip(tip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; border-radius: 5px;"
                f" color: {T.TEXT_ACCENT_SOFT}; font-size: 14px; }}"
                f"QPushButton:hover {{ background-color: {hover_bg}; color: {hover_fg}; }}"
            )
            btn.clicked.connect(slot)
            lay.addWidget(btn)
            return btn

        self.btnNodeAdd = make("＋", "Добавить подразделение", T.BTN_EDIT_BG, T.ACCENT_PRIMARY, lambda: self.on_add_node(self._hover_key))
        self.btnNodeEdit = make("✎", "Редактировать", T.BTN_EDIT_BG, T.ACCENT_PRIMARY, lambda: self.on_edit_node(self._hover_key))
        self.btnNodeDelete = make("✕", "Удалить", T.BTN_DELETE_BG, T.BTN_DELETE_TEXT, lambda: self.on_delete_node(self._hover_key))
        self.nodeActions.adjustSize()
        self.nodeActions.hide()

    def _show_node_actions(self, item: QTreeWidgetItem):
        key = item.data(0, ID_ROLE)
        node = self._nodes.get(key)
        rect = self.treeWidget.visualItemRect(item)
        if not node or rect.isEmpty():
            return
        self._hover_key = key
        # организации редактируются на вкладке «Организации» — здесь только добавление подразделения
        is_dep = node["kind"] == "dep"
        self.btnNodeEdit.setVisible(is_dep)
        self.btnNodeDelete.setVisible(is_dep)
        self.nodeActions.adjustSize()

        vp = self.treeWidget.viewport()
        self.nodeActions.move(vp.width() - self.nodeActions.width() - 6, rect.y() + (rect.height() - self.nodeActions.height()) // 2)
        self.nodeActions.show()
        self.nodeActions.raise_()

    def _hide_node_actions(self):
        self.nodeActions.hide()
        self._hover_key = ""

    def _current_key(self) -> str:
        item = self.treeWidget.currentItem()
        return item.data(0, ID_ROLE) if item else ""

    def update_display(self):
        """Перестроить корни дерева по загруженным организациям"""
        keep = self._current_key()

        t = self.treeWidget
        t.blockSignals(True)
        t.clear()
        self._nodes.clear()
        self._items.clear()

        for org in self.organizations:
            key = f"o:{org['id']}"
            name = org.get("name") or org.get("short_name") or "Без названия"
            self._nodes[key] = {
                "key": key,
                "kind": "org",
                "id": org["id"],
                "org_id": org["id"],
                "parent": "",
                "depth": 0,
                "name": name,
                "raw": org,
                "children": [],
            }
            item = QTreeWidgetItem(t, [name])
            item.setData(0, ID_ROLE, key)
            item.setToolTip(0, name)
            placeholder = QTreeWidgetItem(item, ["…"])  # чтобы у организации была стрелка раскрытия
            placeholder.setData(0, ID_ROLE, "")
            self._items[key] = item
        t.blockSignals(False)

        target = self._items.get(keep) or next(iter(self._items.values()), None)
        if target:
            t.setCurrentItem(target)
        else:
            self._show_detail("")

        self._apply_filter()
        self.position_floating_button()

    def expand_all(self):
        for key, node in list(self._nodes.items()):
            if node["kind"] == "org":
                self._ensure_structure(key)
        self.treeWidget.expandAll()

    # ==================== ПОИСК И ФИЛЬТРЫ ====================

    def on_search_changed(self):
        self.update_reset_button_visibility()
        if self.searchEdit.text().strip():
            # поиск должен видеть все подразделения, поэтому догружаем структуру всех организаций
            for key, node in list(self._nodes.items()):
                if node["kind"] == "org":
                    self._ensure_structure(key)
        self._apply_filter()

    def has_active_filters(self):
        return bool(self.searchEdit.text().strip())

    def update_reset_button_visibility(self):
        if self.has_active_filters():
            self.btnResetFilters.show()
        else:
            self.btnResetFilters.hide()

    def reset_all_filters(self):
        self.searchEdit.clear()
        self.btnResetFilters.hide()
        self._apply_filter()
        self.show_info_notification("Фильтры сброшены")

    def _apply_filter(self):
        query = self.searchEdit.text().strip().lower()

        def visit(item: QTreeWidgetItem) -> bool:
            own = not query or query in item.text(0).lower()
            child_match = False
            for i in range(item.childCount()):
                child_match |= visit(item.child(i))
            visible = own or child_match
            item.setHidden(not visible)
            if query and child_match:
                item.setExpanded(True)
            return visible

        root = self.treeWidget.invisibleRootItem()
        for i in range(root.childCount()):
            visit(root.child(i))

    # ==================== ПРАВАЯ ПАНЕЛЬ ====================

    def _setup_employees_table(self):
        t = self.employeesTable
        t.setColumnCount(4)
        t.setHorizontalHeaderLabels(EMP_HEADERS)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(38)
        t.setShowGrid(False)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        t.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        h = t.horizontalHeader()
        h.setHighlightSections(False)
        h.setSectionsClickable(True)
        h.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        h.sectionClicked.connect(self._on_emp_header_clicked)
        # столбцы тянутся мышью и переставляются; раскладка запоминается; последний столбец занимает остаток
        self._columns = ResizableColumns(t, [30, 25, 28, 17], settings_key=EMP_SETTINGS_KEY)
        attach_context_menu(t, self._emp_menu_items)
        t.cellDoubleClicked.connect(lambda row, _col: self._edit_detail_row(row))
        t.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        # если пользователь растянул столбцы шире панели — учитываем полосу прокрутки в высоте
        t.horizontalScrollBar().rangeChanged.connect(lambda *_: self._fit_table_height())
        self._refresh_emp_headers()

    def _refresh_emp_headers(self):
        self.employeesTable.setHorizontalHeaderLabels(
            [header_label(title, col, self._emp_sort_col, self._emp_sort_asc) for col, title in enumerate(EMP_HEADERS)]
        )

    def _on_emp_header_clicked(self, col: int):
        if self._emp_sort_col == col:
            self._emp_sort_asc = not self._emp_sort_asc
        else:
            self._emp_sort_col, self._emp_sort_asc = col, True
        self._refresh_emp_headers()
        self._show_detail(self._current_key())

    def _sort_rows(self, rows):
        """Сортировка строк таблицы по выбранному столбцу, пустые значения — в конце"""
        col, asc = self._emp_sort_col, self._emp_sort_asc

        def value(r):
            return r["values"][col] or ""

        filled = [r for r in rows if value(r)]
        empty = [r for r in rows if not value(r)]
        filled.sort(key=lambda r: str(value(r)).lower(), reverse=not asc)
        return filled + empty

    def _fit_table_height(self):
        """Таблица лежит внутри прокручиваемой панели — подгоняем высоту под строки"""
        t = self.employeesTable
        height = t.horizontalHeader().height() + 38 * self._rows_count + 4
        sb = t.horizontalScrollBar()
        if sb.maximum() > 0:
            height += sb.sizeHint().height()
        t.setFixedHeight(height)

    def _org_employees(self, org_id: int) -> list[dict[str, Any]]:
        """Сотрудники организации (кэшируются, чтобы не дёргать API при каждом клике)"""
        if org_id not in self._employees_cache:
            try:
                raw = self.org_service.get_org_employees(org_id)
            except Exception as e:
                logger.exception(f"Ошибка загрузки сотрудников организации {org_id}: {e}")
                self.show_error_notification("Не удалось загрузить сотрудников")
                return []
            self._employees_cache[org_id] = [self._prepare_employee(e) for e in raw]
        return self._employees_cache[org_id]

    @staticmethod
    def _prepare_employee(raw: dict[str, Any]) -> dict[str, Any]:
        """Данные сотрудника для таблицы: нормализация + исходные данные (для диалога) + рабочий телефон"""
        emp = dict(normalize_employee(raw))  # копия: исходный dict с сервера не трогаем
        emp["_raw"] = raw
        emp["work_phone"] = work_phone(emp)
        return emp

    def _subtree(self, key: str) -> tuple[set, set]:
        """id и названия подразделения вместе со всеми вложенными"""
        ids, names = set(), set()

        def walk(k):
            node = self._nodes.get(k)
            if not node:
                return
            ids.add(node["id"])
            names.add(node["name"])
            for child in node["children"]:
                walk(child)

        walk(key)
        return ids, names

    def _node_rows(self, key: str) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """Пары (сотрудник, подходящая должность) для выбранного узла"""
        node = self._nodes[key]
        employees = self._org_employees(node["org_id"])

        if node["kind"] == "org":
            return [(e, (e["positions"][0] if e["positions"] else {})) for e in employees]

        ids, names = self._subtree(key)
        rows = []
        for e in employees:
            for p in e["positions"]:
                dep_id = p.get("department_id")
                if (dep_id is not None and dep_id in ids) or (dep_id is None and p.get("department") in names):
                    rows.append((e, p))
        return rows

    def _show_detail(self, key: str):
        node = self._nodes.get(key)
        self.scrollArea.setVisible(bool(node))
        if not node:
            return

        raw = node["raw"]
        is_org = node["kind"] == "org"

        self.titleLabel.setText(node["name"])
        if is_org:
            type_name = "Организация"
        else:
            type_name = (
                raw.get("type_name")
                or raw.get("department_type_name")
                or (raw.get("department_type") or {}).get("name")
                or "Подразделение"
            )
        self.typeBadge.setText(type_name)

        self.fieldCodeCaption.setText("УНП" if is_org else "Код подразделения")
        self.fieldCodeValue.setText((raw.get("unp") if is_org else (raw.get("code") or raw.get("smdo_code"))) or "—")
        self.fieldHeadCaption.setText("Директор" if is_org else "Руководитель")
        head = raw.get("director") if is_org else (raw.get("head") or raw.get("head_name") or raw.get("manager"))
        if isinstance(head, dict):
            head = head.get("full_name") or head.get("name")
        self.fieldHeadValue.setText(head or "Не назначен")
        self.fieldPhoneValue.setText(raw.get("phone_number") or raw.get("phone") or "Не указан")

        if is_org:
            self._ensure_structure(key)  # для путей «МАЗ / НТЦ / Телематика» нужны все отделы организации

        rows = [
            {
                "emp": emp,
                "values": (emp["full_name"], pos.get("position", ""), self._row_path(pos, node), emp.get("work_phone", "")),
            }
            for emp, pos in self._node_rows(key)
        ]
        rows = self._sort_rows(rows)
        self._detail_rows = rows
        self.employeesTitle.setText(f"Сотрудники ({len(rows)})")
        self.noEmployeesLabel.setVisible(not rows)
        self.employeesTable.setVisible(bool(rows))

        t = self.employeesTable
        t.clearContents()
        t.setRowCount(len(rows))
        for row, r in enumerate(rows):
            for col, text in enumerate(r["values"]):
                item = QTableWidgetItem(text or "—")
                item.setToolTip(text or "")
                t.setItem(row, col, item)
        self._rows_count = len(rows)
        self._fit_table_height()

    # ==================== ПУТЬ ОТДЕЛА ====================

    @staticmethod
    def _node_label(node: dict[str, Any]) -> str:
        return (org_label(node["raw"]) or node["name"]) if node["kind"] == "org" else node["name"]

    def _path_of(self, key: str) -> str:
        """«МАЗ / НТЦ / Телематика» — от организации до узла"""
        parts = []
        while key and key in self._nodes:
            node = self._nodes[key]
            parts.append(self._node_label(node))
            key = node["parent"]
        return PATH_SEP.join(reversed(parts))

    def _row_path(self, pos: dict[str, Any], node: dict[str, Any]) -> str:
        """Путь отдела для строки сотрудника (по должности pos)"""
        dep_id = pos.get("department_id")
        if dep_id is not None and f"d:{dep_id}" in self._nodes:
            return self._path_of(f"d:{dep_id}")
        return PATH_SEP.join(p for p in (self._path_of(f"o:{node['org_id']}"), pos.get("department")) if p)

    # ==================== КОНТЕКСТНЫЕ МЕНЮ И «+» ====================

    def _tree_menu_items(self, pos):
        """ПКМ по узлу дерева"""
        item = self.treeWidget.itemAt(pos)
        key = item.data(0, ID_ROLE) if item else ""
        node = self._nodes.get(key)
        if not node:
            return None
        self.treeWidget.setCurrentItem(item)
        if node["kind"] == "org":
            return [
                ("Добавить отдел", lambda: self.on_add_node(key)),
                ("Добавить сотрудника", self.system_actions.add_employee),
            ]
        return [
            ("Редактировать", lambda: self.on_edit_node(key)),
            ("Добавить подотдел", lambda: self.on_add_node(key)),
            SEPARATOR,
            ("Удалить", lambda: self.on_delete_node(key)),
        ]

    def _emp_menu_items(self, pos):
        """ПКМ по строке таблицы сотрудников"""
        row = self.employeesTable.rowAt(pos.y())
        if not 0 <= row < len(self._detail_rows):
            return None
        emp = self._detail_rows[row]["emp"]
        return [
            ("Редактировать", lambda: self.system_actions.edit_employee(emp)),
            SEPARATOR,
            ("Удалить", lambda: self.system_actions.delete_employee(emp)),
        ]

    def _edit_detail_row(self, row: int):
        if 0 <= row < len(self._detail_rows):
            self.system_actions.edit_employee(self._detail_rows[row]["emp"])

    def _show_add_menu(self, *_):
        """Плавающая «+»: сотрудник, отдел, тип отдела, организация"""
        show_menu_above(
            self.floating_btn,
            [
                ("Сотрудник", self.system_actions.add_employee),
                ("Отдел", lambda: self.on_add_node(self._current_key())),
                ("Тип отдела", self.system_actions.add_department_type),
                ("Организация", self.system_actions.add_organization),
            ],
        )

    def _on_action_message(self, kind: str, text: str):
        {"success": self.show_success_notification, "error": self.show_error_notification}.get(
            kind, self.show_info_notification
        )(text)

    def _on_changed(self):
        """Отдел / тип / организация / сотрудник изменены — перезагружаем структуру, сохраняя выбранный узел"""
        node = self._nodes.get(self._current_key())
        keep = node["key"] if node else ""
        org_key = f"o:{node['org_id']}" if node else ""
        self.load_data(notify=False)
        if org_key:  # после перезагрузки подразделения снова нужно подгрузить и вернуть выбор
            self._ensure_structure(org_key)
            if org_key in self._items:
                self._items[org_key].setExpanded(True)
            if keep in self._items:
                self.treeWidget.setCurrentItem(self._items[keep])
        self.structure_changed.emit()

    def reload_employees(self):
        """Сотрудников изменили на другой вкладке — обновляем кэш и панель справа"""
        self._employees_cache.clear()
        self._show_detail(self._current_key())

    # ==================== РАБОТА С ОТДЕЛАМИ (CRUD) ====================

    def on_add_node(self, parent_key: str):
        """Добавить отдел: внутрь выбранного отдела / организации (или без привязки, если ничего не выбрано)"""
        node = self._nodes.get(parent_key) or self._nodes.get(self._current_key())
        if not node:
            self.system_actions.add_department()
            return
        self.system_actions.add_department(node["org_id"], node["id"] if node["kind"] == "dep" else None)

    def on_edit_node(self, key: str):
        node = self._nodes.get(key)
        if not node or node["kind"] != "dep":
            return
        data = dict(node["raw"])
        parent = self._nodes.get(node["parent"])
        data["organization_id"] = node["org_id"]
        data["parent_id"] = parent["id"] if parent and parent["kind"] == "dep" else None
        self.system_actions.edit_department(data)

    def on_delete_node(self, key: str):
        node = self._nodes.get(key)
        if node and node["kind"] == "dep":
            self.system_actions.delete_department(node["id"], node["name"])

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def position_floating_button(self):
        if hasattr(self, "floating_btn"):
            margin = 20
            x = self.width() - self.floating_btn.width() - margin
            y = self.height() - self.floating_btn.height() - margin
            self.floating_btn.update_base_position(x, y)
            self.floating_btn.raise_()

    def on_scroll(self, value):
        if hasattr(self, "floating_btn"):
            self.floating_btn.hide_with_animation()
            self.floating_btn.start_hide_timer()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_floating_button()

        if hasattr(self, "notification_manager"):
            self.notification_manager.container.setGeometry(0, 0, self.width(), self.height())


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = QWidget()
    window.setWindowTitle("Тест - Структура")
    window.setGeometry(100, 100, 1200, 700)

    structure_page = StructurePage()

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(structure_page)

    window.show()
    sys.exit(app.exec())
