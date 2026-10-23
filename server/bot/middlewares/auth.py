from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from server.bot.config import bot_settings

ACCESS_DENIED_TEXT = (
    "⚠️ <b>Доступ запрещен.</b>\n"
    "Ваш Telegram-аккаунт не привязан к профилю сотрудника. Нажмите /start."
)


class EmployeeAuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        bot_repo = data.get("bot_repo")

        if user is None or bot_repo is None or self._is_open_event(event):
            return await handler(event, data)

        employee = await bot_repo.get_employee_by_chat_id(user.id)
        if employee is None:
            await self._deny(event)
            return None

        primary = employee.positions[0] if employee.positions else None
        data["current_employee"] = employee
        data["internal_user_id"] = employee.id
        data["department_id"] = primary.department_id if primary else None
        return await handler(event, data)

    @staticmethod
    def _is_open_event(event: TelegramObject) -> bool:
        """События, которые доступны без привязки аккаунта."""
        if not isinstance(event, Message):
            return False
        if event.chat.id == bot_settings.SUPPORT_CHAT_ID:  # ответы админов в чате поддержки
            return True
        return bool(event.contact or (event.text and event.text.startswith("/start")))

    @staticmethod
    async def _deny(event: TelegramObject) -> None:
        if isinstance(event, Message):
            await event.answer(ACCESS_DENIED_TEXT)
        elif isinstance(event, CallbackQuery):
            await event.answer("Доступ запрещен", show_alert=True)