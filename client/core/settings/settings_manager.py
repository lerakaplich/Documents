# client/core/settings/settings_manager.py

import json
import os
from typing import Any

from .settings_keys import SettingsKeys
from datetime import datetime  # в начале файла


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

    # --- Порядок строк ---
    def get_row_order(self) -> list:
        return self.get(SettingsKeys.ROW_ORDER, [])

    def set_row_order(self, order: list):
        self.set(SettingsKeys.ROW_ORDER, order)

    # --- Высоты строк ---
    def get_row_heights(self) -> dict:
        return self.get(SettingsKeys.ROW_HEIGHTS, {})

    def set_row_heights(self, heights: dict):
        self.set(SettingsKeys.ROW_HEIGHTS, heights)

    # --- Закрепленные ---
    def get_pinned(self) -> list:
        return self.get(SettingsKeys.PINNED, [])

    def set_pinned(self, ids: list):
        self.set(SettingsKeys.PINNED, ids)

    # --- Скрытые строки ---
    def get_hidden_rows(self) -> list:
        return self.get(SettingsKeys.HIDDEN_ROWS, [])

    def set_hidden_rows(self, rows: list):
        self.set(SettingsKeys.HIDDEN_ROWS, rows)

    # ============ НАСТРОЙКИ ПО ТИПУ ДОКУМЕНТА ============

    # --- Колонки ---
    def get_column_widths(self, doc_type: str = None) -> dict:
        key = self._get_type_key(SettingsKeys.COLUMN_WIDTHS, doc_type)
        return self.get(key, {})

    def set_column_widths(self, widths: dict, doc_type: str = None):
        key = self._get_type_key(SettingsKeys.COLUMN_WIDTHS, doc_type)
        self.set(key, widths)

    def get_hidden_columns(self, doc_type: str = None) -> list:
        key = self._get_type_key(SettingsKeys.HIDDEN_COLUMNS, doc_type)
        return self.get(key, [])

    def set_hidden_columns(self, hidden: list, doc_type: str = None):
        key = self._get_type_key(SettingsKeys.HIDDEN_COLUMNS, doc_type)
        self.set(key, hidden)

    def get_column_order(self, doc_type: str = None) -> list:
        key = self._get_type_key(SettingsKeys.COLUMN_ORDER, doc_type)
        return self.get(key, [])

    def set_column_order(self, order: list, doc_type: str = None):
        key = self._get_type_key(SettingsKeys.COLUMN_ORDER, doc_type)
        self.set(key, order)

    # --- Строки для типа ---
    def get_row_heights_by_type(self, doc_type: str = None) -> dict:
        """Получить высоты строк для типа документа"""
        key = self._get_type_key(SettingsKeys.ROW_HEIGHTS_TYPE, doc_type)
        return self.get(key, {})

    def set_row_heights_by_type(self, heights: dict, doc_type: str = None):
        """Сохранить высоты строк для типа документа"""
        key = self._get_type_key(SettingsKeys.ROW_HEIGHTS_TYPE, doc_type)
        self.set(key, heights)

    def get_row_order_by_type(self, doc_type: str = None) -> list:
        """Получить порядок строк для типа документа"""
        key = self._get_type_key(SettingsKeys.ROW_ORDER_TYPE, doc_type)
        return self.get(key, [])

    def set_row_order_by_type(self, order: list, doc_type: str = None):
        """Сохранить порядок строк для типа документа"""
        key = self._get_type_key(SettingsKeys.ROW_ORDER_TYPE, doc_type)
        self.set(key, order)

    def get_pinned_by_type(self, doc_type: str = None) -> list:
        """Получить закрепленные документы для типа"""
        key = self._get_type_key(SettingsKeys.PINNED_TYPE, doc_type)
        return self.get(key, [])

    def set_pinned_by_type(self, ids: list, doc_type: str = None):
        """Сохранить закрепленные документы для типа"""
        key = self._get_type_key(SettingsKeys.PINNED_TYPE, doc_type)
        self.set(key, ids)

    def get_hidden_rows_by_type(self, doc_type: str = None) -> list:
        """Получить скрытые строки для типа документа"""
        key = self._get_type_key(SettingsKeys.HIDDEN_ROWS_TYPE, doc_type)
        return self.get(key, [])

    def set_hidden_rows_by_type(self, rows: list, doc_type: str = None):
        """Сохранить скрытые строки для типа документа"""
        key = self._get_type_key(SettingsKeys.HIDDEN_ROWS_TYPE, doc_type)
        self.set(key, rows)

    # ============ МЕТОДЫ ДЛЯ СОВМЕСТИМОСТИ ============

    # Для обратной совместимости с существующим кодом
    def get_pinned_ids(self, doc_type: str = None) -> list:
        """Получить закрепленные ID документов (совместимость)"""
        if doc_type:
            return self.get_pinned_by_type(doc_type)
        return self.get_pinned()

    def set_pinned_ids(self, ids: list, doc_type: str = None):
        """Сохранить закрепленные ID документов (совместимость)"""
        if doc_type:
            self.set_pinned_by_type(ids, doc_type)
        else:
            self.set_pinned(ids)

    # ============ ОЧИСТКА ============

    def clear_settings_for_type(self, doc_type: str):
        """Очистить все настройки для типа документа"""
        keys_to_remove = [
            SettingsKeys.get_type_key(SettingsKeys.COLUMN_WIDTHS, doc_type),
            SettingsKeys.get_type_key(SettingsKeys.HIDDEN_COLUMNS, doc_type),
            SettingsKeys.get_type_key(SettingsKeys.COLUMN_ORDER, doc_type),
            SettingsKeys.get_type_key(SettingsKeys.ROW_HEIGHTS_TYPE, doc_type),
            SettingsKeys.get_type_key(SettingsKeys.ROW_ORDER_TYPE, doc_type),
            SettingsKeys.get_type_key(SettingsKeys.PINNED_TYPE, doc_type),
            SettingsKeys.get_type_key(SettingsKeys.HIDDEN_ROWS_TYPE, doc_type),
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
        print(f"  column_widths: {self.get_column_widths(doc_type)}")
        print(f"  hidden_columns: {self.get_hidden_columns(doc_type)}")
        print(f"  column_order: {self.get_column_order(doc_type)}")
        print(f"  row_heights: {self.get_row_heights_by_type(doc_type)}")
        print(f"  row_order: {self.get_row_order_by_type(doc_type)}")
        print(f"  pinned: {self.get_pinned_by_type(doc_type)}")
        print(f"  hidden_rows: {self.get_hidden_rows_by_type(doc_type)}")
        print("=====================================\n")

    def print_all_settings(self):
        """Вывод всех настроек в консоль"""
        print("\n=== ALL LOCAL SETTINGS ===")

        # Глобальные настройки
        print(f"  row_order: {self.get_row_order()}")
        print(f"  row_heights: {self.get_row_heights()}")
        print(f"  pinned: {self.get_pinned()}")
        print(f"  hidden_rows: {self.get_hidden_rows()}")

        # Настройки по типам
        print("\n  === Settings by document type ===")
        for key, value in sorted(self._settings.items()):
            if key.startswith((
                "column_widths_", "hidden_columns_", "column_order_",
                "row_heights_", "row_order_", "pinned_", "hidden_rows_"
            )):
                print(f"    {key}: {value}")

        print(f"  Settings file: {self.settings_file}")
        print("==================================\n")

    # client/core/settings/settings_manager.py

    # Добавить эти методы в класс SettingsManager

    # ============ НОВЫЕ МЕТОДЫ ДЛЯ СОВМЕСТИМОСТИ ============

    def get_row_heights_by_doc_type(self, doc_type: str = None) -> dict:
        """
        Получить высоты строк (совместимость).
        Сначала пытается получить новый формат (по ID),
        если нет - старый (по индексу).
        """
        doc_type = doc_type or self.get_current_document_type()

        # Сначала пробуем новый формат
        new_key = self._get_type_key(SettingsKeys.ROW_HEIGHTS_BY_ID_TYPE, doc_type)
        heights = self.get(new_key, None)

        if heights is not None:
            return heights

        # Если нет - пробуем старый
        old_key = self._get_type_key(SettingsKeys.ROW_HEIGHTS_TYPE, doc_type)
        return self.get(old_key, {})

    def set_row_heights_by_doc_type(self, heights: dict, doc_type: str = None):
        """Сохранить высоты строк для типа документа"""
        doc_type = doc_type or self.get_current_document_type()
        key = self._get_type_key(SettingsKeys.ROW_HEIGHTS_TYPE, doc_type)
        self.set(key, heights)

    def get_row_order_by_doc_type(self, doc_type: str = None) -> list:
        """Получить порядок строк для типа документа"""
        doc_type = doc_type or self.get_current_document_type()

        key = self._get_type_key(SettingsKeys.ROW_ORDER_TYPE, doc_type)
        order = self.get(key, None)

        if order is not None:
            return order

        default_key = self._get_type_key(SettingsKeys.ROW_ORDER_TYPE, "default")
        return self.get(default_key, [])

    def set_row_order_by_doc_type(self, order: list, doc_type: str = None):
        """Сохранить порядок строк для типа документа"""
        doc_type = doc_type or self.get_current_document_type()
        key = self._get_type_key(SettingsKeys.ROW_ORDER_TYPE, doc_type)
        self.set(key, order)

    def get_pinned_by_doc_type(self, doc_type: str = None) -> list:
        """Получить закрепленные документы для типа"""
        doc_type = doc_type or self.get_current_document_type()

        key = self._get_type_key(SettingsKeys.PINNED_TYPE, doc_type)
        pinned = self.get(key, None)

        if pinned is not None:
            return pinned

        default_key = self._get_type_key(SettingsKeys.PINNED_TYPE, "default")
        return self.get(default_key, [])

    def set_pinned_by_doc_type(self, ids: list, doc_type: str = None):
        """Сохранить закрепленные документы для типа"""
        doc_type = doc_type or self.get_current_document_type()
        key = self._get_type_key(SettingsKeys.PINNED_TYPE, doc_type)
        self.set(key, ids)

    def get_hidden_rows_by_doc_type(self, doc_type: str = None) -> list:
        """Получить скрытые строки для типа документа"""
        doc_type = doc_type or self.get_current_document_type()

        key = self._get_type_key(SettingsKeys.HIDDEN_ROWS_TYPE, doc_type)
        hidden = self.get(key, None)

        if hidden is not None:
            return hidden

        default_key = self._get_type_key(SettingsKeys.HIDDEN_ROWS_TYPE, "default")
        return self.get(default_key, [])

    def set_hidden_rows_by_doc_type(self, rows: list, doc_type: str = None):
        """Сохранить скрытые строки для типа документа"""
        doc_type = doc_type or self.get_current_document_type()
        key = self._get_type_key(SettingsKeys.HIDDEN_ROWS_TYPE, doc_type)
        self.set(key, rows)

    # client/core/settings/settings_manager.py

    # Добавить методы в класс SettingsManager:

    # ============ ВЫСОТЫ СТРОК ПО ID ============

    def get_row_heights_by_id(self, doc_type: str = None) -> dict:
        """Получить высоты строк по ID документа"""
        key = self._get_type_key(SettingsKeys.ROW_HEIGHTS_BY_ID_TYPE, doc_type)
        return self.get(key, {})

    def set_row_heights_by_id(self, heights: dict, doc_type: str = None):
        """Сохранить высоты строк по ID документа"""
        key = self._get_type_key(SettingsKeys.ROW_HEIGHTS_BY_ID_TYPE, doc_type)
        self.set(key, heights)

    def remove_row_heights_by_type(self, doc_type: str = None):
        """Удалить старые высоты строк для типа"""
        key = self._get_type_key(SettingsKeys.ROW_HEIGHTS_TYPE, doc_type)
        if key in self._settings:
            del self._settings[key]
            self._save_settings()



    def save_auth_session(self, refresh_token: str, phone: str = None):
        """Сохраняет refresh_token и телефон для авто-входа."""
        self.set(SettingsKeys.AUTH_REFRESH_TOKEN, refresh_token)
        if phone:
            self.set(SettingsKeys.AUTH_PHONE, phone)
        self.set(SettingsKeys.AUTH_SAVED_AT, datetime.now().isoformat())
        print("[SettingsManager] Auth session saved")

    def get_auth_session(self) -> dict:
        """Возвращает сохранённую сессию или пустой dict."""
        token = self.get(SettingsKeys.AUTH_REFRESH_TOKEN)
        if not token:
            return {}
        return {
            "refresh_token": token,
            "phone": self.get(SettingsKeys.AUTH_PHONE),
            "saved_at": self.get(SettingsKeys.AUTH_SAVED_AT),
        }

    def clear_auth_session(self):
        """Удаляет сохранённую сессию."""
        self.remove(SettingsKeys.AUTH_REFRESH_TOKEN)
        self.remove(SettingsKeys.AUTH_PHONE)
        self.remove(SettingsKeys.AUTH_SAVED_AT)
        print("[SettingsManager] Auth session cleared")