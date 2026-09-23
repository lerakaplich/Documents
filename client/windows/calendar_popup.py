# client/windows/widgets/calendar_popup.py
"""
Кастомный календарь-виджет для выбора даты.
Заголовок: ◀ [Месяц▾] [Год: SpinBox] ▶
"""
import calendar
from datetime import date

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QToolButton, QFrame, QMenu, QSpinBox,
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QPoint
from PyQt6.QtGui import QFont

from client.core.themes import get_manager


class CalendarPopup(QFrame):
    """
    Кастомный календарь. Показывается как popup.
    """
    date_selected = pyqtSignal(QDate)

    WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    MONTHS = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    ]

    # Границы для поля ввода года
    MIN_YEAR = 1900
    MAX_YEAR = 2200

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup)
        self.setObjectName("CalendarPopup")

        today = QDate.currentDate()
        self._view_year = today.year()
        self._view_month = today.month()
        self._selected = today

        self._build_ui()
        self._build_month_menu()
        self._apply_theme()
        self._render_month()

    # ─────────────── UI ───────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # ── Заголовок: ◀ [Месяц▾] [Год] ▶ ──
        header = QHBoxLayout()
        header.setSpacing(4)

        self.btn_prev = QToolButton()
        self.btn_prev.setText("‹")
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.setFixedSize(26, 26)
        self.btn_prev.clicked.connect(self._prev_month)

        self.btn_month = QToolButton()
        self.btn_month.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_month.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_month.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

        # Год — QSpinBox: можно вводить руками + стрелки
        self.spin_year = QSpinBox()
        self.spin_year.setRange(self.MIN_YEAR, self.MAX_YEAR)
        self.spin_year.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.spin_year.setFixedWidth(60)
        self.spin_year.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_year.setKeyboardTracking(False)   # valueChanged — после Enter/потери фокуса
        self.spin_year.valueChanged.connect(self._on_year_changed)
        self.spin_year.editingFinished.connect(self._on_year_editing_finished)

        self.btn_next = QToolButton()
        self.btn_next.setText("›")
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setFixedSize(26, 26)
        self.btn_next.clicked.connect(self._next_month)

        header.addWidget(self.btn_prev)
        header.addWidget(self.btn_month, 1)
        header.addWidget(self.spin_year)
        header.addWidget(self.btn_next)
        root.addLayout(header)

        # ── Сетка дней ──
        self.grid = QGridLayout()
        self.grid.setSpacing(2)
        self.grid.setContentsMargins(0, 0, 0, 0)

        self.weekday_labels = []
        for i, name in enumerate(self.WEEKDAYS):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedHeight(22)
            f = QFont()
            f.setPointSize(9)
            f.setBold(True)
            lbl.setFont(f)
            self.grid.addWidget(lbl, 0, i)
            self.weekday_labels.append(lbl)

        self.day_buttons = []
        for row in range(6):
            row_buttons = []
            for col in range(7):
                btn = QPushButton("")
                btn.setFixedSize(32, 32)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _c, b=btn: self._on_day_clicked(b))
                self.grid.addWidget(btn, row + 1, col)
                row_buttons.append(btn)
            self.day_buttons.append(row_buttons)

        root.addLayout(self.grid)

        # ── Футер ──
        self.btn_today = QPushButton("Сегодня")
        self.btn_today.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_today.clicked.connect(self._on_today_clicked)
        root.addWidget(self.btn_today)

        self.setFixedWidth(260)

    def _build_month_menu(self):
        """Меню выбора месяца."""
        menu = QMenu(self.btn_month)
        for i, name in enumerate(self.MONTHS, start=1):
            act = menu.addAction(name)
            act.triggered.connect(lambda _c, m=i: self._set_month(m))
        self.btn_month.setMenu(menu)

    # ─────────────── Тема ───────────────

    def _apply_theme(self):
        t = get_manager().current

        self.setStyleSheet(f"""
            QFrame#CalendarPopup {{
                background-color: {t.BG_CARD};
                border: 1px solid {t.BORDER_DEFAULT};
                border-radius: 10px;
            }}
        """)

        nav_style = f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: {t.TEXT_PRIMARY};
                font-size: 18px;
                font-weight: bold;
            }}
            QToolButton:hover {{ background-color: {t.BG_HOVER_LIGHT}; }}
            QToolButton:pressed {{ background-color: {t.BG_PRESSED_LIGHT}; }}
        """
        self.btn_prev.setStyleSheet(nav_style)
        self.btn_next.setStyleSheet(nav_style)

        self.btn_month.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                color: {t.TEXT_HEADING};
                font-size: 11px;
                font-weight: bold;
                padding: 3px 6px;
            }}
            QToolButton:hover {{
                background-color: {t.BG_HOVER_LIGHT};
                border-color: {t.BORDER_DEFAULT};
            }}
            QToolButton::menu-indicator {{ image: none; width: 0px; }}
        """)

        # Стиль меню месяца
        try:
            from client.core.themes import get_menu_style
            self.btn_month.menu().setStyleSheet(get_menu_style())
        except Exception:
            pass

        # Стиль QSpinBox года
        self.spin_year.setStyleSheet(f"""
            QSpinBox {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                color: {t.TEXT_HEADING};
                font-size: 11px;
                font-weight: bold;
                padding: 3px 4px;
            }}
            QSpinBox:hover {{
                background-color: {t.BG_HOVER_LIGHT};
                border-color: {t.BORDER_DEFAULT};
            }}
            QSpinBox:focus {{
                border: 1px solid {t.ACCENT_PRIMARY};
                background-color: {t.BG_INPUT};
                color: {t.TEXT_PRIMARY};
            }}
        """)

        for lbl in self.weekday_labels:
            lbl.setStyleSheet(f"color: {t.TEXT_MUTED_ALT}; background: transparent;")

        self.btn_today.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {t.BORDER_DEFAULT};
                border-radius: 6px;
                color: {t.TEXT_PRIMARY};
                font-size: 11px;
                padding: 4px 10px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {t.BG_HOVER_LIGHT};
                border-color: {t.ACCENT_PRIMARY};
            }}
            QPushButton:pressed {{ background-color: {t.BG_PRESSED_LIGHT}; }}
        """)

    def _style_day_button(self, btn, is_current_month, is_today, is_selected):
        t = get_manager().current
        if is_selected:
            bg, fg, border = t.ACCENT_PRIMARY, t.TEXT_ON_ACCENT, t.ACCENT_PRIMARY
            hover_bg, hover_fg = t.ACCENT_HOVER, t.TEXT_ON_ACCENT
        elif is_today:
            bg, fg, border = "transparent", t.ACCENT_PRIMARY, t.ACCENT_PRIMARY
            hover_bg, hover_fg = t.ACCENT_PRIMARY_ALPHA_20, t.ACCENT_PRIMARY
        elif not is_current_month:
            bg, fg, border = "transparent", t.TEXT_TERTIARY, "transparent"
            hover_bg, hover_fg = t.BG_HOVER_LIGHT, t.TEXT_MUTED_ALT
        else:
            bg, fg, border = "transparent", t.TEXT_PRIMARY, "transparent"
            hover_bg, hover_fg = t.BG_HOVER_LIGHT, t.TEXT_PRIMARY

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 8px;
                font-size: 11px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                color: {hover_fg};
            }}
            QPushButton:pressed {{ background-color: {t.BG_PRESSED_LIGHT}; }}
        """)

    # ─────────────── Рендер ───────────────

    def _render_month(self):
        self.btn_month.setText(self.MONTHS[self._view_month - 1])

        # Обновляем QSpinBox, НЕ вызывая valueChanged (иначе рекурсия)
        self.spin_year.blockSignals(True)
        self.spin_year.setValue(self._view_year)
        self.spin_year.blockSignals(False)

        first = date(self._view_year, self._view_month, 1)
        first_weekday = first.weekday()
        days_in_month = calendar.monthrange(self._view_year, self._view_month)[1]

        today = QDate.currentDate()
        today_d = date(today.year(), today.month(), today.day())
        sel = self._selected
        sel_d = date(sel.year(), sel.month(), sel.day())

        prev_year, prev_month = self._view_year, self._view_month - 1
        if prev_month == 0:
            prev_month, prev_year = 12, prev_year - 1
        days_in_prev = calendar.monthrange(prev_year, prev_month)[1]

        day_num = 1
        for idx in range(42):
            row, col = idx // 7, idx % 7
            btn = self.day_buttons[row][col]

            if idx < first_weekday:
                n = days_in_prev - (first_weekday - 1 - idx)
                d = date(prev_year, prev_month, n)
                is_current_month = False
            elif day_num <= days_in_month:
                d = date(self._view_year, self._view_month, day_num)
                day_num += 1
                is_current_month = True
            else:
                next_year, next_month = self._view_year, self._view_month + 1
                if next_month == 13:
                    next_month, next_year = 1, next_year + 1
                n = idx - (first_weekday + days_in_month) + 1
                d = date(next_year, next_month, n)
                is_current_month = False

            btn.setText(str(d.day))
            btn.setProperty("date", d)
            self._style_day_button(
                btn,
                is_current_month=is_current_month,
                is_today=(d == today_d),
                is_selected=(d == sel_d),
            )

    # ─────────────── Логика ───────────────

    def _prev_month(self):
        if self._view_month == 1:
            self._view_month, self._view_year = 12, self._view_year - 1
        else:
            self._view_month -= 1
        self._render_month()

    def _next_month(self):
        if self._view_month == 12:
            self._view_month, self._view_year = 1, self._view_year + 1
        else:
            self._view_month += 1
        self._render_month()

    def _set_month(self, month: int):
        self._view_month = month
        self._render_month()

    def _on_year_changed(self, value: int):
        """Пользователь закончил редактирование QSpinBox (Enter или потеря фокуса)."""
        if value != self._view_year:
            self._view_year = value
            self._render_month()

    def _on_year_editing_finished(self):
        """На случай, если значение не изменилось — просто перерисуем."""
        self._render_month()

    def _on_day_clicked(self, btn):
        d = btn.property("date")
        if not isinstance(d, date):
            return
        self._selected = QDate(d.year, d.month, d.day)
        self.date_selected.emit(self._selected)
        self.close()

    def _on_today_clicked(self):
        self._selected = QDate.currentDate()
        self._view_year = self._selected.year()
        self._view_month = self._selected.month()
        self.date_selected.emit(self._selected)
        self.close()

    # ─────────────── Публичное API ───────────────

    def set_date(self, qdate: QDate):
        if not qdate.isValid():
            qdate = QDate.currentDate()
        self._selected = qdate
        self._view_year = qdate.year()
        self._view_month = qdate.month()
        self._render_month()

    def selected_date(self) -> QDate:
        return self._selected

    def popup_at(self, global_pos: QPoint):
        self.move(global_pos)
        self.show()
        self.raise_()
        self.activateWindow()

    def reapply_theme(self):
        self._apply_theme()
        self._render_month()