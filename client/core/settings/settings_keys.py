# client/core/settings/settings_keys.py

class SettingsKeys:
    """Ключи для локальных настроек (хранятся в JSON файле)"""

    # ============ ГЛОБАЛЬНЫЕ НАСТРОЙКИ ============
    # (не зависят от типа документа)

    # Порядок строк (глобально)
    ROW_ORDER = "row_order"

    # ============ НАСТРОЙКИ ПО ТИПУ ДОКУМЕНТА ============
    # Формат: {f"{base_key}_{doc_type}": value}

    # Закрепленные документы для типа
    # Формат: {"pinned_{doc_type}": [doc_id1, doc_id2, ...]}
    PINNED = "pinned"

    # Высоты строк для типа (по ID документа)
    # Формат: {"row_heights_{doc_type}": {str(document_id): height, ...}}
    ROW_HEIGHTS = "row_heights"

    # Порядок колонок для типа
    # Формат: {"column_order_{doc_type}": [{"logical_index": 0, "name": "ID"}, ...]}
    COLUMN_ORDER = "column_order"

    # Ширина колонок для типа
    # Формат: {"column_widths_{doc_type}": {"0": 60, "1": 96, ...}}
    COLUMN_WIDTHS = "column_widths"

    # Скрытые колонки для типа
    # Формат: {"hidden_columns_{doc_type}": [0, 1, 2, ...]}
    HIDDEN_COLUMNS = "hidden_columns"

    @staticmethod
    def get_type_key(base_key: str, doc_type: str) -> str:
        """
        Получить ключ с типом документа

        Args:
            base_key: базовый ключ (например, COLUMN_ORDER)
            doc_type: тип документа (например, "1", "2", "incoming")

        Returns:
            str: ключ с типом документа (например, "column_order_1")
        """
        if not doc_type or doc_type == "default":
            return base_key
        return f"{base_key}_{doc_type}"