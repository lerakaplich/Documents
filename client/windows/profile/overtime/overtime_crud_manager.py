# client/windows/profile/overtime/overtime_crud_manager.py
from datetime import datetime
from PyQt6.QtWidgets import QDialog

from client.windows.profile.overtime.overtime_dialog import OvertimeDialog


class OvertimeCrudManager:
    """Создание, редактирование и удаление переработок."""

    def __init__(self, panel):
        self.panel = panel  # OvertimePanel

    @property
    def _parent(self):
        return self.panel.parent

    @property
    def _service(self):
        return self.panel.overtime_service

    def _notify(self, message, duration=3000):
        if hasattr(self._parent, 'notification_manager'):
            self._parent.notification_manager.show_notification(message, duration=duration)

    # ==================== СОЗДАНИЕ ====================

    def add_overtime(self):
        dialog = OvertimeDialog(
            self._parent,
            readonly=False,
            overtime_service=self._service,
            current_employee_id=self.panel.current_employee_id or 1
        )

        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.result_data is None:
            return

        data = dialog.result_data
        employee_id = dialog.get_selected_employee_id()
        if not employee_id:
            self._notify("Не удалось определить сотрудника")
            return

        if not self._service:
            return

        try:
            date_obj = datetime.strptime(data['date'], "%d.%m.%Y")
            create_data = {
                "employee_id": employee_id,
                "note_text": data['description'],
                "overtime_date": date_obj.strftime("%Y-%m-%d"),
                "overtime_start": data['start_time'],
                "overtime_end": data['end_time'],
            }
            self._service.create_overtime(create_data)
            self.panel.load_overtime_data(
                filter_department_id=self.panel.data_manager.current_filter_department_id,
                for_my=False
            )
            self._notify("Переработка успешно добавлена")
        except Exception as e:
            print(f"❌ Ошибка создания переработки: {e}")
            self._notify(f"Ошибка создания: {str(e)}", duration=4000)

    # ==================== РЕДАКТИРОВАНИЕ (ВСЕ) ====================

    def edit_overtime_all(self, overtime_id):
        data = self.panel.data_manager.get_overtime_by_id(overtime_id)
        if not data:
            self._notify("Запись не найдена")
            return

        dialog = OvertimeDialog(
            self._parent,
            readonly=False,
            overtime_service=self._service,
            current_employee_id=self.panel.current_employee_id or 1
        )
        dialog.set_data(data)

        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.result_data is None:
            return

        new_data = dialog.result_data
        if not self._service:
            return

        try:
            date_obj = datetime.strptime(new_data['date'], "%d.%m.%Y")
            update_data = {
                "note_text": new_data['description'],
                "overtime_date": date_obj.strftime("%Y-%m-%d"),
                "overtime_start": new_data['start_time'],
                "overtime_end": new_data['end_time'],
            }
            self._service.update_overtime(overtime_id, update_data)
            self.panel.load_overtime_data(
                filter_department_id=self.panel.data_manager.current_filter_department_id,
                for_my=False
            )
            self._notify("Переработка обновлена")
        except Exception as e:
            print(f"❌ Ошибка обновления переработки: {e}")
            self._notify(f"Ошибка обновления: {str(e)}", duration=4000)

    # ==================== РЕДАКТИРОВАНИЕ (МОИ, ТОЛЬКО ОПИСАНИЕ) ====================

    def edit_overtime_my(self, overtime_id):
        data = self.panel.data_manager.get_overtime_by_id(overtime_id)
        if not data:
            self._notify("Запись не найдена")
            return

        dialog = OvertimeDialog(self._parent, readonly=True)
        dialog.set_data(data)

        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.result_data is None:
            return

        new_note = dialog.result_data.get('description', '')
        if new_note == data.get('description', '') or not self._service:
            return

        try:
            self._service.update_overtime_note(overtime_id, new_note)
            self.panel.load_overtime_data(filter_department_id=None, for_my=True)
            self._notify("Описание обновлено")
        except Exception as e:
            print(f"❌ Ошибка обновления заметки: {e}")
            self._notify(f"Ошибка обновления: {str(e)}", duration=4000)

    # ==================== УДАЛЕНИЕ ====================

    def delete_overtime(self, overtime_id):
        if self._service:
            try:
                self._service.delete_overtime(overtime_id)
            except Exception as e:
                print(f"❌ Ошибка удаления переработки: {e}")
                self._notify(f"Ошибка удаления: {str(e)}", duration=4000)
                return

        self._notify(f"Запись #{overtime_id} удалена")
        self.panel.load_overtime_data(
            filter_department_id=self.panel.data_manager.current_filter_department_id,
            for_my=False
        )