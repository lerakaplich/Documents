import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication, QSizePolicy, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.uic import loadUi

from client.core.filtering.hierarchical_department_filter import HierarchicalDepartmentFilter
from client.core.org_structure.employee.page.employee_data import EmployeeDataManager
from client.core.state.data_events import get_data_events
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.system.departments.api_task import ApiTask, TaskKeeper
from client.windows.system.employees.employee_page_handlers import EmployeeHandlers
from client.windows.system.employees.employee_page_ui import EmployeeUIInitializer


class EmployeesPage(QWidget):
    employees_updated = pyqtSignal()

    def __init__(self, http_client=None, parent=None):
        super().__init__(parent)

        self.http_client = http_client
        self.data_manager = EmployeeDataManager(http_client)

        self.current_sort = "А→Я"
        self.current_org_id = None
        self.current_department_id = None
        self.is_loading = False

        self.department_filter = None
        self.searchEdit = None
        self.comboOrganization = None
        self.btnSort = None
        self.btnResetFilters = None
        self.scrollArea = None
        self.scrollAreaLayout = None
        self.scrollAreaWidgetContents = None

        self.data_events = get_data_events()
        self.data_events.organizations_changed.connect(self._on_external_change)
        self.data_events.departments_changed.connect(self._on_external_change)
        self.data_events.employees_changed.connect(self._on_external_change)
        self._self_change_in_progress = False

        self._tasks = TaskKeeper()

        self.ui_initializer = EmployeeUIInitializer(self)
        self.handlers = EmployeeHandlers(self)

        self.init_ui()
        self.load_data()
        self.setup_connections()

        self.department_filter.set_children_func(self.get_children_departments_data)
        self.on_organization_changed(0)
        self.update_display()

    # ======================== ЗАГРУЗКА ========================

    def load_data(self):
        if self.is_loading:
            return
        self.is_loading = True
        try:
            if self.http_client:
                ok = self.data_manager.load_data(self)
                if not ok:
                    print("[WARN] API не ответил — тестовые данные")
                    self.data_manager.load_test_data(self)
            else:
                print("[WARN] http_client не передан — тестовые данные")
                self.data_manager.load_test_data(self)
        finally:
            self.is_loading = False

    def _on_external_change(self, org_id: int = 0):
        """Другая вкладка изменила данные — перезагружаем в фоне."""
        if self._self_change_in_progress:
            return
        if self.is_loading:
            return
        if not self.http_client:
            return

        self.is_loading = True
        task = ApiTask(self.data_manager.load_data, self)
        task.signals.done.connect(self._on_reload_done)
        task.signals.error.connect(self._on_reload_error)
        self._tasks.submit(task)

    def _on_reload_done(self, ok):
        self.is_loading = False
        if not ok:
            print("[WARN] фоновая перезагрузка не удалась — тестовые данные")
            self.data_manager.load_test_data(self)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.update_display)

    def _on_reload_error(self, err):
        self.is_loading = False
        print(f"[ERROR] reload: {err}")

    def load_test_data(self):
        self.load_data()

    # ======================== UI ========================

    def init_ui(self):
        self.ui_initializer.init_ui()

    def setup_connections(self):
        self.ui_initializer.setup_connections()

    # ======================== ДИАЛОГИ ========================

    def show_add_employee_dialog(self):
        self.handlers.show_add_employee_dialog()

    def show_edit_employee_dialog(self, employee_data):
        self.handlers.show_edit_employee_dialog(employee_data)

    def show_delete_employee_dialog(self, employee_id):
        self.handlers.show_delete_employee_dialog(employee_id)

    def _confirm_delete_employee(self, employee_id):
        self.handlers.confirm_delete_employee(employee_id)

    def on_employee_created(self, employee_id):
        self.handlers.on_employee_created(employee_id)
        self._self_change_in_progress = True
        try:
            self.data_events.employees_changed.emit(employee_id)
        finally:
            self._self_change_in_progress = False

    def on_employee_updated(self, employee_id):
        self.handlers.on_employee_updated(employee_id)
        self._self_change_in_progress = True
        try:
            self.data_events.employees_changed.emit(employee_id)
        finally:
            self._self_change_in_progress = False

    # ======================== ОБРАБОТЧИКИ ========================

    def on_search_changed(self):
        self.update_reset_button_visibility()
        self.update_display()

    def on_organization_changed(self, index):
        self.handlers.on_organization_changed(index)

    def on_department_filter_changed(self, dept_id):
        self.current_department_id = dept_id
        self.update_reset_button_visibility()
        self.update_display()

    def reset_all_filters(self):
        self.handlers.reset_all_filters()

    # ======================== ВСПОМОГАТЕЛЬНЫЕ ========================

    def get_root_departments(self, org_id):
        return self.data_manager.get_root_departments(org_id)

    def get_children_departments_data(self, dept_id):
        return self.data_manager.get_children_departments(dept_id)

    def get_department_path(self, department_id):
        return self.data_manager.get_department_path(department_id)

    def get_children_departments(self, department_id):
        return self.data_manager.get_children_departments(department_id)

    def get_employees_with_positions(self):
        return self.data_manager.get_employees_with_positions()

    def filter_employees(self):
        return self.data_manager.filter_employees(
            self.current_org_id,
            self.current_department_id,
            self.searchEdit.text(),
            self.current_sort
        )

    def group_by_organization(self, employees):
        return self.data_manager.group_by_organization(employees)

    # ======================== СОРТИРОВКА ========================

    def show_sort_menu(self):
        self.ui_initializer.show_sort_menu()

    def apply_sort(self, sort_func, sort_name):
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
        self.ui_initializer.update_display()

    def has_active_filters(self):
        return self.ui_initializer.has_active_filters()

    def update_reset_button_visibility(self):
        self.ui_initializer.update_reset_button_visibility()

    # ======================== ПЛАВАЮЩАЯ КНОПКА ========================

    def position_floating_button(self):
        self.ui_initializer.position_floating_button()

    def on_scroll(self, value):
        self.ui_initializer.on_scroll(value)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_floating_button()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = QWidget()
    window.setWindowTitle("Тест - Сотрудники")
    window.setGeometry(100, 100, 1000, 700)

    employees_page = EmployeesPage()
    layout = QVBoxLayout(window)
    layout.addWidget(employees_page)

    window.show()
    sys.exit(app.exec())