from fastapi import Depends, HTTPException, status

from server.app.database.document_models import AppRights
from server.app.deps import get_current_user
from server.app.schemas.user_schemas.employee_dto import CurrentUser

# --- ПРОВЕРКА РОЛЕЙ (RBAC) ---

class RoleChecker:
    """
    Класс-зависимость для фильтрации доступа по ролям.
    Пример: Depends(RoleChecker([AppRights.admin, AppRights.superadmin]))
    """
    def __init__(self, allowed_rights: list[AppRights]):
        self.allowed_rights = allowed_rights

    def __call__(self, current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.rights not in self.allowed_rights:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Отказ в доступе. Недостаточно системных прав."
            )
        return current_user