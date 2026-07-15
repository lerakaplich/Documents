from fastapi import APIRouter, Depends, status

from server.app.deps import get_auth_service
from server.app.services.authorization.auth_service import AuthService
from server.app.schemas.user_schemas.auth_dto import UserLoginRequest, TokenResponse, TokenRefreshRequest

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(payload: UserLoginRequest, service: AuthService = Depends(get_auth_service)):
    """
    Первичный вход в систему по номеру телефона и паролю (из Telegram).
    Если передать 'remember_me': true, база данных сгенерирует и сохранит refresh_token.
    """
    return await service.authenticate_by_password(payload)


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_session(payload: TokenRefreshRequest, service: AuthService = Depends(get_auth_service)):
    """
    Обновление токена доступа.
    Используется PyQt6 клиентом при старте приложения (авто-вход) или когда access_token истек.
    Выполняет ротацию пары токенов.
    """
    return await service.refresh_access_token(payload)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(payload: TokenRefreshRequest, service: AuthService = Depends(get_auth_service)):
    """
    Выход из аккаунта (Разлогин).
    Полностью удаляет сессию и refresh-токен из базы данных.
    """
    await service.terminate_session(payload.refresh_token)
    return {"status": "success", "message": "Сессия успешно закрыта, рефреш-токен отозван."}