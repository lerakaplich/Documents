from typing import Optional
from fastapi import HTTPException, status

from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.org_repo import OrgRepository
from server.app.schemas.org import (
    DepartmentUpdate,
    DepartmentRead,
    DepartmentCreate,
)
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.common.security_service import SecurityService


class DepartmentService:
    def __init__(
        self,
        repo: OrgRepository,
        emp_repo: EmployeesRepository,
        security: SecurityService,
    ):
        self.repo = repo
        self.emp_repo = emp_repo
        self.security = security

    async def create_department(
        self, current_user: CurrentUser, data: DepartmentCreate
    ) -> DepartmentRead:
        # 1. Проверка прав
        if data.parent_id:
            if not await self.security.can_manage_dept(current_user, data.parent_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет прав на создание подразделения в этом отделе",
                )
        else:
            if not self.security.is_admin(current_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Только администратор может создавать корневые подразделения",
                )

        # 2. Валидация родителя
        parent_path = ""
        if data.parent_id:
            parent = await self.repo.get_department_by_id(data.parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Родительское подразделение не найдено",
                )
            parent_path = parent.hierarchy_path or ""

        # 3. Создание в атомарной транзакции
        async with self.repo.db.begin_nested():
            new_dept = await self.repo.create_department(data)
            new_path = f"{parent_path}/{new_dept.id}".strip("/")
            await self.repo.update_path(new_dept.id, new_path)

        # Перезапрашиваем с джойнами для DepartmentRead (head, type)
        full_dept = await self.repo.get_department_detail(new_dept.id)
        return DepartmentRead.model_validate(full_dept)

    async def update_department(
            self, current_user: CurrentUser, dept_id: int, data: DepartmentUpdate
    ) -> DepartmentRead:
        # 1. Проверка прав
        if not await self.security.can_manage_dept(current_user, dept_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на редактирование этого подразделения",
            )

        # 2. Подготовка данных
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нет данных для обновления",
            )

        # 3. Обновление
        updated_dept = await self.repo.update_department(dept_id, update_data)
        if not updated_dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Подразделение не найдено",
            )

        full_dept = await self.repo.get_department_detail(dept_id)
        return DepartmentRead.model_validate(full_dept)

    async def set_department_head(
        self, user: CurrentUser, dept_id: int, employee_id: int
    ):
        # 1. Проверка прав
        if not await self.security.can_appoint_leader(user, dept_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на назначение руководителя в данном подразделении",
            )

        # 2. Атомарная транзакция бизнес-логики
        async with self.repo.db.begin_nested():
            pos = await self.emp_repo.get_position_by_employee_and_dept(
                employee_id, dept_id
            )
            if not pos:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Сотрудник не состоит в этом подразделении",
                )

            await self.repo.update_department_head(dept_id, employee_id)
            await self.emp_repo.update_is_leader(pos.id, True)

        return {"message": "Руководитель успешно назначен"}

    async def remove_department_head(self, user: CurrentUser, dept_id: int):
        # 1. Проверка прав
        if not await self.security.can_appoint_leader(user, dept_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на снятие руководителя в данном подразделении",
            )

        # 2. Проверка существования департамента и руководителя
        dept = await self.repo.get_department_by_id(dept_id)
        if not dept or not dept.head_employee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="В данном подразделении не назначен руководитель",
            )

        async with self.repo.db.begin_nested():
            pos = await self.emp_repo.get_position_by_employee_and_dept(
                dept.head_employee_id, dept_id
            )
            if pos:
                await self.emp_repo.update_is_leader(pos.id, False)

            await self.repo.update_department_head(dept_id, None)

        return {"message": "Руководитель успешно снят с должности"}

    async def delete_department(self, user: CurrentUser, dept_id: int):
        # 1. Проверка прав
        if not await self.security.can_appoint_leader(user, dept_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на удаление этого подразделения",
            )

        # 2. Проверка дочерних подразделений
        if await self.repo.has_children(dept_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить отдел, у которого есть дочерние подразделения",
            )

        # 3. Проверка сотрудников
        employees = await self.repo.get_employees_by_dept(dept_id)
        if employees:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить отдел, в котором числятся сотрудники",
            )

        # 4. Удаление
        await self.repo.delete_department(dept_id)
        return {"message": "Подразделение успешно удалено"}

    async def move_department(
        self, user: CurrentUser, dept_id: int, new_parent_id: Optional[int]
    ):
        if new_parent_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Подразделение должно иметь родителя",
            )

        if not await self.security.can_appoint_leader(user, dept_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на перемещение этого подразделения",
            )

        # 1. Получаем текущий путь отдела
        old_path = await self.repo.get_dept_path_by_id(dept_id)
        if not old_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Перемещаемое подразделение не найдено",
            )

        # 2. Получаем путь нового родителя
        new_parent_path = await self.repo.get_dept_path_by_id(new_parent_id)
        if new_parent_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Новое родительское подразделение не найдено",
            )

        # 3. Новый путь для текущего отдела
        new_path = f"{new_parent_path}/{dept_id}".strip("/")

        async with self.repo.db.begin_nested():
            # Обновляем сам отдел
            await self.repo.update_parent(dept_id, new_parent_id)
            await self.repo.update_path(dept_id, new_path)

            # 4. Оптимизированное обновление всех потомков
            descendants = await self.repo.get_all_descendants(dept_id)
            for d in descendants:
                if d.id == dept_id:
                    continue
                # Безопасная замена префикса пути
                new_d_path = d.hierarchy_path.replace(old_path, new_path, 1)
                await self.repo.update_path(d.id, new_d_path)

        return {"message": "Подразделение успешно перемещено"}

    async def get_department_by_id(self, dept_id: int) -> DepartmentRead:
        dept = await self.repo.get_department_detail(dept_id)
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Подразделение с ID {dept_id} не найдено",
            )
        return DepartmentRead.model_validate(dept)

    async def archive_department(self, user: CurrentUser, dept_id: int):
        # 1. Проверка прав
        if not await self.security.can_appoint_leader(user, dept_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на архивацию этого подразделения",
            )

        # 2. Проверка сотрудников
        employees = await self.repo.get_employees_by_dept(dept_id)
        if employees:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя архивировать отдел, в котором есть сотрудники",
            )

        # 3. Архивируем
        await self.repo.update_department(dept_id, {"is_active": False})
        return {"message": "Подразделение успешно архивировано"}