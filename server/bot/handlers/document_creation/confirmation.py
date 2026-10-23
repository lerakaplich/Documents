import html
import logging
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

logger = logging.getLogger(__name__)

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

    # 2. Получатели
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

    # ---- Экранируем всё пользовательское / пришедшее из БД ----
    title_safe = html.escape(str(data.get("title") or "—"))
    about_safe = html.escape(str(data.get("about") or "—"))
    sent_date_safe = html.escape(str(data.get("sent_date") or "—"))
    deadline_safe = html.escape(str(data.get("deadline") or "—"))
    sender_safe = html.escape(sender_name)
    recipients_safe = html.escape(", ".join(recipients_names) if recipients_names else "—")
    executors_safe = html.escape(", ".join(executors_names) if executors_names else "—")
    tags_safe = html.escape(" ".join(tag_names) if tag_names else "—")
    files_safe = html.escape(files_str)

    summary_text = (
        "📋 <b>ПРОВЕРЬТЕ ДАННЫЕ ДОКУМЕНТА</b>\n"
        "═════════════════════════════\n\n"
        f"📌 <b>Заголовок:</b> {title_safe}\n"
        f"📄 <b>Касается:</b> {about_safe}\n"
        f"📤 <b>Дата отправки:</b> {sent_date_safe}\n"
        f"📅 <b>Дедлайн:</b> {deadline_safe}\n\n"
        f"👤 <b>Отправитель:</b> {sender_safe}\n"
        f"📥 <b>Получатели:</b> {recipients_safe}\n"
        f"👥 <b>Исполнители:</b> {executors_safe}\n\n"
        f"🏷 <b>Теги:</b> {tags_safe}\n"
        f"📎 <b>Вложения:</b> {files_safe}\n"
        "═════════════════════════════\n\n"
        "Всё верно? Нажмите кнопку для сохранения в СЭД."
    )

    await message.answer(
        summary_text,
        reply_markup=get_confirmation_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(CreateDocumentFSM.confirm_creation, F.data == "confirm_doc_save")
async def process_save_document(
    callback: types.CallbackQuery,
    state: FSMContext,
    bot_repo: BotRepository,
    document_service: DocumentService,
    attachment_service: AttachmentService
):
    await callback.answer("Регистрация документа...")
    data = await state.get_data()

    # 1. Получение текущего сотрудника из БД
    employee = await bot_repo.get_employee_by_chat_id(callback.from_user.id)
    if not employee:
        await callback.message.answer(
            "❌ <b>Ошибка:</b> Ваш профиль Telegram не привязан к сотруднику СЭД.",
            parse_mode="HTML"
        )
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
        # Отправитель передаётся ровно так, как его сохранил participants.py:
        # либо source_employee_id, либо source_organization_id (одно из двух).
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
            source_employee_id=data.get("source_employee_id"),
            source_organization_id=data.get("source_organization_id"),
            executors=data.get("executors", []),
            receivers=data.get("receivers", []),
            tag_ids=data.get("tag_ids", [])
        )

        new_doc = await document_service.create(payload=payload, user=current_user)

        # 3. Обработка файлов
        attachments = data.get("attachments", [])
        if attachments:
            await callback.message.edit_text(
                "⏳ <b>Обработка и конвертация вложений...</b>",
                parse_mode="HTML"
            )

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
        if getattr(new_doc, "reg_number", None):
            reg_info = f" № <b>{html.escape(str(new_doc.reg_number))}</b>"
        else:
            reg_info = ""

        await callback.message.edit_text(
            f"🎉 <b>Документ{reg_info} успешно зарегистрирован!</b>\n\n"
            f"ID записи в СЭД: <code>{new_doc.id}</code>",
            parse_mode="HTML"
        )
        await state.clear()

        await callback.message.answer(
            "Вы вернулись в главное меню.",
            reply_markup=get_main_menu()
        )

    except Exception:
        # Полный стектрейс — только в лог
        logger.exception(
            "Не удалось сохранить документ (user_id=%s, chat_id=%s)",
            current_user.id, callback.from_user.id
        )
        # Пользователю — нейтральный текст без деталей исключения
        await callback.message.answer(
            "❌ <b>Не удалось сохранить документ.</b>\n\n"
            "Попробуйте позже или обратитесь к администратору. "
            "Данные формы сохранены — можно повторить попытку.",
            parse_mode="HTML"
        )