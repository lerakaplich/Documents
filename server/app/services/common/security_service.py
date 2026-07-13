from typing import Optional, Any

from fastapi import HTTPException
from server.app.database.document_models import AppRights, DocumentRole
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.org_repo import OrgRepository


class SecurityService:
    def __init__(self, emp_repo: EmployeesRepository, org_repo: OrgRepository):
        self.emp_repo = emp_repo
        self.org_repo = org_repo

    async def verify_is_admin(self, user: CurrentUser):
        """Проверка, является ли пользователь администратором или суперадмином."""
        if user.rights not in [AppRights.admin, AppRights.superadmin]:
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав: требуется роль администратора"
            )
        return True

    async def verify_is_superadmin(self, user: CurrentUser):
        """Строгая проверка только на суперадмина."""
        if user.rights != AppRights.superadmin:
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав: требуется роль суперадмина"
            )
        return True

    async def verify_is_at_least(self, user: CurrentUser, required_rights: list[AppRights]):
        """Гибкая проверка: является ли пользователь хотя бы одним из списка."""
        if user.rights not in required_rights:
            raise HTTPException(
                status_code=403,
                detail=f"Недостаточно прав. Требуется одна из ролей: {', '.join(required_rights)}"
            )
        return True

    async def verify_document_access(self, user: CurrentUser, doc_id: int, repo: Any) -> bool:
        """
        Универсальная проверка доступа к документу:
        Пропускает, если пользователь Admin/Superadmin ИЛИ является участником (sender, recipient и др.).
        """
        # 1. Админы и суперадмины имеют полный доступ ко всем документам
        if user.rights in [AppRights.admin, AppRights.superadmin]:
            return True

        # 2. Проверяем связь пользователя с документом через репозиторий
        # Метод get_user_relation должен быть реализован в вашем репозитории
        relation = await repo.get_user_relation(doc_id, user.id)
        if relation and relation.role in [DocumentRole.sender, DocumentRole.recipient, DocumentRole.delegate]:
            return True

        raise HTTPException(
            status_code=403,
            detail="Доступ запрещен: вы не являетесь участником этого документа и не имеете прав администратора."
        )

    async def verify_management_rights(self, current_user: CurrentUser, target_path: str):
        """Проверка: может ли юзер управлять объектом по пути target_path."""
        if current_user.rights in [AppRights.admin, AppRights.superadmin]:
            return True

        leader_paths = await self.emp_repo.get_leader_paths(current_user.id)

        # Если хотя бы один путь руководителя является префиксом целевого пути
        if not any(target_path.startswith(path) for path in leader_paths):
            raise HTTPException(status_code=403, detail="Недостаточно прав в иерархии")
        return True

    async def verify_can_review_document(self, relation: Optional[Any]):
        if not relation or relation.role not in [DocumentRole.recipient, DocumentRole.delegate]:
            raise HTTPException(
                status_code=403,
                detail="Вы не являетесь согласующим лицом для данного документа."
            )
        return True

    async def verify_org_access(self, user: CurrentUser, org_id: int):
        # 1. Если это суперадмин — пускаем везде
        if user.rights == AppRights.superadmin:
            return True

        # 2. Если это админ организации, проверяем, что это ЕГО организация
        if user.rights == AppRights.admin and user.org_id == org_id:
            return True

        raise HTTPException(status_code=403, detail="Нет прав на управление этой организацией")

    async def verify_dept_access(self, user: CurrentUser, dept_id: int):
        """Удобная обертка для проверки прав на департамент"""
        path = await self.org_repo.get_dept_path_by_id(dept_id)
        if not path:
            raise HTTPException(status_code=404, detail="Департамент не найден")
        return await self.verify_management_rights(user, path)

    async def verify_head_authority(self, user_id: int, dept_id: int):
        """
        Проверка: является ли пользователь ОФИЦИАЛЬНЫМ Head этого отдела?
        Используем только head_employee_id из таблицы departments.
        """
        dept = await self.org_repo.get_department_by_id(dept_id)
        if not dept or dept.head_employee_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Действие доступно только официальному руководителю подразделения"
            )
        return True

    async def verify_employee_view_access(self, user: CurrentUser, target_emp_id: int):
        """Проверка: может ли юзер просматривать сотрудника."""
        # 1. Админы — везде
        if user.rights in [AppRights.admin, AppRights.superadmin]:
            return True

        # 2. Получаем пути, где юзер — руководитель
        leader_paths = await self.emp_repo.get_leader_paths(user.id)
        # 3. Получаем пути, где работает целевой сотрудник
        target_paths = await self.emp_repo.get_target_dept_paths(target_emp_id)

        # 4. Проверка: пересекаются ли они через префикс?
        # Если хотя бы один целевой путь начинается с пути руководителя — пускаем
        if not any(target_path.startswith(leader_path)
                   for target_path in target_paths
                   for leader_path in leader_paths):
            raise HTTPException(status_code=403, detail="Нет прав на просмотр этого сотрудника")
        return True

    async def verify_can_update_rights(self, manager: CurrentUser, new_rights: str):
        """Проверка: не пытается ли менеджер дать права, которые выше его собственных."""
        # Суперадмин может всё
        if manager.rights == AppRights.superadmin:
            return True

        # Если пытаются присвоить права администратора или выше
        if new_rights in [AppRights.admin, AppRights.superadmin]:
            if manager.rights != AppRights.admin and manager.rights != AppRights.superadmin:
                raise HTTPException(status_code=403, detail="Вы не можете присваивать административные права")

        return True

    async def verify_dept_transfer(self, manager: CurrentUser, old_dept_id: int, new_dept_id: int):
        """Проверка права на перевод сотрудника между отделами."""
        # 1. Менеджер должен иметь права на старый отдел (чтобы уволить/перевести)
        await self.verify_dept_access(manager, old_dept_id)
        # 2. Менеджер должен иметь права на новый отдел (чтобы принять)
        await self.verify_dept_access(manager, new_dept_id)
        return True

    async def verify_can_appoint_leader(self, user: CurrentUser, dept_id: int):
        # 1. Глобальные права
        if user.rights in [AppRights.superadmin, AppRights.admin]:
            return True

        # 2. Иерархические права:
        dept = await self.org_repo.get_department_by_id(dept_id)
        if not dept or not dept.parent_id:
            # Если это корневой отдел и юзер не админ — запрещено
            raise HTTPException(status_code=403,
                                detail="Только администратор может назначать руководителя корневого подразделения")

        # Проверяем, имеет ли юзер права менеджера на РОДИТЕЛЬСКИЙ отдел
        return await self.verify_dept_access(user, dept.parent_id)

    async def verify_is_leader_at_least_once(self, user: CurrentUser):
        """
        Переиспользуем метод, который уже ищет пути руководства пользователя.
        Если список путей не пуст — значит, пользователь руководитель.
        """
        leader_paths = await self.emp_repo.get_leader_paths(user.id)
        if not leader_paths:
            raise HTTPException(
                status_code=403,
                detail="Действие доступно только руководителям подразделений"
            )
        return True