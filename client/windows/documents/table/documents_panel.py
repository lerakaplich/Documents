import os
import sys
from PyQt6.QtWidgets import (QWidget, QMenu, QApplication, QMessageBox)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.uic import loadUi

from client.windows.documents.table.documents_table import DocumentsTable
from client.windows.documents.table.styles import TableStyles

# Исправляем определение ROOT_DIR
ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

print(f"Panel ROOT_DIR: {ROOT_DIR}")


class DocumentsPanel(QWidget):
    filter_changed = pyqtSignal(dict)
    search_requested = pyqtSignal(str)
    document_selected = pyqtSignal(dict)
    document_action_triggered = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(ROOT_DIR, "client", "ui", "documents", "table", "documents_panel.ui")
        print(f"Panel UI path: {ui_path}")
        print(f"Panel UI file exists: {os.path.exists(ui_path)}")

        loadUi(ui_path, self)

        # Создание и добавление таблицы
        self.documents_table = DocumentsTable()

        # Добавляем таблицу в контейнер
        if hasattr(self, 'contentFrame'):
            # Если есть contentFrame, добавляем в него
            self.contentLayout.addWidget(self.documents_table)
            print("Added table to contentFrame")
        elif hasattr(self, 'horizontalLayoutHeader'):
            # Если есть horizontalLayoutHeader, добавляем в основной layout
            self.verticalLayout.addWidget(self.documents_table)
            print("Added table to verticalLayout")
        else:
            # Ищем любой layout и добавляем в него
            print("Looking for available layouts...")
            print("Available attributes:", [attr for attr in dir(self) if 'layout' in attr.lower() or 'Layout' in attr])

            # Пробуем добавить в panelLayout или другой layout
            if hasattr(self, 'panelLayout'):
                self.panelLayout.addWidget(self.documents_table)
                print("Added table to panelLayout")
            else:
                print("ERROR: Cannot find suitable layout for table!")

        # Настройка кнопок и меню
        self.setup_buttons()

        # Подключение сигналов таблицы
        self.connect_table_signals()

    def setup_buttons(self):
        """Настройка кнопок и их меню"""
        # Получаем стиль меню из TableStyles
        menu_style = TableStyles.get_menu_style()

        if hasattr(self, 'columnsBtn'):
            self.columnsBtn.setMenu(self.create_columns_menu(menu_style))
        if hasattr(self, 'filterBtn'):
            self.filterBtn.setMenu(self.create_filter_menu(menu_style))
        if hasattr(self, 'statusesBtn'):
            self.statusesBtn.setMenu(self.create_statuses_menu(menu_style))
        if hasattr(self, 'searchEdit'):
            self.searchEdit.textChanged.connect(self.on_search_changed)

    def create_columns_menu(self, menu_style):
        """Меню выбора столбцов"""
        menu = QMenu(self)
        menu.setStyleSheet(menu_style)

        columns = ["ID", "Номер документа", "Тема", "Тип", "Дата", "Статус", "Отправитель", "Хэштеги"]
        for col in columns:
            action = QAction(col, menu)
            action.setCheckable(True)
            action.setChecked(True)
            menu.addAction(action)

        return menu

    def create_filter_menu(self, menu_style):
        """Меню фильтрации"""
        menu = QMenu(self)
        menu.setStyleSheet(menu_style)

        unread_action = QAction("Непрочитанные", menu)
        unread_action.setCheckable(True)
        menu.addAction(unread_action)

        read_action = QAction("Прочитанные", menu)
        read_action.setCheckable(True)
        menu.addAction(read_action)

        menu.addSeparator()

        my_docs_action = QAction("Мои документы", menu)
        my_docs_action.setCheckable(True)
        menu.addAction(my_docs_action)

        all_docs_action = QAction("Все документы", menu)
        all_docs_action.setCheckable(True)
        all_docs_action.setChecked(True)
        menu.addAction(all_docs_action)

        menu.addSeparator()

        by_date_action = QAction("По дате (сначала новые)", menu)
        by_date_action.setCheckable(True)
        menu.addAction(by_date_action)

        return menu

    def toggle_pin_document(self, document_id: int):
        """
        Переключение закрепления документа

        Args:
            document_id: ID документа
        """
        try:
            row_manager = self.get_row_manager()
            if row_manager:
                # Переключаем закрепление
                row_manager.toggle_pin(document_id)

                # Обновляем статус закрепления в данных документа
                self._update_document_pin_status(document_id)

                # Отправляем сигнал
                is_pinned = row_manager.is_pinned(document_id)
                self.pin_status_changed.emit(document_id, is_pinned)
        except Exception as e:
            print(f"[DocumentsTable] Error toggling pin: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось изменить статус закрепления документа: {str(e)}"
            )

    def create_statuses_menu(self, menu_style):
        """Меню статусов"""
        menu = QMenu(self)
        menu.setStyleSheet(menu_style)

        statuses = ["Черновик", "На рассмотрении", "На подписи", "Подписан", "Завершен"]
        for status in statuses:
            action = QAction(status, menu)
            action.setCheckable(True)
            menu.addAction(action)

        menu.addSeparator()
        clear_action = QAction("Сбросить фильтр статусов", menu)
        menu.addAction(clear_action)

        return menu

    def on_search_changed(self, text):
        """Обработка поиска"""
        self.search_requested.emit(text)

    def connect_table_signals(self):
        """Подключение сигналов таблицы"""
        if hasattr(self, 'documents_table'):
            self.documents_table.document_action_triggered.connect(
                self.document_action_triggered.emit
            )

            self.documents_table.read_status_changed.connect(
                lambda doc_id, is_read: print(f"Document {doc_id} read: {is_read}")
            )

    def update_title(self, title):
        """Обновление заголовка"""
        if hasattr(self, 'labelTitle'):
            self.labelTitle.setText(title)

    def get_documents_table(self):
        """Получение объекта таблицы для внешнего взаимодействия"""
        return self.documents_table


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DocumentsPanel()
    window.setWindowTitle("Documents Panel Test")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())