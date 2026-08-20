from datetime import date, timedelta


def mask_phone_number(phone: str) -> str:
    """
    Маскирует номер телефона, оставляя видимыми код страны и последние 2-4 цифры.
    Пример: '+375291234567' -> '+37529***4567' или '80291234567' -> '8029***4567'
    """
    if not phone or len(phone) < 7:
        return "***"

    # Оставляем первые 5 символов (код страны/оператора) и последние 4 цифры
    return f"{phone[:5]}***{phone[-4:]}"


def get_default_pay_period() -> tuple[date, date]:
    today = date.today()

    # Расчет стартовой даты (25-е число прошлого месяца)
    first_of_current_month = today.replace(day=1)
    last_month_end = first_of_current_month - timedelta(days=1)
    start_date = last_month_end.replace(day=25)

    # Расчет конечной даты
    target_end = today.replace(day=24)
    # Если сегодня еще не наступило 24-е, ограничением будет текущий день
    end_date = min(today, target_end) if today >= start_date else target_end

    return start_date, end_date