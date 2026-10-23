from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from server.app.database.session import async_session_docs, async_session_employees
from server.bot.services.bot_repo import BotRepository


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_employees() as emp_session, async_session_docs() as doc_session:
            data["emp_session"] = emp_session
            data["doc_session"] = doc_session
            data["bot_repo"] = BotRepository(doc_session=doc_session, emp_session=emp_session)
            return await handler(event, data)