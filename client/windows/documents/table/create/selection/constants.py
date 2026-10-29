"""Константы диалога выбора сотрудников / структуры"""

from client.core.org_structure.search_hits import DEPT, EMP, ORG

MODE_RECEIVERS = "receivers"  # организации / отделы / сотрудники, организация — «целиком»
MODE_EMPLOYEES = "employees"  # отправитель / исполнители: только сотрудники

# соответствие типов узлов дерева и видов в счётчике «самых частых»
KIND_BY_TYPE = {ORG: "organization", DEPT: "department", EMP: "employee"}
TYPE_BY_KIND = {v: k for k, v in KIND_BY_TYPE.items()}

FREQUENT_TITLES = {
    "sender": "Самые частые отправители",
    "receiver": "Самые частые получатели",
    "executor": "Самые частые исполнители",
}
FREQUENT_LIMIT = 5
