# server/app/services/sync_service.py
from server.app.database.document_models import AppRights
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.document_repo import DocumentRepository

class SyncService:
    def __init__(self, emp_repo: EmployeesRepository, doc_repo: DocumentRepository):
        self.emp_repo = emp_repo
        self.doc_repo = doc_repo

    async def sync_employee(self, employee_id: int):
        emp = await self.emp_repo.get_by_id(employee_id)
        if not emp:
            return

        existing = await self.doc_repo.get_system_employee(employee_id)
        rights = existing.rights if existing else AppRights.user # По умолчанию user

        # Обновляем, если есть расхождения в ФИО или правах
        if not existing or (
            existing.last_name != emp.last_name or
            existing.first_name != emp.first_name or
            existing.patronymic != emp.patronymic or
            existing.rights != rights
        ):
            await self.doc_repo.upsert_system_employee(
                id=emp.id,
                last_name=emp.last_name,
                first_name=emp.first_name,
                patronymic=emp.patronymic or "",
                rights=rights
            )
            await self.doc_repo.db.commit()