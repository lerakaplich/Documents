from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from server.bot.keyboards.document_create_kb import get_types_keyboard
from server.bot.keyboards.menu_kb import get_main_menu
from server.bot.services.bot_repo import BotRepository
from server.bot.states.bot_states import CreateDocumentFSM

router = Router()


@router.message(F.text == "❌ Отмена")
@router.callback_query(F.data == "cancel_doc_creation")
async def cancel_handler(event: types.Message | types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()

    if isinstance(event, types.CallbackQuery):
        await event.answer()
        await event.message.answer("❌ Действие отменено.", reply_markup=get_main_menu())
    else:
        await event.answer("❌ Действие отменено.", reply_markup=get_main_menu())


@router.message(F.text == "Новый документ")
async def start_create_document(message: types.Message, state: FSMContext, doc_session: AsyncSession):
    bot_repo = BotRepository(doc_session)
    types_list = await bot_repo.get_all_types()

    if not types_list:
        await message.answer("⚠️ В системе пока нет зарегистрированных типов документов.")
        return

    type_map = {t.name: t.id for t in types_list}
    await state.update_data(type_map=type_map)
    await state.set_state(CreateDocumentFSM.waiting_for_type)

    await message.answer(
        "📄 **Шаг 1: Выбор типа документа**\n\n"
        "Выберите тип создаваемого документа из списка ниже:",
        reply_markup=get_types_keyboard(types_list),
        parse_mode="Markdown"
    )


@router.message(CreateDocumentFSM.waiting_for_type)
async def process_type_selection(message: types.Message, state: FSMContext, doc_session: AsyncSession):
    data = await state.get_data()
    type_map = data.get("type_map", {})
    selected_type_name = message.text.strip() if message.text else ""

    if selected_type_name not in type_map:
        await message.answer("⚠️ Пожалуйста, выберите тип документа с помощью кнопок!")
        return

    type_id = type_map[selected_type_name]
    bot_repo = BotRepository(doc_session)
    doc_type = await bot_repo.get_type_by_id(type_id)

    await state.update_data(
        type_id=type_id,
        type_name=selected_type_name,
        auto_num=doc_type.auto_num if doc_type else True,
        type_fields_config=doc_type.fields if (doc_type and doc_type.fields) else {}
    )

    await state.set_state(CreateDocumentFSM.waiting_for_direction)

    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Внутренний", callback_data="direction:internal")
    builder.button(text="📨 Входящий / Внешний", callback_data="direction:external")
    builder.adjust(2)

    await message.answer(
        f"✅ Выбран тип: **{selected_type_name}**\n\n"
        "**Шаг 2: Направление документа**\n"
        "Выберите направление:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )