from fastapi import APIRouter, Depends

from server.app.deps import get_current_user, get_tag_service
from server.app.schemas.doc.tag_dto import TagRead, TagCreate, TagUpdate
from server.app.services.tag_service import TagService

router = APIRouter(prefix="/tag", tags=["Tags"])

@router.get("", response_model=list[TagRead])
async def get_tags(service: TagService = Depends(get_tag_service)):
    return await service.get_all()

@router.get("/{tag_id}", response_model=TagRead)
async def get_tag(tag_id: int, service: TagService = Depends(get_tag_service)):
    return await service.get_one(tag_id)

@router.post("", response_model=TagRead, status_code=201)
async def create_tag(data: TagCreate, u=Depends(get_current_user), s=Depends(get_tag_service)):
    return await s.create(u, data)

@router.patch("/{tag_id}", response_model=TagRead)
async def update_tag(tag_id: int, data: TagUpdate, u=Depends(get_current_user), s=Depends(get_tag_service)):
    return await s.update(u, tag_id, data)

@router.delete("/{tag_id}")
async def delete_tag(tag_id: int, u=Depends(get_current_user), s=Depends(get_tag_service)):
    return await s.delete(u, tag_id)