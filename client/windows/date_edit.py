# client/windows/widgets/date_edit.py
"""
QDateEdit, у которого системный календарь заменён на CalendarPopup.
Клик в любом месте поля (цифры, пустое место, стрелка) открывает
наш кастомный календарь.
"""
from PyQt6.QtWidgets import QDateEdit
from PyQt6.QtCore import Qt, QDate, QPoint, QEvent

from client.windows.calendar_popup import CalendarPopup


class CustomCalendarDateEdit(QDateEdit):
    """QDateEdit с кастомным календарём вместо системного."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Отключаем системный попап
        self.setCalendarPopup(False)

        # Наш календарь
        self._popup = CalendarPopup(self)
        self._popup.date_selected.connect(self.setDate)

        # Клики по тексту ловит внутренний QLineEdit — вешаем фильтр
        # и запрещаем редактирование вручную, чтобы не дёргалось выделение.
        le = self.lineEdit()
        if le is not None:
            le.installEventFilter(self)
            le.setReadOnly(True)

    # ─────────── Открытие попапа ───────────

    def _open_calendar_popup(self):
        self._popup.set_date(self.date())
        pos = self.mapToGlobal(QPoint(0, self.height() + 2))
        self._popup.popup_at(pos)

    # ─────────── События ───────────

    def mousePressEvent(self, event):
        """Клик по самому QDateEdit (в т.ч. по зоне drop-down)."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_calendar_popup()
            event.accept()
            return
        super().mousePressEvent(event)

    def eventFilter(self, obj, event):
        """Клик по внутреннему QLineEdit → открываем попап."""
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton and obj is self.lineEdit():
                self._open_calendar_popup()
                return True
        return super().eventFilter(obj, event)

    # ─────────── Тема ───────────

    def reapply_theme(self):
        self._popup.reapply_theme()