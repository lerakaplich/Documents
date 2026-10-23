import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from cachetools import TTLCache

from server.bot.config import bot_settings
from server.bot.keyboards.menu_kb import get_cancel_keyboard, get_main_menu
from server.bot.services import messages as msg

router = Router()
logger = logging.getLogger("bot_support")

# message_id в чате поддержки -> user_id. TTL, чтобы словарь не рос бесконечно
_ticket_owners: TTLCache[int, int] = TTLCache(maxsize=10_000, ttl=7 * 24 * 3600)


class SupportStates(StatesGroup):
    waiting_for_issue = State()


async def open_support(message: Message, state: FSMContext) -> None:
    await state.set_state(SupportStates.waiting_for_issue)
    await message.answer(msg.SUPPORT_START, reply_markup=get_cancel_keyboard())


@router.message(SupportStates.waiting_for_issue)
async def handle_user_request(message: Message, state: FSMContext, bot: Bot):
    user = message.from_user
    logger.info("Support request from user_id=%s", user.id)

    username = f"@{user.username}" if user.username else "нет юзернейма"
    header = msg.get_support_ticket_header(user.full_name, username, user.id)

    try:
        info = await bot.send_message(bot_settings.SUPPORT_CHAT_ID, header)
        copy = await message.send_copy(
            chat_id=bot_settings.SUPPORT_CHAT_ID, reply_to_message_id=info.message_id
        )
        _ticket_owners[info.message_id] = user.id
        _ticket_owners[copy.message_id] = user.id
        answer = msg.SUPPORT_SUCCESS
    except Exception:
        logger.exception("Support request failed for user_id=%s", user.id)
        answer = msg.SUPPORT_ERROR

    await state.clear()
    await message.answer(answer, reply_markup=get_main_menu())


@router.message(F.chat.id == bot_settings.SUPPORT_CHAT_ID, F.reply_to_message)
@router.channel_post(F.chat.id == bot_settings.SUPPORT_CHAT_ID, F.reply_to_message)
async def handle_admin_reply(message: Message):
    target_user_id = _ticket_owners.get(message.reply_to_message.message_id)
    if not target_user_id:
        return

    try:
        await message.send_copy(chat_id=target_user_id)
        await message.reply(msg.SUPPORT_REPLY_DELIVERED)
    except Exception:
        logger.exception("Failed to deliver support reply to user_id=%s", target_user_id)
        await message.reply(msg.SUPPORT_REPLY_FAILED)