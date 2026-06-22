from fastapi import HTTPException

from server.app.repositories.overtime_repo import OvertimeRepository
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.schemas.user_schemas.overtime_dto import OvertimeCreate, OvertimeUpdate
from server.app.services.security_service import SecurityService


class OvertimeService:
    def __init__(self, security: SecurityService, repo: OvertimeRepository):
        self.security = security
        self.repo = repo

    async def create_by_admin(self, user: CurrentUser, data: OvertimeCreate):
        await self.security.verify_is_admin(user)
        return await self.repo.add(data)

    async def update_note_by_employee(self, user: CurrentUser, ot_id: int, note: str):
        record = await self.repo.get_by_id(ot_id)
        if not record:
            raise HTTPException(status_code=404, detail="Запись не найдена")

        try:
            await self.security.verify_is_admin(user)
        except HTTPException:
            if record.employee_id != user.id:
                raise HTTPException(
                    status_code=403,
                    detail="Недостаточно прав: вы можете редактировать только свои записи"
                )

        return await self.repo.update_note(ot_id, note)

    async def update_by_admin(self, user: CurrentUser, ot_id: int, data: OvertimeUpdate):
        await self.security.verify_is_admin(user)

        update_dict = data.model_dump(exclude_unset=True)

        updated_record = await self.repo.update_all(ot_id, update_dict)

        if not updated_record:
            raise HTTPException(
                status_code=404,
                detail="Запись о переработке не найдена"
            )

        return updated_record

    async def get_by_employee(self, current_user: CurrentUser, target_employee_id: int):
        try:
            await self.security.verify_is_admin(current_user)
        except HTTPException:
            if current_user.id != target_employee_id:
                raise HTTPException(
                    status_code=403,
                    detail="Недостаточно прав: можно смотреть только свои записи"
                )

        return await self.repo.get_by_employee_id(target_employee_id)

    async def get_by_dept(self, user: CurrentUser, dept_id: int):
        await self.security.verify_dept_access(user, dept_id)
        return await self.repo.get_by_dept_id(dept_id)

    async def get_all(self, user: CurrentUser):
        """Доступно только админам/суперадминам"""
        await self.security.verify_is_admin(user)
        return await self.repo.get_all()

    async def delete_by_admin(self, user: CurrentUser, ot_id: int):
        await self.security.verify_is_admin(user)

        deleted_id = await self.repo.delete(ot_id)

        if not deleted_id:
            raise HTTPException(
                status_code=404,
                detail="Запись о переработке не найдена"
            )
        return True