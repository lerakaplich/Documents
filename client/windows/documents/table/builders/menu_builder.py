"""
Построитель меню для панели документов
"""
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction


class MenuBuilder:
    """Построитель меню для кнопок панели"""

    @staticmethod
    def create_columns_menu(parent, style: str) -> QMenu:
        """Меню выбора столбцов"""
        menu = QMenu(parent)
        menu.setStyleSheet(style)

        columns = ["ID", "Номер документа", "Тема", "Тип", "Дата", "Статус", "Отправитель", "Хэштеги"]
        for col in columns:
            action = QAction(col, menu)
            action.setCheckable(True)
            action.setChecked(True)
            menu.addAction(action)

        return menu

    @staticmethod
    def create_filter_menu(parent, style: str) -> QMenu:
        """Меню фильтрации"""
        menu = QMenu(parent)
        menu.setStyleSheet(style)

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

    @staticmethod
    def create_statuses_menu(parent, style: str) -> QMenu:
        """Меню статусов"""
        menu = QMenu(parent)
        menu.setStyleSheet(style)

        statuses = ["Черновик", "На рассмотрении", "На подписи", "Подписан", "Завершен"]
        for status in statuses:
            action = QAction(status, menu)
            action.setCheckable(True)
            menu.addAction(action)

        menu.addSeparator()
        clear_action = QAction("Сбросить фильтр статусов", menu)
        menu.addAction(clear_action)

        return menu