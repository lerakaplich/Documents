# server/app/services/notification_service.py
import logging
from typing import Optional
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramAPIError
from aiogram.types import InlineKeyboardMarkup

from server.app.database.document_models import DocStatus
from server.app.repositories.document_repo import DocumentRepository
from server.app.repositories.employee_repo import EmployeesRepository

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
            self,
            bot: Bot,
            emp_repo: EmployeesRepository,
            doc_repo: DocumentRepository
    ):
        self.bot = bot
        self.emp_repo = emp_repo
        self.doc_repo = doc_repo

    async def _send_safe(
            self,
            chat_id: int,
            text: str,
            reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """Безопасная отправка с обработкой ошибок Telegram API"""
        if not self.bot:
            logger.debug("Telegram Bot не инициализирован, отправка пропущена.")
            return False

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return True
        except TelegramForbiddenError:
            logger.warning(f"Пользователь с chat_id={chat_id} заблокировал бота.")
        except TelegramAPIError as e:
            logger.error(f"Ошибка Telegram API при отправке на chat_id={chat_id}: {e}")
        except Exception as e:
            logger.exception(f"Непредвиденная ошибка при отправке уведомления на chat_id={chat_id}: {e}")
        return False

    async def notify_document_created(self, doc_id: int, actor_id: int):
        """Отправка уведомлений о новом документе исполнителям и получателям"""
        doc = await self.doc_repo.get_by_id(doc_id)
        if not doc:
            return

        participants = await self.doc_repo.get_document_participants_dto(doc_id)

        # Получатели уведомления: исполнители и получатели, исключая самого создателя
        target_emp_ids = [
            emp_id for emp_id in set(participants.executors + participants.recipients)
            # if emp_id != actor_id
        ]

        if not target_emp_ids:
            return

        chat_map = await self.emp_repo.get_chat_ids_by_employee_ids(target_emp_ids)
        if not chat_map:
            return

        reg_num = doc.reg_number or f"ID {doc.id}"
        text = (
            f"📄 <b>Новый документ №{reg_num}</b>\n\n"
            f"<b>Заголовок:</b> {doc.title}\n"
            f"Вам поступил новый документ на исполнение/ознакомление."
        )

        for chat_id in chat_map.values():
            await self._send_safe(chat_id, text)


    async def notify_comment_added(self, doc_id: int, author_id: int, comment_text: str):
        """2. При добавлении комментария — всем участникам (включая делегатов), кроме автора"""
        doc = await self.doc_repo.get_by_id(doc_id)
        if not doc:
            return

        participants = await self.doc_repo.get_document_participants_dto(doc_id)
        # Все участники за исключением автора комментария
        target_emp_ids = [emp_id for emp_id in participants.all_unique_ids if emp_id != author_id]

        chat_map = await self.emp_repo.get_chat_ids_by_employee_ids(target_emp_ids)

        text = (
            f"💬 <b>Новый комментарий к документу №{doc.reg_number or doc.id}</b>\n\n"
            f"<b>Текст:</b> <i>«{comment_text}»</i>"
        )

        for chat_id in chat_map.values():
            await self._send_safe(chat_id, text)

    async def notify_status_changed(
            self,
            doc_id: int,
            new_status: DocStatus,
            actor_id: Optional[int] = None
    ):
        """
        Уведомление об изменении статуса документа.
        Отправляется всем участникам (кроме инициатора действия)
        ТОЛЬКО при переходе в финальные статусы: approved или rejected.
        """
        # Фильтруем статус — отправляем только для утвержденных и отклоненных документов
        if new_status not in (DocStatus.approved, DocStatus.rejected):
            return

        doc = await self.doc_repo.get_by_id(doc_id)
        if not doc:
            return

        participants = await self.doc_repo.get_document_participants_dto(doc_id)

        # Исключаем инициатора (actor_id), если он указан
        target_emp_ids = [
            emp_id for emp_id in participants.all_unique_ids
            if actor_id is None or emp_id != actor_id
        ]

        if not target_emp_ids:
            return

        chat_map = await self.emp_repo.get_chat_ids_by_employee_ids(target_emp_ids)
        if not chat_map:
            return

        reg_num = doc.reg_number or f"ID {doc.id}"

        # Красивые эмодзи и понятные статусы для пользователей
        if new_status == DocStatus.approved:
            status_text = "🟢 <b>Утвержден</b>"
        else:  # rejected
            status_text = "🔴 <b>Отклонен</b>"

        text = (
            f"📋 <b>Изменение статуса документа №{reg_num}</b>\n\n"
            f"<b>Новый статус:</b> {status_text}"
        )

        for chat_id in chat_map.values():
            await self._send_safe(chat_id, text)

    async def notify_delegation_changed(
        self,
        doc_id: int,
        delegatee_id: int,
        is_granted: bool,
        message: Optional[str] = None
    ):
        """Уведомление непосредственно делегату при назначении или отзыве доступа"""
        doc = await self.doc_repo.get_by_id(doc_id)
        if not doc:
            return

        delegatee_map = await self.emp_repo.get_chat_ids_by_employee_ids([delegatee_id])
        delegatee_chat_id = delegatee_map.get(delegatee_id)

        if not delegatee_chat_id:
            return

        reg_num = doc.reg_number or f"ID {doc.id}"

        if is_granted:
            text = (
                f"🔑 <b>Вам делегирован доступ к документу №{reg_num}</b>\n\n"
                f"Вам предоставили права на просмотр и согласование данного документа."
            )
            if message and message.strip():
                text += f"\n\n<b>Сопроводительное сообщение:</b> <i>«{message.strip()}»</i>"
        else:
            text = (
                f"🚫 <b>Отозван доступ к документу №{reg_num}</b>\n\n"
                f"Ваш доступ к данному документу был отозван."
            )

        await self._send_safe(delegatee_chat_id, text)

    async def notify_overtimes_imported(self, employee_ids: set[int]):
        """
        Массовое рассылочное уведомление сотрудникам,
        у которых появились новые импортированные переработки.
        """
        if not employee_ids:
            return

        # Получаем chat_id только тех сотрудников, кому начислили переработки
        chat_map = await self.emp_repo.get_chat_ids_by_employee_ids(list(employee_ids))
        if not chat_map:
            return

        text = (
            "⏰ <b>Обновление данных по переработкам</b>\n\n"
            "В систему импортированы новые записи о ваших переработках.\n"
            "Вы можете проверить обновленную информацию в своем личном кабинете."
        )

        # Рассылаем каждому адресату
        for chat_id in chat_map.values():
            await self._send_safe(chat_id, text)