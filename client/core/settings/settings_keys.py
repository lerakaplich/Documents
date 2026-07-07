# client/core/settings/settings_keys.py

class SettingsKeys:
    """Ключи для локальных настроек (хранятся в JSON файле)"""

    # Базовые ключи (без типа документа)
    ROW_ORDER = "row_order"  # порядок строк
    ROW_HEIGHTS = "row_heights"  # высоты строк

    # Ключи с поддержкой типа документа
    # Используем формат: {key}_{document_type}
    COLUMN_ORDER = "column_order"  # порядок колонок
    COLUMN_WIDTHS = "column_widths"  # ширина колонок
    HIDDEN_COLUMNS = "hidden_columns"  # скрытые колонки

    # Настройки сортировки
    SORT_COLUMN = "sort_column"
    SORT_ORDER = "sort_order"

    @staticmethod
    def get_type_key(base_key: str, doc_type: str) -> str:
        """
        Получить ключ с типом документа

        Args:
            base_key: базовый ключ (например, COLUMN_ORDER)
            doc_type: тип документа (например, "incoming", "outgoing")

        Returns:
            str: ключ с типом документа (например, "column_order_incoming")
        """
        if not doc_type:
            return base_key
        return f"{base_key}_{doc_type}"