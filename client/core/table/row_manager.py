"""Управление строками таблицы"""
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView

from client.core.settings.settings_manager import SettingsManager


class RowManager(QObject):
    """Управление строками: закрепление, порядок, высота"""

    row_order_changed = pyqtSignal(list)
    pin_changed = pyqtSignal(int, bool)

    def __init__(self, table_widget, data_manager, updater, doc_type: str = None):
        super().__init__()
        self.table_widget = table_widget
        self.data_manager = data_manager
        self.updater = updater
        self.doc_type = doc_type or "default"
        self.settings = SettingsManager()
        self._updating = False

        # Получаем закрепленные для этого типа
        self.pinned_ids = self.settings.get_pinned_ids(self.doc_type)
        self._setup_row_behavior()

        # Таймер для debounce сохранения высот
        self._height_save_timer = None

        print(f"[RowManager] Initialized for doc_type: {self.doc_type}")
        print(f"[RowManager] Pinned IDs: {self.pinned_ids}")

    def _setup_row_behavior(self):
        """Настройка поведения строк"""
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.table_widget.setDragEnabled(False)
        self.table_widget.setAcceptDrops(False)
        self.table_widget.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)

        vertical_header = self.table_widget.verticalHeader()
        vertical_header.setSectionsMovable(True)
        vertical_header.setDragEnabled(True)
        vertical_header.setDragDropMode(QHeaderView.DragDropMode.InternalMove)
        vertical_header.setDragDropOverwriteMode(False)
        vertical_header.setDefaultSectionSize(30)
        vertical_header.setMinimumSectionSize(20)
        vertical_header.setVisible(True)
        vertical_header.setSectionsClickable(True)

        vertical_header.sectionMoved.connect(self._on_section_moved)
        vertical_header.sectionResized.connect(self._on_row_height_changed)
        self.table_widget.model().rowsMoved.connect(self._on_rows_moved)

    def toggle_pin(self, document_id: int):
        """Переключение закрепления для текущего типа документа"""
        print(f"[RowManager] Toggle pin: {document_id} for type '{self.doc_type}'")

        # Сохраняем текущие высоты перед обновлением
        self.save_row_heights()

        # Обновляем список для этого типа
        if document_id in self.pinned_ids:
            self.pinned_ids.remove(document_id)
            is_pinned = False
        else:
            self.pinned_ids.insert(0, document_id)
            is_pinned = True

        # Сохраняем для текущего типа
        self.settings.set_pinned_ids(self.pinned_ids, self.doc_type)

        # Применяем
        self._apply_pinning()

        # Восстанавливаем высоты после обновления
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(200, self.restore_row_heights)

        # Сигнал
        self.pin_changed.emit(document_id, is_pinned)

    def is_pinned(self, document_id: int) -> bool:
        """Проверка, закреплен ли документ для текущего типа"""
        return document_id in self.pinned_ids

    def _apply_pinning(self):
        """Применить закрепление"""
        documents = self.data_manager.get_documents()
        if not documents:
            return

        # Разделяем на закрепленные и незакрепленные
        pinned = []
        unpinned = []

        for doc in documents:
            doc_id = doc.get('id')
            if doc_id in self.pinned_ids:
                doc['is_pinned'] = True
                pinned.append(doc)
            else:
                doc['is_pinned'] = False
                unpinned.append(doc)

        # Сортируем закрепленные по порядку
        pinned_sorted = []
        for pid in self.pinned_ids:
            for doc in pinned:
                if doc.get('id') == pid:
                    pinned_sorted.append(doc)
                    break

        # Восстанавливаем порядок незакрепленных (глобально)
        saved_order = self.settings.get_row_order()
        if saved_order:
            unpinned_dict = {doc.get('id'): doc for doc in unpinned}
            unpinned_sorted = []
            remaining = set(unpinned_dict.keys())

            for doc_id in saved_order:
                if doc_id in remaining and doc_id not in self.pinned_ids:
                    unpinned_sorted.append(unpinned_dict[doc_id])
                    remaining.remove(doc_id)

            for doc_id in remaining:
                if doc_id not in self.pinned_ids:
                    unpinned_sorted.append(unpinned_dict[doc_id])

            unpinned = unpinned_sorted

        # Финальный порядок
        sorted_documents = pinned_sorted + unpinned

        # Обновляем данные
        self.data_manager.update_data(sorted_documents)

        # Обновляем UI
        self.updater.force_update()

        # Сохраняем порядок (глобально)
        self.settings.set_row_order([d.get('id') for d in sorted_documents])

    def _on_section_moved(self, logical_index, old_visual_index, new_visual_index):
        if self._updating:
            return
        try:
            documents = self._get_documents_in_order()
            self._save_row_order(documents)
            self.row_order_changed.emit([doc.get('id') for doc in documents])
        except Exception as e:
            print(f"[RowManager] Error in _on_section_moved: {e}")

    def _on_rows_moved(self, parent, start, end, destination, row):
        if self._updating:
            return
        try:
            documents = self._get_documents_in_order()
            self._save_row_order(documents)
            self.row_order_changed.emit([doc.get('id') for doc in documents])
        except Exception as e:
            print(f"[RowManager] Error in _on_rows_moved: {e}")

    def _on_row_height_changed(self, logical_index, old_size, new_size):
        """Обработчик изменения высоты строки - сохраняем по ID документа"""
        if self._updating:
            return
        if self._height_save_timer is not None:
            self._height_save_timer.stop()

        from PyQt6.QtCore import QTimer
        self._height_save_timer = QTimer()
        self._height_save_timer.setSingleShot(True)
        self._height_save_timer.timeout.connect(self.save_row_heights)
        self._height_save_timer.start(500)

    def _get_documents_in_order(self) -> list:
        """Получение документов в текущем порядке строк"""
        documents = []
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, 0)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data:
                    documents.append(doc_data)
        return documents

    def _save_row_order(self, documents: list):
        """Сохранение порядка строк в настройки (глобально) - сохраняем ID документов"""
        order_ids = [doc.get('id') for doc in documents]
        self.settings.set_row_order(order_ids)
        print(f"[RowManager] Saved row order (IDs): {order_ids}")

    def save_row_heights(self):
        """
        Сохранить высоты строк для текущего типа документа по ID документа.
        Формат: {str(document_id): height}
        Сохраняется в ключ row_heights_{doc_type}
        """
        try:
            heights_by_id = {}
            row_count = self.table_widget.rowCount()
            print(f"[RowManager] Saving row heights for {row_count} rows, doc_type: {self.doc_type}")

            for row in range(row_count):
                item = self.table_widget.item(row, 0)
                if item:
                    doc_data = item.data(Qt.ItemDataRole.UserRole)
                    if doc_data:
                        doc_id = doc_data.get('id')
                        if doc_id is not None:
                            height = self.table_widget.rowHeight(row)
                            if height > 0:
                                heights_by_id[str(doc_id)] = height
                                print(f"  Row {row}: doc_id={doc_id}, height={height}")

            if heights_by_id:
                # Сохраняем для текущего типа документа
                self.settings.set_row_heights(heights_by_id, self.doc_type)
                print(f"[RowManager] Saved row heights for {len(heights_by_id)} documents, type: {self.doc_type}")
            else:
                print("[RowManager] No row heights to save")
        except Exception as e:
            print(f"[RowManager] Error saving row heights: {e}")
            import traceback
            traceback.print_exc()

    def restore_row_heights(self):
        """
        Восстановить высоты строк для текущего типа документа по ID документа.
        Ищем в ключе row_heights_{doc_type}
        """
        try:
            # Получаем высоты для текущего типа документа
            heights_by_id = self.settings.get_row_heights(self.doc_type)
            if not heights_by_id:
                print(f"[RowManager] No saved row heights for type: {self.doc_type}")
                return

            restored_count = 0
            row_count = self.table_widget.rowCount()
            print(f"[RowManager] Restoring row heights for {row_count} rows, type: {self.doc_type}")

            for row in range(row_count):
                item = self.table_widget.item(row, 0)
                if item:
                    doc_data = item.data(Qt.ItemDataRole.UserRole)
                    if doc_data:
                        doc_id = doc_data.get('id')
                        if doc_id is not None:
                            height_key = str(doc_id)
                            if height_key in heights_by_id:
                                height = heights_by_id[height_key]
                                if height > 0:
                                    self.table_widget.setRowHeight(row, height)
                                    restored_count += 1
                                    print(f"  Row {row}: doc_id={doc_id}, height={height}")

            print(f"[RowManager] Restored row heights for {restored_count} documents, type: {self.doc_type}")
        except Exception as e:
            print(f"[RowManager] Error restoring row heights: {e}")
            import traceback
            traceback.print_exc()