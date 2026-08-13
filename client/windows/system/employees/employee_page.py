import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QLineEdit, QScrollArea, QMenu, QMessageBox, QApplication,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.uic import loadUi

from client.core.filtering.hierarchical_department_filter import HierarchicalDepartmentFilter
from client.windows.animations.collapsible_group import CollapsibleGroup
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.system.employees.employee_card import EmployeeCard
from client.windows.system.employees.employee_dialog import EmployeeDialog  # <-- ДОБАВЛЕНО


# ============================================================
#  Основная страница сотрудников
# ============================================================
class EmployeesPage(QWidget):
    """Страница сотрудников с универсальной иерархией подразделений"""

    # Сигнал для обновления данных (опционально)
    employees_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Тестовые данные согласно структуре БД
        self.organizations = {}
        self.departments_tree = {}
        self.employees = {}
        self.employee_positions = []

        self.current_sort = "А→Я"
        self.current_org_id = None
        self.current_department_id = None

        self.init_ui()
        self.load_test_data()
        self.setup_connections()

        # После загрузки данных — инициализируем фильтр корневыми подразделениями
        self.department_filter.set_children_func(self.get_children_departments_data)
        self.on_organization_changed(0)

        self.update_display()

    def init_ui(self):
        """Инициализация UI"""
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)

            # Создаем иерархический фильтр и вставляем в dynamicFiltersWidget
            self.department_filter = HierarchicalDepartmentFilter()
            self.department_filter.selectionChanged.connect(self.on_department_filter_changed)

            if hasattr(self, 'dynamicFiltersLayout'):
                self.dynamicFiltersLayout.addWidget(self.department_filter)
            else:
                if hasattr(self, 'dynamicFiltersWidget'):
                    if self.dynamicFiltersWidget.layout() is None:
                        self.dynamicFiltersWidget.setLayout(QHBoxLayout())
                    self.dynamicFiltersWidget.layout().addWidget(self.department_filter)

            # Настройка плавающей кнопки - ЗАМЕНЕНО
            self.floating_btn = FloatingActionButton(self)
            self.floating_btn.clicked.connect(self.show_add_employee_dialog)  # <-- ИЗМЕНЕНО

            # Подключаемся к скроллу
            self.scrollArea.verticalScrollBar().valueChanged.connect(self.on_scroll)
            # ========== ДОБАВЬТЕ ЭТО ==========
            # Устанавливаем минимальную высоту для содержимого
            self.scrollAreaWidgetContents.setMinimumHeight(
                self.scrollArea.height() - 10
            )

            # Или используем sizePolicy с приоритетом
            self.scrollAreaWidgetContents.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.MinimumExpanding
            )
            # ==================================
            # Скрываем кнопку сброса при старте
            self.btnResetFilters.hide()

            # Настройка выравнивания
            self.setup_toolbar_alignment()

    def setup_toolbar_alignment(self):
        """Настройка выравнивания элементов тулбара"""
        self.dynamicFiltersWidget.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Preferred
        )
        self.searchEdit.setMaximumWidth(300)
        self.toolbarLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'employees', 'employee_page.ui')
        return os.path.normpath(ui_path)

    def setup_connections(self):
        """Настройка сигналов"""
        self.btnSort.clicked.connect(self.show_sort_menu)
        self.comboOrganization.currentIndexChanged.connect(self.on_organization_changed)
        self.searchEdit.textChanged.connect(self.on_search_changed)
        self.btnResetFilters.clicked.connect(self.reset_all_filters)

    # ======================== НОВЫЕ МЕТОДЫ ========================

    def show_add_employee_dialog(self):
        """Открывает диалог создания нового сотрудника"""
        try:
            # Проверяем, есть ли выбранная организация
            if not self.current_org_id:
                QMessageBox.warning(
                    self,
                    "Организация не выбрана",
                    "Пожалуйста, выберите организацию, в которую хотите добавить сотрудника."
                )
                return

            # Получаем данные о текущей организации
            current_org = self.organizations.get(self.current_org_id)
            if not current_org:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Выбранная организация не найдена."
                )
                return

            # Определяем права пользователя (можно расширить)
            current_user_rights = 'admin'  # По умолчанию админ
            is_organization_head = False
            is_division_head = False
            is_department_head = False

            # Если выбрано подразделение, передаем его ID
            current_department_id = self.current_department_id if self.current_department_id else None

            # Создаем диалог с правильными параметрами
            dialog = EmployeeDialog(
                parent_editor=self,
                employee=None,  # None = создание нового
                is_maz=False,  # Можно определить по организации
                profile_manager=None,  # Если есть менеджер профилей
                current_user_rights=current_user_rights,
                current_user_org_id=self.current_org_id,
                current_user_div_id=None,  # Если есть подразделения
                current_user_dept_id=current_department_id,
                is_organization_head=is_organization_head,
                is_division_head=is_division_head,
                is_department_head=is_department_head,
                filter_external_only=False,
                organization_head_ids=None
            )

            # Подключаем сигналы
            dialog.employee_created.connect(self.on_employee_created)
            dialog.employee_updated.connect(self.on_employee_updated)

            # Показываем диалог
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось открыть диалог создания сотрудника:\n{str(e)}"
            )
            import traceback
            traceback.print_exc()

    def on_employee_created(self, employee_id):
        """Обработчик создания нового сотрудника"""
        QMessageBox.information(
            self,
            "Успешно",
            f"Сотрудник с ID {employee_id} успешно создан!"
        )
        # Обновляем данные
        self.load_test_data()  # Или загружаем из БД
        self.update_display()
        self.employees_updated.emit()

    def on_employee_updated(self, employee_id):
        """Обработчик обновления сотрудника"""
        QMessageBox.information(
            self,
            "Успешно",
            f"Сотрудник с ID {employee_id} успешно обновлен!"
        )
        # Обновляем данные
        self.load_test_data()  # Или загружаем из БД
        self.update_display()
        self.employees_updated.emit()

    # ======================== КОНЕЦ НОВЫХ МЕТОДОВ ========================

    # -------------------- Обработчики --------------------
    def on_search_changed(self):
        """Обработчик изменения текста поиска"""
        self.update_reset_button_visibility()
        self.update_display()

    def on_organization_changed(self, index):
        """Обработчик изменения организации"""
        self.current_org_id = self.comboOrganization.currentData()
        self.current_department_id = None

        if self.current_org_id:
            root_depts = self.get_root_departments(self.current_org_id)
            self.department_filter.set_root_items(root_depts)
        else:
            self.department_filter.clear()

        self.update_reset_button_visibility()
        self.update_display()

    def on_department_filter_changed(self, dept_id):
        """Обработчик изменения иерархического фильтра"""
        self.current_department_id = dept_id
        self.update_reset_button_visibility()
        self.update_display()

    def reset_all_filters(self):
        """Сброс всех фильтров, сортировки и поиска"""
        self.searchEdit.clear()
        self.current_sort = "А→Я"
        self.btnSort.setText("Сортировка ▼")
        self.comboOrganization.setCurrentIndex(0)
        self.current_org_id = None
        self.current_department_id = None
        self.department_filter.reset()
        self.btnResetFilters.hide()
        self.update_display()

    # -------------------- Вспомогательные методы для фильтра --------------------
    def get_root_departments(self, org_id):
        """Возвращает корневые подразделения организации"""
        return [
            dept for dept in self.departments_tree.values()
            if dept["organization_id"] == org_id and dept["parent_id"] is None
        ]

    def get_children_departments_data(self, dept_id):
        """Возвращает список дочерних подразделений"""
        return [
            dept for dept in self.departments_tree.values()
            if dept.get("parent_id") == dept_id
        ]

    # -------------------- Загрузка тестовых данных --------------------
    def load_test_data(self):
        """Загрузка тестовых данных согласно структуре БД"""
        # 1. Организации
        self.organizations = {
            1: {"id": 1, "unp": "100123456", "name": "ОАО МАЗ", "smdo_code": "MAZ_001",
                "phone_number": "+375 17 276-20-20", "address": "г. Минск, ул. Социалистическая, 42",
                "email": "info@maz.by", "is_subscriber": True},
            2: {"id": 2, "unp": "200234567", "name": "ООО МАЗ-Кузовной", "smdo_code": "MAZ_KUZ_001",
                "phone_number": "+375 17 234-56-78", "address": "г. Минск, ул. Промышленная, 15",
                "email": "info@maz-kuzov.by", "is_subscriber": True},
            3: {"id": 3, "unp": "300345678", "name": "СООО МАЗ-МАН", "smdo_code": "MAZ_MAN_001",
                "phone_number": "+375 17 345-67-89", "address": "г. Минск, ул. Инженерная, 8",
                "email": "info@maz-man.by", "is_subscriber": True}
        }

        # 2. Дерево подразделений
        self.departments_tree = {
            1: {"id": 1, "organization_id": 1, "parent_id": None, "name": "Руководство", "level": 0},
            2: {"id": 2, "organization_id": 1, "parent_id": None, "name": "Техническая дирекция", "level": 0},
            3: {"id": 3, "organization_id": 1, "parent_id": None, "name": "Финансовая дирекция", "level": 0},
            4: {"id": 4, "organization_id": 1, "parent_id": None, "name": "Управление персоналом", "level": 0},
            5: {"id": 5, "organization_id": 1, "parent_id": None, "name": "Правовое управление", "level": 0},
            6: {"id": 6, "organization_id": 1, "parent_id": 2, "name": "Конструкторский отдел", "level": 1},
            7: {"id": 7, "organization_id": 1, "parent_id": 2, "name": "Технологический отдел", "level": 1},
            8: {"id": 8, "organization_id": 1, "parent_id": 2, "name": "Отдел главного механика", "level": 1},
            9: {"id": 9, "organization_id": 1, "parent_id": 2, "name": "Отдел главного энергетика", "level": 1},
            10: {"id": 10, "organization_id": 1, "parent_id": 3, "name": "Бухгалтерия", "level": 1},
            11: {"id": 11, "organization_id": 1, "parent_id": 3, "name": "Планово-экономический отдел", "level": 1},
            12: {"id": 12, "organization_id": 1, "parent_id": 3, "name": "Финансовый отдел", "level": 1},
            13: {"id": 13, "organization_id": 1, "parent_id": 4, "name": "Отдел кадров", "level": 1},
            14: {"id": 14, "organization_id": 1, "parent_id": 4, "name": "Отдел развития персонала", "level": 1},
            15: {"id": 15, "organization_id": 1, "parent_id": 4, "name": "Отдел охраны труда", "level": 1},
            16: {"id": 16, "organization_id": 1, "parent_id": 6, "name": "Сектор двигателей", "level": 2},
            17: {"id": 17, "organization_id": 1, "parent_id": 6, "name": "Сектор трансмиссий", "level": 2},
            18: {"id": 18, "organization_id": 1, "parent_id": 6, "name": "Сектор электрооборудования", "level": 2},
            19: {"id": 19, "organization_id": 2, "parent_id": None, "name": "Дирекция", "level": 0},
            20: {"id": 20, "organization_id": 2, "parent_id": None, "name": "Производственная дирекция", "level": 0},
            21: {"id": 21, "organization_id": 2, "parent_id": 20, "name": "Технический отдел", "level": 1},
            22: {"id": 22, "organization_id": 2, "parent_id": 20, "name": "Производственный отдел", "level": 1},
            23: {"id": 23, "organization_id": 2, "parent_id": 20, "name": "Отдел качества", "level": 1},
            24: {"id": 24, "organization_id": 3, "parent_id": None, "name": "Дирекция", "level": 0},
            25: {"id": 25, "organization_id": 3, "parent_id": None, "name": "Техническая дирекция", "level": 0},
            26: {"id": 26, "organization_id": 3, "parent_id": 25, "name": "Отдел разработок", "level": 1},
            27: {"id": 27, "organization_id": 3, "parent_id": 25, "name": "Проектный отдел", "level": 1},
            28: {"id": 28, "organization_id": 3, "parent_id": 25, "name": "Технический отдел", "level": 1},
        }

        # 3. Сотрудники
        self.employees = {
            1: {"id": 1, "service_number": "001", "last_name": "Иванов", "first_name": "Иван",
                "patronymic": "Иванович", "phone_number": "+375 29 123-45-67",
                "work_number": "101", "email": "i.ivanov@maz.by"},
            2: {"id": 2, "service_number": "002", "last_name": "Петров", "first_name": "Петр",
                "patronymic": "Петрович", "phone_number": "+375 29 234-56-78",
                "work_number": "102", "email": "p.petrov@maz.by"},
            3: {"id": 3, "service_number": "003", "last_name": "Сидорова", "first_name": "Анна",
                "patronymic": "Сергеевна", "phone_number": "+375 29 345-67-89",
                "work_number": "103", "email": "a.sidorova@maz.by"},
            4: {"id": 4, "service_number": "004", "last_name": "Козлов", "first_name": "Дмитрий",
                "patronymic": "Андреевич", "phone_number": "+375 29 456-78-90",
                "work_number": "201", "email": "d.kozlov@maz.by"},
            5: {"id": 5, "service_number": "005", "last_name": "Новикова", "first_name": "Ирина",
                "patronymic": "Викторовна", "phone_number": "+375 29 567-89-01",
                "work_number": "202", "email": "i.novikova@maz.by"},
            6: {"id": 6, "service_number": "006", "last_name": "Морозов", "first_name": "Александр",
                "patronymic": "Сергеевич", "phone_number": "+375 29 678-90-12",
                "work_number": "301", "email": "a.morozov@maz.by"},
            7: {"id": 7, "service_number": "007", "last_name": "Волкова", "first_name": "Елена",
                "patronymic": "Михайловна", "phone_number": "+375 29 789-01-23",
                "work_number": "104", "email": "e.volkova@maz.by"},
            8: {"id": 8, "service_number": "008", "last_name": "Соколов", "first_name": "Андрей",
                "patronymic": "Петрович", "phone_number": "+375 29 890-12-34",
                "work_number": "105", "email": "a.sokolov@maz.by"},
            9: {"id": 9, "service_number": "009", "last_name": "Волков", "first_name": "Сергей",
                "patronymic": "Николаевич", "phone_number": "+375 29 567-89-01",
                "work_number": "301", "email": "s.volkov@maz-kuzov.by"},
            10: {"id": 10, "service_number": "010", "last_name": "Лебедев", "first_name": "Виктор",
                 "patronymic": "Викторович", "phone_number": "+375 29 678-90-12",
                 "work_number": "302", "email": "v.lebedev@maz-kuzov.by"},
            11: {"id": 11, "service_number": "011", "last_name": "Новиков", "first_name": "Александр",
                 "patronymic": "Иванович", "phone_number": "+375 29 789-01-23",
                 "work_number": "401", "email": "a.novikov@maz-man.by"},
            12: {"id": 12, "service_number": "012", "last_name": "Смирнов", "first_name": "Константин",
                 "patronymic": "Петрович", "phone_number": "+375 29 890-12-34",
                 "work_number": "402", "email": "k.smirnov@maz-man.by"},
            13: {"id": 13, "service_number": "013", "last_name": "Михайлова", "first_name": "Ольга",
                 "patronymic": "Владимировна", "phone_number": "+375 29 901-23-45",
                 "work_number": "403", "email": "o.mikhailova@maz-man.by"},
        }

        # 4. Должности сотрудников
        self.employee_positions = [
            {"id": 1, "employee_id": 1, "department_id": 1, "position_name": "Генеральный директор", "is_leader": True},
            {"id": 2, "employee_id": 2, "department_id": 2, "position_name": "Главный инженер", "is_leader": True},
            {"id": 3, "employee_id": 3, "department_id": 13, "position_name": "Начальник отдела кадров",
             "is_leader": True},
            {"id": 4, "employee_id": 4, "department_id": 6, "position_name": "Начальник конструкторского отдела",
             "is_leader": True},
            {"id": 5, "employee_id": 5, "department_id": 7, "position_name": "Начальник технологического отдела",
             "is_leader": True},
            {"id": 6, "employee_id": 6, "department_id": 16, "position_name": "Ведущий инженер-конструктор",
             "is_leader": False},
            {"id": 7, "employee_id": 7, "department_id": 10, "position_name": "Главный бухгалтер", "is_leader": True},
            {"id": 8, "employee_id": 8, "department_id": 11, "position_name": "Начальник ПЭО", "is_leader": True},
            {"id": 9, "employee_id": 9, "department_id": 19, "position_name": "Директор", "is_leader": True},
            {"id": 10, "employee_id": 10, "department_id": 21, "position_name": "Главный инженер", "is_leader": True},
            {"id": 11, "employee_id": 11, "department_id": 24, "position_name": "Директор", "is_leader": True},
            {"id": 12, "employee_id": 12, "department_id": 26, "position_name": "Начальник отдела разработок",
             "is_leader": True},
            {"id": 13, "employee_id": 13, "department_id": 27, "position_name": "Руководитель проектов",
             "is_leader": False},
        ]

        # Заполняем comboOrganization
        self.comboOrganization.clear()
        self.comboOrganization.addItem("Все организации", None)
        for org_id, org_data in self.organizations.items():
            self.comboOrganization.addItem(org_data["name"], org_id)

        # Устанавливаем первую организацию как выбранную по умолчанию
        if self.comboOrganization.count() > 1:  # Если есть хотя бы одна организация
            self.comboOrganization.setCurrentIndex(1)  # Индекс 1 - первая организация (индекс 0 - "Все организации")
            # Это автоматически вызовет on_organization_changed(1)

    # -------------------- Сортировка --------------------
    def show_sort_menu(self):
        """Показать меню сортировки"""
        menu = QMenu(self)
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
            "А→Я": self.sort_by_name_asc,
            "Я→А": self.sort_by_name_desc,
            "по табельному номеру": self.sort_by_tab_number
        }

        for name, func in sort_options.items():
            action = menu.addAction(name)
            action.triggered.connect(lambda checked, f=func, n=name: self.apply_sort(f, n))

        menu.exec(self.btnSort.mapToGlobal(self.btnSort.rect().bottomLeft()))

    def apply_sort(self, sort_func, sort_name):
        """Применить сортировку"""
        self.current_sort = sort_name
        self.btnSort.setText(f"Сортировка ▼ ({sort_name})")
        self.update_reset_button_visibility()
        self.update_display()

    def sort_by_name_asc(self, employees):
        return sorted(employees, key=lambda x: f"{x['last_name']} {x['first_name']} {x.get('patronymic', '')}")

    def sort_by_name_desc(self, employees):
        return sorted(employees, key=lambda x: f"{x['last_name']} {x['first_name']} {x.get('patronymic', '')}",
                      reverse=True)

    def sort_by_tab_number(self, employees):
        return sorted(employees, key=lambda x: x.get('service_number', ''))

    # -------------------- Вспомогательные методы для работы с деревом --------------------
    def get_department_path(self, department_id):
        """Получить путь подразделения для отображения"""
        if not department_id or department_id not in self.departments_tree:
            return ""

        dept = self.departments_tree[department_id]
        path_parts = [dept["name"]]
        current_id = dept["parent_id"]
        while current_id and current_id in self.departments_tree:
            path_parts.insert(0, self.departments_tree[current_id]["name"])
            current_id = self.departments_tree[current_id]["parent_id"]
        return " / ".join(path_parts)

    def get_children_departments(self, department_id):
        """Получить все дочерние подразделения (включая вложенные) для фильтрации"""
        children = []
        for dept_id, dept in self.departments_tree.items():
            if dept.get("parent_id") == department_id:
                children.append(dept_id)
                children.extend(self.get_children_departments(dept_id))
        return children

    # -------------------- Фильтрация и группировка --------------------
    def get_employees_with_positions(self):
        """Получить всех сотрудников с их должностями и подразделениями"""
        result = []
        employee_depts = {}
        for pos in self.employee_positions:
            emp_id = pos["employee_id"]
            if emp_id not in employee_depts:
                employee_depts[emp_id] = []
            employee_depts[emp_id].append(pos)

        for emp_id, emp_data in self.employees.items():
            if emp_id in employee_depts:
                for pos in employee_depts[emp_id]:
                    emp_copy = emp_data.copy()
                    emp_copy["position_name"] = pos["position_name"]
                    emp_copy["department_id"] = pos["department_id"]
                    emp_copy["is_leader"] = pos["is_leader"]
                    if pos["department_id"] in self.departments_tree:
                        dept = self.departments_tree[pos["department_id"]]
                        emp_copy["department_name"] = dept["name"]
                        emp_copy["organization_id"] = dept["organization_id"]
                        emp_copy["department_path"] = self.get_department_path(pos["department_id"])
                    result.append(emp_copy)
        return result

    def filter_employees(self):
        """Фильтрация сотрудников"""
        all_employees = self.get_employees_with_positions()
        filtered = []

        for emp in all_employees:
            # Фильтр по организации
            if self.current_org_id and emp.get("organization_id") != self.current_org_id:
                continue

            # Фильтр по подразделению (включая все дочерние)
            if self.current_department_id:
                dept_id = emp.get("department_id")
                if dept_id != self.current_department_id and dept_id not in self.get_children_departments(
                        self.current_department_id):
                    continue

            # Поиск
            search_text = self.searchEdit.text().strip().lower()
            if search_text:
                full_name = f"{emp.get('last_name', '')} {emp.get('first_name', '')} {emp.get('patronymic', '')}".lower()
                position = emp.get('position_name', '').lower()
                phone = emp.get('phone_number', '').lower()
                work_phone = emp.get('work_number', '').lower()
                if not (
                        search_text in full_name or search_text in position or search_text in phone or search_text in work_phone):
                    continue

            filtered.append(emp)

        # Применяем сортировку
        sort_methods = {
            "А→Я": self.sort_by_name_asc,
            "Я→А": self.sort_by_name_desc,
            "по табельному номеру": self.sort_by_tab_number
        }
        sort_func = sort_methods.get(self.current_sort, self.sort_by_name_asc)
        return sort_func(filtered)

    def group_by_organization(self, employees):
        """Группировка сотрудников по организациям"""
        groups = {}
        for emp in employees:
            org_id = emp.get("organization_id")
            if org_id and org_id in self.organizations:
                org_name = self.organizations[org_id]["name"]
                groups.setdefault(org_name, []).append(emp)
        return groups

    # -------------------- Отображение --------------------
    def update_display(self):
        """Обновление отображения сотрудников"""
        # Очищаем scroll area
        while self.scrollAreaLayout.count():
            widget = self.scrollAreaLayout.takeAt(0).widget()
            if widget:
                widget.deleteLater()

        filtered = self.filter_employees()
        groups = self.group_by_organization(filtered)

        if self.current_org_id and self.current_org_id in self.organizations:
            org_name = self.organizations[self.current_org_id]["name"]
            if org_name in groups:
                groups = {org_name: groups[org_name]}

        org_order = sorted(groups.keys(), key=lambda x: (x != "ОАО МАЗ", x))

        global_counter = 0
        for i, org_name in enumerate(org_order):
            employees = groups[org_name]
            if not employees:
                continue

            is_expanded = False
            if self.current_org_id:
                selected_org_name = self.organizations[self.current_org_id]["name"]
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
                employee_card.edit_clicked.connect(
                    lambda data: QMessageBox.information(self, "Информация", "В разработке")
                )
                employee_card.delete_clicked.connect(
                    lambda emp_id: QMessageBox.information(self, "Информация", "В разработке")
                )

                group.add_widget(employee_card)

            self.scrollAreaLayout.addWidget(group)

        # ========== ДОБАВЬТЕ ЭТО ==========
        # Добавляем растягивающийся спейсер в конец
        self.scrollAreaLayout.addStretch()
        # ==================================

        self.scrollAreaLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.position_floating_button()

    # -------------------- Управление кнопкой сброса --------------------
    def has_active_filters(self):
        """Проверяет, есть ли активные фильтры"""
        if self.searchEdit.text().strip():
            return True
        if self.comboOrganization.currentData() is not None:
            return True
        if self.current_sort != "А→Я":
            return True
        if self.department_filter.get_selected() is not None:
            return True
        return False

    def update_reset_button_visibility(self):
        """Показать или скрыть кнопку сброса"""
        self.btnResetFilters.setVisible(self.has_active_filters())

    # -------------------- Плавающая кнопка и скролл --------------------
    def position_floating_button(self):
        """Позиционирование плавающей кнопки в правом нижнем углу"""
        if hasattr(self, 'floating_btn'):
            margin = 20
            x = self.width() - self.floating_btn.width() - margin
            y = self.height() - self.floating_btn.height() - margin
            self.floating_btn.update_base_position(x, y)
            self.floating_btn.raise_()

    def on_scroll(self, value):
        """Обработчик скролла"""
        if hasattr(self, 'floating_btn'):
            self.floating_btn.hide_with_animation()
            self.floating_btn.start_hide_timer()

    def resizeEvent(self, event):
        """Обработчик изменения размера для позиционирования кнопки"""
        super().resizeEvent(event)
        self.position_floating_button()


# Для тестирования
if __name__ == "__main__":
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