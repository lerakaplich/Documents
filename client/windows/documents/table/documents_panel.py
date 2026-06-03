import os
import sys
from PyQt6.QtWidgets import (QWidget, QMenu, QApplication)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.uic import loadUi

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class DocumentsPanel(QWidget):
    filter_changed = pyqtSignal(dict)
    search_requested = pyqtSignal(str)
    document_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(ROOT_DIR, "ui", "documents", "table", "documents_panel.ui")
        loadUi(ui_path, self)

        # Стиль для меню
        self.setup_menu_style()

        # Настройка кнопок и меню
        self.setup_buttons()

    def setup_menu_style(self):
        """Стиль для выпадающих меню"""
        self.menu_style = """
            QMenu { 
                background-color: white; 
                border: 1px solid #c0c0c0; 
                border-radius: 5px; 
                padding: 5px; 
                color: black;
            }
            QMenu::item { 
                padding: 8px 25px 8px 15px; 
                border-radius: 3px; 
                font-size: 14px; 
            }
            QMenu::item:selected { 
                background-color: #e3f2fd; 
            }
            QMenu::separator { 
                height: 1px; 
                background: #e0e0e0; 
                margin: 5px 10px; 
            }
        """

    def setup_buttons(self):
        """Настройка кнопок и их меню"""
        self.columnsBtn.setMenu(self.create_columns_menu())
        self.filterBtn.setMenu(self.create_filter_menu())
        self.statusesBtn.setMenu(self.create_statuses_menu())
        self.searchEdit.textChanged.connect(self.on_search_changed)

    def create_columns_menu(self):
        """Меню выбора столбцов"""
        menu = QMenu(self)
        menu.setStyleSheet(self.menu_style)

        columns = ["ID", "Номер документа", "Тема", "Тип", "Дата", "Статус", "Отправитель"]
        for col in columns:
            action = QAction(col, menu)
            action.setCheckable(True)
            action.setChecked(True)
            menu.addAction(action)

        return menu

    def create_filter_menu(self):
        """Меню фильтрации"""
        menu = QMenu(self)
        menu.setStyleSheet(self.menu_style)

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

    def create_statuses_menu(self):
        """Меню статусов"""
        menu = QMenu(self)
        menu.setStyleSheet(self.menu_style)

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

    def update_title(self, title):
        """Обновление заголовка"""
        self.labelTitle.setText(title)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DocumentsPanel()
    window.show()
    sys.exit(app.exec())