import logging
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from server.bot.config import bot_settings
from server.bot.keyboards.menu_kb import get_cancel_keyboard, get_main_menu
from server.bot.services import messages as msg

# Кэш для связывания сообщений в канале с пользователями (в ОЗУ)
# Ключ: message_id в канале, Значение: user_id пользователя
support_storage = {}

router = Router()
logger = logging.getLogger("bot_support")


class SupportStates(StatesGroup):
    waiting_for_issue = State()  # Ожидание описания проблемы


@router.message(F.chat.type == "private", F.text == "🆘 Поддержка")
async def start_support_request(message: Message, state: FSMContext):
    """Вход в сценарий отправки обращения в поддержку"""
    await state.set_state(SupportStates.waiting_for_issue)
    await message.answer(
        text=msg.SUPPORT_START,
        reply_markup=get_cancel_keyboard()
    )


@router.message(SupportStates.waiting_for_issue, F.text == "❌ Отмена")
async def cancel_support_request(message: Message, state: FSMContext):
    """Сброс сценария и возврат в главное меню"""
    await state.clear()
    await message.answer(
        text=msg.SUPPORT_CANCEL,
        reply_markup=get_main_menu()
    )


@router.message(SupportStates.waiting_for_issue)
async def handle_user_support_request(message: Message, state: FSMContext, bot: Bot):
    """Принимает обращение (любой контент) и пересылает его в канал поддержки"""

    # Исключаем случайные нажатия на кнопки главного меню во время FSM
    if message.text in ["📄 Новый документ", "📸 Распознать по фото", "⏳ Мои переработки"]:
        await state.clear()
        return

    user_id = message.from_user.id
    logger.info(f"Получено обращение от user_id={user_id}")

    full_name = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else "Нет юзернейма"

    # Генерируем шапку из messages.py
    user_info = msg.get_support_ticket_header(full_name, username, user_id)

    try:
        # 1. Отправляем инфо-шапку в канал поддержки
        info_message = await bot.send_message(
            chat_id=bot_settings.SUPPORT_CHAT_ID,
            text=user_info,
            parse_mode="Markdown"
        )

        # 2. Копируем само сообщение пользователя привязкой к шапке
        copied_message = await message.send_copy(
            chat_id=bot_settings.SUPPORT_CHAT_ID,
            reply_to_message_id=info_message.message_id
        )

        # 3. Сохраняем связи для возможности реплая на любое из сообщений
        support_storage[info_message.message_id] = user_id
        support_storage[copied_message.message_id] = user_id

        await state.clear()
        await message.answer(
            text=msg.SUPPORT_SUCCESS,
            reply_markup=get_main_menu()
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке обращения от {user_id}: {e}", exc_info=True)
        await state.clear()
        await message.answer(
            text=msg.SUPPORT_ERROR,
            reply_markup=get_main_menu()
        )


@router.message(F.chat.id == bot_settings.SUPPORT_CHAT_ID)
@router.channel_post(F.chat.id == bot_settings.SUPPORT_CHAT_ID)
async def handle_admin_reply(message: Message, bot: Bot):
    """Ловит реплаи админов из канала/чата поддержки и отправляет их пользователям"""
    if not message.reply_to_message:
        return

    original_channel_msg_id = message.reply_to_message.message_id
    target_user_id = support_storage.get(original_channel_msg_id)

    if not target_user_id:
        return

    try:
        # Копируем ответ админа (текст/фото/медиа) прямо пользователю в ЛС
        await message.send_copy(chat_id=target_user_id)

        # Подтверждаем отправку в канале поддержки
        await message.reply(text=msg.SUPPORT_REPLY_DELIVERED)
        logger.info(f"Ответ успешно переслан пользователю user_id={target_user_id}")

    except Exception as e:
        logger.error(f"Не удалось отправить ответ пользователю {target_user_id}: {e}")
        await message.reply(text=msg.SUPPORT_REPLY_FAILED)