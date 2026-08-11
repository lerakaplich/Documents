# server/bot/handlers/document_creation/tags.py

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from server.bot.keyboards.tags_kb import get_tags_keyboard
from server.bot.services.bot_repo import BotRepository
from server.bot.states.bot_states import CreateDocumentFSM

router = Router()


async def show_tags_menu(
    event: types.Message | types.CallbackQuery,
    state: FSMContext,
    bot_repo: BotRepository,
    page: int = 1
):
    """Отображает список тегов с пагинацией и кнопками выбора."""
    data = await state.get_data()
    selected_tags = set(data.get("tag_ids", []))

    # Загружаем теги и их общее кол-во из БД
    tags, total_count = await bot_repo.get_tags_paginated(page=page, per_page=6)

    keyboard = get_tags_keyboard(
        tags=tags,
        selected_tag_ids=selected_tags,
        page=page,
        total_count=total_count,
        per_page=6
    )

    text = (
        "🏷 **Выберите теги для классификации документа:**\n\n"
        "Нажимайте на теги, чтобы выбрать или снять выбор."
    )

    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(text, reply_markup=keyboard, parse_mode="Markdown")


# Переключение галочки тега
@router.callback_query(CreateDocumentFSM.waiting_for_tags, F.data.startswith("tag_toggle:"))
async def process_tag_toggle(callback: types.CallbackQuery, state: FSMContext, bot_repository: BotRepository):
    _, tag_id_str, page_str = callback.data.split(":")
    tag_id = int(tag_id_str)
    page = int(page_str)

    data = await state.get_data()
    selected_tags = set(data.get("tag_ids", []))

    if tag_id in selected_tags:
        selected_tags.remove(tag_id)
    else:
        selected_tags.add(tag_id)

    await state.update_data(tag_ids=list(selected_tags))
    await show_tags_menu(callback, state, bot_repository, page=page)


# Переключение страницы тегов
@router.callback_query(CreateDocumentFSM.waiting_for_tags, F.data.startswith("tags_page:"))
async def process_tags_page(callback: types.CallbackQuery, state: FSMContext, bot_repository: BotRepository):
    page = int(callback.data.split(":")[1])
    await show_tags_menu(callback, state, bot_repository, page=page)


# Клик по заглушке пагинации
@router.callback_query(CreateDocumentFSM.waiting_for_tags, F.data == "noop")
async def process_noop(callback: types.CallbackQuery):
    await callback.answer()


# Подтверждение выбора тегов
@router.callback_query(CreateDocumentFSM.waiting_for_tags, F.data == "tags_confirm")
async def process_tags_confirm(callback: types.CallbackQuery, state: FSMContext, bot_repository: BotRepository):
    # Импортируем локально для избежания циклических импортов
    from server.bot.handlers.step_navigator import go_to_next_step

    await callback.answer()
    await go_to_next_step(callback.message, state, bot_repository)