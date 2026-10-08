# client/windows/system/system_actions.py
"""Действия вкладок «Сотрудники» и «Структура» — диалоги и вызовы сервисов в одном месте.

Страницы только показывают данные и вызывают методы этого класса, а результат получают
сигналами: employees_changed / structure_changed (перезагрузить данные) и message
(показать уведомление).

Методы сервисов, которые вызываются здесь (если какого-то нет в сервисе — страница покажет
уведомление «пока не подключено», а не упадёт):
  OrgService:      get_all_organizations(), get_org_structure(org_id), get_org_employees(org_id),
                   get_department_types() [необязательный — иначе типы по умолчанию из диалога],
                   create_department(data), update_department(dep_id, data), delete_department(dep_id),
                   create_department_type(data), create_organization(data)
  EmployeeService: delete_employee(employee_id)
Создание и правка сотрудника идут через EmployeeDialog (он сам ходит в API).
"""

import logging
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QWidget

from client.core.http_client import HttpClient
from client.services.employee_service import EmployeeService
from client.services.org_service import get_org_service
from client.windows.system.system_utils import flatten_departments, to_tree

logger = logging.getLogger(__name__)


class SystemActions(QObject):
    employees_changed = pyqtSignal()
    structure_changed = pyqtSignal()  # отделы / типы отделов / организации
    message = pyqtSignal(str, str)  # ("success" | "error" | "info", текст)

    def __init__(self, parent_widget: QWidget, http_client: HttpClient):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.http_client = http_client
        self.org_service = get_org_service(http_client)
        self.employee_service = EmployeeService(http_client)

    # ==================== ВСПОМОГАТЕЛЬНОЕ ====================

    def _service_call(self, service: Any, method_name: str, *args, what: str) -> tuple[bool, Any]:
        """Вызывает метод сервиса. Возвращает (успех, результат); ошибку показывает уведомлением."""
        method = getattr(service, method_name, None)
        if method is None:
            self.message.emit("error", f"{what}: пока не подключено ({type(service).__name__}.{method_name} отсутствует)")
            return False, None
        try:
            return True, method(*args)
        except Exception as e:
            logger.exception(f"{what}: {e}")
            self.message.emit("error", f"{what}: не удалось выполнить ({e})")
            return False, None

    def _confirm_delete(self, text: str) -> bool:
        box = QMessageBox(self.parent_widget)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Удаление")
        box.setText(text)
        delete_btn = box.addButton("Удалить", QMessageBox.ButtonRole.AcceptRole)
        cancel_btn = box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancel_btn)
        box.exec()
        return box.clickedButton() is delete_btn

    # ==================== СОТРУДНИКИ ====================

    def add_employee(self):
        self._open_employee_dialog(None)

    def edit_employee(self, emp: dict[str, Any]):
        # в диалог уходят исходные данные с сервера, а не нормализованные для таблицы
        self._open_employee_dialog(emp.get("_raw") or emp)

    def _open_employee_dialog(self, employee: dict[str, Any] | None):
        from client.windows.system.employees.employee_dialog import EmployeeDialog

        try:
            # вкладка «Система» доступна администратору — права передаём явно
            dialog = EmployeeDialog(
                parent_editor=self.parent_widget,
                employee=employee,
                http_client=self.http_client,
                current_user_rights="admin",
            )
        except Exception as e:
            logger.exception(f"Не удалось открыть окно сотрудника: {e}")
            self.message.emit("error", "Не удалось открыть окно сотрудника")
            return
        dialog.employee_created.connect(lambda _id: self._employee_saved("Сотрудник добавлен"))
        dialog.employee_updated.connect(lambda _id: self._employee_saved("Сотрудник сохранён"))
        dialog.exec()

    def _employee_saved(self, text: str):
        self.message.emit("success", text)
        self.employees_changed.emit()

    def delete_employee(self, emp: dict[str, Any]):
        name = emp.get("full_name") or "сотрудника"
        if not self._confirm_delete(f"Удалить сотрудника «{name}»?"):
            return
        ok, _ = self._service_call(self.employee_service, "delete_employee", emp.get("id"), what="Удаление сотрудника")
        if ok:
            self.message.emit("success", "Сотрудник удалён")
            self.employees_changed.emit()

    # ==================== ОТДЕЛЫ ====================

    def add_department(self, organization_id: int | None = None, parent_id: int | None = None):
        data: dict[str, Any] = {}
        if organization_id is not None:
            data["organization_id"] = organization_id
        if parent_id is not None:
            data["parent_id"] = parent_id
        self._open_department_dialog(data)

    def edit_department(self, data: dict[str, Any]):
        """data — отдел с сервера + organization_id и parent_id (см. StructurePage)."""
        self._open_department_dialog(data)

    def _org_lookups(self, org_id: int | None, exclude_id: int | None = None) -> tuple[list, list]:
        """Отделы (для выбора родителя, путём «НТЦ / Телематика») и сотрудники (для руководителя) организации."""
        if org_id is None:
            return [], []
        try:
            tree = to_tree(self.org_service.get_org_structure(org_id))
            employees = self.org_service.get_org_employees(org_id)
            return flatten_departments(tree, exclude_id), employees or []
        except Exception as e:
            logger.exception(f"Не удалось загрузить отделы/сотрудников организации {org_id}: {e}")
            self.message.emit("error", "Не удалось загрузить отделы и сотрудников организации")
            return [], []

    def _open_department_dialog(self, data: dict[str, Any]):
        from client.windows.system.departments.department_dialog import DepartmentDialog

        ok, organizations = self._service_call(self.org_service, "get_all_organizations", what="Загрузка организаций")
        if not ok:
            return

        department_types = None  # None → типы по умолчанию из диалога
        if hasattr(self.org_service, "get_department_types"):
            try:
                department_types = self.org_service.get_department_types()
            except Exception as e:
                logger.exception(f"Не удалось загрузить типы отделов: {e}")

        exclude_id = data.get("id")
        departments, employees = self._org_lookups(data.get("organization_id"), exclude_id)

        dialog = DepartmentDialog(
            self.parent_widget,
            department_data=data or None,
            organizations=organizations,
            departments=departments,
            employees=employees,
            department_types=department_types,
        )
        # при смене организации в диалоге подгружаем её отделы и сотрудников
        dialog.organization_changed.connect(lambda org_id, ex=exclude_id: self._on_dialog_org_changed(dialog, org_id, ex))

        if dialog.exec():
            self._save_department(dialog.get_data(), dialog.is_edit_mode)

    def _on_dialog_org_changed(self, dialog, org_id: int | None, exclude_id: int | None):
        departments, employees = self._org_lookups(org_id, exclude_id)
        dialog.set_parent_departments(departments)
        dialog.set_head_employees(employees)

    def _save_department(self, data: dict[str, Any], is_edit: bool):
        payload = {k: v for k, v in data.items() if k != "id"}
        if is_edit:
            ok, _ = self._service_call(
                self.org_service, "update_department", data["id"], payload, what="Сохранение отдела"
            )
            text = "Отдел сохранён"
        else:
            ok, _ = self._service_call(self.org_service, "create_department", payload, what="Добавление отдела")
            text = "Отдел добавлен"
        if ok:
            self.message.emit("success", text)
            self.structure_changed.emit()

    def delete_department(self, dep_id: int, name: str = ""):
        if not self._confirm_delete(f"Удалить отдел «{name}»?" if name else "Удалить отдел?"):
            return
        ok, _ = self._service_call(self.org_service, "delete_department", dep_id, what="Удаление отдела")
        if ok:
            self.message.emit("success", "Отдел удалён")
            self.structure_changed.emit()

    # ==================== ТИП ОТДЕЛА / ОРГАНИЗАЦИЯ ====================

    def add_department_type(self):
        from client.windows.system.departments.department_type_dialog import DepartmentTypeDialog

        dialog = DepartmentTypeDialog(self.parent_widget)
        if not dialog.exec():
            return
        ok, _ = self._service_call(
            self.org_service, "create_department_type", dialog.get_data(), what="Добавление типа отдела"
        )
        if ok:
            self.message.emit("success", "Тип отдела добавлен")
            self.structure_changed.emit()

    def add_organization(self):
        from client.windows.system.organizations.organization_dialog import OrganizationDialog

        dialog = OrganizationDialog(self.parent_widget)
        if not dialog.exec():
            return
        ok, _ = self._service_call(
            self.org_service, "create_organization", dialog.get_data(), what="Добавление организации"
        )
        if ok:
            self.message.emit("success", "Организация добавлена")
            self.structure_changed.emit()
