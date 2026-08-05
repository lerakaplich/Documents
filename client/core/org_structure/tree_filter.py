from typing import Dict, List, Any
from PyQt6.QtWidgets import QTreeWidgetItem


class TreeFilter:
    """Фильтр для дерева выбора"""

    @staticmethod
    def has_match_in_children(struct: Dict, filter_text: str) -> bool:
        if not filter_text:
            return True

        for dept_struct in struct.get('departments', []):
            if filter_text in dept_struct['department']['name'].lower():
                return True
            if TreeFilter.has_match_in_children(dept_struct, filter_text):
                return True

        for emp in struct.get('employees', []):
            if filter_text in emp['name'].lower():
                return True

        return False

    @staticmethod
    def has_match_in_node(item: QTreeWidgetItem, filter_text: str) -> bool:
        if not filter_text:
            return True

        if filter_text in item.text(0).lower():
            return True

        for i in range(item.childCount()):
            if TreeFilter.has_match_in_node(item.child(i), filter_text):
                return True

        return False