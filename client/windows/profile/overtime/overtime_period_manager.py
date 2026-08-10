from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QMessageBox

from client.windows.period_dialog import PeriodDialog


class OvertimePeriodManager:
    """Управление периодами для фильтрации переработок."""

    def __init__(self, parent=None):
        self.parent = parent  # ProfileForm (QWidget)
        self.my_period = None
        self.all_period = None
        self.my_has_filter = False
        self.all_has_filter = False

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
            button.setStyleSheet("""
                QPushButton {
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    padding: 0px 16px;
                    color: #ccab6e;
                    font-size: 13px;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                }
                QPushButton:pressed {
                    background-color: #e0e0e0;
                }
            """)
        else:
            button.setText("Выбрать период")
            button.setStyleSheet("""
                QPushButton {
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    padding: 0px 16px;
                    color: white;
                    background-color: #1B232A;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #D9D9D6;
                    color: black;
                }
                QPushButton:pressed {
                    background-color: #B8B8B5;
                }
            """)

    def show_period_dialog(self, current_period, callback):
        """Показывает диалог выбора периода."""
        try:
            start_date = None
            end_date = None
            if current_period:
                try:
                    start_date = QDate.fromString(current_period['start'], "dd.MM.yyyy")
                    end_date = QDate.fromString(current_period['end'], "dd.MM.yyyy")
                except:
                    pass

            dialog = PeriodDialog(self.parent, start_date=start_date, end_date=end_date)
            dialog.period_selected.connect(callback)
            dialog.exec()
        except Exception as e:
            print(f"Ошибка в show_period_dialog: {e}")
            import traceback
            traceback.print_exc()
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

            if load_callback:
                load_callback(is_my, start_date, end_date)

        except Exception as e:
            print(f"Ошибка в on_period_selected: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self.parent, "Ошибка", f"Не удалось применить фильтр: {str(e)}")

    def reset_period(self, is_my=False, load_callback=None):
        """Сбрасывает период."""
        if is_my:
            self.my_period = None
            self.my_has_filter = False
        else:
            self.all_period = None
            self.all_has_filter = False

        if load_callback:
            load_callback(is_my, None, None)