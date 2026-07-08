"""
Управление высотой строк
"""
from PyQt6.QtCore import QObject, QTimer

from client.core.settings.settings_manager import SettingsManager


class RowHeightManager(QObject):
    """
    Управление высотой строк.
    Отвечает только за сохранение/восстановление высот.
    """

    def __init__(self, table_widget, doc_type: str = "default"):
        super().__init__()
        self._table = table_widget
        self._doc_type = doc_type or "default"
        self._settings = SettingsManager()
        self._save_timer = None

    def set_doc_type(self, doc_type: str):
        """Обновить тип документа"""
        self._doc_type = doc_type or "default"

    def save_heights(self):
        """Сохранить высоты строк"""
        try:
            heights = {}
            for row in range(self._table.rowCount()):
                height = self._table.rowHeight(row)
                if height > 0:
                    heights[str(row)] = height

            if heights:
                self._settings.set_row_heights_by_type(heights, self._doc_type)
        except Exception as e:
            print(f"[RowHeightManager] Error saving heights: {e}")

    def restore_heights(self):
        """Восстановить высоты строк"""
        try:
            row_count = self._table.rowCount()
            if row_count == 0:
                return

            heights = self._settings.get_row_heights_by_type(self._doc_type)
            if not heights:
                return

            for row in range(row_count):
                row_key = str(row)
                if row_key in heights:
                    height = heights[row_key]
                    if height > 0:
                        self._table.setRowHeight(row, height)
        except Exception as e:
            print(f"[RowHeightManager] Error restoring heights: {e}")

    def schedule_save(self):
        """Отложенное сохранение (debounce)"""
        if self._save_timer is not None:
            self._save_timer.stop()

        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.save_heights)
        self._save_timer.start(500)