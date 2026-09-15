"""
Диалог создания/редактирования сотрудника
UI загружается из .ui файла
Поддерживает динамическую древовидную структуру подразделений
"""

import os
import asyncio
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox

from client.core.org_structure.employee.dialog.employee_async_operations import EmployeeAsyncOperations
from client.core.org_structure.employee.dialog.employee_data_manager import EmployeeDataManager
from client.core.org_structure.employee.dialog.hierarchy_manager import HierarchyManager
from client.windows.system.employees.employee_dialog_ui import EmployeeUI


class EmployeeDialog(QtWidgets.QDialog):
    employee_created = pyqtSignal(int)
    employee_updated = pyqtSignal(int)

    def __init__(self, parent_editor=None, employee=None, is_maz=False, http_client=None,
                 current_user_rights='user', current_user_org_id=None, current_user_div_id=None,
                 current_user_dept_id=None, is_organization_head=False, is_division_head=False,
                 is_department_head=False, filter_external_only=False, organization_head_ids=None):
        super().__init__(parent_editor)

        self.http_client = http_client                      # ← было profile_manager
        self.current_user_rights = current_user_rights
        self.filter_external_only = filter_external_only

        self.ui_builder = EmployeeUI(self)
        self.hierarchy_manager = HierarchyManager(self)
        self.data_manager = EmployeeDataManager(self, self.hierarchy_manager)
        self.async_ops = EmployeeAsyncOperations(self, self.data_manager)

        self.data_manager.set_employee(employee)

        self.ui_builder.load_ui()
        self.ui_builder.setup_window(employee, current_user_rights)
        self._connect_signals()
        self._load_initial_data()

    def _load_initial_data(self):
        if self.http_client:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.async_ops.load_data_async(self.filter_external_only))
            except RuntimeError:
                QTimer.singleShot(100, self._load_data_sync)
        else:
            print("[WARN] http_client не передан — тестовые данные")
            self.async_ops._fill_test_data()
            QTimer.singleShot(100, self._fill_employee_data_delayed)

    def _load_data_sync(self):
        try:
            asyncio.run(self.async_ops.load_data_async(self.filter_external_only))
        except Exception as e:
            print(f"[ERROR] {e}")
            self.async_ops._fill_test_data()


    def _connect_signals(self):
        """Подключает сигналы"""
        print("[DEBUG] _connect_signals() вызван")
        if hasattr(self, 'saveButton'):
            self.saveButton.clicked.connect(self.save)


    def _fill_employee_data_delayed(self):
        """Заполняет данные сотрудника с задержкой"""
        print("[DEBUG] _fill_employee_data_delayed() вызван")
        try:
            self.data_manager.fill_employee_data()
        except Exception as e:
            print(f"[ERROR] Ошибка заполнения данных: {e}")
            import traceback
            traceback.print_exc()

    def save(self):
        """Сохраняет данные"""
        errors = self.data_manager.validate()
        if errors:
            QMessageBox.warning(self, "Ошибка валидации", "\n".join(errors))
            return

        data = self.data_manager.get_data()
        is_edit = self.data_manager.employee and self.data_manager.employee.get('id')

        if is_edit:
            self.async_ops.start_async_update(data)
        else:
            self.async_ops.start_async_create(data)

    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        super().closeEvent(event)

    def is_edit_mode(self):
        """Возвращает True, если диалог в режиме редактирования"""
        return self.data_manager.employee and self.data_manager.employee.get('id') is not None


# Тестовый запуск
if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)

    print("=" * 50)
    print("Тест 1: Создание нового сотрудника")
    print("=" * 50)

    dialog = EmployeeDialog(
        parent_editor=None,
        employee=None,
        current_user_rights='admin'
    )
    dialog.show()

    sys.exit(app.exec())