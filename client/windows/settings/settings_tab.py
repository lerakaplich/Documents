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

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SettingsTab(QWidget):
    """Вкладка «Настройки»: контакты, безопасность, оформление, аккаунт."""

    phone_change_requested = pyqtSignal()
    email_change_requested = pyqtSignal()
    password_change_requested = pyqtSignal()
    theme_change_requested = pyqtSignal(str)   # ключ темы, напр. "pink_dark"
    logout_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(ROOT_DIR, "ui", "settings", "settings_tab.ui")
        loadUi(ui_path, self)
        apply_theme_to_widget(self)

        self._connect_signals()
        self._load_palettes()
        self._load_modes()

    # ─────────────────────────────────────────────

    def _connect_signals(self):
        self.changePhoneBtn.clicked.connect(self.phone_change_requested.emit)
        self.changeEmailBtn.clicked.connect(self.email_change_requested.emit)
        self.changePasswordBtn.clicked.connect(self.password_change_requested.emit)
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

    def set_phone(self, phone: str):
        self.phoneValue.setText(phone or "—")

    def set_email(self, email: str):
        self.emailValue.setText(email or "—")

    def set_current_theme(self, theme_key: str):
        """Синхронизирует оба комбобокса с текущей темой без эмита сигнала."""
        palette, mode = get_palette_and_mode(theme_key)

        # палитра
        for i in range(self.paletteCombo.count()):
            if self.paletteCombo.itemData(i) == palette:
                self.paletteCombo.blockSignals(True)
                self.paletteCombo.setCurrentIndex(i)
                self.paletteCombo.blockSignals(False)
                break

        # режим
        for i in range(self.modeCombo.count()):
            if self.modeCombo.itemData(i) == mode:
                self.modeCombo.blockSignals(True)
                self.modeCombo.setCurrentIndex(i)
                self.modeCombo.blockSignals(False)
                break

    def reapply_theme(self):
        """Вызывается apply_theme_to_all_windows()."""
        apply_theme_to_widget(self)