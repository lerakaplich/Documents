"""
Настройка поведения строк
"""
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView


class RowBehaviorManager(QObject):
    """
    Настройка поведения строк: выделение, редактирование, перетаскивание.
    """

    def __init__(self, table_widget):
        super().__init__()
        self._table = table_widget
        self._setup_behavior()

    def _setup_behavior(self):
        """Настройка поведения строк"""
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setDragEnabled(False)
        self._table.setAcceptDrops(False)
        self._table.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)

        vertical_header = self._table.verticalHeader()
        vertical_header.setSectionsMovable(True)
        vertical_header.setDragEnabled(True)
        vertical_header.setDragDropMode(QHeaderView.DragDropMode.InternalMove)
        vertical_header.setDragDropOverwriteMode(False)
        vertical_header.setDefaultSectionSize(30)
        vertical_header.setMinimumSectionSize(20)
        vertical_header.setVisible(True)
        vertical_header.setSectionsClickable(True)