# server/app/services/notification_service.py
import asyncio
import html
import logging
from typing import Optional
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramAPIError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from server.app.database.document_models import DocStatus
from server.app.repositories.document_repo import DocumentRepository
from server.app.repositories.employee_repo import EmployeesRepository

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
            self,
            bot: Optional[Bot],
            session_docs_factory: async_sessionmaker[AsyncSession],
            session_emp_factory: async_sessionmaker[AsyncSession]
    ):
        self.bot = bot
        self.session_docs_factory = session_docs_factory
        self.session_emp_factory = session_emp_factory

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
            logger.warning(
                f"Notification skipped: User with chat_id={chat_id} blocked the bot",
                extra={"event_type": "tg_bot_blocked", "chat_id": chat_id}
            )
        except TelegramRetryAfter as e:
            logger.warning(
                f"Telegram rate limit hit for chat_id={chat_id}. Sleeping for {e.timeout}s",
                extra={"event_type": "tg_rate_limit", "chat_id": chat_id, "retry_after": e.timeout}
            )
            await asyncio.sleep(e.timeout)
            return await self._send_safe(chat_id, text, reply_markup)
        except TelegramAPIError as e:
            logger.error(
                f"Telegram API error when sending to chat_id={chat_id}: {e}",
                extra={"event_type": "tg_api_error", "chat_id": chat_id, "error_details": str(e)}
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error when sending notification to chat_id={chat_id}: {e}",
                extra={"event_type": "tg_send_exception", "chat_id": chat_id}
            )
        return False

    async def _broadcast_messages(self, chat_ids: list[int], text: str) -> int:
        """Вспомогательный метод для ведения рассылок с соблюдением лимитов Telegram API"""
        sent_count = 0
        for chat_id in chat_ids:
            if await self._send_safe(chat_id, text):
                sent_count += 1
            await asyncio.sleep(0.05)
        return sent_count

    async def notify_document_created(self, doc_id: int, actor_id: int):
        # Отдельная короткая сессия для БД документов
        async with self.session_docs_factory() as session_docs:
            doc_repo = DocumentRepository(session_docs)
            doc = await doc_repo.get_by_id(doc_id)
            if not doc:
                return
            participants = await doc_repo.get_document_participants_dto(doc_id)

        target_emp_ids = [
            emp_id for emp_id in set(participants.executors + participants.recipients)
            if emp_id != actor_id
        ]
        if not target_emp_ids:
            return

        # Отдельная короткая сессия для кадровой БД
        async with self.session_emp_factory() as session_emp:
            emp_repo = EmployeesRepository(session_emp)
            chat_map = await emp_repo.get_chat_ids_by_employee_ids(target_emp_ids)

        if not chat_map:
            return

        # Рассылка в Telegram (Обе сессии уже закрыты)
        reg_num = doc.reg_number or f"ID {doc.id}"
        escaped_title = html.escape(doc.title or "")

        text = (
            f"📄 <b>Новый документ №{reg_num}</b>\n\n"
            f"<b>Заголовок:</b> {escaped_title}\n"
            f"Вам поступил новый документ на исполнение/ознакомление."
        )

        await self._broadcast_messages(list(chat_map.values()), text)

    async def notify_comment_added(self, doc_id: int, author_id: int, comment_text: str):
        """При добавлении комментария — всем участникам, кроме автора"""
        async with self.session_docs_factory() as session_docs:
            doc_repo = DocumentRepository(session_docs)
            doc = await doc_repo.get_by_id(doc_id)
            if not doc:
                logger.warning(
                    f"Notification 'comment_added' skipped: Document doc_id={doc_id} not found",
                    extra={"event_type": "notify_doc_not_found", "doc_id": doc_id}
                )
                return

            participants = await doc_repo.get_document_participants_dto(doc_id)

        target_emp_ids = [emp_id for emp_id in participants.all_unique_ids if emp_id != author_id]

        if not target_emp_ids:
            return

        async with self.session_emp_factory() as session_emp:
            emp_repo = EmployeesRepository(session_emp)
            chat_map = await emp_repo.get_chat_ids_by_employee_ids(target_emp_ids)

        if not chat_map:
            return

        escaped_comment = html.escape(comment_text or "")
        reg_num = doc.reg_number or doc.id

        text = (
            f"💬 <b>Новый комментарий к документу №{reg_num}</b>\n\n"
            f"<b>Текст:</b> <i>«{escaped_comment}»</i>"
        )

        sent_count = await self._broadcast_messages(list(chat_map.values()), text)
        logger.info(
            f"Sent 'comment_added' notifications for doc_id={doc_id} ({sent_count}/{len(chat_map)} delivered)",
            extra={
                "event_type": "notify_comment_added",
                "doc_id": doc_id,
                "author_id": author_id,
                "delivered": sent_count
            }
        )

    async def notify_status_changed(
            self,
            doc_id: int,
            new_status: DocStatus,
            actor_id: Optional[int] = None
    ):
        """Уведомление об изменении статуса документа (approved или rejected)"""
        if new_status not in (DocStatus.approved, DocStatus.rejected):
            return

        async with self.session_docs_factory() as session_docs:
            doc_repo = DocumentRepository(session_docs)
            doc = await doc_repo.get_by_id(doc_id)
            if not doc:
                logger.warning(
                    f"Notification 'status_changed' skipped: Document doc_id={doc_id} not found",
                    extra={"event_type": "notify_doc_not_found", "doc_id": doc_id}
                )
                return

            participants = await doc_repo.get_document_participants_dto(doc_id)

        target_emp_ids = [
            emp_id for emp_id in participants.all_unique_ids
            if actor_id is None or emp_id != actor_id
        ]

        if not target_emp_ids:
            return

        async with self.session_emp_factory() as session_emp:
            emp_repo = EmployeesRepository(session_emp)
            chat_map = await emp_repo.get_chat_ids_by_employee_ids(target_emp_ids)

        if not chat_map:
            return

        reg_num = doc.reg_number or f"ID {doc.id}"
        status_text = "🟢 <b>Утвержден</b>" if new_status == DocStatus.approved else "🔴 <b>Отклонен</b>"

        text = (
            f"📋 <b>Изменение статуса документа №{reg_num}</b>\n\n"
            f"<b>Новый статус:</b> {status_text}"
        )

        sent_count = await self._broadcast_messages(list(chat_map.values()), text)
        logger.info(
            f"Sent 'status_changed' notifications for doc_id={doc_id} status={new_status.value} ({sent_count}/{len(chat_map)} delivered)",
            extra={
                "event_type": "notify_status_changed",
                "doc_id": doc_id,
                "new_status": new_status.value,
                "delivered": sent_count
            }
        )

    async def notify_delegation_changed(
        self,
        doc_id: int,
        delegatee_id: int,
        is_granted: bool,
        message: Optional[str] = None
    ):
        """Уведомление непосредственно делегату при назначении или отзыве доступа"""
        async with self.session_docs_factory() as session_docs:
            doc_repo = DocumentRepository(session_docs)
            doc = await doc_repo.get_by_id(doc_id)
            if not doc:
                logger.warning(
                    f"Notification 'delegation_changed' skipped: Document doc_id={doc_id} not found",
                    extra={"event_type": "notify_doc_not_found", "doc_id": doc_id}
                )
                return

        async with self.session_emp_factory() as session_emp:
            emp_repo = EmployeesRepository(session_emp)
            delegatee_map = await emp_repo.get_chat_ids_by_employee_ids([delegatee_id])

        delegatee_chat_id = delegatee_map.get(delegatee_id)

        if not delegatee_chat_id:
            logger.debug(
                f"No Telegram chat_id found for delegatee_id={delegatee_id} on doc_id={doc_id}",
                extra={"event_type": "notify_no_chat_ids", "doc_id": doc_id, "delegatee_id": delegatee_id}
            )
            return

        reg_num = doc.reg_number or f"ID {doc.id}"

        if is_granted:
            text = (
                f"🔑 <b>Вам делегирован доступ к документу №{reg_num}</b>\n\n"
                f"Вам предоставили права на просмотр и согласование данного документа."
            )
            if message and message.strip():
                escaped_msg = html.escape(message.strip())
                text += f"\n\n<b>Сопроводительное сообщение:</b> <i>«{escaped_msg}»</i>"
        else:
            text = (
                f"🚫 <b>Отозван доступ к документу №{reg_num}</b>\n\n"
                f"Ваш доступ к данному документу был отозван."
            )

        success = await self._send_safe(delegatee_chat_id, text)
        logger.info(
            f"Sent 'delegation_changed' notification (granted={is_granted}) for doc_id={doc_id} to delegatee_id={delegatee_id}. Success: {success}",
            extra={
                "event_type": "notify_delegation_changed",
                "doc_id": doc_id,
                "delegatee_id": delegatee_id,
                "is_granted": is_granted,
                "success": success
            }
        )

    async def notify_overtimes_imported(self, employee_ids: set[int]):
        """Массовое рассылочное уведомление об импорте переработок"""
        if not employee_ids:
            return

        async with self.session_emp_factory() as session_emp:
            emp_repo = EmployeesRepository(session_emp)
            chat_map = await emp_repo.get_chat_ids_by_employee_ids(list(employee_ids))

        if not chat_map:
            logger.debug(
                "No Telegram chat_ids found for overtimes notification batch",
                extra={"event_type": "notify_no_chat_ids", "target_count": len(employee_ids)}
            )
            return

        text = (
            "⏰ <b>Обновление данных по переработкам</b>\n\n"
            "В систему импортированы новые записи о ваших переработках.\n"
            "Вы можете проверить обновленную информацию в своем личном кабинете."
        )

        sent_count = await self._broadcast_messages(list(chat_map.values()), text)
        logger.info(
            f"Bulk overtimes import notifications sent ({sent_count}/{len(chat_map)} delivered)",
            extra={
                "event_type": "notify_overtimes_imported",
                "delivered": sent_count,
                "total_targets": len(chat_map)
            }
        )