class SelectionManager:
    """
    Менеджер выбранных элементов.

    Выбор хранится как набор пар (type, id):
        1 — организация, 2 — отдел, 3 — сотрудник.
    Словари organizations/departments/employees — те же объекты, что и у
    HierarchyBuilder: при ленивой подгрузке они пополняются, и новые узлы
    сразу становятся «известными» менеджеру.
    """

    TYPE_ORG = 1
    TYPE_DEPT = 2
    TYPE_EMP = 3

    def __init__(
        self,
        organizations: dict[int, dict],
        departments: dict[int, dict],
        employees: dict[int, dict],
    ):
        self.organizations = organizations
        self.departments = departments
        self.employees = employees
        self.selected_items: set[tuple[int, int]] = set()  # (type, id)

    # ── известность узла ──

    def is_known(self, node_type: int, node_id: int) -> bool:
        """Есть ли такой узел в справочниках (загружен ли он)."""
        if node_type == 1:
            return node_id in self.organizations
        if node_type == 2:
            return node_id in self.departments
        if node_type == 3:
            return node_id in self.employees
        return False

    # оставлено для обратной совместимости
    _is_valid_item = is_known

    def _get_node_type(self, node_id: int) -> int | None:
        """Определяет тип по ID (только для старого кода; при коллизиях id неоднозначно)."""
        if node_id in self.organizations:
            return 1
        if node_id in self.departments:
            return 2
        if node_id in self.employees:
            return 3
        return None

    # ── изменение выбора ──

    def set_selected(self, items: list[tuple[int, int]]):
        """Устанавливает выбранные элементы по списку (type, id); неизвестные пропускаются."""
        self.selected_items.clear()
        for type_id, node_id in items:
            if self.is_known(type_id, node_id):
                self.selected_items.add((type_id, node_id))

    def set_selected_by_ids(self, ids: list[int], node_type: int | None = None):
        self.selected_items.clear()
        for node_id in ids:
            t = node_type if node_type is not None else self._get_node_type(node_id)
            if t is not None and self.is_known(t, node_id):
                self.selected_items.add((t, node_id))

    def add(self, node_id: int, node_type: int | None = None):
        if node_type is None:
            node_type = self._get_node_type(node_id)
        if node_type is not None and self.is_known(node_type, node_id):
            self.selected_items.add((node_type, node_id))

    def remove(self, node_id: int, node_type: int | None = None):
        if node_type is None:
            node_type = self._get_node_type(node_id)
        if node_type is not None:
            self.selected_items.discard((node_type, node_id))

    def toggle(self, node_id: int, selected: bool, node_type: int | None = None):
        """Устанавливает состояние выбора узла. Неизвестные узлы игнорируются."""
        if node_type is None:
            node_type = self._get_node_type(node_id)
        if node_type is None or not self.is_known(node_type, node_id):
            return
        if selected:
            self.selected_items.add((node_type, node_id))
        else:
            self.selected_items.discard((node_type, node_id))

    # ── чтение ──

    def is_selected(self, node_id: int, node_type: int | None = None) -> bool:
        """Выбран ли узел. ВСЕГДА передавайте node_type — иначе при совпадении id возможна путаница."""
        if node_type is None:
            node_type = self._get_node_type(node_id)
        if node_type is None:
            return False
        return (node_type, node_id) in self.selected_items

    def get_selected_items(self) -> set[tuple[int, int]]:
        return self.selected_items

    def get_selected_pairs(self) -> list[tuple[int, int]]:
        return sorted(self.selected_items)

    def get_selected_ids(self) -> list[int]:
        """Только id, без типов (для старого кода)."""
        return [item_id for _, item_id in sorted(self.selected_items)]

    def get_selected_organizations(self) -> list[dict]:
        return [self.organizations[i] for t, i in self.selected_items if t == 1 and i in self.organizations]

    def get_selected_departments(self) -> list[dict]:
        return [self.departments[i] for t, i in self.selected_items if t == 2 and i in self.departments]

    def get_selected_employees(self) -> list[dict]:
        return [self.employees[i] for t, i in self.selected_items if t == 3 and i in self.employees]

    def get_selection_stats(self) -> dict[str, int]:
        org = sum(1 for t, _ in self.selected_items if t == 1)
        dept = sum(1 for t, _ in self.selected_items if t == 2)
        emp = sum(1 for t, _ in self.selected_items if t == 3)
        return {"total": len(self.selected_items), "organizations": org, "departments": dept, "employees": emp}