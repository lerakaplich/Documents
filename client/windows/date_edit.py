# client/windows/widgets/date_edit.py
"""
QDateEdit, у которого системный календарь заменён на CalendarPopup.
Клик в любом месте поля (цифры, пустое место, стрелка) открывает
наш кастомный календарь.
"""

from PyQt6.QtCore import QEvent, QPoint, Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QDateEdit

from client.windows.calendar_popup import CalendarPopup


class CustomCalendarDateEdit(QDateEdit):
    """QDateEdit с кастомным календарём вместо системного."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # ВАЖНО: НЕ отключаем calendarPopup.
        # При False Qt перестаёт резервировать область под drop-down
        # (SC_SpinBoxEditField на всю ширину), а CSS из .ui всё равно
        # рисует ::drop-down/::down-arrow — иконка календаря уезжает
        # за правый край поля.
        # Оставляем True → Qt корректно раскладывает ::drop-down,
        # иконка стоит внутри QDateEdit, ровно в зоне padding-right:32px.
        # Системный попап мы всё равно не дадим открыться — клики
        # перехватываются ниже.
        self.setCalendarPopup(True)

        # Наш календарь
        self._popup = CalendarPopup(self)
        self._popup.date_selected.connect(self.setDate)

        # Клики по тексту ловит внутренний QLineEdit — вешаем фильтр.
        le = self.lineEdit()
        if le is not None:
            le.installEventFilter(self)
            le.setReadOnly(True)

    # ─────────── Открытие попапа ───────────

    def _open_calendar_popup(self):
        self._popup.set_date(self.date())

        # Форсируем пересчёт размеров ДО расчёта позиции
        self._popup.adjustSize()

        popup_w = self._popup.width()
        popup_h = self._popup.height()

        tl = self.mapToGlobal(self.rect().topLeft())
        bl = self.mapToGlobal(self.rect().bottomLeft())

        x = bl.x()
        y = bl.y() + 2

        # Зажимаем попап в границах экрана
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            if x + popup_w > avail.right():
                x = avail.right() - popup_w
            if x < avail.left():
                x = avail.left()
            if y + popup_h > avail.bottom():
                y = tl.y() - popup_h - 2
                if y < avail.top():
                    y = avail.top()

        self._popup.popup_at(QPoint(x, y))

    # ─────────── События ───────────

    def mousePressEvent(self, event):
        """
        Клик по самому QDateEdit (в т.ч. по styled drop-down с иконкой).
        Перехватываем ЛЮБОЙ левый клик и открываем наш попап — так системный
        календарь QDateEdit никогда не появится, а иконка из .ui останется
        на месте (внутри поля).
        """
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