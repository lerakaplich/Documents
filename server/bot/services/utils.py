import bcrypt
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.deps import get_security_service, get_attachment_service, get_doc_service
from server.app.services.documents.document_service import DocumentService

async def build_doc_service_for_bot(
    db_docs: AsyncSession,
    db_emp: AsyncSession
) -> DocumentService:
    security_svc = get_security_service(emp_db=db_emp)
    attachment_svc = get_attachment_service(db_docs=db_docs, security_svc=security_svc)
    return await get_doc_service(db_docs=db_docs, db_emp=db_emp, attachment_svc=attachment_svc)

def hash_password(password: str) -> str:
    """Хэширование пароля с солью bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def get_period_for_date(target_date: date) -> tuple[date, date, str]:
    """
    Для любой даты определяет границы расчетного периода (с 25 по 24 число)
    и возвращает (start_date, end_date, 'Месяц Год' выплаты).

    Пример:
    - 20.05.2026 -> период 25.04.2026 - 24.05.2026 (Май 2026)
    - 26.05.2026 -> период 25.05.2026 - 24.06.2026 (Июнь 2026)
    """
    if target_date.day >= 25:
        # Если число >= 25, это уже следующий расчетный месяц
        start_year = target_date.year
        start_month = target_date.month

        # Вычисляем конец периода (следующий месяц)
        if start_month == 12:
            end_year = start_year + 1
            end_month = 1
        else:
            end_year = start_year
            end_month = start_month + 1
    else:
        # Если число < 25, мы находимся в текущем расчетном месяце
        end_year = target_date.year
        end_month = target_date.month

        # Начало было в предыдущем месяце
        if end_month == 1:
            start_year = end_year - 1
            start_month = 12
        else:
            start_year = end_year
            start_month = end_month - 1

    start_date = date(start_year, start_month, 25)
    end_date = date(end_year, end_month, 24)

    # Красивое название месяца выплаты
    months_ru = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель", 5: "Май", 6: "Июнь",
        7: "Июль", 8: "Август", 9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }

    period_name = f"{months_ru[end_month]} {end_year}"
    return start_date, end_date, period_name


def get_recent_periods(count: int = 6) -> list[dict]:
    """
    Генерирует список последних N расчетных периодов от текущей даты назад.
    Возвращает список словарей с границами и названиями.
    """
    today = date.today()
    periods = []

    # Начинаем с текущей даты и шагаем назад по ~30 дней
    current_pivot = today
    for _ in range(count):
        start, end, name = get_period_for_date(current_pivot)
        periods.append({
            "start": start,
            "end": end,
            "name": name,
            "label": name
        })
        # Сдвигаем точку отсчета назад, за пределы текущего периода
        current_pivot = start - timedelta(days=5)

    return periods
