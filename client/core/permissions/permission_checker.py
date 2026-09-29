from enum import Enum
from typing import Any


class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class PermissionChecker:
    """Проверка прав доступа на клиенте"""

    def __init__(self, current_user: dict[str, Any]):
        self.user = current_user
        self.role = UserRole(current_user.get("rights", "user"))
        self.is_organization_head = current_user.get("is_organization_head", False)
        self.is_division_head = current_user.get("is_division_head", False)
        self.is_department_head = current_user.get("is_department_head", False)
        self.org_id = current_user.get("organization_id")
        self.division_id = current_user.get("division_id")
        self.department_id = current_user.get("department_id")

    def can_view_personal_phone(self, target_user: dict | None = None) -> bool:
        """Может ли видеть личный номер телефона"""
        if self.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            return True
        return bool(target_user and self._is_subordinate(target_user))

    def can_add_employee(self) -> bool:
        """Может ли добавлять сотрудников"""
        return self.role in [UserRole.ADMIN, UserRole.SUPERADMIN] or self.is_division_head or self.is_department_head

    def can_edit_employee(self, target_user: dict[str, Any]) -> bool:
        """Может ли редактировать сотрудника"""
        if self.role == UserRole.SUPERADMIN:
            return True

        if self.role == UserRole.ADMIN:
            return target_user.get("rights") != "superadmin"

        if self.is_department_head:
            return target_user.get("department_id") == self.department_id

        if self.is_division_head:
            return target_user.get("division_id") == self.division_id

        return False

    def can_delete_employee(self, target_user: dict[str, Any]) -> bool:
        """Может ли удалять сотрудников"""
        return self.can_edit_employee(target_user)

    def can_edit_system_tags(self) -> bool:
        """Может ли редактировать системные хэштеги"""
        return self.role == UserRole.SUPERADMIN

    def can_access_db_management(self) -> bool:
        """Может ли управлять БД"""
        return self.role == UserRole.SUPERADMIN

    def can_export_overtimes(self) -> bool:
        """Может ли экспортировать переработки"""
        return self.role in [UserRole.ADMIN, UserRole.SUPERADMIN]

    def can_view_all_overtimes(self) -> bool:
        """Может ли видеть все переработки (вкладка Все переработки)"""
        return self.role in [UserRole.ADMIN, UserRole.SUPERADMIN]

    def _is_subordinate(self, target_user: dict[str, Any]) -> bool:
        """Проверяет, является ли целевой пользователь подчиненным"""
        if self.is_department_head:
            return target_user.get("department_id") == self.department_id
        if self.is_division_head:
            return target_user.get("division_id") == self.division_id
        return False
