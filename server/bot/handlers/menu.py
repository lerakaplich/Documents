from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from server.bot.handlers.document_creation.common import start_create_document
from server.bot.handlers.overtimes import open_overtimes
from server.bot.handlers.photo_to_tiff import open_photo_to_tiff
from server.bot.handlers.support import open_support
from server.bot.keyboards.texts import MenuButton
from server.bot.services.bot_repo import BotRepository

router = Router()
router.message.filter(F.chat.type == "private")


@router.message(F.text == MenuButton.NEW_DOCUMENT)
async def menu_new_document(message: Message, state: FSMContext, bot_repo: BotRepository):
    await state.clear()
    await start_create_document(message, state, bot_repo)


@router.message(F.text == MenuButton.PHOTO_TO_TIFF)
async def menu_photo_to_tiff(message: Message, state: FSMContext):
    await open_photo_to_tiff(message, state)


@router.message(F.text == MenuButton.OVERTIMES)
async def menu_overtimes(message: Message, state: FSMContext):
    await state.clear()
    await open_overtimes(message)


@router.message(F.text == MenuButton.SUPPORT)
async def menu_support(message: Message, state: FSMContext):
    await open_support(message, state)