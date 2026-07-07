# client/core/settings/settings_manager.py

import json
import os
from typing import Any

from .settings_keys import SettingsKeys


class SettingsManager:
    """Менеджер локальных настроек клиента с поддержкой разных типов документов"""

    _instance = None
    _current_document_type = None  # Текущий тип документа

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Путь к файлу настроек
        self.settings_dir = os.path.join(os.path.expanduser("~"), ".documents_app")
        self.settings_file = os.path.join(self.settings_dir, "settings.json")

        # Создаем директорию если её нет
        os.makedirs(self.settings_dir, exist_ok=True)

        # Загружаем настройки
        self._settings = self._load_settings()
        print(f"[SettingsManager] Settings file: {self.settings_file}")

    def _load_settings(self) -> dict:
        """Загрузка настроек из JSON файла"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
        except Exception as e:
            print(f"[SettingsManager] Error loading settings: {e}")
        return {}

    def _save_settings(self):
        """Сохранение настроек в JSON файл"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[SettingsManager] Error saving settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение настройки"""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any):
        """Установить значение настройки"""
        self._settings[key] = value
        self._save_settings()

    def remove(self, key: str):
        """Удалить настройку"""
        if key in self._settings:
            del self._settings[key]
            self._save_settings()

    def set_current_document_type(self, doc_type: str):
        """Установить текущий тип документа для настроек"""
        self._current_document_type = doc_type
        print(f"[SettingsManager] Current document type: {doc_type}")

    def get_current_document_type(self) -> str:
        """Получить текущий тип документа"""
        return self._current_document_type or "default"

    def _get_key_with_type(self, base_key: str) -> str:
        """Получить ключ с типом документа"""
        doc_type = self.get_current_document_type()
        return SettingsKeys.get_type_key(base_key, doc_type)

    # ============ ВРЕМЕННО: Закрепленные документы (пока нет БД) ============

    def get_pinned_ids(self) -> list:
        """Получить закрепленные ID (ВРЕМЕННО)"""
        return self.get("pinned_documents", [])

    def set_pinned_ids(self, ids: list):
        """Сохранить закрепленные ID (ВРЕМЕННО)"""
        self.set("pinned_documents", ids)

    # ============ Локальные настройки таблицы ============

    def get_row_order(self) -> list:
        """Получить порядок строк (локально)"""
        return self.get(SettingsKeys.ROW_ORDER, [])

    def set_row_order(self, order: list):
        """Сохранить порядок строк (локально)"""
        self.set(SettingsKeys.ROW_ORDER, order)

    def get_row_heights(self) -> dict:
        """Получить высоты строк (локально)"""
        return self.get(SettingsKeys.ROW_HEIGHTS, {})

    def set_row_heights(self, heights: dict):
        """Сохранить высоты строк (локально)"""
        self.set(SettingsKeys.ROW_HEIGHTS, heights)

    # ============ Настройки колонок с поддержкой типа документа ============

    def get_column_order(self, doc_type: str = None) -> list:
        """
        Получить порядок колонок для конкретного типа документа

        Args:
            doc_type: тип документа (если None - используется текущий)
        """
        if doc_type is None:
            doc_type = self.get_current_document_type()
        key = SettingsKeys.get_type_key(SettingsKeys.COLUMN_ORDER, doc_type)
        return self.get(key, [])

    def set_column_order(self, order: list, doc_type: str = None):
        """
        Сохранить порядок колонок для конкретного типа документа

        Args:
            order: порядок колонок
            doc_type: тип документа (если None - используется текущий)
        """
        if doc_type is None:
            doc_type = self.get_current_document_type()
        key = SettingsKeys.get_type_key(SettingsKeys.COLUMN_ORDER, doc_type)
        self.set(key, order)

    def get_column_widths(self, doc_type: str = None) -> dict:
        """
        Получить ширины колонок для конкретного типа документа

        Args:
            doc_type: тип документа (если None - используется текущий)
        """
        if doc_type is None:
            doc_type = self.get_current_document_type()
        key = SettingsKeys.get_type_key(SettingsKeys.COLUMN_WIDTHS, doc_type)
        return self.get(key, {})

    def set_column_widths(self, widths: dict, doc_type: str = None):
        """
        Сохранить ширины колонок для конкретного типа документа

        Args:
            widths: ширины колонок
            doc_type: тип документа (если None - используется текущий)
        """
        if doc_type is None:
            doc_type = self.get_current_document_type()
        key = SettingsKeys.get_type_key(SettingsKeys.COLUMN_WIDTHS, doc_type)
        self.set(key, widths)

    def get_hidden_columns(self, doc_type: str = None) -> list:
        """
        Получить скрытые колонки для конкретного типа документа

        Args:
            doc_type: тип документа (если None - используется текущий)
        """
        if doc_type is None:
            doc_type = self.get_current_document_type()
        key = SettingsKeys.get_type_key(SettingsKeys.HIDDEN_COLUMNS, doc_type)
        return self.get(key, [])

    def set_hidden_columns(self, hidden: list, doc_type: str = None):
        """
        Сохранить скрытые колонки для конкретного типа документа

        Args:
            hidden: скрытые колонки
            doc_type: тип документа (если None - используется текущий)
        """
        if doc_type is None:
            doc_type = self.get_current_document_type()
        key = SettingsKeys.get_type_key(SettingsKeys.HIDDEN_COLUMNS, doc_type)
        self.set(key, hidden)

    # ============ Вспомогательные методы ============

    def print_all_settings(self):
        """Вывод всех настроек в консоль"""
        print("\n=== LOCAL SETTINGS (UI only) ===")
        keys = [
            "pinned_documents",
            SettingsKeys.ROW_ORDER,
            SettingsKeys.ROW_HEIGHTS,
            f"{SettingsKeys.COLUMN_ORDER}_*",
            f"{SettingsKeys.COLUMN_WIDTHS}_*",
            f"{SettingsKeys.HIDDEN_COLUMNS}_*",
            SettingsKeys.SORT_COLUMN,
            SettingsKeys.SORT_ORDER
        ]

        for key in keys:
            value = self.get(key, "<not set>")
            print(f"  {key}: {value}")

        print(f"  Settings file: {self.settings_file}")
        print("==================================\n")

    def clear_all_settings(self):
        """Очистка всех локальных настроек"""
        self._settings = {}
        self._save_settings()
        print("[SettingsManager] All local settings cleared")

    def clear_settings_for_type(self, doc_type: str):
        """Очистить настройки для конкретного типа документа"""
        keys_to_remove = [
            SettingsKeys.get_type_key(SettingsKeys.COLUMN_ORDER, doc_type),
            SettingsKeys.get_type_key(SettingsKeys.COLUMN_WIDTHS, doc_type),
            SettingsKeys.get_type_key(SettingsKeys.HIDDEN_COLUMNS, doc_type),
        ]
        for key in keys_to_remove:
            if key in self._settings:
                del self._settings[key]
        self._save_settings()
        print(f"[SettingsManager] Cleared settings for type: {doc_type}")