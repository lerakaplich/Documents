# client/core/settings/settings_manager.py

import json
import os
from typing import Any

from .settings_keys import SettingsKeys


class SettingsManager:
    """Менеджер локальных настроек клиента с поддержкой разных типов документов"""

    _instance = None
    _current_document_type = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.settings_dir = os.path.join(os.path.expanduser("~"), ".documents_app")
        self.settings_file = os.path.join(self.settings_dir, "settings.json")

        os.makedirs(self.settings_dir, exist_ok=True)
        self._settings = self._load_settings()
        print(f"[SettingsManager] Settings file: {self.settings_file}")

    def _load_settings(self) -> dict:
        """Загрузка настроек из JSON файла"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
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
        """Установить текущий тип документа для настроек колонок"""
        self._current_document_type = str(doc_type) if doc_type else "default"
        print(f"[SettingsManager] Current document type: {self._current_document_type}")

    def get_current_document_type(self) -> str:
        """Получить текущий тип документа"""
        return self._current_document_type or "default"

    def _get_type_key(self, base_key: str, doc_type: str = None) -> str:
        """Получить ключ с типом документа"""
        if doc_type is None:
            doc_type = self.get_current_document_type()
        return SettingsKeys.get_type_key(base_key, doc_type)

    # ============ ГЛОБАЛЬНЫЕ НАСТРОЙКИ ============

    def get_row_order(self) -> list:
        """Получить порядок строк (глобально)"""
        return self.get(SettingsKeys.ROW_ORDER, [])

    def set_row_order(self, order: list):
        """Сохранить порядок строк (глобально)"""
        self.set(SettingsKeys.ROW_ORDER, order)

    # ============ НАСТРОЙКИ ПО ТИПУ ДОКУМЕНТА ============

    # --- Закрепленные документы ---

    def get_pinned_ids(self, doc_type: str = None) -> list:
        """Получить закрепленные ID документов для типа"""
        key = self._get_type_key(SettingsKeys.PINNED, doc_type)
        return self.get(key, [])

    def set_pinned_ids(self, ids: list, doc_type: str = None):
        """Сохранить закрепленные ID документов для типа"""
        key = self._get_type_key(SettingsKeys.PINNED, doc_type)
        self.set(key, ids)

    # --- Высоты строк по ID документа ---

    def get_row_heights(self, doc_type: str = None) -> dict:
        """
        Получить высоты строк для типа документа по ID документа

        Args:
            doc_type: тип документа (если None - используется текущий)

        Returns:
            dict: {str(document_id): height, ...}
        """
        key = self._get_type_key(SettingsKeys.ROW_HEIGHTS, doc_type)
        return self.get(key, {})

    def set_row_heights(self, heights: dict, doc_type: str = None):
        """
        Сохранить высоты строк для типа документа по ID документа

        Args:
            heights: {str(document_id): height, ...}
            doc_type: тип документа (если None - используется текущий)
        """
        key = self._get_type_key(SettingsKeys.ROW_HEIGHTS, doc_type)
        self.set(key, heights)

    # --- Порядок колонок ---

    def get_column_order(self, doc_type: str = None) -> list:
        """Получить порядок колонок для типа документа"""
        key = self._get_type_key(SettingsKeys.COLUMN_ORDER, doc_type)
        return self.get(key, [])

    def set_column_order(self, order: list, doc_type: str = None):
        """Сохранить порядок колонок для типа документа"""
        key = self._get_type_key(SettingsKeys.COLUMN_ORDER, doc_type)
        self.set(key, order)

    # --- Ширина колонок ---

    def get_column_widths(self, doc_type: str = None) -> dict:
        """Получить ширины колонок для типа документа"""
        key = self._get_type_key(SettingsKeys.COLUMN_WIDTHS, doc_type)
        return self.get(key, {})

    def set_column_widths(self, widths: dict, doc_type: str = None):
        """Сохранить ширины колонок для типа документа"""
        key = self._get_type_key(SettingsKeys.COLUMN_WIDTHS, doc_type)
        self.set(key, widths)

    # --- Скрытые колонки ---

    def get_hidden_columns(self, doc_type: str = None) -> list:
        """Получить скрытые колонки для типа документа"""
        key = self._get_type_key(SettingsKeys.HIDDEN_COLUMNS, doc_type)
        return self.get(key, [])

    def set_hidden_columns(self, hidden: list, doc_type: str = None):
        """Сохранить скрытые колонки для типа документа"""
        key = self._get_type_key(SettingsKeys.HIDDEN_COLUMNS, doc_type)
        self.set(key, hidden)

    # ============ ОЧИСТКА ============

    def clear_settings_for_type(self, doc_type: str):
        """Очистить все настройки для типа документа"""
        keys_to_remove = [
            SettingsKeys.get_type_key(SettingsKeys.PINNED, doc_type),
            SettingsKeys.get_type_key(SettingsKeys.ROW_HEIGHTS, doc_type),
            SettingsKeys.get_type_key(SettingsKeys.COLUMN_ORDER, doc_type),
            SettingsKeys.get_type_key(SettingsKeys.COLUMN_WIDTHS, doc_type),
            SettingsKeys.get_type_key(SettingsKeys.HIDDEN_COLUMNS, doc_type),
        ]
        for key in keys_to_remove:
            if key in self._settings:
                del self._settings[key]
        self._save_settings()
        print(f"[SettingsManager] Cleared all settings for type: {doc_type}")

    def clear_all_settings(self):
        """Очистка всех локальных настроек"""
        self._settings = {}
        self._save_settings()
        print("[SettingsManager] All local settings cleared")

    def print_settings_for_type(self, doc_type: str = None):
        """Вывести настройки для типа документа"""
        if doc_type is None:
            doc_type = self.get_current_document_type()

        print(f"\n=== Settings for document type: {doc_type} ===")
        print(f"  pinned: {self.get_pinned_ids(doc_type)}")
        print(f"  row_heights: {self.get_row_heights(doc_type)}")
        print(f"  column_order: {self.get_column_order(doc_type)}")
        print(f"  column_widths: {self.get_column_widths(doc_type)}")
        print(f"  hidden_columns: {self.get_hidden_columns(doc_type)}")
        print("=====================================\n")

    def print_all_settings(self):
        """Вывод всех настроек в консоль"""
        print("\n=== ALL LOCAL SETTINGS ===")

        # Глобальные настройки
        print(f"  {SettingsKeys.ROW_ORDER}: {self.get(SettingsKeys.ROW_ORDER, [])}")

        # Настройки по типам
        print("\n  === Settings by document type ===")
        for key, value in sorted(self._settings.items()):
            if key.startswith(("pinned_", "row_heights_", "column_order_", "column_widths_", "hidden_columns_")):
                print(f"    {key}: {value}")

        print(f"  Settings file: {self.settings_file}")
        print("==================================\n")