# client/windows/system/departments/builders/department_node_builder.py
from client.windows.system.departments.department_node import DepartmentNode


def detect_department_type(node) -> str:
    if node.get("department_type_id"):
        return {
            1: "divisions", 2: "departments", 3: "bureaus",
            4: "sections", 5: "workshops",
        }.get(node["department_type_id"], "departments")
    name = (node.get("name") or "").lower()
    for key, val in [("управл", "divisions"), ("цех", "workshops"),
                     ("бюро", "bureaus"), ("сектор", "sections"),
                     ("дирекц", "directorates"), ("отдел", "departments")]:
        if key in name:
            return val
    return "departments"


def type_display_name(key: str) -> str:
    return {
        "divisions": "Управления", "departments": "Отделы",
        "workshops": "Цеха", "branches": "Филиалы",
        "sections": "Сектора", "bureaus": "Бюро",
        "directorates": "Дирекции",
    }.get(key, key.capitalize())


def build_child_node(node_data, org_name: str, page) -> DepartmentNode:
    """Строит дочерний DepartmentNode, подключает сигналы к page."""
    tdisp = type_display_name(detect_department_type(node_data))

    # ⚠️ ГЛАВНОЕ ИЗМЕНЕНИЕ:
    # Отделы ВСЕГДА считаем expandable — потому что у них могут быть
    # сотрудники, даже если нет вложенных подразделений.
    # Раньше логика требовала наличия 'children' в узле → узлы без
    # вложенности не пытались грузить сотрудников.
    explicit_has_children = True

    item = {
        'id': node_data.get('id'),
        'name': node_data.get('name'),
        'type_display': tdisp,
        'code': str(node_data.get('id', '')),
        'leader': node_data.get('leader', 'Не назначен'),
        'phone': node_data.get('phone', ''),
        'description': node_data.get('description', ''),
        'organization': org_name,
        'has_children': explicit_has_children,
        'lazy': True,
    }
    node = DepartmentNode(item)
    node.set_card_data({
        'id': item['id'], 'name': item['name'], 'code': item['code'],
        'leader': item['leader'], 'phone': item['phone'],
        'description': item['description'], 'type': item['type_display'],
        'organization': item['organization'],
    })
    node.edit_clicked.connect(page.on_edit_department)
    node.delete_clicked.connect(page.on_delete_department)
    node.expand_requested.connect(page._on_node_expand_requested)
    return node