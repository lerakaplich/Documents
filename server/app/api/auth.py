# Авторизация и выдача сессий
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.app.database.models import Employee, UserSession
from server.app.database.session import get_employees_db, get_docs_db
from server.app.schemas.user_schemas.auth_dto import AuthRequestCode, TokenResponse, AuthVerifyCode, TokenRefreshRequest

router = APIRouter(prefix="/auth", tags=["Auth"])

# Имитация кэша для кодов подтверждения (в реальном проекте лучше Redis, но для старта монолита хватит словаря)
# Структура: {"+79991112233": {"code": "1234", "expires_at": datetime}}
VERIFICATION_CODES = {}


@router.post("/request-code")
async def request_code(payload: AuthRequestCode, db_emp: AsyncSession = Depends(get_employees_db)):
    """
    ЭНДПОИНТ 1: Запрос одноразового кода.
    Ищет сотрудника по личному мобильному номеру в кадровой базе.
    """
    # 1. Ищем сотрудника в БД Кадров МАЗ
    result = await db_emp.execute(select(Employee).where(Employee.phone_number == payload.phone_number))
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сотрудник с таким номером телефона не найден в базе кадров."
        )

    if not employee.chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы не активировали Telegram-бота. Сначала запустите бота на вашем телефоне."
        )

    # 2. Генерируем 4-значный код
    generated_code = str(secrets.randbelow(9000) + 1000)  # от 1000 до 9999

    # 3. Сохраняем код в кэш на 5 минут
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    VERIFICATION_CODES[payload.phone_number] = {
        "code": generated_code,
        "expires_at": expire_time
    }

    # TODO: Передать код Разработчику 3 (в Telegram Bot).
    # Бот увидит этот код (или дернет специальный внутренний эндпоинт) и перешлет юзеру в чат.
    print(f"[DEBUG LOG] Код {generated_code} сгенерирован для отправки на chat_id {employee.chat_id}")

    return {"status": "success", "message": "Код отправлен в Telegram"}


@router.post("/verify-code", response_model=TokenResponse)
async def verify_code(
        payload: AuthVerifyCode,
        db_emp: AsyncSession = Depends(get_employees_db),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    """
    ЭНДПОИНТ 2: Проверка кода, который ввел пользователь.
    Выдает короткий Access JWT и длинный Refresh (при 'Запомнить меня').
    """
    # 1. Проверяем код в нашем кэше
    cached_data = VERIFICATION_CODES.get(payload.phone_number)
    if not cached_data:
        raise HTTPException(status_code=400, detail="Код не запрашивался или устарел.")

    if datetime.now(timezone.utc) > cached_data["expires_at"]:
        VERIFICATION_CODES.pop(payload.phone_number, None)
        raise HTTPException(status_code=400, detail="Срок действия кода истек.")

    if cached_data["code"] != payload.code:
        raise HTTPException(status_code=400, detail="Неверный код подтверждения.")

    # Код верный — удаляем из кэша
    VERIFICATION_CODES.pop(payload.phone_number, None)

    # 2. Получаем ID сотрудника из кадровой БД
    emp_result = await db_emp.execute(select(Employee).where(Employee.phone_number == payload.phone_number))
    employee = emp_result.scalar_one_or_none()

    # 3. Генерируем фейковый JWT-access токен (для простоты примера, Разработчик 2 позже обернет в настоящий PyJWT)
    access_token = f"access_secret_jwt_for_id_{employee.id}"
    refresh_token = None

    # 4. Если нажата галочка "Запомнить меня" — генерируем долгоживущую сессию в БД документов
    if payload.remember_me:
        refresh_token = secrets.token_urlsafe(64)  # Мощная случайная строка
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)  # На 30 дней

        new_session = UserSession(
            employee_id=employee.id,
            refresh_token=refresh_token,
            device_info=payload.device_info,
            expires_at=expires_at
        )
        db_docs.add(new_session)
        await db_docs.flush()  # Фиксируем в БД документов

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(payload: TokenRefreshRequest, db_docs: AsyncSession = Depends(get_docs_db)):
    """
    ЭНДПОИНТ 3: Функция "Запомнить меня".
    Вызывается автоматически при старте PyQt6, если найден локальный токен.
    """
    # Ищем сессию в БД документов
    result = await db_docs.execute(select(UserSession).where(UserSession.refresh_token == payload.refresh_token))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=401, detail="Сессия не найдена. Авторизуйтесь заново.")

    # Проверяем протух ли токен по дате
    # Преобразуем дату из БД к TZ-aware для корректного сравнения
    db_expires = session.expires_at.replace(
        tzinfo=timezone.utc) if session.expires_at.tzinfo is None else session.expires_at
    if datetime.now(timezone.utc) > db_expires:
        await db_docs.delete(session)  # Удаляем старье
        raise HTTPException(status_code=401, detail="Срок действия сессии истек.")

    # Генерируем новый короткий Access токен
    new_access_token = f"access_secret_jwt_for_id_{session.employee_id}"

    return TokenResponse(access_token=new_access_token, refresh_token=session.refresh_token)


@router.post("/logout")
async def logout(payload: TokenRefreshRequest, db_docs: AsyncSession = Depends(get_docs_db)):
    """
    ЭНДПОИНТ 4: Полный выход из системы (нажатие кнопки Выйти в UI).
    Стирает сессию из базы данных документов.
    """
    result = await db_docs.execute(select(UserSession).where(UserSession.refresh_token == payload.refresh_token))
    session = result.scalar_one_or_none()

    if session:
        await db_docs.delete(session)
        return {"status": "success", "message": "Сессия успешно закрыта в БД"}

    return {"status": "success", "message": "Сессия не существовала или уже удалена"}
