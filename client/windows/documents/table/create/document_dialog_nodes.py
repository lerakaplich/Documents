# client/windows/documents/table/create/document_dialog_nodes.py
"""
Работа с узлами оргструктуры в диалоге документа: пары (type, id),
справочники, подписи и фоновое получение названий (режим edit).
"""

import concurrent.futures

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal


class _NameResolveSignals(QObject):
    done = pyqtSignal(object)


class _NameResolveTask(QRunnable):
    """
    Режим edit: подтягивает названия только тех узлов, что есть в документе
    (по одному запросу на узел), вместо загрузки всей оргструктуры.
    nodes — список пар (type, id); type 0 = неизвестен (пробуем отдел, затем организацию).
    """

    _PATHS = {
        1: ("/org/{id}",),
        2: ("/departments/{id}",),
        3: ("/employees/{id}",),
        0: ("/departments/{id}", "/org/{id}"),
    }

    def __init__(self, http_client, nodes):
        super().__init__()
        self.http = http_client
        self.nodes = nodes
        self.signals = _NameResolveSignals()
        self.setAutoDelete(False)

    def _fetch(self, node):
        node_type, node_id = node
        for path in self._PATHS.get(node_type, ()):
            try:
                data = self.http.get(path.format(id=node_id))
            except Exception as e:  # noqa: BLE001
                print(f"[DocumentDialog] {path.format(id=node_id)}: {e}")
                continue
            if isinstance(data, dict) and data:
                real_type = node_type or (2 if path.startswith("/departments") else 1)
                return node_type, node_id, real_type, data
        return node_type, node_id, None, None

    def run(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            result = list(ex.map(self._fetch, self.nodes))
        self.signals.done.emit(result)


class NodesMixin:
    """Выбор узлов: пары (type, id). type: 1 — организация, 2 — отдел, 3 — сотрудник."""

    def _lookup_node(self, node_type: int, node_id: int) -> dict | None:
        source = {1: self.organizations, 2: self.departments, 3: self.employees}.get(node_type, [])
        return next((x for x in source if x.get("id") == node_id), None)

    def _as_pairs(self, items, prefer=(3, 2, 1)) -> list[tuple[int, int]]:
        """
        Приводит список к парам (type, id). Принимает пары [type, id]
        либо «голые» id (старый формат из edit-данных): тип тогда определяется
        по справочникам в порядке prefer; если не найден — тип 0 (неизвестен).
        """
        result: list[tuple[int, int]] = []
        for it in items or []:
            if isinstance(it, (list, tuple)) and len(it) == 2:
                result.append((int(it[0]), int(it[1])))
                continue
            try:
                node_id = int(it)
            except (TypeError, ValueError):
                continue
            node_type = next((t for t in prefer if self._lookup_node(t, node_id) is not None), 0)
            result.append((node_type, node_id))
        return result

    @staticmethod
    def _with_name(node: dict) -> dict:
        if not node.get("name"):
            parts = [node.get("last_name"), node.get("first_name"), node.get("patronymic")]
            node["name"] = " ".join(p for p in parts if p).strip() or node.get("full_name") or ""
        return node

    def _resolve_names_async(self):
        """edit: названия получателей/исполнителей — точечно, в фоне (по запросу на узел)."""
        if not self.http_client:
            return
        nodes = []
        for t, i in [*self.selected_receivers, *self.selected_executors]:
            known = self._lookup_node(t, i) is not None if t else any(
                self._lookup_node(x, i) is not None for x in (1, 2, 3)
            )
            if not known and (t, i) not in nodes:
                nodes.append((t, i))
        if not nodes:
            return
        task = _NameResolveTask(self.http_client, nodes)
        task.signals.done.connect(self._on_names_resolved)
        self._name_task = task  # держим ссылку
        QThreadPool.globalInstance().start(task)

    def _on_names_resolved(self, results):
        type_fix: dict[int, int] = {}
        for _orig_type, node_id, real_type, data in results:
            if not data:
                continue
            data = self._with_name(dict(data))
            target = {1: self.organizations, 2: self.departments, 3: self.employees}[real_type]
            if not any(x.get("id") == node_id for x in target):
                target.append(data)
            if not _orig_type:
                type_fix[node_id] = real_type
        if type_fix:  # у получателей с неизвестным типом проставляем найденный
            self.selected_receivers = [
                (type_fix.get(i, t) if t == 0 else t, i) for t, i in self.selected_receivers
            ]
        self._update_receiver_button_text()
        self._update_executor_button_text()

    def _nodes_for_save(self, pairs: list) -> list:
        """create: пары (type, id) — DocumentService различает узлы по типу.
        edit: «голые» id — как отдавалось раньше (контроллер обновления их ожидает)."""
        if self.mode == "create":
            return [tuple(p) for p in pairs]
        return [i for _, i in pairs]

    def _merge_picked(self, dialog):
        """Добавляет выбранные в пикере узлы в справочники диалога (без дублей)."""
        for attr, getter in (
            ("organizations", dialog.get_selected_organizations),
            ("departments", dialog.get_selected_departments),
            ("employees", dialog.get_selected_employees),
        ):
            current = getattr(self, attr)
            known = {x.get("id") for x in current}
            setattr(self, attr, [*current, *(x for x in getter() if x.get("id") not in known)])

    def _get_employee_names(self, nodes: list) -> list:
        """
        Подписи для кнопок получателей/исполнителей. nodes — пары (type, id);
        тип 0 (неизвестен) ищется по всем справочникам.
        """

        def title(item: dict) -> str:
            return (
                item.get("name")
                or item.get("full_name")
                or item.get("display_text")
                or " ".join(
                    filter(
                        None,
                        [item.get("last_name", ""), item.get("first_name", ""), item.get("patronymic", "")],
                    )
                ).strip()
            )

        names = []
        for node_type, node_id in self._as_pairs(nodes):
            types = (node_type,) if node_type in (1, 2, 3) else (3, 2, 1)
            found = None
            for t in types:
                item = self._lookup_node(t, node_id)
                if item:
                    found = title(item)
                    break
            names.append(found or f"ID:{node_id}")
        return names
