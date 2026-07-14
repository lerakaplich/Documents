import secrets
import bcrypt
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.employee_models import Employee
from server.bot.services import messages as msg

router = Router()


def hash_password(password: str) -> str:
    """Хэширование пароля с солью bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Приветствие и запрос номера телефона через кнопку"""
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=msg.BTN_SHARE_CONTACT, request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        msg.START_WELCOME.format(name=message.from_user.first_name),
        reply_markup=contact_keyboard
    )


@router.message(F.contact)
async def handle_contact(message: Message, emp_db: AsyncSession):
    """Обработка полученного контакта, связывание chat_id и генерация пароля"""
    contact = message.contact

    # Защита от подделки контакта
    if contact.user_id != message.from_user.id:
        await message.answer(msg.ERROR_NOT_OWNER_CONTACT)
        return

    # Приводим номер к единому формату без плюса
    phone = contact.phone_number.replace("+", "")

    # Поиск сотрудника по номеру телефона
    query = select(Employee).where(
        (Employee.phone_number == phone) |
        (Employee.phone_number == f"+{phone}")
    )
    result = await emp_db.execute(query)
    employee = result.scalar_one_or_none()

    if not employee:
        await message.answer(
            msg.ERROR_EMPLOYEE_NOT_FOUND,
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # Генерация временного пароля
    raw_password = f"SED-{secrets.token_hex(3).upper()}"
    hashed = hash_password(raw_password)

    # Обновление данных в бд кадров
    employee.chat_id = message.from_user.id
    employee.password_hash = hashed

    await emp_db.commit()

    # Отправка структурированного ответа
    await message.answer(
        msg.AUTH_SUCCESS.format(phone=phone, password=raw_password),
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )