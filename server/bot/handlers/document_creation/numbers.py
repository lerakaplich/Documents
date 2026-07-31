from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.document_models import DocDirection
from server.app.deps import get_doc_service
from server.bot.handlers.step_navigator import go_to_next_step
from server.bot.keyboards.menu_kb import get_cancel_keyboard
from server.bot.services.bot_repo import BotRepository
from server.bot.services.utils import build_doc_service_for_bot
from server.bot.states.bot_states import CreateDocumentFSM

router = Router()


# ШАГ 2.1: Обработка выбранного направления -> Генерация Порядкового номера
@router.callback_query(F.data.startswith("direction:"), CreateDocumentFSM.waiting_for_direction)
async def process_direction_selection(
    callback: types.CallbackQuery,
    state: FSMContext,
    doc_session: AsyncSession,
    emp_session: AsyncSession,
    internal_user_id: int,  # 👈 Автоматически из EmployeeAuthMiddleware
    department_id: int | None  # 👈 Автоматически из EmployeeAuthMiddleware
):
    direction_str = callback.data.split(":")[1]
    await state.update_data(
        direction=direction_str,
        department_id=department_id
    )
    await callback.answer()

    data = await state.get_data()
    type_id: int = data.get("type_id")
    direction_enum = DocDirection(direction_str)

    # Получаем бизнес-сервис
    doc_service = await build_doc_service_for_bot(db_docs=doc_session, db_emp=emp_session)

    # Вызываем расчет предложенных номеров с РЕАЛЬНЫМ internal_user_id из базы кадров
    proposed_res = await doc_service.generate_proposed_number(
        type_id=type_id,
        direction=direction_enum,
        user_id=internal_user_id
    )

    next_seq_num = proposed_res.sequence_number
    await state.update_data(
        suggested_seq_num=next_seq_num,
        suggested_reg_num=proposed_res.proposed_number
    )

    await state.set_state(CreateDocumentFSM.waiting_for_sequence_num)

    builder = InlineKeyboardBuilder()
    builder.button(text=f"✅ Использовать {next_seq_num}", callback_data="use_suggested_seq_num")
    builder.button(text="❌ Отмена", callback_data="cancel_doc_creation")
    builder.adjust(1)

    await callback.message.answer(
        f"🔢 **Порядковый номер документа**\n\n"
        f"Предлагаемый номер: `{next_seq_num}`\n\n"
        "Нажмите кнопку, чтобы использовать его, или **введите другой номер вручную**:",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )


# ШАГ 2.2: Сохранение Порядкового номера
@router.callback_query(F.data == "use_suggested_seq_num", CreateDocumentFSM.waiting_for_sequence_num)
async def process_suggested_seq_num(
        callback: types.CallbackQuery,
        state: FSMContext,
        doc_session: AsyncSession,
        emp_session: AsyncSession
):
    data = await state.get_data()
    seq_num = data.get("suggested_seq_num")
    await state.update_data(sequence_number=seq_num)
    await callback.answer()

    await ask_reg_number(callback.message, state)


@router.message(CreateDocumentFSM.waiting_for_sequence_num)
async def process_manual_seq_num(
        message: types.Message,
        state: FSMContext
):
    if not message.text or not message.text.isdigit():
        await message.answer("⚠️ Порядковый номер должен состоять только из цифр. Попробуйте еще раз:")
        return

    seq_num = int(message.text.strip())
    await state.update_data(sequence_number=seq_num)

    await ask_reg_number(message, state)

async def ask_reg_number(
    message: types.Message,
    state: FSMContext
):
    data = await state.get_data()
    gen_reg_num = data.get("suggested_reg_num")

    await state.set_state(CreateDocumentFSM.waiting_for_reg_num)

    if gen_reg_num:
        builder = InlineKeyboardBuilder()
        builder.button(text=f"✅ Использовать {gen_reg_num}", callback_data="use_suggested_reg_num")
        builder.button(text="❌ Отмена", callback_data="cancel_doc_creation")
        builder.adjust(1)

        await message.answer(
            f"📋 **Регистрационный номер** (Автоматический режим)\n\n"
            f"Сгенерирован номер: `{gen_reg_num}`\n\n"
            "Нажмите кнопку ниже или **введите свой номер вручную**:",
            parse_mode="Markdown",
            reply_markup=builder.as_markup()
        )
    else:
        await message.answer(
            "📋 **Регистрационный номер**\n\n"
            "Для данного типа документа автогенерация отключена.\n"
            "**Введите регистрационный номер документа вручную:**",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard()
        )


# ШАГ 2.3: Сохранение Регистрационного номера -> Вызов go_to_next_step
@router.callback_query(F.data == "use_suggested_reg_num", CreateDocumentFSM.waiting_for_reg_num)
async def process_suggested_reg_num(
    callback: types.CallbackQuery,
    state: FSMContext
):
    data = await state.get_data()
    reg_num = data.get("suggested_reg_num")
    await state.update_data(reg_number=reg_num)
    await callback.answer()

    await ask_needs_response(callback.message, state)


@router.message(CreateDocumentFSM.waiting_for_reg_num)
async def process_manual_reg_num(
    message: types.Message,
    state: FSMContext
):
    reg_num = message.text.strip() if message.text else ""
    if not reg_num:
        await message.answer("⚠️ Регистрационный номер не может быть пустым.")
        return

    await state.update_data(reg_number=reg_num)

    await ask_needs_response(message, state)

async def ask_needs_response(
    message: types.Message,
    state: FSMContext
):
    """Обязательный шаг: Уточнение, требуется ли ответ на документ"""
    await state.set_state(CreateDocumentFSM.waiting_for_needs_response)

    builder = InlineKeyboardBuilder()
    builder.button(text="❓ Да, требуется", callback_data="needs_resp:yes")
    builder.button(text="🚫 Нет, не требуется", callback_data="needs_resp:no")
    builder.button(text="❌ Отмена", callback_data="cancel_doc_creation")
    builder.adjust(2, 1)

    await message.answer(
        "📩 **Требуется ли ответ на данный документ?**\n\n"
        "Укажите, ожидается ли официальный ответ/отклик от получателей:",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )


# ШАГ 2.4: Сохранение флага needs_response -> Переход к динамическим шагам
@router.callback_query(F.data.startswith("needs_resp:"), CreateDocumentFSM.waiting_for_needs_response)
async def process_needs_response_selection(
    callback: types.CallbackQuery,
    state: FSMContext,
    doc_session: AsyncSession,
    emp_session: AsyncSession
):
    resp_choice = callback.data.split(":")[1]
    needs_response_val = (resp_choice == "yes")

    # Сохраняем флаг в FSM
    await state.update_data(needs_response=needs_response_val)
    await callback.answer()

    # Переходим к следующему шагу (к динамическим полям типа title, about, deadline и т.д.)
    bot_repo = BotRepository(doc_session=doc_session, emp_session=emp_session)
    await go_to_next_step(callback.message, state, bot_repo)