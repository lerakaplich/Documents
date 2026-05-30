from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.app.database.document_models import SystemEmployee, AppRights
from server.app.database.session import get_docs_db  # УБРАЛИ кадровый get_employees_db
from server.app.schemas.user_schemas.employee_dto import CurrentUser

security = HTTPBearer()


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db_docs: AsyncSession = Depends(get_docs_db)
) -> CurrentUser:
    """
    Основная зависимость авторизации СЭД.
    Работает ИСКЛЮЧИТЕЛЬНО с локальной базой db_documents ради микросервисной изоляции.
    """
    token = credentials.credentials

    # Парсинг нашего тестового токена (на проде здесь будет jwt.decode)
    if not token.startswith("access_secret_jwt_for_id_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный сессионный токен.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id_str = token.replace("access_secret_jwt_for_id_", "")
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Искаженный токен авторизации.",
        )

    # Запрашиваем данные пользователя из ЛОКАЛЬНОЙ таблицы system_employees базы СЭД
    sys_result = await db_docs.execute(select(SystemEmployee).where(SystemEmployee.id == user_id))
    system_user = sys_result.scalar_one_or_none()

    if not system_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не зарегистрирован в системе документооборота."
        )

    return CurrentUser(
        id=system_user.id,
        last_name=system_user.last_name,
        first_name=system_user.first_name,
        patronymic=system_user.patronymic,
        rights=system_user.rights,
        service_number="N/A"
    )


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