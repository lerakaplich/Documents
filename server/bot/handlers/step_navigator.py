from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from server.bot.handlers.document_creation.confirmation import show_confirmation_summary
from server.bot.handlers.document_creation.participants import show_org_tree
from server.bot.handlers.document_creation.tags import show_tags_menu
from server.bot.keyboards.document_create_kb import get_skip_or_cancel_keyboard, get_cancel_keyboard, \
    get_attachments_keyboard
from server.bot.services.bot_repo import BotRepository
from server.bot.states.bot_states import CreateDocumentFSM

async def go_to_next_step(message: Message, state: FSMContext, bot_repository: BotRepository):
    """
    Глобальный диспетчер: анализирует JSONB-конфигурацию типа документа
    и запрашивает только те поля, которые установлены в true.
    Вложения (attachments) проверяются всегда в самом конце.
    """
    data = await state.get_data()

    # Считываем JSONB-словарь флагов для текущего типа документа
    # Пример: {"title": true, "about": true, "deadline": true, "executors": true, ...}
    fields_config: dict[str, bool] = data.get("type_fields_config", {})

    # =========================================================================
    # ДИНАМИЧЕСКИЕ ПОЛЯ (из JSONB types.fields)
    # =========================================================================

    # 1. Тема / Заголовок (title)
    if fields_config.get("title", False) and "title" not in data:
        await state.set_state(CreateDocumentFSM.waiting_for_title)
        await message.answer(
            "📝 **Введите тему (заголовок) документа:**\n\n"
            "_Кратко опишите суть документа._",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard()
        )
        return

    # 2. Касается / Содержание (about)
    if fields_config.get("about", False) and "about" not in data:
        await state.set_state(CreateDocumentFSM.waiting_for_about)
        await message.answer(
            "📄 **Введите подробное содержание / «Касается»:**",
            parse_mode="Markdown",
            reply_markup=get_skip_or_cancel_keyboard("about")
        )
        return

    # 3. Дата отправки (sent_date)
    if fields_config.get("sent_date", False) and "sent_date" not in data:
        await state.set_state(CreateDocumentFSM.waiting_for_sent_date)
        await message.answer(
            "📤 **Укажите дату отправки:**\n\n"
            "Введите дату в формате `ГГГГ-ММ-ДД`:",
            parse_mode="Markdown",
            reply_markup=get_skip_or_cancel_keyboard("sent_date")
        )
        return

    # 4. Дедлайн / Срок исполнения (deadline)
    if fields_config.get("deadline", False) and "deadline" not in data:
        await state.set_state(CreateDocumentFSM.waiting_for_deadline)
        await message.answer(
            "📅 **Укажите срок исполнения (дедлайн):**\n\n"
            "Введите дату в формате `ГГГГ-ММ-ДД` (например, `2026-06-15`):",
            parse_mode="Markdown",
            reply_markup=get_skip_or_cancel_keyboard("deadline")
        )
        return

    # 5. Отправитель (sender_id) — запуск дерева выбора
    if fields_config.get("sender_id", False) and "sender_id" not in data:
        await state.set_state(CreateDocumentFSM.waiting_for_sender)
        await show_org_tree(
            event=message,
            state=state,
            bot_repo=bot_repository,
            target_role="sender"
        )
        return

    # 6. Получатели (recipients) — запуск дерева выбора
    if fields_config.get("recipients", False) and "recipients" not in data:
        await state.set_state(CreateDocumentFSM.waiting_for_recipients)
        await show_org_tree(
            event=message,
            state=state,
            bot_repo=bot_repository,
            target_role="recipients"
        )
        return

    # 7. Исполнители (executors) — запуск дерева выбора
    if fields_config.get("executors", False) and "executors" not in data:
        await state.set_state(CreateDocumentFSM.waiting_for_executors)
        await show_org_tree(
            event=message,
            state=state,
            bot_repo=bot_repository,
            target_role="executors"
        )
        return

    # 8. Теги (tag_ids)
    if fields_config.get("tag_ids", False) and "tag_ids" not in data:
        await state.set_state(CreateDocumentFSM.waiting_for_tags)
        await show_tags_menu(
            event=message,
            state=state,
            bot_repo=bot_repository,
            page=1
        )
        return

    # =========================================================================
    # ОБЯЗАТЕЛЬНЫЙ ФИНАЛЬНЫЙ ШАГ БАЗИСА
    # =========================================================================

    # 9. Вложения (attachments) — Всегда запрашиваются в конце
    if "attachments" not in data:
        await state.set_state(CreateDocumentFSM.waiting_for_attachments)
        await message.answer(
            "📎 **Прикрепите файлы к документу:**\n\n"
            "Отправляйте файлы по одному. Когда закончите — нажмите кнопку ниже.",
            reply_markup=get_attachments_keyboard(has_files=False),
            parse_mode="Markdown"
        )
        return

    # Все требуемые поля собраны — переход к подтверждению
    await state.set_state(CreateDocumentFSM.confirm_creation)
    await show_confirmation_summary(message, state, bot_repository)