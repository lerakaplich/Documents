import secrets
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command, StateFilter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.employee_models import Employee
from server.bot.keyboads.menu_kb import get_main_menu
from server.bot.services import messages as msg
from server.bot.services.utils import hash_password

router = Router()


@router.message(CommandStart())
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, emp_db: AsyncSession):
    """
    Единый обработчик команды /start.
    Проверяет, авторизован ли пользователь, и выдает соответствующий интерфейс.
    """
    await state.clear()  # На всякий случай сбрасываем любые зависшие состояния FSM

    # Ищем сотрудника в БД по его Telegram chat_id
    query = select(Employee).where(Employee.chat_id == message.from_user.id)
    result = await emp_db.execute(query)
    employee = result.scalar_one_or_none()

    # СЦЕНАРИЙ 1: Пользователь уже авторизован
    if employee:
        await message.answer(
            "👋 Рад приветствовать вас в мобильном помощнике СЭД!\n"
            "Используйте кнопки меню внизу для работы с документами.",
            reply_markup=get_main_menu()
        )
        return

    # СЦЕНАРИЙ 2: Новый пользователь (нужна привязка телефона)
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

    # Отправка структурированного ответа с выдачей ГЛАВНОГО МЕНЮ
    await message.answer(
        msg.AUTH_SUCCESS.format(phone=phone, password=raw_password),
        parse_mode="HTML",
        reply_markup=get_main_menu()  # Сразу даем ему рабочую клавиатуру
    )


# --- ГЛОБАЛЬНАЯ ОТМЕНА ---

@router.message(Command("cancel"), StateFilter("*"))
@router.message(F.text.casefold() == "❌ отмена", StateFilter("*"))
@router.message(F.text.casefold() == "отмена", StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext):
    """
    Прерывает любой пошаговый процесс, очищает FSM-контекст
    и возвращает пользователя в главное меню.
    """
    current_state = await state.get_state()

    if current_state is None:
        await message.answer(
            "В данный момент вы нигде не находитесь. Всё спокойно!",
            reply_markup=get_main_menu()
        )
        return

    # Если состояние было активным — сбрасываем его
    await state.clear()
    await message.answer(
        "Действие отменено. Возвращаю вас в главное меню.",
        reply_markup=get_main_menu()
    )