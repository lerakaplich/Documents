# client/core/state/data_events.py

from PyQt6.QtCore import QObject, pyqtSignal


class DataEvents(QObject):
    organizations_changed = pyqtSignal(int)  # org_id (0 = «не знаю какой»)
    departments_changed = pyqtSignal(int)  # dept_id
    employees_changed = pyqtSignal(int)  # emp_id

    # НОВОЕ: смена контактов текущего пользователя.
    # Передаём словарь с полями, которые изменились:
    #   {"phone_number": "+375...", "email": "..."} — может быть частично.
    profile_changed = pyqtSignal(dict)


_instance: DataEvents | None = None


def get_data_events() -> DataEvents:
    global _instance
    if _instance is None:
        _instance = DataEvents()
    return _instance
