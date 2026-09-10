from typing import Optional, Dict, Any
from client.core.http_client import HttpClient, AuthError
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Сервис авторизации"""

    def __init__(self, http_client: HttpClient):
        self.client = http_client

    def login(self, phone: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
        """
        Вход в систему

        Args:
            phone: Номер телефона (с +375 или без)
            password: Пароль
            remember_me: Запомнить сессию

        Returns:
            Dict с токенами и данными пользователя
        """
        try:
            # Очищаем номер телефона от лишних символов
            clean_phone = phone.strip()
            # Убеждаемся, что номер начинается с +
            if not clean_phone.startswith('+'):
                clean_phone = '+' + clean_phone

            logger.info(f"Попытка входа для номера: {clean_phone}")

            response = self.client.post(
                "/auth/login",
                json={
                    "phone_number": clean_phone,
                    "password": password,
                    "remember_me": remember_me
                }
            )

            # Сохраняем токены в клиенте
            if "access_token" in response and "refresh_token" in response:
                self.client.set_tokens(
                    access_token=response["access_token"],
                    refresh_token=response["refresh_token"],
                    expires_in=response.get("expires_in", 3600)
                )
                logger.info("Токены успешно сохранены")

            return response

        except Exception as e:
            logger.error(f"Ошибка входа: {e}")
            raise

    def logout(self, refresh_token: str = None) -> bool:
        """
        Выход из системы

        Args:
            refresh_token: Токен обновления (если не передан, берется из клиента)
        """
        try:
            token = refresh_token or self.client._refresh_token
            if not token:
                logger.warning("Нет refresh_token для выхода")
                self.client.clear_tokens()
                return True

            self.client.post("/auth/logout", json={"refresh_token": token})
            self.client.clear_tokens()
            logger.info("Выход выполнен успешно")
            return True

        except Exception as e:
            logger.error(f"Ошибка выхода: {e}")
            self.client.clear_tokens()
            return False

    def refresh_token(self) -> Optional[Dict[str, Any]]:
        """Обновить токен доступа"""
        try:
            if not self.client._refresh_token:
                logger.warning("Нет refresh_token для обновления")
                return None

            response = self.client.post(
                "/auth/refresh",
                json={"refresh_token": self.client._refresh_token}
            )

            if "access_token" in response:
                self.client.set_tokens(
                    access_token=response["access_token"],
                    refresh_token=response.get("refresh_token", self.client._refresh_token),
                    expires_in=response.get("expires_in", 3600)
                )
                logger.info("Токен успешно обновлен")
                return response

            return None

        except Exception as e:
            logger.error(f"Ошибка обновления токена: {e}")
            return None

    def change_password(self, current_password: str, new_password: str) -> bool:
        """Сменить пароль"""
        try:
            self.client.post(
                "/auth/change-password",
                json={
                    "current_password": current_password,
                    "new_password": new_password
                }
            )
            logger.info("Пароль успешно изменен")
            return True

        except Exception as e:
            logger.error(f"Ошибка смены пароля: {e}")
            raise

    def forgot_password(self, phone_number: str) -> bool:
        """Запрос на восстановление пароля"""
        try:
            clean_phone = phone_number.strip()
            if not clean_phone.startswith('+'):
                clean_phone = '+' + clean_phone

            self.client.post(
                "/auth/forgot-password",
                json={"phone_number": clean_phone}
            )
            logger.info(f"Запрос восстановления отправлен для {clean_phone}")
            return True

        except Exception as e:
            logger.error(f"Ошибка запроса восстановления: {e}")
            raise

    def verify_reset_code(self, phone_number: str, code: str) -> bool:
        """Подтверждение кода восстановления"""
        try:
            clean_phone = phone_number.strip()
            if not clean_phone.startswith('+'):
                clean_phone = '+' + clean_phone

            self.client.post(
                "/auth/verify-reset-code",
                json={
                    "phone_number": clean_phone,
                    "code": code
                }
            )
            logger.info(f"Код подтвержден для {clean_phone}")
            return True

        except Exception as e:
            logger.error(f"Ошибка подтверждения кода: {e}")
            raise

    def reset_password(self, phone_number: str, code: str, new_password: str) -> bool:
        """Сброс пароля с подтверждением кода"""
        try:
            clean_phone = phone_number.strip()
            if not clean_phone.startswith('+'):
                clean_phone = '+' + clean_phone

            self.client.post(
                "/auth/reset-password",
                json={
                    "phone_number": clean_phone,
                    "code": code,
                    "new_password": new_password
                }
            )
            logger.info(f"Пароль сброшен для {clean_phone}")
            return True

        except Exception as e:
            logger.error(f"Ошибка сброса пароля: {e}")
            raise

