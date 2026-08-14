from PyQt6.QtWidgets import QMessageBox
from client.windows.system.delete_dialog import DeleteDialog
from client.windows.system.employees.employee_dialog import EmployeeDialog
from client.windows.system.employees.employee_edit_dialog import EmployeeEditDialog


class EmployeeHandlers:
    """Обработчики диалогов и событий для страницы сотрудников"""

    def __init__(self, page):
        self.page = page

    def show_add_employee_dialog(self):
        """Открывает диалог создания нового сотрудника"""
        try:
            if not self.page.current_org_id:
                QMessageBox.warning(
                    self.page,
                    "Организация не выбрана",
                    "Пожалуйста, выберите организацию, в которую хотите добавить сотрудника."
                )
                return

            current_org = self.page.data_manager.organizations.get(self.page.current_org_id)
            if not current_org:
                QMessageBox.warning(self.page, "Ошибка", "Выбранная организация не найдена.")
                return

            current_user_rights = 'admin'
            current_department_id = self.page.current_department_id if self.page.current_department_id else None

            dialog = EmployeeDialog(
                parent_editor=self.page,
                employee=None,
                is_maz=False,
                profile_manager=None,
                current_user_rights=current_user_rights,
                current_user_org_id=self.page.current_org_id,
                current_user_div_id=None,
                current_user_dept_id=current_department_id,
                is_organization_head=False,
                is_division_head=False,
                is_department_head=False,
                filter_external_only=False,
                organization_head_ids=None
            )

            dialog.employee_created.connect(self.page.on_employee_created)
            dialog.employee_updated.connect(self.page.on_employee_updated)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self.page, "Ошибка", f"Не удалось открыть диалог создания сотрудника:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def show_edit_employee_dialog(self, employee_data):
        """Открывает диалог редактирования сотрудника"""
        try:
            employee_id = employee_data.get('id')
            if not employee_id:
                QMessageBox.warning(self.page, "Ошибка", "ID сотрудника не найден")
                return

            employee = self.page.data_manager.employees.get(employee_id)
            if not employee:
                QMessageBox.warning(self.page, "Ошибка", "Сотрудник не найден")
                return

            dialog = EmployeeEditDialog(
                parent_editor=self.page,
                employee=employee,
                is_maz=False,
                profile_manager=None,
                current_user_rights='admin',
                current_user_org_id=self.page.current_org_id,
                current_user_div_id=None,
                current_user_dept_id=self.page.current_department_id,
                is_organization_head=False,
                is_division_head=False,
                is_department_head=False,
                filter_external_only=False,
                organization_head_ids=None
            )

            dialog.employee_updated.connect(self.page.on_employee_updated)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self.page, "Ошибка", f"Не удалось открыть диалог редактирования сотрудника:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def show_delete_employee_dialog(self, employee_id):
        """Открывает диалог подтверждения удаления"""
        try:
            employee = self.page.data_manager.employees.get(employee_id)
            if not employee:
                QMessageBox.warning(self.page, "Ошибка", "Сотрудник не найден")
                return

            full_name = f"{employee.get('last_name', '')} {employee.get('first_name', '')} {employee.get('patronymic', '')}".strip()
            if not full_name:
                full_name = f"ID: {employee_id}"

            dialog = DeleteDialog(parent=self.page)

            if hasattr(dialog, 'messageLabel'):
                dialog.messageLabel.setText(f"Вы уверены, что хотите удалить сотрудника:\n\n{full_name}?")
            if hasattr(dialog, 'nameLabel'):
                dialog.nameLabel.setText(f"Сотрудник: {full_name}")

            dialog.deleted.connect(lambda: self.confirm_delete_employee(employee_id))
            dialog.exec()

        except Exception as e:
            import traceback
            traceback.print_exc()

    def confirm_delete_employee(self, employee_id):
        """Подтверждение удаления сотрудника"""
        try:
            if employee_id not in self.page.data_manager.employees:
                QMessageBox.warning(self.page, "Ошибка", "Сотрудник не найден")
                return

            del self.page.data_manager.employees[employee_id]
            self.page.data_manager.employee_positions = [
                pos for pos in self.page.data_manager.employee_positions
                if pos.get('employee_id') != employee_id
            ]

            QMessageBox.information(self.page, "Успешно", "Сотрудник успешно удален!")
            self.page.update_display()
            self.page.employees_updated.emit()

        except Exception as e:
            QMessageBox.critical(self.page, "Ошибка", f"Не удалось удалить сотрудника:\n{str(e)}")

    def on_employee_created(self, employee_id):
        """Обработчик создания нового сотрудника"""
        QMessageBox.information(self.page, "Успешно", f"Сотрудник с ID {employee_id} успешно создан!")
        self.page.data_manager.load_test_data(self.page)
        self.page.update_display()
        self.page.employees_updated.emit()

    def on_employee_updated(self, employee_id):
        """Обработчик обновления сотрудника"""
        QMessageBox.information(self.page, "Успешно", f"Сотрудник с ID {employee_id} успешно обновлен!")
        self.page.data_manager.load_test_data(self.page)
        self.page.update_display()
        self.page.employees_updated.emit()

    def on_organization_changed(self, index):
        """Обработчик изменения организации"""
        self.page.current_org_id = self.page.comboOrganization.currentData()
        self.page.current_department_id = None

        if self.page.current_org_id:
            root_depts = self.page.get_root_departments(self.page.current_org_id)
            self.page.department_filter.set_root_items(root_depts)
        else:
            self.page.department_filter.clear()

        self.page.update_reset_button_visibility()
        self.page.update_display()

    def reset_all_filters(self):
        """Сброс всех фильтров, сортировки и поиска"""
        self.page.searchEdit.clear()
        self.page.current_sort = "А→Я"
        self.page.btnSort.setText("Сортировка ▼")
        self.page.comboOrganization.setCurrentIndex(0)
        self.page.current_org_id = None
        self.page.current_department_id = None
        self.page.department_filter.reset()
        self.page.btnResetFilters.hide()
        self.page.update_display()