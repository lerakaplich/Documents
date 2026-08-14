"""
Модуль построения пользовательского интерфейса
"""

import os
from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QVBoxLayout


class EmployeeUI:
    """Строит и настраивает пользовательский интерфейс"""

    def __init__(self, parent_dialog):
        self.parent = parent_dialog

    def load_ui(self):
        """Загружает UI из .ui файла"""
        print("[DEBUG] load_ui() вызван")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(
            current_dir, '..', '..', '..', 'ui', 'system', 'employees', 'employee_dialog.ui'
        )
        ui_path = os.path.normpath(ui_path)

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI file not found: {ui_path}")

        uic.loadUi(ui_path, self.parent)
        print(f"[DEBUG] UI загружен из {ui_path}")

    def setup_window(self, employee, current_user_rights):
        """Настраивает заголовок окна и инициализирует лейауты"""
        print("[DEBUG] setup_window() вызван")
        is_edit = employee and employee.get('id')

        if is_edit:
            full_name = f"{employee.get('last_name', '')} {employee.get('first_name', '')}"
            self.parent.setWindowTitle(f"Редактирование сотрудника - {full_name}")
            self.parent.titleLabel.setText(f"Редактирование сотрудника")
        else:
            self.parent.setWindowTitle("Новый сотрудник")
            self.parent.titleLabel.setText("Новый сотрудник")

        self.setup_static_comboboxes(current_user_rights)
        self.recreate_hierarchy_layout()

    def setup_static_comboboxes(self, current_user_rights):
        """Настраивает статические комбобоксы"""
        print("[DEBUG] setup_static_comboboxes() вызван")
        self.parent.rightsCombo.clear()
        self.parent.rightsCombo.addItem("Пользователь", "user")

        if current_user_rights in ['admin', 'superadmin']:
            self.parent.rightsCombo.addItem("Администратор", "admin")

        self.parent.isLeaderCheckbox.hide()

    def recreate_hierarchy_layout(self):
        """Пересоздает лейаут иерархии"""
        parent_widget = self.parent.hierarchyLayout.parentWidget()
        old_layout = self.parent.hierarchyLayout
        old_layout.deleteLater()

        new_layout = QVBoxLayout()
        new_layout.setSpacing(8)
        self.parent.hierarchyLayout = new_layout
        parent_widget.layout().insertLayout(
            parent_widget.layout().indexOf(old_layout),
            new_layout
        )