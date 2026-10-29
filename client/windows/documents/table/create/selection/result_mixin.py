"""Итог выбора: пары, счётчик, дескрипторы для «самых частых»"""

from typing import Any

from client.core.org_structure.search_hits import DEPT, EMP, ORG
from client.windows.documents.table.create.selection.constants import KIND_BY_TYPE, MODE_EMPLOYEES


class ResultMixin:
    """Результат выбора и подсказка «Выбрано: N элементов»."""

    def _all_selected(self) -> set[tuple[int, int]]:
        return set(self.selection_manager.get_selected_items()) | self._pending

    def _result_pairs(self) -> list[tuple[int, int]]:
        selected = self._all_selected()
        if self.mode == MODE_EMPLOYEES:
            if not self.allow_org:
                return sorted(p for p in selected if p[0] == EMP)
            # сотрудники и организации (организация — сама по себе, без перечисления её сотрудников);
            # отделы в результат не попадают, их сотрудники перечисляются поштучно
            drop_emps: set[tuple[int, int]] = set()
            for t, i in selected:
                if t == ORG and self.selection_manager.is_known(t, i):
                    _depts, emps = self.builder.descendants(t, i)
                    drop_emps |= {(EMP, e) for e in emps}
            return sorted(p for p in selected if p[0] in (ORG, EMP) and p not in drop_emps)

        # receivers: у выбранной организации/отдела потомков не перечисляем
        drop: set[tuple[int, int]] = set()
        for t, i in selected:
            if t in (ORG, DEPT) and self.selection_manager.is_known(t, i):
                depts, emps = self.builder.descendants(t, i)
                drop |= {(DEPT, d) for d in depts}
                drop |= {(EMP, e) for e in emps}
        return sorted(p for p in selected if p not in drop)

    def _update_selection_info(self):
        self._refresh_frequent()
        if not hasattr(self, "selectionInfoLabel"):
            return
        selected = self._all_selected()
        org_count = sum(1 for t, _ in selected if t == ORG)
        dept_count = sum(1 for t, _ in selected if t == DEPT)
        emp_count = sum(1 for t, _ in selected if t == EMP)

        total = len(selected)
        if total == 0:
            self.selectionInfoLabel.setText("Выбрано: 0 элементов")
            return
        parts = [f"Выбрано: {total} элементов"]
        if org_count:
            parts.append(f"организаций: {org_count}")
        if dept_count:
            parts.append(f"отделов: {dept_count}")
        if emp_count:
            parts.append(f"сотрудников: {emp_count}")
        self.selectionInfoLabel.setText(" (".join(parts) + ")")

    def _on_select(self):
        self.selection_confirmed.emit([list(p) for p in self._result_pairs()])
        self.accept()

    def get_selected_pairs(self) -> list[tuple[int, int]]:
        return self._result_pairs()

    def get_selected_ids(self) -> list[int]:
        return [i for _, i in self._result_pairs()]

    def get_selected_organizations(self) -> list[dict]:
        return self.selection_manager.get_selected_organizations()

    def get_selected_departments(self) -> list[dict]:
        return self.selection_manager.get_selected_departments()

    def get_selected_employees(self) -> list[dict]:
        return self.selection_manager.get_selected_employees()

    def _lookup_node(self, node_type: int, node_id: int) -> dict:
        src = {ORG: self.builder.organizations, DEPT: self.builder.departments, EMP: self.builder.employees}[node_type]
        obj = None
        if isinstance(src, dict):
            obj = src.get(node_id)
        else:
            obj = next((x for x in src if isinstance(x, dict) and x.get("id") == node_id), None)
        return obj if isinstance(obj, dict) else {}

    def _find_org_of(self, node_type: int, node_id: int):
        if node_type == ORG:
            return node_id
        obj = self._lookup_node(node_type, node_id)
        org_id = obj.get("organization_id")
        if org_id is None:
            org_id = self._seed_org_of.get((node_type, node_id))
        if org_id is None:
            for oid in self.builder.organizations:
                if self.builder.is_loaded(oid):
                    depts, emps = self.builder.descendants(ORG, oid)
                    if node_id in (depts if node_type == DEPT else emps):
                        return oid
        return org_id

    def get_picked_descriptors(self) -> list[dict]:
        """Итог выбора в виде [{"kind","id","name","org_id"}] — для счётчика «самых частых»."""
        result = []
        for node_type, node_id in self._result_pairs():
            kind = KIND_BY_TYPE.get(node_type)
            if kind is None:
                continue
            item: dict[str, Any] = {"kind": kind, "id": node_id}
            try:
                obj = self._lookup_node(node_type, node_id)
                if node_type == EMP:
                    name = obj.get("full_name") or " ".join(
                        filter(None, [obj.get("last_name"), obj.get("first_name"), obj.get("patronymic")])
                    )
                else:
                    name = obj.get("name")
                if name:
                    item["name"] = name
                org_id = self._find_org_of(node_type, node_id)
                if org_id is not None and node_type != ORG:
                    item["org_id"] = org_id
            except Exception as e:  # noqa: BLE001
                print(f"[EmployeeSelectionDialog] descriptor {node_type}:{node_id}: {e}")
            result.append(item)
        return result
