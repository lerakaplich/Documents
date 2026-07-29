from aiogram import Router

from .common import router as common_router
from .numbers import router as numbers_router
from .dynamic_steps import router as dynamic_steps_router
from .participants import router as participants_router
from .tags import router as tags_router
from .confirmation import router as confirmation_router

# Создаем объединяющий роутер
doc_creation_router = Router()

# Порядок подключения РЕШАЕТ (от специфичных к общим)
doc_creation_router.include_router(common_router)
doc_creation_router.include_router(numbers_router)
doc_creation_router.include_router(dynamic_steps_router)
doc_creation_router.include_router(participants_router)
doc_creation_router.include_router(tags_router)
doc_creation_router.include_router(confirmation_router)