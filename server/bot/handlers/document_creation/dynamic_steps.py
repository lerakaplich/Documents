from datetime import datetime
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from server.bot.handlers.step_navigator import go_to_next_step
from server.bot.keyboards.document_create_kb import get_attachments_keyboard
from server.bot.services.bot_repo import BotRepository
from server.bot.states.bot_states import CreateDocumentFSM

router = Router()


@router.message(CreateDocumentFSM.waiting_for_title)
async def process_title_input(message: types.Message, state: FSMContext, bot_repository: BotRepository):
    title = message.text.strip() if message.text else ""
    if len(title) < 3:
        await message.answer("⚠️ Тема слишком короткая. Введите более подробную тему:")
        return

    await state.update_data(title=title)
    await go_to_next_step(message, state, bot_repository)


@router.message(CreateDocumentFSM.waiting_for_about)
async def process_about_input(message: types.Message, state: FSMContext, bot_repository: BotRepository):
    about = message.text.strip() if message.text else ""
    await state.update_data(about=about)

    await go_to_next_step(message, state, bot_repository)


@router.message(CreateDocumentFSM.waiting_for_sent_date)
async def process_sent_date_input(message: types.Message, state: FSMContext, bot_repository: BotRepository):
    date_text = message.text.strip() if message.text else ""

    try:
        valid_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        await state.update_data(sent_date=valid_date.isoformat())
    except ValueError:
        await message.answer("⚠️ Неверный формат даты! Введите дату отправки в формате `ГГГГ-ММ-ДД` (например, `2026-07-24`):")
        return

    await go_to_next_step(message, state, bot_repository)


@router.message(CreateDocumentFSM.waiting_for_deadline)
async def process_deadline_input(message: types.Message, state: FSMContext, bot_repository: BotRepository):
    date_text = message.text.strip() if message.text else ""

    try:
        valid_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        await state.update_data(deadline=valid_date.isoformat())
    except ValueError:
        await message.answer("⚠️ Неверный формат даты! Введите дату в формате `ГГГГ-ММ-ДД` (например, `2026-06-15`):")
        return

    await go_to_next_step(message, state, bot_repository)


@router.message(CreateDocumentFSM.waiting_for_sender)
async def process_sender_input(message: types.Message, state: FSMContext, bot_repository: BotRepository):
    if message.text and message.text.isdigit():
        sender_id = int(message.text.strip())
        await state.update_data(sender_id=sender_id)
        await go_to_next_step(message, state, bot_repository)
    else:
        await message.answer("⚠️ Отправьте числовой ID отправителя или воспользуйтесь выбором из списка.")


@router.message(CreateDocumentFSM.waiting_for_recipients)
async def process_recipients_input(message: types.Message, state: FSMContext, bot_repository: BotRepository):
    text = message.text.strip() if message.text else ""
    try:
        recipients = [int(x.strip()) for x in text.split(",") if x.strip().isdigit()]
        if not recipients:
            raise ValueError

        await state.update_data(recipients=recipients)
        await go_to_next_step(message, state, bot_repository)
    except ValueError:
        await message.answer("⚠️ Введите ID получателей через запятую (например: `2, 14`) или нажмите кнопку пропуска.")


@router.message(CreateDocumentFSM.waiting_for_executors)
async def process_executors_input(message: types.Message, state: FSMContext, bot_repository: BotRepository):
    text = message.text.strip() if message.text else ""
    try:
        executors = [int(x.strip()) for x in text.split(",") if x.strip().isdigit()]
        if not executors:
            raise ValueError

        await state.update_data(executors=executors)
        await go_to_next_step(message, state, bot_repository)
    except ValueError:
        await message.answer("⚠️ Введите ID исполнителей через запятую (например: `5, 8`) или нажмите кнопку пропуска.")


@router.message(CreateDocumentFSM.waiting_for_tags)
async def process_tags_input(message: types.Message, state: FSMContext, bot_repository: BotRepository):
    text = message.text.strip() if message.text else ""
    try:
        tag_ids = [int(x.strip()) for x in text.split(",") if x.strip().isdigit()]
        if not tag_ids:
            raise ValueError

        await state.update_data(tag_ids=tag_ids)
        await go_to_next_step(message, state, bot_repository)
    except ValueError:
        await message.answer("⚠️ Введите ID тегов через запятую (например: `1, 3`) или нажмите кнопку пропуска.")


@router.message(CreateDocumentFSM.waiting_for_attachments, F.document)
async def process_attachment_file(message: types.Message, state: FSMContext, bot_repository: BotRepository):
    doc = message.document
    data = await state.get_data()
    attachments = data.get("attachments", [])

    attachments.append({
        "file_id": doc.file_id,
        "file_name": doc.file_name or "document",
        "file_size": doc.file_size,
        "mime_type": doc.mime_type
    })

    await state.update_data(attachments=attachments)

    count = len(attachments)
    kb = get_attachments_keyboard(has_files=True)

    await message.answer(
        f"✅ Файл **{doc.file_name}** добавлен (всего: {count}).\n\n"
        "Вы можете отправить ещё файлы или нажать **«Завершить и продолжить»**.",
        parse_mode="Markdown",
        reply_markup=kb
    )


@router.callback_query(F.data == "attachments_finish")
async def process_attachments_finish(
    callback: types.CallbackQuery,
    state: FSMContext,
    bot_repository: BotRepository
):
    """Завершение отправки файлов и переход к итоговой карточке."""
    await callback.answer()

    # Гарантируем, что список файлов инициализирован
    data = await state.get_data()
    if "attachments" not in data:
        await state.update_data(attachments=[])

    # Переходим к следующему шагу (сводной карточке)
    await go_to_next_step(callback.message, state, bot_repository)


@router.callback_query(F.data.startswith("skip_step:"))
async def process_skip_step(callback: types.CallbackQuery, state: FSMContext, bot_repository: BotRepository):
    step_name = callback.data.split(":")[1]

    if step_name == "about":
        await state.update_data(about=None)
    elif step_name == "sent_date":
        await state.update_data(sent_date=None)
    elif step_name == "deadline":
        await state.update_data(deadline=None)
    elif step_name in ("recipients", "executors", "tag_ids", "attachments"):
        await state.update_data({step_name: []})

    await callback.answer("Шаг пропущен")
    await go_to_next_step(callback.message, state, bot_repository)