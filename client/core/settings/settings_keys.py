# client/core/settings/settings_keys.py

class SettingsKeys:
    """Ключи для локальных настроек (хранятся в JSON файле)"""

    # ============ ГЛОБАЛЬНЫЕ НАСТРОЙКИ ============
    ROW_ORDER = "row_order"
    ROW_HEIGHTS = "row_heights"  # Устаревает, используем ROW_HEIGHTS_BY_ID
    ROW_HEIGHTS_BY_ID = "row_heights_by_id"  # НОВЫЙ КЛЮЧ - по ID
    PINNED = "pinned"
    HIDDEN_ROWS = "hidden_rows"

    # ============ НАСТРОЙКИ ПО ТИПУ ДОКУМЕНТА ============
    COLUMN_WIDTHS = "column_widths"
    HIDDEN_COLUMNS = "hidden_columns"
    COLUMN_ORDER = "column_order"

    ROW_HEIGHTS_TYPE = "row_heights"  # Устаревает
    ROW_HEIGHTS_BY_ID_TYPE = "row_heights_by_id"  # НОВЫЙ КЛЮЧ
    ROW_ORDER_TYPE = "row_order"
    PINNED_TYPE = "pinned"
    HIDDEN_ROWS_TYPE = "hidden_rows"

    DEFAULT_TYPE = "default"
    EMPTY_TYPE = "{}"

    @staticmethod
    def get_type_key(base_key: str, doc_type: str) -> str:
        if not doc_type or doc_type == SettingsKeys.DEFAULT_TYPE:
            return base_key
        return f"{base_key}_{doc_type}"