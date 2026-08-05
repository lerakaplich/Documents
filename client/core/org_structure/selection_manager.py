from typing import List, Dict, Any, Set, Optional, Tuple

class SelectionManager:
    """Менеджер управления выбранными элементами"""

    def __init__(self, organizations: Dict[int, Dict], departments: Dict[int, Dict], employees: Dict[int, Dict]):
        self.organizations = organizations
        self.departments = departments
        self.employees = employees
        # Используем составной ключ (type, id) для уникальной идентификации
        self.selected_items: Set[Tuple[int, int]] = set()  # (type, id)

    def set_selected(self, items: List[Tuple[int, int]]):
        """Устанавливает выбранные элементы по списку (type, id)"""
        self.selected_items.clear()
        for type_id, node_id in items:
            if self._is_valid_item(type_id, node_id):
                self.selected_items.add((type_id, node_id))

    def set_selected_by_ids(self, ids: List[int], node_type: int = None):
        """Устанавливает выбранные элементы по списку ID (с определением типа)"""
        self.selected_items.clear()
        for node_id in ids:
            if node_type is not None:
                # Если тип указан явно
                if self._is_valid_item(node_type, node_id):
                    self.selected_items.add((node_type, node_id))
            else:
                # Пытаемся определить тип
                detected_type = self._get_node_type(node_id)
                if detected_type is not None:
                    self.selected_items.add((detected_type, node_id))

    def add(self, node_id: int, node_type: int = None):
        """Добавляет элемент в выбранные"""
        if node_type is None:
            node_type = self._get_node_type(node_id)
        if node_type is not None and self._is_valid_item(node_type, node_id):
            self.selected_items.add((node_type, node_id))

    def remove(self, node_id: int, node_type: int = None):
        """Удаляет элемент из выбранных"""
        if node_type is None:
            node_type = self._get_node_type(node_id)
        if node_type is not None:
            self.selected_items.discard((node_type, node_id))

    def toggle(self, node_id: int, selected: bool, node_type: int = None):
        """Устанавливает состояние выбора для узла"""
        if node_type is None:
            node_type = self._get_node_type(node_id)

        if node_type is None:
            print(f"[SelectionManager] Ошибка: не удалось определить тип для id={node_id}")
            return

        if not self._is_valid_item(node_type, node_id):
            print(f"[SelectionManager] Ошибка: элемент не найден type={node_type}, id={node_id}")
            return

        print(f"[SelectionManager] toggle: type={node_type}, id={node_id}, selected={selected}")

        if selected:
            self.selected_items.add((node_type, node_id))
        else:
            self.selected_items.discard((node_type, node_id))

        print(f"[SelectionManager] selected_items: {self.selected_items}")

    def get_selected_ids(self) -> List[int]:
        """Возвращает список выбранных ID (без учета типов)"""
        result = [item_id for _, item_id in self.selected_items]
        print(f"[SelectionManager] get_selected_ids: {result}")
        return result

    def get_selected_items(self) -> Set[Tuple[int, int]]:
        """Возвращает набор выбранных элементов (type, id)"""
        return self.selected_items

    def is_selected(self, node_id: int, node_type: int = None) -> bool:
        """Проверяет, выбран ли узел"""
        if node_type is None:
            node_type = self._get_node_type(node_id)

        if node_type is None:
            return False

        return (node_type, node_id) in self.selected_items

    def get_selected_organizations(self) -> List[Dict]:
        """Возвращает выбранные организации"""
        result = []
        for type_id, org_id in self.selected_items:
            if type_id == 1:
                org = self.organizations.get(org_id)
                if org:
                    result.append(org)
        return result

    def get_selected_departments(self) -> List[Dict]:
        """Возвращает выбранные отделы"""
        result = []
        for type_id, dept_id in self.selected_items:
            if type_id == 2:
                dept = self.departments.get(dept_id)
                if dept:
                    result.append(dept)
        return result

    def get_selected_employees(self) -> List[Dict]:
        """Возвращает выбранных сотрудников"""
        result = []
        for type_id, emp_id in self.selected_items:
            if type_id == 3:
                emp = self.employees.get(emp_id)
                if emp:
                    result.append(emp)
        return result

    def get_selection_stats(self) -> Dict[str, int]:
        """Возвращает статистику выбранных элементов"""
        org_count = 0
        dept_count = 0
        emp_count = 0

        for type_id, _ in self.selected_items:
            if type_id == 1:
                org_count += 1
            elif type_id == 2:
                dept_count += 1
            elif type_id == 3:
                emp_count += 1

        return {
            'total': len(self.selected_items),
            'organizations': org_count,
            'departments': dept_count,
            'employees': emp_count
        }

    def _get_node_type(self, node_id: int) -> Optional[int]:
        """Определяет тип узла по ID"""
        # Проверяем все возможные типы
        if node_id in self.organizations:
            return 1  # Организация
        if node_id in self.departments:
            return 2  # Отдел
        if node_id in self.employees:
            return 3  # Сотрудник
        return None

    def _is_valid_item(self, node_type: int, node_id: int) -> bool:
        """Проверяет, существует ли элемент с данным типом и ID"""
        if node_type == 1:
            return node_id in self.organizations
        elif node_type == 2:
            return node_id in self.departments
        elif node_type == 3:
            return node_id in self.employees
        return False