"""
Модуль управления строками таблицы: перемещение, закрепление
"""
from PyQt6.QtCore import Qt, QSettings, QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QApplication


class RowManager(QObject):
    """Класс для управления строками таблицы: перемещение, закрепление"""

    row_order_changed = pyqtSignal(list)
    pin_changed = pyqtSignal(int, bool)

    def __init__(self, table_widget, parent=None):
        super().__init__(parent)
        self.table_widget = table_widget
        self.settings = QSettings("YourCompany", "DocumentsApp")
        self.pinned_ids = []
        self._updating = False
        self._pending_update = False

        self._restore_pinned()
        self._setup_row_behavior()

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
        self.table_widget.model().rowsMoved.connect(self._on_rows_moved)

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
        """Сохранение порядка строк в настройки"""
        order_ids = [doc.get('id') for doc in documents]
        self.settings.setValue("row_order", order_ids)
        print(f"[RowManager] Saved row order: {order_ids}")

    def _restore_pinned(self):
        """Восстановление списка закрепленных документов"""
        self.pinned_ids = self.settings.value("pinned_documents", [])
        if not isinstance(self.pinned_ids, list):
            self.pinned_ids = []
        self.pinned_ids = [int(id) for id in self.pinned_ids if id is not None]
        print(f"[RowManager] Restored pinned: {self.pinned_ids}")

    def _get_saved_row_order(self) -> list:
        """Получение сохраненного порядка строк"""
        saved_order = self.settings.value("row_order", [])
        if not isinstance(saved_order, list):
            saved_order = []
        return [int(id) for id in saved_order if id is not None]

    def toggle_pin(self, document_id: int):
        """Переключение закрепления документа"""
        if self._updating:
            return

        print(f"[RowManager] Toggle pin START: {document_id}")

        try:
            # Обновляем список закрепленных
            if document_id in self.pinned_ids:
                self.pinned_ids.remove(document_id)
                is_pinned = False
            else:
                self.pinned_ids.insert(0, document_id)
                is_pinned = True

            # Сохраняем в настройки
            self.settings.setValue("pinned_documents", self.pinned_ids)
            print(f"[RowManager] Toggle pin: {document_id} -> {is_pinned}")
            print(f"[RowManager] Pinned IDs: {self.pinned_ids}")

            # Применяем закрепление (НЕ ставим _updating здесь!)
            self._apply_pinning_direct()

            # Сигнал об изменении
            self.pin_changed.emit(document_id, is_pinned)

            print(f"[RowManager] Toggle pin COMPLETE: {document_id}")

        except Exception as e:
            print(f"[RowManager] Error toggling pin: {e}")
            import traceback
            traceback.print_exc()

    def _apply_pinning_direct(self):
        """Применение закрепления (без проверки _updating)"""
        print("[RowManager] _apply_pinning_direct START")
        try:
            # Получаем текущий порядок документов из таблицы
            documents = self._get_documents_in_order()
            if not documents:
                print("[RowManager] No documents found")
                return

            print(f"[RowManager] Current documents: {[d.get('id') for d in documents]}")

            # Получаем сохраненный порядок
            saved_order = self._get_saved_row_order()
            print(f"[RowManager] Saved order: {saved_order}")

            # Создаем словарь документов
            docs_dict = {doc.get('id'): doc for doc in documents}

            # 1. Формируем список закрепленных в порядке pinned_ids
            pinned_docs = []
            for pid in self.pinned_ids:
                if pid in docs_dict:
                    doc = docs_dict[pid]
                    doc['is_pinned'] = True
                    pinned_docs.append(doc)

            # 2. Формируем список незакрепленных
            unpinned_docs = []
            for doc in documents:
                if doc.get('id') not in self.pinned_ids:
                    doc['is_pinned'] = False
                    unpinned_docs.append(doc)

            # 3. Восстанавливаем порядок незакрепленных
            if saved_order:
                unpinned_dict = {doc.get('id'): doc for doc in unpinned_docs}
                unpinned_sorted = []
                remaining = set(unpinned_dict.keys())

                for doc_id in saved_order:
                    if doc_id in remaining and doc_id not in self.pinned_ids:
                        unpinned_sorted.append(unpinned_dict[doc_id])
                        remaining.remove(doc_id)

                for doc_id in remaining:
                    if doc_id not in self.pinned_ids:
                        unpinned_sorted.append(unpinned_dict[doc_id])

                unpinned_docs = unpinned_sorted

            # Финальный порядок
            sorted_documents = pinned_docs + unpinned_docs

            print(f"[RowManager] Final order: {[d.get('id') for d in sorted_documents]}")

            # Перестраиваем таблицу
            self._rebuild_table(sorted_documents)

            # Сохраняем полный порядок
            self._save_row_order(sorted_documents)

            print("[RowManager] _apply_pinning_direct COMPLETE")

        except Exception as e:
            print(f"[RowManager] Error applying pinning: {e}")
            import traceback
            traceback.print_exc()

    def is_pinned(self, document_id: int) -> bool:
        """Проверка, закреплен ли документ"""
        return document_id in self.pinned_ids

    def _apply_pinning(self):
        """Применение закрепления"""
        if self._updating:
            return

        print("[RowManager] _apply_pinning START")
        self._updating = True
        try:
            # Получаем текущий порядок документов из таблицы
            documents = self._get_documents_in_order()
            if not documents:
                print("[RowManager] No documents found")
                return

            print(f"[RowManager] Current documents: {[d.get('id') for d in documents]}")

            # Получаем сохраненный порядок
            saved_order = self._get_saved_row_order()
            print(f"[RowManager] Saved order: {saved_order}")

            # Создаем словарь документов
            docs_dict = {doc.get('id'): doc for doc in documents}

            # 1. Формируем список закрепленных в порядке pinned_ids
            pinned_docs = []
            for pid in self.pinned_ids:
                if pid in docs_dict:
                    doc = docs_dict[pid]
                    doc['is_pinned'] = True
                    pinned_docs.append(doc)

            # 2. Формируем список незакрепленных
            unpinned_docs = []
            for doc in documents:
                if doc.get('id') not in self.pinned_ids:
                    doc['is_pinned'] = False
                    unpinned_docs.append(doc)

            # 3. Восстанавливаем порядок незакрепленных
            if saved_order:
                unpinned_dict = {doc.get('id'): doc for doc in unpinned_docs}
                unpinned_sorted = []
                remaining = set(unpinned_dict.keys())

                for doc_id in saved_order:
                    if doc_id in remaining and doc_id not in self.pinned_ids:
                        unpinned_sorted.append(unpinned_dict[doc_id])
                        remaining.remove(doc_id)

                for doc_id in remaining:
                    if doc_id not in self.pinned_ids:
                        unpinned_sorted.append(unpinned_dict[doc_id])

                unpinned_docs = unpinned_sorted

            # Финальный порядок
            sorted_documents = pinned_docs + unpinned_docs

            print(f"[RowManager] Final order: {[d.get('id') for d in sorted_documents]}")

            # Перестраиваем таблицу
            self._rebuild_table(sorted_documents)

            # Сохраняем полный порядок
            self._save_row_order(sorted_documents)

            print("[RowManager] _apply_pinning COMPLETE")

        except Exception as e:
            print(f"[RowManager] Error applying pinning: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._updating = False

    def update_order_after_load(self):
        """Обновление порядка после загрузки новых данных"""
        if self._updating:
            return

        print("[RowManager] update_order_after_load START")
        self._updating = True
        try:
            documents = self._get_documents_in_order()
            if not documents:
                return

            saved_order = self._get_saved_row_order()
            docs_dict = {doc.get('id'): doc for doc in documents}

            if saved_order:
                sorted_docs = []
                remaining = set(docs_dict.keys())

                for doc_id in saved_order:
                    if doc_id in remaining:
                        sorted_docs.append(docs_dict[doc_id])
                        remaining.remove(doc_id)

                for doc_id in remaining:
                    sorted_docs.append(docs_dict[doc_id])

                documents = sorted_docs

            self._apply_pinning_to_list(documents)
            print("[RowManager] update_order_after_load COMPLETE")

        except Exception as e:
            print(f"[RowManager] Error updating order after load: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._updating = False

    def _apply_pinning_to_list(self, documents):
        """Применяет закрепление к списку документов"""
        try:
            docs_dict = {doc.get('id'): doc for doc in documents}

            pinned_docs = []
            for pid in self.pinned_ids:
                if pid in docs_dict:
                    doc = docs_dict[pid]
                    doc['is_pinned'] = True
                    pinned_docs.append(doc)

            unpinned_docs = []
            for doc in documents:
                if doc.get('id') not in self.pinned_ids:
                    doc['is_pinned'] = False
                    unpinned_docs.append(doc)

            sorted_documents = pinned_docs + unpinned_docs

            print(f"[RowManager] Applying pinning: {[d.get('id') for d in sorted_documents]}")

            self._rebuild_table(sorted_documents)
            self._save_row_order(sorted_documents)

        except Exception as e:
            print(f"[RowManager] Error applying pinning to list: {e}")
            import traceback
            traceback.print_exc()

    def _rebuild_table(self, sorted_documents: list):
        """Пересоздание таблицы в правильном порядке"""
        try:
            print(f"[RowManager] === REBUILDING TABLE ===")
            print(f"[RowManager] New order: {[doc.get('id') for doc in sorted_documents]}")

            # Сохраняем ID выделенного документа
            selected_doc_id = None
            current_row = self.table_widget.currentRow()
            if current_row >= 0:
                item = self.table_widget.item(current_row, 0)
                if item:
                    doc_data = item.data(Qt.ItemDataRole.UserRole)
                    if doc_data:
                        selected_doc_id = doc_data.get('id')

            # Получаем parent и row_filler
            parent = self.table_widget.parent()
            if not hasattr(parent, 'row_filler'):
                print("[RowManager] ERROR: parent.row_filler not found!")
                return

            # БЛОКИРУЕМ ОБНОВЛЕНИЯ
            self.table_widget.setUpdatesEnabled(False)
            self.table_widget.blockSignals(True)

            # Очищаем таблицу
            self.table_widget.clearContents()
            self.table_widget.setRowCount(0)

            # Устанавливаем количество строк
            self.table_widget.setRowCount(len(sorted_documents))

            # Заполняем таблицу
            for row, doc in enumerate(sorted_documents):
                doc_id = doc.get('id')
                doc['is_pinned'] = doc_id in self.pinned_ids
                parent.row_filler.fill_row(row, doc)

            # Восстанавливаем выделение
            if selected_doc_id:
                for row in range(self.table_widget.rowCount()):
                    item = self.table_widget.item(row, 0)
                    if item:
                        doc_data = item.data(Qt.ItemDataRole.UserRole)
                        if doc_data and doc_data.get('id') == selected_doc_id:
                            self.table_widget.selectRow(row)
                            break

            # РАЗБЛОКИРУЕМ ОБНОВЛЕНИЯ
            self.table_widget.blockSignals(False)
            self.table_widget.setUpdatesEnabled(True)

            # ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ
            self._force_table_update()

            print(f"[RowManager] Table rebuilt with {len(sorted_documents)} rows")

        except Exception as e:
            print(f"[RowManager] Error rebuilding table: {e}")
            import traceback
            traceback.print_exc()
            self.table_widget.blockSignals(False)
            self.table_widget.setUpdatesEnabled(True)

    def _force_table_update(self):
        """МАКСИМАЛЬНО ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ ТАБЛИЦЫ"""
        try:
            print("[RowManager] FORCE UPDATE START")

            # 1. Обновляем геометрию
            self.table_widget.resizeRowsToContents()
            self.table_widget.resizeColumnsToContents()

            # 2. Обновляем viewport
            self.table_widget.viewport().update()

            # 3. Обновляем сам виджет
            self.table_widget.update()

            # 4. Принудительная перерисовка
            self.table_widget.repaint()

            # 5. Обновляем все ячейки
            for row in range(self.table_widget.rowCount()):
                for col in range(self.table_widget.columnCount()):
                    item = self.table_widget.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    widget = self.table_widget.cellWidget(row, col)
                    if widget:
                        widget.update()
                        widget.repaint()

            # 6. Обновляем заголовки
            self.table_widget.horizontalHeader().update()
            self.table_widget.verticalHeader().update()

            # 7. Принудительная обработка событий
            QApplication.processEvents()

            # 8. Дополнительное обновление через таймер
            QTimer.singleShot(50, self._extra_update)

            print("[RowManager] FORCE UPDATE COMPLETE")

        except Exception as e:
            print(f"[RowManager] Error in force update: {e}")

    def _extra_update(self):
        """Дополнительное обновление"""
        try:
            print("[RowManager] EXTRA UPDATE")
            self.table_widget.viewport().update()
            self.table_widget.update()
            self.table_widget.repaint()
            QApplication.processEvents()
        except Exception as e:
            print(f"[RowManager] Error in extra update: {e}")

    def _get_doc_id_at_row(self, row):
        """Получить ID документа в строке"""
        item = self.table_widget.item(row, 0)
        if item:
            doc_data = item.data(Qt.ItemDataRole.UserRole)
            if doc_data:
                return doc_data.get('id')
        return None

    def apply_initial_pinning(self):
        """Применение закрепления при инициализации"""
        self.update_order_after_load()

    def get_pinned_count(self) -> int:
        """Получение количества закрепленных документов"""
        return len(self.pinned_ids)

    def reset_row_order(self):
        """Сброс порядка строк и закреплений"""
        if self._updating:
            return

        self._updating = True
        try:
            self.settings.remove("row_order")
            self.settings.remove("pinned_documents")
            self.pinned_ids = []

            parent = self.table_widget.parent()
            if hasattr(parent, 'load_test_data'):
                parent.load_test_data()

        except Exception as e:
            print(f"[RowManager] Error resetting row order: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._updating = False