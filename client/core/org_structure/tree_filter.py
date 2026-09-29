from PyQt6.QtWidgets import QTreeWidgetItem


class TreeFilter:
    """Фильтр для дерева выбора"""

    @staticmethod
    def has_match_in_children(struct: dict, filter_text: str) -> bool:
        if not filter_text:
            return True

        for dept_struct in struct.get("departments", []):
            if filter_text in dept_struct["department"]["name"].lower():
                return True
            if TreeFilter.has_match_in_children(dept_struct, filter_text):
                return True

        return any(filter_text in emp["name"].lower() for emp in struct.get("employees", []))

    @staticmethod
    def has_match_in_node(item: QTreeWidgetItem, filter_text: str) -> bool:
        if not filter_text:
            return True

        if filter_text in item.text(0).lower():
            return True

        return any(TreeFilter.has_match_in_node(item.child(i), filter_text) for i in range(item.childCount()))
