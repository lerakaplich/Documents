import os
from typing import Any

from PyQt6.QtCore import QObject, QRunnable, Qt, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QDialog, QLayout, QPushButton, QSizePolicy, QTreeWidgetItem

from client.core.org_structure.employee_selection_data_loader import (
    EmployeeSelectionDataLoader,
)
from client.core.org_structure.hierarchy_builder import HierarchyBuilder
from client.core.org_structure.selection_manager import SelectionManager
from client.core.org_structure.tree_builder import TreeBuilder
from client.core.themes import apply_theme_to_widget
from client.windows.documents.table.create.employee_selection import EmployeeSelection

ORG, DEPT, EMP = 1, 2, 3

MODE_RECEIVERS = "receivers"  # организации / отделы / сотрудники, организация — «целиком»
MODE_EMPLOYEES = "employees"  # отправитель / исполнители: только сотрудники


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


class EmployeeSelectionDialog(QDialog):
    """
    Диалог выбора получателей / исполнителей / отправителя (ленивый).

    - при открытии грузится ТОЛЬКО список организаций;
    - структура и сотрудники организации подгружаются при её раскрытии
      (или при установке галочки на организации) в фоне;
    - уже выбранные узлы (preselected_ids) определяют, какие организации
      нужно сразу подгрузить и раскрыть;
    - поиск — по кнопке «Поиск» (или Enter).

    selection_confirmed отдаёт список пар [type, id]: 1 — организация,
    2 — отдел, 3 — сотрудник.
    В режиме receivers результат «схлопывается»: у выбранной организации/отдела
    потомки не перечисляются.

    Если http_client нет, работает по переданным спискам (как раньше).
    """

    selection_confirmed = pyqtSignal(list)

    def __init__(
        self,
        organizations: list[dict[str, Any]] | None = None,
        departments: list[dict[str, Any]] | None = None,
        employees: list[dict[str, Any]] | None = None,
        preselected_ids: list | None = None,
        parent=None,
        title: str = "Выбор получателей",
        instruction: str = "Выберите организации, отделы или сотрудников:",
        http_client=None,
        mode: str = MODE_RECEIVERS,
    ):
        super().__init__(parent)

        self._updating = False
        self._closing = False
        self._search_mode = False
        self._last_query = ""
        self.mode = mode
        self.http_client = http_client or self._resolve_http_client()
        self._lazy = self.http_client is not None

        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(6)
        self._tasks: dict[Any, _LoadTask] = {}
        self._loading_orgs: set[int] = set()
        self._expand_orgs: set[int] = set()
        self._org_items: dict[int, QTreeWidgetItem] = {}

        self.loader = EmployeeSelectionDataLoader(self.http_client) if self._lazy else None

        self._init_data(organizations or [], departments or [], employees or [], preselected_ids)
        self._init_ui(title, instruction)
        self._populate_tree()
        self._connect_signals()
        self._update_selection_info()
        self._start_preload()

    @staticmethod
    def _resolve_http_client():
        try:
            from client.core.state.app_state import AppState

            return AppState().http_client
        except Exception:
            return None

    # ───────────────────────── данные ─────────────────────────

    def _init_data(self, organizations, departments, employees, preselected_ids):
        if self._lazy:
            orgs = []
            try:
                orgs = self.loader.load_organizations()
            except Exception as e:
                print(f"[EmployeeSelectionDialog] Ошибка загрузки организаций: {e}")
            # ВАЖНО: переданные organizations могут быть неполными (только выбранные ранее),
            # поэтому используются лишь как запасной вариант.
            orgs = orgs or organizations
            self.builder = HierarchyBuilder(orgs)
        else:
            self.builder = HierarchyBuilder(organizations, departments, employees)

        # «известные» узлы из переданных списков: помогают найти организацию выбранного узла
        self._seed_org_of: dict[tuple[int, int], int] = {}
        for d in departments:
            if d.get("id") is not None and d.get("organization_id") is not None:
                self._seed_org_of[(DEPT, d["id"])] = d["organization_id"]
        for e in employees:
            if e.get("id") is None:
                continue
            org_id = e.get("organization_id")
            if org_id is None:
                for pos in e.get("positions") or []:
                    org_id = pos.get("organization_id")
                    if org_id is None and pos.get("department_id") is not None:
                        org_id = self._seed_org_of.get((DEPT, pos["department_id"]))
                    if org_id is not None:
                        break
            if org_id is not None:
                self._seed_org_of[(EMP, e["id"])] = org_id

        self.selection_manager = SelectionManager(
            self.builder.organizations,
            self.builder.departments,
            self.builder.employees,
        )
        self.tree_builder = TreeBuilder(
            self.builder,
            self.selection_manager,
            allow_org_select=(self.mode == MODE_RECEIVERS),
        )

        # выбранные ранее: пары (type, id); пока узел не загружен — лежат в _pending
        self._pending: set[tuple[int, int]] = set(self._normalize_preselected(preselected_ids))
        self._resolve_pending()

    def _normalize_preselected(self, items) -> list[tuple[int, int]]:
        result = []
        for it in items or []:
            if isinstance(it, (list, tuple)) and len(it) == 2:
                result.append((int(it[0]), int(it[1])))
            elif isinstance(it, int):  # старый формат — голые id
                if it in self.builder.organizations and (self.mode == MODE_RECEIVERS):
                    result.append((ORG, it))
                elif (DEPT, it) in self._seed_org_of:
                    result.append((DEPT, it))
                elif (EMP, it) in self._seed_org_of:
                    result.append((EMP, it))
                elif it in self.builder.organizations:
                    result.append((ORG, it))
        return result

    def _resolve_pending(self):
        """Переносит в менеджер выбора те pending-узлы, которые уже загружены."""
        for pair in list(self._pending):
            if self.selection_manager.is_known(*pair):
                self.selection_manager.add(pair[1], pair[0])
                self._pending.discard(pair)

    def _start_preload(self):
        """Подгружает организации, в которых есть выбранные ранее узлы."""
        if not self._lazy:
            return
        for t, i in list(self._pending):
            org_id = i if t == ORG else self._seed_org_of.get((t, i))
            if org_id is not None and org_id in self.builder.organizations:
                self._expand_orgs.add(org_id)
                if t != ORG:
                    self._start_load(org_id)
        # выбранная организация сама по себе грузить не нужно; её потомки подгрузятся при раскрытии

    # ───────────────────────── загрузка в фоне ─────────────────────────

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
            if not self._search_mode:
                self._fill_org(org_id)
            self._update_selection_info()

        elif kind == "search":
            if key[1] != self._last_query:
                return  # устаревший запрос
            for org_id, data in result.items():
                self.builder.add_org_data(org_id, data["departments"], data["employees"])
                self._loading_orgs.discard(org_id)
            self._resolve_pending()
            self._show_search_results(key[1])

    def _on_task_failed(self, key, message):
        self._tasks.pop(key, None)
        if self._closing:
            return
        print(f"[EmployeeSelectionDialog] Ошибка загрузки {key}: {message}")
        if key[0] == "org":
            org_id = key[1]
            self._loading_orgs.discard(org_id)
            item = self._org_items.get(org_id)
            if item is not None:
                self.tree_builder.set_placeholder_text(item, "Не удалось загрузить — сверните и раскройте снова")
        elif key[0] == "search":
            self._set_search_busy(False)

    # ───────────────────────── UI ─────────────────────────

    def _init_ui(self, title: str, instruction: str):
        ui_path = EmployeeSelection.get_ui_path()
        EmployeeSelection.load_ui(self, ui_path)
        apply_theme_to_widget(self)

        if hasattr(self, "titleLabel"):
            self.titleLabel.setText(title)
        if hasattr(self, "instructionLabel"):
            self.instructionLabel.setText(instruction)

        if hasattr(self, "treeWidget"):
            self.treeWidget.setHeaderLabel("Структура организации")
            self.treeWidget.setIndentation(20)
            self.treeWidget.setItemsExpandable(True)

        self._ensure_search_button()

        base_dir = self._get_root_dir()
        EmployeeSelection.apply_checkbox_styles(self, base_dir)

    def _ensure_search_button(self):
        """
        Кнопка поиска: берём из .ui (btnSearch или searchButton); если её нет —
        добавляем рядом с searchEdit.
        """
        for name in ("btnSearch", "searchButton"):
            btn = getattr(self, name, None)
            if btn is not None:
                self.searchButton = btn
                break
        else:
            if not hasattr(self, "searchEdit"):
                return
            self.searchButton = QPushButton("Поиск", self)
            layout, index = self._find_layout_of(self.layout(), self.searchEdit)
            if layout is not None and hasattr(layout, "insertWidget"):
                layout.insertWidget(index + 1, self.searchButton)
            elif layout is not None:
                layout.addWidget(self.searchButton)

        self._search_button_text = self.searchButton.text() or "Поиск"

        # Высота кнопки = высоте строки поиска (работает и без правок в .ui):
        # снимаем фиксированную высоту и даём кнопке растягиваться по строке layout'а.
        self.searchButton.setMinimumHeight(0)
        self.searchButton.setMaximumHeight(16777215)
        policy = self.searchButton.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        self.searchButton.setSizePolicy(policy)
        self.searchButton.setToolTip("Найти (поиск выполняется по нажатию кнопки или Enter)")
        # Enter в поле поиска не должен «нажимать» кнопку подтверждения и закрывать диалог
        for name in ("searchButton", "selectButton", "cancelButton"):
            btn = getattr(self, name, None)
            if btn is not None:
                btn.setAutoDefault(False)
                btn.setDefault(False)

    def _find_layout_of(self, layout: QLayout | None, widget):
        if layout is None:
            return None, -1
        idx = layout.indexOf(widget)
        if idx >= 0:
            return layout, idx
        for i in range(layout.count()):
            sub = layout.itemAt(i).layout()
            if sub is not None:
                found, found_idx = self._find_layout_of(sub, widget)
                if found is not None:
                    return found, found_idx
        return None, -1

    def reapply_theme(self):
        apply_theme_to_widget(self)
        base_dir = self._get_root_dir()
        EmployeeSelection.apply_checkbox_styles(self, base_dir)

    def _get_root_dir(self) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = base_dir
        for _ in range(4):
            root_dir = os.path.dirname(root_dir)
        return root_dir

    def _connect_signals(self):
        if hasattr(self, "searchEdit"):
            self.searchEdit.returnPressed.connect(self._on_search)
            self.searchEdit.textChanged.connect(self._on_search_text_changed)
        if hasattr(self, "searchButton"):
            self.searchButton.clicked.connect(self._on_search)
        if hasattr(self, "treeWidget"):
            self.treeWidget.itemChanged.connect(self._on_tree_item_changed)
            self.treeWidget.itemExpanded.connect(self._on_item_expanded)
        if hasattr(self, "selectButton"):
            self.selectButton.clicked.connect(self._on_select)
        if hasattr(self, "cancelButton"):
            self.cancelButton.clicked.connect(self.reject)

    def done(self, result):
        self._closing = True
        self._pool.clear()
        super().done(result)

    # ───────────────────────── дерево ─────────────────────────

    def _populate_tree(self):
        """Ленивое дерево: все организации, содержимое — у загруженных."""
        if not hasattr(self, "treeWidget"):
            return
        self._search_mode = False
        self.treeWidget.blockSignals(True)
        self._updating = True
        try:
            self.treeWidget.clear()
            self._org_items.clear()
            for item in self.tree_builder.build_org_items():
                self.treeWidget.addTopLevelItem(item)
                org_id = item.data(0, Qt.ItemDataRole.UserRole)["id"]
                self._org_items[org_id] = item
                if self.builder.is_loaded(org_id):
                    self._after_fill(item, org_id)
        finally:
            self._updating = False
            self.treeWidget.blockSignals(False)

    def _fill_org(self, org_id: int):
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
            if self.selection_manager.is_selected(node_id, node_type) and self.mode == MODE_RECEIVERS:
                self._select_descendants(node_type, node_id, True)
                return
        for i in range(item.childCount()):
            self._cascade_selected(item.child(i))

    def _on_item_expanded(self, item: QTreeWidgetItem):
        if self._search_mode:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        if data.get("type") == ORG and not self.builder.is_loaded(data["id"]):
            self.tree_builder.set_placeholder_text(item, "Загрузка…")
            self._start_load(data["id"])

    # ───────────────────────── чекбоксы ─────────────────────────

    def _select_descendants(self, node_type: int, node_id: int, checked: bool):
        depts, emps = self.builder.descendants(node_type, node_id)
        for d in depts:
            self.selection_manager.toggle(d, checked, DEPT)
        for e in emps:
            self.selection_manager.toggle(e, checked, EMP)

    def _sync_item_states(self, item: QTreeWidgetItem):
        """Выставляет галочки в поддереве по состоянию менеджера выбора."""
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        node_type, node_id = data.get("type"), data.get("id")
        if (
            node_type in (ORG, DEPT, EMP)
            and node_id is not None
            and node_id > 0
            and item.flags() & Qt.ItemFlag.ItemIsUserCheckable
        ):
            state = (
                Qt.CheckState.Checked
                if self.selection_manager.is_selected(node_id, node_type)
                else Qt.CheckState.Unchecked
            )
            if item.checkState(0) != state:
                item.setCheckState(0, state)
        for i in range(item.childCount()):
            self._sync_item_states(item.child(i))

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
                    self.selection_manager.toggle(data["id"], all_checked, data["type"])
            parent = parent.parent()

    # ───────────────────────── поиск ─────────────────────────

    def _on_search_text_changed(self, text: str):
        if not text.strip() and self._search_mode:
            self._last_query = ""
            self._set_search_busy(False)
            self._populate_tree()

    def _set_search_busy(self, busy: bool):
        if hasattr(self, "searchButton"):
            self.searchButton.setEnabled(not busy)
            self.searchButton.setText("Поиск…" if busy else getattr(self, "_search_button_text", "Поиск"))

    def _on_search(self, *_):
        if not hasattr(self, "searchEdit"):
            return
        query = self.searchEdit.text().strip()
        if not query:
            self._last_query = ""
            if self._search_mode:
                self._populate_tree()
            return

        self._last_query = query
        if not self._lazy:
            self._show_search_results(query)
            return

        # грузим организации, которых ещё нет (остальные берутся из кэша загрузчика)
        self._set_search_busy(True)
        loader = self.loader
        org_ids = list(self.builder.organizations)
        self._tasks.pop(("search", query), None)
        self._start_task(("search", query), lambda: loader.load_all_orgs_data(org_ids))

    def _show_search_results(self, query: str):
        self._set_search_busy(False)
        self._search_mode = True
        self.treeWidget.blockSignals(True)
        self._updating = True
        try:
            self.treeWidget.clear()
            self._org_items.clear()
            items = self.tree_builder.build_search_items(query)
            if not items:
                empty = QTreeWidgetItem(["Ничего не найдено"])
                empty.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.treeWidget.addTopLevelItem(empty)
            for item in items:
                self.treeWidget.addTopLevelItem(item)
        finally:
            self._updating = False
            self.treeWidget.blockSignals(False)

    # ───────────────────────── итог ─────────────────────────

    def _all_selected(self) -> set[tuple[int, int]]:
        return set(self.selection_manager.get_selected_items()) | self._pending

    def _result_pairs(self) -> list[tuple[int, int]]:
        selected = self._all_selected()
        if self.mode == MODE_EMPLOYEES:
            return sorted(p for p in selected if p[0] == EMP)

        # receivers: у выбранной организации/отдела потомков не перечисляем
        drop: set[tuple[int, int]] = set()
        for t, i in selected:
            if t in (ORG, DEPT) and self.selection_manager.is_known(t, i):
                depts, emps = self.builder.descendants(t, i)
                drop |= {(DEPT, d) for d in depts}
                drop |= {(EMP, e) for e in emps}
        return sorted(p for p in selected if p not in drop)

    def _update_selection_info(self):
        if not hasattr(self, "selectionInfoLabel"):
            return
        selected = self._all_selected()
        org_count = sum(1 for t, _ in selected if t == ORG)
        dept_count = sum(1 for t, _ in selected if t == DEPT)
        emp_count = sum(1 for t, _ in selected if t == EMP)

        total = len(selected)
        if total == 0:
            self.selectionInfoLabel.setText("Выбрано: 0 элементов")
            return
        parts = [f"Выбрано: {total} элементов"]
        if org_count:
            parts.append(f"организаций: {org_count}")
        if dept_count:
            parts.append(f"отделов: {dept_count}")
        if emp_count:
            parts.append(f"сотрудников: {emp_count}")
        self.selectionInfoLabel.setText(" (".join(parts) + ")")

    def _on_select(self):
        self.selection_confirmed.emit([list(p) for p in self._result_pairs()])
        self.accept()

    # ───────────────────────── public ─────────────────────────

    def get_selected_pairs(self) -> list[tuple[int, int]]:
        return self._result_pairs()

    def get_selected_ids(self) -> list[int]:
        return [i for _, i in self._result_pairs()]

    def get_selected_organizations(self) -> list[dict]:
        return self.selection_manager.get_selected_organizations()

    def get_selected_departments(self) -> list[dict]:
        return self.selection_manager.get_selected_departments()

    def get_selected_employees(self) -> list[dict]:
        return self.selection_manager.get_selected_employees()