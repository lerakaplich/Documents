from datetime import date
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QMessageBox

from client.core.themes import T
from client.windows.animations.animated_notification import NotificationManager
from client.windows.period_dialog import PeriodDialog


class OvertimePeriodManager:
    """Управление периодами для фильтрации переработок."""

    def __init__(self, parent=None):
        self.parent = parent

        default_period = self.get_default_overtime_period()
        self.my_period = default_period
        self.all_period = default_period
        self.my_has_filter = False
        self.all_has_filter = False

        if hasattr(parent, 'notification_manager'):
            self.notification_manager = parent.notification_manager
        else:
            self.notification_manager = NotificationManager(parent, max_visible=3)

    @staticmethod
    def get_default_overtime_period():
        """
        Текущий расчётный период переработок: с 25 числа предыдущего месяца
        по 24 число текущего/следующего.
        Пример: 10.09.2026 → 25.08.2026 – 24.09.2026;
                28.09.2026 → 25.09.2026 – 24.10.2026.
        """
        today = date.today()
        if today.day >= 25:
            start = date(today.year, today.month, 25)
            if today.month == 12:
                end = date(today.year + 1, 1, 24)
            else:
                end = date(today.year, today.month + 1, 24)
        else:
            end = date(today.year, today.month, 24)
            if today.month == 1:
                start = date(today.year - 1, 12, 25)
            else:
                start = date(today.year, today.month - 1, 25)
        return {'start': start.strftime('%d.%m.%Y'),
                'end': end.strftime('%d.%m.%Y')}

    @staticmethod
    def period_for_button(period):
        """{'start','end'} → {'start_date_str','end_date_str'} для update_period_button_text."""
        if not period:
            return None
        return {'start_date_str': period['start'], 'end_date_str': period['end']}

    def update_period_button_text(self, button, period_data):
        """Обновляет текст на кнопке выбора периода."""
        if not button:
            return

        if period_data:
            start = period_data['start_date_str']
            end = period_data['end_date_str']
            start_short = start[:-2] + start[-2:]
            end_short = end[:-2] + end[-2:]
            button.setText(f"{start_short} - {end_short}")
            button.setStyleSheet(f"""
                QPushButton {{
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    padding: 0px 16px;
                    color: {T.ACCENT_PRIMARY};
                    font-size: 13px;
                    background-color: transparent;
                }}
                QPushButton:hover {{ background-color: {T.BG_HOVER_LIGHT}; }}
                QPushButton:pressed {{ background-color: {T.BG_PRESSED_LIGHT}; }}
            """)
        else:
            button.setText("Выбрать период")
            button.setStyleSheet(f"""
                QPushButton {{
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    padding: 0px 16px;
                    color: {T.TEXT_ON_ACCENT};
                    background-color: {T.BTN_DARK_BG};
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {T.BTN_DARK_HOVER_BG};
                    color: {T.TEXT_BLACK};
                }}
                QPushButton:pressed {{ background-color: {T.BTN_DARK_PRESSED_BG}; }}
            """)

    def show_period_dialog(self, current_period, callback):
        """Показывает диалог выбора периода."""
        try:
            # Если период не выбран — показываем текущий расчётный
            if current_period:
                start_date = QDate.fromString(current_period['start'], "dd.MM.yyyy")
                end_date = QDate.fromString(current_period['end'], "dd.MM.yyyy")
            else:
                default = self.get_default_overtime_period()
                start_date = QDate.fromString(default['start'], "dd.MM.yyyy")
                end_date = QDate.fromString(default['end'], "dd.MM.yyyy")

            dialog = PeriodDialog(self.parent, start_date=start_date, end_date=end_date)
            dialog.period_selected.connect(callback)
            dialog.exec()
        except Exception as e:
            print(f"Ошибка в show_period_dialog: {e}")
            import traceback
            traceback.print_exc()

            # Показываем уведомление об ошибке
            self.notification_manager.show_notification(
                f"Не удалось открыть окно выбора периода: {str(e)}",
                duration=4000
            )

            QMessageBox.warning(self.parent, "Ошибка", f"Не удалось открыть окно выбора периода\n{str(e)}")

    def on_period_selected(self, period_data, is_my=False, load_callback=None):
        """Обработчик выбора периода."""
        try:
            start_date = period_data['start_date_str']
            end_date = period_data['end_date_str']
            tab_name = "Моих переработок" if is_my else "Всех переработок"

            print(f"Выбран период для '{tab_name}': {start_date} - {end_date}")

            if is_my:
                self.my_period = {'start': start_date, 'end': end_date}
                self.my_has_filter = True
            else:
                self.all_period = {'start': start_date, 'end': end_date}
                self.all_has_filter = True

            # Показываем уведомление об успешном применении фильтра
            self.notification_manager.show_notification(
                f"Фильтр применен: {start_date} - {end_date}",
                duration=3000
            )

            if load_callback:
                load_callback(is_my, start_date, end_date)

        except Exception as e:
            print(f"Ошибка в on_period_selected: {e}")
            import traceback
            traceback.print_exc()

            # Показываем уведомление об ошибке
            self.notification_manager.show_notification(
                f"Ошибка применения фильтра: {str(e)}",
                duration=4000
            )

            QMessageBox.warning(self.parent, "Ошибка", f"Не удалось применить фильтр: {str(e)}")

    def reset_period(self, is_my=False, load_callback=None):
        """Сбрасывает период."""
        if is_my:
            self.my_period = None
            self.my_has_filter = False
            tab_name = "Моих переработок"
        else:
            self.all_period = None
            self.all_has_filter = False
            tab_name = "Всех переработок"

        # Показываем уведомление о сбросе фильтра
        self.notification_manager.show_notification(
            f"Фильтр для '{tab_name}' сброшен",
            duration=2500
        )

        if load_callback:
            load_callback(is_my, None, None)