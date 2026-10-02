import logging
import os
import re
import sys

from PyQt6 import QtCore, QtGui, QtWidgets, uic
from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtSvg import QSvgRenderer

from client.core.themes import get_manager
from client.windows.animations.animated_notification import NotificationManager

logger = logging.getLogger(__name__)

# .../client
CLIENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
UI_PATH = os.path.join(CLIENT_DIR, "ui", "settings", "user_data", "new_password_window.ui")
EYE_OPEN_PATH = os.path.join(CLIENT_DIR, "icons", "eye-open.svg")
EYE_CLOSED_PATH = os.path.join(CLIENT_DIR, "icons", "eye-closed.svg")

EYE_ICON_SIZE = 20


def _make_eye_icon(path: str, color: str, size: int = EYE_ICON_SIZE) -> QtGui.QIcon:
    """Рисует SVG-иконку, подставляя цвет темы вместо currentColor
    (иначе в тёмной теме глазок был бы чёрным на тёмном)."""
    try:
        with open(path, encoding="utf-8") as f:
            svg = f.read().replace("currentColor", color)

        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        if not renderer.isValid():
            raise ValueError("SVG не удалось разобрать")

        scale = 2  # чёткость на HiDPI
        pixmap = QtGui.QPixmap(size * scale, size * scale)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QtGui.QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        pixmap.setDevicePixelRatio(scale)
        return QtGui.QIcon(pixmap)
    except Exception as e:
        logger.warning(f"Не удалось отрисовать иконку {path}: {e}")
        return QtGui.QIcon(path)


class NewPasswordWindow(QtWidgets.QDialog):
    """Окно смены пароля в стиле PhoneEditWindow / EmailEditWindow.

    change_callback(old_password, new_password) — функция, которая реально
    меняет пароль (запрос на сервер). Если она бросает исключение, окно
    остаётся открытым и показывает ошибку; если отработала без ошибок —
    окно закрывается через accept().
    """

    def __init__(self, change_callback=None, parent=None):
        super().__init__(parent)

        uic.loadUi(UI_PATH, self)

        self._change_callback = change_callback

        # (поле, кнопка-глазок)
        self._fields = [
            (self.oldPasswordInput, self.toggleOldPasswordButton),
            (self.newPasswordInput, self.toggleNewPasswordButton),
            (self.confirmPasswordInput, self.toggleConfirmPasswordButton),
        ]

        for line_edit, button in self._fields:
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # фокус остаётся в поле
            button.clicked.connect(lambda _=False, le=line_edit: self._toggle_visibility(le))

        self._apply_styles()
        self._update_eye_icons()

        # Всплывающие уведомления: внизу главного окна по центру
        self.notification_manager = NotificationManager.for_dialog(self)

        self.saveButton.setDefault(True)  # Enter = «Сохранить»
        self.saveButton.clicked.connect(self.save_password)
        self.setModal(True)

        self.oldPasswordInput.setFocus()

    # ─────────── Глазки ───────────

    def _toggle_visibility(self, line_edit: QtWidgets.QLineEdit):
        if line_edit.echoMode() == QtWidgets.QLineEdit.EchoMode.Password:
            line_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Normal)
        else:
            line_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self._update_eye_icons()

    def _update_eye_icons(self):
        t = get_manager().current
        color = getattr(t, "TEXT_TERTIARY", "#888888")

        # Пароль скрыт → eye-closed, показан → eye-open (как на экране входа)
        closed_icon = _make_eye_icon(EYE_CLOSED_PATH, color)
        open_icon = _make_eye_icon(EYE_OPEN_PATH, color)

        for line_edit, button in self._fields:
            hidden = line_edit.echoMode() == QtWidgets.QLineEdit.EchoMode.Password
            button.setIcon(closed_icon if hidden else open_icon)

    # ─────────── Стили (как в PhoneEditWindow) ───────────

    def _apply_styles(self):
        t = get_manager().current

        self.setStyleSheet(f"QDialog {{ background-color: {t.BG_DIALOG}; }}")

        self.titleLabel.setStyleSheet(
            f"color: {t.TEXT_PRIMARY}; font-size: 20px; font-weight: bold; background: transparent; padding: 0 0 4px 0;"
        )

        # padding-right 40px — чтобы текст не заезжал под глазок
        input_style = f"""
            QLineEdit {{
                border: 1px solid {t.BORDER_DEFAULT};
                border-radius: 6px;
                padding: 6px 40px 6px 10px;
                background-color: {t.BG_INPUT};
                color: {t.TEXT_PRIMARY};
                font-size: 14px;
                min-height: 26px;
            }}
            QLineEdit:hover {{
                border-color: {t.ACCENT_PRIMARY};
            }}
            QLineEdit:focus {{
                border: 2px solid {t.ACCENT_PRIMARY};
            }}
            QLineEdit::placeholder {{
                color: {t.TEXT_TERTIARY};
            }}
        """
        for line_edit, _ in self._fields:
            line_edit.setStyleSheet(input_style)

        for container in (
            self.oldPasswordContainer,
            self.newPasswordContainer,
            self.confirmPasswordContainer,
        ):
            container.setStyleSheet("background: transparent; border: none;")

        self.saveButton.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.ACCENT_PRIMARY};
                color: {t.TEXT_ON_ACCENT};
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                padding: 0 20px;
                min-height: 42px;
            }}
            QPushButton:hover {{
                background-color: {t.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {t.ACCENT_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {t.BORDER_DEFAULT};
            }}
        """)

    def reapply_theme(self):
        self._apply_styles()
        self._update_eye_icons()

    # ─────────── Логика ───────────

    @staticmethod
    def validate_passwords(old: str, new: str, confirm: str):
        """Возвращает (сообщение, имя_поля) или None, если всё в порядке.
        Правила совпадают с серверными (PasswordChangeRequest)."""
        if not old:
            return "Введите старый пароль", "oldPasswordInput"
        if not new:
            return "Введите новый пароль", "newPasswordInput"
        if len(new) < 8:
            return "Новый пароль должен содержать не менее 8 символов", "newPasswordInput"
        if len(new) > 64:
            return "Новый пароль не должен быть длиннее 64 символов", "newPasswordInput"
        if not re.search(r"[A-ZА-ЯЁ]", new):
            return "Пароль должен содержать хотя бы одну заглавную букву", "newPasswordInput"
        if not re.search(r"[a-zа-яё]", new):
            return "Пароль должен содержать хотя бы одну строчную букву", "newPasswordInput"
        if not re.search(r"\d", new):
            return "Пароль должен содержать хотя бы одну цифру", "newPasswordInput"
        if new == old:
            return "Новый пароль не должен совпадать со старым", "newPasswordInput"
        if not confirm:
            return "Повторите новый пароль", "confirmPasswordInput"
        if new != confirm:
            return "Пароли не совпадают", "confirmPasswordInput"
        return None

    def _show_error(self, text: str):
        self.notification_manager.show_notification(text, duration=4000)

    def save_password(self):
        old = self.oldPasswordInput.text()
        new = self.newPasswordInput.text()
        confirm = self.confirmPasswordInput.text()

        problem = self.validate_passwords(old, new, confirm)
        if problem:
            message, field_name = problem
            self._show_error(message)
            getattr(self, field_name).setFocus()
            return

        if self._change_callback is None:
            self._show_error("Смена пароля не настроена")
            return

        self.saveButton.setEnabled(False)
        QtWidgets.QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._change_callback(old, new)
        except Exception as e:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.saveButton.setEnabled(True)

            text = str(e)
            if "старый пароль" in text.lower():
                self._show_error("Неверно указан старый пароль")
                self.oldPasswordInput.clear()
                self.oldPasswordInput.setFocus()
            elif "совпадать со старым" in text.lower():
                self._show_error("Новый пароль не должен совпадать со старым")
                self.newPasswordInput.setFocus()
            else:
                self._show_error(f"Не удалось сменить пароль:\n{text}")
            return

        QtWidgets.QApplication.restoreOverrideCursor()
        self.saveButton.setEnabled(True)
        self.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    def _fake_change(old, new):
        print(f"Смена пароля: old={old!r} new={new!r}")

    window = NewPasswordWindow(_fake_change)
    window.show()
    sys.exit(app.exec())