import logging
import os
import re
import sys

from PyQt6.QtCore import QEvent, QObject, QPoint, QSize, Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QLineEdit, QStyle, QStyleOption, QWidget
from PyQt6.uic import loadUi

from client.core.state.app_state import AppState

logger = logging.getLogger(__name__)

TELEGRAM_BOT_URL = "https://t.me/Documents2035_bot"
RESEND_TEXT = "Повторить отправку"


def normalize_phone_for_server(phone: str) -> str:
    """Нормализует номер телефона в формат, который ожидает сервер"""
    digits = "".join(re.findall(r"\d", phone))

    if digits.startswith("80") and len(digits) == 11:
        digits = "375" + digits[2:]
    elif len(digits) == 9 and digits.startswith(("29", "44", "33", "25")):
        digits = "375" + digits
    elif digits.startswith("375") and len(digits) == 12:
        pass
    else:
        if len(digits) == 9:
            digits = "375" + digits
        elif len(digits) == 12 and not digits.startswith("375"):
            if digits.startswith(("29", "44", "33", "25")):
                digits = "375" + digits[2:] if len(digits) == 11 else "375" + digits
            else:
                digits = "375" + digits

    if not digits.startswith("375") or len(digits) != 12:
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
            logger.exception(f"Ошибка отправки кода: {e}")
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
            logger.exception(f"Ошибка проверки кода: {e}")
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

        if hasattr(self, "backToLoginButton"):
            self.backToLoginButton.clicked.connect(self.back_to_login.emit)

        if hasattr(self, "resendCodeButton"):
            self.resendCodeButton.clicked.connect(self._on_resend_code_clicked)

        if hasattr(self, "resetPasswordButton"):
            self.resetPasswordButton.clicked.connect(self._on_reset_password_clicked)

        self._setup_qr_button()
        self._setup_code_inputs()
        self._set_code_inputs_enabled(False)

    def _setup_qr_button(self):
        """QR-код со ссылкой на Telegram-бота (icons/qr.png). Клик открывает бота в браузере/Telegram."""
        if not hasattr(self, "qrButton"):
            return

        qr_path = os.path.join(self.root_dir, "icons", "qr.png")
        pixmap = QPixmap(qr_path)

        if pixmap.isNull():
            logger.warning(f"QR-код не найден или не читается: {qr_path}")
            self.qrButton.setText("Открыть бота\nв Telegram")
            self.qrButton.setStyleSheet(
                "QPushButton { background-color: white; border: 2px solid #D22730; border-radius: 20px;"
                " color: #D22730; font-size: 18px; font-weight: bold; }"
                "QPushButton:hover { background-color: #F7E3E4; }"
            )
        else:
            self.qrButton.setIcon(QIcon(pixmap))
            self.qrButton.setIconSize(QSize(190, 190))

        self.qrButton.clicked.connect(self._open_telegram_bot)

    def _open_telegram_bot(self):
        if not QDesktopServices.openUrl(QUrl(TELEGRAM_BOT_URL)):
            logger.error(f"Не удалось открыть ссылку: {TELEGRAM_BOT_URL}")
            if self.notification_manager:
                self.notification_manager.show_notification("Не удалось открыть ссылку на бота", duration=3000)

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

        if hasattr(self, "resetPasswordButton"):
            self.resetPasswordButton.setEnabled(enabled)

        if hasattr(self, "resendCodeButton"):
            self.resendCodeButton.setEnabled(not enabled)

    def _send_reset_code(self):
        if not self.phone_number:
            if self.notification_manager:
                self.notification_manager.show_notification("Номер телефона не указан", duration=3000)
            return


        if hasattr(self, "resendCodeButton"):
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
            logger.exception(f"Ошибка при запуске потока: {e}")
            self._on_code_sent_error(str(e))

    def _on_code_sent_success(self):
        self.is_code_sent = True

        if self.notification_manager:
            self.notification_manager.show_notification("Код подтверждения отправлен в Telegram", duration=3000)

        self._set_code_inputs_enabled(True)

        if self.code_inputs:
            self.code_inputs[0].setFocus()

        if hasattr(self, "resendCodeButton"):
            self.resendCodeButton.setEnabled(False)
            self.resendCodeButton.setText(self._resend_countdown_text(30))
            self.resend_timer = 30
            self._start_resend_timer()

    def _on_code_sent_error(self, error_msg):
        self.is_code_sent = False


        self._set_code_inputs_enabled(False)

        if hasattr(self, "resendCodeButton"):
            self.resendCodeButton.setEnabled(True)
            self.resendCodeButton.setText(RESEND_TEXT)

        if self.notification_manager:
            if "404" in error_msg:
                self.notification_manager.show_notification("Пользователь с таким номером не найден", duration=3000)
            elif "Connection" in error_msg:
                self.notification_manager.show_notification("Не удалось подключиться к серверу", duration=3000)
            else:
                self.notification_manager.show_notification(f"Ошибка: {error_msg[:50]}...", duration=3000)

    @staticmethod
    def _resend_countdown_text(seconds: int) -> str:
        return f"Повторить отправку через {seconds} с"

    def _start_resend_timer(self):
        from PyQt6.QtCore import QTimer

        self.resend_timer_obj = QTimer()
        self.resend_timer_obj.timeout.connect(self._update_resend_button)
        self.resend_timer_obj.start(1000)

    def _update_resend_button(self):
        self.resend_timer -= 1

        if hasattr(self, "resendCodeButton"):
            if self.resend_timer > 0:
                self.resendCodeButton.setText(self._resend_countdown_text(self.resend_timer))
            else:
                self.resendCodeButton.setEnabled(True)
                self.resendCodeButton.setText(RESEND_TEXT)
                if hasattr(self, "resend_timer_obj") and self.resend_timer_obj:
                    self.resend_timer_obj.stop()
                    self.resend_timer_obj = None

    def _on_resend_code_clicked(self):
        if hasattr(self, "resendCodeButton"):
            self.resendCodeButton.setEnabled(False)
            self.resendCodeButton.setText("Отправка...")
        self._send_reset_code()

    def _setup_code_inputs(self):
        self.code_inputs = []
        self._sel_range = None  # (первая, последняя) выделенные ячейки
        self._drag_anchor = None  # ячейка, с которой начато выделение мышью
        for i in range(1, 7):
            input_name = f"codeDigit{i}"
            if hasattr(self, input_name):
                input_field = getattr(self, input_name)
                self.code_inputs.append(input_field)
                input_field.textChanged.connect(lambda text, idx=i - 1: self._on_code_input_changed(text, idx))
                input_field.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj in getattr(self, "code_inputs", []):
            event_type = event.type()
            if event_type == QEvent.Type.KeyPress:
                if self._handle_code_key_press(obj, event):
                    return True
            elif event_type in (QEvent.Type.MouseButtonPress, QEvent.Type.FocusIn):
                if self._sel_range:
                    self._reset_selection()
                if event_type == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                    self._drag_anchor = self.code_inputs.index(obj)
            elif event_type == QEvent.Type.MouseMove:
                if self._drag_anchor is not None and event.buttons() & Qt.MouseButton.LeftButton:
                    current = self._cell_index_at(event.globalPosition().x())
                    if current != self._drag_anchor or self._sel_range:
                        # Выделение мышью сразу по нескольким ячейкам
                        self._select_range(self._drag_anchor, current)
                        return True
            elif event_type == QEvent.Type.MouseButtonRelease:
                self._drag_anchor = None
        return super().eventFilter(obj, event)

    def _cell_index_at(self, global_x: float) -> int:
        """Индекс ячейки под курсором по горизонтали (работает и в промежутках, и за краями ряда)."""
        index = 0
        for i, cell in enumerate(self.code_inputs):
            if cell.mapToGlobal(QPoint(0, 0)).x() <= global_x:
                index = i
        return index

    @staticmethod
    def _is_ctrl_shortcut(event, latin_key, ctrl_char, win_vk) -> bool:
        """Ctrl+буква независимо от раскладки: в русской раскладке key() может не совпасть с латинской буквой."""
        if event.key() == latin_key or event.text() == ctrl_char:
            return True
        return sys.platform == "win32" and event.nativeVirtualKey() == win_vk

    def _clear_selected_cells(self) -> int:
        """Очищает выделенные ячейки и возвращает индекс первой из них."""
        lo, hi = self._sel_range
        self._reset_selection()
        for cell in self.code_inputs[lo : hi + 1]:
            cell.clear()
        return lo

    def _handle_code_key_press(self, field, event) -> bool:
        """True — событие обработано, стандартную обработку QLineEdit пропускаем."""
        index = self.code_inputs.index(field)
        key = event.key()

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self._is_ctrl_shortcut(event, Qt.Key.Key_V, "\x16", 0x56):
                self._paste_code()
                return True
            if self._is_ctrl_shortcut(event, Qt.Key.Key_A, "\x01", 0x41):
                self._select_all_code()
                return True
            if self._is_ctrl_shortcut(event, Qt.Key.Key_C, "\x03", 0x43):
                self._copy_code()
                return True
            if self._is_ctrl_shortcut(event, Qt.Key.Key_X, "\x18", 0x58):
                self._cut_code()
                return True
            return False

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_reset_password_clicked()
            return True

        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            if self._sel_range:
                self._focus_cell(self._clear_selected_cells())
            elif field.text():
                field.clear()
            elif key == Qt.Key.Key_Backspace and index > 0:
                prev_field = self.code_inputs[index - 1]
                prev_field.clear()
                prev_field.setFocus()
            return True

        text = event.text()
        if text and text.isprintable():
            # В ячейки принимаются только цифры, остальные печатные символы игнорируем
            if text.isascii() and text.isdigit():
                if self._sel_range:
                    index = self._clear_selected_cells()
                    field = self.code_inputs[index]
                field.setText(text)
                self._focus_cell(index + 1)
            return True

        return False

    def _focus_cell(self, index: int):
        if 0 <= index < len(self.code_inputs):
            cell = self.code_inputs[index]
            cell.setFocus()
            cell.selectAll()

    def _paste_code(self):
        text = QApplication.clipboard().text()
        match = re.search(r"(?<!\d)\d{6}(?!\d)", text)
        if match:
            digits = match.group(0)
        else:
            digits = "".join(ch for ch in text if ch.isascii() and ch.isdigit())[:6]
        if not digits:
            return

        self._reset_selection()
        for i, cell in enumerate(self.code_inputs):
            cell.blockSignals(True)
            cell.setText(digits[i] if i < len(digits) else "")
            cell.blockSignals(False)

        self._focus_cell(min(len(digits), len(self.code_inputs) - 1))
        if len(digits) >= len(self.code_inputs):
            self._on_reset_password_clicked()

    def _select_range(self, first: int, last: int):
        lo, hi = sorted((first, last))
        self._sel_range = (lo, hi)
        for i, cell in enumerate(self.code_inputs):
            if lo <= i <= hi:
                cell.selectAll()
            else:
                cell.deselect()

    def _select_all_code(self):
        if self.code_inputs and self.get_code():
            self._select_range(0, len(self.code_inputs) - 1)

    def _reset_selection(self):
        self._sel_range = None
        for cell in self.code_inputs:
            cell.deselect()

    def _cut_code(self):
        """Копирует выделенное (или весь код) и очищает эти ячейки."""
        if not self.get_code():
            return
        self._copy_code()
        if self._sel_range:
            self._focus_cell(self._clear_selected_cells())
        else:
            self.clear_code()

    def _copy_code(self):
        if self._sel_range:
            lo, hi = self._sel_range
            code = "".join(cell.text() for cell in self.code_inputs[lo : hi + 1])
        else:
            code = self.get_code()
        if code:
            QApplication.clipboard().setText(code)

    def _on_code_input_changed(self, text, index):
        if len(text) == 1:
            self._focus_cell(index + 1)
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

        if hasattr(self, "resetPasswordButton"):
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
            logger.exception(f"Ошибка при запуске потока верификации: {e}")
            self._on_code_verify_error(str(e))

    def _on_code_verified(self):

        if self.notification_manager:
            self.notification_manager.show_notification("Код подтвержден! Придумайте новый пароль.", duration=2000)

        # Получаем код
        code = self.get_code()

        # Проверяем, что данные не пустые
        if not self.phone_number:
            logger.error("❌ Номер телефона пустой!")
            if self.notification_manager:
                self.notification_manager.show_notification("Ошибка: номер телефона не указан", duration=3000)
            return

        if not code:
            logger.error("❌ Код пустой!")
            if self.notification_manager:
                self.notification_manager.show_notification("Ошибка: код не указан", duration=3000)
            return

        logger.info(f"📤 Передаем данные через сигнал: phone={self.phone_number}, code={code}")

        # Отправляем сигнал с данными
        self.go_to_new_password.emit(self.phone_number, code)

    def _on_code_verify_error(self, error_msg):
        if hasattr(self, "resetPasswordButton"):
            self.resetPasswordButton.setEnabled(True)

        if "400" in error_msg or "Неверный код" in error_msg:
            self.set_error_state("Неверный код! Попробуйте еще раз.")
        else:
            if self.notification_manager:
                self.notification_manager.show_notification(f"Ошибка: {error_msg[:50]}...", duration=3000)

    def set_error_state(self, message="Неверный код! Попробуйте еще раз."):
        if self.notification_manager:
            self.notification_manager.show_notification(message, duration=3000)
        self.clear_code()
        if self.code_inputs:
            self.code_inputs[0].setFocus()

    def clear_code(self):
        self._sel_range = None
        for input_field in self.code_inputs:
            input_field.setText("")
        if self.code_inputs:
            self.code_inputs[0].setFocus()

    def _cleanup_thread(self):
        try:
            if hasattr(self, "thread") and self.thread:
                self.thread.deleteLater()
                self.thread = None
            if hasattr(self, "worker") and self.worker:
                self.worker.deleteLater()
                self.worker = None
        except Exception as e:
            logger.exception(f"Ошибка при очистке потока: {e}")

    def _cleanup_verify_thread(self):
        try:
            if hasattr(self, "verify_thread") and self.verify_thread:
                self.verify_thread.deleteLater()
                self.verify_thread = None
            if hasattr(self, "verify_worker") and self.verify_worker:
                self.verify_worker.deleteLater()
                self.verify_worker = None
        except Exception as e:
            logger.exception(f"Ошибка при очистке потока верификации: {e}")

    def closeEvent(self, event):
        try:
            if hasattr(self, "resend_timer_obj") and self.resend_timer_obj:
                self.resend_timer_obj.stop()
                self.resend_timer_obj = None
            self._cleanup_thread()
            self._cleanup_verify_thread()
        except Exception as e:
            logger.exception(f"Ошибка при закрытии: {e}")
        super().closeEvent(event)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        super().paintEvent(event)