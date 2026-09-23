# client/windows/settings/settings_tab.py

import os
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
from PyQt6.uic import loadUi

from client.core.themes import apply_theme_to_widget

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SettingsTab(QWidget):
    """Вкладка «Настройки»: контакты, безопасность, оформление."""

    phone_change_requested = pyqtSignal()
    email_change_requested = pyqtSignal()
    password_change_requested = pyqtSignal()
    theme_change_requested = pyqtSignal(str)  # ключ темы

    def __init__(self, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(ROOT_DIR, "ui", "settings", "settings_tab.ui")
        loadUi(ui_path, self)
        apply_theme_to_widget(self)

        self._connect_signals()
        self._load_themes()

    # ─────────────────────────────────────────────

    def _connect_signals(self):
        self.changePhoneBtn.clicked.connect(self.phone_change_requested.emit)
        self.changeEmailBtn.clicked.connect(self.email_change_requested.emit)
        self.changePasswordBtn.clicked.connect(self.password_change_requested.emit)
        self.themeCombo.currentIndexChanged.connect(self._on_theme_selected)

    def _load_themes(self):
        """Заполняет список тем из реестра AVAILABLE_THEMES."""
        from client.core.themes import AVAILABLE_THEMES
        for key, (_, label) in AVAILABLE_THEMES.items():
            self.themeCombo.addItem(label, userData=key)

    def _on_theme_selected(self, index: int):
        key = self.themeCombo.itemData(index)
        if key:
            self.theme_change_requested.emit(key)

    # ─────────────────────────────────────────────
    # Публичное API

    def set_phone(self, phone: str):
        self.phoneValue.setText(phone or "—")

    def set_email(self, email: str):
        self.emailValue.setText(email or "—")

    def set_current_theme(self, key: str):
        """Устанавливает тему в комбобоксе без эмита сигнала."""
        for i in range(self.themeCombo.count()):
            if self.themeCombo.itemData(i) == key:
                self.themeCombo.blockSignals(True)
                self.themeCombo.setCurrentIndex(i)
                self.themeCombo.blockSignals(False)
                break