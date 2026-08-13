import os
from PyQt6.QtWidgets import QWidget, QLineEdit
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import pyqtSignal
from PyQt6.uic import loadUi


class AuthWidget(QWidget):
    # Добавляем сигнал успешного входа
    login_successful = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Загружаем интерфейс карточки авторизации
        ui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui", "login",
                               "auth_widget.ui")
        loadUi(ui_path, self)

        # Сохраняем пути к иконкам
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.eye_closed_path = os.path.join(base_dir, "icons", "eye-closed.svg")
        self.eye_open_path = os.path.join(base_dir, "icons", "eye-open.svg")

        # Подключаем переключение видимости пароля
        if hasattr(self, 'togglePasswordButton') and hasattr(self, 'passwordInput'):
            self.togglePasswordButton.clicked.connect(self._toggle_password_visibility)
            self._update_eye_icon()

        # Подключаем кнопку входа
        if hasattr(self, 'loginButton'):
            self.loginButton.clicked.connect(self._on_login_clicked)

    def _toggle_password_visibility(self):
        if self.passwordInput.echoMode() == QLineEdit.EchoMode.Password:
            self.passwordInput.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.passwordInput.setEchoMode(QLineEdit.EchoMode.Password)
        self._update_eye_icon()

    def _update_eye_icon(self):
        """Обновляет иконку глаза в зависимости от режима отображения пароля"""
        if self.passwordInput.echoMode() == QLineEdit.EchoMode.Password:
            icon_path = self.eye_closed_path
        else:
            icon_path = self.eye_open_path

        if os.path.exists(icon_path):
            self.togglePasswordButton.setIcon(QIcon(icon_path))
        else:
            print(f"Warning: Icon file not found: {icon_path}")

    def _on_login_clicked(self):
        """Обработчик нажатия кнопки входа"""
        # Здесь должна быть ваша логика авторизации
        username = self.usernameInput.text() if hasattr(self, 'usernameInput') else ""
        password = self.passwordInput.text() if hasattr(self, 'passwordInput') else ""

        print(f"Попытка входа: {username}")

        # ДОБАВЬТЕ СВОЮ ЛОГИКУ ПРОВЕРКИ АВТОРИЗАЦИИ ЗДЕСЬ
        # Например:
        if username and password:  # Временно пропускаем любые логин/пароль
            self.login_successful.emit()  # Сигнал об успешном входе
        else:
            print("Введите логин и пароль")