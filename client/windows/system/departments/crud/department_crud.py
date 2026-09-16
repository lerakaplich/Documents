# client/windows/system/departments/crud/department_crud.py
from PyQt6.QtWidgets import QMessageBox

from client.windows.system.departments.department_dialog import DepartmentDialog


class DepartmentCrud:
    """Создание / редактирование / удаление отделов."""

    def __init__(self, page, service, organizations_provider, items_provider, employees_provider):
        self.page = page
        self.service = service
        self.get_orgs = organizations_provider
        self.get_items = items_provider
        self.get_employees = employees_provider    # оставлен для совместимости

    # ─── публичные ───

    def add(self):
        dialog = DepartmentDialog(
            self.page,
            organizations=self.get_orgs(),
            departments=self.get_items(),
            employees=[],                                    # у нового отдела ещё нет сотрудников
            department_types=self._load_types(),
        )
        if dialog.exec():
            data = dialog.get_data()
            if data:
                self._create(data)

    def edit(self, data: dict):
        dept_id = data.get('id')
        if not dept_id:
            self.page.show_error_notification("ID отдела не найден")
            return
        try:
            server_dept = self.service.get_department(dept_id) or data

            # ⚠️ Грузим сотрудников ИМЕННО ЭТОГО отдела
            staff = self.service.get_department_staff(dept_id)

            dialog = DepartmentDialog(
                self.page,
                department_data=server_dept,
                organizations=self.get_orgs(),
                departments=self.get_items(),
                employees=staff,                             # ← реальные сотрудники отдела
                department_types=self._load_types(),
            )
            if dialog.exec():
                self._update(dept_id, dialog.get_data())
        except Exception as e:
            print(f"Ошибка редактирования: {e}")
            self.page.show_error_notification("Не удалось загрузить данные отдела")

    def delete(self, dept_id: int):
        name = "Неизвестный отдел"
        for it in self.get_items():
            if it.get('id') == dept_id:
                name = it.get('name', name)
                break
        reply = QMessageBox.question(
            self.page, "Подтверждение удаления",
            f"Удалить отдел «{name}»?\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._delete(dept_id, name)

    # ─── приватные ───

    def _load_types(self):
        """Пытаемся взять реальные типы с сервера, иначе — fallback."""
        try:
            if hasattr(self.service, 'get_department_types'):
                types = self.service.get_department_types()
                if types:
                    return types
        except Exception as e:
            print(f"[WARN] _load_types: {e}")
        return DepartmentDialog.FALLBACK_TYPES

    def _create(self, data):
        try:
            res = self.service.create_department(data)
            new_id = res.get('id') if res else 0
            if res:
                self.page.show_success_notification(f"Отдел «{res.get('name')}» создан")
                self.page.load_data()
            else:
                self.page.show_error_notification("Не удалось создать отдел")
            self.page.data_events.departments_changed.emit(new_id)
        except Exception as e:
            print(f"Ошибка создания: {e}")
            self.page.show_error_notification("Не удалось создать отдел")

    def _update(self, dept_id, data):
        try:
            res = self.service.update_department(dept_id, data)
            if res:
                self.page.show_success_notification(f"Отдел «{res.get('name')}» обновлен")
                self.page.load_data()
            else:
                self.page.show_error_notification("Не удалось обновить отдел")
            self.page.data_events.departments_changed.emit(dept_id)
        except Exception as e:
            print(f"Ошибка обновления: {e}")
            self.page.show_error_notification("Не удалось обновить отдел")

    def _delete(self, dept_id, name):
        try:
            ok = self.service.delete_department(dept_id)
            if ok:
                self.page.show_success_notification(f"Отдел «{name}» удален")
                self.page.load_data()
            else:
                self.page.show_error_notification("Не удалось удалить отдел")
            self.page.data_events.departments_changed.emit(dept_id)
        except Exception as e:
            print(f"Ошибка удаления: {e}")
            self.page.show_error_notification("Не удалось удалить отдел")