import secrets

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.core.security_tokens import hash_password  # добавить рядом с verify_password
from server.app.database.employee_models import Employee
from server.bot.keyboards.menu_kb import get_main_menu
from server.bot.keyboards.texts import CANCEL_TEXT
from server.bot.services import messages as msg
from server.bot.services.bot_repo import BotRepository

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot_repo: BotRepository):
    await state.clear()

    if await bot_repo.get_employee_by_chat_id(message.from_user.id):
        await message.answer(msg.START_AUTHORIZED, reply_markup=get_main_menu())
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=msg.BTN_SHARE_CONTACT, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(
        msg.START_WELCOME.format(name=message.from_user.first_name), reply_markup=keyboard
    )


@router.message(F.contact)
async def handle_contact(message: Message, emp_session: AsyncSession):
    contact = message.contact
    if contact.user_id != message.from_user.id:
        await message.answer(msg.ERROR_NOT_OWNER_CONTACT)
        return

    phone = contact.phone_number.lstrip("+")
    result = await emp_session.execute(
        select(Employee).where(Employee.phone_number.in_([phone, f"+{phone}"]))
    )
    employee = result.scalar_one_or_none()

    if not employee:
        await message.answer(msg.ERROR_EMPLOYEE_NOT_FOUND, reply_markup=ReplyKeyboardRemove())
        return

    raw_password = f"SED-{secrets.token_hex(3).upper()}"
    employee.chat_id = message.from_user.id
    employee.password_hash = hash_password(raw_password)
    await emp_session.commit()

    await message.answer(
        msg.AUTH_SUCCESS.format(phone=phone, password=raw_password),
        reply_markup=get_main_menu(),
    )


@router.message(Command("cancel"), StateFilter("*"))
@router.message(F.text.casefold() == CANCEL_TEXT.casefold(), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Единственный обработчик отмены для reply-кнопки."""
    if await state.get_state() is None:
        await message.answer(msg.NOTHING_TO_CANCEL, reply_markup=get_main_menu())
        return
    await state.clear()
    await message.answer(msg.CANCELLED, reply_markup=get_main_menu())