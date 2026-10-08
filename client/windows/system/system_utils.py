# client/windows/system/system_utils.py
"""Общие функции вкладок «Сотрудники» и «Структура»: дерево отделов, пути, рабочий телефон."""

from typing import Any

PATH_SEP = " / "
WORK_PHONE_KEYS = ("work_phone", "work_phone_number", "phone_work", "office_phone")


def children_of(raw: dict[str, Any]) -> list[dict[str, Any]]:
    return raw.get("children") or raw.get("departments") or []


def to_tree(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Приводит ответ API к дереву. Понимает и вложенный (children), и плоский (parent_id) вид."""
    if not items:
        return []

    nested = any(i.get("children") or i.get("departments") for i in items)
    has_parent = any("parent_id" in i for i in items)
    if nested or not has_parent:
        return items

    by_id = {i["id"]: {**i, "children": []} for i in items}
    roots = []
    for i in items:
        parent = by_id.get(i.get("parent_id"))
        (parent["children"] if parent else roots).append(by_id[i["id"]])
    return roots


def org_label(org: dict[str, Any]) -> str:
    """Короткое название организации для пути («МАЗ»)."""
    return org.get("short_name") or org.get("name") or org.get("full_name") or ""


def collect_paths(org_name: str, tree: list[dict[str, Any]]) -> dict[int, str]:
    """{id отдела: "МАЗ / НТЦ / Телематика"} для всего дерева организации."""
    paths: dict[int, str] = {}

    def walk(items, parts):
        for item in items:
            current = [*parts, item.get("name") or "Без названия"]
            if item.get("id") is not None:
                paths[item["id"]] = PATH_SEP.join(current)
            walk(children_of(item), current)

    walk(tree, [org_name] if org_name else [])
    return paths


def flatten_departments(tree: list[dict[str, Any]], exclude_id: int | None = None) -> list[dict[str, Any]]:
    """Плоский список [{id, name: "НТЦ / Телематика"}] для выбора родительского отдела.

    Отдел exclude_id и всё его поддерево пропускаются (нельзя сделать отдел родителем самого себя).
    """
    flat: list[dict[str, Any]] = []

    def walk(items, parts):
        for item in items:
            if exclude_id is not None and item.get("id") == exclude_id:
                continue
            current = [*parts, item.get("name") or "Без названия"]
            flat.append({"id": item["id"], "name": PATH_SEP.join(current)})
            walk(children_of(item), current)

    walk(tree, [])
    return flat


def work_phone(emp: dict[str, Any]) -> str:
    """Рабочий телефон сотрудника (ищем и в нормализованных данных, и в исходных с сервера)."""
    for source in (emp, emp.get("_raw") or {}):
        for key in WORK_PHONE_KEYS:
            value = source.get(key)
            if value:
                return str(value)
    return ""
