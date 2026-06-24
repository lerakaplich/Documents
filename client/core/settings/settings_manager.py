"""Управление настройками"""
from PyQt6.QtCore import QSettings
from .settings_keys import SettingsKeys


class SettingsManager:
    """Менеджер настроек"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.settings = QSettings("YourCompany", "DocumentsApp")

    def get(self, key, default=None):
        """Получить значение"""
        return self.settings.value(key, default)

    def set(self, key, value):
        """Установить значение"""
        self.settings.setValue(key, value)

    def remove(self, key):
        """Удалить значение"""
        self.settings.remove(key)

    def get_pinned_ids(self):
        """Получить закрепленные ID"""
        ids = self.get(SettingsKeys.PINNED_DOCUMENTS, [])
        if not isinstance(ids, list):
            ids = []
        return [int(id) for id in ids if id is not None]

    def set_pinned_ids(self, ids):
        """Сохранить закрепленные ID"""
        self.set(SettingsKeys.PINNED_DOCUMENTS, ids)

    def get_row_order(self):
        """Получить порядок строк"""
        order = self.get(SettingsKeys.ROW_ORDER, [])
        if not isinstance(order, list):
            order = []
        return [int(id) for id in order if id is not None]

    def set_row_order(self, order):
        """Сохранить порядок строк"""
        self.set(SettingsKeys.ROW_ORDER, order)