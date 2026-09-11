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
        self._my_pagination = {'page': 1, 'pages': 1, 'total': 0, 'size': 100}
        self._all_pagination = {'page': 1, 'pages': 1, 'total': 0, 'size': 100}

    def set_overtime_service(self, overtime_service: OvertimeService):
        """Устанавливает сервис переработок"""
        self.overtime_service = overtime_service
        print("✅ OvertimeService установлен в OvertimeDataManager")

    def load_overtime_from_api(self, my_start=None, my_end=None,
                               all_start=None, all_end=None,
                               my_page=1, all_page=1, page_size=100):
        if not self.overtime_service:
            print("⚠️ OvertimeService не установлен, используем тестовые данные")
            return self.get_test_data()

        api_my_start = self._to_iso(my_start) or "2000-01-01"
        api_my_end = self._to_iso(my_end) or "2100-01-01"
        api_all_start = self._to_iso(all_start) or "2000-01-01"
        api_all_end = self._to_iso(all_end) or "2100-01-01"

        try:
            my_resp = self.overtime_service.get_my_overtime(
                api_my_start, api_my_end, page=my_page, size=page_size)
            all_resp = self.overtime_service.get_all_overtime(
                api_all_start, api_all_end, page=all_page, size=page_size)

            # ─── Сохраняем метаданные пагинации ───
            self._my_pagination = {
                'page': my_resp.get('page', 1),
                'pages': my_resp.get('pages', 1),
                'total': my_resp.get('total', 0),
                'size': my_resp.get('size', page_size),
            }
            self._all_pagination = {
                'page': all_resp.get('page', 1),
                'pages': all_resp.get('pages', 1),
                'total': all_resp.get('total', 0),
                'size': all_resp.get('size', page_size),
            }

            my_formatted = self._format_overtime_data(my_resp.get('items', []))
            all_formatted = self._format_overtime_data(all_resp.get('items', []))

            self._cache_my_data = my_formatted
            self._cache_all_data = all_formatted

            return my_formatted, all_formatted
        except Exception as e:
            print(f"❌ Ошибка загрузки переработок: {e}")
            return self.get_test_data()

    def get_my_pagination(self):
        return self._my_pagination.copy()

    def get_all_pagination(self):
        return self._all_pagination.copy()

    @staticmethod
    def _to_iso(date_str: Optional[str]) -> Optional[str]:
        """'10.09.2026' -> '2026-09-10'"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
        except ValueError:
            return None

    def _format_overtime_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Форматирует данные переработок для отображения (под схему API)."""
        if isinstance(data, dict):
            data = data.get('items', [])
        if not isinstance(data, list):
            return []

        formatted = []
        for item in data:
            # Дата
            overtime_date = item.get('overtime_date')
            date_str = ''
            if overtime_date:
                try:
                    dt = datetime.fromisoformat(str(overtime_date).replace('Z', '+00:00'))
                    date_str = dt.strftime('%d.%m.%Y')
                except Exception:
                    date_str = str(overtime_date)

            # Время: сервер может вернуть '18:00:00' или '18:00:00.000Z'
            start_time = item.get('overtime_start') or ''
            end_time = item.get('overtime_end') or ''
            start_time = start_time[:5] if len(start_time) >= 5 else start_time
            end_time = end_time[:5] if len(end_time) >= 5 else end_time

            # Длительность
            duration = 0.0
            if start_time and end_time:
                try:
                    s = datetime.strptime(start_time, '%H:%M')
                    e = datetime.strptime(end_time, '%H:%M')
                    duration = (e - s).seconds / 3600.0
                except Exception:
                    pass

            # ФИО — сервер отдаёт готовое поле full_name
            full_name = item.get('full_name') or ''

            formatted.append({
                'id': item.get('id'),
                'employee_id': item.get('employee_id'),
                'employee_name': full_name,
                'department_id': item.get('department_id'),  # в ответе может не быть
                'department_name': item.get('department_name', ''),
                'created_at': date_str,
                'description': item.get('note_text', '') or '',
                'date': date_str,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'raw_data': item,
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
                    filter_department_id: Optional[int] = None) -> tuple:
        """Фильтрует данные только по отделу. Даты — серверная ответственность."""
        if filter_department_id is not None:
            print(f"Применяем фильтр по отделу ID: {filter_department_id}")
            all_ids = self.get_all_child_ids(filter_department_id)
            all_data = [item for item in all_data if item.get('department_id') in all_ids]
            my_data = [item for item in my_data if item.get('department_id') in all_ids]

        return my_data, all_data

    def refresh_data(self) -> tuple:
        """Обновляет данные из API"""
        if self.overtime_service:
            return self.load_overtime_from_api()
        return self.get_test_data()