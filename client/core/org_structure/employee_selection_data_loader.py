# client/core/org_structure/employee_selection_data_loader.py
"""
Загрузка данных (организации / отделы / сотрудники) для диалога
выбора сотрудников.

Два режима:
- ленивый (основной для пикера): load_organizations() + load_org_data(org_id)
  → структура и сотрудники ОДНОЙ организации (2 запроса, кэш 60 с);
- полный (для режима edit): load_departments_flat() / load_employees()
  → всё по всем организациям параллельно.

Общее:
- кэш на уровне класса (сбрасывается через clear_cache());
- блокировки: если несколько компонентов одновременно просят одни и те же
  данные, грузит только первый, остальные ждут и берут готовый кэш;
- пустой результат при ошибке сети не кэшируется.
"""

import concurrent.futures
import threading
import time
from typing import Any


class EmployeeSelectionDataLoader:
    """Загружает данные для EmployeeSelectionDialog."""

    # ── Блокировки (по одной на каждый вид данных) ──
    # Порядок захвата: depts/emps -> orgs (обратного порядка нет, взаимной блокировки быть не может)
    _orgs_lock = threading.Lock()
    _depts_lock = threading.Lock()
    _emps_lock = threading.Lock()

    # ── Кэш (общий для всех инстансов) ──
    _cache_orgs: list[dict] | None = None
    _cache_departments: list[dict] | None = None
    _cache_employees: list[dict] | None = None

    # ── Ленивый кэш по организациям: org_id -> (monotonic_time, data) ──
    _ORG_TTL = 60  # секунд
    _cache_org_data: dict[int, tuple[float, dict]] = {}
    _org_locks: dict[int, threading.Lock] = {}
    _org_locks_guard = threading.Lock()

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
        cls._cache_org_data.clear()
        print("[Loader] кэш сброшен")

    # ── организации ─────────────────────────────────────────────────

    def load_organizations(self) -> list[dict[str, Any]]:
        cls = EmployeeSelectionDataLoader
        if cls._cache_orgs is not None:
            return cls._cache_orgs
        with cls._orgs_lock:
            return self._load_organizations_impl()

    def _load_organizations_impl(self) -> list[dict[str, Any]]:
        cls = EmployeeSelectionDataLoader
        # повторная проверка: пока ждали замок, другой поток мог уже всё загрузить
        if cls._cache_orgs is not None:
            return cls._cache_orgs
        try:
            result = self.http.get("/org", params={"limit": 500, "offset": 0})
            if isinstance(result, list):
                cls._cache_orgs = result
                print(f"[Loader] организации загружены: {len(result)}")
                return result
            print(f"[Loader] /org вернул не список: {type(result).__name__}")
            return []
        except Exception as e:
            print(f"[Loader] Ошибка загрузки организаций: {e}")
            return []

    # ── ЛЕНИВАЯ загрузка одной организации ──────────────────────────

    @classmethod
    def _lock_for(cls, org_id: int) -> threading.Lock:
        with cls._org_locks_guard:
            return cls._org_locks.setdefault(org_id, threading.Lock())

    def load_org_data(self, org_id: int, force: bool = False) -> dict[str, list]:
        """
        Структура + сотрудники ОДНОЙ организации (2 параллельных запроса).
        Кэш 60 секунд. При ошибке сети бросает исключение (и ничего не кэширует),
        чтобы вызывающий мог показать ошибку и дать повторить.

        Возвращает {"departments": [...плоский список...], "employees": [...]}.
        """
        cls = EmployeeSelectionDataLoader

        def fresh():
            hit = cls._cache_org_data.get(org_id)
            if hit and not force and time.monotonic() - hit[0] < cls._ORG_TTL:
                return hit[1]
            return None

        data = fresh()
        if data is not None:
            return data

        with cls._lock_for(org_id):
            # пока ждали замок, другой поток мог уже всё загрузить
            data = fresh()
            if data is not None:
                return data

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
                f_tree = ex.submit(self.http.get, f"/org/{org_id}/structure")
                f_emps = ex.submit(self.http.get, f"/org/{org_id}/employees")
                tree = f_tree.result()
                emps = f_emps.result()

            departments: list[dict[str, Any]] = []
            self._flatten_tree(tree if isinstance(tree, list) else [], org_id, departments, parent_id=None)
            employees = [self._normalize_employee(e, org_id) for e in (emps if isinstance(emps, list) else [])]

            data = {"departments": departments, "employees": employees}
            cls._cache_org_data[org_id] = (time.monotonic(), data)
            print(f"[Loader] org {org_id}: отделов {len(departments)}, сотрудников {len(employees)}")
            return data

    def load_all_orgs_data(self, org_ids: list[int] | None = None) -> dict[int, dict[str, list]]:
        """
        Данные нескольких организаций параллельно (для поиска).
        Организации, которые не удалось загрузить, пропускаются.

        ВНИМАНИЕ: если на бэкенде появится эндпоинт поиска — заменить этот
        метод одним запросом и возвращать тот же формат {org_id: {...}}.
        """
        if org_ids is None:
            org_ids = [o["id"] for o in self.load_organizations() if o.get("id") is not None]

        def one(org_id: int):
            try:
                return org_id, self.load_org_data(org_id)
            except Exception as e:
                print(f"[Loader] Ошибка загрузки org {org_id}: {e}")
                return org_id, None

        result: dict[int, dict[str, list]] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._MAX_WORKERS) as ex:
            for org_id, data in ex.map(one, org_ids):
                if data is not None:
                    result[org_id] = data
        return result

    # ── отделы (все организации сразу) ──────────────────────────────

    def load_departments_flat(self) -> list[dict[str, Any]]:
        cls = EmployeeSelectionDataLoader
        if cls._cache_departments is not None:
            return cls._cache_departments
        with cls._depts_lock:
            return self._load_departments_impl()

    def _load_departments_impl(self) -> list[dict[str, Any]]:
        cls = EmployeeSelectionDataLoader
        if cls._cache_departments is not None:
            return cls._cache_departments

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
            for org, tree in zip(orgs, ex.map(fetch_structure, orgs), strict=False):
                if tree:
                    self._flatten_tree(tree, org.get("id"), result, parent_id=None)

        # если организации не загрузились (ошибка сети), пустой результат не кэшируем
        if orgs:
            cls._cache_departments = result
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
                    "number": node.get("number"),
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

    # ── сотрудники (все организации сразу) ──────────────────────────

    def load_employees(self) -> list[dict[str, Any]]:
        cls = EmployeeSelectionDataLoader
        if cls._cache_employees is not None:
            return cls._cache_employees
        with cls._emps_lock:
            return self._load_employees_impl()

    def _load_employees_impl(self) -> list[dict[str, Any]]:
        cls = EmployeeSelectionDataLoader
        if cls._cache_employees is not None:
            return cls._cache_employees

        orgs = self.load_organizations()
        result: list[dict[str, Any]] = []
        seen = set()

        def fetch_employees(org: dict) -> tuple[Any, list]:
            org_id = org.get("id")
            if org_id is None:
                return None, []
            try:
                emps = self.http.get(f"/org/{org_id}/employees")
                return org_id, emps if isinstance(emps, list) else []
            except Exception as e:
                print(f"[Loader] Ошибка /org/{org_id}/employees: {e}")
                return org_id, []

        # ── параллельно по всем организациям ──
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._MAX_WORKERS) as ex:
            for org_id, emps in ex.map(fetch_employees, orgs):
                for emp in emps:
                    emp_id = emp.get("id")
                    if emp_id in seen:
                        continue
                    seen.add(emp_id)
                    result.append(self._normalize_employee(emp, org_id))

        # если организации не загрузились (ошибка сети), пустой результат не кэшируем
        if orgs:
            cls._cache_employees = result
        print(f"[Loader] сотрудники загружены: {len(result)} (из {len(orgs)} организаций)")
        return result

    # ── общие помощники ─────────────────────────────────────────────

    @classmethod
    def _normalize_employee(cls, emp: dict[str, Any], org_id: int | None) -> dict[str, Any]:
        name = cls._format_name(emp)
        emp["name"] = name
        emp["full_name"] = name
        if org_id is not None:
            emp.setdefault("organization_id", org_id)
        if not emp.get("positions"):
            dept_id = emp.get("department_id")
            emp["positions"] = [{"department_id": dept_id}] if dept_id is not None else []
        return emp

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