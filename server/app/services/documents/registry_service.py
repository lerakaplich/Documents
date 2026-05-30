from typing import List, Optional, Tuple
from datetime import date
from server.app.database.document_models import Document, AppRights, DocStatus, DocDirection
from server.app.repositories.document_repo import DocumentRepository


class DocumentRegistryService:
    def __init__(self, db_repo: DocumentRepository):
        self.repo = db_repo

    async def get_all_paginated(
            self,
            user_id: int,
            user_rights: AppRights,
            is_completed: Optional[bool] = None,
            status_filters: Optional[List[DocStatus]] = None,
            type_id: Optional[int] = None,
            direction: Optional[DocDirection] = None,
            tag_ids: Optional[List[int]] = None,
            date_from: Optional[date] = None,
            date_to: Optional[date] = None,
            search: Optional[str] = None,
            sort_by: str = "created_at",
            sort_order: str = "desc",
            limit: int = 20,
            offset: int = 0
    ) -> Tuple[int, List[Document]]:
        """
        Бизнес-точка входа для формирования главной таблицы PyQt6.
        Обеспечивает порционную загрузку данных (пагинацию), фильтрацию и поиск по ключевым словам.
        """
        # Просто перенаправляем очищенные параметры в оптимизированный репозиторий
        return await self.repo.get_paginated_list(
            user_id=user_id,
            user_rights=user_rights,
            is_completed=is_completed,
            statuses=status_filters,
            type_id=type_id,
            direction=direction,
            tag_ids=tag_ids,
            date_from=date_from,
            date_to=date_to,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset
        )