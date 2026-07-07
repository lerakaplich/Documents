"""Обновление UI таблицы"""
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication


class TableUpdater(QObject):
    """Класс для обновления таблицы"""

    def __init__(self, table_widget):
        super().__init__()
        self.table_widget = table_widget

    def force_update(self):
        """Максимально принудительное обновление"""
        try:
            print("[TableUpdater] Force update START")

            # Блокируем обновления для предотвращения мерцания
            self.table_widget.setUpdatesEnabled(False)

            # Обновляем геометрию
            self.table_widget.resizeRowsToContents()
            self.table_widget.resizeColumnsToContents()

            # Обновляем все элементы
            self.table_widget.viewport().update()
            self.table_widget.update()
            self.table_widget.repaint()

            # Обновляем заголовки
            self.table_widget.horizontalHeader().update()
            self.table_widget.verticalHeader().update()

            # Обновляем все виджеты в ячейках
            for row in range(self.table_widget.rowCount()):
                for col in range(self.table_widget.columnCount()):
                    widget = self.table_widget.cellWidget(row, col)
                    if widget:
                        widget.update()
                        widget.repaint()

            self.table_widget.setUpdatesEnabled(True)

            # Обработка событий
            QApplication.processEvents()

            # Дополнительное обновление через таймер
            QTimer.singleShot(50, self._extra_update)

            print("[TableUpdater] Force update COMPLETE")

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



    def set_row_manager(self, row_manager):
        """Установить менеджер строк для восстановления высот"""
        self._row_manager = row_manager