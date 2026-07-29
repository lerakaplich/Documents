from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.repositories.employee_repo import EmployeesRepository
from server.bot.services.bot_repo import BotRepository


class EmployeeAuthMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        event_user: User | None = data.get("event_from_user")
        emp_session: AsyncSession | None = data.get("emp_session")
        doc_session: AsyncSession | None = data.get("doc_session")

        if not event_user or not emp_session:
            return await handler(event, data)

        # Создаем репозиторий бота
        bot_repo = BotRepository(doc_session=doc_session, emp_session=emp_session)

        # 1. Находим сотрудника по chat_id (Telegram ID)
        employee = await bot_repo.get_employee_by_chat_id(event_user.id)

        # ❌ Если пользователь не найден в кадровой базе
        if not employee:
            text = "⚠️ **Доступ запрещен.**\nВаш Telegram-аккаунт не привязан к профилю сотрудника в системе."
            if isinstance(event, Message):
                await event.answer(text, parse_mode="Markdown")
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ запрещен", show_alert=True)
                if event.message and isinstance(event.message, Message):
                    await event.message.answer(text, parse_mode="Markdown")
            return None

        # 2. Безопасно извлекаем основную должность и department_id
        primary_position = employee.positions[0] if employee.positions else None
        department_id = primary_position.department_id if primary_position else None

        # ✅ Пробрасываем контекст прямо в аргументы хэндлеров
        data["bot_repo"] = bot_repo
        data["current_employee"] = employee
        data["internal_user_id"] = employee.id
        data["department_id"] = department_id

        return await handler(event, data)