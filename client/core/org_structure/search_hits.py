# client/core/org_structure/search_hits.py
"""
Общий разбор ответа серверного поиска GET /org/structure/search.
Используется диалогами перенаправления и выбора сотрудников.
"""

from typing import Any

ORG, DEPT, EMP = 1, 2, 3

MIN_SEARCH_LEN = 2  # на сервере q: min_length=2

# Как сервер может называть тип найденного узла (см. StructureSearchResult)
_TYPE_ALIASES = {
    ORG: {"organization", "organisation", "org", "1"},
    DEPT: {"department", "dept", "2"},
    EMP: {"employee", "emp", "3"},
}


def parse_search_hits(raw: Any) -> list[tuple[int, int, int | None]]:
    """
    Ответ GET /org/structure/search → список (type, id, org_id).
    type: 1 — организация, 2 — отдел, 3 — сотрудник; org_id — организация узла
    (для организации это её собственный id).

    Формат сервера (StructureSearchResult):
        {"id": 1092, "type": "department", "title": "...", "subtitle": "Подразделение",
         "ancestors": [{"id": 92, "name": "...", "type": "organization"}, ...]}
    Организации у отдела/сотрудника в ответе нет отдельным полем — она берётся из ancestors
    (ближайший предок типа organization).
    """
    if isinstance(raw, dict):
        raw = raw.get("items") or raw.get("results") or []
    hits: list[tuple[int, int, int | None]] = []
    for h in raw or []:
        if not isinstance(h, dict):
            continue
        node_type = next((t for t, names in _TYPE_ALIASES.items() if str(h.get("type")).lower() in names), None)
        node_id = h.get("id")
        if node_type is None or node_id is None:
            print(f"[Search] пропущена запись неизвестного формата: {h!r}")
            continue

        if node_type == ORG:
            org_id = node_id
        else:
            org_id = None
            for anc in reversed(h.get("ancestors") or []):  # ближайший к узлу предок-организация
                if str(anc.get("type")).lower() in _TYPE_ALIASES[ORG]:
                    org_id = anc.get("id")
                    break
            if org_id is None:
                print(f"[Search] у записи нет организации в ancestors: {h!r}")
        hits.append((node_type, int(node_id), int(org_id) if org_id is not None else None))

    if raw and not hits:
        raise ValueError(f"не распознан формат ответа поиска, пример: {raw[0]!r}")
    return hits