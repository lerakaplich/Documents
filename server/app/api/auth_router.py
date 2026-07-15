from fastapi import APIRouter, Depends, status

from server.app.deps import get_auth_service, get_current_user
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.authorization.auth_service import AuthService
from server.app.schemas.user_schemas.auth_dto import UserLoginRequest, TokenResponse, TokenRefreshRequest, \
    PasswordChangeRequest, ResetPasswordConfirm, ForgotPasswordRequest

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


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service)
):
    """Смена пароля из личного кабинета авторизованного пользователя"""
    await service.change_user_password(int(current_user.id), payload)
    return {"status": "success", "message": "Пароль успешно изменен."}

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    payload: ForgotPasswordRequest,
    service: AuthService = Depends(get_auth_service)
):
    """Шаг 1: Запрос кода восстановления в Telegram-бот"""
    await service.send_reset_code(payload.phone_number)
    return {"status": "success", "message": "Код подтверждения отправлен в Telegram."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    payload: ResetPasswordConfirm,
    service: AuthService = Depends(get_auth_service)
):
    """Шаг 2: Валидация кода и установка нового пароля"""
    await service.reset_password_by_code(payload)
    return {"status": "success", "message": "Пароль успешно обновлен. Войдите с новым паролем."}