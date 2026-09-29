# client/core/org_structure/employee_selection_data_loader.py
"""
Загрузка данных (организации / отделы / сотрудники) для диалога
выбора сотрудников.

Оптимизации:
- параллельные HTTP-запросы через ThreadPoolExecutor;
- кэш на уровне класса (сбрасывается через clear_cache());
- пропуск организаций, у которых нет данных.
"""

import concurrent.futures
from typing import Any


class EmployeeSelectionDataLoader:
    """Загружает данные для EmployeeSelectionDialog."""

    # ── Кэш (общий для всех инстансов) ──
    _cache_orgs: list[dict] | None = None
    _cache_departments: list[dict] | None = None
    _cache_employees: list[dict] | None = None

    # Сколько запросов пускать параллельно
    _MAX_WORKERS = 16

    def __init__(self, http_client):
        self.http = http_client

    # ── управление кэшем ────────────────────────────────────────────

    @classmethod
    def clear_cache(cls):
        """Сбросить кэш — вызывать при изменении оргструктуры/сотрудников."""
        cls._cache_orgs = None
        cls._cache_departments = None
        cls._cache_employees = None
        print("[Loader] кэш сброшен")

    # ── организации ─────────────────────────────────────────────────

    def load_organizations(self) -> list[dict[str, Any]]:
        if EmployeeSelectionDataLoader._cache_orgs is not None:
            print(
                f"[Loader] организации из кэша: {len(EmployeeSelectionDataLoader._cache_orgs)}"
            )
            return EmployeeSelectionDataLoader._cache_orgs
        try:
            result = self.http.get("/org", params={"limit": 500, "offset": 0})
            if isinstance(result, list):
                EmployeeSelectionDataLoader._cache_orgs = result
                return result
            print(f"[Loader] /org вернул не список: {type(result).__name__}")
            return []
        except Exception as e:
            print(f"[Loader] Ошибка загрузки организаций: {e}")
            return []

    # ── отделы ──────────────────────────────────────────────────────

    def load_departments_flat(self) -> list[dict[str, Any]]:
        if EmployeeSelectionDataLoader._cache_departments is not None:
            print(
                f"[Loader] отделы из кэша: {len(EmployeeSelectionDataLoader._cache_departments)}"
            )
            return EmployeeSelectionDataLoader._cache_departments

        orgs = self.load_organizations()
        result: list[dict[str, Any]] = []

        def fetch_structure(org: dict) -> list:
            org_id = org.get("id")
            if org_id is None:
                return []
            try:
                tree = self.http.get(f"/org/{org_id}/structure")
                return tree if isinstance(tree, list) else []
            except Exception as e:
                print(f"[Loader] Ошибка structure для org {org_id}: {e}")
                return []

        # ── параллельно по всем организациям ──
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._MAX_WORKERS) as ex:
            for org, tree in zip(orgs, ex.map(fetch_structure, orgs)):
                if tree:
                    self._flatten_tree(tree, org.get("id"), result, parent_id=None)

        EmployeeSelectionDataLoader._cache_departments = result
        print(f"[Loader] отделы загружены: {len(result)} (из {len(orgs)} организаций)")
        return result

    @staticmethod
    def _flatten_tree(nodes, org_id, out, parent_id):
        for node in nodes or []:
            node_id = node.get("id")
            out.append(
                {
                    "id": node_id,
                    "name": node.get("name", ""),
                    "parent_id": parent_id,
                    "organization_id": org_id,
                    "department_type_id": node.get("department_type_id"),
                    "department_type_name": node.get("department_type_name"),
                }
            )
            children = node.get("children")
            if children:
                EmployeeSelectionDataLoader._flatten_tree(
                    children,
                    org_id,
                    out,
                    parent_id=node_id,
                )

    # ── сотрудники ──────────────────────────────────────────────────

    def load_employees(self) -> list[dict[str, Any]]:
        if EmployeeSelectionDataLoader._cache_employees is not None:
            print(
                f"[Loader] сотрудники из кэша: {len(EmployeeSelectionDataLoader._cache_employees)}"
            )
            return EmployeeSelectionDataLoader._cache_employees

        orgs = self.load_organizations()
        result: list[dict[str, Any]] = []
        seen = set()

        def fetch_employees(org: dict) -> list:
            org_id = org.get("id")
            if org_id is None:
                return []
            try:
                emps = self.http.get(f"/org/{org_id}/employees")
                return emps if isinstance(emps, list) else []
            except Exception as e:
                print(f"[Loader] Ошибка /org/{org_id}/employees: {e}")
                return []

        # ── параллельно по всем организациям ──
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._MAX_WORKERS) as ex:
            for emps in ex.map(fetch_employees, orgs):
                for emp in emps:
                    emp_id = emp.get("id")
                    if emp_id in seen:
                        continue
                    seen.add(emp_id)

                    name = self._format_name(emp)
                    emp["name"] = name
                    emp["full_name"] = name

                    if not emp.get("positions"):
                        dept_id = emp.get("department_id")
                        if dept_id is not None:
                            emp["positions"] = [{"department_id": dept_id}]
                        else:
                            emp["positions"] = []

                    result.append(emp)

        EmployeeSelectionDataLoader._cache_employees = result
        print(
            f"[Loader] сотрудники загружены: {len(result)} (из {len(orgs)} организаций)"
        )
        return result

    @staticmethod
    def _format_name(emp: dict[str, Any]) -> str:
        parts = [
            emp.get("last_name", "") or "",
            emp.get("first_name", "") or "",
            emp.get("patronymic", "") or "",
        ]
        name = " ".join(p for p in parts if p).strip()
        if name:
            return name
        return emp.get("full_name") or f"ID: {emp.get('id')}"
