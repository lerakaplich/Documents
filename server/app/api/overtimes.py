from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, status, UploadFile, File, Query
from starlette.responses import StreamingResponse

from server.app.deps import get_current_user, get_overtime_service, get_overtime_import_service, \
    get_overtime_export_service

from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.schemas.user_schemas.overtime_dto import OvertimeRead, OvertimeCreate, OvertimeUpdate, \
    OvertimeBulkUpdateNote
from server.app.services.overtime.overtime import OvertimeService
from server.app.services.overtime.overtime_export import OvertimeExportService
from server.app.services.overtime.overtime_import import OvertimeImportService

router = APIRouter(prefix="/overtime", tags=["Overtime"])

@router.post("", response_model=OvertimeRead, status_code=status.HTTP_201_CREATED)
async def create_overtime(
    data: OvertimeCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    return await service.create_by_admin(current_user, data)

@router.patch("/bulk-description") #bot
async def update_bulk_descriptions(
    data: OvertimeBulkUpdateNote,
    current_user: CurrentUser = Depends(get_current_user),
    service: OvertimeService = Depends(get_overtime_service)
):
    """
    Массовое обновление заметок/описаний для списка переработок
    """
    return await service.update_bulk_notes_by_employee(current_user, data.overtime_ids, data.note)

@router.patch("/{ot_id}/description")
async def update_my_description(
    ot_id: int,
    note: str,
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    return await service.update_note_by_employee(current_user, ot_id, note)

@router.patch("/{ot_id}")
async def admin_update_overtime(
    ot_id: int,
    data: OvertimeUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    return await service.update_by_admin(current_user, ot_id, data)

@router.get("/my", response_model=list[OvertimeRead])
async def get_my_overtime(
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    return await service.get_by_employee(current_user, current_user.id)

@router.get("/department/{dept_id}", response_model=list[OvertimeRead])
async def get_dept_overtime(
    dept_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    return await service.get_by_dept(current_user, dept_id)

@router.get("/all", response_model=list[OvertimeRead])
async def get_all_overtime(
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    return await service.get_all(current_user)

@router.delete("/{ot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_overtime(
    ot_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    await service.delete_by_admin(current_user, ot_id)


@router.post("/import-excel", status_code=status.HTTP_200_OK)
async def import_overtimes_from_excel(
        file: UploadFile = File(..., description="Excel файл выгрузки СКУД"),
        current_user: CurrentUser = Depends(get_current_user),
        import_service: OvertimeImportService = Depends(get_overtime_import_service)
):
    """Эндпоинт для пакетного импорта переработок сотрудников из Excel файлов"""


    # 2. Передаем бинарный поток напрямую в сервис
    # file.file - это и есть файловый объект (File-like object), который ожидает pandas
    import_result = await import_service.import_from_excel_file(file.file)

    return {
        "status": "completed",
        "data": import_result
    }


@router.get("/export-excel", response_class=StreamingResponse)
async def export_overtime_to_excel(
        dept_id: Optional[int] = Query(None, description="ID департамента для фильтрации"),
        start_date: Optional[date] = Query(None, description="Начало периода"),
        end_date: Optional[date] = Query(None, description="Конец периода"),
        current_user: CurrentUser = Depends(get_current_user),
        export_service: OvertimeExportService = Depends(get_overtime_export_service)
):
    """
    Эндпоинт генерирует и отдаёт Excel-файл со сводным отчетом по переработкам
    """
    # 1. Проверяем права пользователя на выгрузку отчетов внутри сервиса безопасности
    await export_service.security.verify_can_export(current_user, dept_id)

    # 2. Генерируем Excel в байтовый поток в памяти (BytesIO)
    file_buffer, filename = await export_service.generate_report_buffer(
        dept_id=dept_id,
        start_date=start_date,
        end_date=end_date
    )

    # 3. Отдаем файл клиенту напрямую
    return StreamingResponse(
        file_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )