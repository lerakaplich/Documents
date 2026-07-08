# client/core/settings/settings_keys.py

class SettingsKeys:
    """Ключи для локальных настроек (хранятся в JSON файле)"""

    # ============ ГЛОБАЛЬНЫЕ НАСТРОЙКИ ============
    ROW_ORDER = "row_order"  # Порядок строк (глобально)
    ROW_HEIGHTS = "row_heights"  # Высоты строк (глобально)
    PINNED = "pinned"  # Закрепленные документы (глобально)
    HIDDEN_ROWS = "hidden_rows"  # Скрытые строки (глобально)

    # ============ НАСТРОЙКИ ПО ТИПУ ДОКУМЕНТА ============
    # Колонки
    COLUMN_WIDTHS = "column_widths"  # Ширина колонок
    HIDDEN_COLUMNS = "hidden_columns"  # Скрытые колонки
    COLUMN_ORDER = "column_order"  # Порядок колонок

    # Строки
    ROW_HEIGHTS_TYPE = "row_heights"  # Высоты строк для типа
    ROW_ORDER_TYPE = "row_order"  # Порядок строк для типа
    PINNED_TYPE = "pinned"  # Закрепленные для типа
    HIDDEN_ROWS_TYPE = "hidden_rows"  # Скрытые строки для типа

    # ============ СПЕЦИАЛЬНЫЕ ТИПЫ ============
    DEFAULT_TYPE = "default"  # Настройки по умолчанию
    EMPTY_TYPE = "{}"  # Особый режим (пустой/новый документ)

    @staticmethod
    def get_type_key(base_key: str, doc_type: str) -> str:
        """
        Получить ключ с типом документа

        Args:
            base_key: базовый ключ (например, COLUMN_ORDER)
            doc_type: тип документа (например, "1", "2", "default", "{}")

        Returns:
            str: ключ с типом документа (например, "column_order_1")
        """
        if not doc_type or doc_type == SettingsKeys.DEFAULT_TYPE:
            return base_key
        return f"{base_key}_{doc_type}"