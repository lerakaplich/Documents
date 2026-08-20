from typing import Optional, Any

from fastapi import HTTPException, status

from server.app.database.document_models import AppRights, DocumentRole
from server.app.repositories.document_repo import DocumentRepository
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.org_repo import OrgRepository


class SecurityService:
    def __init__(
        self,
        emp_repo: EmployeesRepository,
        org_repo: OrgRepository,
        doc_repo: DocumentRepository
    ):
        self.emp_repo = emp_repo
        self.org_repo = org_repo
        self.doc_repo = doc_repo

    # 1. ГЛОБАЛЬНЫЕ СИСТЕМНЫЕ РОЛИ (AppRights)

    def is_admin(self, user: CurrentUser) -> bool:
        """Пользователь является администратором или суперадмином."""
        return user.rights in [AppRights.admin, AppRights.superadmin]

    def is_superadmin(self, user: CurrentUser) -> bool:
        """Пользователь является суперадмином."""
        return user.rights == AppRights.superadmin

    def is_at_least(self, user: CurrentUser, required_rights: list[AppRights]) -> bool:
        """Проверяет, входит ли роль пользователя в допустимый список."""
        return user.rights in required_rights

    def can_update_rights(self, manager: CurrentUser, new_rights: AppRights) -> bool:
        """Проверка: не пытается ли менеджер выдать права выше собственных."""
        if self.is_superadmin(manager):
            return True
        if new_rights in [AppRights.admin, AppRights.superadmin]:
            return self.is_admin(manager)
        return True

    # 2. ОРГАНИЗАЦИИ И ИЕРАРХИЯ ПОДРАЗДЕЛЕНИЙ

    async def can_manage_org(self, user: CurrentUser, org_id: int) -> bool:
        """Суперадмин управляет всеми, обычный админ — только своей организацией."""
        if self.is_superadmin(user):
            return True
        return self.is_admin(user) and getattr(user, "org_id", None) == org_id

    async def can_manage_path(self, user: CurrentUser, target_path: str) -> bool:
        """Проверяет, покрывается ли целевой путь одним из путей руководства юзера."""
        if self.is_admin(user):
            return True

        leader_paths = await self.emp_repo.get_leader_paths(user.id)
        return any(target_path.startswith(path) for path in leader_paths)

    async def can_manage_dept(self, user: CurrentUser, dept_id: int) -> bool:
        """Проверяет наличие доступа к департаменту по его ID."""
        path = await self.org_repo.get_dept_path_by_id(dept_id)
        if not path:
            return False
        return await self.can_manage_path(user, path)

    async def is_dept_head(self, user_id: int, dept_id: int) -> bool:
        """Является ли пользователь официальным руководителем отдельного департамента."""
        dept = await self.org_repo.get_department_by_id(dept_id)
        return bool(dept and dept.head_employee_id == user_id)

    async def is_leader_anywhere(self, user: CurrentUser) -> bool:
        """Является ли пользователь руководителем хотя бы одного подразделения."""
        leader_paths = await self.emp_repo.get_leader_paths(user.id)
        return bool(leader_paths)

    async def can_view_employee(self, user: CurrentUser, target_emp_id: int) -> bool:
        """Проверка: может ли юзер просматривать профиль сотрудника в иерархии."""
        if self.is_admin(user):
            return True

        leader_paths = await self.emp_repo.get_leader_paths(user.id)
        if not leader_paths:
            return False

        target_paths = await self.emp_repo.get_target_dept_paths(target_emp_id)
        return any(
            target_path.startswith(leader_path)
            for target_path in target_paths
            for leader_path in leader_paths
        )

    async def can_appoint_leader(self, user: CurrentUser, dept_id: int) -> bool:
        """Назначение лидера: для корня — только админ, иначе — менеджер родительского отдела."""
        if self.is_admin(user):
            return True

        dept = await self.org_repo.get_department_by_id(dept_id)
        if not dept or not dept.parent_id:
            return False

        return await self.can_manage_dept(user, dept.parent_id)

    async def can_transfer_employee(self, manager: CurrentUser, old_dept_id: int, new_dept_id: int) -> bool:
        """Перевод сотрудника требует прав управления над обоими подразделениями."""
        can_from = await self.can_manage_dept(manager, old_dept_id)
        can_to = await self.can_manage_dept(manager, new_dept_id)
        return can_from and can_to

    # 3. ДОКУМЕНТООБОРОТ (Доступ к документам)

    async def can_access_document(self, user: CurrentUser, doc_id: int) -> bool:
        """Проверка прав на просмотр/работу с документом."""
        if self.is_admin(user):
            return True

        relation = await self.doc_repo.get_user_relation(doc_id, user.id)
        allowed_roles = [DocumentRole.sender, DocumentRole.recipient, DocumentRole.delegate]
        return bool(relation and relation.role in allowed_roles)

    def can_review_document(self, relation: Optional[Any]) -> bool:
        """Является ли участник согласовантом/делегатом документа."""
        allowed_roles = [DocumentRole.recipient, DocumentRole.delegate]
        return bool(relation and relation.role in allowed_roles)

    async def can_export(self, user: CurrentUser, dept_id: Optional[int] = None) -> None:
        """
        Проверяет право на экспорт отчета по переработкам.
        - Админ / суперадмин может экспортировать всё.
        - Руководитель может экспортировать только свой отдел и вложенные в него.
        - Выгружать отчет без указания dept_id (по всей компании) обычным руководителям запрещено.
        """
        # 1. Админам и суперадминам разрешено всё
        if self.is_admin(user):
            return

        # 2. Если dept_id не передан, обычный пользователь/руководитель не может сгрузить всю базу
        if dept_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Для экспорта отчета необходимо выбрать подразделение"
            )

        # 3. Проверяем, является ли пользователь руководителем выбранного отдела (или вышестоящего)
        can_manage = await self.can_manage_dept(user, dept_id)
        if not can_manage:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет прав на экспорт отчета по данному подразделению"
            )