from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.app.database.session import get_docs_db, get_employees_db
from server.app.database.models import Employee, SystemEmployee, AppRights
from server.app.schemas.user_schemas.employee_dto import CurrentUser

# Инициализируем схему авторизации через заголовок Authorization: Bearer <token>
security = HTTPBearer()


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db_emp: AsyncSession = Depends(get_employees_db),
        db_docs: AsyncSession = Depends(get_docs_db)
) -> CurrentUser:
    """
    Основная зависимость, которая извлекает access-токен, проверяет его
    и собирает полную информацию о пользователе из двух баз данных.
    """
    token = credentials.credentials

    # В Части 2 'auth.py' мы временно генерировали токен как "access_secret_jwt_for_id_<id>"
    # Разработчик 2 на реальном проде разберет здесь полноценный JWT-токен.
    # Сейчас мы парсим наш тестовый токен для проверки работоспособности.
    if not token.startswith("access_secret_jwt_for_id_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный сессионный токен.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Извлекаем ID пользователя из строки нашего тестового токена
        user_id_str = token.replace("access_secret_jwt_for_id_", "")
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Искаженный токен авторизации.",
        )

    # 1. Запрашиваем личные данные из Кадровой БД МАЗ
    emp_result = await db_emp.execute(select(Employee).where(Employee.id == user_id))
    employee = emp_result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь, связанный с этим токеном, не найден в кадровой системе."
        )

    # 2. Запрашиваем уровень прав доступа из БД Документов (СЭД)
    sys_result = await db_docs.execute(select(SystemEmployee).where(SystemEmployee.id == user_id))
    system_user = sys_result.scalar_one_or_none()

    # Если сотрудника добавили в кадры, но еще не завели в СЭД — даем базовую роль 'user'
    user_role = system_user.rights if system_user else AppRights.user

    # 3. Собираем и возвращаем объединенный объект
    return CurrentUser(
        id=employee.id,
        service_number=employee.service_number,
        last_name=employee.last_name,
        first_name=employee.first_name,
        patronymic=employee.patronymic,
        position=employee.position,
        role=user_role
    )


# --- ПРОВЕРКА РОЛЕЙ (RBAC) ---

class RoleChecker:
    """
    Класс-зависимость для жесткой фильтрации доступа по ролям.
    Позволяет писать: Depends(RoleChecker([AppRights.admin, AppRights.superadmin]))
    """

    def __init__(self, allowed_roles: list[AppRights]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Отказ в доступе. Недостаточно системных прав для выполнения операции."
            )
        return current_user