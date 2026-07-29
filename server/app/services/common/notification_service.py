# server/app/services/notification_service.py
import logging
from typing import List, Optional
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramAPIError
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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

    async def notify_status_changed(self, doc_id: int, old_status: str, new_status: str, actor_id: int):
        """3. При смене статуса — всем участникам"""
        doc = await self.doc_repo.get_by_id(doc_id)
        if not doc:
            return

        participants = await self.doc_repo.get_document_participants_dto(doc_id)
        target_emp_ids = [emp_id for emp_id in participants.all_unique_ids if emp_id != actor_id]

        chat_map = await self.emp_repo.get_chat_ids_by_employee_ids(target_emp_ids)

        text = (
            f"🔄 <b>Изменение статуса документа №{doc.reg_number or doc.id}</b>\n\n"
            f"<b>Новый статус:</b> {new_status}"
        )

        for chat_id in chat_map.values():
            await self._send_safe(chat_id, text)

    async def notify_delegation_changed(
            self,
            doc_id: int,
            delegator_id: int,
            delegatee_id: int,
            is_granted: bool
    ):
        """4. При делегировании прав или их отзыве"""
        doc = await self.doc_repo.get_by_id(doc_id)
        if not doc:
            return

        # Уведомляем непосредственно делегата
        delegatee_map = await self.emp_repo.get_chat_ids_by_employee_ids([delegatee_id])
        delegatee_chat_id = delegatee_map.get(delegatee_id)

        if delegatee_chat_id:
            action_str = "предоставлен" if is_granted else "отозван"
            text_for_delegatee = (
                f"🔑 <b>Доступ к документу №{doc.reg_number or doc.id} {action_str}</b>\n\n"
                f"Вам {'делегированы права' if is_granted else 'закрыт доступ'} по данному документу."
            )
            await self._send_safe(delegatee_chat_id, text_for_delegatee)

    async def notify_overtime_announcement(self, announcement_text: str):
        """5. Рассылка по переработкам — вообще всем людям"""
        all_chat_ids = await self.emp_repo.get_all_active_chat_ids()

        text = (
            f"⏰ <b>Информация о переработках</b>\n\n"
            f"{announcement_text}"
        )

        for chat_id in all_chat_ids:
            await self._send_safe(chat_id, text)