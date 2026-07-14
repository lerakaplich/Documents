"""
Диалог для просмотра и добавления комментариев к документу
"""
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, Qt, QEvent
from PyQt6.QtWidgets import (
    QDialog, QMessageBox, QApplication,
    QScrollArea, QVBoxLayout, QWidget, QSizePolicy, QFrame, QLabel
)

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

        # Заменяем QListWidget на QScrollArea с контейнером
        self.setup_scroll_area()

        # Заполнение списка комментариев
        self.populate_comments()

        # Подключение сигналов
        self.sendButton.clicked.connect(self.add_comment)

        # Обработка Ctrl+Enter для отправки
        self.commentTextEdit.installEventFilter(self)

        self.setModal(True)

    def setup_scroll_area(self):
        """Настройка скролл-области вместо QListWidget"""
        # Получаем родительский лейаут
        parent_layout = self.commentsListWidget.parent().layout()

        # Сохраняем индекс виджета в лейауте
        index = parent_layout.indexOf(self.commentsListWidget)

        # Удаляем QListWidget
        parent_layout.removeWidget(self.commentsListWidget)
        self.commentsListWidget.deleteLater()

        # Создаем QScrollArea
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Стилизация скролла
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                background-color: #FAFAFA;
            }
            QScrollBar:vertical {
                background: #F5F5F5;
                width: 8px;
                border-radius: 4px;
                margin: 0px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #C1C1C1;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #A0A0A0;
            }
            QScrollBar::handle:vertical:pressed {
                background: #888888;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                width: 0px;
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        # Создаем контейнер для комментариев
        # Создаем контейнер для комментариев
        self.comments_container = QWidget()
        self.comments_container.setStyleSheet("background-color: transparent;")

        # ВАЖНО: Добавляем выравнивание Qt.AlignmentFlag.AlignTop
        self.comments_layout = QVBoxLayout(self.comments_container)
        self.comments_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.comments_layout.setSpacing(10)  # Можно вернуть небольшой отступ между блоками
        self.comments_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area.setWidget(self.comments_container)
        parent_layout.insertWidget(index, self.scroll_area)

    def populate_comments(self):
        """Заполнение списка комментариев"""
        # Очищаем контейнер (включая старые пружины/растяжки)
        while self.comments_layout.count() > 0:
            item = self.comments_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            # Удаляем элементы без виджетов (например, stretch)
            elif item.spacerItem():
                pass

        if not self.comments:
            no_comments_label = QLabel("Нет комментариев")
            no_comments_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_comments_label.setStyleSheet("color: gray; padding: 20px;")
            self.comments_layout.addWidget(no_comments_label)
            return

        sorted_comments = sorted(
            self.comments,
            key=lambda x: x.get('created_at', ''),
            reverse=False
        )

        # Добавляем комментарии
        for comment in sorted_comments:
            comment_widget = CommentWidget(comment)
            self.comments_layout.addWidget(comment_widget)

        # ВАЖНО: Добавляем stretch в самый конец, чтобы комментарии не растягивались по высоте
        self.comments_layout.addStretch()

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
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

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
    test_comments = []
    for i in range(5):
        test_comments.append({
            "id": i + 1,
            "text": f"Комментарий #{i + 1}: " + "Это тестовый комментарий с разной длиной текста. " * (i % 3 + 1),
            "created_at": f"2026-05-{28 + i % 3:02d}T{7 + i % 12:02d}:{i % 60:02d}:00Z",
            "author_fio": f"Автор {i + 1}"
        })

    test_doc = {
        'id': 1,
        'number': '12-3-5/001',
        'subject': 'Тестовый документ',
        'comments': test_comments
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