# Шаблон приветствия при старте (команда /start)
START_WELCOME = (
    "Приветствую, {name}.\n\n"
    "Для активации вашей учетной записи в СЭД МАЗ и генерации временного пароля, "
    "предоставьте ваш номер телефона с помощью кнопки на клавиатуре."
)

# Текст на кнопке отправки контакта
BTN_SHARE_CONTACT = "Предоставить номер телефона"

# Ошибка валидации владельца контакта
ERROR_NOT_OWNER_CONTACT = (
    "Доступ отклонен. Пожалуйста, отправьте ваш собственный контакт "
    "с помощью кнопки на клавиатуре."
)

# Ошибка: сотрудника нет в БД кадров
ERROR_EMPLOYEE_NOT_FOUND = (
    "Ошибка авторизации. Ваш номер телефона не найден в базе данных кадров СЭД.\n"
    "Для регистрации номера обратитесь в отдел кадров."
)

# Успешная генерация пароля и привязка аккаунта
AUTH_SUCCESS = (
    "Активация выполнена успешно.\n\n"
    "Ваши данные для входа в СЭД:\n"
    "Логин (телефон): <code>+{phone}</code>\n"
    "Временный пароль: <code>{password}</code>\n\n"
    "Используйте эти учетные данные для авторизации в десктопном приложении. "
    "Рекомендуется изменить временный пароль в настройках профиля при первом входе."
)

SUPPORT_START = (
    "Опишите вашу проблему или задайте вопрос.\n"
    "Вы можете отправить текст, фото, голосовое сообщение или кружочек."
)

SUPPORT_CANCEL = "Ввод отменен. Возвращаю вас в главное меню."

SUPPORT_SUCCESS = "Ваше обращение успешно отправлено в поддержку. Мы ответим вам в ближайшее время!"

SUPPORT_ERROR = "Произошла ошибка при отправке сообщения. Попробуйте позже."

SUPPORT_REPLY_DELIVERED = "Ответ успешно доставлен пользователю!"

SUPPORT_REPLY_FAILED = "Не удалось доставить ответ (возможно, бот заблокирован)."


def get_support_ticket_header(full_name: str, username: str, user_id: int) -> str:
    """Генерирует информационную шапку обращения для канала поддержки"""
    return (
        f"<b>Новое обращение!</b>\n"
        f"От: {full_name} ({username})\n"
        f"ID: <code>{user_id}</code>\n\n"
    )


# Сообщения для переработок

OVERTIME_CHOOSE_PERIOD = f"<b>Ваши переработки</b>\nВыберете расчетный период для просмотра:"
OVERTIME_NO_RECORDS = "За период <b>{period_name}</b> переработок не найдено."


def format_overtime_duration(start, end) -> float:
    """Вычисляет разницу в часах между началом и концом переработки"""
    if not start or not end:
        return 0.0
    # Переводим в минуты для точности
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    return round((end_minutes - start_minutes) / 60.0, 1)


def get_overtime_list_text(period_name: str, start_date, end_date, overtimes_page: list,
                           total_hours: float, page: int, total_pages: int) -> str:
    """Форматирует список переработок за период для конкретной страницы пагинации"""
    text = (
        f"<b>Переработки за период: {period_name}</b>\n"
        f"Интервал: {start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')}\n"
        f"Всего отработано: {total_hours} ч.\n\n"
        f"Страница {page} из {total_pages}:\n"
    )

    for idx, ov in enumerate(overtimes_page, 1):
        status_emoji = "🟢" if ov.note_text else "🟡"
        duration = format_overtime_duration(ov.overtime_start, ov.overtime_end)
        note_preview = f"«{ov.note_text[:25]}...»" if ov.note_text else "⚠️ <b>Описание не добавлено</b>"

        text += f"{status_emoji} <b>{idx}. {ov.overtime_date.strftime('%d.%m')}</b> — {duration} ч.\n"
        text += f"   └ {note_preview}\n\n"

    text += "Выберете номер переработки ниже, чтобы управлять описанием."
    return text


def get_overtime_detail_text(ov) -> str:
    """Форматирует карточку конкретной переработки"""
    duration = format_overtime_duration(ov.overtime_start, ov.overtime_end)
    time_str = f"{ov.overtime_start.strftime('%H:%M')} - {ov.overtime_end.strftime('%H:%M')}" \
        if ov.overtime_start else "Не указано"

    note = ov.note_text if ov.note_text else "❌ Описание отсутствует"

    return (
        f"Детали переработки за {ov.overtime_date.strftime('%d.%m.%Y')}\n\n"
        f"Длительность: {duration} ч. ({time_str})\n"
        f"Текущее описание:\n{note}\n\n"
        f"Чтобы изменить или добавить описание, просто отправьте текст следующим сообщением!"
    )