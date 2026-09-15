"""
Модуль управления данными сотрудника
"""

from datetime import date
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
        if hasattr(self.parent, 'lastNameEdit'):
            self.parent.lastNameEdit.setText(self.employee.get('last_name', ''))

        if hasattr(self.parent, 'firstNameEdit'):
            self.parent.firstNameEdit.setText(self.employee.get('first_name', ''))

        if hasattr(self.parent, 'patronymicEdit'):
            self.parent.patronymicEdit.setText(self.employee.get('patronymic', ''))

        if hasattr(self.parent, 'serviceNumberEdit'):
            self.parent.serviceNumberEdit.setText(self.employee.get('service_number', ''))

        birth_date = self.employee.get('birth_date')
        if birth_date and hasattr(self.parent, 'birthDateEdit'):
            if isinstance(birth_date, str):
                from datetime import datetime
                try:
                    birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
                except:
                    birth_date = date(1980, 1, 1)
            self.parent.birthDateEdit.setDate(birth_date)
        elif hasattr(self.parent, 'birthDateEdit'):
            self.parent.birthDateEdit.setDate(date(1980, 1, 1))

        if hasattr(self.parent, 'phoneEdit'):
            self.parent.phoneEdit.setText(self.employee.get('phone_number', ''))

        if hasattr(self.parent, 'workPhoneEdit'):
            self.parent.workPhoneEdit.setText(self.employee.get('work_number', ''))

        if hasattr(self.parent, 'emailEdit'):
            self.parent.emailEdit.setText(self.employee.get('email', ''))

        chat_id = self.employee.get('chat_id')
        if hasattr(self.parent, 'chatIdEdit'):
            self.parent.chatIdEdit.setText(str(chat_id) if chat_id else '')

        if hasattr(self.parent, 'positionEdit'):
            self.parent.positionEdit.setText(self.employee.get('position_name', ''))

        if hasattr(self.parent, 'assignmentTypeCombo'):
            assignment_type = self.employee.get('assignment_kind', 'primary')
            for i in range(self.parent.assignmentTypeCombo.count()):
                if self.parent.assignmentTypeCombo.itemData(i) == assignment_type:
                    self.parent.assignmentTypeCombo.setCurrentIndex(i)
                    break

        if hasattr(self.parent, 'rightsCombo'):
            rights = self.employee.get('rights') or 'user'
            idx = self.parent.rightsCombo.findData(rights)
            if idx >= 0:
                self.parent.rightsCombo.setCurrentIndex(idx)

        is_leader = self.employee.get('is_leader', False)
        hierarchy_path = self.employee.get('hierarchy_path', [])

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

        elif self.employee.get('organization_id'):
            org_id = self.employee.get('organization_id')
            dept_id = self.employee.get('department_id')

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
                current_id = self.hierarchy_manager.departments_tree[current_id]['parent_id']

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

    def get_data(self):
        """Возвращает данные из формы"""
        rights_index = self.parent.rightsCombo.currentIndex() if hasattr(self.parent, 'rightsCombo') else -1
        rights = self.parent.rightsCombo.itemData(rights_index) or 'user' if rights_index >= 0 else 'user'

        assignment_index = self.parent.assignmentTypeCombo.currentIndex() if hasattr(self.parent, 'assignmentTypeCombo') else -1
        assignment_kind = self.parent.assignmentTypeCombo.itemData(
            assignment_index) or 'primary' if assignment_index >= 0 else 'primary'

        hierarchy_path = self.hierarchy_manager.get_current_hierarchy_path()

        is_leader = self.hierarchy_manager.leader_checkbox.isChecked() if self.hierarchy_manager.leader_checkbox else False

        if is_leader:
            if len(self.hierarchy_manager.hierarchy_combos) > 1:
                last_combo = self.hierarchy_manager.hierarchy_combos[-1][0]
                last_selected = last_combo.currentData()

                if last_selected:
                    department_id = last_selected
                else:
                    if len(self.hierarchy_manager.hierarchy_combos) > 2:
                        prev_combo = self.hierarchy_manager.hierarchy_combos[-2][0]
                        department_id = prev_combo.currentData()
                    else:
                        department_id = None
            else:
                department_id = None
        else:
            department_id = hierarchy_path[-1] if hierarchy_path else None

        organization_id = hierarchy_path[0] if hierarchy_path else None

        chat_id_text = self.parent.chatIdEdit.text().strip() if hasattr(self.parent, 'chatIdEdit') else ''
        chat_id = int(chat_id_text) if chat_id_text and chat_id_text.isdigit() else None

        data = {
            'last_name': self.parent.lastNameEdit.text().strip() if hasattr(self.parent, 'lastNameEdit') else '',
            'first_name': self.parent.firstNameEdit.text().strip() if hasattr(self.parent, 'firstNameEdit') else '',
            'patronymic': self.parent.patronymicEdit.text().strip() if hasattr(self.parent, 'patronymicEdit') else '',
            'phone_number': self.parent.phoneEdit.text().strip() if hasattr(self.parent, 'phoneEdit') else '',
            'work_number': self.parent.workPhoneEdit.text().strip() if hasattr(self.parent, 'workPhoneEdit') else '',
            'email': self.parent.emailEdit.text().strip() if hasattr(self.parent, 'emailEdit') else '',
            'birth_date': self.parent.birthDateEdit.date().toPyDate() if hasattr(self.parent, 'birthDateEdit') else date(1980, 1, 1),
            'chat_id': chat_id,
            'organization_id': organization_id,
            'department_id': department_id,
            'hierarchy_path': hierarchy_path,
            'position_name': self.parent.positionEdit.text().strip() if hasattr(self.parent, 'positionEdit') else '',
            'assignment_kind': assignment_kind,
            'is_leader': is_leader,
            'rights': rights,
            'is_active': True
        }

        if self.employee and self.employee.get('id'):
            data['id'] = self.employee['id']

        return data

    def validate(self):
        """Валидация данных"""
        errors = []

        if hasattr(self.parent, 'lastNameEdit') and not self.parent.lastNameEdit.text().strip():
            errors.append("Фамилия обязательна для заполнения")

        if hasattr(self.parent, 'firstNameEdit') and not self.parent.firstNameEdit.text().strip():
            errors.append("Имя обязательно для заполнения")

        if hasattr(self.parent, 'positionEdit') and not self.parent.positionEdit.text().strip():
            errors.append("Должность обязательна для заполнения")

        hierarchy_path = self.hierarchy_manager.get_current_hierarchy_path()
        if not hierarchy_path:
            errors.append("Организация обязательна для заполнения")

        return errors