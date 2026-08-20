import logging

from fastapi import HTTPException, status

from server.app.repositories.overtime_repo import OvertimeRepository
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.schemas.user_schemas.overtime_dto import OvertimeCreate, OvertimeUpdate
from server.app.services.common.security_service import SecurityService

logger = logging.getLogger(__name__)

class OvertimeService:
    def __init__(self, security: SecurityService, repo: OvertimeRepository):
        self.security = security
        self.repo = repo

    async def create_by_admin(self, user: CurrentUser, data: OvertimeCreate):
        if not self.security.is_admin(user):
            logger.warning(
                "Access denied for creating overtime record",
                extra={"user_id": user.id, "target_employee_id": data.employee_id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только администратор может создавать записи о переработке",
            )

        new_record = await self.repo.add(data)
        logger.info(
            "Overtime record created by admin",
            extra={
                "admin_id": user.id,
                "employee_id": data.employee_id,
                "overtime_id": getattr(new_record, "id", None),
            },
        )
        return new_record

    async def update_note_by_employee(self, user: CurrentUser, ot_id: int, note: str):
        record = await self.repo.get_by_id(ot_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Запись о переработке не найдена",
            )

        is_admin_user = self.security.is_admin(user)
        if not is_admin_user and record.employee_id != user.id:
            logger.warning(
                "Access denied for updating overtime note",
                extra={"user_id": user.id, "overtime_id": ot_id, "owner_id": record.employee_id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав: вы можете редактировать только свои записи",
            )

        updated = await self.repo.update_note(ot_id, note)
        logger.info(
            "Overtime note updated",
            extra={"user_id": user.id, "overtime_id": ot_id},
        )
        return updated

    async def update_by_admin(
        self, user: CurrentUser, ot_id: int, data: OvertimeUpdate
    ):
        if not self.security.is_admin(user):
            logger.warning(
                "Access denied for updating overtime record",
                extra={"user_id": user.id, "overtime_id": ot_id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только администратор может обновлять данные переработок",
            )

        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нет данных для обновления",
            )

        updated_record = await self.repo.update_all(ot_id, update_dict)
        if not updated_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Запись о переработке не найдена",
            )

        logger.info(
            "Overtime record updated by admin",
            extra={"admin_id": user.id, "overtime_id": ot_id},
        )
        return updated_record

    async def get_by_employee(
        self, current_user: CurrentUser, target_employee_id: int
    ):
        is_admin_user = self.security.is_admin(current_user)
        if not is_admin_user and current_user.id != target_employee_id:
            logger.warning(
                "Access denied for viewing employee overtimes",
                extra={"user_id": current_user.id, "target_employee_id": target_employee_id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав: можно просматривать только свои записи",
            )

        return await self.repo.get_by_employee_id(target_employee_id)

    async def get_by_dept(self, user: CurrentUser, dept_id: int):
        if not await self.security.can_manage_dept(user, dept_id):
            logger.warning(
                "Access denied for department overtimes",
                extra={"user_id": user.id, "dept_id": dept_id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на просмотр переработок данного подразделения",
            )
        return await self.repo.get_by_dept_id(dept_id)

    async def get_all(self, user: CurrentUser):
        """Доступно только админам/суперадминам"""
        if not self.security.is_admin(user):
            logger.warning(
                "Access denied for getting all overtimes",
                extra={"user_id": user.id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ разрешен только администраторам",
            )
        return await self.repo.get_all()

    async def delete_by_admin(self, user: CurrentUser, ot_id: int):
        if not self.security.is_admin(user):
            logger.warning(
                "Access denied for deleting overtime record",
                extra={"user_id": user.id, "overtime_id": ot_id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только администратор может удалять записи о переработке",
            )

        deleted_id = await self.repo.delete(ot_id)
        if not deleted_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Запись о переработке не найдена",
            )

        logger.info(
            "Overtime record deleted",
            extra={"admin_id": user.id, "overtime_id": ot_id},
        )
        return True

    async def update_bulk_notes_by_employee(
        self, user: CurrentUser, overtime_ids: list[int], note: str
    ):
        if not overtime_ids:
            return {"updated_count": 0}

        records = await self.repo.get_by_ids(overtime_ids)

        found_ids = {r.id for r in records}
        missing_ids = set(overtime_ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Записи с ID {list(missing_ids)} не найдены",
            )

        is_admin_user = self.security.is_admin(user)
        if not is_admin_user:
            forbidden_ids = [r.id for r in records if r.employee_id != user.id]
            if forbidden_ids:
                logger.warning(
                    "Access denied for bulk overtime note update",
                    extra={
                        "user_id": user.id,
                        "forbidden_overtime_ids": forbidden_ids,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Недостаточно прав: вы можете редактировать только свои собственные записи",
                )

        result = await self.repo.update_bulk_notes_for_employee(
            overtime_ids=overtime_ids,
            employee_id=user.id,
            note=note,
        )
        logger.info(
            "Bulk overtime notes updated",
            extra={"user_id": user.id, "count": len(overtime_ids)},
        )
        return result