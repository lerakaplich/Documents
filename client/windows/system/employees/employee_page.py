import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication, QSizePolicy, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.uic import loadUi

from client.core.filtering.hierarchical_department_filter import HierarchicalDepartmentFilter
from client.core.org_structure.employee.page.employee_data import EmployeeDataManager
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.system.employees.employee_page_handlers import EmployeeHandlers
from client.windows.system.employees.employee_page_ui import EmployeeUIInitializer


class EmployeesPage(QWidget):
    """Страница сотрудников с универсальной иерархией подразделений"""

    employees_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Менеджеры данных
        self.data_manager = EmployeeDataManager()

        # Инициализация UI
        self.ui_initializer = EmployeeUIInitializer(self)
        self.handlers = EmployeeHandlers(self)

        self.current_sort = "А→Я"
        self.current_org_id = None
        self.current_department_id = None

        self.init_ui()
        self.load_test_data()
        self.setup_connections()

        self.department_filter.set_children_func(self.get_children_departments_data)
        self.on_organization_changed(0)
        self.update_display()

    def init_ui(self):
        """Инициализация UI"""
        self.ui_initializer.init_ui()

    def setup_connections(self):
        """Настройка сигналов"""
        self.ui_initializer.setup_connections()

    def load_test_data(self):
        """Загрузка тестовых данных"""
        self.data_manager.load_test_data(self)

    # ======================== ДИАЛОГИ СОТРУДНИКОВ ========================

    def show_add_employee_dialog(self):
        """Открывает диалог создания нового сотрудника"""
        self.handlers.show_add_employee_dialog()

    def show_edit_employee_dialog(self, employee_data):
        """Открывает диалог редактирования сотрудника"""
        self.handlers.show_edit_employee_dialog(employee_data)

    def show_delete_employee_dialog(self, employee_id):
        """Открывает диалог подтверждения удаления"""
        self.handlers.show_delete_employee_dialog(employee_id)

    def _confirm_delete_employee(self, employee_id):
        """Подтверждение удаления сотрудника"""
        self.handlers.confirm_delete_employee(employee_id)

    def on_employee_created(self, employee_id):
        """Обработчик создания нового сотрудника"""
        self.handlers.on_employee_created(employee_id)

    def on_employee_updated(self, employee_id):
        """Обработчик обновления сотрудника"""
        self.handlers.on_employee_updated(employee_id)

    # ======================== ОБРАБОТЧИКИ ========================

    def on_search_changed(self):
        """Обработчик изменения текста поиска"""
        self.update_reset_button_visibility()
        self.update_display()

    def on_organization_changed(self, index):
        """Обработчик изменения организации"""
        self.handlers.on_organization_changed(index)

    def on_department_filter_changed(self, dept_id):
        """Обработчик изменения иерархического фильтра"""
        self.current_department_id = dept_id
        self.update_reset_button_visibility()
        self.update_display()

    def reset_all_filters(self):
        """Сброс всех фильтров, сортировки и поиска"""
        self.handlers.reset_all_filters()

    # ======================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ========================

    def get_root_departments(self, org_id):
        """Возвращает корневые подразделения организации"""
        return self.data_manager.get_root_departments(org_id)

    def get_children_departments_data(self, dept_id):
        """Возвращает список дочерних подразделений"""
        return self.data_manager.get_children_departments(dept_id)

    def get_department_path(self, department_id):
        """Получить путь подразделения для отображения"""
        return self.data_manager.get_department_path(department_id)

    def get_children_departments(self, department_id):
        """Получить все дочерние подразделения (включая вложенные)"""
        return self.data_manager.get_children_departments(department_id)

    def get_employees_with_positions(self):
        """Получить всех сотрудников с их должностями и подразделениями"""
        return self.data_manager.get_employees_with_positions()

    def filter_employees(self):
        """Фильтрация сотрудников"""
        return self.data_manager.filter_employees(
            self.current_org_id,
            self.current_department_id,
            self.searchEdit.text(),
            self.current_sort
        )

    def group_by_organization(self, employees):
        """Группировка сотрудников по организациям"""
        return self.data_manager.group_by_organization(employees)

    # ======================== СОРТИРОВКА ========================

    def show_sort_menu(self):
        """Показать меню сортировки"""
        self.ui_initializer.show_sort_menu()

    def apply_sort(self, sort_func, sort_name):
        """Применить сортировку"""
        self.current_sort = sort_name
        self.btnSort.setText(f"Сортировка ▼ ({sort_name})")
        self.update_reset_button_visibility()
        self.update_display()

    def sort_by_name_asc(self, employees):
        return self.data_manager.sort_by_name_asc(employees)

    def sort_by_name_desc(self, employees):
        return self.data_manager.sort_by_name_desc(employees)

    def sort_by_tab_number(self, employees):
        return self.data_manager.sort_by_tab_number(employees)

    # ======================== ОТОБРАЖЕНИЕ ========================

    def update_display(self):
        """Обновление отображения сотрудников"""
        self.ui_initializer.update_display()

    # ======================== УПРАВЛЕНИЕ КНОПКОЙ СБРОСА ========================

    def has_active_filters(self):
        """Проверяет, есть ли активные фильтры"""
        return self.ui_initializer.has_active_filters()

    def update_reset_button_visibility(self):
        """Показать или скрыть кнопку сброса"""
        self.ui_initializer.update_reset_button_visibility()

    # ======================== ПЛАВАЮЩАЯ КНОПКА ========================

    def position_floating_button(self):
        """Позиционирование плавающей кнопки"""
        self.ui_initializer.position_floating_button()

    def on_scroll(self, value):
        """Обработчик скролла"""
        self.ui_initializer.on_scroll(value)

    def resizeEvent(self, event):
        """Обработчик изменения размера"""
        super().resizeEvent(event)
        self.position_floating_button()


# Для тестирования
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    from PyQt6.QtWidgets import QWidget

    window = QWidget()
    window.setWindowTitle("Тест - Сотрудники")
    window.setGeometry(100, 100, 1000, 700)

    employees_page = EmployeesPage()
    layout = QVBoxLayout(window)
    layout.addWidget(employees_page)

    window.show()
    sys.exit(app.exec())