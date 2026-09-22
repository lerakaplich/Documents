# client/windows/profile/overtime/overtime_card.py

import os
from PyQt6.QtWidgets import QFrame, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.uic import loadUi

from client.core.themes import apply_theme_to_widget, T
from client.windows.delete_dialog import DeleteDialog


class OvertimeCard(QFrame):
    """Карточка сверхурочной работы"""

    # Сигналы для взаимодействия с родительским окном
    edit_clicked = pyqtSignal(int)  # передаём id записи
    delete_clicked = pyqtSignal(int)  # передаём id записи

    def __init__(self, overtime_id: int, data: dict, parent=None):
        """
        Инициализация карточки

        Args:
            overtime_id: ID записи о сверхурочной работе
            data: Словарь с данными:
            data: Словарь с данными:
                - employee_name: str - ФИО сотрудника
                - created_at: str - дата создания
                - description: str - описание работы
                - date: str - дата выполнения
                - start_time: str - время начала
                - end_time: str - время окончания
                - duration: float - продолжительность в часах
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.overtime_id = overtime_id
        self.data = data

        # Загружаем UI
        self._load_ui()

        # Настраиваем карточку
        self._setup_card()

        # Заполняем данными
        self._populate_data()

        # Подключаем сигналы
        self._connect_signals()

    def _load_ui(self):
        """Загрузка UI из файла"""
        # Определяем путь к UI файлу
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(
            current_dir,
            '../../../../client/ui/profile/overtime/overtime_card.ui'
        )
        ui_path = os.path.normpath(ui_path)

        if not os.path.exists(ui_path):
            # Если файл не найден, создаём карточку программно
            self._create_ui_programmatically()
        else:
            loadUi(ui_path, self)
            apply_theme_to_widget(self)

    def _create_ui_programmatically(self):
        """Создание UI программно (если файл .ui не найден)"""
        from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QSpacerItem
        from PyQt6.QtCore import QSize

        # Основной layout
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 12, 15, 12)

        # Левая часть - основная информация
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)

        # Шапка: ФИО и дата создания
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        self.labelEmployee = QLabel()
        self.labelEmployee.setStyleSheet(
            f"border: none; font-size: 16px; font-weight: bold; "
            f"color: {T.TEXT_ACCENT_DARK_STRONG}; background-color: transparent;"
        )
        self.labelEmployee.setSizePolicy(
            self.sizePolicy().Policy.Expanding,
            self.sizePolicy().Policy.Preferred
        )
        header_layout.addWidget(self.labelEmployee)

        spacer = QSpacerItem(40, 20, QSpacerItem.SizePolicy.Expanding, QSpacerItem.SizePolicy.Minimum)
        header_layout.addItem(spacer)

        self.labelCreatedAt = QLabel()
        self.labelCreatedAt.setStyleSheet(
            f"border: none; font-size: 11px; color: {T.TEXT_ACCENT_SOFT}; background-color: transparent;"
        )
        header_layout.addWidget(self.labelCreatedAt)

        left_layout.addLayout(header_layout)

        # Строка с описанием и кнопкой редактирования
        description_layout = QHBoxLayout()
        description_layout.setSpacing(10)

        self.labelDescription = QLabel()
        self.labelDescription.setStyleSheet(
            f"border: none; font-size: 13px; color: {T.TEXT_ACCENT_DARK}; background-color: transparent;"
        )
        self.labelDescription.setWordWrap(True)
        self.labelDescription.setSizePolicy(
            self.sizePolicy().Policy.Expanding,
            self.sizePolicy().Policy.Preferred
        )
        description_layout.addWidget(self.labelDescription)

        self.btnEdit = QPushButton("✏️ Редактировать")
        self.btnEdit.setMinimumSize(90, 28)
        self.btnEdit.setMaximumSize(90, 28)
        self.btnEdit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnEdit.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.BTN_EDIT_BG};
                color: {T.ACCENT_PRIMARY};
                border: 1px solid {T.ACCENT_PRIMARY};
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {T.ACCENT_PRIMARY};
                color: {T.TEXT_ON_ACCENT};
            }}
            QPushButton:pressed {{
                background-color: {T.ACCENT_HOVER_SOFT};
            }}
        """)
        description_layout.addWidget(self.btnEdit)

        left_layout.addLayout(description_layout)

        # Информационная строка (дата, время, продолжительность, удаление)
        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)

        self.labelDateIcon = QLabel("📅")
        self.labelDateIcon.setStyleSheet("border: none; font-size: 13px; background-color: transparent;")
        info_layout.addWidget(self.labelDateIcon)

        self.labelDate = QLabel()
        self.labelDate.setStyleSheet(
            f"border: none; font-size: 13px; color: {T.TEXT_SUCCESS}; font-weight: bold; background-color: transparent;"
        )
        info_layout.addWidget(self.labelDate)

        self.labelTimeIcon = QLabel("⏰")
        self.labelTimeIcon.setStyleSheet("border: none; font-size: 13px; background-color: transparent;")
        info_layout.addWidget(self.labelTimeIcon)

        self.labelTime = QLabel()
        self.labelTime.setStyleSheet(
            f"border: none; font-size: 13px; color: {T.TEXT_ACCENT_DARK}; background-color: transparent;"
        )
        info_layout.addWidget(self.labelTime)

        self.labelDurationIcon = QLabel("⏱️")
        self.labelDurationIcon.setStyleSheet("border: none; font-size: 13px; background-color: transparent;")
        info_layout.addWidget(self.labelDurationIcon)

        self.labelDuration = QLabel()
        self.labelDuration.setStyleSheet(
            f"border: none; font-size: 13px; color: {T.ACCENT_PRIMARY}; font-weight: bold; background-color: transparent;"
        )
        info_layout.addWidget(self.labelDuration)

        self.btnDelete = QPushButton("🗑️ Удалить")
        self.btnDelete.setMinimumSize(80, 28)
        self.btnDelete.setMaximumSize(80, 28)
        self.btnDelete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnDelete.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.BTN_DELETE_BG};
                color: {T.BTN_DELETE_TEXT};
                border: 1px solid {T.BTN_DELETE_BORDER};
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {T.BTN_DELETE_TEXT};
                color: {T.TEXT_ON_ACCENT};
            }}
            QPushButton:pressed {{
                background-color: {T.BTN_DELETE_PRESSED_BG};
            }}
        """)
        info_layout.addWidget(self.btnDelete)

        info_spacer = QSpacerItem(40, 20, QSpacerItem.SizePolicy.Expanding, QSpacerItem.SizePolicy.Minimum)
        info_layout.addItem(info_spacer)

        left_layout.addLayout(info_layout)
        main_layout.addLayout(left_layout)

        # Стили для карточки
        self.setStyleSheet(f"""
            QFrame#OvertimeCard {{
                background-color: {T.BG_CARD};
                border: 1px solid {T.BORDER_DEFAULT};
                border-radius: 10px;
            }}
            QFrame#OvertimeCard:hover {{
                border: 2px solid {T.ACCENT_PRIMARY};
                background-color: {T.BG_HOVER_ACCENT_SOFT};
            }}
        """)
        self.setObjectName("OvertimeCard")
        self.setMinimumSize(400, 120)
        self.setMaximumSize(16777215, 200)

    def _setup_card(self):
        """Настройка карточки"""
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def _populate_data(self):
        """Заполнение карточки данными"""
        # ФИО сотрудника
        self.labelEmployee.setText(self.data.get('employee_name', 'Не указан'))

        # Дата создания (если есть)
        created_at = self.data.get('created_at', '')
        if created_at:
            self.labelCreatedAt.setText(f"Создана: {created_at}")
        else:
            self.labelCreatedAt.setText("")

        # Описание
        description = self.data.get('description', '')
        if description:
            self.labelDescription.setText(description)
        else:
            self.labelDescription.setText("(Нет описания)")
            self.labelDescription.setStyleSheet(
                f"border: none; font-size: 13px; color: {T.TEXT_MUTED_WARM}; "
                f"font-style: italic; background-color: transparent;"
            )

        # Дата выполнения
        date_value = self.data.get('date', '')
        if date_value:
            self.labelDate.setText(date_value)
        else:
            self.labelDate.setText("Не указана")

        # Время
        start_time = self.data.get('start_time', '')
        end_time = self.data.get('end_time', '')
        if start_time and end_time:
            self.labelTime.setText(f"{start_time} - {end_time}")
        else:
            self.labelTime.setText("Время не указано")

        # Продолжительность
        duration = self.data.get('duration', 0)
        self.labelDuration.setText(f"{duration:.2f} ч.")

    def _connect_signals(self):
        """Подключение сигналов кнопок"""
        self.btnEdit.clicked.connect(self._on_edit_clicked)
        self.btnDelete.clicked.connect(self._on_delete_clicked)

    def _on_edit_clicked(self):
        """Обработчик нажатия кнопки редактирования"""
        self.edit_clicked.emit(self.overtime_id)

    def _on_delete_clicked(self):
        # Используем кастомный диалог удаления
        if DeleteDialog.show_confirmation(self):
            self.delete_clicked.emit(self.overtime_id)

    def update_data(self, new_data: dict):
        """
        Обновление данных карточки

        Args:
            new_data: Новые данные карточки
        """
        self.data.update(new_data)
        self._populate_data()

    def get_overtime_id(self) -> int:
        """Получение ID записи"""
        return self.overtime_id

    def get_data(self) -> dict:
        """Получение данных карточки"""
        return self.data.copy()


# Пример использования карточки в родительском виджете
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QScrollArea, QVBoxLayout, QWidget


    class TestWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Тест карточки сверхурочной работы")
            self.setGeometry(100, 100, 650, 500)

            # Создаём скролл-область
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background-color: #F5F5F5; }")

            # Контейнер для карточек
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setSpacing(15)
            layout.setContentsMargins(20, 20, 20, 20)

            # Тестовые данные
            test_data = [
                {
                    'employee_name': 'Иванов Иван Иванович',
                    'created_at': '01.06.2026',
                    'description': 'Срочный проект - подготовка отчётности для налоговой инспекции',
                    'date': '15.06.2026',
                    'start_time': '18:00',
                    'end_time': '20:00',
                    'duration': 2.0
                },
                {
                    'employee_name': 'Петрова Анна Сергеевна',
                    'created_at': '02.06.2026',
                    'description': 'Разработка презентации для заказчика',
                    'date': '16.06.2026',
                    'start_time': '19:00',
                    'end_time': '21:30',
                    'duration': 2.5
                },
                {
                    'employee_name': 'Сидоров Алексей Владимирович',
                    'created_at': '03.06.2026',
                    'description': '',
                    'date': '17.06.2026',
                    'start_time': '17:30',
                    'end_time': '19:00',
                    'duration': 1.5
                }
            ]

            # Создаём карточки
            self.cards = []
            for i, data in enumerate(test_data):
                card = OvertimeCard(i + 1, data)
                card.edit_clicked.connect(self.on_edit)
                card.delete_clicked.connect(self.on_delete)
                layout.addWidget(card)
                self.cards.append(card)

            # Добавляем растяжку в конец
            layout.addStretch()

            scroll.setWidget(container)

            # Основной layout
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.addWidget(scroll)

        def on_edit(self, overtime_id):
            print(f"Редактирование записи ID: {overtime_id}")
            QMessageBox.information(self, "Редактирование", f"Редактирование записи #{overtime_id}")

        def on_delete(self, overtime_id):
            print(f"Удаление записи ID: {overtime_id}")
            QMessageBox.information(self, "Удаление", f"Запись #{overtime_id} удалена")


    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())