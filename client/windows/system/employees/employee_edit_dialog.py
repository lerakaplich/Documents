"""
Диалог редактирования сотрудника
Наследуется от EmployeeDialog и переопределяет заголовок
"""

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer
from client.windows.system.employees.employee_dialog import EmployeeDialog


class EmployeeEditDialog(EmployeeDialog):
    """Диалог редактирования сотрудника"""

    def __init__(self, parent_editor=None, employee=None, is_maz=False, profile_manager=None,
                 current_user_rights='user', current_user_org_id=None, current_user_div_id=None,
                 current_user_dept_id=None, is_organization_head=False, is_division_head=False,
                 is_department_head=False, filter_external_only=False, organization_head_ids=None):

        # Сохраняем данные сотрудника
        self._original_employee = employee

        # Вызываем конструктор родителя
        super().__init__(
            parent_editor=parent_editor,
            employee=employee,
            is_maz=is_maz,
            profile_manager=profile_manager,
            current_user_rights=current_user_rights,
            current_user_org_id=current_user_org_id,
            current_user_div_id=current_user_div_id,
            current_user_dept_id=current_user_dept_id,
            is_organization_head=is_organization_head,
            is_division_head=is_division_head,
            is_department_head=is_department_head,
            filter_external_only=filter_external_only,
            organization_head_ids=organization_head_ids
        )

        # Переопределяем заголовок окна после загрузки UI
        QTimer.singleShot(0, self._setup_edit_title)

    def _setup_edit_title(self):
        """Настраивает заголовок для режима редактирования"""
        if self._original_employee and self._original_employee.get('id'):
            last_name = self._original_employee.get('last_name', '')
            first_name = self._original_employee.get('first_name', '')
            patronymic = self._original_employee.get('patronymic', '')

            full_name = f"{last_name} {first_name} {patronymic}".strip()
            if full_name:
                self.setWindowTitle(f"Редактирование сотрудника - {full_name}")
            else:
                self.setWindowTitle("Редактирование сотрудника")

            # Обновляем заголовок в UI
            if hasattr(self, 'titleLabel'):
                if full_name:
                    self.titleLabel.setText(f"Редактирование сотрудника")
                else:
                    self.titleLabel.setText("Редактирование сотрудника")
        else:
            self.setWindowTitle("Редактирование сотрудника")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Редактирование сотрудника")

    def save(self):
        """Переопределяем метод save для редактирования"""
        errors = self.data_manager.validate()
        if errors:
            QMessageBox.warning(self, "Ошибка валидации", "\n".join(errors))
            return

        data = self.data_manager.get_data()
        # Для редактирования всегда передаем ID
        if self.data_manager.employee and self.data_manager.employee.get('id'):
            self.async_ops.start_async_update(data)
        else:
            # Если вдруг ID нет, создаем нового
            QMessageBox.warning(self, "Ошибка", "Не удалось определить ID сотрудника для редактирования")
            return


# Тестовый запуск
if __name__ == '__main__':
    import sys
    from PyQt6 import QtWidgets

    app = QtWidgets.QApplication(sys.argv)

    print("=" * 50)
    print("Тест: Редактирование сотрудника")
    print("=" * 50)

    test_employee = {
        'id': 1,
        'last_name': 'Иванов',
        'first_name': 'Иван',
        'patronymic': 'Иванович',
        'phone_number': '+375 29 123-45-67',
        'work_number': '101',
        'email': 'i.ivanov@maz.by',
        'position_name': 'Генеральный директор',
        'rights': 'admin'
    }

    dialog = EmployeeEditDialog(
        parent_editor=None,
        employee=test_employee,
        current_user_rights='admin'
    )
    dialog.show()

    sys.exit(app.exec())