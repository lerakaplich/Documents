# client/windows/profile/overtime/overtime_import_export_manager.py
from datetime import datetime

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QFileDialog

from client.windows.period_dialog import PeriodDialog


class OvertimeImportExportManager:
    """Импорт из Excel и экспорт в Excel."""

    def __init__(self, panel):
        self.panel = panel  # OvertimePanel

    def _notify(self, message, duration=3000):
        parent = self.panel.parent
        if hasattr(parent, 'notification_manager'):
            parent.notification_manager.show_notification(message, duration=duration)

    # ==================== ИМПОРТ ====================

    def on_import_clicked(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self.panel.parent,
                "Выберите файл выгрузки СКУД",
                "",
                "Excel files (*.xlsx *.xls)"
            )
            if not file_path:
                return

            if not self.panel.overtime_service:
                self._notify("Сервис переработок недоступен")
                return

            self._notify("Импорт переработок... Пожалуйста, подождите")

            result = self.panel.overtime_service.import_overtime(file_path)

            self.panel.load_overtime_data(
                filter_department_id=self.panel.data_manager.current_filter_department_id,
            )

            message = "Импорт завершён"
            if isinstance(result, dict):
                data = result.get("data")
                if isinstance(data, dict):
                    for key in ("imported", "created", "updated", "total", "processed"):
                        if key in data:
                            message += f". {key}: {data[key]}"
                            break
            self._notify(message, duration=5000)
        except Exception as e:
            print(f"❌ Ошибка импорта переработок: {e}")
            import traceback
            traceback.print_exc()
            self._notify(f"Ошибка импорта: {str(e)}", duration=5000)

    # ==================== ЭКСПОРТ ====================

    def on_export_clicked(self):
        try:
            start_date = None
            end_date = None
            period_manager = self.panel.period_manager
            if period_manager.all_period:
                try:
                    start_date = QDate.fromString(period_manager.all_period['start'], "dd.MM.yyyy")
                    end_date = QDate.fromString(period_manager.all_period['end'], "dd.MM.yyyy")
                except Exception:
                    pass

            if not start_date or not start_date.isValid():
                default = period_manager.get_default_overtime_period()
                start_date = QDate.fromString(default['start'], "dd.MM.yyyy")
                end_date = QDate.fromString(default['end'], "dd.MM.yyyy")

            dialog = PeriodDialog(self.panel.parent, start_date=start_date, end_date=end_date)
            dialog.period_selected.connect(self.on_export_period_selected)
            dialog.exec()
        except Exception as e:
            self._notify(f"Ошибка открытия окна экспорта: {str(e)}", duration=4000)

    def on_export_period_selected(self, period_data):
        try:
            start_date_str = period_data['start_date_str']
            end_date_str = period_data['end_date_str']
            print(f"Экспорт данных за период: {start_date_str} - {end_date_str}")

            if not self.panel.overtime_service:
                self._notify(f"Экспорт за период {start_date_str} - {end_date_str} (заглушка)")
                return

            try:
                start_date = datetime.strptime(start_date_str, "%d.%m.%Y").date()
                end_date = datetime.strptime(end_date_str, "%d.%m.%Y").date()

                excel_data = self.panel.overtime_service.export_overtime(
                    dept_id=self.panel.data_manager.current_filter_department_id,
                    start_date=start_date,
                    end_date=end_date
                )

                file_path, _ = QFileDialog.getSaveFileName(
                    self.panel.parent,
                    "Сохранить отчет",
                    f"Отчет_по_переработкам_{start_date_str}_{end_date_str}.xlsx",
                    "Excel files (*.xlsx)"
                )
                if file_path:
                    with open(file_path, 'wb') as f:
                        f.write(excel_data)
                    self._notify(f"Отчет сохранен: {file_path}")
            except Exception as e:
                print(f"❌ Ошибка экспорта: {e}")
                self._notify(f"Ошибка экспорта: {str(e)}", duration=4000)
        except Exception as e:
            print(f"Ошибка в on_export_period_selected: {e}")
            import traceback
            traceback.print_exc()
            self._notify(f"Ошибка экспорта: {str(e)}", duration=4000)