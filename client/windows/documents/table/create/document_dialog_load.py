# client/windows/documents/table/create/document_dialog_load.py
"""
Заполнение формы данными документа (режим edit) и установка справочников
"""

from datetime import date, datetime

from PyQt6.QtCore import QDate


class LoadMixin:
    @staticmethod
    def _set_date(widget, value):
        """Ставит дату в QDateEdit из datetime / date / ISO-строки. Пустое значение игнорируется."""
        if not value:
            return
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return
        if isinstance(value, (datetime, date)):
            widget.setDate(QDate(value.year, value.month, value.day))

    def _load_document_data(self):
        """Загружает данные документа в поля (для режима редактирования)"""
        if not self.document_data:
            return

        data = self.document_data

        if hasattr(self, "topic_edit"):
            self.topic_edit.setText(data.get("title", ""))

        if hasattr(self, "type_box"):
            # Ищем по type_id (userData), а не по названию — название могло
            # измениться, id — нет.
            type_id = data.get("type_id")
            if type_id is not None:
                index = self.type_box.findData(type_id)
                if index >= 0:
                    self.type_box.setCurrentIndex(index)

        if hasattr(self, "regarding_edit"):
            self.regarding_edit.setText(data.get("about", ""))

        if hasattr(self, "number_edit"):
            self.number_edit.setText(data.get("reg_number", "") or "")

        if hasattr(self, "index_number_edit"):
            seq = data.get("sequence_number", data.get("sequence_numb"))
            self.index_number_edit.setText("" if seq is None else str(seq))

        # date_edit — это sent_date (дата отправки), а не created_at
        if hasattr(self, "date_edit"):
            self._set_date(self.date_edit, data.get("sent_date"))

        if hasattr(self, "date_deadline"):
            self._set_date(self.date_deadline, data.get("deadline"))

        if hasattr(self, "direction_box"):
            # direction в данных — реальное значение enum ('internal'/'external'),
            # ищем по userData, а не по русскому тексту.
            direction = data.get("direction", "")
            index = self.direction_box.findData(direction)
            if index >= 0:
                self.direction_box.setCurrentIndex(index)

        if hasattr(self, "needs_response_check"):
            self.needs_response_check.setChecked(bool(data.get("needs_response")))

        # Отправитель
        sender = data.get("sender")
        if sender and hasattr(self, "btn_sender"):
            self.selected_sender = sender
            self._update_sender_button_text()

        # Получатели
        receivers = data.get("receivers")
        if isinstance(receivers, list) and receivers and isinstance(receivers[0], dict):
            # сырой формат сервера: точные типы узлов
            pairs = []
            for r in receivers:
                if r.get("target_department_id") is not None:
                    pairs.append((2, r["target_department_id"]))
                elif r.get("target_organization_id") is not None:
                    pairs.append((1, r["target_organization_id"]))
            self.selected_receivers = pairs
        else:
            self.selected_receivers = self._as_pairs(data.get("receiver_ids", []), prefer=(2, 1, 3))
        self._update_receiver_button_text()

        # Исполнители
        executors = data.get("executors")
        if isinstance(executors, list) and executors and isinstance(executors[0], dict):
            for e in executors:  # уже готовые данные сотрудников — кладём в справочник
                emp_id = e.get("id", e.get("employee_id"))
                if emp_id is not None and self._lookup_node(3, emp_id) is None:
                    self.employees.append(self._with_name({**e, "id": emp_id}))
            ex_ids = [e.get("id", e.get("employee_id")) for e in executors]
        else:
            ex_ids = data.get("executor_ids", [])
        # исполнитель — всегда сотрудник
        self.selected_executors = [(3, int(i)) for _, i in self._as_pairs(ex_ids, prefer=(3,))]
        self._update_executor_button_text()

        # Теги
        tags_data = data.get("tags", [])
        if tags_data:
            if isinstance(tags_data[0], (int, str)):
                # В документе только id тегов — названия нужны, поэтому справочник тянем
                # ОДИН раз и только в этом случае (если теги пришли объектами, запроса нет).
                if not self.available_tags:
                    self.available_tags = self._fetch_tags()
                self.selected_tags = [tag for tag in self.available_tags if tag.get("id") in tags_data]
            else:
                self.selected_tags = tags_data
            self._update_tag_button_text()

    # ─────────────────── СПРАВОЧНИКИ ───────────────────

    def set_organizations_data(self, organizations: list[dict]):
        self.organizations = organizations
        print(f"[UI] Загружено {len(organizations)} организаций")

    def set_departments_data(self, departments: list[dict]):
        self.departments = departments
        print(f"[UI] Загружено {len(departments)} отделов")

    def set_employees_data(self, employees: list[dict]):
        self.employees = employees
        print(f"[UI] Загружено {len(employees)} сотрудников")