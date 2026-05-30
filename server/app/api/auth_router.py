from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.session import get_employees_db, get_docs_db
from server.app.repositories.session_repo import SessionRepository
from server.app.services.auth_service import AuthService
from server.app.schemas.user_schemas.auth_dto import AuthRequestCode, TokenResponse, AuthVerifyCode, TokenRefreshRequest

router = APIRouter(prefix="/auth", tags=["Auth"])


# Вспомогательная функция сборки сервиса
def get_auth_service(
    db_emp: AsyncSession = Depends(get_employees_db),
    db_docs: AsyncSession = Depends(get_docs_db)
) -> AuthService:
    session_repo = SessionRepository(db_docs)
    return AuthService(db_emp=db_emp, session_repo=session_repo)


@router.post("/request-code", status_code=status.HTTP_200_OK)
async def request_code(payload: AuthRequestCode, service: AuthService = Depends(get_auth_service)):
    """Запрос одноразового OTP кода подтверждения через Telegram"""
    await service.generate_verification_code(payload.phone_number)
    return {"status": "success", "message": "Код отправлен в Telegram"}


@router.post("/verify-code", response_model=TokenResponse)
async def verify_code(payload: AuthVerifyCode, service: AuthService = Depends(get_auth_service)):
    """Проверка кода и выдача пары токенов (Вход в систему)"""
    return await service.verify_code_and_login(payload)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(payload: TokenRefreshRequest, service: AuthService = Depends(get_auth_service)):
    """Автоматическое обновление токена доступа для PyQt6 клиентуры"""
    return await service.refresh_access_token(payload)


@router.post("/logout")
async def logout(payload: TokenRefreshRequest, service: AuthService = Depends(get_auth_service)):
    """Полное уничтожение сессии устройства и отзыв refresh-токена"""
    await service.terminate_session(payload.refresh_token)
    return {"status": "success", "message": "Сессия успешно закрыта"}