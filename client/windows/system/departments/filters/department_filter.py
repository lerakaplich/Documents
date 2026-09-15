# client/windows/system/departments/filters/department_filter.py


class DepartmentFilter:
    """Поиск по организациям + сортировка."""

    def __init__(self, page):
        self.page = page
        self.current_sort = "А→Я"

    def matches_org(self, org: dict, query: str) -> bool:
        if not query:
            return True
        return query in org.get('name', '').lower()

    def apply_sort(self, items, method_name: str):
        if method_name == "Я→А (по названию)":
            return sorted(items, key=lambda x: x.get('name', '').lower(), reverse=True)
        return sorted(items, key=lambda x: x.get('name', '').lower())

    def sort_key(self):
        return {
            "А→Я": "А→Я (по названию)",
            "А→Я (по названию)": "А→Я (по названию)",
            "Я→А (по названию)": "Я→А (по названию)",
        }.get(self.current_sort, "А→Я (по названию)")