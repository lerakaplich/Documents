from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date


# Описываем структуры колбэков
class PeriodCallback(CallbackData, prefix="ov_period"):
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    name: str
    page: int = 1     # Страница списка ПЕРЕРАБОТОК внутри периода
    current_periods_page: int = 1  # Текущая страница самих ПЕРИОДОВ (месяцев)


class OvertimeListCallback(CallbackData, prefix="ov_list"):
    start_date: str
    end_date: str
    name: str
    page: int
    action: str = "view"  # "view", "prev_page", "next_page"


class OvertimeDetailCallback(CallbackData, prefix="ov_detail"):
    overtime_id: int
    parent_page: int
    parent_start: str
    parent_end: str
    parent_name: str

# Новая структура для листания месяцев
class PeriodPageCallback(CallbackData, prefix="ov_per_page"):
    page: int

def get_periods_keyboard(periods_page: list, page: int, total_pages: int) -> InlineKeyboardBuilder:
    """Генерирует список расчетных периодов с поддержкой пагинации по месяцам"""
    builder = InlineKeyboardBuilder()

    # 1. Выводим список месяцев текущей страницы
    for p in periods_page:
        builder.button(
            text=p["label"],
            callback_data=PeriodCallback(
                start_date=p["start"].isoformat(),
                end_date=p["end"].isoformat(),
                name=p["name"],
                page=1,  # При выборе нового месяца всегда открываем 1-ю страницу его переработок
                current_periods_page=page
            )
        )
    builder.adjust(1)  # Каждый месяц на отдельной строчке

    # 2. Ряд пагинации по месяцам
    nav_builder = InlineKeyboardBuilder()

    if page > 1:
        nav_builder.button(text="⏪ Пред. месяц", callback_data=PeriodPageCallback(page=page - 1))

    nav_builder.button(text=f"📅 {page}/{total_pages}", callback_data="noop")

    if page < total_pages:
        nav_builder.button(text="След. месяц ⏩", callback_data=PeriodPageCallback(page=page + 1))

    nav_builder.adjust(3 if (page > 1 and page < total_pages) else 2)
    builder.attach(nav_builder)

    return builder


def get_overtimes_keyboard(overtimes_page: list, page: int, total_pages: int,
                           period_cb: PeriodCallback) -> InlineKeyboardBuilder:
    """Генерирует клавиатуру для списка переработок конкретного периода"""
    builder = InlineKeyboardBuilder()

    # 1. Кнопки выбора конкретной переработки (номера 1, 2, 3...)
    row_buttons = []
    for idx, ov in enumerate(overtimes_page, 1):
        row_buttons.append(
            builder.button(
                text=f" {idx} ",
                callback_data=OvertimeDetailCallback(
                    overtime_id=ov.id,
                    parent_page=page,
                    parent_start=period_cb.start_date,
                    parent_end=period_cb.end_date,
                    parent_name=period_cb.name
                )
            )
        )

    # 2. Кнопки пагинации [ Назад ] [ Страница ] [ Вперед ]
    nav_row = []
    if page > 1:
        builder.button(
            text="⬅️ Пред.",
            callback_data=OvertimeListCallback(
                start_date=period_cb.start_date,
                end_date=period_cb.end_date,
                name=period_cb.name,
                page=page - 1,
                action="prev_page"
            )
        )

    # Кнопка с текущим номером страницы (просто информационная)
    builder.button(text=f"📄 {page}/{total_pages}", callback_data="noop")

    if page < total_pages:
        builder.button(
            text="След. ➡️",
            callback_data=OvertimeListCallback(
                start_date=period_cb.start_date,
                end_date=period_cb.end_date,
                name=period_cb.name,
                page=page + 1,
                action="next_page"
            )
        )

    # 3. Кнопка возврата к списку ПЕРИОДОВ
    builder.button(
        text="◀️ К периодам",
        callback_data=f"ov_back_to_periods:{period_cb.current_periods_page}"
    )

    # Правильно распределяем сетку кнопок:
    # - Первый ряд: кнопки номеров переработок
    # - Второй ряд: кнопки навигации (их может быть 2 или 3)
    # - Третий ряд: Кнопка "Назад"
    builder.adjust(len(overtimes_page), 3 if (page > 1 and page < total_pages) else 2, 1)
    return builder


def get_overtime_detail_keyboard(parent_page: int, start: str, end: str, name: str) -> InlineKeyboardBuilder:
    """Клавиатура карточки детализации"""
    builder = InlineKeyboardBuilder()
    # Возвращает назад на ту же страницу списка, откуда пришел пользователь
    builder.button(
        text="◀️ Назад к списку",
        callback_data=OvertimeListCallback(
            start_date=start,
            end_date=end,
            name=name,
            page=parent_page
        )
    )
    return builder