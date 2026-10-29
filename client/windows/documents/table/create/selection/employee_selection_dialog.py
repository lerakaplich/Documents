"""Диалог выбора получателей / исполнителей / отправителя"""

import os
from typing import Any

from PyQt6.QtCore import QThreadPool, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QLayout,
    QPushButton,
    QSizePolicy,
    QTreeWidgetItem,
)

from client.core.org_structure.employee_selection_data_loader import EmployeeSelectionDataLoader
from client.core.org_structure.hierarchy_builder import HierarchyBuilder
from client.core.org_structure.search_hits import DEPT, EMP, ORG
from client.core.org_structure.selection_manager import SelectionManager
from client.core.org_structure.tree_builder import TreeBuilder
from client.core.themes import apply_theme_to_widget
from client.windows.documents.table.create.selection.background_loader import BackgroundLoadMixin, _LoadTask
from client.windows.documents.table.create.selection.constants import MODE_EMPLOYEES, MODE_RECEIVERS
from client.windows.documents.table.create.selection.employee_selection import EmployeeSelection
from client.windows.documents.table.create.selection.frequent_mixin import FrequentMixin
from client.windows.documents.table.create.selection.result_mixin import ResultMixin
from client.windows.documents.table.create.selection.search_mixin import SearchMixin
from client.windows.documents.table.create.selection.tree_mixin import TreeMixin

__all__ = ["EmployeeSelectionDialog", "MODE_RECEIVERS", "MODE_EMPLOYEES"]


class EmployeeSelectionDialog(
    BackgroundLoadMixin, TreeMixin, SearchMixin, FrequentMixin, ResultMixin, QDialog
):
    """
    Диалог выбора получателей / исполнителей / отправителя (ленивый).

    - при открытии грузится ТОЛЬКО список организаций;
    - структура и сотрудники организации подгружаются при её раскрытии
      (или при установке галочки на организации) в фоне;
    - уже выбранные узлы (preselected_ids) определяют, какие организации
      нужно сразу подгрузить и раскрыть;
    - поиск — по кнопке «Поиск» (или Enter): серверный GET /org/structure/search,
      затем подгружаются только организации, в которых что-то найдено;
    - в результатах поиска галочка на организации/отделе, показанных лишь как путь
      к найденному (МАЗ → НТЦ → Телематика → Иванов), выбирает только найденных.

    selection_confirmed отдаёт список пар [type, id]: 1 — организация,
    2 — отдел, 3 — сотрудник.
    В режиме receivers результат «схлопывается»: у выбранной организации/отдела
    потомки не перечисляются.

    Если http_client нет, работает по переданным спискам и локальному поиску (как раньше).
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
        allow_org_select: bool | None = None,
        frequent_role: str | None = None,
    ):
        super().__init__(parent)

        # «самые частые»: роль (sender / receiver / executor) или None — строка не показывается
        self._frequent_role = frequent_role
        self._frequent_tree = None
        self._frequent_items: dict[tuple[int, int], QTreeWidgetItem] = {}
        self._frequent_updating = False

        self._updating = False
        self._closing = False
        self._search_mode = False
        self._path_mode = False  # серверный поиск: работает логика «узлов-путей»
        self._search_matches: set[tuple[int, int]] = set()  # реально найденные узлы (type, id)
        self._last_query = ""
        self.mode = mode
        # можно ли отмечать организацию: по умолчанию — только в режиме receivers;
        # для режима employees (отправитель/исполнители) включается явно allow_org_select=True
        self.allow_org = (mode == MODE_RECEIVERS) if allow_org_select is None else allow_org_select
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
            allow_org_select=self.allow_org,
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

        self._build_frequent_strip()

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
        self._restyle_frequent()

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
