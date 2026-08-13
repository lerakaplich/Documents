import os
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QMessageBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import pyqtSignal
from PyQt6.uic import loadUi


class NewPasswordWidget(QWidget):
    # Добавляем сигнал успешной смены пароля
    password_changed_successfully = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Загружаем интерфейс
        ui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui", "login",
                               "new_password_widget.ui")
        loadUi(ui_path, self)

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.eye_closed_path = os.path.join(base_dir, "icons", "eye-closed.svg")
        self.eye_open_path = os.path.join(base_dir, "icons", "eye-open.svg")

        # Подключаем переключение видимости пароля для нового пароля
        if hasattr(self, 'togglePasswordButton') and hasattr(self, 'newPasswordInput'):
            self.togglePasswordButton.clicked.connect(
                lambda: self._toggle_password_visibility('newPasswordInput', 'togglePasswordButton')
            )
            self._update_eye_icon('newPasswordInput', 'togglePasswordButton')

        # Подключаем переключение видимости пароля для подтверждения
        if hasattr(self, 'toggleConfirmPasswordButton') and hasattr(self, 'confirmPasswordInput'):
            self.toggleConfirmPasswordButton.clicked.connect(
                lambda: self._toggle_password_visibility('confirmPasswordInput', 'toggleConfirmPasswordButton')
            )
            self._update_eye_icon('confirmPasswordInput', 'toggleConfirmPasswordButton')

        # Подключаем кнопку создания пароля
        if hasattr(self, 'createPasswordButton'):
            self.createPasswordButton.clicked.connect(self._on_create_password)

        # Подключаем кнопку возврата к входу
        if hasattr(self, 'backToLoginButton'):
            self.backToLoginButton.clicked.connect(self._on_back_to_login)

    def _toggle_password_visibility(self, input_name, button_name):
        """Переключает видимость пароля для указанного поля"""
        password_input = getattr(self, input_name, None)
        toggle_button = getattr(self, button_name, None)

        if password_input and toggle_button:
            if password_input.echoMode() == QLineEdit.EchoMode.Password:
                password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            else:
                password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._update_eye_icon(input_name, button_name)

    def _update_eye_icon(self, input_name, button_name):
        """Обновляет иконку глаза в зависимости от режима отображения пароля"""
        password_input = getattr(self, input_name, None)
        toggle_button = getattr(self, button_name, None)

        if password_input and toggle_button:
            if password_input.echoMode() == QLineEdit.EchoMode.Password:
                icon_path = self.eye_closed_path
            else:
                icon_path = self.eye_open_path

            if os.path.exists(icon_path):
                toggle_button.setIcon(QIcon(icon_path))
            else:
                print(f"Warning: Icon file not found: {icon_path}")

    def _on_create_password(self):
        """Обработчик нажатия кнопки создания пароля"""
        new_password = self.newPasswordInput.text() if hasattr(self, 'newPasswordInput') else ""
        confirm_password = self.confirmPasswordInput.text() if hasattr(self, 'confirmPasswordInput') else ""

        # Проверяем, что пароли совпадают
        if new_password != confirm_password:
            print("Пароли не совпадают!")
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают!")
            return

        # Проверяем длину пароля
        if len(new_password) < 8:
            print("Пароль должен содержать не менее 8 символов!")
            QMessageBox.warning(self, "Ошибка", "Пароль должен содержать не менее 8 символов!")
            return

        # Здесь добавляем логику сохранения пароля
        print(f"Пароль установлен: {new_password}")

        # После успешной смены пароля отправляем сигнал
        self.password_changed_successfully.emit()

    def _on_back_to_login(self):
        """Обработчик нажатия кнопки возврата к входу"""
        print("Возврат к окну входа")
        # Здесь можно добавить логику переключения на окно авторизации