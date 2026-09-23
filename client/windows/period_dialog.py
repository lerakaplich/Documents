# client/windows/period_dialog.py
"""
Диалог выбора периода дат.

- Стили задаются явно на каждом виджете (QSS из .ui в этом окружении
  не долетает до вложенных виджетов).
- По клику на QDateEdit открывается наш CalendarPopup.
- Кнопка «Отмена» убрана, «Применить» растянута.
"""
import os
import sys

from PyQt6.QtWidgets import (
    QDialog, QApplication, QMessageBox,
    QSizePolicy,
)
from PyQt6.QtCore import QDate, pyqtSignal, Qt, QPoint, QEvent, QTimer
from PyQt6.uic import loadUi

from client.core.themes import get_manager
from client.core.themes.icon_utils import icon_path
from client.windows.calendar_popup import CalendarPopup

try:
    _HAS_POPUP = True
except ImportError as e:
    _HAS_POPUP = False
    print(f"[PeriodDialog] CalendarPopup недоступен: {e}")


class PeriodDialog(QDialog):
    """Диалог выбора периода дат."""

    period_selected = pyqtSignal(dict)

    QUICK_BUTTONS = ("todayButton", "weekButton", "monthButton", "quarterButton")

    def __init__(self, parent=None, start_date=None, end_date=None):
        super().__init__(parent)

        self._active_button = None
        self._popups = {}                 # name -> CalendarPopup
        self._field_popup_map = {}        # id(widget) -> popup

        self._load_ui()
        self._setup_spacing()
        self._install_popups()
        self._setup_dates(start_date, end_date)
        self._connect_signals()
        self._apply_styles()

    # ─────────── Загрузка UI ───────────

    def _load_ui(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        client_dir = os.path.dirname(current_dir)
        ui_path = os.path.join(client_dir, "ui", "period_dialog.ui")

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI файл не найден: {ui_path}")

        loadUi(ui_path, self)

    # ─────────── Воздух между «Начало» и «Конец» ───────────

    def _setup_spacing(self):
        """Больше места между строками с датами."""
        try:
            self.periodLayout.setSpacing(20)
        except Exception:
            pass
        # Между двумя строками дат можно добавить ещё чуть-чуть
        try:
            from PyQt6.QtWidgets import QSpacerItem
            spacer = QSpacerItem(
                0, 6,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Fixed,
            )
            # Вставляем перед endDateLayout (индекс 1)
            self.periodLayout.insertItem(1, spacer)
        except Exception:
            pass



    # ─────────── Кастомный календарь на существующих QDateEdit ───────────

    from PyQt6.QtCore import QTimer  # добавьте в импорты

    def _install_popups(self):
        """Открываем CalendarPopup по клику на поле даты (включая иконку)."""
        if not _HAS_POPUP:
            for name in ("startDateEdit", "endDateEdit"):
                f = getattr(self, name, None)
                if f is not None:
                    try:
                        f.setCalendarPopup(True)
                    except Exception:
                        pass
            return

        for name in ("startDateEdit", "endDateEdit"):
            field = getattr(self, name, None)
            if field is None:
                continue

            # ВАЖНО: True, чтобы Qt отрисовал настоящий ::drop-down
            # (иконка календаря) и она попадала в клик-зону виджета.
            # Системный попап не покажется — eventFilter его съест.
            try:
                field.setCalendarPopup(True)
            except Exception:
                pass

            popup = CalendarPopup(field)
            popup.date_selected.connect(field.setDate)
            self._popups[name] = popup

            field.installEventFilter(self)
            self._field_popup_map[id(field)] = popup

            le = field.lineEdit()
            if le is not None:
                le.installEventFilter(self)
                self._field_popup_map[id(le)] = popup

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.MouseButtonPress,
                            QEvent.Type.MouseButtonDblClick):
            if event.button() == Qt.MouseButton.LeftButton:
                popup = self._field_popup_map.get(id(obj))
                if popup is not None:
                    field = popup.parent()
                    if field is not None:
                        popup.set_date(field.date())
                        pos = field.mapToGlobal(QPoint(0, field.height() + 2))
                        popup.popup_at(pos)
                        return True
        return super().eventFilter(obj, event)

    # ─────────── Стили (явно на каждом виджете) ───────────

    def _apply_styles(self):
        _t = get_manager().current

        self.setStyleSheet(f"QDialog {{ background-color: {_t.BG_DIALOG}; }}")

        self.titleLabel.setStyleSheet(
            f"color: {_t.TEXT_PRIMARY}; font-size: 20px; font-weight: bold; "
            f"background: transparent; padding: 0 0 4px 0;"
        )



        for name in ("startLabel", "endLabel"):
            lbl = getattr(self, name, None)
            if lbl is not None:
                lbl.setStyleSheet(
                    f"color: {_t.TEXT_PRIMARY}; background: transparent; "
                    f"font-size: 13px;"
                )

        cal_icon = icon_path("calendar_date", _t.ICON_COLOR)
        date_style = f"""
            QDateEdit {{
                border: 1px solid {_t.BORDER_DEFAULT};
                border-radius: 6px;
                padding: 6px 8px;
                padding-right: 32px;
                background-color: {_t.BG_INPUT};
                color: {_t.TEXT_PRIMARY};
                font-size: 13px;
                min-height: 22px;
            }}
            QDateEdit:hover {{
                border-color: {_t.ACCENT_PRIMARY};
            }}
            QDateEdit:focus {{
                border: 2px solid {_t.ACCENT_PRIMARY};
            }}
            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border: none;
                background: transparent;
            }}
            QDateEdit::down-arrow {{
                image: url({cal_icon});
                width: 16px;
                height: 16px;
                margin-right: 6px;
            }}
        """
        for name in ("startDateEdit", "endDateEdit"):
            field = getattr(self, name, None)
            if field is None:
                continue
            field.setStyleSheet(date_style)
            le = field.lineEdit()
            if le is not None:
                le.setStyleSheet(
                    f"background: transparent; color: {_t.TEXT_PRIMARY}; "
                    f"border: none; padding: 0;"
                )



        # «Применить»
        self.applyButton.setStyleSheet(f"""
            QPushButton {{
                background-color: {_t.ACCENT_PRIMARY};
                color: {_t.TEXT_ON_ACCENT};
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                padding: 0 20px;
                min-height: 42px;
            }}
            QPushButton:hover {{
                background-color: {_t.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {_t.ACCENT_PRESSED};
            }}
        """)

        self._refresh_quick_styles()

    def _refresh_quick_styles(self):
        for name in self.QUICK_BUTTONS:
            btn = getattr(self, name, None)
            if btn is None:
                continue
            self._style_quick(btn, btn is self._active_button)

    @staticmethod
    def _style_quick(btn, is_active: bool):
        _t = get_manager().current
        if is_active:
            color = _t.ACCENT_PRIMARY
            border = _t.ACCENT_PRIMARY
            bg = _t.ACCENT_PRIMARY_ALPHA_10
        else:
            color = _t.TEXT_PRIMARY
            border = "transparent"
            bg = "transparent"

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: 1px solid {border};
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 4px 10px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                color: {_t.ACCENT_PRIMARY};
                border: 1px solid {_t.ACCENT_PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {_t.BG_PRESSED_LIGHT};
            }}
        """)

    # ─────────── Даты ───────────

    def _setup_dates(self, start_date, end_date):
        today = QDate.currentDate()
        if start_date is None:
            start_date = QDate(today.year(), today.month(), 1)
        if end_date is None:
            end_date = today
        self.startDateEdit.setDate(start_date)
        self.endDateEdit.setDate(end_date)

    # ─────────── Сигналы ───────────

    def _connect_signals(self):
        self.applyButton.clicked.connect(self._on_apply)

        self.weekButton.clicked.connect(lambda: self._apply_quick("weekButton", self._set_week))
        self.monthButton.clicked.connect(lambda: self._apply_quick("monthButton", self._set_month))
        self.quarterButton.clicked.connect(lambda: self._apply_quick("quarterButton", self._set_quarter))

        self.startDateEdit.dateChanged.connect(self._on_date_changed)
        self.endDateEdit.dateChanged.connect(self._on_date_changed)

    def _apply_quick(self, button_name, setter):
        setter()
        self._set_active_button(getattr(self, button_name))

    def _on_date_changed(self, _date):
        if self._active_button is not None:
            self._set_active_button(None)

    def _set_active_button(self, button):
        old = self._active_button
        self._active_button = button
        if old is not None:
            self._style_quick(old, False)
        if button is not None:
            self._style_quick(button, True)

    # ─────────── Логика quick-кнопок ───────────

    def _set_today(self):
        t = QDate.currentDate()
        self.startDateEdit.setDate(t)
        self.endDateEdit.setDate(t)

    def _set_week(self):
        today = QDate.currentDate()
        monday = today.addDays(-(today.dayOfWeek() - 1))
        self.startDateEdit.setDate(monday)
        self.endDateEdit.setDate(monday.addDays(6))

    def _set_month(self):
        today = QDate.currentDate()
        self.startDateEdit.setDate(QDate(today.year(), today.month(), 1))
        self.endDateEdit.setDate(QDate(today.year(), today.month(), today.daysInMonth()))

    def _set_quarter(self):
        today = QDate.currentDate()
        m = today.month()
        if m <= 3:   sm, em = 1, 3
        elif m <= 6: sm, em = 4, 6
        elif m <= 9: sm, em = 7, 9
        else:        sm, em = 10, 12
        y = today.year()
        self.startDateEdit.setDate(QDate(y, sm, 1))
        self.endDateEdit.setDate(QDate(y, em, QDate(y, em, 1).daysInMonth()))

    # ─────────── Применить ───────────

    def _on_apply(self):
        s = self.startDateEdit.date()
        e = self.endDateEdit.date()
        if s > e:
            QMessageBox.warning(self, "Ошибка",
                                "Дата начала не может быть позже даты окончания")
            return

        self.period_selected.emit({
            "start_date": s,
            "end_date": e,
            "start_date_str": s.toString("dd.MM.yyyy"),
            "end_date_str": e.toString("dd.MM.yyyy"),
            "start_date_python": s.toPyDate(),
            "end_date_python": e.toPyDate(),
        })
        self.accept()

    # ─────────── Тема ───────────

    def reapply_theme(self):
        self._apply_styles()
        for popup in self._popups.values():
            try:
                popup.reapply_theme()
            except Exception:
                pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = PeriodDialog()
    dlg.period_selected.connect(
        lambda d: print(f"Период: {d['start_date_str']} – {d['end_date_str']}")
    )
    sys.exit(dlg.exec())