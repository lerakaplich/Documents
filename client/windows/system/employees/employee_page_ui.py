import os
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QMenu, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

from client.core.filtering.hierarchical_department_filter import HierarchicalDepartmentFilter
from client.windows.animations.collapsible_group import CollapsibleGroup
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.system.employees.employee_card import EmployeeCard


class EmployeeUIInitializer:
    """Инициализация UI для страницы сотрудников"""

    def __init__(self, page):
        self.page = page

    def init_ui(self):
        """Инициализация UI"""
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self.page)

            # Создаем иерархический фильтр
            self.page.department_filter = HierarchicalDepartmentFilter()
            self.page.department_filter.selectionChanged.connect(
                self.page.on_department_filter_changed
            )

            # Добавляем фильтр в layout
            if hasattr(self.page, 'dynamicFiltersLayout'):
                self.page.dynamicFiltersLayout.addWidget(self.page.department_filter)
            elif hasattr(self.page, 'dynamicFiltersWidget'):
                if self.page.dynamicFiltersWidget.layout() is None:
                    self.page.dynamicFiltersWidget.setLayout(QHBoxLayout())
                self.page.dynamicFiltersWidget.layout().addWidget(self.page.department_filter)

            # Настройка плавающей кнопки
            self.page.floating_btn = FloatingActionButton(self.page)
            self.page.floating_btn.clicked.connect(self.page.show_add_employee_dialog)

            # Подключаем скролл
            self.page.scrollArea.verticalScrollBar().valueChanged.connect(self.page.on_scroll)

            # Устанавливаем минимальную высоту
            self.page.scrollAreaWidgetContents.setMinimumHeight(
                self.page.scrollArea.height() - 10
            )
            self.page.scrollAreaWidgetContents.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.MinimumExpanding
            )

            # Скрываем кнопку сброса
            self.page.btnResetFilters.hide()

            # Настройка выравнивания
            self.setup_toolbar_alignment()

    def setup_toolbar_alignment(self):
        """Настройка выравнивания элементов тулбара"""
        self.page.dynamicFiltersWidget.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Preferred
        )
        self.page.searchEdit.setMaximumWidth(300)
        self.page.toolbarLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'employees', 'employee_page.ui')
        return os.path.normpath(ui_path)

    def setup_connections(self):
        """Настройка сигналов"""
        self.page.btnSort.clicked.connect(self.page.show_sort_menu)
        self.page.comboOrganization.currentIndexChanged.connect(self.page.on_organization_changed)
        self.page.searchEdit.textChanged.connect(self.page.on_search_changed)
        self.page.btnResetFilters.clicked.connect(self.page.reset_all_filters)

    def show_sort_menu(self):
        """Показать меню сортировки"""
        menu = QMenu(self.page)
        menu.setStyleSheet("""
            QMenu { 
                background-color: white; 
                border: 1px solid #c0c0c0; 
                border-radius: 5px; 
                padding: 5px; 
                color: black;
            }
            QMenu::item { 
                padding: 8px 25px 8px 15px; 
                border-radius: 3px; 
                font-size: 14px; 
            }
            QMenu::item:selected { 
                background-color: #e3f2fd; 
            }
            QMenu::separator { 
                height: 1px; 
                background: #e0e0e0; 
                margin: 5px 10px; 
            }
        """)
        sort_options = {
            "А→Я": self.page.sort_by_name_asc,
            "Я→А": self.page.sort_by_name_desc,
            "по табельному номеру": self.page.sort_by_tab_number
        }

        for name, func in sort_options.items():
            action = menu.addAction(name)
            action.triggered.connect(
                lambda checked, f=func, n=name: self.page.apply_sort(f, n)
            )

        menu.exec(self.page.btnSort.mapToGlobal(self.page.btnSort.rect().bottomLeft()))

    def update_display(self):
        """Обновление отображения сотрудников"""
        # Очищаем scroll area
        while self.page.scrollAreaLayout.count():
            widget = self.page.scrollAreaLayout.takeAt(0).widget()
            if widget:
                widget.deleteLater()

        filtered = self.page.filter_employees()
        groups = self.page.group_by_organization(filtered)

        if self.page.current_org_id and self.page.current_org_id in self.page.data_manager.organizations:
            org_name = self.page.data_manager.organizations[self.page.current_org_id]["name"]
            if org_name in groups:
                groups = {org_name: groups[org_name]}

        org_order = sorted(groups.keys(), key=lambda x: (x != "ОАО МАЗ", x))

        global_counter = 0
        for i, org_name in enumerate(org_order):
            employees = groups[org_name]
            if not employees:
                continue

            is_expanded = False
            if self.page.current_org_id:
                selected_org_name = self.page.data_manager.organizations[self.page.current_org_id]["name"]
                is_expanded = (org_name == selected_org_name)
            else:
                is_expanded = (i == 0)

            group = CollapsibleGroup(org_name, is_expanded)

            if hasattr(group, 'content_layout') and isinstance(group.content_layout, QVBoxLayout):
                group.content_layout.setSpacing(12)
                group.content_layout.setContentsMargins(8, 8, 8, 12)
            elif hasattr(group, 'layout') and isinstance(group.layout, QVBoxLayout):
                group.layout.setSpacing(12)

            for emp in employees:
                global_counter += 1
                full_name = f"{emp.get('last_name', '')} {emp.get('first_name', '')} {emp.get('patronymic', '')}".strip()

                card_data = {
                    "id": emp.get("id"),
                    "display_number": str(global_counter),
                    "full_name": full_name,
                    "position": emp.get("position_name", ""),
                    "company": org_name,
                    "department": emp.get("department_name", ""),
                    "subdivision": emp.get("department_path", ""),
                    "work_phone": emp.get("work_number", ""),
                    "email": emp.get("email", ""),
                    "rights": "Администратор" if emp.get("is_leader") else "Пользователь"
                }

                employee_card = EmployeeCard(card_data)
                emp_id = emp.get('id')

                employee_card.edit_clicked.connect(
                    lambda data, card_data=card_data: self.page.show_edit_employee_dialog(card_data)
                )
                employee_card.delete_clicked.connect(
                    lambda eid, emp_id=emp_id: self.page.show_delete_employee_dialog(emp_id)
                )

                group.add_widget(employee_card)

            self.page.scrollAreaLayout.addWidget(group)

        self.page.scrollAreaLayout.addStretch()
        self.page.scrollAreaLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.page.position_floating_button()

    def has_active_filters(self):
        """Проверяет, есть ли активные фильтры"""
        if self.page.searchEdit.text().strip():
            return True
        if self.page.comboOrganization.currentData() is not None:
            return True
        if self.page.current_sort != "А→Я":
            return True
        if self.page.department_filter.get_selected() is not None:
            return True
        return False

    def update_reset_button_visibility(self):
        """Показать или скрыть кнопку сброса"""
        self.page.btnResetFilters.setVisible(self.has_active_filters())

    def position_floating_button(self):
        """Позиционирование плавающей кнопки"""
        if hasattr(self.page, 'floating_btn'):
            margin = 20
            x = self.page.width() - self.page.floating_btn.width() - margin
            y = self.page.height() - self.page.floating_btn.height() - margin
            self.page.floating_btn.update_base_position(x, y)
            self.page.floating_btn.raise_()

    def on_scroll(self, value):
        """Обработчик скролла"""
        if hasattr(self.page, 'floating_btn'):
            self.page.floating_btn.hide_with_animation()
            self.page.floating_btn.start_hide_timer()