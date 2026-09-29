from datetime import datetime

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from server.app.database.document_models import AppRights
from server.app.database.employee_models import Organization, Department
from server.app.schemas.doc.document_dto import DocumentCreateForm
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.documents.attachment_service import AttachmentService
from server.app.services.documents.document_service import DocumentService
from server.bot.keyboards.menu_kb import get_main_menu
from server.bot.middlewares.file_upload import TelegramUploadFile
from server.bot.services.bot_repo import BotRepository
from server.bot.states.bot_states import CreateDocumentFSM

router = Router()


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Создать документ", callback_data="confirm_doc_save")],
            [InlineKeyboardButton(text="❌ Отменить создание", callback_data="cancel_doc_creation")]
        ]
    )


async def show_confirmation_summary(
        message: types.Message,
        state: FSMContext,
        bot_repo: BotRepository
):
    """Формирует итоговую сводную карточку документа."""
    await state.set_state(CreateDocumentFSM.confirm_creation)
    data = await state.get_data()

    # 1. Отправитель (Сотрудник или Организация)
    sender_name = "Не указан"
    if data.get("source_employee_id"):
        emp = await bot_repo.get_employee_by_id(data["source_employee_id"])
        if emp:
            sender_name = f"{emp.last_name} {emp.first_name}"
    elif data.get("source_organization_id"):
        org = await bot_repo.emp_session.get(Organization, data["source_organization_id"])
        if org:
            sender_name = f"🏢 {org.name}"

    # 2. Получатели (Разбор DTO структуры receivers)
    recipients_names = []
    receivers = data.get("receivers", [])
    for r in receivers:
        if r.get("target_organization_id"):
            org = await bot_repo.emp_session.get(Organization, r["target_organization_id"])
            if org:
                recipients_names.append(f"🏢 {org.name}")
        elif r.get("target_department_id"):
            dept = await bot_repo.emp_session.get(Department, r["target_department_id"])
            if dept:
                recipients_names.append(f"📁 {dept.name}")
        elif r.get("employee_id"):
            emp = await bot_repo.get_employee_by_id(r["employee_id"])
            if emp:
                recipients_names.append(f"👤 {emp.last_name} {emp.first_name}")

    # 3. Исполнители
    executors_names = []
    if data.get("executors"):
        exe_list = await bot_repo.get_employees_by_ids(data["executors"])
        executors_names = [f"{e.last_name} {e.first_name}" for e in exe_list]

    # 4. Теги
    tag_names = []
    if data.get("tag_ids"):
        tags = await bot_repo.get_tags_by_ids(data["tag_ids"])
        tag_names = [f"#{t.name}" for t in tags]

    # 5. Вложения
    attachments = data.get("attachments", [])
    files_str = f"{len(attachments)} шт." if attachments else "Нет"

    summary_text = (
        "📋 **ПРОВЕРЬТЕ ДАННЫЕ ДОКУМЕНТА**\n"
        "═════════════════════════════\n\n"
        f"📌 **Заголовок:** {data.get('title', '—')}\n"
        f"📄 **Касается:** {data.get('about') or '—'}\n"
        f"📤 **Дата отправки:** {data.get('sent_date') or '—'}\n"
        f"📅 **Дедлайн:** {data.get('deadline') or '—'}\n\n"
        f"👤 **Отправитель:** {sender_name}\n"
        f"📥 **Получатели:** {', '.join(recipients_names) if recipients_names else '—'}\n"
        f"👥 **Исполнители:** {', '.join(executors_names) if executors_names else '—'}\n\n"
        f"🏷 **Теги:** {' '.join(tag_names) if tag_names else '—'}\n"
        f"📎 **Вложения:** {files_str}\n"
        "═════════════════════════════\n\n"
        "Всё верно? Нажмите кнопку для сохранения в СЭД."
    )

    await message.answer(
        summary_text,
        reply_markup=get_confirmation_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(CreateDocumentFSM.confirm_creation, F.data == "confirm_doc_save")
async def process_save_document(
    callback: types.CallbackQuery,
    state: FSMContext,
    bot_repository: BotRepository,
    document_service: DocumentService,
    attachment_service: AttachmentService
):
    await callback.answer("Регистрация документа...")
    data = await state.get_data()

    # 1. Получение текущего сотрудника из БД
    employee = await bot_repository.get_employee_by_chat_id(callback.from_user.id)
    if not employee:
        await callback.message.answer("❌ **Ошибка:** Ваш профиль Telegram не привязан к сотруднику СЭД.")
        return

    rights = getattr(employee, "rights", None)
    if not rights and hasattr(employee, "system_employee") and employee.system_employee:
        rights = employee.system_employee.rights

    current_user = CurrentUser(
        id=employee.id,
        service_number=getattr(employee, "service_number", "N/A"),
        last_name=employee.last_name,
        first_name=employee.first_name,
        patronymic=employee.patronymic,
        rights=rights or AppRights.user
    )

    try:
        # Даты
        sent_date = data.get("sent_date")
        if isinstance(sent_date, str):
            sent_date = datetime.strptime(sent_date, "%Y-%m-%d").date()

        deadline = data.get("deadline")
        if isinstance(deadline, str):
            deadline = datetime.strptime(deadline, "%Y-%m-%d").date()

        # 2. Сборка DTO сохранения документа
        payload = DocumentCreateForm(
            type_id=data["type_id"],
            direction=data["direction"],
            needs_response=data.get("needs_response", False),
            title=data.get("title"),
            about=data.get("about"),
            reg_number=data.get("reg_number"),
            sequence_number=data.get("sequence_number"),
            deadline=deadline,
            global_msg_id=data.get("global_msg_id"),
            parent_document_id=data.get("parent_document_id"),
            confident_flag=data.get("confident_flag", False),
            clearance_id=data.get("clearance_id"),
            sender_id=data.get("source_employee_id"),  # Берём сохранённого сотрудника
            executors=data.get("executors", []),
            receivers=data.get("receivers", []),        # Передаём сформированный массив receivers
            tag_ids=data.get("tag_ids", [])
        )

        new_doc = await document_service.create(payload=payload, user=current_user)

        # 3. Обработка файлов
        attachments = data.get("attachments", [])
        if attachments:
            await callback.message.edit_text("⏳ **Обработка и конвертация вложений...**")

            for att in attachments:
                file_info = await callback.bot.get_file(att["file_id"])
                file_bytes_io = await callback.bot.download_file(file_info.file_path)
                file_bytes = file_bytes_io.read()

                upload_file = TelegramUploadFile(
                    file_bytes=file_bytes,
                    filename=att["file_name"],
                    content_type=att.get("mime_type", "application/octet-stream")
                )

                await attachment_service.add_attachment(
                    doc_id=new_doc.id,
                    file=upload_file,
                    current_user=current_user,
                    sent_date=sent_date or datetime.now().date()
                )

        # 4. Завершение
        reg_info = f" № **{new_doc.reg_number}**" if getattr(new_doc, "reg_number", None) else ""
        await callback.message.edit_text(
            f"🎉 **Документ{reg_info} успешно зарегистрирован!**\n\n"
            f"ID записи в СЭД: `{new_doc.id}`",
            parse_mode="Markdown"
        )
        await state.clear()

        await callback.message.answer(
            "Вы вернулись в главное меню.",
            reply_markup=get_main_menu()
        )

    except Exception as e:
        await callback.message.answer(
            f"❌ **Ошибка при сохранении документа:**\n`{str(e)}`",
            parse_mode="Markdown"
        )