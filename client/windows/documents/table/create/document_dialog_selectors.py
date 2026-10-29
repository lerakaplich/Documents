# client/windows/documents/table/create/document_dialog_selectors.py
"""
Выбор участников и тегов в диалоге документа:
отправитель, получатели, исполнители, теги
"""

from PyQt6.QtWidgets import QMessageBox

from client.core.frequent_manager import (
    ROLE_EXECUTOR,
    ROLE_RECEIVER,
    ROLE_SENDER,
    FrequentManager,
)
from client.windows.documents.table.create.selection.employee_selection_dialog import (
    EmployeeSelectionDialog,
)
from client.windows.documents.table.create.selection.tag_selection_dialog import (
    TagSelectionDialog,
)


class SelectorsMixin:
    # ─────────────────── «САМЫЕ ЧАСТЫЕ» ───────────────────

    def _stash_frequent(self, role: str, dialog):
        """Запомнить последний подтверждённый выбор роли; в счётчик попадёт только после сохранения."""
        try:
            if not hasattr(self, "_frequent_pending"):
                self._frequent_pending = {}
            self._frequent_pending[role] = dialog.get_picked_descriptors()
        except Exception as e:
            print(f"[Selectors] не удалось запомнить выбор для частых ({role}): {e}")

    def _commit_frequent(self):
        """Вызвать ОДИН раз после успешного сохранения документа: +1 к счётчикам выбранных."""
        pending = getattr(self, "_frequent_pending", None)
        if not pending:
            return
        try:
            fm = FrequentManager()
            for role, items in pending.items():
                fm.record(role, items)
        except Exception as e:
            print(f"[Selectors] не удалось обновить частые: {e}")
        self._frequent_pending = {}

    # ─────────────────── ОТПРАВИТЕЛЬ ───────────────────

    def _open_sender_selection(self):
        """Открывает диалог выбора отправителя (single-select)."""
        print(f"[DEBUG] selected_sender = {self.selected_sender!r}")
        print(f"[DEBUG] type = {type(self.selected_sender)}")
        if self.selected_sender:
            print(
                f"[DEBUG] keys = {list(self.selected_sender.keys()) if isinstance(self.selected_sender, dict) else 'не dict'}"
            )

        # Безопасно достаём id
        sender_id = None
        if isinstance(self.selected_sender, dict):
            sender_id = self.selected_sender.get("id")
        preselected = [(3, sender_id)] if sender_id else []

        dialog = EmployeeSelectionDialog(
            organizations=self.organizations,
            departments=self.departments,
            employees=self.employees,
            preselected_ids=preselected,
            parent=self,
            title="Выбор отправителя",
            instruction="Выберите отправителя документа:",
            http_client=self.http_client,
            mode="employees",
            allow_org_select=True,
            frequent_role=ROLE_SENDER,
        )
        dialog.selection_confirmed.connect(
            lambda ids, d=dialog: (self._merge_picked(d), self._stash_frequent(ROLE_SENDER, d), self._on_sender_selected(ids))
        )
        dialog.exec()

    def _on_sender_selected(self, selected_pairs):
        pairs = [(t, i) for t, i in self._as_pairs(selected_pairs) if t in (0, 1, 3)]
        if not pairs:
            self.selected_sender = None
            self._update_sender_button_text()
            return

        if len(pairs) > 1:
            QMessageBox.warning(
                self,
                "Внимание",
                "Можно выбрать только одного отправителя. Будет использован первый.",
            )

        node_type, node_id = pairs[0]
        if node_type == 1:
            org = next((o for o in self.organizations if o.get("id") == node_id), None)
            self.selected_sender = {**(org or {}), "id": node_id, "is_organization": True}
        else:
            emp = next((e for e in self.employees if e.get("id") == node_id), None)
            self.selected_sender = emp if emp else {"id": node_id}
        self._update_sender_button_text()

    def _update_sender_button_text(self):
        if not hasattr(self, "btn_sender"):
            return

        if not self.selected_sender:
            self.btn_sender.setText("Выберите отправителя")
            self.btn_sender.setToolTip("")
            return

        s = self.selected_sender
        name = (
            s.get("name")
            or s.get("full_name")
            or " ".join(
                filter(
                    None,
                    [
                        s.get("last_name", ""),
                        s.get("first_name", ""),
                        s.get("patronymic", ""),
                    ],
                )
            ).strip()
        )
        if not name:
            name = f"ID: {s.get('id')}"

        self.btn_sender.setText(name)
        self.btn_sender.setToolTip(name)

    def add_sender(self):
        QMessageBox.information(self, "Поиск", "Используйте кнопку «Выберите отправителя» для выбора.")

    # ─────────────────── ПОЛУЧАТЕЛИ ───────────────────

    def _open_receiver_selection(self):
        """Открывает диалог выбора получателей."""
        dialog = EmployeeSelectionDialog(
            organizations=self.organizations,
            departments=self.departments,
            employees=self.employees,
            preselected_ids=self.selected_receivers,
            parent=self,
            title="Выбор получателей",
            instruction="Выберите получателей документа:",
            http_client=self.http_client,
            mode="receivers",
            frequent_role=ROLE_RECEIVER,
        )
        dialog.selection_confirmed.connect(
            lambda ids, d=dialog: (self._merge_picked(d), self._stash_frequent(ROLE_RECEIVER, d), self._on_receivers_selected(ids))
        )
        dialog.exec()

    def _on_receivers_selected(self, selected_pairs):
        self.selected_receivers = self._as_pairs(selected_pairs, prefer=(2, 1, 3))
        self._update_receiver_button_text()

    def _update_receiver_button_text(self):
        if not hasattr(self, "btn_receiver"):
            return

        if not self.selected_receivers:
            self.btn_receiver.setText("Выберите получателя")
            self.btn_receiver.setToolTip("")
            return

        names = self._get_employee_names(self.selected_receivers)
        text = ", ".join(names[:3])
        if len(self.selected_receivers) > 3:
            text += f" +{len(self.selected_receivers) - 3}..."
        self.btn_receiver.setText(text)
        self.btn_receiver.setToolTip(", ".join(names))

    # ─────────────────── ИСПОЛНИТЕЛИ ───────────────────

    def _open_executor_selection(self):
        """Открывает диалог выбора исполнителей."""
        dialog = EmployeeSelectionDialog(
            organizations=self.organizations,
            departments=self.departments,
            employees=self.employees,
            preselected_ids=self.selected_executors,
            parent=self,
            title="Выбор исполнителей",
            instruction="Выберите исполнителей документа:",
            http_client=self.http_client,
            mode="employees",
            frequent_role=ROLE_EXECUTOR,
        )
        dialog.selection_confirmed.connect(
            lambda ids, d=dialog: (self._merge_picked(d), self._stash_frequent(ROLE_EXECUTOR, d), self._on_executors_selected(ids))
        )
        dialog.exec()

    def _on_executors_selected(self, selected_pairs):
        self.selected_executors = self._as_pairs(selected_pairs)
        self._update_executor_button_text()

    def _update_executor_button_text(self):
        if not hasattr(self, "btnExecutor"):
            return

        if not self.selected_executors:
            self.btnExecutor.setText("Выберите исполнителя")
            self.btnExecutor.setToolTip("")
            return

        names = self._get_employee_names(self.selected_executors)
        text = ", ".join(names[:3])
        if len(self.selected_executors) > 3:
            text += f" +{len(self.selected_executors) - 3}..."
        self.btnExecutor.setText(text)
        self.btnExecutor.setToolTip(", ".join(names))

    # ─────────────────── ТЕГИ ───────────────────

    def _open_tag_selection(self):
        """Открывает диалог выбора тегов."""
        dialog = TagSelectionDialog(
            tags_list=self.available_tags,
            parent=self,
            http_client=self.http_client,
        )

        if self.selected_tags:
            selected_ids = [tag.get("id") for tag in self.selected_tags]
            dialog.set_selected_tags(selected_ids)

        if hasattr(dialog, "setupUi"):
            dialog.setupUi()

        dialog.tags_selected.connect(self._on_tags_selected)
        dialog.exec()

    def _on_tags_selected(self, selected_tags):
        self.selected_tags = selected_tags
        self._update_tag_button_text()

    def _update_tag_button_text(self):
        if not hasattr(self, "btn_tag"):
            return

        if not self.selected_tags:
            self.btn_tag.setText("Выберите теги")
            self.btn_tag.setToolTip("")
            return

        names = [tag.get("name", "") for tag in self.selected_tags[:3]]
        text = ", ".join(names)
        if len(self.selected_tags) > 3:
            text += f" +{len(self.selected_tags) - 3}..."
        self.btn_tag.setText(text)
        self.btn_tag.setToolTip(", ".join(tag.get("name", "") for tag in self.selected_tags))