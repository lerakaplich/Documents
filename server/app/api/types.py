from fastapi import APIRouter, Depends, status
from server.app.deps import get_current_user, get_doc_type_service
from server.app.schemas.doc.doc_type import DocTypeRead, DocTypeCreate, DocTypeUpdate
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.doc_type_service import DocTypeService

router = APIRouter(prefix="/doc-types", tags=["Document Types"])

@router.get("", response_model=list[DocTypeRead])
async def get_all_types(service: DocTypeService = Depends(get_doc_type_service)):
    return await service.get_all()

@router.get("/{type_id}", response_model=DocTypeRead)
async def get_type(type_id: int, service: DocTypeService = Depends(get_doc_type_service)):
    return await service.get_one(type_id)

@router.post("", response_model=DocTypeRead, status_code=status.HTTP_201_CREATED)
async def create_doc_type(
    data: DocTypeCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: DocTypeService = Depends(get_doc_type_service)
):
    return await service.create(current_user, data)

@router.patch("/{type_id}", response_model=DocTypeRead)
async def update_doc_type(
    type_id: int,
    data: DocTypeUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: DocTypeService = Depends(get_doc_type_service)
):
    return await service.update(current_user, type_id, data)

@router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doc_type(
    type_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: DocTypeService = Depends(get_doc_type_service)
):
    await service.delete(current_user, type_id)
    return None