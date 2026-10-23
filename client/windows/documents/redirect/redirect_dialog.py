# client/windows/documents/redirect/redirect_dialog.py
"""
Диалог перенаправления документа (ленивая загрузка).

- при открытии грузится ТОЛЬКО список организаций (один запрос);
- при раскрытии (или установке галочки) организации в фоне грузятся её отделы и
  сотрудники (по одному запросу на организацию);
- поиск — по кнопке «Поиск» (или Enter): серверный GET /org/structure/search,
  затем подгружаются только организации, в которых что-то найдено;
- текущие делегаты (preselected) определяют, какие организации подгрузить сразу.

Сигнал: redirect_confirmed(list_of_employee_ids, comment_text)
"""

import os
from typing import Any

from PyQt6.QtCore import QObject, QRunnable, Qt, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QDialog, QMessageBox, QTreeWidgetItem

from client.core.org_structure.employee_selection_data_loader import (
    EmployeeSelectionDataLoader,
)
from client.core.org_structure.hierarchy_builder import HierarchyBuilder
from client.core.org_structure.search_hits import (  # noqa: F401
    DEPT,
    EMP,
    MIN_SEARCH_LEN,
    ORG,
    parse_search_hits,
)
from client.core.org_structure.selection_manager import SelectionManager
from client.core.org_structure.tree_builder import TreeBuilder
from client.core.themes import apply_theme_to_widget, get_manager
from client.core.themes.icon_utils import icon_path

# ───────────────────────── фоновые задачи ─────────────────────────


class _LoadSignals(QObject):
    done = pyqtSignal(object, object)  # key, result
    failed = pyqtSignal(object, str)  # key, message


class _LoadTask(QRunnable):
    """Выполняет fn() в потоке пула и возвращает результат сигналом (в GUI-поток)."""

    def __init__(self, key, fn):
        super().__init__()
        self.key = key
        self.fn = fn
        self.signals = _LoadSignals()
        self.setAutoDelete(False)  # жизнью задачи управляет диалог

    def run(self):
        try:
            result = self.fn()
        except Exception as e:  # noqa: BLE001
            self.signals.failed.emit(self.key, str(e))
            return
        self.signals.done.emit(self.key, result)


# ───────────────────────── диалог ─────────────────────────


class RedirectDialog(QDialog):
    """
    Диалог перенаправления документа.

    Args:
        current_recipients: список делегатов (dict с 'id' или строка с именем)
        all_employees:      опционально — список сотрудников (помогает найти организацию
                            делегата, чтобы подгрузить только её)
        parent:             родительское окно
        http_client:        HTTP-клиент (если не передан — берётся из AppState)
    """

    redirect_confirmed = pyqtSignal(list, str)

    def __init__(
        self,
        current_recipients: list,
        all_employees: list | None = None,
        parent=None,
        http_client=None,
    ):
        super().__init__(parent)

        self._updating = False
        self._closing = False
        self._search_mode = False
        self._search_matches: set[tuple[int, int]] = set()  # реально найденные узлы (type, id)
        self._last_query = ""
        self.http_client = http_client or self._resolve_http_client()
        self._lazy = self.http_client is not None

        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(6)
        self._tasks: dict[Any, _LoadTask] = {}
        self._loading_orgs: set[int] = set()
        self._expand_orgs: set[int] = set()
        self._org_items: dict[int, QTreeWidgetItem] = {}

        self.loader = EmployeeSelectionDataLoader(self.http_client) if self._lazy else None

        # ─── предзаполненные ID ───
        self.preselected_ids = self._extract_ids(current_recipients)

        self._init_data(current_recipients, all_employees or [])
        self._init_ui()
        self._populate_tree()
        self._connect_signals()
        self._update_selection_info()
        self._start_preload()

    # ─────────── Вспомогательные ───────────

    @staticmethod
    def _resolve_http_client():
        try:
            from client.core.state.app_state import AppState

            return AppState().http_client
        except Exception:
            return None

    @staticmethod
    def _extract_ids(current_recipients: list) -> list[int]:
        """Достаём ID из текущих делегатов (dict или строк)."""
        ids: list[int] = []
        for emp in current_recipients or []:
            if isinstance(emp, dict) and emp.get("id") is not None:
                ids.append(emp["id"])
        return ids

    @staticmethod
    def _org_of_employee(emp: dict) -> int | None:
        org_id = emp.get("organization_id")
        if org_id is None and isinstance(emp.get("organization"), dict):
            org_id = emp["organization"].get("id")
        if org_id is None:
            for pos in emp.get("positions") or []:
                if pos.get("organization_id") is not None:
                    return pos["organization_id"]
        return org_id

    # ─────────── Данные ───────────

    def _init_data(self, current_recipients: list, all_employees: list):
        orgs: list[dict] = []
        if self._lazy:
            print("[RedirectDialog] Загрузка списка организаций...")
            try:
                orgs = self.loader.load_organizations()
                print(f"[RedirectDialog] Организаций: {len(orgs)}")
            except Exception as e:
                print(f"[RedirectDialog] Ошибка загрузки организаций: {e}")
        else:
            print("[RedirectDialog] http_client не задан — данные не загружены")

        # Только организации: отделы и сотрудники придут лениво (add_org_data)
        self.builder = HierarchyBuilder(orgs)
        self.selection_manager = SelectionManager(
            self.builder.organizations,
            self.builder.departments,
            self.builder.employees,
        )
        self.tree_builder = TreeBuilder(self.builder, self.selection_manager)

        # Организация каждого делегата — чтобы подгрузить только её
        wanted = set(self.preselected_ids)
        self._seed_org_of: dict[int, int] = {}
        for emp in [*(e for e in current_recipients if isinstance(e, dict)), *all_employees]:
            emp_id = emp.get("id")
            if emp_id in wanted and emp_id not in self._seed_org_of:
                org_id = self._org_of_employee(emp)
                if org_id is not None:
                    self._seed_org_of[emp_id] = org_id

        # Текущие делегаты — всегда сотрудники (тип 3). Пока сотрудник не загружен,
        # он лежит в _pending и попадает в итог как есть.
        self._pending: set[tuple[int, int]] = {(EMP, i) for i in self.preselected_ids}
        self._resolve_pending()

    def _resolve_pending(self):
        """Переносит в менеджер выбора те pending-узлы, которые уже загружены."""
        for pair in list(self._pending):
            if self.selection_manager.is_known(*pair):
                self.selection_manager.add(pair[1], pair[0])
                self._pending.discard(pair)

    def _start_preload(self):
        """Подгружает организации, в которых есть текущие делегаты (и раскрывает их)."""
        if not self._lazy:
            return
        for _t, emp_id in list(self._pending):
            org_id = self._seed_org_of.get(emp_id)
            if org_id is not None and org_id in self.builder.organizations:
                self._expand_orgs.add(org_id)
                self._start_load(org_id)

    # ─────────── Загрузка в фоне ───────────

    def _start_task(self, key, fn):
        if key in self._tasks:
            return
        task = _LoadTask(key, fn)
        task.signals.done.connect(self._on_task_done)
        task.signals.failed.connect(self._on_task_failed)
        self._tasks[key] = task
        self._pool.start(task)

    def _start_load(self, org_id: int):
        if not self._lazy or self.builder.is_loaded(org_id) or org_id in self._loading_orgs:
            return
        self._loading_orgs.add(org_id)
        loader = self.loader
        self._start_task(("org", org_id), lambda: loader.load_org_data(org_id))

    def _on_task_done(self, key, result):
        self._tasks.pop(key, None)
        if self._closing:
            return
        kind = key[0]

        if kind == "org":
            org_id = key[1]
            self._loading_orgs.discard(org_id)
            self.builder.add_org_data(org_id, result["departments"], result["employees"])
            self._resolve_pending()
            self._fill_org(org_id)
            self._update_selection_info()

        elif kind == "search":
            if key[1] != self._last_query:
                return  # устаревший запрос
            hits, orgs_data = result
            for org_id, data in orgs_data.items():
                self.builder.add_org_data(org_id, data["departments"], data["employees"])
                self._loading_orgs.discard(org_id)
            self._resolve_pending()
            self._show_search_results(hits)
            self._update_selection_info()

    def _on_task_failed(self, key, message):
        self._tasks.pop(key, None)
        if self._closing:
            return
        print(f"[RedirectDialog] Ошибка загрузки {key}: {message}")
        if key[0] == "org":
            org_id = key[1]
            self._loading_orgs.discard(org_id)
            item = self._org_items.get(org_id)
            if item is not None:
                self.tree_builder.set_placeholder_text(item, "Не удалось загрузить — сверните и раскройте снова")
        elif key[0] == "search" and key[1] == self._last_query:
            self._set_search_busy(False)
            QMessageBox.warning(self, "Поиск", f"Не удалось выполнить поиск:\n{message}")

    # ─────────── UI ───────────

    def _load_ui(self):
        """Путь к .ui."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # поднимаемся до client/
        # client/windows/documents/redirect/ → client/
        client_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        return os.path.join(client_dir, "ui", "documents", "redirect_dialog.ui")

    def _init_ui(self):
        from PyQt6.uic import loadUi

        ui_path = self._load_ui()
        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI файл не найден: {ui_path}")

        loadUi(ui_path, self)
        apply_theme_to_widget(self)

        # Заголовок
        if hasattr(self, "titleLabel"):
            self.titleLabel.setText("Перенаправление документа")

        # Настройка дерева
        if hasattr(self, "treeWidget"):
            self.treeWidget.setHeaderLabel("Структура организации")
            self.treeWidget.setIndentation(20)
            self.treeWidget.setItemsExpandable(True)

        if hasattr(self, "btnSearch"):
            self._search_button_text = self.btnSearch.text() or "Поиск"
            self.btnSearch.setToolTip("Найти (поиск выполняется по нажатию кнопки или Enter)")
        # Enter в поле поиска не должен «нажимать» кнопку отправки и закрывать диалог
        for name in ("btnSearch", "sendButton"):
            btn = getattr(self, name, None)
            if btn is not None:
                btn.setAutoDefault(False)
                btn.setDefault(False)

        # Чекбоксы из темы
        self._apply_checkbox_styles()

    def _apply_checkbox_styles(self):
        if not hasattr(self, "treeWidget"):
            return
        _t = get_manager().current
        checked = icon_path("cb_checked", _t.ICON_COLOR)
        unchecked = icon_path("cb_unchecked", _t.ICON_COLOR)
        partial = icon_path("cb_partial", _t.ICON_COLOR)

        cb_style = f"""
            QTreeWidget::indicator {{
                width: 18px; height: 18px;
            }}
            QTreeWidget::indicator:unchecked {{
                image: url({unchecked});
            }}
            QTreeWidget::indicator:checked {{
                image: url({checked});
            }}
            QTreeWidget::indicator:indeterminate {{
                image: url({partial});
            }}
        """
        current = self.treeWidget.styleSheet() or ""
        self.treeWidget.setStyleSheet(current + cb_style)

    def _connect_signals(self):
        if hasattr(self, "searchEdit"):
            self.searchEdit.returnPressed.connect(self._on_search)
            self.searchEdit.textChanged.connect(self._on_search_text_changed)
        if hasattr(self, "btnSearch"):
            self.btnSearch.clicked.connect(self._on_search)
        if hasattr(self, "treeWidget"):
            self.treeWidget.itemChanged.connect(self._on_tree_item_changed)
            self.treeWidget.itemExpanded.connect(self._on_item_expanded)
        if hasattr(self, "sendButton"):
            self.sendButton.clicked.connect(self._on_send)

    def done(self, result):
        self._closing = True
        self._pool.clear()
        super().done(result)

    # ─────────── Дерево ───────────

    def _register_org_items(self, items: list[QTreeWidgetItem]):
        self._org_items.clear()
        for item in items:
            data = item.data(0, Qt.ItemDataRole.UserRole) or {}
            if data.get("type") == ORG:
                self._org_items[data["id"]] = item

    def _populate_tree(self):
        """Ленивое дерево: все организации, содержимое — у загруженных."""
        if not hasattr(self, "treeWidget"):
            return
        self._search_mode = False
        self.treeWidget.blockSignals(True)
        self._updating = True
        try:
            self.treeWidget.clear()
            items = self.tree_builder.build_org_items()
            self._register_org_items(items)
            for item in items:
                self.treeWidget.addTopLevelItem(item)
                org_id = item.data(0, Qt.ItemDataRole.UserRole)["id"]
                if self.builder.is_loaded(org_id):
                    self._after_fill(item, org_id)
        finally:
            self._updating = False
            self.treeWidget.blockSignals(False)

    def _fill_org(self, org_id: int):
        if self._search_mode and (ORG, org_id) not in self._search_matches:
            return  # в результатах поиска показываем только найденное, а не всю организацию
        item = self._org_items.get(org_id)
        if item is None:
            return
        self.treeWidget.blockSignals(True)
        self._updating = True
        try:
            self.tree_builder.fill_org_item(item, org_id)
            self._after_fill(item, org_id)
        finally:
            self._updating = False
            self.treeWidget.blockSignals(False)

    def _after_fill(self, org_item: QTreeWidgetItem, org_id: int):
        """Раскрыть путь к ранее выбранным, затем доразвернуть выбор «целиком» на потомков."""
        expanded = self._expand_selected(org_item)
        if org_id in self._expand_orgs and (expanded or org_item.childCount()):
            org_item.setExpanded(True)
        self._cascade_selected(org_item)
        self._sync_item_states(org_item)

    def _expand_selected(self, item: QTreeWidgetItem) -> bool:
        found = False
        for i in range(item.childCount()):
            child = item.child(i)
            checked = bool(child.flags() & Qt.ItemFlag.ItemIsUserCheckable) and (
                child.checkState(0) == Qt.CheckState.Checked
            )
            if self._expand_selected(child) or checked:
                found = True
        if found:
            item.setExpanded(True)
        return found

    def _cascade_selected(self, item: QTreeWidgetItem):
        """Если организация/отдел выбраны «целиком» — выбрать и всех загруженных потомков."""
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        node_type, node_id = data.get("type"), data.get("id")
        if node_type in (ORG, DEPT) and node_id is not None and node_id > 0:
            if self.selection_manager.is_selected(node_id, node_type):
                self._select_descendants(node_type, node_id, True)
                return
        for i in range(item.childCount()):
            self._cascade_selected(item.child(i))

    def _on_item_expanded(self, item: QTreeWidgetItem):
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        if self._search_mode and (data.get("type"), data.get("id")) not in self._search_matches:
            return
        if data.get("type") == ORG and not self.builder.is_loaded(data["id"]):
            self.tree_builder.set_placeholder_text(item, "Загрузка…")
            self._start_load(data["id"])

    # ─────────── Чекбоксы ───────────

    def _select_descendants(self, node_type: int, node_id: int, checked: bool):
        depts, emps = self.builder.descendants(node_type, node_id)
        for d in depts:
            self.selection_manager.toggle(d, checked, DEPT)
        for e in emps:
            self.selection_manager.toggle(e, checked, EMP)

    def _is_path_node(self, node_type, node_id) -> bool:
        """
        Узел-«путь» в результатах поиска: организация/отдел, которые сами НЕ найдены,
        а лишь показаны как предки найденного (МАЗ → НТЦ → Телематика → Иванов).
        Галочка на таком узле выбирает только найденных под ним, но не всю организацию.
        """
        return self._search_mode and node_type in (ORG, DEPT) and (node_type, node_id) not in self._search_matches

    def _sync_item_states(self, item: QTreeWidgetItem):
        """Выставляет галочки в поддереве по состоянию менеджера выбора."""
        for i in range(item.childCount()):
            self._sync_item_states(item.child(i))

        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        node_type, node_id = data.get("type"), data.get("id")
        if (
            node_type in (ORG, DEPT, EMP)
            and node_id is not None
            and node_id > 0
            and item.flags() & Qt.ItemFlag.ItemIsUserCheckable
        ):
            if self._is_path_node(node_type, node_id):
                # предок в поиске: отмечен, если отмечены все найденные под ним
                kids = self._checkable_children(item)
                checked = bool(kids) and all(k.checkState(0) == Qt.CheckState.Checked for k in kids)
            else:
                checked = self.selection_manager.is_selected(node_id, node_type)
            state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            if item.checkState(0) != state:
                item.setCheckState(0, state)

    def _apply_to_visible(self, item: QTreeWidgetItem, checked: bool):
        """Режим поиска: переключает только узлы, видимые под item (то есть найденные)."""
        for i in range(item.childCount()):
            child = item.child(i)
            if not (child.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                self._apply_to_visible(child, checked)  # группа «Сотрудники»
                continue
            data = child.data(0, Qt.ItemDataRole.UserRole) or {}
            cid, ctype = data.get("id"), data.get("type")
            if cid is None or cid < 0 or ctype not in (ORG, DEPT, EMP):
                continue
            if self._is_path_node(ctype, cid):
                self._apply_to_visible(child, checked)
            else:
                self.selection_manager.toggle(cid, checked, ctype)
                if ctype == DEPT or (ctype == ORG and self.builder.is_loaded(cid)):
                    self._select_descendants(ctype, cid, checked)

    def _on_tree_item_changed(self, item, column):
        if self._updating:
            return
        if not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        node_id, node_type = data.get("id"), data.get("type")
        if node_id is None or node_id < 0 or node_type not in (ORG, DEPT, EMP):
            return

        is_checked = item.checkState(column) == Qt.CheckState.Checked

        print(
            f"[RedirectDialog] галочка: type={node_type} id={node_id} checked={is_checked} "
            f"search_mode={self._search_mode} path_node={self._is_path_node(node_type, node_id)} "
            f"matches={sorted(self._search_matches)}"
        )

        # Поиск: галочка на МАЗ/НТЦ/Телематике выбирает только найденных (Иванова), не всю организацию
        if self._is_path_node(node_type, node_id):
            self._updating = True
            try:
                self._apply_to_visible(item, is_checked)
                self._sync_item_states(item)
                self._update_parents(item)
                self._update_selection_info()
            finally:
                self._updating = False
            return

        self._updating = True
        try:
            self.selection_manager.toggle(node_id, is_checked, node_type)

            if node_type == ORG:
                if self.builder.is_loaded(node_id):
                    self._select_descendants(ORG, node_id, is_checked)
                elif is_checked:
                    # структуры ещё нет — грузим; по готовности _after_fill отметит всех потомков
                    self._expand_orgs.add(node_id)
                    self._start_load(node_id)
            elif node_type == DEPT:
                self._select_descendants(DEPT, node_id, is_checked)

            self._sync_item_states(item)
            self._update_parents(item)
            self._update_selection_info()
        finally:
            self._updating = False

    def _checkable_children(self, item: QTreeWidgetItem) -> list[QTreeWidgetItem]:
        """Чекабельные потомки: отделы и сотрудники (сотрудники лежат внутри группы «Сотрудники»)."""
        result = []
        for i in range(item.childCount()):
            child = item.child(i)
            if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                result.append(child)
            else:
                data = child.data(0, Qt.ItemDataRole.UserRole) or {}
                if data.get("id") == -1:
                    for j in range(child.childCount()):
                        sub = child.child(j)
                        if sub.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                            result.append(sub)
        return result

    def _update_parents(self, item: QTreeWidgetItem):
        """Родитель отмечен, только если отмечены все его чекабельные потомки (и в менеджере тоже)."""
        parent = item.parent()
        while parent is not None:
            if parent.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                data = parent.data(0, Qt.ItemDataRole.UserRole) or {}
                kids = self._checkable_children(parent)
                if kids and data.get("id", -1) > 0:
                    all_checked = all(k.checkState(0) == Qt.CheckState.Checked for k in kids)
                    parent.setCheckState(0, Qt.CheckState.Checked if all_checked else Qt.CheckState.Unchecked)
                    # предков-«путь» в поиске в менеджер не пишем — иначе при отправке развернётся вся организация
                    if not self._is_path_node(data["type"], data["id"]):
                        self.selection_manager.toggle(data["id"], all_checked, data["type"])
            parent = parent.parent()

    # ─────────── Поиск (сервер) ───────────

    def _on_search_text_changed(self, text: str):
        if not text.strip() and self._search_mode:
            self._last_query = ""
            self._set_search_busy(False)
            self._populate_tree()

    def _set_search_busy(self, busy: bool):
        if hasattr(self, "btnSearch"):
            self.btnSearch.setEnabled(not busy)
            self.btnSearch.setText("Поиск…" if busy else getattr(self, "_search_button_text", "Поиск"))

    def _on_search(self, *_):
        if not hasattr(self, "searchEdit"):
            return
        query = self.searchEdit.text().strip()
        if not query:
            self._last_query = ""
            if self._search_mode:
                self._populate_tree()
            return
        if len(query) < MIN_SEARCH_LEN:
            QMessageBox.information(self, "Поиск", f"Введите минимум {MIN_SEARCH_LEN} символа для поиска.")
            return
        if not self._lazy:
            return

        self._last_query = query
        self._set_search_busy(True)

        from client.services.org_service import get_org_service

        service = get_org_service(self.http_client)
        loader = self.loader
        organizations = set(self.builder.organizations)

        def work():
            print(f"[RedirectDialog] Поиск: GET /org/structure/search?q={query!r}")
            raw = service.search_structure(query)
            print(f"[RedirectDialog] Поиск: сервер вернул {len(raw)} записей")
            hits = parse_search_hits(raw)
            by_type = {ORG: 0, DEPT: 0, EMP: 0}
            for t, _id, _org in hits:
                by_type[t] += 1
            print(
                f"[RedirectDialog] Поиск: разобрано {len(hits)} "
                f"(организаций: {by_type[ORG]}, отделов: {by_type[DEPT]}, сотрудников: {by_type[EMP]})"
            )

            # Организации, где найдены отделы/сотрудники: грузим только их (и только ещё не загруженные)
            wanted_orgs = {org for t, _id, org in hits if t != ORG and org is not None}
            unknown = sorted(o for o in wanted_orgs if o not in organizations)
            if unknown:
                print(f"[RedirectDialog] Поиск: организаций нет в списке (пропущены): {unknown}")
            need = sorted(o for o in wanted_orgs if o in organizations and not self.builder.is_loaded(o))
            already = len(wanted_orgs) - len(need) - len(unknown)
            print(f"[RedirectDialog] Поиск: нужно загрузить организаций: {len(need)} {need}, уже загружено: {already}")
            orgs_data = loader.load_all_orgs_data(need) if need else {}
            print(f"[RedirectDialog] Поиск: загружено организаций: {len(orgs_data)}")
            return hits, orgs_data

        self._tasks.pop(("search", query), None)
        self._start_task(("search", query), work)

    def _show_search_results(self, hits: list[tuple[int, int, int | None]]):
        self._set_search_busy(False)
        self._search_mode = True
        matches = {(t, i) for t, i, _org in hits}
        self._search_matches = matches

        # Найденные узлы, которых нет в загруженных данных, в дереве не появятся
        missing = [(t, i) for t, i in sorted(matches) if t != ORG and not self.selection_manager.is_known(t, i)]
        if missing:
            print(f"[RedirectDialog] Поиск: найдено, но нет в загруженных данных ({len(missing)}): {missing[:20]}")

        self.treeWidget.blockSignals(True)
        self._updating = True
        try:
            self.treeWidget.clear()
            items = self.tree_builder.build_match_items(matches)
            print(f"[RedirectDialog] Поиск: в дереве организаций: {len(items)}")
            self._register_org_items(items)
            if not items:
                empty = QTreeWidgetItem(["Ничего не найдено"])
                empty.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.treeWidget.addTopLevelItem(empty)
            for item in items:
                self.treeWidget.addTopLevelItem(item)
                self._sync_item_states(item)
        finally:
            self._updating = False
            self.treeWidget.blockSignals(False)

    # ─────────── Инфо-лейбл ───────────

    def _all_selected(self) -> set[tuple[int, int]]:
        return set(self.selection_manager.get_selected_items()) | self._pending

    def _update_selection_info(self):
        if not hasattr(self, "selectionInfoLabel"):
            return
        items = self._all_selected()

        org_c = sum(1 for t, _ in items if t == ORG)
        dept_c = sum(1 for t, _ in items if t == DEPT)
        emp_c = sum(1 for t, _ in items if t == EMP)

        total = len(items)
        if total == 0:
            self.selectionInfoLabel.setText("Выбрано: 0 элементов")
            return

        parts = [f"Выбрано: {total} элементов"]
        if org_c:
            parts.append(f"организаций: {org_c}")
        if dept_c:
            parts.append(f"отделов: {dept_c}")
        if emp_c:
            parts.append(f"сотрудников: {emp_c}")
        self.selectionInfoLabel.setText(" (".join(parts) + ")")

    # ─────────── Отправка ───────────

    def _ensure_org_loaded_sync(self, org_id: int):
        """Выбрана организация, данные которой ещё не пришли, — догружаем (редкий случай)."""
        if self.builder.is_loaded(org_id) or not self.loader:
            return
        try:
            data = self.loader.load_org_data(org_id)
            self.builder.add_org_data(org_id, data["departments"], data["employees"])
        except Exception as e:  # noqa: BLE001
            print(f"[RedirectDialog] Не удалось догрузить организацию {org_id}: {e}")

    def _selected_employee_ids(self) -> list[int]:
        """ID выбранных сотрудников (менеджер выбора + ещё не загруженные делегаты), без дублей."""
        ids = {i for t, i in self._all_selected() if t == EMP}
        return sorted(ids)

    def _on_send(self):
        """Собираем ID выбранных сотрудников (в т.ч. из выбранных отделов/организаций) и комментарий → сигнал."""
        selected = self._all_selected()
        print(
            f"[RedirectDialog] выбрано перед отправкой: орг={sorted(x for t, x in selected if t == ORG)}, "
            f"отделов={sum(1 for t, _ in selected if t == DEPT)}, "
            f"сотрудников={sorted(x for t, x in selected if t == EMP)}"
        )

        # Организации/отделы, выбранные «целиком», превращаем в конкретных сотрудников в менеджере выбора
        for t, node_id in sorted(selected):
            if t == ORG:
                self._ensure_org_loaded_sync(node_id)
            if t in (ORG, DEPT) and self.selection_manager.is_known(t, node_id):
                self._select_descendants(t, node_id, True)

        # Итог — только сотрудники (как get_selected_employees): всё, что выбрано, уже лежит в менеджере
        employee_ids = self._selected_employee_ids()

        if not employee_ids:
            QMessageBox.warning(self, "Внимание", "Не выбрано ни одного сотрудника для перенаправления.")
            return

        comment = ""
        if hasattr(self, "commentTextEdit"):
            comment = self.commentTextEdit.toPlainText().strip()

        print(f"[RedirectDialog] ID сотрудников: {employee_ids}, комментарий: {comment!r}")

        self.redirect_confirmed.emit(employee_ids, comment)
        self.accept()

    # ─────────── Тема ───────────

    def reapply_theme(self):
        apply_theme_to_widget(self)
        self._apply_checkbox_styles()