from contextlib import asynccontextmanager
from server.app.database.session import get_employees_db, get_docs_db  # Твой генератор сессий БД
from server.bot.services.bot_repo import BotRepository


class DbSessionMiddleware:
    async def __call__(self, handler, event, data):
        async with asynccontextmanager(get_employees_db)() as emp_session:
            async with asynccontextmanager(get_docs_db)() as doc_session:
                data["emp_session"] = emp_session
                data["doc_session"] = doc_session  # или data["session"]
                data["bot_repository"] = BotRepository(doc_session=doc_session, emp_session=emp_session)
                return await handler(event, data)