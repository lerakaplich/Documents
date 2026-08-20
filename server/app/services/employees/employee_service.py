import logging
from typing import Optional

from fastapi import HTTPException,status

from server.app.repositories.document_repo import DocumentRepository
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.schemas.org import DepartmentPathItem
from server.app.schemas.user_schemas.employee_dto import EmployeeRead, EmployeeListRead, CurrentUser, \
    EmployeeDetailRead, EmployeeCreate, EmployeeProfileUpdate, EmployeeFullUpdate, PositionCreate, \
    PositionUpdate, EmployeePositionRead
from server.app.services.common.security_service import SecurityService

logger = logging.getLogger(__name__)

class EmployeeService:
    def __init__(
        self,
        repo: EmployeesRepository,
        doc_repo: DocumentRepository,
        security: SecurityService
    ):
        self.emp_repo = repo
        self.doc_repo = doc_repo
        self.security = security

    async def get_staff_by_department(
        self, department_id: int, include_inactive: bool = False
    ) -> list[EmployeeRead]:
        """Получение списка сотрудников подразделения"""
        employees = await self.emp_repo.get_by_department(
            department_id, include_inactive=include_inactive
        )
        return [EmployeeRead.model_validate(e) for e in employees]

    async def get_employees_list(
        self, page: int, limit: int, show_fired: bool
    ) -> list[EmployeeListRead]:
        """Пагинированный список сотрудников со статусами прав"""
        offset = (page - 1) * limit

        employees_rows = await self.emp_repo.get_paginated_employees(
            limit, offset, show_fired
        )

        emp_ids = [r.id for r in employees_rows]
        rights_map = await self.doc_repo.get_rights_map(emp_ids)

        return [
            EmployeeListRead(
                id=r.id,
                full_name=r.full_name,
                position_name=r.position_name,
                department_name=r.department_name,
                phone_number=r.phone_number,
                rights=rights_map.get(r.id, "user"),
            )
            for r in employees_rows
        ]

    async def get_full_employee_info(
        self, current_user: CurrentUser, emp_id: int
    ) -> Optional[EmployeeDetailRead]:
        """Получение полной информации о сотруднике"""
        if not await self.security.can_view_employee(current_user, emp_id):
            logger.warning(
                f"User user_id={current_user.id} denied view access to emp_id={emp_id}",
                extra={"event_type": "employee_view_denied", "user_id": current_user.id, "target_emp_id": emp_id}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на просмотр данных этого сотрудника.",
            )

        employee = await self.emp_repo.get_by_id(emp_id)
        if not employee:
            return None

        rights_data = await self.doc_repo.get_rights_map([emp_id])
        user_rights = rights_data.get(emp_id, "user")

        emp_dict = employee.__dict__.copy()
        emp_dict["rights"] = user_rights

        return EmployeeDetailRead.model_validate(emp_dict)

    async def create_employee(
        self, current_user: CurrentUser, data: EmployeeCreate
    ):
        """Создание сотрудника с привязкой должности и системных прав"""
        if not await self.security.can_manage_dept(
            current_user, data.position.department_id
        ):
            logger.warning(
                f"User user_id={current_user.id} denied creating employee in dept_id={data.position.department_id}",
                extra={"event_type": "employee_create_denied", "user_id": current_user.id, "dept_id": data.position.department_id}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на добавление сотрудников в данное подразделение.",
            )

        try:
            new_emp = await self.emp_repo.add_employee(data)
            await self.emp_repo.add_position(
                new_emp.id,
                data.position.department_id,
                data.position.position_name,
                data.position.is_leader,
            )
            await self.doc_repo.upsert_system_employee(
                id=new_emp.id,
                last_name=data.last_name,
                first_name=data.first_name,
                patronymic=data.patronymic or "",
                rights=data.rights,
            )

            await self.emp_repo.db.commit()

            logger.info(
                f"Employee created: emp_id={new_emp.id} by user_id={current_user.id}",
                extra={
                    "event_type": "employee_created",
                    "target_emp_id": new_emp.id,
                    "created_by": current_user.id,
                    "rights": data.rights
                }
            )
            return await self.emp_repo.get_employee_with_positions(new_emp.id)
        except Exception as e:
            await self.emp_repo.db.rollback()
            logger.error(
                f"Error creating employee by user_id={current_user.id}: {str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при создании нового сотрудника."
            )

    async def update_own_profile(self, user_id: int, data: EmployeeProfileUpdate):
        """Обновление личных данных текущего пользователя"""
        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нет данных для обновления.",
            )

        try:
            await self.emp_repo.update_employee_profile(user_id, update_dict)
            await self.emp_repo.db.commit()

            logger.info(
                f"User user_id={user_id} updated own profile",
                extra={"event_type": "own_profile_updated", "user_id": user_id}
            )
            return await self.emp_repo.get_by_id(user_id)
        except Exception as e:
            await self.emp_repo.db.rollback()
            logger.error(f"Error updating profile for user_id={user_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении профиля."
            )

    async def update_employee_by_manager(
        self,
        manager_user: CurrentUser,
        target_id: int,
        data: EmployeeFullUpdate,
    ):
        """Комплексное обновление данных сотрудника руководителем/администратором"""
        if not await self.security.can_view_employee(manager_user, target_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на редактирование этого сотрудника.",
            )

        if data.rights is not None:
            if not self.security.can_update_rights(manager_user, data.rights):
                logger.warning(
                    f"Privilege escalation attempt by user_id={manager_user.id} setting rights '{data.rights}' for emp_id={target_id}",
                    extra={"event_type": "privilege_escalation_attempt", "user_id": manager_user.id, "target_id": target_id}
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Недостаточно прав для назначения указанного уровня доступа.",
                )

        current_emp = await self.emp_repo.get_by_id(target_id)
        current_sys = await self.doc_repo.get_system_employee_by_id(target_id)
        if not current_emp or not current_sys:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сотрудник не найден.",
            )

        if data.positions is not None:
            current_positions = await self.emp_repo.get_positions_by_employee(target_id)
            current_dept_ids = {p.department_id for p in current_positions}

            for pos in data.positions:
                if pos.department_id not in current_dept_ids:
                    if not await self.security.can_manage_dept(manager_user, pos.department_id):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Нет прав на перевод сотрудника в подразделение ID {pos.department_id}.",
                        )

        try:
            update_data = data.model_dump(
                exclude={"positions", "rights", "last_name", "first_name", "patronymic"},
                exclude_unset=True,
            )
            if update_data:
                await self.emp_repo.update_employee_profile(target_id, update_data)

            if data.positions is not None:
                await self.sync_employee_positions(target_id, data.positions)

            new_rights = data.rights if data.rights is not None else current_sys.rights

            await self.doc_repo.upsert_system_employee(
                id=target_id,
                last_name=data.last_name or current_emp.last_name,
                first_name=data.first_name or current_emp.first_name,
                patronymic=data.patronymic if data.patronymic is not None else current_emp.patronymic,
                rights=new_rights,
            )

            await self.emp_repo.db.commit()

            logger.info(
                f"Employee emp_id={target_id} updated by manager_id={manager_user.id}",
                extra={
                    "event_type": "employee_updated_by_manager",
                    "target_emp_id": target_id,
                    "updated_by": manager_user.id,
                    "new_rights": new_rights
                }
            )

            updated_emp = await self.emp_repo.get_employee_with_positions(target_id)
            result = updated_emp.__dict__.copy()
            result["rights"] = new_rights
            return EmployeeDetailRead.model_validate(result)

        except HTTPException:
            await self.emp_repo.db.rollback()
            raise
        except Exception as e:
            await self.emp_repo.db.rollback()
            logger.error(
                f"Error updating employee emp_id={target_id} by manager_id={manager_user.id}: {str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении профиля сотрудника."
            )

    async def sync_employee_positions(
        self, employee_id: int, new_positions: list[PositionUpdate]
    ) -> None:
        """Синхронизация должностей сотрудника без принудительного commit"""
        current_positions = await self.emp_repo.get_positions_by_employee(employee_id)
        current_map = {p.id: p for p in current_positions}
        new_ids = {p.id for p in new_positions if p.id is not None}

        for p_id in current_map:
            if p_id not in new_ids:
                await self.emp_repo.delete_position(p_id)

        for pos_data in new_positions:
            if pos_data.id and pos_data.id in current_map:
                await self.emp_repo.update_position(pos_data)
            else:
                await self.emp_repo.add_position(
                    employee_id,
                    pos_data.department_id,
                    pos_data.position_name,
                    pos_data.is_leader,
                )

    async def add_employee_position(
        self, current_user: CurrentUser, emp_id: int, data: PositionCreate
    ):
        """Добавление отдельной должности сотруднику"""
        if not await self.security.can_manage_dept(current_user, data.department_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на добавление должности в данном подразделении.",
            )

        try:
            position = await self.emp_repo.add_position(
                employee_id=emp_id,
                dept_id=data.department_id,
                name=data.position_name,
                is_leader=data.is_leader,
            )
            await self.emp_repo.db.commit()

            logger.info(
                f"Position added for emp_id={emp_id} in dept_id={data.department_id} by user_id={current_user.id}",
                extra={
                    "event_type": "employee_position_added",
                    "target_emp_id": emp_id,
                    "dept_id": data.department_id,
                    "user_id": current_user.id
                }
            )
            return position
        except Exception as e:
            await self.emp_repo.db.rollback()
            logger.error(f"Error adding position for emp_id={emp_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при добавлении должности."
            )

    async def remove_employee_position(
        self, current_user: CurrentUser, emp_id: int, pos_id: int
    ):
        """Удаление должности сотрудника"""
        positions = await self.emp_repo.get_positions_by_employee(emp_id)
        if len(positions) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить единственную должность сотрудника.",
            )

        pos_to_delete = next((p for p in positions if p.id == pos_id), None)
        if not pos_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Должность не найдена.",
            )

        if not await self.security.can_manage_dept(current_user, pos_to_delete.department_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на удаление должности в этом подразделении.",
            )

        try:
            result = await self.emp_repo.delete_position(pos_id)
            await self.emp_repo.db.commit()

            logger.info(
                f"Position pos_id={pos_id} removed for emp_id={emp_id} by user_id={current_user.id}",
                extra={
                    "event_type": "employee_position_removed",
                    "target_emp_id": emp_id,
                    "pos_id": pos_id,
                    "user_id": current_user.id
                }
            )
            return result
        except Exception as e:
            await self.emp_repo.db.rollback()
            logger.error(f"Error removing pos_id={pos_id} for emp_id={emp_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при удалении должности."
            )

    async def set_access_leadership(
        self, user: CurrentUser, pos_id: int, is_leader: bool
    ):
        """Назначение или снятие статуса руководителя должности"""
        pos = await self.emp_repo.get_position_by_id(pos_id)
        if not pos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Должность не найдена.",
            )

        if not await self.security.can_manage_dept(user, pos.department_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на изменение статуса руководителя в этом подразделении.",
            )

        try:
            updated_pos = await self.emp_repo.update_is_leader(pos_id, is_leader)
            await self.emp_repo.db.commit()

            logger.info(
                f"Leadership status for pos_id={pos_id} set to {is_leader} by user_id={user.id}",
                extra={
                    "event_type": "leadership_status_changed",
                    "pos_id": pos_id,
                    "is_leader": is_leader,
                    "changed_by": user.id
                }
            )
            return updated_pos
        except Exception as e:
            await self.emp_repo.db.rollback()
            logger.error(f"Error setting leadership status for pos_id={pos_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при изменении статуса руководителя."
            )

    @staticmethod
    def _parse_hierarchy_path(path: Optional[str]) -> list[int]:
        """Вспомогательный метод парсинга пути вида '1/5/3'"""
        if not path:
            return []
        return [int(x) for x in path.split("/") if x.strip().isdigit()]

    async def get_my_profile(self, current_user: CurrentUser) -> Optional[EmployeeDetailRead]:
        """Получение и сборка полного профиля текущего сотрудника со всеми цепочками отделов и правами"""
        employee = await self.emp_repo.get_by_id_with_departments(current_user.id)
        if not employee:
            return None

        needed_dept_ids: set[int] = set()
        for pos in employee.positions:
            if pos.department and pos.department.hierarchy_path:
                needed_dept_ids.update(self._parse_hierarchy_path(pos.department.hierarchy_path))

        depts_map = await self.emp_repo.get_departments_by_ids(needed_dept_ids)

        positions_dto: list[EmployeePositionRead] = []

        for pos in employee.positions:
            pos_chain: list[DepartmentPathItem] = []
            pos_path_names: list[str] = []

            if pos.department and pos.department.hierarchy_path:
                chain_ids = self._parse_hierarchy_path(pos.department.hierarchy_path)

                for d_id in chain_ids:
                    dept_obj = depts_map.get(d_id)
                    if dept_obj:
                        type_name = dept_obj.department_type.name if dept_obj.department_type else None

                        pos_chain.append(
                            DepartmentPathItem(
                                id=dept_obj.id,
                                name=dept_obj.name,
                                number=dept_obj.number,
                                department_type_name=type_name,
                            )
                        )
                        pos_path_names.append(dept_obj.name)

            pos_dto = EmployeePositionRead(
                id=pos.id,
                department_id=pos.department_id,
                position_name=pos.position_name,
                is_leader=pos.is_leader,
                department_chain=pos_chain
            )
            positions_dto.append(pos_dto)

        rights_data = await self.doc_repo.get_rights_map([current_user.id])
        user_rights = rights_data.get(current_user.id, "user")

        return EmployeeDetailRead(
            id=employee.id,
            service_number=employee.service_number,
            last_name=employee.last_name,
            first_name=employee.first_name,
            patronymic=employee.patronymic,
            phone_number=employee.phone_number,
            work_number=employee.work_number,
            email=employee.email,
            birth_date=employee.birth_date,
            chat_id=employee.chat_id,
            is_active=employee.is_active,
            rights=user_rights,
            positions=positions_dto
        )

    async def get_user_primary_dept_id(self, user_id: int) -> Optional[int]:
        """Получение ID основного актуального подразделения сотрудника"""
        return await self.emp_repo.get_primary_department_id(user_id)