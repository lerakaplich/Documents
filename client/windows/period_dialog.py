# client/windows/period_dialog.py
import sys
import os
from datetime import datetime, timedelta

from PyQt6.QtWidgets import QDialog, QApplication, QMessageBox
from PyQt6.QtCore import QDate, pyqtSignal
from PyQt6.uic import loadUi

from client.core.themes import T, apply_theme_to_widget


class PeriodDialog(QDialog):
    """
    Диалог для выбора периода дат
    """
    period_selected = pyqtSignal(dict)  # Сигнал с выбранными датами

    def __init__(self, parent=None, start_date=None, end_date=None):
        super().__init__(parent)

        # Инициализация атрибутов ДО загрузки UI
        self.quick_buttons = []
        self.active_button = None

        # Загрузка UI
        self.load_ui()

        # Инициализация
        self.setup_ui(start_date, end_date)
        self.setup_connections()

    def load_ui(self):
        """
        Загрузка UI из файла period_dialog.ui
        """
        try:
            current_file = os.path.abspath(__file__)
            current_dir = os.path.dirname(current_file)
            client_dir = os.path.dirname(current_dir)
            ui_dir = os.path.join(client_dir, 'ui')
            ui_path = os.path.join(ui_dir, 'period_dialog.ui')

            print(f"Поиск UI файла: {ui_path}")

            if not os.path.exists(ui_path):
                alternative_paths = [
                    os.path.join(current_dir, 'period_dialog.ui'),
                    os.path.join(current_dir, '..', 'ui', 'period_dialog.ui'),
                    os.path.join(client_dir, 'period_dialog.ui'),
                    os.path.join(os.path.dirname(client_dir), 'ui', 'period_dialog.ui'),
                ]
                for alt_path in alternative_paths:
                    if os.path.exists(alt_path):
                        ui_path = alt_path
                        print(f"Найден UI файл: {ui_path}")
                        break
                else:
                    print("UI файл не найден, создаю стандартный интерфейс")
                    self.create_default_ui()
                    return

            print(f"Загрузка UI из: {ui_path}")
            loadUi(ui_path, self)
            apply_theme_to_widget(self)

            if hasattr(self, 'todayButton'):
                self.quick_buttons = [
                    self.todayButton,
                    self.weekButton,
                    self.monthButton,
                    self.quarterButton
                ]
                for btn in self.quick_buttons:
                    self.set_default_button_style(btn)

        except Exception as e:
            print(f"Ошибка загрузки UI: {e}")
            self.create_default_ui()

    def create_default_ui(self):
        """Создание UI программно (если файл .ui не найден)"""
        from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QGroupBox,
                                     QLabel, QDateEdit, QPushButton)
        from PyQt6.QtCore import Qt

        self.setWindowTitle("Выбор периода")
        self.setMinimumSize(450, 250)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        self.titleLabel = QLabel("Выбор периода")
        self.titleLabel.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {T.TEXT_PRIMARY};"
        )
        layout.addWidget(self.titleLabel)

        # Группа
        group = QGroupBox("Период")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 14px;
                border: 1px solid {T.BORDER_DEFAULT};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {T.BG_CARD};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {T.TEXT_PRIMARY};
            }}
        """)
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        group_layout.setContentsMargins(15, 15, 15, 15)

        # Начало
        start_layout = QHBoxLayout()
        start_label = QLabel("Начало периода:")
        start_label.setMinimumWidth(90)
        start_label.setStyleSheet(
            f"color: {T.TEXT_PRIMARY}; font-weight: 500;"
        )
        self.startDateEdit = QDateEdit()
        self.startDateEdit.setCalendarPopup(True)
        self.startDateEdit.setDisplayFormat("dd.MM.yyyy")
        self.startDateEdit.setStyleSheet(f"""
            QDateEdit {{
                border: 1px solid {T.BORDER_DEFAULT};
                border-radius: 6px;
                padding: 8px;
                background-color: {T.BG_INPUT};
                color: {T.TEXT_PRIMARY};
                font-size: 13px;
                min-height: 32px;
            }}
            QDateEdit:hover {{ border-color: {T.ACCENT_PRIMARY}; }}
            QDateEdit:focus {{ border: 2px solid {T.ACCENT_PRIMARY}; }}
        """)
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.startDateEdit)
        group_layout.addLayout(start_layout)

        # Конец
        end_layout = QHBoxLayout()
        end_label = QLabel("Конец периода:")
        end_label.setMinimumWidth(90)
        end_label.setStyleSheet(
            f"color: {T.TEXT_PRIMARY}; font-weight: 500;"
        )
        self.endDateEdit = QDateEdit()
        self.endDateEdit.setCalendarPopup(True)
        self.endDateEdit.setDisplayFormat("dd.MM.yyyy")
        self.endDateEdit.setStyleSheet(f"""
            QDateEdit {{
                border: 1px solid {T.BORDER_DEFAULT};
                border-radius: 6px;
                padding: 8px;
                background-color: {T.BG_INPUT};
                color: {T.TEXT_PRIMARY};
                font-size: 13px;
                min-height: 32px;
            }}
            QDateEdit:hover {{ border-color: {T.ACCENT_PRIMARY}; }}
            QDateEdit:focus {{ border: 2px solid {T.ACCENT_PRIMARY}; }}
        """)
        end_layout.addWidget(end_label)
        end_layout.addWidget(self.endDateEdit)
        group_layout.addLayout(end_layout)

        # Кнопки быстрого выбора
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(10)

        self.todayButton = QPushButton("Сегодня")
        self.weekButton = QPushButton("Неделя")
        self.monthButton = QPushButton("Месяц")
        self.quarterButton = QPushButton("Квартал")

        for btn in [self.todayButton, self.weekButton,
                    self.monthButton, self.quarterButton]:
            self.set_default_button_style(btn)
            btn.setCursor(True)

        quick_layout.addWidget(self.todayButton)
        quick_layout.addWidget(self.weekButton)
        quick_layout.addWidget(self.monthButton)
        quick_layout.addWidget(self.quarterButton)
        quick_layout.addStretch()
        group_layout.addLayout(quick_layout)

        layout.addWidget(group)

        # Кнопки действий
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancelButton = QPushButton("Отмена")
        self.applyButton = QPushButton("Применить")

        self.cancelButton.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.BG_HOVER_ALT};
                color: {T.TEXT_PRIMARY};
                border-radius: 8px;
                font-size: 14px;
                border: none;
                padding: 8px 20px;
                min-height: 36px;
            }}
            QPushButton:hover {{ background-color: {T.BG_HOVER_ALT_DARK}; }}
        """)

        self.applyButton.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.ACCENT_PRIMARY};
                color: {T.TEXT_ON_ACCENT};
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 8px 20px;
                min-height: 36px;
            }}
            QPushButton:hover {{ background-color: {T.ACCENT_HOVER}; }}
            QPushButton:pressed {{ background-color: {T.ACCENT_PRESSED}; }}
        """)

        self.cancelButton.setCursor(True)
        self.applyButton.setCursor(True)

        button_layout.addWidget(self.cancelButton)
        button_layout.addWidget(self.applyButton)
        layout.addLayout(button_layout)

        self.periodGroup = group
        self.quick_buttons = [
            self.todayButton, self.weekButton,
            self.monthButton, self.quarterButton
        ]

    def set_default_button_style(self, button):
        """Стандартный стиль кнопки (НЕактивной): чёрный жирный"""
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {T.TEXT_PRIMARY};
                font-weight: bold;
                font-size: 12px;
                border: none;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                color: {T.ACCENT_PRIMARY};
            }}
        """)

    def set_active_button_style(self, button):
        """Активный стиль кнопки: золотой подчёркнутый"""
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {T.ACCENT_PRIMARY};
                font-weight: bold;
                font-size: 12px;
                border: none;
                padding: 4px 8px;
                text-decoration: underline;
            }}
            QPushButton:hover {{
                color: {T.ACCENT_HOVER};
            }}
        """)

    def set_active_button(self, button):
        """Устанавливает активную кнопку и обновляет стили"""
        if self.active_button and self.active_button in self.quick_buttons:
            self.set_default_button_style(self.active_button)

        if button and button in self.quick_buttons:
            self.set_active_button_style(button)
            self.active_button = button
        else:
            self.active_button = None

    def setup_ui(self, start_date=None, end_date=None):
        """Настройка UI с датами"""
        today = QDate.currentDate()

        if start_date:
            self.startDateEdit.setDate(start_date)
        else:
            first_day = QDate(today.year(), today.month(), 1)
            self.startDateEdit.setDate(first_day)

        if end_date:
            self.endDateEdit.setDate(end_date)
        else:
            self.endDateEdit.setDate(today)

        if hasattr(self, 'todayButton') and not self.quick_buttons:
            self.quick_buttons = [self.todayButton, self.weekButton,
                                  self.monthButton, self.quarterButton]
            for btn in self.quick_buttons:
                self.set_default_button_style(btn)

        if start_date and end_date:
            if start_date == today and end_date == today:
                self.set_active_button(self.todayButton)

    def setup_connections(self):
        """Настройка сигналов"""
        if hasattr(self, 'applyButton'):
            self.applyButton.clicked.connect(self.apply_period)
        if hasattr(self, 'cancelButton'):
            self.cancelButton.clicked.connect(self.reject)
        if hasattr(self, 'todayButton'):
            self.todayButton.clicked.connect(self.on_today_clicked)
            self.weekButton.clicked.connect(self.on_week_clicked)
            self.monthButton.clicked.connect(self.on_month_clicked)
            self.quarterButton.clicked.connect(self.on_quarter_clicked)
        if hasattr(self, 'startDateEdit'):
            self.startDateEdit.dateChanged.connect(self.on_date_changed)
        if hasattr(self, 'endDateEdit'):
            self.endDateEdit.dateChanged.connect(self.on_date_changed)

    def on_today_clicked(self):
        self.set_today()
        self.set_active_button(self.todayButton)

    def on_week_clicked(self):
        self.set_week()
        self.set_active_button(self.weekButton)

    def on_month_clicked(self):
        self.set_month()
        self.set_active_button(self.monthButton)

    def on_quarter_clicked(self):
        self.set_quarter()
        self.set_active_button(self.quarterButton)

    def apply_period(self):
        start_date = self.startDateEdit.date()
        end_date = self.endDateEdit.date()

        if start_date > end_date:
            QMessageBox.warning(self, "Ошибка",
                                "Дата начала не может быть позже даты окончания")
            return

        data = {
            'start_date': start_date,
            'end_date': end_date,
            'start_date_str': start_date.toString("dd.MM.yyyy"),
            'end_date_str': end_date.toString("dd.MM.yyyy"),
            'start_date_python': start_date.toPyDate(),
            'end_date_python': end_date.toPyDate()
        }

        self.period_selected.emit(data)
        self.accept()

    def set_today(self):
        today = QDate.currentDate()
        self.startDateEdit.setDate(today)
        self.endDateEdit.setDate(today)

    def set_week(self):
        today = QDate.currentDate()
        days_to_monday = today.dayOfWeek() - 1
        start = today.addDays(-days_to_monday)
        self.startDateEdit.setDate(start)
        end = start.addDays(6)
        self.endDateEdit.setDate(end)

    def set_month(self):
        today = QDate.currentDate()
        first_day = QDate(today.year(), today.month(), 1)
        last_day = QDate(today.year(), today.month(), today.daysInMonth())
        self.startDateEdit.setDate(first_day)
        self.endDateEdit.setDate(last_day)

    def set_quarter(self):
        today = QDate.currentDate()
        month = today.month()

        if month <= 3:
            start_month, end_month = 1, 3
        elif month <= 6:
            start_month, end_month = 4, 6
        elif month <= 9:
            start_month, end_month = 7, 9
        else:
            start_month, end_month = 10, 12

        year = today.year()
        first_day = QDate(year, start_month, 1)
        last_day = QDate(year, end_month,
                         QDate(year, end_month, 1).daysInMonth())

        self.startDateEdit.setDate(first_day)
        self.endDateEdit.setDate(last_day)

    def on_date_changed(self, date):
        """Сброс активной кнопки при ручном изменении даты."""
        if self.active_button:
            self.set_active_button(None)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = PeriodDialog()

    def on_period_selected(data):
        print(f"Выбран период: {data['start_date_str']} - {data['end_date_str']}")
        print(f"Объекты дат: {data['start_date_python']} - {data['end_date_python']}")

    dialog.period_selected.connect(on_period_selected)
    result = dialog.exec()

    if result == QDialog.DialogCode.Accepted:
        print("Период выбран")
    else:
        print("Выбор отменен")

    sys.exit(app.exec())