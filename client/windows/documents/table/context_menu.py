"""
Модуль контекстного меню для таблицы документов
"""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMenu, QMessageBox

from client.core.themes import get_menu_style


class ContextMenu(QObject):
    """Класс для управления контекстным меню таблицы документов"""

    # Сигналы для действий
    redirect_requested = pyqtSignal(dict)
    comment_requested = pyqtSignal(dict)
    history_requested = pyqtSignal(dict)
    edit_requested = pyqtSignal(dict)
    attachment_requested = pyqtSignal(dict)
    reply_attachment_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)
    pin_toggle_requested = pyqtSignal(dict)
    archive_toggle_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_table = parent

    def create_menu(self, document_data, has_reply=False):
        """
        Создание контекстного меню для документа

        Args:
            document_data: данные документа
            has_reply: есть ли ответ на документ

        Returns:
            QMenu: созданное меню
        """
        menu = QMenu(self.parent_table)

        # Применяем стиль из текущей темы
        menu.setStyleSheet(get_menu_style())

        # 1. Перенаправить
        redirect_action = menu.addAction("Перенаправить")
        redirect_action.triggered.connect(lambda: self.redirect_requested.emit(document_data))

        # 2. Комментировать
        comment_action = menu.addAction("Комментировать")
        comment_action.triggered.connect(lambda: self.comment_requested.emit(document_data))

        menu.addSeparator()

        # 3. Закрепить/открепить документ
        is_pinned = document_data.get("is_pinned", False)
        pin_text = "Закрепить" if not is_pinned else "Открепить"
        pin_action = menu.addAction(pin_text)
        pin_action.triggered.connect(lambda: self.pin_toggle_requested.emit(document_data))

        # 3.5. Архивировать / Восстановить из архива (персональный архив юзера)
        is_archived = document_data.get("is_archived", False)
        archive_text = "Восстановить из архива" if is_archived else "Архивировать"
        archive_action = menu.addAction(archive_text)
        archive_action.triggered.connect(lambda: self.archive_toggle_requested.emit(document_data))

        menu.addSeparator()

        # 4. Посмотреть историю документа
        history_action = menu.addAction("Посмотреть историю документа")
        history_action.triggered.connect(lambda: self.history_requested.emit(document_data))

        # 5. Редактировать документ
        edit_action = menu.addAction("Редактировать документ")
        edit_action.triggered.connect(lambda: self.edit_requested.emit(document_data))

        menu.addSeparator()

        # 6. Прикрепить вложение
        attachment_action = menu.addAction("Прикрепить вложение")
        attachment_action.triggered.connect(lambda: self.attachment_requested.emit(document_data))

        # 7. Добавить ответное вложение
        reply_attachment_action = menu.addAction("Добавить ответное вложение")
        reply_attachment_action.triggered.connect(lambda: self.reply_attachment_requested.emit(document_data))

        # Отключаем ответное вложение, если есть reply
        if has_reply:
            reply_attachment_action.setEnabled(False)
            reply_attachment_action.setToolTip("На этот документ уже есть ответ")

        menu.addSeparator()

        # 8. Удалить документ
        delete_action = menu.addAction("Удалить документ")
        delete_action.triggered.connect(lambda: self._confirm_delete(document_data))

        return menu

    def _confirm_delete(self, document_data):
        """
        Подтверждение удаления документа

        Args:
            document_data: данные документа
        """
        doc_name = document_data.get("name", "Документ")
        doc_id = document_data.get("id", "")

        reply = QMessageBox.question(
            self.parent_table,
            "Подтверждение удаления",
            f"Вы действительно хотите удалить документ '{doc_name}' (ID: {doc_id})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(document_data)

    def show_context_menu(self, position, document_data, has_reply=False):
        """
        Показать контекстное меню в указанной позиции

        Args:
            position: позиция для отображения меню (QPoint)
            document_data: данные документа
            has_reply: есть ли ответ на документ
        """
        menu = self.create_menu(document_data, has_reply)
        menu.exec(position)