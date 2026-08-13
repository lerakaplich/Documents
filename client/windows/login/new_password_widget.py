import os
from PyQt6.QtWidgets import QWidget, QLineEdit
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import pyqtSignal, QThread, QObject
from PyQt6.uic import loadUi
import logging
import re

from client.core.state.app_state import AppState

logger = logging.getLogger(__name__)


class ResetPasswordWorker(QObject):
    finished = pyqtSignal(dict)  # Передаем данные пользователя
    error = pyqtSignal(str)

    def __init__(self, phone_number: str, code: str, new_password: str):
        super().__init__()
        self.phone_number = phone_number
        self.code = code
        self.new_password = new_password

    def run(self):
        try:
            app_state = AppState()
            # Нормализуем номер телефона
            clean_phone = re.sub(r'[^\d+]', '', self.phone_number)
            if clean_phone.startswith('375'):
                clean_phone = f'+{clean_phone}'

            logger.info(f"📤 Отправка запроса на сброс пароля для номера: {clean_phone}")
            # Сначала сбрасываем пароль
            app_state.auth_service.reset_password(clean_phone, self.code, self.new_password)

            # Затем выполняем вход с новым паролем
            logger.info(f"🔐 Выполняем вход с новым паролем для {clean_phone}")
            login_result = app_state.auth_service.login(clean_phone, self.new_password, True)

            # Получаем данные пользователя
            try:
                user_data = app_state.employee_service.get_my_profile()
                app_state.set_user(user_data)
                login_result["user"] = user_data
            except Exception as e:
                logger.warning(f"Не удалось получить профиль: {e}")
                user_data = {}

            self.finished.emit(login_result)
        except Exception as e:
            logger.error(f"Ошибка сброса пароля: {e}")
            self.error.emit(str(e))


class NewPasswordWidget(QWidget):
    # Изменяем сигнал - теперь он передает данные пользователя
    password_changed_successfully = pyqtSignal(dict)
    back_to_login = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ui_path = os.path.join(self.root_dir, "ui", "login", "new_password_widget.ui")
        print(f"Загрузка NewPasswordWidget UI: {ui_path}")

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI файл не найден: {ui_path}")

        loadUi(ui_path, self)

        self.notification_manager = None
        self.phone_number = ""
        self.reset_code = ""
        self.eye_closed_path = os.path.join(self.root_dir, "icons", "eye-closed.svg")
        self.eye_open_path = os.path.join(self.root_dir, "icons", "eye-open.svg")

        # Переменные для потоков
        self.thread = None
        self.worker = None

        # Настройка переключения видимости пароля
        if hasattr(self, 'togglePasswordButton') and hasattr(self, 'newPasswordInput'):
            self.togglePasswordButton.clicked.connect(
                lambda: self._toggle_password_visibility('newPasswordInput', 'togglePasswordButton')
            )
            self._update_eye_icon('newPasswordInput', 'togglePasswordButton')

        if hasattr(self, 'toggleConfirmPasswordButton') and hasattr(self, 'confirmPasswordInput'):
            self.toggleConfirmPasswordButton.clicked.connect(
                lambda: self._toggle_password_visibility('confirmPasswordInput', 'toggleConfirmPasswordButton')
            )
            self._update_eye_icon('confirmPasswordInput', 'toggleConfirmPasswordButton')

        if hasattr(self, 'createPasswordButton'):
            self.createPasswordButton.clicked.connect(self._on_create_password)

        if hasattr(self, 'backToLoginButton'):
            self.backToLoginButton.clicked.connect(self._on_back_to_login)

    def set_notification_manager(self, manager):
        """Устанавливает менеджер уведомлений"""
        self.notification_manager = manager

    def set_reset_data(self, phone_number: str, code: str):
        """Устанавливает номер телефона и код для сброса пароля"""
        self.phone_number = phone_number
        self.reset_code = code
        logger.info(f"📱 Установлены данные для сброса: номер {phone_number}, код {code}")

        # Очищаем поля ввода пароля
        if hasattr(self, 'newPasswordInput'):
            self.newPasswordInput.clear()
        if hasattr(self, 'confirmPasswordInput'):
            self.confirmPasswordInput.clear()

        # Устанавливаем фокус на поле нового пароля
        if hasattr(self, 'newPasswordInput'):
            self.newPasswordInput.setFocus()

    def _toggle_password_visibility(self, input_name, button_name):
        password_input = getattr(self, input_name, None)
        toggle_button = getattr(self, button_name, None)

        if password_input and toggle_button:
            if password_input.echoMode() == QLineEdit.EchoMode.Password:
                password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            else:
                password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._update_eye_icon(input_name, button_name)

    def _update_eye_icon(self, input_name, button_name):
        password_input = getattr(self, input_name, None)
        toggle_button = getattr(self, button_name, None)

        if password_input and toggle_button:
            if password_input.echoMode() == QLineEdit.EchoMode.Password:
                icon_path = self.eye_closed_path
            else:
                icon_path = self.eye_open_path

            if os.path.exists(icon_path):
                toggle_button.setIcon(QIcon(icon_path))

    def _validate_password(self, password: str) -> tuple:
        """Валидация пароля"""
        if len(password) < 8:
            return False, "Пароль должен содержать не менее 8 символов!"

        if not any(char.isdigit() for char in password):
            return False, "Пароль должен содержать хотя бы одну цифру!"

        if not any(char.isupper() for char in password):
            return False, "Пароль должен содержать хотя бы одну заглавную букву!"

        if not any(char.islower() for char in password):
            return False, "Пароль должен содержать хотя бы одну строчную букву!"

        return True, ""

    def _on_create_password(self):
        new_password = self.newPasswordInput.text() if hasattr(self, 'newPasswordInput') else ""
        confirm_password = self.confirmPasswordInput.text() if hasattr(self, 'confirmPasswordInput') else ""

        # Проверка, что пароль введен
        if not new_password:
            if self.notification_manager:
                self.notification_manager.show_notification(
                    "Введите новый пароль!",
                    duration=3000
                )
            if hasattr(self, 'newPasswordInput'):
                self.newPasswordInput.setFocus()
            return

        # Проверка, что подтверждение введено
        if not confirm_password:
            if self.notification_manager:
                self.notification_manager.show_notification(
                    "Подтвердите пароль!",
                    duration=3000
                )
            if hasattr(self, 'confirmPasswordInput'):
                self.confirmPasswordInput.setFocus()
            return

        # Проверка совпадения паролей
        if new_password != confirm_password:
            if self.notification_manager:
                self.notification_manager.show_notification(
                    "Пароли не совпадают!",
                    duration=3000
                )
            if hasattr(self, 'confirmPasswordInput'):
                self.confirmPasswordInput.clear()
                self.confirmPasswordInput.setFocus()
            return

        # Валидация пароля
        is_valid, error_message = self._validate_password(new_password)
        if not is_valid:
            if self.notification_manager:
                self.notification_manager.show_notification(
                    error_message,
                    duration=4000
                )
            if hasattr(self, 'newPasswordInput'):
                self.newPasswordInput.clear()
                self.newPasswordInput.setFocus()
            if hasattr(self, 'confirmPasswordInput'):
                self.confirmPasswordInput.clear()
            return

        # Проверка наличия номера телефона и кода
        logger.info(f"🔍 Проверка данных: phone='{self.phone_number}', code='{self.reset_code}'")

        if not self.phone_number or not self.reset_code:
            error_msg = f"Отсутствуют данные: phone={self.phone_number}, code={self.reset_code}"
            logger.error(f"❌ {error_msg}")
            if self.notification_manager:
                try:
                    self.notification_manager.show_notification(
                        "Ошибка: отсутствуют данные для сброса пароля. Попробуйте заново.",
                        duration=4000
                    )
                except Exception as e:
                    logger.error(f"Ошибка при показе уведомления: {e}")
            return

        # Отправляем запрос на сброс пароля
        self._send_reset_password(new_password)

    def _send_reset_password(self, new_password: str):
        """Отправляет запрос на сброс пароля"""
        if hasattr(self, 'createPasswordButton'):
            self.createPasswordButton.setEnabled(False)
            self.createPasswordButton.setText("Сохранение...")

        if self.notification_manager:
            try:
                self.notification_manager.show_notification(
                    "Отправка запроса...",
                    duration=2000
                )
            except Exception as e:
                logger.error(f"Ошибка при показе уведомления: {e}")

        try:
            self.thread = QThread()
            self.worker = ResetPasswordWorker(self.phone_number, self.reset_code, new_password)
            self.worker.moveToThread(self.thread)

            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self._on_reset_password_success)
            self.worker.error.connect(self._on_reset_password_error)
            self.worker.finished.connect(self.thread.quit)
            self.worker.error.connect(self.thread.quit)
            self.thread.finished.connect(self._cleanup_thread)

            self.thread.start()
        except Exception as e:
            logger.error(f"Ошибка при запуске потока сброса пароля: {e}")
            self._on_reset_password_error(str(e))

    def _on_reset_password_success(self, login_result):
        """Успешный сброс пароля и вход"""
        if hasattr(self, 'createPasswordButton'):
            self.createPasswordButton.setEnabled(True)
            self.createPasswordButton.setText("Создать пароль")

        if self.notification_manager:
            try:
                self.notification_manager.show_notification(
                    "✅ Пароль успешно изменен! Выполняется вход...",
                    duration=3000
                )
            except Exception as e:
                logger.error(f"Ошибка при показе уведомления: {e}")

        logger.info("✅ Пароль успешно изменен и выполнена авторизация")

        if hasattr(self, 'newPasswordInput'):
            self.newPasswordInput.clear()
        if hasattr(self, 'confirmPasswordInput'):
            self.confirmPasswordInput.clear()

        # Эмитим сигнал с данными пользователя
        self.password_changed_successfully.emit(login_result)

    def _on_reset_password_error(self, error_msg):
        """Ошибка при сбросе пароля"""
        if hasattr(self, 'createPasswordButton'):
            self.createPasswordButton.setEnabled(True)
            self.createPasswordButton.setText("Создать пароль")

        logger.error(f"❌ Ошибка сброса пароля: {error_msg}")

        if self.notification_manager:
            try:
                if "404" in error_msg:
                    self.notification_manager.show_notification(
                        "❌ Пользователь не найден",
                        duration=3000
                    )
                elif "400" in error_msg or "Invalid" in error_msg:
                    self.notification_manager.show_notification(
                        "❌ Неверный код подтверждения",
                        duration=3000
                    )
                elif "Connection" in error_msg:
                    self.notification_manager.show_notification(
                        "❌ Не удалось подключиться к серверу",
                        duration=3000
                    )
                else:
                    self.notification_manager.show_notification(
                        f"❌ Ошибка: {error_msg[:50]}...",
                        duration=3000
                    )
            except Exception as e:
                logger.error(f"Ошибка при показе уведомления: {e}")

        if hasattr(self, 'newPasswordInput'):
            self.newPasswordInput.clear()
        if hasattr(self, 'confirmPasswordInput'):
            self.confirmPasswordInput.clear()
            self.confirmPasswordInput.setFocus()

    def _on_back_to_login(self):
        """Возврат к окну входа"""
        logger.info("Возврат к окну входа")
        self.back_to_login.emit()

    def _cleanup_thread(self):
        """Очистка потока"""
        try:
            if hasattr(self, 'thread') and self.thread:
                self.thread.deleteLater()
                self.thread = None
            if hasattr(self, 'worker') and self.worker:
                self.worker.deleteLater()
                self.worker = None
        except Exception as e:
            logger.error(f"Ошибка при очистке потока: {e}")

    def closeEvent(self, event):
        """Закрытие виджета с очисткой ресурсов"""
        try:
            self._cleanup_thread()
        except Exception as e:
            logger.error(f"Ошибка при закрытии: {e}")
        super().closeEvent(event)