"""
Управление данными таблицы - связь между репозиторием и UI
"""
from PyQt6.QtCore import QObject, pyqtSignal
from typing import List, Dict, Any, Optional


class TableDataManager(QObject):
    """
    Управление данными в таблице.
    Хранит текущий список документов и управляет их отображением.
    """

    data_changed = pyqtSignal()
    document_selected = pyqtSignal(dict)

    def __init__(self, table_widget, row_filler):
        super().__init__()
        self.table_widget = table_widget
        self.row_filler = row_filler
        self._documents: List[Dict[str, Any]] = []
        self._selected_document: Optional[Dict[str, Any]] = None
        self._current_doc_type: str = "default"

    def load_data(self, documents: List[Dict[str, Any]], doc_type: str = "default"):
        """
        Загрузка данных с указанием типа документа

        Args:
            documents: список документов
            doc_type: тип документа для настроек
        """
        self._documents = documents
        self._current_doc_type = doc_type
        self._update_table()
        self.data_changed.emit()
        print(f"[TableDataManager] Loaded {len(documents)} documents, type: {doc_type}")

    def update_data(self, documents: List[Dict[str, Any]]):
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

    def get_documents(self) -> List[Dict[str, Any]]:
        """Получить все документы"""
        return self._documents.copy()

    def get_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Получить документ по ID"""
        for doc in self._documents:
            if doc.get('id') == doc_id:
                return doc
        return None

    def get_document_by_row(self, row: int) -> Optional[Dict[str, Any]]:
        """Получить документ по номеру строки"""
        if 0 <= row < len(self._documents):
            return self._documents[row]
        return None

    def get_row_by_document_id(self, doc_id: int) -> int:
        """Получить номер строки по ID документа"""
        for idx, doc in enumerate(self._documents):
            if doc.get('id') == doc_id:
                return idx
        return -1

    def select_document(self, doc_id: int):
        """Выбрать документ по ID"""
        doc = self.get_document_by_id(doc_id)
        if doc:
            self._selected_document = doc
            self.document_selected.emit(doc)
            return True
        return False

    def get_selected_document(self) -> Optional[Dict[str, Any]]:
        """Получить выбранный документ"""
        return self._selected_document

    def get_current_doc_type(self) -> str:
        """Получить текущий тип документа"""
        return self._current_doc_type

    def count(self) -> int:
        """Количество документов"""
        return len(self._documents)

    def is_empty(self) -> bool:
        """Пусто ли"""
        return len(self._documents) == 0