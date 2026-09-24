# client/windows/settings/settings_tab.py

import os
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
from PyQt6.uic import loadUi

from client.core.themes import (
    apply_theme_to_widget,
    AVAILABLE_PALETTES,
    AVAILABLE_MODES,
    resolve_theme_key,
    get_palette_and_mode,
)
from client.windows.animations.animated_notification import NotificationManager

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SettingsTab(QWidget):
    """Вкладка «Настройки»: контакты, безопасность, оформление, аккаунт."""

    theme_change_requested = pyqtSignal(str)   # ключ темы, напр. "pink_dark"
    logout_requested = pyqtSignal()
    phone_updated = pyqtSignal(str)  # ← новое
    email_updated = pyqtSignal(str)

    def __init__(self, parent=None, http_client=None):
        super().__init__(parent)

        # HTTP-клиент (нужен для PATCH /employees/me/profile)
        self.http_client = http_client

        ui_path = os.path.join(ROOT_DIR, "ui", "settings", "settings_tab.ui")
        loadUi(ui_path, self)
        apply_theme_to_widget(self)

        # Менеджер всплывающих уведомлений внутри вкладки
        self.notification_manager = NotificationManager(self, max_visible=3)

        self._connect_signals()
        self._load_palettes()
        self._load_modes()

        from client.core.state.data_events import get_data_events

        # в __init__, после _load_modes():
        get_data_events().profile_changed.connect(self._on_profile_changed)

    def _on_profile_changed(self, data: dict):
        if "phone_number" in data:
            self.set_phone(data["phone_number"] or "")
        if "email" in data:
            self.set_email(data["email"] or "")

    def refresh_contacts(self):
        """Подтянуть телефон и email с сервера."""
        if not self.http_client:
            return
        from client.services.employee_service import EmployeeService
        try:
            me = EmployeeService(self.http_client).get_my_profile()
        except Exception as e:
            self.notification_manager.show_notification(
                f"Не удалось загрузить контакты: {e}", duration=4000
            )
            return
        self.set_phone(me.get("phone_number") or "")
        self.set_email(me.get("email") or "")

    # ─────────────────────────────────────────────

    def _connect_signals(self):
        self.changePhoneBtn.clicked.connect(self.on_change_phone)
        self.changeEmailBtn.clicked.connect(self.on_change_email)
        self.changePasswordBtn.clicked.connect(self.on_change_password)
        self.paletteCombo.currentIndexChanged.connect(self._on_theme_changed)
        self.modeCombo.currentIndexChanged.connect(self._on_theme_changed)
        self.logoutBtn.clicked.connect(self.logout_requested.emit)

    def _load_palettes(self):
        for key, (_, _, label) in AVAILABLE_PALETTES.items():
            self.paletteCombo.addItem(label, userData=key)

    def _load_modes(self):
        for key, label in AVAILABLE_MODES.items():
            self.modeCombo.addItem(label, userData=key)

    def _on_theme_changed(self, _index: int = 0):
        palette = self.paletteCombo.currentData()
        mode = self.modeCombo.currentData()
        if not palette or not mode:
            return
        key = resolve_theme_key(palette, mode)
        self.theme_change_requested.emit(key)

    # ─────────────────────────────────────────────
    # Публичное API

    def set_http_client(self, http_client):
        self.http_client = http_client

    def set_phone(self, phone: str):
        """Устанавливает номер в формате '+375 (XX) XXX-XX-XX'."""
        self.phoneValue.setText(self._format_phone(phone) if phone else "—")

    @staticmethod
    def _format_phone(phone: str) -> str:
        if not phone:
            return "—"
        digits = "".join(filter(str.isdigit, phone))
        if len(digits) == 12 and digits.startswith("375"):
            return f"+{digits[:3]} ({digits[3:5]}) {digits[5:8]}-{digits[8:10]}-{digits[10:12]}"
        return phone

    def set_email(self, email: str):
        self.emailValue.setText(email or "—")

    def set_current_theme(self, theme_key: str):
        """Синхронизирует оба комбобокса с текущей темой без эмита сигнала."""
        palette, mode = get_palette_and_mode(theme_key)

        for i in range(self.paletteCombo.count()):
            if self.paletteCombo.itemData(i) == palette:
                self.paletteCombo.blockSignals(True)
                self.paletteCombo.setCurrentIndex(i)
                self.paletteCombo.blockSignals(False)
                break

        for i in range(self.modeCombo.count()):
            if self.modeCombo.itemData(i) == mode:
                self.modeCombo.blockSignals(True)
                self.modeCombo.setCurrentIndex(i)
                self.modeCombo.blockSignals(False)
                break

    def reapply_theme(self):
        """Вызывается apply_theme_to_all_windows()."""
        apply_theme_to_widget(self)

    # ─────────────────────────────────────────────
    # Смена телефона

    def on_change_phone(self):
        """Открывает диалог смены телефона."""
        from client.windows.settings.user_data.phone_edit_window import PhoneEditWindow

        current_digits = "".join(
            filter(str.isdigit, self.phoneValue.text())
        ) or ""

        dialog = PhoneEditWindow(current_digits, parent=self)
        dialog.phone_updated.connect(self._apply_phone_change)
        dialog.exec()

    def _apply_phone_change(self, new_phone: str):
        if not self.http_client:
            self.notification_manager.show_notification(
                "HTTP-клиент не установлен", duration=4000
            )
            return

        from client.services.employee_service import EmployeeService
        from client.core.state.data_events import get_data_events

        try:
            EmployeeService(self.http_client).update_my_profile(
                {"phone_number": new_phone}
            )
        except Exception as e:
            self.notification_manager.show_notification(
                f"Не удалось обновить телефон: {e}",
                duration=4000
            )
            return

        self.set_phone(new_phone)

        # Оповещаем остальные части приложения
        get_data_events().profile_changed.emit({"phone_number": new_phone})

        self.notification_manager.show_notification(
            "Номер телефона обновлён", duration=3000
        )

    def _apply_email_change(self, new_email: str):
        if not self.http_client:
            self.notification_manager.show_notification(
                "HTTP-клиент не установлен", duration=4000
            )
            return

        from client.services.employee_service import EmployeeService
        from client.core.state.data_events import get_data_events

        try:
            EmployeeService(self.http_client).update_my_profile({"email": new_email})
        except Exception as e:
            self.notification_manager.show_notification(
                f"Не удалось обновить email: {e}",
                duration=4000
            )
            return

        self.set_email(new_email)

        # Оповещаем остальные части приложения
        get_data_events().profile_changed.emit({"email": new_email})

        self.notification_manager.show_notification(
            "Email обновлён", duration=3000
        )

    # ─────────────────────────────────────────────
    # Смена email

    def on_change_email(self):
        """Открывает диалог смены email."""
        from client.windows.settings.user_data.email_edit_window import EmailEditWindow

        current = self.emailValue.text()
        if current == "—":
            current = ""

        dialog = EmailEditWindow(current, parent=self)
        dialog.email_updated.connect(self._apply_email_change)
        dialog.exec()

    # ─────────────────────────────────────────────
    # Смена пароля (заглушка)

    def on_change_password(self):
        self.notification_manager.show_notification(
            "Смена пароля будет добавлена позже",
            duration=3000
        )