import os
import sys
import traceback
from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox, QFormLayout, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QFrame
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

from client.windows.profile.overtime.overtime_panel import OvertimePanel
from client.windows.profile.profile_info import ProfileInfo

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def global_exception_handler(exctype, value, tb):
    print("=" * 80)
    print("ГЛОБАЛЬНОЕ ИСКЛЮЧЕНИЕ:")
    print(f"Тип: {exctype}")
    print(f"Значение: {value}")
    print("Трассировка:")
    traceback.print_tb(tb)
    print("=" * 80)
    sys.__excepthook__(exctype, value, tb)


sys.excepthook = global_exception_handler


class ProfileForm(QWidget):
    """Главная форма профиля, объединяет ProfileInfo и OvertimePanel."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Загрузка UI
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

        # Создаём компоненты
        self.profile_info = ProfileInfo(self)
        self.overtime_panel = OvertimePanel(self)

        # Передаём виджеты в компоненты
        self.profile_info.setup_ui_elements(
            infoFrame=self.infoFrame,
            labelTitle=self.labelTitle,
            label_position_value=self.label_position_value,
            label_phone_value=self.label_phone_value,
            label_email_value=self.label_email_value,
            label_birth_date_value=self.label_birth_date_value,
            btnEditPhone=self.btnEditPhone,
            btnEditEmail=self.btnEditEmail,
            mainLayout=self.mainLayout
        )

        self.overtime_panel.setup_ui_elements(
            tabWidget=self.tabWidget,
            btnSelectPeriod=self.btnSelectPeriod,
            btnSelectPeriodAll=self.btnSelectPeriodAll,
            btnResetFilters=self.btnResetFilters,
            btnResetFiltersAll=self.btnResetFiltersAll,
            btnAddOvertimeAll=self.btnAddOvertimeAll,
            btnExport=self.btnExport,
            labelTotalHoursMy=self.labelTotalHoursMy,
            labelTotalHoursAll=self.labelTotalHoursAll,
            allOvertimeFiltersLayout=self.allOvertimeFiltersLayout,
            btnAddOvertime=self.btnAddOvertime if hasattr(self, 'btnAddOvertime') else None
        )

        # Стилизация кнопок редактирования
        self.setup_edit_buttons()

        # Подключение сигналов
        self.setup_connections()

        # Загрузка тестовых данных
        self.load_test_data()
        self.load_overtime_data()

    def setup_edit_buttons(self):
        """Устанавливает стиль для кнопок редактирования телефона и email."""
        style = """
            QToolButton, QPushButton {
                background-color: transparent;
                color: #ccab6e;
                font-size: 20px;
                border: none;
                border-radius: 8px;
                padding: 5px;
            }
            QToolButton:hover, QPushButton:hover {
                color: #b8944a;
                background-color: rgba(204, 171, 110, 0.1);
            }
            QToolButton:pressed, QPushButton:pressed {
                color: #7a6a50;
                background-color: rgba(204, 171, 110, 0.2);
            }
        """
        if hasattr(self, 'btnEditPhone') and self.btnEditPhone:
            self.btnEditPhone.setStyleSheet(style)
            self.btnEditPhone.setText("✏️")
            self.btnEditPhone.setMinimumSize(30, 30)

        if hasattr(self, 'btnEditEmail') and self.btnEditEmail:
            self.btnEditEmail.setStyleSheet(style)
            self.btnEditEmail.setText("✏️")
            self.btnEditEmail.setMinimumSize(30, 30)

    def setup_connections(self):
        """Подключает сигналы кнопок и фильтров."""
        # Кнопки периода
        if hasattr(self, 'btnSelectPeriod') and self.btnSelectPeriod:
            self.btnSelectPeriod.clicked.connect(self.overtime_panel.on_select_period_clicked)
        if hasattr(self, 'btnSelectPeriodAll') and self.btnSelectPeriodAll:
            self.btnSelectPeriodAll.clicked.connect(self.overtime_panel.on_select_period_all_clicked)

        # Кнопки сброса
        if hasattr(self, 'btnResetFilters') and self.btnResetFilters:
            self.btnResetFilters.clicked.connect(self.overtime_panel.reset_my_filters)
        if hasattr(self, 'btnResetFiltersAll') and self.btnResetFiltersAll:
            self.btnResetFiltersAll.clicked.connect(self.overtime_panel.reset_all_filters)

        # Добавление переработки
        if hasattr(self, 'btnAddOvertimeAll') and self.btnAddOvertimeAll:
            self.btnAddOvertimeAll.clicked.connect(self.overtime_panel.on_add_overtime_all_clicked)

        # Экспорт
        if hasattr(self, 'btnExport') and self.btnExport:
            self.btnExport.clicked.connect(self.overtime_panel.on_export_clicked)

        # Сигналы редактирования телефона/email уже подключены внутри ProfileInfo

    def load_test_data(self):
        """Загружает тестовые данные профиля."""
        print("load_test_data вызван")
        department_chain = [
            ("Отдел", "Телематика"),
            ("Подразделение", "НТЦ"),
            ("Сектор", "Разработки")
        ]
        self.profile_info.update_profile(
            full_name="Иванов Иван Петрович",
            position="Ведущий разработчик",
            department_chain=department_chain,
            phone="375291234567",
            email="ivan.ivanov@company.by",
            birth_date="15.05.1985"
        )

    def load_overtime_data(self):
        """Загружает переработки (без фильтров)."""
        self.overtime_panel.load_overtime_data()

    def create_fallback_ui(self):
        """Создаёт простой UI, если не удалось загрузить profile.ui."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Профиль сотрудника")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        self.infoFrame = QFrame()
        self.infoFrame.setFrameStyle(QFrame.Shape.Box)
        self.infoFrame.setLayout(QFormLayout())
        main_layout.addWidget(self.infoFrame)

        self.label_position_value = QLabel()
        self.label_phone_value = QLabel()
        self.label_email_value = QLabel()
        self.label_birth_date_value = QLabel()
        self.btnEditPhone = QPushButton("✏️")
        self.btnEditEmail = QPushButton("✏️")
        self.tabWidget = QTabWidget()
        main_layout.addWidget(self.tabWidget)

        # Передаём в компоненты (часть виджетов может отсутствовать)
        self.profile_info.setup_ui_elements(
            infoFrame=self.infoFrame,
            labelTitle=title,
            label_position_value=self.label_position_value,
            label_phone_value=self.label_phone_value,
            label_email_value=self.label_email_value,
            label_birth_date_value=self.label_birth_date_value,
            btnEditPhone=self.btnEditPhone,
            btnEditEmail=self.btnEditEmail,
            mainLayout=main_layout
        )
        # Для overtime_panel необходимо создать фиктивные виджеты, но в этом случае
        # лучше просто не использовать overtime, либо доработать.
        # Здесь оставляем заглушку.
        self.load_test_data()
        self.load_overtime_data()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProfileForm()
    window.setWindowTitle("Профиль сотрудника")
    window.setGeometry(100, 100, 920, 820)
    window.show()
    sys.exit(app.exec())