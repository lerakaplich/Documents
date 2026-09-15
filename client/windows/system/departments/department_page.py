# client/windows/system/departments/department_page.py
import os
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QLabel, QMenu, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.uic import loadUi

from client.core.config import config
from client.core.http_client import HttpClient
from client.core.state.app_state import AppState
from client.services.department_service import get_department_service
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.animations.animated_notification import NotificationManager
from client.windows.system.departments.api_task import ApiTask, TaskKeeper
from client.windows.system.departments.data.department_data_loader import DepartmentDataLoader
from client.windows.system.departments.lazy.department_lazy_loader import DepartmentLazyLoader
from client.windows.system.departments.filters.department_filter import DepartmentFilter
from client.windows.system.departments.crud.department_crud import DepartmentCrud
from client.windows.system.departments.builders.employee_group_builder import build_employee_group
from client.windows.system.employees.employee_card import EmployeeCard


class DepartmentPage(QWidget):
    """
    Тонкий View. Всю работу делегирует:
      • DepartmentDataLoader   — сеть + кэш
      • DepartmentLazyLoader   — раскрытие узлов
      • DepartmentCrud         — create/update/delete
      • DepartmentFilter       — поиск/сортировка
    """

    data_loaded = pyqtSignal()

    def __init__(self, parent=None, http_client: Optional[HttpClient] = None, structure_data=None):
        super().__init__(parent)

        # ─── HTTP ───
        if http_client is None:
            app_state = AppState()
            self.http_client = app_state.http_client or HttpClient(config.base_url)
        else:
            self.http_client = http_client

        self.department_service = get_department_service(self.http_client)

        # ─── Сервисные слои ───
        self.loader = DepartmentDataLoader(self.http_client)
        self.lazy_loader = DepartmentLazyLoader(self, self.loader)
        self.filter = DepartmentFilter(self)
        self.crud = DepartmentCrud(
            self,
            self.department_service,
            organizations_provider=lambda: self.loader.cache.organizations,
            items_provider=lambda: list(self.loader.cache.nodes_data.values()),
            employees_provider=lambda: [],
        )

        # ─── Состояние UI ───
        self.is_loading = False
        self._updating = False
        self._tasks = TaskKeeper()

        self.init_ui()
        self.setup_connections()
        self.notification_manager = NotificationManager(self, max_visible=3)

        QTimer.singleShot(100, self.load_data)

    # ==================== UI ====================

    def init_ui(self):
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)

        if hasattr(self, 'scrollArea'):
            self.scrollArea.setWidgetResizable(True)
            self.scrollArea.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            if hasattr(self, 'scrollAreaWidgetContents'):
                self.scrollAreaWidgetContents.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self.on_add_department)

        if hasattr(self, 'scrollArea'):
            self.scrollArea.verticalScrollBar().valueChanged.connect(self.on_scroll)

        if hasattr(self, 'btnResetFilters'):
            self.btnResetFilters.hide()

    def get_ui_path(self):
        d = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(
            d, '..', '..', '..', 'ui', 'system', 'departments', 'department_page.ui'))

    def setup_connections(self):
        if hasattr(self, 'btnSort'):
            self.btnSort.clicked.connect(self.show_sort_menu)
        if hasattr(self, 'searchEdit'):
            self.searchEdit.textChanged.connect(self.on_search_changed)
        if hasattr(self, 'btnResetFilters'):
            self.btnResetFilters.clicked.connect(self.reset_all_filters)

    # ==================== Уведомления ====================

    def show_success_notification(self, msg): self.notification_manager.show_notification(f"✅ {msg}", 2500)
    def show_error_notification(self, msg):   self.notification_manager.show_notification(f"❌ {msg}", 3000)
    def show_info_notification(self, msg):    self.notification_manager.show_notification(f"ℹ️ {msg}", 2500)

    # ==================== ЗАГРУЗКА ====================

    def load_data(self):
        """Асинхронная загрузка списка организаций."""
        if self.is_loading:
            return
        self.is_loading = True

        task = ApiTask(self.loader.fetch_organizations)
        task.signals.done.connect(self._on_orgs_loaded)
        task.signals.error.connect(self._on_orgs_error)
        self._tasks.submit(task)

    def _on_orgs_loaded(self, orgs):
        self.loader.cache.organizations = orgs or []
        self.loader.cache.clear()  # структура будет строиться лениво
        # но organizations уже стёрли — восстановим:
        self.loader.cache.organizations = orgs or []
        self.is_loading = False

        self.update_display()
        self.data_loaded.emit()

        if orgs:
            self.show_success_notification(f"Загружено {len(orgs)} организаций")

    def _on_orgs_error(self, err):
        self.is_loading = False
        print(f"Ошибка загрузки организаций: {err}")
        self.show_error_notification("Не удалось загрузить организации")

    # ==================== ОТОБРАЖЕНИЕ ====================

    def update_display(self):
        """Строит только корневые узлы (организации)."""
        if self._updating:
            return
        self._updating = True
        try:
            if hasattr(self, 'scrollAreaLayout'):
                self.clear_layout(self.scrollAreaLayout)

            orgs = self.loader.cache.organizations
            if not orgs:
                self._add_empty("Нет организаций")
                return

            query = ""
            if hasattr(self, 'searchEdit'):
                query = self.searchEdit.text().strip().lower()

            shown = 0
            for org in orgs:
                if not self.filter.matches_org(org, query):
                    continue
                node = self._build_org_node(org)
                node.expand_requested.connect(self.lazy_loader.on_expand_requested)
                self.scrollAreaLayout.addWidget(node)
                shown += 1

            if shown == 0:
                self._add_empty("Ничего не найдено")
            self.scrollAreaLayout.addStretch()
        finally:
            self._updating = False
            if hasattr(self, 'scrollAreaWidgetContents'):
                self.scrollAreaWidgetContents.updateGeometry()
            if hasattr(self, 'scrollArea'):
                self.scrollArea.updateGeometry()
            self.updateGeometry()

    def _build_org_node(self, org):
        from client.windows.system.departments.department_node import DepartmentNode
        return DepartmentNode({
            'id': org.get('id'),
            'name': org.get('name', ''),
            'type_display': 'Организация',
            'code': org.get('code', ''),
            'has_children': True,
            'lazy': True,
        }, is_root=True)

    def _add_empty(self, text):
        empty = QLabel(text)
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setStyleSheet("color: #999; font-size: 16px; padding: 40px;")
        self.scrollAreaLayout.addWidget(empty)

    def clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    # ==================== ДЕЛЕГИРОВАНИЕ В CRUD ====================

    def on_add_department(self):
        self.crud.add()

    def on_edit_department(self, data):
        self.crud.edit(data)

    def on_delete_department(self, dept_id):
        self.crud.delete(dept_id)

    # ==================== ФИЛЬТР / ПОИСК / СОРТ ====================

    def show_sort_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #c0c0c0;
                    border-radius: 5px; padding: 5px; color: black; }
            QMenu::item { padding: 8px 25px 8px 15px; border-radius: 3px; font-size: 14px; }
            QMenu::item:selected { background-color: #e3f2fd; }
        """)
        for name in ["А→Я (по названию)", "Я→А (по названию)"]:
            action = menu.addAction(name)
            action.triggered.connect(lambda _c, n=name: self._apply_sort(n))
        if hasattr(self, 'btnSort'):
            menu.exec(self.btnSort.mapToGlobal(self.btnSort.rect().bottomLeft()))

    def _apply_sort(self, name):
        self.filter.current_sort = name
        short = name.split('(')[0].strip() if '(' in name else name
        if hasattr(self, 'btnSort'):
            self.btnSort.setText(f"Сортировка ▼ ({short})")
        self.update_reset_button_visibility()
        self.update_display()

    def on_search_changed(self):
        self.update_reset_button_visibility()
        self.update_display()

    def has_active_filters(self):
        if hasattr(self, 'searchEdit') and self.searchEdit.text().strip():
            return True
        return self.filter.current_sort != "А→Я"

    def update_reset_button_visibility(self):
        if hasattr(self, 'btnResetFilters'):
            self.btnResetFilters.setVisible(self.has_active_filters())

    def reset_all_filters(self):
        if hasattr(self, 'searchEdit'):
            self.searchEdit.clear()
        self.filter.current_sort = "А→Я"
        if hasattr(self, 'btnSort'):
            self.btnSort.setText("Сортировка ▼")
        if hasattr(self, 'btnResetFilters'):
            self.btnResetFilters.hide()
        self.update_display()

    # ==================== ОБРАБОТЧИКИ ЛЕНИВОЙ ЗАГРУЗКИ ====================

    def _on_node_expand_requested(self, node):
        """Вызывается из DepartmentLazyLoader; оставлено для совместимости с сигналом."""
        self.lazy_loader.on_expand_requested(node)
        # Просим scrollArea пересчитать содержимое после вставки
        QTimer.singleShot(0, self._refresh_scroll_area)

    def _refresh_scroll_area(self):
        """Пересчитывает layout внутри scrollArea, чтобы всё влезло."""
        if hasattr(self, 'scrollAreaWidgetContents'):
            self.scrollAreaWidgetContents.updateGeometry()
            if self.scrollAreaWidgetContents.layout():
                self.scrollAreaWidgetContents.layout().activate()
            self.scrollAreaWidgetContents.adjustSize()
        if hasattr(self, 'scrollArea'):
            self.scrollArea.updateGeometry()
        self.updateGeometry()

    # ==================== СОЗДАНИЕ КАРТОЧКИ СОТРУДНИКА ====================

    def _create_employee_card(self, emp_data):
        full_name = " ".join(filter(None, [
            emp_data.get('last_name', ''),
            emp_data.get('first_name', ''),
            emp_data.get('patronymic', ''),
        ])) or f"Сотрудник #{emp_data.get('id', '?')}"

        card = EmployeeCard({
            "id": emp_data.get('id'),
            "display_number": "",
            "full_name": full_name,
            "position": emp_data.get('position_name', 'Должность не указана'),
            "company": "",
            "department": "",
            "subdivision": "",
            "work_phone": emp_data.get('work_number', ''),
            "email": emp_data.get('email', ''),
            "rights": "Сотрудник",
            # сохраняем сырые данные — пригодятся для диалога
            "_raw": emp_data,
        })
        # Подключаем сигналы — по ним откроем диалог/профиль
        card.edit_clicked.connect(self._on_employee_edit_clicked)
        card.delete_clicked.connect(self._on_employee_delete_clicked)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return card

    def _on_employee_edit_clicked(self, emp_data: dict):
        """Открывает EmployeeDialog для сотрудника (совместимо с разными сигнатурами)."""
        import inspect
        from client.windows.system.employees.employee_dialog import EmployeeDialog

        emp_id = emp_data.get('id') or emp_data.get('employee_id')
        raw = emp_data.get('_raw') or emp_data
        print(f"👤 Клик по сотруднику id={emp_id}")

        try:
            sig = inspect.signature(EmployeeDialog.__init__)
            params = list(sig.parameters.keys())
            print(f"[DEBUG] EmployeeDialog.__init__ параметры: {params}")

            # Пробуем разные варианты — какой сработает, тот и используем
            attempts = [
                lambda: EmployeeDialog(self, employee_id=emp_id),
                lambda: EmployeeDialog(self, emp_id=emp_id),
                lambda: EmployeeDialog(self, employee=raw),
                lambda: EmployeeDialog(self, data=raw),
                lambda: EmployeeDialog(self, employee_data=raw),
                lambda: EmployeeDialog(self, profile_manager=None),
                lambda: EmployeeDialog(self, parent=self),  # если parent keyword-only
                lambda: EmployeeDialog(self),  # без данных, отдельно
            ]

            dialog = None
            last_err = None
            for i, attempt in enumerate(attempts):
                try:
                    dialog = attempt()
                    print(f"[DEBUG] Успешный вариант: {i}")
                    break
                except TypeError as e:
                    last_err = e
                    continue

            if dialog is None:
                raise last_err or RuntimeError("Не удалось создать EmployeeDialog")

            # Если данные надо залить отдельно — попробуем несколько методов
            for setter_name in ('set_employee_data', 'set_data',
                                'load_employee', 'set_employee', 'fill_data'):
                if hasattr(dialog, setter_name):
                    try:
                        getattr(dialog, setter_name)(raw)
                        print(f"[DEBUG] Данные переданы через {setter_name}")
                        break
                    except Exception as e:
                        print(f"[WARN] {setter_name} не сработал: {e}")

            dialog.exec()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.show_error_notification(f"Не удалось открыть сотрудника: {e}")

    def _on_employee_delete_clicked(self, emp_id: int):
        """Заглушка — удаление сотрудника из отдела (пока ничего не делаем)."""
        print(f"🗑️ Клик «удалить» у сотрудника id={emp_id}")
        self.show_info_notification("Удаление сотрудника из этой вкладки не поддерживается")

    # ==================== FLOATING BUTTON ====================

    def position_floating_button(self):
        if hasattr(self, 'floating_btn'):
            m = 20
            self.floating_btn.update_base_position(
                self.width() - self.floating_btn.width() - m,
                self.height() - self.floating_btn.height() - m,
            )
            self.floating_btn.raise_()

    def on_scroll(self, _value):
        if hasattr(self, 'floating_btn'):
            self.floating_btn.hide_with_animation()
            self.floating_btn.start_hide_timer()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_floating_button()
        if hasattr(self, 'notification_manager'):
            self.notification_manager.container.setGeometry(0, 0, self.width(), self.height())


def main():
    import sys
    app = QApplication(sys.argv)
    w = DepartmentPage()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()