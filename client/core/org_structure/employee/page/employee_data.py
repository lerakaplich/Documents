# client/core/org_structure/employee/page/employee_data.py
from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import QMessageBox
from client.services.service_factory import ServiceFactory
from client.core.config import config


class EmployeeDataManager:
    """Управление данными сотрудников с поддержкой API"""

    def __init__(self):
        self.organizations = {}
        self.departments_tree = {}
        self.employees = {}
        self.employee_positions = []

        # Флаги для отслеживания загрузки
        self._is_loaded = False
        self._org_service = None
        self._employee_service = None

    @property
    def org_service(self):
        if self._org_service is None:
            self._org_service = ServiceFactory.get_org_service()
        return self._org_service

    @property
    def employee_service(self):
        if self._employee_service is None:
            self._employee_service = ServiceFactory.get_employee_service()
        return self._employee_service

    def load_data_from_api(self, page) -> bool:
        """Загрузка данных из API"""
        try:
            # Загружаем организации
            orgs_data = self.org_service.get_organizations()
            self.organizations = {
                org["id"]: org for org in orgs_data
            }

            # Загружаем все подразделения
            depts_data = self.org_service.get_departments()
            self.departments_tree = {
                dept["id"]: dept for dept in depts_data
            }

            # Загружаем сотрудников (с пагинацией)
            all_employees = []
            page_num = 1
            limit = 100

            while True:
                response = self.employee_service.get_all_employees(
                    page=page_num,
                    limit=limit,
                    show_fired=False
                )

                # Обрабатываем ответ
                if isinstance(response, dict):
                    items = response.get("items", [])
                    all_employees.extend(items)

                    # Проверяем, есть ли еще страницы
                    total = response.get("total", 0)
                    if page_num * limit >= total:
                        break
                    page_num += 1
                else:
                    # Если ответ - список (старая версия API)
                    all_employees = response
                    break

            # Преобразуем сотрудников в словарь
            self.employees = {}
            for emp in all_employees:
                emp_id = emp.get("id")
                if emp_id:
                    self.employees[emp_id] = emp

            # Формируем должности сотрудников
            self.employee_positions = []
            for emp_id, emp_data in self.employees.items():
                # Если у сотрудника есть position, добавляем его
                position_name = emp_data.get("position") or emp_data.get("position_name")
                if position_name:
                    self.employee_positions.append({
                        "id": emp_id,
                        "employee_id": emp_id,
                        "department_id": emp_data.get("department_id"),
                        "position_name": position_name,
                        "is_leader": emp_data.get("is_leader", False)
                    })

            # Заполняем comboBox организации
            if hasattr(page, 'comboOrganization'):
                page.comboOrganization.clear()
                page.comboOrganization.addItem("Все организации", None)
                for org_id, org_data in self.organizations.items():
                    page.comboOrganization.addItem(
                        org_data.get("name", f"Организация {org_id}"),
                        org_id
                    )

                if page.comboOrganization.count() > 1:
                    page.comboOrganization.setCurrentIndex(1)

            self._is_loaded = True
            return True

        except Exception as e:
            # Логируем ошибку, но не показываем пользователю,
            # т.к. будет использоваться fallback с тестовыми данными
            print(f"Ошибка загрузки данных из API: {e}")
            return False

    def load_test_data(self, page):
        """Загрузка тестовых данных (резервный вариант)"""
        # Сохраняем ваш существующий код load_test_data здесь
        # ... (весь код тестовых данных из вашего файла)

        # Пример минимального набора тестовых данных:
        self.organizations = {
            1: {"id": 1, "unp": "100123456", "name": "ОАО МАЗ"},
            2: {"id": 2, "unp": "200234567", "name": "ООО МАЗ-Кузовной"},
            3: {"id": 3, "unp": "300345678", "name": "СООО МАЗ-МАН"}
        }

        # Добавьте остальные тестовые данные из вашего файла...
        # (скопируйте сюда код из вашего существующего метода load_test_data)

        # Заполняем comboBox
        if hasattr(page, 'comboOrganization'):
            page.comboOrganization.clear()
            page.comboOrganization.addItem("Все организации", None)
            for org_id, org_data in self.organizations.items():
                page.comboOrganization.addItem(org_data.get("name", f"Организация {org_id}"), org_id)

            if page.comboOrganization.count() > 1:
                page.comboOrganization.setCurrentIndex(1)

    def refresh_data(self, page) -> bool:
        """Обновить данные из API"""
        self._is_loaded = False
        success = self.load_data_from_api(page)
        if not success:
            self.load_test_data(page)
        return success

    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С ДАННЫМИ ====================
    # (оставляем все существующие методы без изменений)

    def get_root_departments(self, org_id):
        """Возвращает корневые подразделения организации"""
        return [
            dept for dept in self.departments_tree.values()
            if dept.get("organization_id") == org_id and dept.get("parent_id") is None
        ]

    def get_children_departments(self, dept_id):
        """Возвращает список дочерних подразделений"""
        return [
            dept for dept in self.departments_tree.values()
            if dept.get("parent_id") == dept_id
        ]

    def get_children_departments_all(self, department_id):
        """Получить все дочерние подразделения (включая вложенные)"""
        children = []
        for dept_id, dept in self.departments_tree.items():
            if dept.get("parent_id") == department_id:
                children.append(dept_id)
                children.extend(self.get_children_departments_all(dept_id))
        return children

    def get_department_path(self, department_id):
        """Получить путь подразделения"""
        if not department_id or department_id not in self.departments_tree:
            return ""

        dept = self.departments_tree[department_id]
        path_parts = [dept.get("name", "")]
        current_id = dept.get("parent_id")

        while current_id and current_id in self.departments_tree:
            parent = self.departments_tree[current_id]
            path_parts.insert(0, parent.get("name", ""))
            current_id = parent.get("parent_id")

        return " / ".join(path_parts)

    def get_employees_with_positions(self):
        """Получить всех сотрудников с их должностями и подразделениями"""
        result = []

        for emp_id, emp_data in self.employees.items():
            # Ищем должность сотрудника
            position = None
            for pos in self.employee_positions:
                if pos.get("employee_id") == emp_id:
                    position = pos
                    break

            emp_copy = emp_data.copy()

            if position:
                emp_copy["position_name"] = position.get("position_name", "")
                emp_copy["department_id"] = position.get("department_id")
                emp_copy["is_leader"] = position.get("is_leader", False)

                dept_id = position.get("department_id")
                if dept_id and dept_id in self.departments_tree:
                    dept = self.departments_tree[dept_id]
                    emp_copy["department_name"] = dept.get("name", "")
                    emp_copy["organization_id"] = dept.get("organization_id")
                    emp_copy["department_path"] = self.get_department_path(dept_id)
            else:
                emp_copy["position_name"] = ""
                emp_copy["department_id"] = None
                emp_copy["is_leader"] = False

            result.append(emp_copy)

        return result

    def filter_employees(self, current_org_id, current_department_id, search_text, current_sort):
        """Фильтрация сотрудников"""
        all_employees = self.get_employees_with_positions()
        filtered = []

        for emp in all_employees:
            if current_org_id and emp.get("organization_id") != current_org_id:
                continue

            if current_department_id:
                dept_id = emp.get("department_id")
                if dept_id != current_department_id and dept_id not in self.get_children_departments_all(
                        current_department_id):
                    continue

            search = search_text.strip().lower()
            if search:
                full_name = f"{emp.get('last_name', '')} {emp.get('first_name', '')} {emp.get('patronymic', '')}".lower()
                position = emp.get('position_name', '').lower()
                phone = emp.get('phone_number', '').lower()
                work_phone = emp.get('work_number', '').lower()
                email = emp.get('email', '').lower()

                if not (
                        search in full_name or search in position or search in phone or search in work_phone or search in email):
                    continue

            filtered.append(emp)

        sort_methods = {
            "А→Я": self.sort_by_name_asc,
            "Я→А": self.sort_by_name_desc,
            "по табельному номеру": self.sort_by_tab_number
        }
        sort_func = sort_methods.get(current_sort, self.sort_by_name_asc)
        return sort_func(filtered)

    def group_by_organization(self, employees):
        """Группировка сотрудников по организациям"""
        groups = {}
        for emp in employees:
            org_id = emp.get("organization_id")
            if org_id and org_id in self.organizations:
                org_name = self.organizations[org_id].get("name", f"Организация {org_id}")
                groups.setdefault(org_name, []).append(emp)
            else:
                groups.setdefault("Без организации", []).append(emp)
        return groups

    def sort_by_name_asc(self, employees):
        return sorted(
            employees,
            key=lambda x: f"{x.get('last_name', '')} {x.get('first_name', '')} {x.get('patronymic', '')}"
        )

    def sort_by_name_desc(self, employees):
        return sorted(
            employees,
            key=lambda x: f"{x.get('last_name', '')} {x.get('first_name', '')} {x.get('patronymic', '')}",
            reverse=True
        )

    def sort_by_tab_number(self, employees):
        return sorted(employees, key=lambda x: x.get('service_number', ''))