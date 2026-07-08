"""
Управление высотой строк
"""
from PyQt6.QtCore import QObject, QTimer

from client.core.settings.settings_manager import SettingsManager


class RowHeightManager(QObject):
    """
    Управление высотой строк.
    Сохраняет высоты по ID документа, а не по индексу строки.
    """

    def __init__(self, table_widget, doc_type: str = "default"):
        super().__init__()
        self._table = table_widget
        self._doc_type = doc_type or "default"
        self._settings = SettingsManager()
        self._save_timer = None
        self._document_id_map = {}  # row -> document_id

    def set_doc_type(self, doc_type: str):
        """Обновить тип документа"""
        self._doc_type = doc_type or "default"

    def update_document_map(self, documents: list):
        """
        Обновить маппинг строк -> ID документов.
        Вызывать при обновлении данных.
        """
        self._document_id_map = {}
        for row, doc in enumerate(documents):
            doc_id = doc.get('id')
            if doc_id is not None:
                self._document_id_map[row] = doc_id

    def get_document_id_at_row(self, row: int):
        """Получить ID документа по индексу строки"""
        return self._document_id_map.get(row)

    def save_heights(self):
        """Сохранить высоты строк по ID документа"""
        try:
            heights_by_id = {}
            for row in range(self._table.rowCount()):
                doc_id = self.get_document_id_at_row(row)
                if doc_id is None:
                    continue

                height = self._table.rowHeight(row)
                if height > 0:
                    heights_by_id[str(doc_id)] = height

            if heights_by_id:
                self._settings.set_row_heights_by_id(heights_by_id, self._doc_type)
                print(f"[RowHeightManager] Saved {len(heights_by_id)} heights by ID for '{self._doc_type}'")
        except Exception as e:
            print(f"[RowHeightManager] Error saving heights: {e}")

    def restore_heights(self):
        """Восстановить высоты строк по ID документа"""
        try:
            row_count = self._table.rowCount()
            if row_count == 0:
                return

            heights_by_id = self._settings.get_row_heights_by_id(self._doc_type)
            if not heights_by_id:
                return

            restored_count = 0
            for row in range(row_count):
                doc_id = self.get_document_id_at_row(row)
                if doc_id is None:
                    continue

                doc_id_str = str(doc_id)
                if doc_id_str in heights_by_id:
                    height = heights_by_id[doc_id_str]
                    if height > 0:
                        self._table.setRowHeight(row, height)
                        restored_count += 1

            if restored_count > 0:
                print(f"[RowHeightManager] Restored {restored_count} heights by ID for '{self._doc_type}'")
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

    # ============ МИГРАЦИЯ СТАРЫХ ДАННЫХ ============

    def migrate_from_old_format(self):
        """
        Миграция из старого формата (по индексу) в новый (по ID).
        Вызывать при первом запуске после обновления.
        """
        old_heights = self._settings.get_row_heights_by_type(self._doc_type)
        if not old_heights:
            return

        # Пытаемся сопоставить индексы с ID
        heights_by_id = {}
        for row_str, height in old_heights.items():
            try:
                row = int(row_str)
                doc_id = self.get_document_id_at_row(row)
                if doc_id is not None:
                    heights_by_id[str(doc_id)] = height
            except ValueError:
                continue

        if heights_by_id:
            self._settings.set_row_heights_by_id(heights_by_id, self._doc_type)
            # Удаляем старые данные
            self._settings.remove_row_heights_by_type(self._doc_type)
            print(f"[RowHeightManager] Migrated {len(heights_by_id)} heights from old format")