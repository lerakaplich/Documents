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
from client.core.state.data_events import get_data_events
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
    """Тонкий View. Делегирует работу сервисным слоям."""

    data_loaded = pyqtSignal()

    def __init__(self, parent=None, http_client: Optional[HttpClient] = None, structure_data=None):
        super().__init__(parent)

        if http_client is None:
            app_state = AppState()
            self.http_client = app_state.http_client or HttpClient(config.base_url)
        else:
            self.http_client = http_client

        self.data_events = get_data_events()
        self.data_events.organizations_changed.connect(self._on_external_change)
        self.data_events.employees_changed.connect(self._on_external_change)

        self.department_service = get_department_service(self.http_client)

        self.loader = DepartmentDataLoader(self.http_client)
        self.lazy_loader = DepartmentLazyLoader(self, self.loader)
        self.filter = DepartmentFilter(self)
        self.crud = DepartmentCrud(
            self,
            self.department_service,
            organizations_provider=lambda: self.loader.cache.organizations,
            items_provider=lambda: list(self.loader.cache.nodes_data.values()),
            employees_provider=self._get_cached_employees,  # ← было lambda: []
        )
        self.is_loading = False
        self._updating = False
        self._search_mode = False
        self._search_results = []
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

        if hasattr(self, 'scrollAreaLayout'):
            self.scrollAreaLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

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
            self.searchEdit.returnPressed.connect(self.on_search_clicked)
        if hasattr(self, 'btnResetFilters'):
            self.btnResetFilters.clicked.connect(self.reset_all_filters)
        if hasattr(self, 'btnSearch'):
            self.btnSearch.clicked.connect(self.on_search_clicked)

    def _get_cached_employees(self) -> list:
        """Все уникальные сотрудники, разложенные по отделам в кэше ленивой загрузки."""
        seen = set()
        result = []
        for emps in self.loader.cache.employees_by_dept.values():
            for emp in emps:
                eid = emp.get('id')
                if eid and eid not in seen:
                    seen.add(eid)
                    result.append(emp)
        return result

    def _on_external_change(self, org_id: int = 0):
        """Другая вкладка изменила организации/сотрудников — перезагружаем дерево."""
        if self.is_loading:
            return
        QTimer.singleShot(0, self.load_data)

    # ==================== ПОИСК ====================

    def on_search_clicked(self):
        if not hasattr(self, 'searchEdit'):
            return
        q = self.searchEdit.text().strip()
        if len(q) < 2:
            self.show_info_notification("Введите минимум 2 символа")
            return
        if self.is_loading:
            return

        self.is_loading = True
        task = ApiTask(self.loader.search_structure, q)
        task.signals.done.connect(self._on_search_results)
        task.signals.error.connect(self._on_search_error)
        self._tasks.submit(task)

    def _on_search_results(self, results):
        self.is_loading = False
        self._search_mode = True
        self._search_results = results or []
        self.update_reset_button_visibility()
        self.update_display()

        if self._search_results:
            self.show_success_notification(f"Найдено: {len(self._search_results)}")
        else:
            self.show_info_notification("Ничего не найдено")

    def _on_search_error(self, err):
        self.is_loading = False
        print(f"[ERROR] search: {err}")
        self.show_error_notification("Ошибка поиска")

    # ==================== УВЕДОМЛЕНИЯ ====================

    def show_success_notification(self, msg): self.notification_manager.show_notification(f"✅ {msg}", 2500)
    def show_error_notification(self, msg):   self.notification_manager.show_notification(f"❌ {msg}", 3000)
    def show_info_notification(self, msg):    self.notification_manager.show_notification(f"ℹ️ {msg}", 2500)

    # ==================== ЗАГРУЗКА ====================

    def load_data(self):
        if self.is_loading:
            return
        self.is_loading = True

        task = ApiTask(self.loader.fetch_organizations)
        task.signals.done.connect(self._on_orgs_loaded)
        task.signals.error.connect(self._on_orgs_error)
        self._tasks.submit(task)

    def _on_orgs_loaded(self, orgs):
        self.loader.cache.organizations = orgs or []
        self.loader.cache.clear()
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
        if self._updating:
            return
        self._updating = True
        try:
            if hasattr(self, 'scrollAreaLayout'):
                self.clear_layout(self.scrollAreaLayout)
                self.loader.cache.children_nodes.clear()

            if self._search_mode:
                self._render_search_results()
            else:
                self._render_tree()
        finally:
            self._updating = False
            if hasattr(self, 'scrollAreaWidgetContents'):
                self.scrollAreaWidgetContents.updateGeometry()
            if hasattr(self, 'scrollArea'):
                self.scrollArea.updateGeometry()
            self.updateGeometry()

    def _render_tree(self):
        orgs = self.loader.cache.organizations
        if not orgs:
            self._add_empty("Нет организаций")
            return

        for org in orgs:
            node = self._build_org_node(org)
            node.expand_requested.connect(self.lazy_loader.on_expand_requested)
            self.scrollAreaLayout.addWidget(node)

        self.scrollAreaLayout.addStretch()

    def _render_search_results(self):
        if not self._search_results:
            self._add_empty("Ничего не найдено")
            return

        header = QLabel(f"Результаты поиска: {len(self._search_results)}")
        header.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #1B232A; padding: 6px 2px;"
        )
        self.scrollAreaLayout.addWidget(header)

        for item in self._search_results:
            card = self._build_search_result_card(item)
            if card:
                self.scrollAreaLayout.addWidget(card)

    def _build_search_result_card(self, item):
        print(f"[DEBUG] search item: {item}")
        if not isinstance(item, dict):
            return None

        entity_type = (
                item.get('type') or item.get('entity_type') or item.get('kind') or ''
        ).lower()
        entity_id = item.get('id') or item.get('entity_id')
        name = (
                item.get('name') or item.get('full_name') or item.get('title') or ''
        ).strip()

        path = item.get('path') or item.get('department_path') or ''
        if isinstance(path, list):
            path = ' / '.join(str(p) for p in path)

        is_org = entity_type in ('organization', 'org', 'company')
        is_dept = entity_type in ('department', 'dept', 'division', 'unit')
        is_emp = entity_type in ('employee', 'emp', 'user', 'person')

        if not any((is_org, is_dept, is_emp)):
            if item.get('unp'):
                is_org = True
            elif item.get('position_name') or item.get('position'):
                is_emp = True
            else:
                is_dept = True

        if is_emp:
            full_name = name or ' '.join(filter(None, [
                item.get('last_name', ''),
                item.get('first_name', ''),
                item.get('patronymic', ''),
            ])) or f"Сотрудник #{entity_id}"

            card = EmployeeCard({
                'id': entity_id,
                'display_number': '',
                'full_name': full_name,
                'position': item.get('position_name') or item.get('position') or '',
                'company': item.get('organization_name', ''),
                'department': item.get('department_name', ''),
                'subdivision': path,
                'work_phone': item.get('work_number', ''),
                'email': item.get('email', ''),
                'rights': '',
                '_raw': item,
            })
            card.edit_clicked.connect(self._on_employee_edit_clicked)
            card.delete_clicked.connect(self._on_employee_delete_clicked)

        elif is_org:
            from client.windows.system.organizations.organization_card import OrganizationCard
            phone = item.get('phone_number') or item.get('phone') or ''
            card = OrganizationCard({
                'id': entity_id,
                'name': name,
                'unp': item.get('unp', ''),
                'address': item.get('address', ''),
                'phone': str(phone) if phone else '',
                'email': item.get('email', ''),
                'director': item.get('director', ''),
            })
            card.edit_clicked.connect(self._on_org_card_edit)
            card.delete_clicked.connect(self._on_org_card_delete)

        else:
            from client.windows.system.departments.department_card import DepartmentCard
            card = DepartmentCard({
                'id': entity_id,
                'name': name,
                'code': str(entity_id or ''),
                'leader': item.get('leader', ''),
                'phone': item.get('phone', ''),
                'description': path or item.get('description', ''),
                'type': item.get('department_type_name') or 'Отдел',
                'organization': item.get('organization_name', ''),
            })
            card.edit_clicked.connect(self.on_edit_department)
            card.delete_clicked.connect(self.on_delete_department)

        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return card

    def _build_org_node(self, org):
        from client.windows.system.departments.department_node import DepartmentNode
        return DepartmentNode({
            'id': org.get('id'),
            'name': org.get('name', ''),
            'type_display': 'Организация',
            'code': org.get('code', ''),
            'has_children': True,
            'lazy': True,
            '_raw': org,
        }, is_root=True)

    # ==================== РЕДАКТИРОВАНИЕ ОРГАНИЗАЦИИ ИЗ СТРУКТУРЫ ====================

    def _on_org_card_edit(self, org_data):
        """Редактирование организации из вкладки «Структура»."""
        from client.windows.system.organizations.organization_dialog import OrganizationDialog

        org_id = org_data.get('id')
        if not org_id:
            return
        try:
            server_org = self.loader.org_service.get_organization(org_id) or org_data
            dialog = OrganizationDialog(self, item=server_org)
            if dialog.exec():
                updated = dialog.get_data()
                phone = updated.get('phone_number') or updated.get('phone') or None
                payload = {
                    'name':          updated.get('full_name') or updated.get('name', ''),
                    'full_name':     updated.get('full_name', ''),
                    'short_name':    updated.get('short_name', ''),
                    'unp':           updated.get('unp', ''),
                    'address':       updated.get('address', ''),
                    'phone_number':  str(phone) if phone else None,
                    'email':         updated.get('email', ''),
                    'director':      updated.get('director', ''),
                    'smdo_code':     updated.get('smdo_code', ''),
                    'is_subscriber': updated.get('is_subscriber', False),
                }
                self.loader.org_service.update_organization(org_id, payload)
                # передаём id — подписчики сделают точечное обновление
                self.data_events.organizations_changed.emit(org_id)
                self.show_success_notification(
                    f"Организация «{updated.get('full_name') or updated.get('name')}» обновлена"
                )
                # обновляем себя — полный refetch, т.к. изменились данные узла
                self.load_data()
        except Exception as e:
            print(f"[ERROR] _on_org_card_edit: {e}")
            self.show_error_notification("Не удалось обновить организацию")

    def _on_org_card_delete(self, org_id):
        self.show_info_notification(
            "Удаление организации доступно во вкладке «Организации»"
        )

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
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
                continue
            sub = item.layout()
            if sub is not None:
                self.clear_layout(sub)
                sub.deleteLater()
                continue
            del item

    # ==================== CRUD ДЕЛЕГИРОВАНИЕ ====================

    def on_add_department(self):
        self.crud.add()

    def on_edit_department(self, data):
        self.crud.edit(data)

    def on_delete_department(self, dept_id):
        self.crud.delete(dept_id)

    # ==================== ФИЛЬТР / СОРТ ====================

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
        text = self.searchEdit.text().strip() if hasattr(self, 'searchEdit') else ''
        if not text and self._search_mode:
            self._search_mode = False
            self._search_results = []
        self.update_reset_button_visibility()
        self.update_display()

    def has_active_filters(self):
        if self._search_mode:
            return True
        return self.filter.current_sort != "А→Я"

    def reset_all_filters(self):
        if hasattr(self, 'searchEdit'):
            self.searchEdit.clear()
        self._search_mode = False
        self._search_results = []
        self.filter.current_sort = "А→Я"
        if hasattr(self, 'btnSort'):
            self.btnSort.setText("Сортировка ▼")
        if hasattr(self, 'btnResetFilters'):
            self.btnResetFilters.hide()
        self.update_display()

    def update_reset_button_visibility(self):
        if hasattr(self, 'btnResetFilters'):
            self.btnResetFilters.setVisible(self.has_active_filters())

    # ==================== ЛЕНИВАЯ ЗАГРУЗКА ====================

    def _on_node_expand_requested(self, node):
        self.lazy_loader.on_expand_requested(node)
        QTimer.singleShot(0, self._refresh_scroll_area)

    def _refresh_scroll_area(self):
        if hasattr(self, 'scrollAreaWidgetContents'):
            self.scrollAreaWidgetContents.updateGeometry()
            if self.scrollAreaWidgetContents.layout():
                self.scrollAreaWidgetContents.layout().activate()
            self.scrollAreaWidgetContents.adjustSize()
        if hasattr(self, 'scrollArea'):
            self.scrollArea.updateGeometry()
        self.updateGeometry()

    # ==================== КАРТОЧКА СОТРУДНИКА ====================

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
            "_raw": emp_data,
        })
        card.edit_clicked.connect(self._on_employee_edit_clicked)
        card.delete_clicked.connect(self._on_employee_delete_clicked)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return card

    def _on_employee_edit_clicked(self, emp_data: dict):
        import inspect
        from client.windows.system.employees.employee_dialog import EmployeeDialog

        emp_id = emp_data.get('id') or emp_data.get('employee_id')
        raw = emp_data.get('_raw') or emp_data
        print(f"👤 Клик по сотруднику id={emp_id}")

        try:
            sig = inspect.signature(EmployeeDialog.__init__)
            params = list(sig.parameters.keys())
            print(f"[DEBUG] EmployeeDialog.__init__ параметры: {params}")

            attempts = [
                lambda: EmployeeDialog(self, employee_id=emp_id),
                lambda: EmployeeDialog(self, emp_id=emp_id),
                lambda: EmployeeDialog(self, employee=raw),
                lambda: EmployeeDialog(self, data=raw),
                lambda: EmployeeDialog(self, employee_data=raw),
                lambda: EmployeeDialog(self, profile_manager=None),
                lambda: EmployeeDialog(self, parent=self),
                lambda: EmployeeDialog(self),
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