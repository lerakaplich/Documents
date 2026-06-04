from server.app.repositories.org_repo import OrgRepository
from pydantic import BaseModel
from typing import List, Optional

from server.app.schemas.user_schemas.org_dto import DepartmentNode

class OrgService:
    def __init__(self, repo: OrgRepository):
        self.repo = repo

    async def get_org_structure(self, org_id: int) -> List[DepartmentNode]:
        depts = await self.repo.get_departments_by_org(org_id)

        # Создаем словарь для быстрого поиска
        nodes = {d.id: DepartmentNode(id=d.id, name=d.name) for d in depts}
        root_nodes = []

        for d in depts:
            node = nodes[d.id]
            if d.parent_id is None:
                root_nodes.append(node)
            else:
                if d.parent_id in nodes:
                    nodes[d.parent_id].children.append(node)

        return root_nodes