"""Блок «Самые частые» над деревом выбора"""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QGridLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from client.core.org_structure.search_hits import DEPT, EMP, ORG
from client.core.themes import apply_theme_to_widget
from client.windows.documents.table.create.selection.constants import (
    FREQUENT_LIMIT,
    FREQUENT_TITLES,
    KIND_BY_TYPE,
    MODE_EMPLOYEES,
    TYPE_BY_KIND,
)


class FrequentMixin:
    """
    Блок «Самые частые …» (топ-5) над основным деревом.
    Оформлен как такое же дерево с теми же чекбоксами и стилем, что и основное.
    """

    def _frequent_allowed_types(self) -> set[int]:
        if self.mode == MODE_EMPLOYEES:
            return {ORG, EMP} if self.allow_org else {EMP}
        return {ORG, DEPT, EMP}

    def _build_frequent_strip(self):
        if not self._frequent_role or not hasattr(self, "treeWidget"):
            return
        try:
            from client.core.frequent_manager import FrequentManager

            kinds = {KIND_BY_TYPE[t] for t in self._frequent_allowed_types()}
            top = [r for r in FrequentManager().top(self._frequent_role, FREQUENT_LIMIT, kinds) if r.get("name")]
        except Exception as e:  # noqa: BLE001
            print(f"[EmployeeSelectionDialog] Не удалось загрузить частые: {e}")
            return
        if not top:
            return

        tree = QTreeWidget(self)
        # то же имя, что у основного дерева: правила темы/.ui, заданные по имени, сработают и здесь
        tree.setObjectName(self.treeWidget.objectName() or "treeWidget")
        tree.setHeaderLabel(FREQUENT_TITLES.get(self._frequent_role, "Самые частые"))
        tree.setRootIsDecorated(False)
        tree.setUniformRowHeights(True)
        tree.setIndentation(0)
        tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        items: dict[tuple[int, int], QTreeWidgetItem] = {}
        for rec in top:
            node_type = TYPE_BY_KIND.get(rec.get("kind"))
            node_id = rec.get("id")
            if node_type is None or node_id is None:
                continue
            pair = (node_type, node_id)
            if node_type != ORG and rec.get("org_id") is not None:
                self._seed_org_of.setdefault(pair, rec["org_id"])  # какую организацию подгрузить

            name = rec["name"]
            suffix = {ORG: "организация", DEPT: "отдел"}.get(node_type)
            item = QTreeWidgetItem([f"{name}  ({suffix})" if suffix else name])
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(0, Qt.CheckState.Unchecked)
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": node_type, "id": node_id})
            item.setToolTip(0, f"{name}\nВыбирался: {rec.get('count', 0)}")
            tree.addTopLevelItem(item)
            items[pair] = item

        if not items:
            tree.deleteLater()
            return

        self._frequent_tree = tree
        self._frequent_items = items
        self._restyle_frequent()

        tree.itemChanged.connect(self._on_frequent_item_changed)

        if not self._insert_above_tree(tree):
            print("[EmployeeSelectionDialog] Не удалось вставить блок «частые» над деревом")
            tree.deleteLater()
            self._frequent_tree = None
            self._frequent_items = {}
            return

        # высоту считаем по реальным размерам строк/заголовка с учётом темы:
        # сразу и ещё раз, когда диалог уже показан и стили применены
        self._fit_frequent_height()
        QTimer.singleShot(0, self._fit_frequent_height)

    def _fit_frequent_height(self):
        tree = getattr(self, "_frequent_tree", None)
        if tree is None:
            return
        tree.ensurePolished()
        row_h = tree.sizeHintForRow(0)
        if row_h <= 0:
            return
        header = tree.header()
        header_h = max(header.height(), header.sizeHint().height())
        rows = tree.topLevelItemCount()
        # запас на рамку и внутренние отступы из темы
        tree.setFixedHeight(header_h + row_h * rows + 2 * tree.frameWidth())

    def _restyle_frequent(self):
        """Тот же стиль, что у основного дерева (чекбоксы с иконками темы и т.д.)."""
        tree = getattr(self, "_frequent_tree", None)
        if tree is None:
            return
        tree.setStyleSheet("")
        try:
            apply_theme_to_widget(tree)  # фон, цвет текста и т.д. из текущей темы
        except Exception as e:  # noqa: BLE001
            print(f"[EmployeeSelectionDialog] Не удалось применить тему к «частым»: {e}")
        if hasattr(self, "treeWidget"):
            # плюс то же, что у основного дерева (чекбоксы с иконками темы и т.д.)
            tree.setStyleSheet((tree.styleSheet() or "") + (self.treeWidget.styleSheet() or ""))

    def _find_tree_layout(self):
        """Layout, в котором лежит дерево: сначала layout родителя дерева (рамка/группа), потом диалога."""
        tree = self.treeWidget
        parent = tree.parentWidget()
        candidates = []
        if parent is not None and parent.layout() is not None:
            candidates.append(parent.layout())
        if self.layout() is not None:
            candidates.append(self.layout())
        for lay in candidates:
            found, idx = self._find_layout_of(lay, tree)
            if found is not None:
                return found, idx
        return None, -1

    def _insert_above_tree(self, widget: QWidget) -> bool:
        """Вставить widget прямо над деревом для любого вида layout (box / grid)."""
        layout, index = self._find_tree_layout()
        tree = self.treeWidget
        if layout is None:
            parent = tree.parentWidget()
            print(
                "[EmployeeSelectionDialog] layout дерева не найден; "
                f"родитель дерева: {type(parent).__name__}, layout диалога: {type(self.layout()).__name__}"
            )
            return False

        if hasattr(layout, "insertWidget"):  # QVBoxLayout / QHBoxLayout
            layout.insertWidget(index, widget)
            return True

        if isinstance(layout, QGridLayout):
            row, col, row_span, col_span = layout.getItemPosition(index)
            layout.removeWidget(tree)
            container = QWidget(self)
            v = QVBoxLayout(container)
            v.setContentsMargins(0, 0, 0, 0)
            v.addWidget(widget)
            v.addWidget(tree, 1)
            layout.addWidget(container, row, col, row_span, col_span)
            return True

        print(f"[EmployeeSelectionDialog] неподдерживаемый layout дерева: {type(layout).__name__}")
        return False

    def _refresh_frequent(self):
        """Отметить строки «частых» по текущему выбору (без повторных сигналов)."""
        tree = getattr(self, "_frequent_tree", None)
        if tree is None:
            return
        selected = self._all_selected()
        tree.blockSignals(True)
        try:
            for pair, item in self._frequent_items.items():
                state = Qt.CheckState.Checked if pair in selected else Qt.CheckState.Unchecked
                if item.checkState(0) != state:
                    item.setCheckState(0, state)
        finally:
            tree.blockSignals(False)

    def _sync_all_items(self, expand: bool = False):
        if not hasattr(self, "treeWidget"):
            return
        self.treeWidget.blockSignals(True)
        try:
            for k in range(self.treeWidget.topLevelItemCount()):
                top = self.treeWidget.topLevelItem(k)
                self._sync_item_states(top)
                if expand:
                    self._expand_selected(top)
        finally:
            self.treeWidget.blockSignals(False)

    def _on_frequent_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._closing:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        if data.get("type") is None or data.get("id") is None:
            return
        checked = item.checkState(column) == Qt.CheckState.Checked
        self._apply_frequent_choice((data["type"], data["id"]), checked)

    def _apply_frequent_choice(self, pair: tuple[int, int], checked: bool):
        """Выбрать/снять «частого» так же, как галочкой в дереве (с учётом ленивой загрузки)."""
        node_type, node_id = pair
        self._updating = True
        try:
            if self.selection_manager.is_known(node_type, node_id):
                self.selection_manager.toggle(node_id, checked, node_type)
                if node_type == ORG:
                    if self.builder.is_loaded(node_id):
                        self._select_descendants(ORG, node_id, checked)
                    elif checked:
                        self._expand_orgs.add(node_id)
                        self._start_load(node_id)
                elif node_type == DEPT:
                    self._select_descendants(DEPT, node_id, checked)
                self._sync_all_items(expand=checked)
            elif checked:
                # узел ещё не загружен: запоминаем и подгружаем его организацию
                self._pending.add(pair)
                org_id = self._seed_org_of.get(pair)
                if org_id is not None and org_id in self.builder.organizations:
                    self._expand_orgs.add(org_id)
                    self._start_load(org_id)
            else:
                self._pending.discard(pair)
        finally:
            self._updating = False
        self._update_selection_info()