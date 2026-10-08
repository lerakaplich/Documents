"""
Модуль управления данными сотрудника
"""

from datetime import date, datetime

from PyQt6.QtCore import QTimer


class EmployeeDataManager:
    """Управляет загрузкой и обработкой данных сотрудника"""

    def __init__(self, parent_dialog, hierarchy_manager):
        self.parent = parent_dialog
        self.hierarchy_manager = hierarchy_manager
        self.employee = {}
        self._data_loaded = False

    def set_employee(self, employee):
        """Устанавливает данные сотрудника"""
        self.employee = employee if employee is not None else {}

    def fill_employee_data(self):
        """Заполняет поля данными сотрудника"""
        if not self.employee or not self._data_loaded:
            return

        print("[INFO] Заполнение данных сотрудника...")

        # Проверяем наличие виджетов перед заполнением
        if hasattr(self.parent, "lastNameEdit"):
            self.parent.lastNameEdit.setText(self.employee.get("last_name", ""))

        if hasattr(self.parent, "firstNameEdit"):
            self.parent.firstNameEdit.setText(self.employee.get("first_name", ""))

        if hasattr(self.parent, "patronymicEdit"):
            self.parent.patronymicEdit.setText(self.employee.get("patronymic", ""))

        if hasattr(self.parent, "serviceNumberEdit"):
            self.parent.serviceNumberEdit.setText(self.employee.get("service_number", ""))

        birth_date = self.employee.get("birth_date")
        if birth_date and hasattr(self.parent, "birthDateEdit"):
            if isinstance(birth_date, str):
                try:
                    birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    birth_date = date(1980, 1, 1)
            self.parent.birthDateEdit.setDate(birth_date)
        elif hasattr(self.parent, "birthDateEdit"):
            self.parent.birthDateEdit.setDate(date(1980, 1, 1))

        if hasattr(self.parent, "phoneEdit"):
            self.parent.phoneEdit.setText(self.employee.get("phone_number", ""))

        if hasattr(self.parent, "workPhoneEdit"):
            self.parent.workPhoneEdit.setText(self.employee.get("work_number", ""))

        if hasattr(self.parent, "emailEdit"):
            self.parent.emailEdit.setText(self.employee.get("email", ""))

        chat_id = self.employee.get("chat_id")
        if hasattr(self.parent, "chatIdEdit"):
            self.parent.chatIdEdit.setText(str(chat_id) if chat_id else "")

        if hasattr(self.parent, "positionEdit"):
            self.parent.positionEdit.setText(self.employee.get("position_name", ""))

        if hasattr(self.parent, "assignmentTypeCombo"):
            assignment_type = self.employee.get("assignment_kind", "primary")
            for i in range(self.parent.assignmentTypeCombo.count()):
                if self.parent.assignmentTypeCombo.itemData(i) == assignment_type:
                    self.parent.assignmentTypeCombo.setCurrentIndex(i)
                    break

        if hasattr(self.parent, "rightsCombo"):
            rights = self.employee.get("rights") or "user"
            idx = self.parent.rightsCombo.findData(rights)
            if idx >= 0:
                self.parent.rightsCombo.setCurrentIndex(idx)

        is_leader = self.employee.get("is_leader", False)
        hierarchy_path = self.employee.get("hierarchy_path", [])

        if hierarchy_path:
            for level, item_id in enumerate(hierarchy_path):
                if level < len(self.hierarchy_manager.hierarchy_combos):
                    combo = self.hierarchy_manager.hierarchy_combos[level][0]
                    index = combo.findData(item_id)
                    if index >= 0:
                        combo.setCurrentIndex(index)
                        self.hierarchy_manager.update_label_text(level, item_id)

            if is_leader and self.hierarchy_manager.leader_checkbox:
                self.hierarchy_manager.leader_checkbox.setChecked(True)

        elif self.employee.get("organization_id"):
            org_id = self.employee.get("organization_id")
            dept_id = self.employee.get("department_id")

            if self.hierarchy_manager.hierarchy_combos:
                combo = self.hierarchy_manager.hierarchy_combos[0][0]
                index = combo.findData(org_id)
                if index >= 0:
                    combo.setCurrentIndex(index)
                    self.hierarchy_manager.update_label_text(0, org_id)

            if dept_id:
                QTimer.singleShot(500, lambda: self.set_old_format_data(dept_id, is_leader))

    def set_old_format_data(self, dept_id, is_leader):
        """Устанавливает данные из старого формата"""
        if dept_id in self.hierarchy_manager.departments_tree:
            path = []
            current_id = dept_id
            while current_id:
                path.insert(0, current_id)
                current_id = self.hierarchy_manager.departments_tree[current_id]["parent_id"]

            for level, item_id in enumerate(path):
                combo_level = level + 1
                if combo_level < len(self.hierarchy_manager.hierarchy_combos):
                    combo = self.hierarchy_manager.hierarchy_combos[combo_level][0]
                    index = combo.findData(item_id)
                    if index >= 0:
                        combo.setCurrentIndex(index)
                        self.hierarchy_manager.update_label_text(combo_level, item_id)

            if is_leader and self.hierarchy_manager.leader_checkbox:
                self.hierarchy_manager.leader_checkbox.setChecked(True)

    # ────────────────────────────────────────────────────────────────
    #                          GET DATA
    # ────────────────────────────────────────────────────────────────

    def _get_rights(self) -> str:
        """Права доступа из combo."""
        if not hasattr(self.parent, "rightsCombo"):
            return "user"
        idx = self.parent.rightsCombo.currentIndex()
        if idx < 0:
            return "user"
        return self.parent.rightsCombo.itemData(idx) or "user"

    def _get_department_id(self, hierarchy_path: list, is_leader: bool):
        """Определяет department_id для position (учитывает флаг руководителя)."""
        if not is_leader:
            return hierarchy_path[-1] if hierarchy_path else None

        # Руководитель: подразделение — уровень выше последнего выбранного
        if len(self.hierarchy_manager.hierarchy_combos) > 1:
            last_combo = self.hierarchy_manager.hierarchy_combos[-1][0]
            last_selected = last_combo.currentData()
            if last_selected:
                return last_selected
            if len(self.hierarchy_manager.hierarchy_combos) > 2:
                return self.hierarchy_manager.hierarchy_combos[-2][0].currentData()
            return None
        return None

    def _get_service_number(self) -> str:
        """
        Табельный номер.

        Если редактируем — берём существующий. Если создаём и поле пустое —
        генерируем EMP_<timestamp>. Схема EmployeeCreate требует поле обязательным.
        """
        if self.employee and self.employee.get("service_number"):
            return self.employee["service_number"]

        if hasattr(self.parent, "serviceNumberEdit"):
            text = self.parent.serviceNumberEdit.text().strip()
            if text:
                return text

        # Генерируем временный табельный — бэкенд примет, потом админ поправит
        return f"EMP_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _get_birth_date_iso(self):
        """Дата рождения в ISO-формате (YYYY-MM-DD) или None."""
        if not hasattr(self.parent, "birthDateEdit"):
            return None
        qdate = self.parent.birthDateEdit.date()
        if not qdate.isValid():
            return None
        return qdate.toString("yyyy-MM-dd")

    def get_data(self) -> dict:
        """
        Возвращает данные формы в формате, который ждёт сервер (схема EmployeeCreate).

        Структура:
            {
              service_number, last_name, first_name, patronymic,
              phone_number, work_number, email, birth_date, chat_id,
              rights,
              position: {department_id, position_name, is_leader, start_date, end_date}
            }
        """
        hierarchy_path = self.hierarchy_manager.get_current_hierarchy_path()
        is_leader = (
            self.hierarchy_manager.leader_checkbox.isChecked() if self.hierarchy_manager.leader_checkbox else False
        )
        department_id = self._get_department_id(hierarchy_path, is_leader)

        chat_id_text = self.parent.chatIdEdit.text().strip() if hasattr(self.parent, "chatIdEdit") else ""
        chat_id = int(chat_id_text) if chat_id_text and chat_id_text.isdigit() else None

        def _val(attr_name: str) -> str | None:
            if not hasattr(self.parent, attr_name):
                return None
            text = getattr(self.parent, attr_name).text().strip()
            return text or None

        data = {
            # ── EmployeeBase ──
            "service_number": self._get_service_number(),
            "last_name": _val("lastNameEdit") or "",
            "first_name": _val("firstNameEdit") or "",
            "patronymic": _val("patronymicEdit"),
            "phone_number": _val("phoneEdit"),
            "work_number": _val("workPhoneEdit"),
            "email": _val("emailEdit"),
            "birth_date": self._get_birth_date_iso(),
            "chat_id": chat_id,
            # ── EmployeeCreate ──
            "rights": self._get_rights(),
            # ── PositionCreate (вложенный) ──
            "position": {
                "department_id": department_id,
                "position_name": _val("positionEdit") or "",
                "is_leader": is_leader,
                "start_date": date.today().isoformat(),
                "end_date": None,
            },
        }

        # При редактировании сервер может ожидать поле id отдельно — оставляем на случай,
        # если в схеме EmployeeFullUpdate оно когда-нибудь понадобится. Для создания
        # сервер его игнорирует (нет в EmployeeCreate).
        if self.employee and self.employee.get("id"):
            data["id"] = self.employee["id"]

        return data

    def validate(self):
        """Валидация данных"""
        errors = []

        if hasattr(self.parent, "lastNameEdit") and not self.parent.lastNameEdit.text().strip():
            errors.append("Фамилия обязательна для заполнения")

        if hasattr(self.parent, "firstNameEdit") and not self.parent.firstNameEdit.text().strip():
            errors.append("Имя обязательно для заполнения")

        if hasattr(self.parent, "positionEdit") and not self.parent.positionEdit.text().strip():
            errors.append("Должность обязательна для заполнения")

        hierarchy_path = self.hierarchy_manager.get_current_hierarchy_path()
        if not hierarchy_path:
            errors.append("Организация обязательна для заполнения")

        return errors