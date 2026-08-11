from datetime import date, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from server.bot.services.tg_client import TelegramClient

from server.app.database.employee_models import Employee
from server.app.database.document_models import (
    EmployeeDocument,
    Document,
    Tag,
    TagPriority
)


class StatsNotificationService:
    EXPIRING_DAYS_INTERVAL = 4

    MSG_TEMPLATE = (
        "<b>Доброе утро, {first_name} {last_name}.</b>\n\n"
        "Персональная статистика важных документов СЭД\n"
        "Дата: {today_str}\n\n"
        "Срочные документы: <b>{urgent}</b>\n"
        "С истекающим сроком исполнения (до {days} дней): <b>{expiring}</b>\n"
        "Просроченные документы: <b>{overdue}</b>\n\n"
        "{footer}"
    )

    MSG_FOOTER_CLEAN = "У вас нет срочных, истекающих или просроченных документов на исполнении.\n"
    MSG_FOOTER_ATTENTION = "Пожалуйста, ознакомьтесь со списком документов, требующих вашего внимания."

    def __init__(self, emp_db: AsyncSession, doc_db: AsyncSession, tg_client: TelegramClient):
        self.emp_db = emp_db
        self.doc_db = doc_db
        self.tg = tg_client

    async def get_subscribers(self):
        """Получаем всех активных сотрудников с заполненным chat_id из базы кадров"""
        query = (
            select(
                Employee.id,
                Employee.last_name,
                Employee.first_name,
                Employee.patronymic,
                Employee.chat_id
            )
            .where(
                and_(
                    Employee.is_active == True,
                    Employee.chat_id.isnot(None)
                )
            )
        )
        result = await self.emp_db.execute(query)
        return result.all()

    async def get_employee_stats(self, emp_id: int):
        """Считаем типы важных документов в базе СЭД с помощью ORM агрегаций"""
        today = date.today()
        four_days_later = today + timedelta(days=self.EXPIRING_DAYS_INTERVAL)

        overdue_case = func.count(func.nullif(Document.deadline < today, False))
        expiring_case = func.count(
            func.nullif(
                and_(Document.deadline >= today, Document.deadline <= four_days_later),
                False
            )
        )
        urgent_case = func.count(func.nullif(Tag.priority == TagPriority.urgent, False))

        query = (
            select(overdue_case, expiring_case, urgent_case)
            .select_from(EmployeeDocument)
            .join(Document, EmployeeDocument.document_id == Document.id)
            .outerjoin(Document.tags)
            .where(
                and_(
                    EmployeeDocument.employee_id == emp_id,
                    EmployeeDocument.is_completed == False
                )
            )
        )

        result = await self.doc_db.execute(query)
        row = result.fetchone()
        return row if row else (0, 0, 0)

    def format_message(self, last_name: str, first_name: str, stats) -> str:
        """Форматирует красивое HTML-сообщение, используя константы класса"""
        overdue, expiring, urgent = stats
        today_str = date.today().strftime("%d.%m.%Y")

        # Определяем подвал в зависимости от наличия документов
        if overdue == 0 and expiring == 0 and urgent == 0:
            footer = self.MSG_FOOTER_CLEAN
        else:
            footer = self.MSG_FOOTER_ATTENTION

        # Собираем итоговую строку по шаблону
        return self.MSG_TEMPLATE.format(
            first_name=first_name,
            last_name=last_name,
            today_str=today_str,
            urgent=urgent,
            expiring=expiring,
            overdue=overdue,
            days=self.EXPIRING_DAYS_INTERVAL,
            footer=footer
        )

    async def run_daily_broadcast(self):
        """Запуск рассылки по всем подписчикам"""
        subscribers = await self.get_subscribers()
        for sub in subscribers:
            emp_id, last_name, first_name, patronymic, chat_id = sub

            stats = await self.get_employee_stats(emp_id)
            message_text = self.format_message(last_name, first_name, stats)
            await self.tg.send_message(chat_id, message_text)