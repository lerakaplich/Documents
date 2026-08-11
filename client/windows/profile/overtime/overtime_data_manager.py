from datetime import datetime
from PyQt6.QtWidgets import QMessageBox


class OvertimeDataManager:
    """Управление загрузкой и фильтрацией данных переработок."""

    def __init__(self, parent=None):
        self.parent = parent
        self.current_filter_department_id = None
        self.my_period = None
        self.all_period = None

    def get_children_departments(self, department_id):
        """Заглушка для получения дочерних отделов."""
        print(f"_get_children_departments called with {department_id}")
        tree = {
            None: [{"id": 1, "name": "Телематика"}, {"id": 2, "name": "Бухгалтерия"}],
            1: [{"id": 3, "name": "НТЦ"}, {"id": 4, "name": "Отдел продаж"}],
            3: [{"id": 5, "name": "Разработки"}, {"id": 6, "name": "Тестирования"}],
            2: [{"id": 7, "name": "Расчётный отдел"}],
        }
        result = tree.get(department_id, [])
        print(f"Returning {result}")
        return result

    def get_all_child_ids(self, dept_id):
        """Рекурсивно собирает все ID подразделений в поддереве."""
        ids = [dept_id]
        children = self.get_children_departments(dept_id)
        for child in children:
            ids.extend(self.get_all_child_ids(child["id"]))
        return ids

    def filter_by_date(self, data_list, start_date, end_date):
        """Фильтрует список по диапазону дат."""
        filtered = []
        for item in data_list:
            try:
                item_date = datetime.strptime(item['date'], "%d.%m.%Y")
                if start_date <= item_date <= end_date:
                    filtered.append(item)
            except ValueError:
                continue
        return filtered

    def get_test_data(self):
        """Возвращает тестовые данные для переработок с уникальными id."""
        my_data = [
            {'id': 1, 'employee_name': 'Иванов Иван', 'department_id': 1, 'created_at': '10.05.2026',
             'description': 'Дедлайн проекта', 'date': '15.05.2026', 'start_time': '18:00',
             'end_time': '20:30', 'duration': 2.5},
            {'id': 2, 'employee_name': 'Иванов Иван', 'department_id': 5, 'created_at': '18.05.2026',
             'description': 'Релиз версии', 'date': '22.05.2026', 'start_time': '17:00',
             'end_time': '20:00', 'duration': 3.0}
        ]
        all_data = [
            {'id': 3, 'employee_name': 'Иванов Иван', 'department_id': 1, 'created_at': '10.05.2026',
             'description': 'Дедлайн проекта', 'date': '15.05.2026', 'start_time': '18:00',
             'end_time': '20:30', 'duration': 2.5},
            {'id': 4, 'employee_name': 'Петров Петр', 'department_id': 2, 'created_at': '12.05.2026',
             'description': 'Консультация', 'date': '16.05.2026', 'start_time': '19:00',
             'end_time': '20:00', 'duration': 1.0},
            {'id': 5, 'employee_name': 'Сидорова Анна', 'department_id': 3, 'created_at': '15.05.2026',
             'description': 'Внеплановые задачи', 'date': '20.05.2026', 'start_time': '18:00',
             'end_time': '22:00', 'duration': 4.0},
            {'id': 6, 'employee_name': 'Иванов Иван', 'department_id': 5, 'created_at': '18.05.2026',
             'description': 'Релиз версии', 'date': '22.05.2026', 'start_time': '17:00',
             'end_time': '20:00', 'duration': 3.0}
        ]
        return my_data, all_data

    def get_overtime_by_id(self, overtime_id):
        my_data, all_data = self.get_test_data()
        all_items = my_data + all_data
        for item in all_items:
            if item.get('id') == overtime_id:
                return item
        return None

    def filter_data(self, my_data, all_data, filter_department_id=None, start_date_str=None, end_date_str=None):
        """Фильтрует данные по отделу и датам."""
        # Фильтрация по отделам
        if filter_department_id is not None:
            print(f"Применяем фильтр по отделу ID: {filter_department_id}")
            all_ids = self.get_all_child_ids(filter_department_id)
            all_data = [item for item in all_data if item.get('department_id') in all_ids]
            my_data = [item for item in my_data if item.get('department_id') in all_ids]

        # Фильтрация по датам
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%d.%m.%Y")
                end_date = datetime.strptime(end_date_str, "%d.%m.%Y")
                all_data = self.filter_by_date(all_data, start_date, end_date)
                my_data = self.filter_by_date(my_data, start_date, end_date)
                print(f"После фильтрации по датам: all_data={len(all_data)}, my_data={len(my_data)}")
            except ValueError as e:
                print(f"Ошибка парсинга дат: {e}")

        return my_data, all_data

