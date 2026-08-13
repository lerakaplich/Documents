import os
from PyQt6.QtWidgets import QWidget, QStyleOption, QStyle, QLineEdit
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPainter
from PyQt6.uic import loadUi


class ResetPasswordWidget(QWidget):
    # Сигналы для общения с главным окном
    back_to_login = pyqtSignal()
    reset_password = pyqtSignal(str)  # Сигнал с кодом
    resend_code = pyqtSignal()
    go_to_new_password = pyqtSignal()  # Новый сигнал для перехода к смене пароля

    def __init__(self, parent=None):
        super().__init__(parent)


        ui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui", "login",
                               "reset_password_widget.ui")
        loadUi(ui_path, self)

        # Устанавливаем стили фона
        self.setStyleSheet("""
            ResetPasswordWidget {
                background-color: rgba(217, 217, 214, 0.95);
                border-radius: 30px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)

        # Подключаем кнопки к сигналам
        if hasattr(self, 'backToLoginButton'):
            self.backToLoginButton.clicked.connect(self.back_to_login.emit)

        if hasattr(self, 'resendCodeButton'):
            self.resendCodeButton.clicked.connect(self.resend_code.emit)

        # Подключаем кнопку подтверждения
        if hasattr(self, 'resetPasswordButton'):
            self.resetPasswordButton.clicked.connect(self._on_reset_password_clicked)

        # Настраиваем автоматический переход между полями ввода кода
        self._setup_code_inputs()

    def _setup_code_inputs(self):
        """Настраивает автоматический переход между полями ввода кода"""
        self.code_inputs = []
        for i in range(1, 7):
            input_name = f"codeDigit{i}"
            if hasattr(self, input_name):
                input_field = getattr(self, input_name)
                self.code_inputs.append(input_field)

                # При вводе цифры переходим к следующему полю
                input_field.textChanged.connect(
                    lambda text, idx=i - 1: self._on_code_input_changed(text, idx)
                )

                # При нажатии Backspace переходим к предыдущему полю
                input_field.keyPressEvent = self._create_key_press_handler(input_field, i)

    def _create_key_press_handler(self, field, index):
        """Создает обработчик нажатия клавиш для поля ввода кода"""

        def key_press_handler(event):
            if event.key() == Qt.Key.Key_Backspace and field.text() == "" and index > 1:
                # Переход к предыдущему полю при Backspace
                prev_field = getattr(self, f"codeDigit{index - 1}", None)
                if prev_field:
                    prev_field.setFocus()
                    prev_field.selectAll()
            elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                # Нажатие Enter - подтверждаем код
                self._on_reset_password_clicked()
            else:
                # Вызываем стандартный обработчик
                QLineEdit.keyPressEvent(field, event)

        return key_press_handler

    def _on_code_input_changed(self, text, index):
        """Обработчик изменения текста в поле ввода кода"""
        if len(text) == 1 and index < len(self.code_inputs) - 1:
            # Переход к следующему полю
            next_field = self.code_inputs[index + 1]
            if next_field:
                next_field.setFocus()
                next_field.selectAll()
        elif len(text) > 1:
            # Если вставлено больше одной цифры, распределяем по полям
            for i, char in enumerate(text[:6]):
                if i < len(self.code_inputs):
                    self.code_inputs[i].setText(char)
                    self.code_inputs[i].setFocus()

    def get_code(self):
        """Собирает код из всех полей ввода"""
        code = ""
        for input_field in self.code_inputs:
            code += input_field.text()
        return code

    def _on_reset_password_clicked(self):
        """Обработчик нажатия кнопки подтверждения"""
        code = self.get_code()

        # Проверяем, что код состоит из 6 цифр
        if len(code) != 6 or not code.isdigit():
            self.set_error_state("Введите корректный 6-значный код")
            return

        # Отправляем сигнал с кодом
        self.reset_password.emit(code)

        # Переходим к окну смены пароля
        self.go_to_new_password.emit()

    def set_error_state(self, message="Неверный код! Попробуйте еще раз."):
        """Установка состояния ошибки"""
        if hasattr(self, 'infoLabel'):
            self.infoLabel.setText(message)
            self.infoLabel.setStyleSheet("color: #D22730; font-size: 16px; font-weight: bold; background: transparent;")

        # Очищаем поля ввода
        self.clear_code()

        # Устанавливаем фокус на первое поле
        if self.code_inputs:
            self.code_inputs[0].setFocus()

    def set_success_state(self):
        """Установка успешного состояния"""
        if hasattr(self, 'infoLabel'):
            self.infoLabel.setText("Успешно! Перенаправление...")
            self.infoLabel.setStyleSheet("color: #27D24A; font-size: 16px; font-weight: bold; background: transparent;")

    def reset_styles(self):
        """Сброс текста и стиля к исходному"""
        if hasattr(self, 'infoLabel'):
            self.infoLabel.setText("Код подтверждения отправлен в Telegram")
            self.infoLabel.setStyleSheet(
                "color: #555; font-size: 18px; background: transparent; border: none; padding: 0 10px;")

    def clear_code(self):
        """Очистка введенных полей"""
        for input_field in self.code_inputs:
            input_field.setText("")
        if self.code_inputs:
            self.code_inputs[0].setFocus()

    def paintEvent(self, event):
        """Обязательный метод: заставляет QWidget использовать стили QSS"""
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        super().paintEvent(event)