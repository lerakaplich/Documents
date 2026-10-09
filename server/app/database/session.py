import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Загружаем переменные из локального файла .env
load_dotenv()

# Получаем URLs из окружения
DOCUMENTS_DB_URL = os.getenv("DOCUMENTS_DB_URL")
EMPLOYEES_DB_URL = os.getenv("EMPLOYEES_DB_URL")
DOCS_DB_URL_RAW = os.getenv("DOCS_DB_URL_RAW")

# Дополнительная проверка, чтобы приложение сразу падало, если забыли заполнить .env
if not DOCUMENTS_DB_URL or not EMPLOYEES_DB_URL:
    raise ValueError("Не заданы переменные окружения для подключения к БД!")

# 1. Создаем асинхронные движки
# Пул для БД документов
engine_docs = create_async_engine(
    DOCUMENTS_DB_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=50,         # Держим 50 постоянных соединений
    max_overflow=50,      # До 50 временно при пиках (всего 100)
    pool_timeout=10.0,    # Не ждем свободое соединение дольше 10 сек (выдаст ошибку сразу)
    pool_recycle=1800,    # Пересоздаем соединения каждые 30 мин
)

# Пул для БД сотрудников
engine_employees = create_async_engine(
    EMPLOYEES_DB_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
    pool_timeout=10.0,
    pool_recycle=1800,
)

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
    async with async_session_docs() as session:
        yield session

async def get_employees_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_employees() as session:
        yield session