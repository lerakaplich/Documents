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

# Колбэк для переключения выделения переработки (toggle checkbox)
class OvertimeToggleCallback(CallbackData, prefix="ov_toggle"):
    overtime_id: int
    page: int

# Новая структура для листания месяцев
class PeriodPageCallback(CallbackData, prefix="ov_per_page"):
    page: int

# Действие выбора всех или применения описания
class OvertimeBulkActionCallback(CallbackData, prefix="ov_bulk"):
    action: str  # "select_all", "submit_description"
    page: int

def get_periods_keyboard(periods_page: list, page: int, total_pages: int) -> InlineKeyboardBuilder:
    """Генерирует список месяцев с пагинацией"""
    builder = InlineKeyboardBuilder()

    for p in periods_page:
        builder.button(
            text=p["label"],
            callback_data=PeriodCallback(
                start_date=p["start"].isoformat(),
                end_date=p["end"].isoformat(),
                name=p["name"],
                page=1,
                current_periods_page=page
            )
        )
    builder.adjust(1)

    nav_builder = InlineKeyboardBuilder()
    if page > 1:
        nav_builder.button(text="⏪ Пред. месяц", callback_data=PeriodPageCallback(page=page - 1))

    nav_builder.button(text=f"📅 {page}/{total_pages}", callback_data="noop")

    if page < total_pages:
        nav_builder.button(text="След. месяц ⏩", callback_data=PeriodPageCallback(page=page + 1))

    nav_builder.adjust(3 if (page > 1 and page < total_pages) else 2)
    builder.attach(nav_builder)

    return builder


def get_overtimes_keyboard(
        overtimes_page: list,
        page: int,
        total_pages: int,
        period_cb: PeriodCallback,
        selected_ids: set[int]
) -> InlineKeyboardBuilder:
    """Генерирует клавиатуру мультивыбора переработок"""
    builder = InlineKeyboardBuilder()

    # 1. Кнопки элементов списка с чекбоксами [✅ 1] [ 2 ] [✅ 3]
    for idx, ov in enumerate(overtimes_page, 1):
        is_selected = ov.id in selected_ids
        icon = "✅" if is_selected else ""
        text = f"{icon} {idx}".strip()

        builder.button(
            text=text,
            callback_data=OvertimeToggleCallback(
                overtime_id=ov.id,
                page=page
            )
        )

    # Ряд кнопок действий с мультивыбором
    bulk_builder = InlineKeyboardBuilder()

    # Кнопка "Выбрать все на странице"
    bulk_builder.button(
        text="☑️ Выбрать все на странице",
        callback_data=OvertimeBulkActionCallback(action="select_all", page=page)
    )

    # Если есть хоть одна выбранная запись — показываем кнопку ввода описания
    if selected_ids:
        bulk_builder.button(
            text=f"✏️ Добавить описание ({len(selected_ids)})",
            callback_data=OvertimeBulkActionCallback(action="submit_description", page=page)
        )

    # 2. Пагинация по страницам переработок
    nav_builder = InlineKeyboardBuilder()
    if page > 1:
        nav_builder.button(
            text="⬅️ Пред.",
            callback_data=OvertimeListCallback(
                start_date=period_cb.start_date,
                end_date=period_cb.end_date,
                name=period_cb.name,
                page=page - 1,
                action="prev_page"
            )
        )

    nav_builder.button(text=f"📄 {page}/{total_pages}", callback_data="noop")

    if page < total_pages:
        nav_builder.button(
            text="След. ➡️",
            callback_data=OvertimeListCallback(
                start_date=period_cb.start_date,
                end_date=period_cb.end_date,
                name=period_cb.name,
                page=page + 1,
                action="next_page"
            )
        )

    # Компоновка
    builder.adjust(len(overtimes_page))  # Чекбоксы переработок в 1 ряд

    # Регулируем кнопки быстрых действий (по 1 или 2 в ряд)
    bulk_builder.adjust(2 if selected_ids else 1)
    builder.attach(bulk_builder)

    nav_builder.adjust(3 if (page > 1 and page < total_pages) else 2)
    builder.attach(nav_builder)

    # Кнопка "Назад к периодам"
    back_builder = InlineKeyboardBuilder()
    back_builder.button(
        text="◀️ К периодам",
        callback_data=f"ov_back_to_periods:{period_cb.current_periods_page}"
    )
    builder.attach(back_builder)

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