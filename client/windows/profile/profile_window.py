import json
import os
import sys
import traceback
import requests
from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox, QFormLayout, QLabel, QVBoxLayout, QHBoxLayout, \
    QPushButton, QTabWidget, QFrame
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.uic import loadUi

from client.windows.profile.overtime.overtime_panel import OvertimePanel
from client.windows.profile.profile_info import ProfileInfo
from client.core.http_client import HttpClient
from client.services.employee_service import EmployeeService

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


# ===== ProfileLoader - класс для загрузки данных в отдельном потоке =====
# client/windows/profile/profile_window.py
class ProfileLoader(QThread):
    """Загрузка профиля в отдельном потоке"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, http_client: HttpClient, use_current_user: bool = True):
        super().__init__()
        self.http_client = http_client
        self.use_current_user = use_current_user  # True = /me, False = /{id}

    def run(self):
        try:
            service = EmployeeService(self.http_client)

            if self.use_current_user:
                # Используем /me для текущего пользователя
                print("📥 Загружаем профиль текущего пользователя (/me)")
                data = service.get_my_profile()
            else:
                # Или загружаем конкретного сотрудника (для отладки)
                print("📥 Загружаем сотрудника с ID: 1")
                data = service.get_employee(1)

            self.finished.emit(data)

        except requests.exceptions.ConnectionError:
            self.error.emit("Не удалось подключиться к серверу. Проверьте, что сервер запущен.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.error.emit(f"Ошибка авторизации. Токен истек или неверный.\n{e.response.text}")
            elif e.response.status_code == 404:
                self.error.emit("Профиль пользователя не найден.")
            else:
                self.error.emit(f"Ошибка сервера: {e.response.status_code}\n{e.response.text}")
        except Exception as e:
            self.error.emit(f"Ошибка загрузки профиля: {str(e)}")



# ===== Конец класса ProfileLoader =====

class ProfileForm(QWidget):
    """Главная форма профиля, объединяет ProfileInfo и OvertimePanel."""

    def __init__(self, parent=None, employee_id: int = None):
        super().__init__(parent)

        # Если передан employee_id - загружаем конкретного, иначе - текущего
        self.employee_id = employee_id
        self.use_current_user = employee_id is None  # ← Если ID нет - используем /me

        if self.use_current_user:
            print("👤 Загружаем профиль текущего пользователя")
        else:
            print(f"👤 Загружаем профиль сотрудника с ID: {self.employee_id}")

        # ===== Инициализация HTTP клиента с реальным токеном =====
        self.base_url = "http://localhost:8000/api/v1"
        # ВСТАВЬТЕ ВАШ ТОКЕН СЮДА:
        self.token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwic2VydmljZV9udW1iZXIiOiJNQVowMDEiLCJpc19sZWFkZXIiOnRydWUsImV4cCI6MTc4NjQ0OTY3MH0.INMWABaTjeBYztZeZ835DG4RUWSo-SIgvVLjplQh6Os"

        self.http_client = HttpClient(self.base_url, self.token)

        self.http_client = HttpClient(self.base_url, self.token)
        # ===== Конец инициализации HTTP клиента =====

        # ===== Загрузка UI =====
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
        # ===== Конец загрузки UI =====

        # ===== Создаём компоненты =====
        self.profile_info = ProfileInfo(self)
        self.overtime_panel = OvertimePanel(self)
        # ===== Конец создания компонентов =====

        # ===== Передаём виджеты в компоненты =====
        self.profile_info.setup_ui_elements(
            infoFrame=self.infoFrame if hasattr(self, 'infoFrame') else None,
            labelTitle=self.labelTitle if hasattr(self, 'labelTitle') else None,
            label_position_value=self.label_position_value if hasattr(self, 'label_position_value') else None,
            label_phone_value=self.label_phone_value if hasattr(self, 'label_phone_value') else None,
            label_email_value=self.label_email_value if hasattr(self, 'label_email_value') else None,
            label_birth_date_value=self.label_birth_date_value if hasattr(self, 'label_birth_date_value') else None,
            btnEditPhone=self.btnEditPhone if hasattr(self, 'btnEditPhone') else None,
            btnEditEmail=self.btnEditEmail if hasattr(self, 'btnEditEmail') else None,
            mainLayout=self.mainLayout if hasattr(self, 'mainLayout') else None
        )

        # Передаем HTTP клиент в ProfileInfo для редактирования
        self.profile_info.set_http_client(self.http_client)
        # ===== Конец передачи виджетов =====

        # ===== Настройка overtime panel =====
        if hasattr(self, 'tabWidget'):
            self.overtime_panel.setup_ui_elements(
                tabWidget=self.tabWidget,
                btnSelectPeriod=self.btnSelectPeriod if hasattr(self, 'btnSelectPeriod') else None,
                btnSelectPeriodAll=self.btnSelectPeriodAll if hasattr(self, 'btnSelectPeriodAll') else None,
                btnResetFilters=self.btnResetFilters if hasattr(self, 'btnResetFilters') else None,
                btnResetFiltersAll=self.btnResetFiltersAll if hasattr(self, 'btnResetFiltersAll') else None,
                btnAddOvertimeAll=self.btnAddOvertimeAll if hasattr(self, 'btnAddOvertimeAll') else None,
                btnExport=self.btnExport if hasattr(self, 'btnExport') else None,
                labelTotalHoursMy=self.labelTotalHoursMy if hasattr(self, 'labelTotalHoursMy') else None,
                labelTotalHoursAll=self.labelTotalHoursAll if hasattr(self, 'labelTotalHoursAll') else None,
                allOvertimeFiltersLayout=self.allOvertimeFiltersLayout if hasattr(self,
                                                                                  'allOvertimeFiltersLayout') else None,
                btnAddOvertime=self.btnAddOvertime if hasattr(self, 'btnAddOvertime') else None
            )
        # ===== Конец настройки overtime panel =====

        # ===== Стилизация кнопок =====
        self.setup_edit_buttons()
        # ===== Конец стилизации =====

        # ===== Подключение сигналов =====
        self.setup_connections()
        # ===== Конец подключения сигналов =====

        # ===== Загрузка данных через API =====
        self.load_profile_from_api()
        # ===== Конец загрузки =====

    def load_profile_from_api(self):
        """Загрузка профиля через API в отдельном потоке"""
        if self.profile_info.labelTitle:
            self.profile_info.labelTitle.setText("⏳ Загрузка...")

        # Создаем загрузчик с параметром use_current_user
        self.loader = ProfileLoader(
            self.http_client,
            use_current_user=self.use_current_user
        )
        self.loader.finished.connect(self.on_profile_loaded)
        self.loader.error.connect(self.on_profile_error)
        self.loader.start()
        print("📥 Загрузка профиля начата...")

    def on_profile_loaded(self, data: dict):
        """Обработка успешной загрузки профиля"""
        try:
            print("=" * 60)
            print("✅ ДАННЫЕ ПРОФИЛЯ ПОЛУЧЕНЫ:")
            print("=" * 60)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print("=" * 60)

            # ==== 1. ФИО ====
            # Собираем из отдельных полей
            last_name = data.get('last_name', '')
            first_name = data.get('first_name', '')
            patronymic = data.get('patronymic', '')

            # Формируем полное ФИО
            full_name_parts = []
            if last_name:
                full_name_parts.append(last_name)
            if first_name:
                full_name_parts.append(first_name)
            if patronymic:
                full_name_parts.append(patronymic)

            full_name = ' '.join(full_name_parts) if full_name_parts else 'Не указано'
            print(f"📝 Собрано ФИО: {full_name}")

            # ==== 2. Должность ====
            positions = data.get('positions', [])
            position_name = 'Не указана'
            department_chain = []
            department_ids = []  # Для дополнительной информации

            if positions and len(positions) > 0:
                # Берем первую должность (обычно основная)
                first_position = positions[0]
                position_name = first_position.get('position_name', 'Не указана')

                # Если есть department_id - получаем название отдела
                department_id = first_position.get('department_id')
                if department_id:
                    department_ids.append(department_id)
                    # Пока используем ID, потом можно загрузить название через API
                    department_chain.append(("Отдел", f"ID: {department_id}"))

            print(f"📋 Должность: {position_name}")
            print(f"📋 Отделы: {department_chain}")

            # ==== 3. Телефон ====
            phone = data.get('phone_number', '')
            print(f"📞 Телефон: {phone}")

            # ==== 4. Email ====
            email = data.get('email', '')
            print(f"📧 Email: {email}")

            # ==== 5. Дата рождения ====
            birth_date = data.get('birth_date', 'Не указана')
            # Форматируем дату если нужно
            if birth_date and birth_date != 'Не указана':
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(birth_date)
                    birth_date = dt.strftime('%d.%m.%Y')
                except:
                    pass
            print(f"🎂 Дата рождения: {birth_date}")

            # ==== 6. Дополнительная информация ====
            service_number = data.get('service_number', '')
            rights = data.get('rights', '')
            is_active = data.get('is_active', False)

            print(f"📋 Дополнительно:")
            print(f"  - Табельный номер: {service_number}")
            print(f"  - Права: {rights}")
            print(f"  - Активен: {is_active}")

            # Обновляем профиль
            self.profile_info.update_profile(
                full_name=full_name,
                position=position_name,
                department_chain=department_chain,
                phone=phone,
                email=email,
                birth_date=birth_date
            )

            # Сохраняем данные для редактирования
            self.profile_info.current_phone_raw = phone
            self.profile_info.current_email_raw = email

            # Загружаем переработки
            self.load_overtime_data()

            print("✅ Профиль успешно обновлен")

        except Exception as e:
            print(f"❌ Ошибка обработки данных: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Ошибка", f"Не удалось обработать данные профиля:\n{str(e)}")

    def on_profile_error(self, error_msg: str):
        """Обработка ошибки загрузки профиля"""
        print(f"Ошибка загрузки профиля: {error_msg}")
        QMessageBox.warning(self, "Ошибка загрузки", error_msg)

        # Загружаем тестовые данные, если не удалось загрузить с сервера
        self.load_test_data()

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

    def load_test_data(self):
        """Загружает тестовые данные профиля (для отладки)."""
        print("load_test_data вызван (тестовые данные)")
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
        """Загружает переработки (пока заглушка)."""
        # TODO: Загружать переработки через API
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

        # Передаём в компоненты
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


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Проверяем аргументы командной строки для ID сотрудника
    employee_id = None
    if len(sys.argv) > 1:
        try:
            employee_id = int(sys.argv[1])
        except ValueError:
            pass

    window = ProfileForm(employee_id=employee_id)
    window.setWindowTitle("Профиль сотрудника")
    window.setGeometry(100, 100, 920, 820)
    window.show()
    sys.exit(app.exec())