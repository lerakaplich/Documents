# client/windows/system/departments/data/department_data_indexer.py
from typing import List, Dict, Any


def index_tree(cache, nodes: List[Dict[str, Any]]):
    """Складывает узлы дерева в cache.nodes_data по id."""
    for n in nodes or []:
        nid = n.get('id')
        if nid is not None:
            cache.nodes_data[nid] = n
        if n.get('children'):
            index_tree(cache, n['children'])


def index_employees_by_department(cache, employees: List[dict]):
    """Раскладывает сотрудников по dept_id на основе positions[].department_id."""
    if not employees:
        return

    # Диагностика: есть ли вообще positions?
    has_positions = any(emp.get('positions') for emp in employees)
    if not has_positions:
        print(f"[WARN] Сотрудников {len(employees)}, но ни у одного нет 'positions'. "
              f"Значит /org/{{id}}/employees не отдаёт позиции — раскладка по отделам "
              f"невозможна. Проверь схему EmployeeRead.")

    for emp in employees:
        added = set()

        # Основной путь: positions[].department_id
        for pos in emp.get('positions') or []:
            dept_id = pos.get('department_id')
            if dept_id is None or dept_id in added:
                continue
            added.add(dept_id)
            cache.employees_by_dept.setdefault(dept_id, []).append(emp)

        # Fallback: department_id прямо на сотруднике
        single = emp.get('department_id')
        if single is not None and single not in added:
            cache.employees_by_dept.setdefault(single, []).append(emp)

    # Логируем распределение
    dist = {d: len(v) for d, v in cache.employees_by_dept.items()}
    print(f"[DEBUG] Сотрудники разложены по dept_id: {dist}")