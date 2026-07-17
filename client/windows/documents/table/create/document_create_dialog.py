"""
Диалог создания нового документа
"""
import os
import sys
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, Qt, QDate
from PyQt6.QtWidgets import (
    QWidget, QApplication, QMessageBox, QPushButton,
    QComboBox, QTextEdit, QDateEdit, QTextBrowser
)


class DocumentCreateDialog(QWidget):
    """
    Диалог создания нового документа
    """

    # Сигналы
    document_created = pyqtSignal(dict)  # Сигнал при создании документа
    cancelled = pyqtSignal()  # Сигнал при отмене

    def __init__(self, parent=None, current_user: Optional[Dict[str, Any]] = None):
        """
        Инициализация диалога создания документа

        Args:
            parent: родительский виджет
            current_user: данные текущего пользователя
        """
        super().__init__(parent)

        self.current_user = current_user or {}

        # Загрузка UI
        self._load_ui()

        # Инициализация данных
        self._init_data()

        # Настройка виджетов
        self._setup_widgets()

        # Подключение сигналов
        self._connect_signals()

        # Установка текущей даты
        self._set_default_dates()

    def _load_ui(self):
        """Загрузка UI из .ui файла"""
        # Текущая директория: D:\Documents\client\windows\documents\table\create
        # Нужно подняться на 4 уровня вверх до D:\Documents\client
        # Затем спуститься в ui\documents\create\document_create_dialog.ui

        current_dir = os.path.dirname(os.path.abspath(__file__))  # .../client/windows/documents/table/create
        client_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))  # .../client
        ui_path = os.path.join(client_dir, 'ui', 'documents', 'create', 'document_create_dialog.ui')
        ui_path = os.path.normpath(ui_path)

        print(f"[DocumentCreateDialog] Ищем UI: {ui_path}")
        print(f"[DocumentCreateDialog] Файл существует: {os.path.exists(ui_path)}")

        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
            print(f"[DocumentCreateDialog] UI успешно загружен")
        else:
            print(f"[DocumentCreateDialog] UI файл не найден: {ui_path}")
            # Создаем базовый интерфейс, если файл не найден
            self._create_fallback_ui()

    def _create_fallback_ui(self):
        """Создание базового UI если файл не найден"""
        from PyQt6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(8, 8, 8, 8)

        # Заголовок
        title = QLabel("Создание документа")
        title.setStyleSheet("font-weight: bold; font-size: 16px; color: #1B232A;")
        layout.addWidget(title)

        # Разделитель
        line = QLabel()
        line.setStyleSheet("border: 1px solid #E0E0E0;")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # Сообщение об ошибке
        error_label = QLabel("UI файл не найден.\nПожалуйста, проверьте путь:\nclient/ui/documents/create/document_create_dialog.ui")
        error_label.setStyleSheet("color: red; padding: 20px;")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(error_label)

        # Кнопка закрытия
        btn_close = QPushButton("Закрыть")
        btn_close.setStyleSheet("""
            QPushButton {
                border-radius: 10px;
                background-color: #CCAB6E;
                color: white;
                border: none;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #998664;
            }
        """)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        # Создаем минимальный набор атрибутов для избежания ошибок
        self.direction_box = QComboBox()
        self.index_number_edit = QTextEdit()
        self.number_edit = QTextEdit()
        self.date_edit = QDateEdit()
        self.date_deadline = QDateEdit()
        self.regarding_edit = QTextEdit()
        self.topic_edit = QTextEdit()
        self.sender_box = QComboBox()
        self.btnAddSender = QPushButton()
        self.btn_receiver = QPushButton()
        self.btnAddExecutor = QPushButton()
        self.btnExecutor = QPushButton()
        self.btnAddReceiver = QPushButton()
        self.btn_tag = QPushButton()
        self.btnAddTag = QPushButton()
        self.select_box = QComboBox()
        self.namedoc_browser = QTextBrowser()
        self.btn_attach = QPushButton()

    def _init_data(self):
        """Инициализация данных"""
        # Списки для комбобоксов
        self.directions = ["Входящий", "Исходящий", "Внутренний"]
        self.senders = []
        self.receivers = []
        self.executors = []
        self.tags = []
        self.create_methods = ["Создать новый", "Из шаблона", "Загрузить файл"]

        # Хранилище выбранных элементов
        self.selected_receivers = []
        self.selected_executors = []
        self.selected_tags = []
        self.selected_sender = None

    def _setup_widgets(self):
        """Настройка виджетов"""
        # Направление
        if hasattr(self, 'direction_box'):
            self.direction_box.addItems(self.directions)
            self.direction_box.setCurrentIndex(-1)  # Ничего не выбрано
            self.direction_box.setPlaceholderText("Выберите направление")

        # Отправитель
        if hasattr(self, 'sender_box'):
            self.sender_box.addItem("Выберите отправителя")
            self.sender_box.setCurrentIndex(0)
            # TODO: Загрузить список отправителей из базы

        # Способ создания
        if hasattr(self, 'select_box'):
            self.select_box.addItems(self.create_methods)
            self.select_box.setCurrentIndex(-1)  # Ничего не выбрано
            self.select_box.setPlaceholderText("Выберите способ создания документа")

        # Настройка дат
        if hasattr(self, 'date_edit'):
            self.date_edit.setCalendarPopup(True)
            self.date_edit.setDisplayFormat("dd.MM.yyyy")

        if hasattr(self, 'date_deadline'):
            self.date_deadline.setCalendarPopup(True)
            self.date_deadline.setDisplayFormat("dd.MM.yyyy")

        # Настройка кнопок
        if hasattr(self, 'btn_attach'):
            self.btn_attach.setText("Сохранить документ")

    def _set_default_dates(self):
        """Установка дат по умолчанию"""
        today = QDate.currentDate()

        if hasattr(self, 'date_edit'):
            self.date_edit.setDate(today)

        if hasattr(self, 'date_deadline'):
            # Срок ответа + 30 дней от сегодня
            deadline = today.addDays(30)
            self.date_deadline.setDate(deadline)

    def _connect_signals(self):
        """Подключение сигналов"""
        # Кнопка сохранения
        if hasattr(self, 'btn_attach'):
            self.btn_attach.clicked.connect(self.save_document)

        # Кнопки добавления
        if hasattr(self, 'btnAddSender'):
            self.btnAddSender.clicked.connect(self.add_sender)

        if hasattr(self, 'btnAddExecutor'):
            self.btnAddExecutor.clicked.connect(self.add_executor)

        if hasattr(self, 'btnAddReceiver'):
            self.btnAddReceiver.clicked.connect(self.add_receiver)

        if hasattr(self, 'btnAddTag'):
            self.btnAddTag.clicked.connect(self.add_tag)

        # Кнопки выбора
        if hasattr(self, 'btn_receiver'):
            self.btn_receiver.clicked.connect(self.select_receiver)

        if hasattr(self, 'btnExecutor'):
            self.btnExecutor.clicked.connect(self.select_executor)

        if hasattr(self, 'btn_tag'):
            self.btn_tag.clicked.connect(self.select_tags)

        # Изменение направления
        if hasattr(self, 'direction_box'):
            self.direction_box.currentIndexChanged.connect(self.on_direction_changed)

        # Изменение способа создания
        if hasattr(self, 'select_box'):
            self.select_box.currentIndexChanged.connect(self.on_create_method_changed)

    # ========== ОБРАБОТЧИКИ СОБЫТИЙ ==========

    def on_direction_changed(self, index):
        """Обработка изменения направления документа"""
        if index >= 0:
            direction = self.directions[index]
            print(f"[DocumentCreateDialog] Выбрано направление: {direction}")
            # TODO: Обновить список доступных отправителей/получателей

    def on_create_method_changed(self, index):
        """Обработка изменения способа создания"""
        if index >= 0:
            method = self.create_methods[index]
            print(f"[DocumentCreateDialog] Выбран способ создания: {method}")
            # TODO: Показать/скрыть соответствующие поля

    # ========== ДОБАВЛЕНИЕ УЧАСТНИКОВ ==========

    def add_sender(self):
        """Добавление отправителя"""
        # TODO: Открыть диалог выбора отправителя
        QMessageBox.information(
            self,
            "Добавление отправителя",
            "Открытие диалога выбора отправителя\n\nЭта функция в разработке."
        )

    def add_receiver(self):
        """Добавление получателя"""
        # TODO: Открыть диалог выбора получателя
        QMessageBox.information(
            self,
            "Добавление получателя",
            "Открытие диалога выбора получателя\n\nЭта функция в разработке."
        )

    def add_executor(self):
        """Добавление исполнителя"""
        # TODO: Открыть диалог выбора исполнителя
        QMessageBox.information(
            self,
            "Добавление исполнителя",
            "Открытие диалога выбора исполнителя\n\nЭта функция в разработке."
        )

    def add_tag(self):
        """Добавление тега"""
        # TODO: Открыть диалог выбора тега
        QMessageBox.information(
            self,
            "Добавление тега",
            "Открытие диалога выбора тегов\n\nЭта функция в разработке."
        )

    # ========== ВЫБОР УЧАСТНИКОВ ==========

    def select_receiver(self):
        """Выбор получателя"""
        # TODO: Открыть диалог выбора получателя
        QMessageBox.information(
            self,
            "Выбор получателя",
            "Открытие диалога выбора получателя\n\nЭта функция в разработке."
        )

    def select_executor(self):
        """Выбор исполнителя"""
        # TODO: Открыть диалог выбора исполнителя
        QMessageBox.information(
            self,
            "Выбор исполнителя",
            "Открытие диалога выбора исполнителя\n\nЭта функция в разработке."
        )

    def select_tags(self):
        """Выбор тегов"""
        # TODO: Открыть диалог выбора тегов
        QMessageBox.information(
            self,
            "Выбор тегов",
            "Открытие диалога выбора тегов\n\nЭта функция в разработке."
        )

    # ========== СОХРАНЕНИЕ ДОКУМЕНТА ==========

    def save_document(self):
        """Сохранение документа"""
        # Валидация данных
        if not self.validate_data():
            return

        # Сбор данных
        document_data = self.collect_data()

        # TODO: Отправить данные на сервер
        print(f"[DocumentCreateDialog] Создание документа: {document_data}")

        # Сигнал о создании документа
        self.document_created.emit(document_data)

        # Показать сообщение об успехе
        QMessageBox.information(
            self,
            "Успешно",
            "Документ успешно создан!"
        )

        # Очищаем форму после сохранения
        self.clear_form()

    def validate_data(self) -> bool:
        """
        Валидация введенных данных

        Returns:
            bool: True если данные валидны
        """
        errors = []

        # Проверка направления
        if hasattr(self, 'direction_box') and self.direction_box.currentIndex() < 0:
            errors.append("Выберите направление документа")

        # Проверка отправителя
        if hasattr(self, 'sender_box') and self.sender_box.currentIndex() <= 0:
            errors.append("Выберите отправителя")

        # Проверка получателя (хотя бы один)
        if not self.selected_receivers:
            errors.append("Добавьте хотя бы одного получателя")

        # Проверка исполнителя (хотя бы один)
        if not self.selected_executors:
            errors.append("Добавьте хотя бы одного исполнителя")

        # Проверка содержания
        if hasattr(self, 'regarding_edit') and not self.regarding_edit.toPlainText().strip():
            errors.append("Заполните поле 'Касается'")

        if hasattr(self, 'topic_edit') and not self.topic_edit.toPlainText().strip():
            errors.append("Заполните поле 'Тема'")

        # Проверка дат
        if hasattr(self, 'date_edit') and hasattr(self, 'date_deadline'):
            send_date = self.date_edit.date()
            deadline = self.date_deadline.date()

            if send_date > deadline:
                errors.append("Дата отправки не может быть позже срока ответа")

        # Если есть ошибки - показываем
        if errors:
            error_msg = "\n".join(f"• {err}" for err in errors)
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                f"Пожалуйста, исправьте следующие ошибки:\n\n{error_msg}"
            )
            return False

        return True

    def collect_data(self) -> Dict[str, Any]:
        """
        Сбор данных из формы

        Returns:
            Dict[str, Any]: Словарь с данными документа
        """
        data = {
            "direction": self.direction_box.currentText() if hasattr(self, 'direction_box') else "",
            "index_number": self.index_number_edit.toPlainText().strip() if hasattr(self, 'index_number_edit') else "",
            "number": self.number_edit.toPlainText().strip() if hasattr(self, 'number_edit') else "",
            "regarding": self.regarding_edit.toPlainText().strip() if hasattr(self, 'regarding_edit') else "",
            "topic": self.topic_edit.toPlainText().strip() if hasattr(self, 'topic_edit') else "",
            "sender": self.selected_sender,
            "receivers": self.selected_receivers,
            "executors": self.selected_executors,
            "tags": self.selected_tags,
            "create_method": self.select_box.currentText() if hasattr(self, 'select_box') else "",
            "file_name": self.namedoc_browser.toPlainText().strip() if hasattr(self, 'namedoc_browser') else "",
        }

        # Даты
        if hasattr(self, 'date_edit'):
            qdate = self.date_edit.date()
            data["send_date"] = qdate.toString("yyyy-MM-dd")

        if hasattr(self, 'date_deadline'):
            qdate = self.date_deadline.date()
            data["deadline"] = qdate.toString("yyyy-MM-dd")

        # Добавляем пользователя
        if self.current_user:
            data["created_by"] = self.current_user.get("id")
            data["creator_name"] = self.current_user.get("full_name", "Пользователь")

        return data

    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========

    def clear_form(self):
        """Очистка всех полей формы"""
        if hasattr(self, 'direction_box'):
            self.direction_box.setCurrentIndex(-1)

        if hasattr(self, 'index_number_edit'):
            self.index_number_edit.clear()

        if hasattr(self, 'number_edit'):
            self.number_edit.clear()

        if hasattr(self, 'regarding_edit'):
            self.regarding_edit.clear()

        if hasattr(self, 'topic_edit'):
            self.topic_edit.clear()

        if hasattr(self, 'sender_box'):
            self.sender_box.setCurrentIndex(0)

        if hasattr(self, 'select_box'):
            self.select_box.setCurrentIndex(-1)

        if hasattr(self, 'namedoc_browser'):
            self.namedoc_browser.clear()

        # Очищаем списки выбранных
        self.selected_receivers = []
        self.selected_executors = []
        self.selected_tags = []
        self.selected_sender = None

        # Сбрасываем кнопки
        if hasattr(self, 'btn_receiver'):
            self.btn_receiver.setText("Выберите получателя")

        if hasattr(self, 'btnExecutor'):
            self.btnExecutor.setText("Выберите исполнителя")

        if hasattr(self, 'btn_tag'):
            self.btn_tag.setText("Выберите теги")

        # Устанавливаем даты по умолчанию
        self._set_default_dates()

    def set_document_data(self, data: Dict[str, Any]):
        """
        Заполнение формы данными документа (для редактирования)

        Args:
            data: Данные документа
        """
        if not data:
            return

        # Заполнение полей
        if hasattr(self, 'direction_box') and 'direction' in data:
            index = self.direction_box.findText(data['direction'])
            if index >= 0:
                self.direction_box.setCurrentIndex(index)

        if hasattr(self, 'index_number_edit') and 'index_number' in data:
            self.index_number_edit.setText(str(data['index_number']))

        if hasattr(self, 'number_edit') and 'number' in data:
            self.number_edit.setText(str(data['number']))

        if hasattr(self, 'regarding_edit') and 'regarding' in data:
            self.regarding_edit.setText(data['regarding'])

        if hasattr(self, 'topic_edit') and 'topic' in data:
            self.topic_edit.setText(data['topic'])

        # Даты
        if hasattr(self, 'date_edit') and 'send_date' in data:
            try:
                qdate = QDate.fromString(data['send_date'], "yyyy-MM-dd")
                if qdate.isValid():
                    self.date_edit.setDate(qdate)
            except:
                pass

        if hasattr(self, 'date_deadline') and 'deadline' in data:
            try:
                qdate = QDate.fromString(data['deadline'], "yyyy-MM-dd")
                if qdate.isValid():
                    self.date_deadline.setDate(qdate)
            except:
                pass

        # Участники
        if 'receivers' in data and data['receivers']:
            self.selected_receivers = data['receivers']
            if hasattr(self, 'btn_receiver'):
                names = [r.get('name', '') for r in data['receivers'] if r.get('name')]
                self.btn_receiver.setText(f"Получатели: {', '.join(names)}")

        if 'executors' in data and data['executors']:
            self.selected_executors = data['executors']
            if hasattr(self, 'btnExecutor'):
                names = [e.get('name', '') for e in data['executors'] if e.get('name')]
                self.btnExecutor.setText(f"Исполнители: {', '.join(names)}")

        if 'tags' in data and data['tags']:
            self.selected_tags = data['tags']
            if hasattr(self, 'btn_tag'):
                names = [t.get('name', '') for t in data['tags'] if t.get('name')]
                self.btn_tag.setText(f"Теги: {', '.join(names)}")


if __name__ == "__main__":
    # Тестовый запуск
    app = QApplication(sys.argv)

    # Тестовый пользователь
    test_user = {
        'id': 1,
        'full_name': 'Иванов Иван Иванович',
        'last_name': 'Иванов',
        'first_name': 'Иван',
        'middle_name': 'Иванович'
    }

    window = DocumentCreateDialog(current_user=test_user)
    window.setWindowTitle("Создание документа")
    window.resize(351, 803)
    window.show()

    sys.exit(app.exec())