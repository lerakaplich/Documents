import os
from PyQt6.QtWidgets import QWidget, QLineEdit
from PyQt6.QtGui import QIcon, QValidator
from PyQt6.QtCore import pyqtSignal, QThread, QObject, Qt
from PyQt6.uic import loadUi
import logging

from client.core.settings.settings_manager import SettingsManager
from client.core.state.app_state import AppState

logger = logging.getLogger(__name__)


class BelarusianPhoneValidator(QValidator):
    """Валидатор маски +375 (__) ___-__-__"""

    def validate(self, input_str: str, pos: int):
        digits = ''.join(filter(str.isdigit, input_str))

        # Автоподстановка 375, если пользователь очистил поле
        if not digits.startswith("375"):
            digits = "375"

        # Обрезка до 12 цифр
        digits = digits[:12]

        formatted = self._format_phone(digits)

        # Если ровно 12 цифр — поле полностью заполнено
        if len(digits) == 12:
            return QValidator.State.Acceptable, formatted, pos

        return QValidator.State.Intermediate, formatted, pos

    @staticmethod
    def _format_phone(digits: str) -> str:
        d = digits[3:]  # отсекаем 375
        c_code = d[:2].ljust(2, '_')
        p1 = d[2:5].ljust(3, '_')
        p2 = d[5:7].ljust(2, '_')
        p3 = d[7:9].ljust(2, '_')

        return f"+375 ({c_code}) {p1}-{p2}-{p3}"

class LoginWorker(QObject):
    """Рабочий поток для выполнения запроса входа"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, phone: str, password: str, remember_me: bool):
        super().__init__()
        self.phone = phone
        self.password = password
        self.remember_me = remember_me

    def run(self):
        try:
            app_state = AppState()
            result = app_state.auth_service.login(
                self.phone,
                self.password,
                self.remember_me
            )

            if "user" in result:
                user_data = result["user"]
            else:
                try:
                    user_data = app_state.employee_service.get_my_profile()
                    result["user"] = user_data
                except Exception as e:
                    logger.warning(f"Не удалось получить профиль пользователя: {e}")
                    user_data = {}

            app_state.set_user(user_data)
            self.finished.emit(result)

        except Exception as e:
            logger.error(f"Ошибка входа: {e}")
            self.error.emit(str(e))


class AuthWidget(QWidget):
    login_successful = pyqtSignal(dict)
    forgot_password_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ui_path = os.path.join(self.root_dir, "ui", "login", "auth_widget.ui")

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI файл не найден: {ui_path}")

        loadUi(ui_path, self)
        self._apply_checkbox_icons()

        self.notification_manager = None
        self.eye_closed_path = os.path.join(self.root_dir, "icons", "eye-closed.svg")
        self.eye_open_path = os.path.join(self.root_dir, "icons", "eye-open.svg")

        # --- НАСТРОЙКА ВВОДА ТЕЛЕФОНА С МАСКОЙ ---
        if hasattr(self, 'phoneInput'):
            self.phoneInput.setInputMask("+375 (99) 999-99-99;_")

            # Настраиваем тонкий курсор каретки без изменения остальных стилей
            self.phoneInput.setStyleSheet("""
                        QLineEdit {
                            background-color: white;
                            border: 2px solid #D22730;
                            border-radius: 15px;
                            padding: 12px 22px;
                            font-size: 24px;
                            color: #1B232A;
                            caret-color: #1B232A; /* Тонкая линия цвета текста */
                        }
                    """)

            self.phoneInput.textChanged.connect(self._on_phone_changed)

        # Подключаем переключение видимости пароля
        if hasattr(self, 'togglePasswordButton') and hasattr(self, 'passwordInput'):
            self.togglePasswordButton.clicked.connect(self._toggle_password_visibility)
            self._update_eye_icon()

        if hasattr(self, 'loginButton'):
            self.loginButton.clicked.connect(self._on_login_clicked)

        if hasattr(self, 'rememberCheckBox'):
            self.rememberCheckBox.stateChanged.connect(self._on_remember_me_changed)

        if hasattr(self, 'forgotPasswordButton'):
            self.forgotPasswordButton.setEnabled(False)
            self.forgotPasswordButton.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #999999;
                    font-size: 21px;
                    border: none;
                    text-decoration: underline;
                }
                QPushButton:hover {
                    color: #666666;
                }
                QPushButton:enabled {
                    color: #D22730;
                }
                QPushButton:enabled:hover {
                    color: #B81C24;
                }
            """)
            self.forgotPasswordButton.clicked.connect(self._on_forgot_password_clicked)

        # Предзаполнение из сохранённой сессии
        session = SettingsManager().get_auth_session()
        if session.get("phone") and hasattr(self, 'phoneInput'):
            self.phoneInput.setText(session["phone"])
            if hasattr(self, 'rememberCheckBox'):
                self.rememberCheckBox.setChecked(True)

    def _get_clean_phone(self) -> str:
        """Возвращает чистые цифры из поля ввода (например: 375291234567)"""
        if not hasattr(self, 'phoneInput'):
            return ""
        return ''.join(filter(str.isdigit, self.phoneInput.text()))

    def _is_valid_phone(self, phone: str = None) -> bool:
        """
        Проверяет, содержит ли номер РОВНО 12 цифр и начинается ли с 375
        """
        digits = self._get_clean_phone() if phone is None else ''.join(filter(str.isdigit, phone))
        return len(digits) == 12 and digits.startswith('375')

    def _on_phone_changed(self, text):
        """Обработчик изменения номера телефона"""
        is_valid = self._is_valid_phone()

        if hasattr(self, 'forgotPasswordButton'):
            self.forgotPasswordButton.setEnabled(is_valid)
            if is_valid:
                self.forgotPasswordButton.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.forgotPasswordButton.setCursor(Qt.CursorShape.ArrowCursor)

    def _on_forgot_password_clicked(self):
        if not self._is_valid_phone():
            if self.notification_manager:
                self.notification_manager.show_notification(
                    "Введите полный номер телефона (12 цифр)",
                    duration=3000
                )
            if hasattr(self, 'phoneInput'):
                self.phoneInput.setFocus()
            return

        self.forgot_password_clicked.emit()

    def _on_login_clicked(self):
        clean_phone = self._get_clean_phone()
        password = self.passwordInput.text().strip() if hasattr(self, 'passwordInput') else ""
        remember_me = hasattr(self, 'rememberCheckBox') and self.rememberCheckBox.isChecked()

        # Валидация
        if not self._is_valid_phone(clean_phone):
            if self.notification_manager:
                self.notification_manager.show_notification(
                    "Введите корректный номер телефона полностью",
                    duration=3000
                )
            return

        if not password:
            if self.notification_manager:
                self.notification_manager.show_notification(
                    "Введите пароль",
                    duration=3000
                )
            return

        # Отправляем на бэкенд чистый номер с '+' (например, +375291234567)
        formatted_phone_for_api = f"+{clean_phone}"

        self.loginButton.setEnabled(False)
        self.loginButton.setText("Вход...")

        self.thread = QThread()
        self.worker = LoginWorker(formatted_phone_for_api, password, remember_me)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_login_success)
        self.worker.error.connect(self._on_login_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.finished.connect(self._cleanup_thread)

        self.thread.start()

    def set_notification_manager(self, manager):
        """Устанавливает менеджер уведомлений"""
        self.notification_manager = manager

    def _toggle_password_visibility(self):
        if hasattr(self, 'passwordInput'):
            if self.passwordInput.echoMode() == QLineEdit.EchoMode.Password:
                self.passwordInput.setEchoMode(QLineEdit.EchoMode.Normal)
            else:
                self.passwordInput.setEchoMode(QLineEdit.EchoMode.Password)
            self._update_eye_icon()

    def _update_eye_icon(self):
        if hasattr(self, 'togglePasswordButton') and hasattr(self, 'passwordInput'):
            if self.passwordInput.echoMode() == QLineEdit.EchoMode.Password:
                icon_path = self.eye_closed_path
            else:
                icon_path = self.eye_open_path

            if os.path.exists(icon_path):
                self.togglePasswordButton.setIcon(QIcon(icon_path))

    def _on_remember_me_changed(self, state):
        """Обработчик изменения чекбокса "Запомнить меня" """
        is_checked = state == 2  # Qt.CheckState.Checked
        print(f"Запомнить меня: {is_checked}")

    def _on_login_success(self, result):
        """Успешный вход"""
        self.loginButton.setEnabled(True)
        self.loginButton.setText("Войти")

        user_data = result.get("user", {})

        if self.notification_manager:
            self.notification_manager.show_notification(
                "Добро пожаловать!",
                duration=2000
            )

        self.login_successful.emit(user_data)

    def _apply_checkbox_icons(self):
        """Подставляет золотые иконки чекбокса из папки icons в стиль .ui."""
        if not hasattr(self, 'rememberCheckBox'):
            return

        def _p(name: str) -> str:
            path = os.path.join(self.root_dir, "icons", name).replace("\\", "/")
            return f'"{path}"'  # кавычки обязательны для url() в QSS

        qss = self.rememberCheckBox.styleSheet()
        qss = qss.replace("{ICON_CHECKBOX_UNCHECKED_PATH}", _p("cb_unchecked.svg"))
        qss = qss.replace("{ICON_CHECKBOX_CHECKED_PATH}", _p("cb_checked.svg"))
        self.rememberCheckBox.setStyleSheet(qss)

    def _on_login_error(self, error_msg):
        """Ошибка входа"""
        self.loginButton.setEnabled(True)
        self.loginButton.setText("Войти")

        if self.notification_manager:
            if "401" in error_msg or "Unauthorized" in error_msg:
                self.notification_manager.show_notification(
                    "Неверный номер телефона или пароль",
                    duration=3000
                )
            elif "Connection" in error_msg or "Failed to connect" in error_msg:
                self.notification_manager.show_notification(
                    "Не удалось подключиться к серверу",
                    duration=3000
                )
            else:
                self.notification_manager.show_notification(
                    f"Ошибка: {error_msg[:50]}...",
                    duration=3000
                )

    def _cleanup_thread(self):
        """Очистка потока после завершения"""
        if hasattr(self, 'thread'):
            self.thread.deleteLater()
        if hasattr(self, 'worker'):
            self.worker.deleteLater()