"""
Управление данными таблицы - только данные, без UI логики
"""

from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal


class TableDataManager(QObject):
    """
    Управление данными в таблице.
    Хранит текущий список документов и управляет их отображением.
    Единый источник истины для данных.
    """

    data_changed = pyqtSignal()
    document_selected = pyqtSignal(dict)

    def __init__(self, table_widget, row_renderer):
        super().__init__()
        self._table_widget = table_widget
        self._row_renderer = row_renderer
        self._documents: list[dict[str, Any]] = []
        self._selected_document: dict[str, Any] | None = None
        self._current_doc_type: str = "default"
        self._columns_config: dict = {}

    def set_columns_config(self, columns_config: dict):
        """Обновить конфигурацию колонок"""
        self._columns_config = columns_config
        if self._row_renderer:
            self._row_renderer.update_columns_config(columns_config)

    def load_data(self, documents: list[dict[str, Any]], doc_type: str = "default"):
        """Загрузка данных с указанием типа документа"""
        self._documents = documents
        self._current_doc_type = doc_type
        self._update_table()
        self.data_changed.emit()
        print(f"[TableDataManager] Loaded {len(documents)} documents, type: {doc_type}")

    def update_data(self, documents: list[dict[str, Any]]):
        """Обновление данных"""
        self._documents = documents
        self._update_table()
        self.data_changed.emit()

    def _update_table(self):
        tw = self._table_widget
        tw.setUpdatesEnabled(False)
        tw.blockSignals(True)
        try:
            tw.setRowCount(0)
            tw.setRowCount(len(self._documents))
            for row, doc in enumerate(self._documents):
                self._row_renderer.render_row(row, doc)
            tw.resizeRowsToContents()
        finally:
            tw.blockSignals(False)
            tw.setUpdatesEnabled(True)

    def get_documents(self) -> list[dict[str, Any]]:
        """Получить все документы"""
        return self._documents.copy()

    def get_document_by_id(self, doc_id: int) -> dict[str, Any] | None:
        """Получить документ по ID"""
        for doc in self._documents:
            if doc.get("id") == doc_id:
                return doc
        return None

    def get_document_by_row(self, row: int) -> dict[str, Any] | None:
        """Получить документ по номеру строки"""
        if 0 <= row < len(self._documents):
            return self._documents[row]
        return None

    def get_row_by_document_id(self, doc_id: int) -> int:
        """Получить номер строки по ID документа"""
        for idx, doc in enumerate(self._documents):
            if doc.get("id") == doc_id:
                return idx
        return -1

    def select_document(self, doc_id: int) -> bool:
        """Выбрать документ по ID"""
        doc = self.get_document_by_id(doc_id)
        if doc:
            self._selected_document = doc
            self.document_selected.emit(doc)
            return True
        return False

    def get_selected_document(self) -> dict[str, Any] | None:
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
