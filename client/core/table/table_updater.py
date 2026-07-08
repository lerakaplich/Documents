"""
Обновление UI таблицы
"""
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication


class TableUpdater(QObject):
    """Класс для обновления таблицы"""

    def __init__(self, table_widget):
        super().__init__()
        self.table_widget = table_widget
        self._row_manager = None
        self._update_timer = None

    def set_row_manager(self, row_manager):
        """Установить менеджер строк для восстановления высот"""
        self._row_manager = row_manager

    def force_update(self):
        """Максимально принудительное обновление"""
        try:
            self.table_widget.setUpdatesEnabled(False)

            self.table_widget.resizeRowsToContents()
            self.table_widget.resizeColumnsToContents()

            self.table_widget.viewport().update()
            self.table_widget.update()
            self.table_widget.repaint()

            self.table_widget.horizontalHeader().update()
            self.table_widget.verticalHeader().update()

            for row in range(self.table_widget.rowCount()):
                for col in range(self.table_widget.columnCount()):
                    widget = self.table_widget.cellWidget(row, col)
                    if widget:
                        widget.update()
                        widget.repaint()

            self.table_widget.setUpdatesEnabled(True)
            QApplication.processEvents()

            QTimer.singleShot(50, self._extra_update)

        except Exception as e:
            print(f"[TableUpdater] Error: {e}")
            self.table_widget.setUpdatesEnabled(True)

    def _extra_update(self):
        """Дополнительное обновление"""
        try:
            self.table_widget.viewport().update()
            self.table_widget.update()
            self.table_widget.repaint()
            QApplication.processEvents()
        except Exception as e:
            print(f"[TableUpdater] Error in extra update: {e}")

    def update_after_data_change(self):
        """Обновление после изменения данных"""
        if self._update_timer is not None:
            self._update_timer.stop()

        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._do_update_after_data_change)
        self._update_timer.start(100)

    def _do_update_after_data_change(self):
        """Выполнить обновление после изменения данных"""
        try:
            self.table_widget.resizeRowsToContents()

            if self._row_manager:
                self._row_manager.restore_row_heights()

            self.table_widget.viewport().update()
            self.table_widget.update()
            QApplication.processEvents()
        except Exception as e:
            print(f"[TableUpdater] Error in update_after_data_change: {e}")

    def update_row(self, row: int):
        """Обновить конкретную строку"""
        try:
            if 0 <= row < self.table_widget.rowCount():
                self.table_widget.updateRow(row)
                self.table_widget.viewport().update()
        except Exception as e:
            print(f"[TableUpdater] Error updating row {row}: {e}")

    def update_rows(self, rows: list):
        """Обновить несколько строк"""
        try:
            for row in rows:
                if 0 <= row < self.table_widget.rowCount():
                    self.table_widget.updateRow(row)
            self.table_widget.viewport().update()
        except Exception as e:
            print(f"[TableUpdater] Error updating rows: {e}")