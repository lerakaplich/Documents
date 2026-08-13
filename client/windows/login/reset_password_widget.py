import os
from PyQt6.QtWidgets import QWidget, QStyleOption, QStyle, QLineEdit, QApplication
from PyQt6.QtCore import pyqtSignal, Qt, QThread, QObject
from PyQt6.QtGui import QPainter, QKeyEvent
from PyQt6.uic import loadUi
import logging
import re

from client.core.state.app_state import AppState

logger = logging.getLogger(__name__)


def normalize_phone_for_server(phone: str) -> str:
    """Нормализует номер телефона в формат, который ожидает сервер"""
    digits = ''.join(re.findall(r'\d', phone))

    if digits.startswith('80') and len(digits) == 11:
        digits = '375' + digits[2:]
    elif len(digits) == 9 and digits.startswith(('29', '44', '33', '25')):
        digits = '375' + digits
    elif digits.startswith('375') and len(digits) == 12:
        pass
    else:
        if len(digits) == 9:
            digits = '375' + digits
        elif len(digits) == 12 and not digits.startswith('375'):
            if digits.startswith(('29', '44', '33', '25')):
                digits = '375' + digits[2:] if len(digits) == 11 else '375' + digits
            else:
                digits = '375' + digits

    if not digits.startswith('375') or len(digits) != 12:
        logger.warning(f"Некорректный формат номера: {phone} -> {digits}")
        return phone

    return f"+{digits}"


class ResetCodeWorker(QObject):
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)

    def __init__(self, phone_number: str):
        super().__init__()
        self.phone_number = phone_number

    def run(self):
        try:
            app_state = AppState()
            normalized_phone = normalize_phone_for_server(self.phone_number)
            logger.info(f"📤 Отправка кода на номер: {normalized_phone}")
            app_state.auth_service.forgot_password(normalized_phone)
            self.finished.emit(True)
        except Exception as e:
            logger.error(f"Ошибка отправки кода: {e}")
            self.error.emit(str(e))


class VerifyCodeWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, phone_number: str, code: str):
        super().__init__()
        self.phone_number = phone_number
        self.code = code

    def run(self):
        try:
            app_state = AppState()
            normalized_phone = normalize_phone_for_server(self.phone_number)
            logger.info(f"📤 Проверка кода для номера: {normalized_phone}, код: {self.code}")
            app_state.auth_service.verify_reset_code(normalized_phone, self.code)
            self.finished.emit()
        except Exception as e:
            logger.error(f"Ошибка проверки кода: {e}")
            self.error.emit(str(e))


class ResetPasswordWidget(QWidget):
    back_to_login = pyqtSignal()
    reset_password = pyqtSignal(str)
    resend_code = pyqtSignal()
    # Изменяем сигнал: теперь он передает номер телефона и код
    go_to_new_password = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ui_path = os.path.join(self.root_dir, "ui", "login", "reset_password_widget.ui")
        print(f"Загрузка ResetPasswordWidget UI: {ui_path}")

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI файл не найден: {ui_path}")

        loadUi(ui_path, self)

        self.notification_manager = None
        self.phone_number = ""
        self.is_code_sent = False
        self.thread = None
        self.worker = None
        self.verify_thread = None
        self.verify_worker = None
        self.resend_timer_obj = None
        self.resend_timer = 0

        self.setStyleSheet("""
            ResetPasswordWidget {
                background-color: rgba(217, 217, 214, 0.95);
                border-radius: 30px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)

        if hasattr(self, 'backToLoginButton'):
            self.backToLoginButton.clicked.connect(self.back_to_login.emit)

        if hasattr(self, 'resendCodeButton'):
            self.resendCodeButton.clicked.connect(self._on_resend_code_clicked)

        if hasattr(self, 'resetPasswordButton'):
            self.resetPasswordButton.clicked.connect(self._on_reset_password_clicked)

        self._setup_code_inputs()
        self._set_code_inputs_enabled(False)

    def set_notification_manager(self, manager):
        self.notification_manager = manager

    def set_phone_number(self, phone: str):
        self.phone_number = phone
        normalized = normalize_phone_for_server(phone)
        print(f"📱 Номер телефона для восстановления: {normalized}")
        self._send_reset_code()

    def _set_code_inputs_enabled(self, enabled: bool):
        for input_field in self.code_inputs:
            input_field.setEnabled(enabled)

        if hasattr(self, 'resetPasswordButton'):
            self.resetPasswordButton.setEnabled(enabled)

        if hasattr(self, 'resendCodeButton'):
            self.resendCodeButton.setEnabled(not enabled)

    def _send_reset_code(self):
        if not self.phone_number:
            if self.notification_manager:
                self.notification_manager.show_notification("Номер телефона не указан", duration=3000)
            return

        if hasattr(self, 'infoLabel'):
            self.infoLabel.setText("Отправка кода...")
            self.infoLabel.setStyleSheet("color: #555; font-size: 18px; background: transparent;")

        if hasattr(self, 'resendCodeButton'):
            self.resendCodeButton.setEnabled(False)

        try:
            self.thread = QThread()
            self.worker = ResetCodeWorker(self.phone_number)
            self.worker.moveToThread(self.thread)

            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self._on_code_sent_success)
            self.worker.error.connect(self._on_code_sent_error)
            self.worker.finished.connect(self.thread.quit)
            self.worker.error.connect(self.thread.quit)
            self.thread.finished.connect(self._cleanup_thread)

            self.thread.start()
        except Exception as e:
            logger.error(f"Ошибка при запуске потока: {e}")
            self._on_code_sent_error(str(e))

    def _on_code_sent_success(self):
        self.is_code_sent = True

        if hasattr(self, 'infoLabel'):
            self.infoLabel.setText("Код отправлен в Telegram")
        if self.notification_manager:
            self.notification_manager.show_notification("Код подтверждения отправлен в Telegram", duration=3000)

        self._set_code_inputs_enabled(True)

        if self.code_inputs:
            self.code_inputs[0].setFocus()

        if hasattr(self, 'resendCodeButton'):
            self.resendCodeButton.setEnabled(False)
            self.resendCodeButton.setText("30с")
            self.resend_timer = 30
            self._start_resend_timer()

    def _on_code_sent_error(self, error_msg):
        self.is_code_sent = False

        if hasattr(self, 'infoLabel'):
            self.infoLabel.setText("Ошибка отправки")
            self.infoLabel.setStyleSheet("color: #D22730; font-size: 18px; background: transparent;")

        self._set_code_inputs_enabled(False)

        if hasattr(self, 'resendCodeButton'):
            self.resendCodeButton.setEnabled(True)
            self.resendCodeButton.setText("Повторить")

        if self.notification_manager:
            if "404" in error_msg:
                self.notification_manager.show_notification("Пользователь с таким номером не найден", duration=3000)
            elif "Connection" in error_msg:
                self.notification_manager.show_notification("Не удалось подключиться к серверу", duration=3000)
            else:
                self.notification_manager.show_notification(f"Ошибка: {error_msg[:50]}...", duration=3000)

    def _start_resend_timer(self):
        from PyQt6.QtCore import QTimer

        self.resend_timer_obj = QTimer()
        self.resend_timer_obj.timeout.connect(self._update_resend_button)
        self.resend_timer_obj.start(1000)

    def _update_resend_button(self):
        self.resend_timer -= 1

        if hasattr(self, 'resendCodeButton'):
            if self.resend_timer > 0:
                self.resendCodeButton.setText(f"{self.resend_timer}с")
            else:
                self.resendCodeButton.setEnabled(True)
                self.resendCodeButton.setText("Повторить")
                if hasattr(self, 'resend_timer_obj') and self.resend_timer_obj:
                    self.resend_timer_obj.stop()
                    self.resend_timer_obj = None

    def _on_resend_code_clicked(self):
        if hasattr(self, 'resendCodeButton'):
            self.resendCodeButton.setEnabled(False)
            self.resendCodeButton.setText("Отправка...")
        self._send_reset_code()

    def _setup_code_inputs(self):
        self.code_inputs = []
        for i in range(1, 7):
            input_name = f"codeDigit{i}"
            if hasattr(self, input_name):
                input_field = getattr(self, input_name)
                self.code_inputs.append(input_field)

                input_field.textChanged.connect(
                    lambda text, idx=i - 1: self._on_code_input_changed(text, idx)
                )

                original_key_press = input_field.keyPressEvent

                def create_key_handler(field, index, original_handler):
                    def key_press_handler(event):
                        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_V:
                            try:
                                clipboard = QApplication.clipboard()
                                text = clipboard.text()
                                digits = ''.join(filter(str.isdigit, text))
                                if digits:
                                    for i, char in enumerate(digits[:6]):
                                        if i < len(self.code_inputs):
                                            self.code_inputs[i].setText(char)
                                    filled_count = min(len(digits), 6)
                                    if filled_count < 6:
                                        self.code_inputs[filled_count].setFocus()
                                    else:
                                        self.code_inputs[5].setFocus()
                                    if len(digits) >= 6:
                                        self._on_reset_password_clicked()
                            except Exception as e:
                                logger.error(f"Ошибка при вставке из буфера: {e}")
                            return

                        if event.key() == Qt.Key.Key_Backspace and field.text() == "" and index > 1:
                            prev_field = getattr(self, f"codeDigit{index - 1}", None)
                            if prev_field:
                                prev_field.setFocus()
                                prev_field.selectAll()
                            return

                        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                            self._on_reset_password_clicked()
                            return

                        if original_handler:
                            original_handler(event)
                        else:
                            QLineEdit.keyPressEvent(field, event)

                    return key_press_handler

                input_field.keyPressEvent = create_key_handler(
                    input_field, i - 1, original_key_press
                )

    def _on_code_input_changed(self, text, index):
        if len(text) == 1 and index < len(self.code_inputs) - 1:
            next_field = self.code_inputs[index + 1]
            if next_field:
                next_field.setFocus()
                next_field.selectAll()
        elif len(text) > 1:
            for i, char in enumerate(text[:6]):
                if i < len(self.code_inputs):
                    self.code_inputs[i].setText(char)
                    self.code_inputs[i].setFocus()

    def get_code(self):
        code = ""
        for input_field in self.code_inputs:
            code += input_field.text()
        return code

    def _on_reset_password_clicked(self):
        if not self.is_code_sent:
            if self.notification_manager:
                self.notification_manager.show_notification("Сначала запросите код подтверждения", duration=3000)
            return

        code = self.get_code()

        if len(code) != 6 or not code.isdigit():
            self.set_error_state("Введите корректный 6-значный код")
            return

        self._verify_code(code)

    def _verify_code(self, code: str):
        if hasattr(self, 'infoLabel'):
            self.infoLabel.setText("Проверка кода...")
            self.infoLabel.setStyleSheet("color: #555; font-size: 18px; background: transparent;")

        if hasattr(self, 'resetPasswordButton'):
            self.resetPasswordButton.setEnabled(False)

        try:
            self.verify_thread = QThread()
            self.verify_worker = VerifyCodeWorker(self.phone_number, code)
            self.verify_worker.moveToThread(self.verify_thread)

            self.verify_thread.started.connect(self.verify_worker.run)
            self.verify_worker.finished.connect(self._on_code_verified)
            self.verify_worker.error.connect(self._on_code_verify_error)
            self.verify_worker.finished.connect(self.verify_thread.quit)
            self.verify_worker.error.connect(self.verify_thread.quit)
            self.verify_thread.finished.connect(self._cleanup_verify_thread)

            self.verify_thread.start()
        except Exception as e:
            logger.error(f"Ошибка при запуске потока верификации: {e}")
            self._on_code_verify_error(str(e))

    def _on_code_verified(self):
        if hasattr(self, 'infoLabel'):
            self.infoLabel.setText("Код подтвержден!")

        if self.notification_manager:
            self.notification_manager.show_notification(
                "Код подтвержден! Придумайте новый пароль.",
                duration=2000
            )

        # Получаем код
        code = self.get_code()

        # Проверяем, что данные не пустые
        if not self.phone_number:
            logger.error("❌ Номер телефона пустой!")
            if self.notification_manager:
                self.notification_manager.show_notification(
                    "Ошибка: номер телефона не указан",
                    duration=3000
                )
            return

        if not code:
            logger.error("❌ Код пустой!")
            if self.notification_manager:
                self.notification_manager.show_notification(
                    "Ошибка: код не указан",
                    duration=3000
                )
            return

        logger.info(f"📤 Передаем данные через сигнал: phone={self.phone_number}, code={code}")

        # Отправляем сигнал с данными
        self.go_to_new_password.emit(self.phone_number, code)

    def _on_code_verify_error(self, error_msg):
        if hasattr(self, 'resetPasswordButton'):
            self.resetPasswordButton.setEnabled(True)

        if "400" in error_msg or "Неверный код" in error_msg:
            self.set_error_state("Неверный код! Попробуйте еще раз.")
            if self.notification_manager:
                self.notification_manager.show_notification("Неверный код подтверждения", duration=3000)
        else:
            if self.notification_manager:
                self.notification_manager.show_notification(f"Ошибка: {error_msg[:50]}...", duration=3000)
            if hasattr(self, 'infoLabel'):
                self.infoLabel.setText("Ошибка проверки")
                self.infoLabel.setStyleSheet("color: #D22730; font-size: 18px; background: transparent;")

    def set_error_state(self, message="Неверный код! Попробуйте еще раз."):
        if hasattr(self, 'infoLabel'):
            self.infoLabel.setText(message)
            self.infoLabel.setStyleSheet("color: #D22730; font-size: 16px;  background: transparent;")
        self.clear_code()
        if self.code_inputs:
            self.code_inputs[0].setFocus()

    def clear_code(self):
        for input_field in self.code_inputs:
            input_field.setText("")
        if self.code_inputs:
            self.code_inputs[0].setFocus()

    def _cleanup_thread(self):
        try:
            if hasattr(self, 'thread') and self.thread:
                self.thread.deleteLater()
                self.thread = None
            if hasattr(self, 'worker') and self.worker:
                self.worker.deleteLater()
                self.worker = None
        except Exception as e:
            logger.error(f"Ошибка при очистке потока: {e}")

    def _cleanup_verify_thread(self):
        try:
            if hasattr(self, 'verify_thread') and self.verify_thread:
                self.verify_thread.deleteLater()
                self.verify_thread = None
            if hasattr(self, 'verify_worker') and self.verify_worker:
                self.verify_worker.deleteLater()
                self.verify_worker = None
        except Exception as e:
            logger.error(f"Ошибка при очистке потока верификации: {e}")

    def closeEvent(self, event):
        try:
            if hasattr(self, 'resend_timer_obj') and self.resend_timer_obj:
                self.resend_timer_obj.stop()
                self.resend_timer_obj = None
            self._cleanup_thread()
            self._cleanup_verify_thread()
        except Exception as e:
            logger.error(f"Ошибка при закрытии: {e}")
        super().closeEvent(event)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        super().paintEvent(event)