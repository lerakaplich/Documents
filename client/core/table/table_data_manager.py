"""Управление данными таблицы"""
from PyQt6.QtCore import QObject, pyqtSignal


class TableDataManager(QObject):
    """Управление данными в таблице"""

    data_changed = pyqtSignal()

    def __init__(self, table_widget, row_filler):
        super().__init__()
        self.table_widget = table_widget
        self.row_filler = row_filler
        self._documents = []

    def load_data(self, documents):
        """Загрузка данных"""
        self._documents = documents
        self._update_table()

    def update_data(self, documents):
        """Обновление данных"""
        self._documents = documents
        self._update_table()
        self.data_changed.emit()

    def _update_table(self):
        """Обновление таблицы"""
        self.table_widget.setRowCount(0)
        self.table_widget.setRowCount(len(self._documents))

        for row, doc in enumerate(self._documents):
            self.row_filler.fill_row(row, doc)

        self.table_widget.resizeRowsToContents()

    def get_documents(self):
        """Получить все документы"""
        return self._documents.copy()

    def get_document_by_id(self, doc_id):
        """Получить документ по ID"""
        for doc in self._documents:
            if doc.get('id') == doc_id:
                return doc
        return None