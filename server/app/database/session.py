from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Конфигурационные строки подключения (Разработчик 2 уберет их в .env файл)
DOCUMENTS_DB_URL = "postgresql+asyncpg://postgres:admin@127.0.0.1:5432/documents"
EMPLOYEES_DB_URL = "postgresql+asyncpg://postgres:admin@127.0.0.1:5432/employees"

# 1. Создаем асинхронные движки
engine_docs = create_async_engine(DOCUMENTS_DB_URL, echo=False, pool_pre_ping=True)
engine_employees = create_async_engine(EMPLOYEES_DB_URL, echo=False, pool_pre_ping=True)

# 2. Создаем фабрики сессий
async_session_docs = async_sessionmaker(
    bind=engine_docs,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

async_session_employees = async_sessionmaker(
    bind=engine_employees,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# 3. Функции-зависимости (Depends) для использования в эндпоинтах FastAPI

async def get_docs_db() -> AsyncGenerator[AsyncSession, None]:
    """Генератор сессии для работы с базой данных Документов"""
    async with async_session_docs() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_employees_db() -> AsyncGenerator[AsyncSession, None]:
    """Генератор сессии для работы с кадровой базой данных МАЗ"""
    async with async_session_employees() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()