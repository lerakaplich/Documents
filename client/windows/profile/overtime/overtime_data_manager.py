# client/windows/profile/overtime/overtime_data_manager.py
from datetime import datetime
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import QMessageBox

from client.services.overtime_service import OvertimeService


class OvertimeDataManager:
    """Управление загрузкой и фильтрацией данных переработок."""

    def __init__(self, parent=None):
        self.parent = parent
        self.current_filter_department_id = None
        self.my_period = None
        self.all_period = None
        self.overtime_service = None
        self._cache_my_data = []
        self._cache_all_data = []
        self._departments_cache = None

    def set_overtime_service(self, overtime_service: OvertimeService):
        """Устанавливает сервис переработок"""
        self.overtime_service = overtime_service
        print("✅ OvertimeService установлен в OvertimeDataManager")

    def load_overtime_from_api(self):
        """Загружает переработки через API"""
        if not self.overtime_service:
            print("⚠️ OvertimeService не установлен, используем тестовые данные")
            return self.get_test_data()

        try:
            my_data = self.overtime_service.get_my_overtime()
            all_data = self.overtime_service.get_all_overtime()

            # Преобразуем данные в формат для отображения
            my_formatted = self._format_overtime_data(my_data)
            all_formatted = self._format_overtime_data(all_data)

            self._cache_my_data = my_formatted
            self._cache_all_data = all_formatted

            return my_formatted, all_formatted
        except Exception as e:
            print(f"❌ Ошибка загрузки переработок: {e}")
            return self.get_test_data()

    def _format_overtime_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Форматирует данные переработок для отображения"""
        formatted = []
        for item in data:
            # Получаем информацию о сотруднике
            employee = item.get('employee', {})
            department = item.get('department', {})

            # Форматируем дату
            overtime_date = item.get('overtime_date')
            if overtime_date:
                try:
                    dt = datetime.fromisoformat(overtime_date)
                    date_str = dt.strftime('%d.%m.%Y')
                except:
                    date_str = str(overtime_date)
            else:
                date_str = ''

            # Форматируем время
            start_time = item.get('overtime_start')
            end_time = item.get('overtime_end')
            if start_time:
                start_time = start_time[:5] if len(start_time) > 5 else start_time
            if end_time:
                end_time = end_time[:5] if len(end_time) > 5 else end_time

            # Вычисляем длительность
            duration = 0
            if start_time and end_time:
                try:
                    start = datetime.strptime(start_time, '%H:%M')
                    end = datetime.strptime(end_time, '%H:%M')
                    duration = (end - start).seconds / 3600.0
                except:
                    pass

            formatted.append({
                'id': item.get('id'),
                'employee_name': f"{employee.get('last_name', '')} {employee.get('first_name', '')}".strip(),
                'department_id': department.get('id'),
                'department_name': department.get('name', ''),
                'created_at': date_str,  # или используем другое поле
                'description': item.get('note_text', ''),
                'date': date_str,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'raw_data': item  # сохраняем оригинальные данные для редактирования
            })
        return formatted

    def get_children_departments(self, department_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Возвращает список дочерних отделов для иерархического фильтра
        Заглушка - в реальном приложении нужно загружать с сервера
        """
        print(f"_get_children_departments called with {department_id}")

        # Если кэш пуст, загружаем структуру отделов
        if self._departments_cache is None:
            self._load_departments_structure()

        # Возвращаем дочерние отделы
        if department_id is None:
            # Корневые отделы
            return [dept for dept in self._departments_cache.values() if dept.get('parent_id') is None]
        else:
            # Дочерние отделы
            return [dept for dept in self._departments_cache.values()
                    if dept.get('parent_id') == department_id]

    def _load_departments_structure(self):
        """Загружает структуру отделов (заглушка)"""
        # В реальном приложении нужно загружать с сервера через DepartmentService
        self._departments_cache = {
            1: {"id": 1, "name": "Управление информационных технологий", "parent_id": None},
            2: {"id": 2, "name": "Отдел разработки", "parent_id": 1},
            3: {"id": 3, "name": "Сектор фронтенда", "parent_id": 2},
            4: {"id": 4, "name": "Сектор бэкенда", "parent_id": 2},
            5: {"id": 5, "name": "Отдел тестирования", "parent_id": 1},
            6: {"id": 6, "name": "Бухгалтерия", "parent_id": None},
            7: {"id": 7, "name": "Отдел продаж", "parent_id": None},
        }

    def get_all_child_ids(self, dept_id: int) -> List[int]:
        """Рекурсивно собирает все ID подразделений в поддереве."""
        ids = [dept_id]
        children = self.get_children_departments(dept_id)
        for child in children:
            ids.extend(self.get_all_child_ids(child["id"]))
        return ids

    def filter_by_date(self, data_list: List[Dict], start_date: datetime, end_date: datetime) -> List[Dict]:
        """Фильтрует список по диапазону дат."""
        filtered = []
        for item in data_list:
            try:
                item_date = datetime.strptime(item['date'], "%d.%m.%Y")
                if start_date <= item_date <= end_date:
                    filtered.append(item)
            except (ValueError, KeyError):
                continue
        return filtered

    def get_test_data(self) -> tuple:
        """Возвращает тестовые данные для переработок с уникальными id."""
        my_data = [
            {'id': 1, 'employee_name': 'Иванов Иван', 'department_id': 1,
             'created_at': '10.05.2026', 'description': 'Дедлайн проекта',
             'date': '15.05.2026', 'start_time': '18:00', 'end_time': '20:30',
             'duration': 2.5},
            {'id': 2, 'employee_name': 'Иванов Иван', 'department_id': 2,
             'created_at': '18.05.2026', 'description': 'Релиз версии',
             'date': '22.05.2026', 'start_time': '17:00', 'end_time': '20:00',
             'duration': 3.0}
        ]
        all_data = [
            {'id': 3, 'employee_name': 'Иванов Иван', 'department_id': 1,
             'created_at': '10.05.2026', 'description': 'Дедлайн проекта',
             'date': '15.05.2026', 'start_time': '18:00', 'end_time': '20:30',
             'duration': 2.5},
            {'id': 4, 'employee_name': 'Петров Петр', 'department_id': 6,
             'created_at': '12.05.2026', 'description': 'Консультация',
             'date': '16.05.2026', 'start_time': '19:00', 'end_time': '20:00',
             'duration': 1.0},
            {'id': 5, 'employee_name': 'Сидорова Анна', 'department_id': 3,
             'created_at': '15.05.2026', 'description': 'Внеплановые задачи',
             'date': '20.05.2026', 'start_time': '18:00', 'end_time': '22:00',
             'duration': 4.0},
            {'id': 6, 'employee_name': 'Иванов Иван', 'department_id': 2,
             'created_at': '18.05.2026', 'description': 'Релиз версии',
             'date': '22.05.2026', 'start_time': '17:00', 'end_time': '20:00',
             'duration': 3.0}
        ]
        return my_data, all_data

    def get_overtime_by_id(self, overtime_id: int) -> Optional[Dict]:
        """Получает переработку по ID из кэша"""
        all_items = self._cache_my_data + self._cache_all_data
        for item in all_items:
            if item.get('id') == overtime_id:
                return item
        return None

    def filter_data(self, my_data: List[Dict], all_data: List[Dict],
                    filter_department_id: Optional[int] = None,
                    start_date_str: Optional[str] = None,
                    end_date_str: Optional[str] = None) -> tuple:
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

    def refresh_data(self) -> tuple:
        """Обновляет данные из API"""
        if self.overtime_service:
            return self.load_overtime_from_api()
        return self.get_test_data()