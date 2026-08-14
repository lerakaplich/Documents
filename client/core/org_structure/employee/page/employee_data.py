from PyQt6.QtWidgets import QMessageBox


class EmployeeDataManager:
    """Управление данными сотрудников"""

    def __init__(self):
        self.organizations = {}
        self.departments_tree = {}
        self.employees = {}
        self.employee_positions = []

    def load_test_data(self, page):
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
            {"id": 3, "employee_id": 3, "department_id": 13, "position_name": "Начальник отдела кадров", "is_leader": True},
            {"id": 4, "employee_id": 4, "department_id": 6, "position_name": "Начальник конструкторского отдела", "is_leader": True},
            {"id": 5, "employee_id": 5, "department_id": 7, "position_name": "Начальник технологического отдела", "is_leader": True},
            {"id": 6, "employee_id": 6, "department_id": 16, "position_name": "Ведущий инженер-конструктор", "is_leader": False},
            {"id": 7, "employee_id": 7, "department_id": 10, "position_name": "Главный бухгалтер", "is_leader": True},
            {"id": 8, "employee_id": 8, "department_id": 11, "position_name": "Начальник ПЭО", "is_leader": True},
            {"id": 9, "employee_id": 9, "department_id": 19, "position_name": "Директор", "is_leader": True},
            {"id": 10, "employee_id": 10, "department_id": 21, "position_name": "Главный инженер", "is_leader": True},
            {"id": 11, "employee_id": 11, "department_id": 24, "position_name": "Директор", "is_leader": True},
            {"id": 12, "employee_id": 12, "department_id": 26, "position_name": "Начальник отдела разработок", "is_leader": True},
            {"id": 13, "employee_id": 13, "department_id": 27, "position_name": "Руководитель проектов", "is_leader": False},
        ]

        # Заполняем comboOrganization
        page.comboOrganization.clear()
        page.comboOrganization.addItem("Все организации", None)
        for org_id, org_data in self.organizations.items():
            page.comboOrganization.addItem(org_data["name"], org_id)

        if page.comboOrganization.count() > 1:
            page.comboOrganization.setCurrentIndex(1)

    def get_root_departments(self, org_id):
        """Возвращает корневые подразделения организации"""
        return [
            dept for dept in self.departments_tree.values()
            if dept["organization_id"] == org_id and dept["parent_id"] is None
        ]

    def get_children_departments(self, dept_id):
        """Возвращает список дочерних подразделений"""
        return [
            dept for dept in self.departments_tree.values()
            if dept.get("parent_id") == dept_id
        ]

    def get_department_path(self, department_id):
        """Получить путь подразделения"""
        if not department_id or department_id not in self.departments_tree:
            return ""

        dept = self.departments_tree[department_id]
        path_parts = [dept["name"]]
        current_id = dept["parent_id"]
        while current_id and current_id in self.departments_tree:
            path_parts.insert(0, self.departments_tree[current_id]["name"])
            current_id = self.departments_tree[current_id]["parent_id"]
        return " / ".join(path_parts)

    def get_children_departments_all(self, department_id):
        """Получить все дочерние подразделения (включая вложенные)"""
        children = []
        for dept_id, dept in self.departments_tree.items():
            if dept.get("parent_id") == department_id:
                children.append(dept_id)
                children.extend(self.get_children_departments_all(dept_id))
        return children

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

    def filter_employees(self, current_org_id, current_department_id, search_text, current_sort):
        """Фильтрация сотрудников"""
        all_employees = self.get_employees_with_positions()
        filtered = []

        for emp in all_employees:
            if current_org_id and emp.get("organization_id") != current_org_id:
                continue

            if current_department_id:
                dept_id = emp.get("department_id")
                if dept_id != current_department_id and dept_id not in self.get_children_departments_all(current_department_id):
                    continue

            search = search_text.strip().lower()
            if search:
                full_name = f"{emp.get('last_name', '')} {emp.get('first_name', '')} {emp.get('patronymic', '')}".lower()
                position = emp.get('position_name', '').lower()
                phone = emp.get('phone_number', '').lower()
                work_phone = emp.get('work_number', '').lower()
                if not (search in full_name or search in position or search in phone or search in work_phone):
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
                org_name = self.organizations[org_id]["name"]
                groups.setdefault(org_name, []).append(emp)
        return groups

    def sort_by_name_asc(self, employees):
        return sorted(employees, key=lambda x: f"{x['last_name']} {x['first_name']} {x.get('patronymic', '')}")

    def sort_by_name_desc(self, employees):
        return sorted(employees, key=lambda x: f"{x['last_name']} {x['first_name']} {x.get('patronymic', '')}", reverse=True)

    def sort_by_tab_number(self, employees):
        return sorted(employees, key=lambda x: x.get('service_number', ''))