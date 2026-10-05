# client/windows/documents/table/create/quick_add.py
"""
Быстрое добавление недостающих объектов прямо из диалога документа.

Кнопки «+» у отправителя, получателей и исполнителей открывают меню
«Сотрудник / Организация / Отдел» и нужный диалог создания (те же, что в разделе
«Система»); кнопка «+» у тегов открывает диалог тега. Созданный объект сразу
подставляется в соответствующее поле документа.

Какие пункты доступны для какой роли, задаёт ROLE_RULES: то, что сервер не сохранит для
этой роли (см. DocumentService._build_create_payload), в меню неактивно с подсказкой.
Чтобы разрешить пункт, замените причину на None.
"""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox

logger = logging.getLogger(__name__)

EMPLOYEE, ORGANIZATION, DEPARTMENT = "employee", "organization", "department"

MENU_ITEMS = (
    (EMPLOYEE, "Сотрудник"),
    (ORGANIZATION, "Организация"),
    (DEPARTMENT, "Отдел"),
)

# None — пункт доступен; строка — причина, почему он неактивен
ROLE_RULES = {
    "sender": {
        EMPLOYEE: None,
        ORGANIZATION: "Отправитель документа — сотрудник",
        DEPARTMENT: "Отправитель документа — сотрудник",
    },
    "receiver": {
        EMPLOYEE: "Получатель — отдел или организация: сотрудник как получатель на сервере не хранится",
        ORGANIZATION: None,
        DEPARTMENT: None,
    },
    "executor": {
        EMPLOYEE: None,
        ORGANIZATION: "Исполнитель документа — сотрудник",
        DEPARTMENT: "Исполнитель документа — сотрудник",
    },
}


class QuickAddController:
    """Привязан к одному DocumentDialog и работает с его полями."""

    def __init__(self, dialog):
        self.dlg = dialog

    # ───────────────────────── меню ─────────────────────────

    def show_menu(self, button, role: str):
        from client.core.themes import get_menu_style

        menu = QMenu(button)
        menu.setStyleSheet(get_menu_style())
        menu.setToolTipsVisible(True)

        rules = ROLE_RULES[role]
        for kind, title in MENU_ITEMS:
            action = QAction(title, menu)
            reason = rules.get(kind)
            if reason:
                action.setEnabled(False)
                action.setToolTip(reason)
            else:
                action.triggered.connect(lambda checked=False, k=kind: self._create(role, k))
            menu.addAction(action)

        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def _create(self, role: str, kind: str):
        d = self.dlg
        if not d.http_client:
            QMessageBox.warning(d, "Внимание", "Нет подключения к серверу")
            return

        creators = {
            EMPLOYEE: self._create_employee,
            ORGANIZATION: self._create_organization,
            DEPARTMENT: self._create_department,
        }
        try:
            new_id = creators[kind]()
        except Exception as e:  # noqa: BLE001
            logger.exception(f"Быстрое добавление ({kind}) не удалось: {e}")
            QMessageBox.critical(d, "Ошибка", f"Не удалось создать:\n{e}")
            return

        if new_id is None:  # отмена диалога или ошибка (сообщение уже показано)
            return

        self._reload_directories()
        self._select(role, new_id)

    # ───────────────────── создание объектов ─────────────────────

    def _create_employee(self):
        from client.windows.system.employees.employee_dialog import EmployeeDialog

        d = self.dlg
        user = d.current_user or {}
        created: list[int] = []

        dialog = EmployeeDialog(
            parent_editor=d,
            employee=None,
            is_maz=False,
            http_client=d.http_client,
            current_user_rights=user.get("rights") or user.get("role") or "user",
            current_user_org_id=user.get("organization_id"),
            current_user_div_id=None,
            current_user_dept_id=user.get("department_id"),
            is_organization_head=False,
            is_division_head=False,
            is_department_head=False,
            filter_external_only=False,
            organization_head_ids=None,
        )
        dialog.employee_created.connect(created.append)  # диалог сам отправляет данные на сервер
        dialog.exec()
        return created[-1] if created else None

    def _create_organization(self):
        from client.services.org_service import OrgService
        from client.windows.system.organizations.organization_dialog import OrganizationDialog

        d = self.dlg
        dialog = OrganizationDialog(d, item={})
        if not dialog.exec():
            return None

        result = OrgService(d.http_client).create_organization(dialog.get_data())
        if not result:
            QMessageBox.warning(
                d,
                "Организация",
                "Не удалось создать организацию.\nВозможные причины: нет прав администратора или УНП уже есть в системе.",
            )
            return None
        return result.get("id")

    def _create_department(self):
        from client.services.department_service import DepartmentService
        from client.windows.system.departments.department_dialog import DepartmentDialog

        d = self.dlg
        service = DepartmentService(d.http_client)

        types = None
        try:
            if hasattr(service, "get_department_types"):
                types = service.get_department_types()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Типы отделов не загрузились: {e}")

        dialog = DepartmentDialog(
            d,
            organizations=d.organizations,
            departments=d.departments,
            employees=[],  # у нового отдела ещё нет сотрудников
            department_types=types or DepartmentDialog.FALLBACK_TYPES,
        )
        if not dialog.exec():
            return None
        data = dialog.get_data()
        if not data:
            return None

        result = service.create_department(data)  # при ошибке/403 HttpClient бросит исключение — покажем текст
        return result.get("id") if isinstance(result, dict) else None

    # ─────────────────────────── теги ───────────────────────────

    def create_tag(self):
        from client.services.tag_service import get_tag_service
        from client.windows.system.tags.tag_dialog import TagDialog

        d = self.dlg
        if not d.http_client:
            QMessageBox.warning(d, "Внимание", "Нет подключения к серверу")
            return

        dialog = TagDialog(d)
        if not dialog.exec():
            return

        data = dialog.get_tag_data()
        data.pop("id", None)
        result = get_tag_service(d.http_client).create_tag(data)
        if not result:
            QMessageBox.warning(d, "Хэштег", "Не удалось создать хэштег.")
            return

        tag = {
            "id": result.get("id"),
            "name": result.get("name", data.get("name", "")),
            "color": result.get("color", data.get("color", "#ccab6e")),
            "priority": result.get("priority", data.get("priority", "normal")),
        }
        d.available_tags.append(tag)  # появится и в окне выбора тегов
        d.selected_tags = [*d.selected_tags, tag]  # и сразу выбран в документе
        d._update_tag_button_text()

    # ───────────────────── обновление и выбор ─────────────────────

    def _reload_directories(self):
        """Справочники в диалоге и общий кэш загрузчика (его используют окна выбора)."""
        from client.core.org_structure.employee_selection_data_loader import EmployeeSelectionDataLoader

        d = self.dlg
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            EmployeeSelectionDataLoader.clear_cache()
            loader = EmployeeSelectionDataLoader(d.http_client)
            d.organizations = loader.load_organizations()
            d.departments = loader.load_departments_flat()
            d.employees = loader.load_employees()
        except Exception as e:  # noqa: BLE001
            logger.exception(f"Не удалось обновить справочники: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def _select(self, role: str, new_id: int):
        """Подставляет созданный объект в поле документа."""
        d = self.dlg
        if role == "sender":
            emp = next((e for e in d.employees if e.get("id") == new_id), None)
            d.selected_sender = emp if emp else {"id": new_id}
            d._update_sender_button_text()
        elif role == "receiver":
            if new_id not in d.selected_receivers:
                d.selected_receivers = [*d.selected_receivers, new_id]
            d._update_receiver_button_text()
        elif role == "executor":
            if new_id not in d.selected_executors:
                d.selected_executors = [*d.selected_executors, new_id]
            d._update_executor_button_text()
