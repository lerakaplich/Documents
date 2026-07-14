"""
Диалог для просмотра и добавления комментариев к документу
"""
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, Qt, QEvent
from PyQt6.QtWidgets import QListWidgetItem, QDialog, QMessageBox, QApplication

from client.core.utils.icon_manager import icon_manager
from client.windows.documents.comments.comment_widget import CommentWidget


class CommentsDialog(QDialog):
    """
    Диалог для просмотра и добавления комментариев к документу
    """

    # Сигнал при добавлении нового комментария
    comment_added = pyqtSignal(dict)
    # Сигнал при закрытии диалога
    dialog_closed = pyqtSignal()

    def __init__(self, document_data: Dict[str, Any], parent=None, current_user: Optional[Dict[str, Any]] = None):
        """
        Инициализация диалога

        Args:
            document_data: данные документа в формате API
            parent: родительский виджет
            current_user: данные текущего пользователя
        """
        super().__init__(parent)

        self.document_data = document_data
        self.current_user = current_user or {}
        # Комментарии уже в правильном формате из API
        self.comments = document_data.get('comments', [])

        # Загрузка UI
        ui_path = os.path.join(os.path.dirname(__file__), '../../../ui/documents/comments/comments_dialog.ui')
        ui_path = os.path.normpath(ui_path)

        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)

        # Настройка окна
        self.setWindowTitle(f"Комментарии к документу №{document_data.get('number', '')}")

        # Установка информации о документе
        doc_number = document_data.get('number', '')
        doc_subject = document_data.get('subject', '')
        self.docInfoLabel.setText(f"Документ: №{doc_number} - {doc_subject}")

        # Заполнение списка комментариев
        self.populate_comments()

        # Подключение сигналов
        self.sendButton.clicked.connect(self.add_comment)

        # Обработка Ctrl+Enter для отправки
        self.commentTextEdit.installEventFilter(self)

        self.setModal(True)

    def populate_comments(self):
        """Заполнение списка комментариев"""
        self.commentsListWidget.clear()

        if not self.comments:
            # Добавляем сообщение об отсутствии комментариев
            item = QListWidgetItem("Нет комментариев")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(Qt.GlobalColor.gray)
            self.commentsListWidget.addItem(item)
            return

        # Сортируем комментарии по времени (старые сверху)
        sorted_comments = sorted(
            self.comments,
            key=lambda x: x.get('created_at', ''),
            reverse=False
        )

        for comment in sorted_comments:
            # Создаем виджет комментария
            comment_widget = CommentWidget(comment)

            # Создаем элемент списка
            item = QListWidgetItem()
            item.setSizeHint(comment_widget.sizeHint())
            self.commentsListWidget.addItem(item)
            self.commentsListWidget.setItemWidget(item, comment_widget)

    def add_comment(self):
        """Добавление нового комментария"""
        text = self.commentTextEdit.toPlainText().strip()

        if not text:
            QMessageBox.warning(self, "Ошибка", "Введите текст комментария!")
            return

        # Формируем ФИО в формате API
        author_fio = self.current_user.get('full_name', '')
        if not author_fio:
            # Если full_name нет, собираем из частей
            last_name = self.current_user.get('last_name', '')
            first_name = self.current_user.get('first_name', '')
            middle_name = self.current_user.get('middle_name', '')

            if last_name:
                author_fio = last_name
                if first_name:
                    author_fio += f" {first_name[0]}."
                if middle_name:
                    author_fio += f" {middle_name[0]}."
            else:
                author_fio = 'Пользователь'

        # Создаем комментарий в формате API
        comment_data = {
            'author_fio': author_fio,
            'text': text,
            'created_at': datetime.now().isoformat() + 'Z'  # Формат ISO с Z
        }

        # Добавляем в список
        self.comments.append(comment_data)

        # Обновляем отображение
        self.populate_comments()

        # Очищаем поле ввода
        self.commentTextEdit.clear()

        # Сигнал о добавлении комментария
        self.comment_added.emit(comment_data)

        # Прокручиваем к последнему комментарию
        self.commentsListWidget.scrollToBottom()

    def eventFilter(self, obj, event):
        """Обработка событий (Ctrl+Enter)"""
        if obj == self.commentTextEdit and event.type() == QEvent.Type.KeyPress:
            key_event = event
            if key_event.key() == Qt.Key.Key_Return and key_event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.add_comment()
                return True
        return super().eventFilter(obj, event)

    def close_dialog(self):
        """Закрытие диалога"""
        self.dialog_closed.emit()
        self.accept()

    def get_comments(self) -> List[Dict[str, Any]]:
        """Получение всех комментариев"""
        return self.comments


if __name__ == "__main__":
    # Тестовый запуск
    app = QApplication(sys.argv)

    # Тестовые данные в формате API
    test_doc = {
        'id': 1,
        'number': '12-3-5/001',
        'subject': 'Тестовый документ',
        'comments': [
            {
                "id": 1,
                "text": "Развернула RabbitMQ в тестовом контейнере Docker, пропускная способность LSTM выросла. Нужен продуктовый Redis.",
                "created_at": "2026-05-28T07:20:00Z",
                "author_fio": "Шершнева Е.И."
            },
            {
                "id": 2,
                "text": "Проверяю конфигурацию брокера. Конфиг очередей RabbitMQ нужно вынести в ENV-файлы микросервиса.",
                "created_at": "2026-05-29T08:15:00Z",
                "author_fio": "Овчинников И.И."
            }
        ]
    }

    current_user = {
        'id': 2,
        'full_name': 'Сидоров С.С.',
        'last_name': 'Сидоров',
        'first_name': 'Сергей',
        'middle_name': 'Сергеевич'
    }

    dialog = CommentsDialog(test_doc, current_user=current_user)
    dialog.comment_added.connect(lambda data: print(f"Добавлен комментарий: {data}"))
    dialog.exec()
    sys.exit(app.exec())