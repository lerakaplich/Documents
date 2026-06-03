import os
import sys
from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем окна редактирования
from client.windows.profile.user_data.email_edit_window import EmailEditWindow
from client.windows.profile.user_data.phone_edit_window import PhoneEditWindow


class ProfileForm(QWidget):
    """Форма профиля сотрудника"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Путь к UI файлу
        ui_path = os.path.join(ROOT_DIR, "ui", "profile", "profile.ui")

        try:
            if os.path.exists(ui_path):
                loadUi(ui_path, self)
                print("ProfileForm: UI загружен успешно")
            else:
                print(f"ProfileForm: UI файл не найден: {ui_path}")
                self.create_fallback_ui()
        except Exception as e:
            print(f"ProfileForm: ошибка загрузки UI - {e}")
            self.create_fallback_ui()

        # Удаляем лишнюю кнопку "Добавить переработку" из вкладки "Мои переработки"
        self.remove_add_button_from_my_overtime()

        # Загрузка тестовых данных
        self.load_test_data()

        # Настройка таблиц
        self.setup_tables()

        # Подключение сигналов
        self.setup_connections()

        # Настройка кнопок редактирования
        self.setup_edit_buttons()

    def remove_add_button_from_my_overtime(self):
        """Удаляем кнопку 'Добавить переработку' из вкладки 'Мои переработки', если она там есть"""
        # Проверяем, есть ли btnAddOvertime во вкладке Мои переработки
        if hasattr(self, 'btnAddOvertime'):
            # Если кнопка существует, проверяем её родителя
            parent = self.btnAddOvertime.parent()
            # Если родитель - вкладка Мои переработки, удаляем кнопку
            if parent and parent.objectName() == "tabMyOvertime":
                self.btnAddOvertime.deleteLater()
                self.btnAddOvertime = None
                print("Кнопка 'Добавить переработку' удалена из вкладки 'Мои переработки'")

    def setup_tables(self):
        """Настройка таблиц"""
        # Настройка таблицы "Мои переработки"
        if hasattr(self, 'myOvertimeTable'):
            self.myOvertimeTable.setColumnCount(4)
            self.myOvertimeTable.setHorizontalHeaderLabels(["Дата", "Часы", "Причина", "Статус"])
            self.myOvertimeTable.horizontalHeader().setStretchLastSection(True)

        # Настройка таблицы "Все переработки"
        if hasattr(self, 'allOvertimeTable'):
            self.allOvertimeTable.setColumnCount(5)
            self.allOvertimeTable.setHorizontalHeaderLabels(["Сотрудник", "Дата", "Часы", "Причина", "Статус"])
            self.allOvertimeTable.horizontalHeader().setStretchLastSection(True)

        # Заполняем тестовыми данными
        self.load_test_overtime_data()

    def load_test_overtime_data(self):
        """Загрузка тестовых данных переработок"""
        # Тестовые данные для "Мои переработки"
        if hasattr(self, 'myOvertimeTable'):
            my_data = [
                ["15.05.2026", "2.5", "Дедлайн проекта", "Согласовано"],
                ["20.05.2026", "1.5", "Исправление багов", "На рассмотрении"],
                ["22.05.2026", "3.0", "Релиз версии", "Черновик"],
            ]
            self.myOvertimeTable.setRowCount(len(my_data))
            for row, row_data in enumerate(my_data):
                for col, value in enumerate(row_data):
                    self.myOvertimeTable.setItem(row, col, QTableWidgetItem(value))

        # Тестовые данные для "Все переработки"
        if hasattr(self, 'allOvertimeTable'):
            all_data = [
                ["Иванов Иван", "15.05.2026", "2.5", "Дедлайн проекта", "Согласовано"],
                ["Петров Петр", "16.05.2026", "1.0", "Консультация", "Согласовано"],
                ["Сидорова Анна", "20.05.2026", "4.0", "Внеплановые задачи", "На рассмотрении"],
                ["Иванов Иван", "22.05.2026", "3.0", "Релиз версии", "Черновик"],
            ]
            self.allOvertimeTable.setRowCount(len(all_data))
            for row, row_data in enumerate(all_data):
                for col, value in enumerate(row_data):
                    self.allOvertimeTable.setItem(row, col, QTableWidgetItem(value))

    def create_fallback_ui(self):
        """Создает простой UI если файл не найден"""
        from PyQt6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QTabWidget, QHBoxLayout, QFrame, QTableWidget, \
            QTableWidgetItem

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        title = QLabel("Профиль сотрудника")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        # Информация о сотруднике
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.Box)
        info_layout = QVBoxLayout(info_frame)

        self.label_position_value = QLabel("Должность: Ведущий разработчик")
        self.label_department_value = QLabel("Отдел: Отдел разработки")
        self.label_phone_value = QLabel("Телефон: +375 (29) 123-45-67")
        self.label_email_value = QLabel("Email: ivan.ivanov@company.by")
        self.label_birth_date_value = QLabel("Дата рождения: 15.05.1985")
        self.label_division_value = QLabel("Подразделение: ИТ-департамент")

        # Создаем кнопки редактирования
        self.btnEditPhone = QPushButton("✏️")
        self.btnEditEmail = QPushButton("✏️")

        # Добавляем в layout с кнопками
        phone_layout = QHBoxLayout()
        phone_layout.addWidget(self.label_phone_value)
        phone_layout.addWidget(self.btnEditPhone)
        phone_layout.addStretch()

        email_layout = QHBoxLayout()
        email_layout.addWidget(self.label_email_value)
        email_layout.addWidget(self.btnEditEmail)
        email_layout.addStretch()

        info_layout.addWidget(self.label_position_value)
        info_layout.addWidget(self.label_department_value)
        info_layout.addLayout(phone_layout)
        info_layout.addLayout(email_layout)
        info_layout.addWidget(self.label_birth_date_value)
        info_layout.addWidget(self.label_division_value)

        main_layout.addWidget(info_frame)

        # Создаем вкладки
        self.tabWidget = QTabWidget()

        # Вкладка "Мои переработки"
        my_overtime_tab = QWidget()
        my_overtime_layout = QVBoxLayout(my_overtime_tab)

        # Кнопка выбора периода (без кнопки добавления)
        self.btnSelectPeriod = QPushButton("Выбрать период")
        my_overtime_layout.addWidget(self.btnSelectPeriod)

        # Таблица
        self.myOvertimeTable = QTableWidget()
        self.myOvertimeTable.setColumnCount(4)
        self.myOvertimeTable.setHorizontalHeaderLabels(["Дата", "Часы", "Причина", "Статус"])
        my_overtime_layout.addWidget(self.myOvertimeTable)

        self.tabWidget.addTab(my_overtime_tab, "Мои переработки")

        # Вкладка "Все переработки"
        all_overtime_tab = QWidget()
        all_overtime_layout = QVBoxLayout(all_overtime_tab)

        # Верхняя панель с фильтрами и кнопками
        filters_layout = QHBoxLayout()

        from PyQt6.QtWidgets import QComboBox
        self.comboDepartment = QComboBox()
        self.comboDepartment.addItem("Все отделы")
        self.comboDepartment.addItem("Отдел разработки")
        self.comboDepartment.addItem("Отдел тестирования")
        self.comboDepartment.addItem("Отдел аналитики")
        filters_layout.addWidget(self.comboDepartment)

        self.btnSelectPeriodAll = QPushButton("Выбрать период")
        self.btnClearFilters = QPushButton("Сбросить фильтр")
        self.btnExport = QPushButton("Экспорт")
        self.btnAddOvertimeAll = QPushButton("+ Добавить переработку")

        filters_layout.addWidget(self.btnSelectPeriodAll)
        filters_layout.addWidget(self.btnClearFilters)
        filters_layout.addWidget(self.btnExport)
        filters_layout.addStretch()
        filters_layout.addWidget(self.btnAddOvertimeAll)

        all_overtime_layout.addLayout(filters_layout)

        # Таблица
        self.allOvertimeTable = QTableWidget()
        self.allOvertimeTable.setColumnCount(5)
        self.allOvertimeTable.setHorizontalHeaderLabels(["Сотрудник", "Дата", "Часы", "Причина", "Статус"])
        all_overtime_layout.addWidget(self.allOvertimeTable)

        self.tabWidget.addTab(all_overtime_tab, "Все переработки")

        main_layout.addWidget(self.tabWidget)

        # Загружаем тестовые данные для fallback UI
        self.load_test_overtime_data()

    def setup_edit_buttons(self):
        """Настройка кнопок редактирования с эффектами тени"""
        # Стиль для QToolButton (из UI файла)
        tool_btn_style = """
            QToolButton {
                background-color: transparent;
                color: #ccab6e;
                font-size: 20px;
                border: none;
                border-radius: 8px;
                padding: 5px;
            }
            QToolButton:hover {
                color: #b8944a;
                background-color: #bdbdbd;
            }
            QToolButton:pressed {
                color: #7a6a50;
                background-color: #757575;
            }
        """

        # Стиль для QPushButton (fallback UI)
        push_btn_style = """
            QPushButton {
                background-color: transparent;
                color: #ccab6e;
                font-size: 20px;
                border: none;
                border-radius: 8px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #b8944a;
                background-color: rgba(204, 171, 110, 0.1);
            }
            QPushButton:pressed {
                color: #7a6a50;
                background-color: rgba(204, 171, 110, 0.2);
            }
        """

        # Настройка кнопки телефона
        if hasattr(self, 'btnEditPhone') and self.btnEditPhone:
            if 'QToolButton' in str(type(self.btnEditPhone)):
                self.btnEditPhone.setStyleSheet(tool_btn_style)
            else:
                self.btnEditPhone.setStyleSheet(push_btn_style)
            self.btnEditPhone.setText("✏️")
            self.btnEditPhone.setMinimumSize(30, 30)

        # Настройка кнопки email
        if hasattr(self, 'btnEditEmail') and self.btnEditEmail:
            if 'QToolButton' in str(type(self.btnEditEmail)):
                self.btnEditEmail.setStyleSheet(tool_btn_style)
            else:
                self.btnEditEmail.setStyleSheet(push_btn_style)
            self.btnEditEmail.setText("✏️")
            self.btnEditEmail.setMinimumSize(30, 30)

    def setup_connections(self):
        """Подключение сигналов к слотам"""
        # Вкладка "Мои переработки"
        if hasattr(self, 'btnSelectPeriod') and self.btnSelectPeriod:
            self.btnSelectPeriod.clicked.connect(self.on_select_period_clicked)

        # Вкладка "Все переработки"
        if hasattr(self, 'btnAddOvertimeAll') and self.btnAddOvertimeAll:
            self.btnAddOvertimeAll.clicked.connect(self.on_add_overtime_all_clicked)

        if hasattr(self, 'btnSelectPeriodAll') and self.btnSelectPeriodAll:
            self.btnSelectPeriodAll.clicked.connect(self.on_select_period_all_clicked)

        if hasattr(self, 'btnClearFilters') and self.btnClearFilters:
            self.btnClearFilters.clicked.connect(self.on_clear_filters_clicked)

        if hasattr(self, 'btnExport') and self.btnExport:
            self.btnExport.clicked.connect(self.on_export_clicked)

        if hasattr(self, 'comboDepartment') and self.comboDepartment:
            self.comboDepartment.currentTextChanged.connect(self.on_department_filter_changed)

        # Кнопки редактирования
        if hasattr(self, 'btnEditPhone') and self.btnEditPhone:
            self.btnEditPhone.clicked.connect(self.on_edit_phone_clicked)

        if hasattr(self, 'btnEditEmail') and self.btnEditEmail:
            self.btnEditEmail.clicked.connect(self.on_edit_email_clicked)

    def load_test_data(self):
        """Загрузка тестовых данных профиля"""
        profile_data = {
            "position": "Ведущий разработчик",
            "department": "Отдел разработки",
            "phone": "+375291234567",
            "email": "ivan.ivanov@company.by",
            "birth_date": "15.05.1985",
            "division": "ИТ-департамент"
        }

        if hasattr(self, 'label_position_value') and self.label_position_value:
            self.label_position_value.setText(profile_data["position"])

        if hasattr(self, 'label_department_value') and self.label_department_value:
            self.label_department_value.setText(profile_data["department"])

        if hasattr(self, 'label_phone_value') and self.label_phone_value:
            formatted_phone = self.format_phone_display(profile_data["phone"])
            self.label_phone_value.setText(formatted_phone)

        if hasattr(self, 'label_email_value') and self.label_email_value:
            self.label_email_value.setText(profile_data["email"])

        if hasattr(self, 'label_birth_date_value') and self.label_birth_date_value:
            self.label_birth_date_value.setText(profile_data["birth_date"])

        if hasattr(self, 'label_division_value') and self.label_division_value:
            self.label_division_value.setText(profile_data["division"])

        # Сохраняем чистые данные для редактирования
        self.current_phone_raw = profile_data["phone"]
        self.current_email_raw = profile_data["email"]

    def format_phone_display(self, phone: str) -> str:
        """Форматирует номер телефона для отображения"""
        if len(phone) == 12 and phone.isdigit():
            return f"+{phone[:3]} ({phone[3:5]}) {phone[5:8]}-{phone[8:10]}-{phone[10:12]}"
        return phone

    def on_edit_phone_clicked(self):
        """Редактирование телефона"""
        try:
            dialog = PhoneEditWindow(self.current_phone_raw, parent=None)
            dialog.phone_updated.connect(self.on_phone_updated)
            dialog.exec()
        except Exception as e:
            print(f"Ошибка открытия окна редактирования телефона: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть окно редактирования телефона\n{str(e)}")

    def on_phone_updated(self, new_phone: str):
        """Обработчик обновления телефона"""
        self.current_phone_raw = new_phone
        if hasattr(self, 'label_phone_value') and self.label_phone_value:
            formatted_phone = self.format_phone_display(new_phone)
            self.label_phone_value.setText(formatted_phone)
        print(f"Телефон обновлен: +{new_phone}")
        QMessageBox.information(self, "Успешно", f"Номер телефона успешно обновлен\n+{new_phone}")

    def on_edit_email_clicked(self):
        """Редактирование email"""
        try:
            dialog = EmailEditWindow(self.current_email_raw, parent=None)
            dialog.email_updated.connect(self.on_email_updated)
            dialog.exec()
        except Exception as e:
            print(f"Ошибка открытия окна редактирования email: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть окно редактирования email\n{str(e)}")

    def on_email_updated(self, new_email: str):
        """Обработчик обновления email"""
        self.current_email_raw = new_email
        if hasattr(self, 'label_email_value') and self.label_email_value:
            display_email = new_email if new_email else "Не указан"
            self.label_email_value.setText(display_email)
        print(f"Email обновлен: {new_email}")

        if new_email:
            QMessageBox.information(self, "Успешно", f"Email успешно обновлен\n{new_email}")
        else:
            QMessageBox.information(self, "Успешно", "Email успешно удален")

    def on_select_period_clicked(self):
        """Выбор периода (мои переработки)"""
        QMessageBox.information(self, "Выбор периода", "Открыть календарь для выбора периода")

    def on_add_overtime_all_clicked(self):
        """Добавление переработки (все)"""
        QMessageBox.information(self, "Добавление переработки",
                                "Открыть форму создания карточки переработки для сотрудника")

    def on_select_period_all_clicked(self):
        """Выбор периода (все переработки)"""
        QMessageBox.information(self, "Выбор периода", "Открыть календарь для выбора периода")

    def on_clear_filters_clicked(self):
        """Сброс фильтров"""
        if hasattr(self, 'comboDepartment') and self.comboDepartment:
            self.comboDepartment.setCurrentIndex(0)
        QMessageBox.information(self, "Фильтры", "Фильтры сброшены")

    def on_export_clicked(self):
        """Экспорт данных"""
        QMessageBox.information(self, "Экспорт", "Экспорт данных в Excel/PDF")

    def on_department_filter_changed(self, department: str):
        """Изменение фильтра по отделу"""
        if department:
            print(f"Фильтр по отделу: {department}")


# Добавляем импорт для QTableWidgetItem
from PyQt6.QtWidgets import QTableWidgetItem

# Пример запуска для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProfileForm()
    window.setWindowTitle("Профиль сотрудника")
    window.setGeometry(100, 100, 920, 820)
    window.show()
    sys.exit(app.exec())