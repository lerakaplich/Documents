"""Дерево выбора: построение, ленивое заполнение, чекбоксы"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem

from client.core.org_structure.search_hits import DEPT, EMP, ORG
from client.windows.documents.table.create.selection.constants import MODE_RECEIVERS


class TreeMixin:
    """Работа с деревом организаций/отделов/сотрудников и чекбоксами."""

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
        self._path_mode = False
        self._search_matches = set()
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
            if self.selection_manager.is_selected(node_id, node_type) and (self.mode == MODE_RECEIVERS or self.allow_org):
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

    def _select_descendants(self, node_type: int, node_id: int, checked: bool):
        depts, emps = self.builder.descendants(node_type, node_id)
        for d in depts:
            self.selection_manager.toggle(d, checked, DEPT)
        for e in emps:
            self.selection_manager.toggle(e, checked, EMP)

    def _is_path_item(self, item: QTreeWidgetItem) -> bool:
        """
        Узел-«путь» в результатах серверного поиска: организация/отдел, которые сами НЕ найдены
        и не лежат внутри найденного, а лишь показаны как предки (МАЗ → НТЦ → Телематика → Иванов).
        Галочка на таком узле выбирает только найденных под ним, но не всю организацию.
        """
        if not self._path_mode:
            return False
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        if data.get("type") not in (ORG, DEPT) or (data.get("id") or -1) < 0:
            return False
        node = item
        while node is not None:
            d = node.data(0, Qt.ItemDataRole.UserRole) or {}
            if (d.get("type"), d.get("id")) in self._search_matches:
                return False
            node = node.parent()
        return True

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
            if self._is_path_item(item):
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
            if self._is_path_item(child):
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

        # Поиск: галочка на МАЗ/НТЦ/Телематике выбирает только найденных (Иванова), не всю организацию
        if self._is_path_item(item):
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
                    # предков-«путь» в поиске в менеджер не пишем — иначе выберется вся организация
                    if not self._is_path_item(parent):
                        self.selection_manager.toggle(data["id"], all_checked, data["type"])
            parent = parent.parent()
