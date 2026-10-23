import logging
from datetime import date
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.employee_models import Employee
from server.app.repositories.overtime_repo import OvertimeRepository
from server.bot.keyboards import overtime_kb as kb
from server.bot.keyboards.menu_kb import get_main_menu, get_cancel_keyboard
from server.bot.keyboards.overtime_kb import PeriodCallback
from server.bot.services import messages as msg
from server.bot.services.utils import get_recent_periods

router = Router()
logger = logging.getLogger("bot_overtime")

ITEMS_PER_PAGE = 5  # Выводим по 5 переработок на страницу
PERIODS_PER_PAGE = 4   # По сколько МЕСЯЦЕВ выводить на страницу пагинации

class OvertimeStates(StatesGroup):
    selecting_items = State()       # Выбор переработок галочками
    awaiting_description = State()  # Ожидание ввода текста для выбранных элементов


def paginate_periods(all_periods: list, page: int) -> tuple[list, int]:
    total_items = len(all_periods)
    total_pages = (total_items + PERIODS_PER_PAGE - 1) // PERIODS_PER_PAGE
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * PERIODS_PER_PAGE
    return all_periods[start_idx:start_idx + PERIODS_PER_PAGE], total_pages


async def render_overtimes_list(
    message_or_callback: Message | CallbackQuery,
    emp_session: AsyncSession,
    state: FSMContext,
    current_employee: Employee,
    start_dt: date,
    end_dt: date,
    period_name: str,
    page: int,
    current_periods_page: int,
):
    """Единая функция отрисовки списка переработок с учётом выбранных чекбоксов."""
    repo = OvertimeRepository(emp_session)

    total_items = await repo.count_by_employee_period(current_employee.id, start_dt, end_dt)

    if total_items == 0:
        all_periods = get_recent_periods(count=12)
        periods_page, total_periods_pages = paginate_periods(all_periods, current_periods_page)

        text = msg.OVERTIME_NO_RECORDS.format(period_name=period_name)
        reply_markup = kb.get_periods_keyboard(
            periods_page, page=current_periods_page, total_pages=total_periods_pages
        ).as_markup()

        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.edit_text(text=text, reply_markup=reply_markup)
            await message_or_callback.answer()
        else:
            await message_or_callback.answer(text=text, reply_markup=reply_markup)
        return

    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page = max(1, min(page, total_pages))

    overtimes_page = await repo.get_by_employee_period(
        current_employee.id, start_dt, end_dt, page=page, size=ITEMS_PER_PAGE
    )

    # Часы считаем в Python через msg.format_overtime_duration,
    # но тянем из БД только два столбца (start, end), без ORM-объектов.
    hours_rows = await repo.get_hours_rows_by_employee_period(
        current_employee.id, start_dt, end_dt
    )
    total_hours = round(
        sum(msg.format_overtime_duration(s, e) for s, e in hours_rows), 1
    )

    fsm_data = await state.get_data()
    selected_ids = set(fsm_data.get("selected_ids", []))

    text = msg.get_overtime_list_text(
        period_name=period_name,
        start_date=start_dt,
        end_date=end_dt,
        overtimes_page=list(overtimes_page),
        total_hours=total_hours,
        page=page,
        total_pages=total_pages,
    )

    period_cb = PeriodCallback(
        start_date=start_dt.isoformat(),
        end_date=end_dt.isoformat(),
        name=period_name,
        page=page,
        current_periods_page=current_periods_page,
    )

    keyboard = kb.get_overtimes_keyboard(
        list(overtimes_page), page, total_pages, period_cb, selected_ids
    )

    await state.set_state(OvertimeStates.selecting_items)
    await state.update_data(
        start_date=start_dt.isoformat(),
        end_date=end_dt.isoformat(),
        period_name=period_name,
        page=page,
        current_periods_page=current_periods_page,
        page_overtime_ids=[ov.id for ov in overtimes_page],
    )

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text=text, reply_markup=keyboard.as_markup())
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(text=text, reply_markup=keyboard.as_markup())

# ==================== 1. Вход в режим просмотра ====================

async def open_overtimes(message):
    all_periods = get_recent_periods(count=12)
    periods_page, total_pages = paginate_periods(all_periods, 1)

    await message.answer(
        text=msg.OVERTIME_CHOOSE_PERIOD,
        reply_markup=kb.get_periods_keyboard(periods_page, page=1, total_pages=total_pages).as_markup()
    )


# ==================== 2. Возврат к периодам из инлайна ====================

@router.callback_query(kb.PeriodPageCallback.filter())
async def process_periods_page(callback: CallbackQuery, callback_data: kb.PeriodPageCallback):
    all_periods = get_recent_periods(count=12)
    periods_page, total_pages = paginate_periods(all_periods, callback_data.page)

    await callback.message.edit_text(
        text=msg.OVERTIME_CHOOSE_PERIOD,
        reply_markup=kb.get_periods_keyboard(periods_page, page=callback_data.page, total_pages=total_pages).as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ov_back_to_periods:"))
async def back_to_periods_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        current_page = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        current_page = 1

    all_periods = get_recent_periods(count=12)
    periods_page, total_pages = paginate_periods(all_periods, current_page)

    await callback.message.edit_text(
        text=msg.OVERTIME_CHOOSE_PERIOD,
        reply_markup=kb.get_periods_keyboard(periods_page, page=current_page, total_pages=total_pages).as_markup()
    )
    await callback.answer()


# ==================== 3. Просмотр списка переработок (и пагинация) ====================

@router.callback_query(kb.PeriodCallback.filter())
@router.callback_query(kb.OvertimeListCallback.filter())
async def show_overtimes_list(
    callback: CallbackQuery,
    callback_data: kb.PeriodCallback | kb.OvertimeListCallback,
    emp_session: AsyncSession,
    state: FSMContext,
    current_employee: Employee,
):
    await render_overtimes_list(
        message_or_callback=callback,
        emp_session=emp_session,
        state=state,
        current_employee=current_employee,
        start_dt=date.fromisoformat(callback_data.start_date),
        end_dt=date.fromisoformat(callback_data.end_date),
        period_name=callback_data.name,
        page=callback_data.page,
        current_periods_page=getattr(callback_data, "current_periods_page", 1),
    )


@router.callback_query(kb.OvertimeToggleCallback.filter())
async def toggle_overtime_selection(
    callback: CallbackQuery,
    callback_data: kb.OvertimeToggleCallback,
    emp_session: AsyncSession,
    state: FSMContext,
    current_employee: Employee,
):
    data = await state.get_data()
    selected_ids = set(data.get("selected_ids", []))
    ov_id = callback_data.overtime_id

    if ov_id in selected_ids:
        selected_ids.remove(ov_id)
    else:
        selected_ids.add(ov_id)

    await state.update_data(selected_ids=list(selected_ids))

    await render_overtimes_list(
        message_or_callback=callback,
        emp_session=emp_session,
        state=state,
        current_employee=current_employee,
        start_dt=date.fromisoformat(data["start_date"]),
        end_dt=date.fromisoformat(data["end_date"]),
        period_name=data["period_name"],
        page=callback_data.page,
        current_periods_page=data.get("current_periods_page", 1),
    )

@router.callback_query(kb.OvertimeBulkActionCallback.filter())
async def handle_bulk_action(
    callback: CallbackQuery,
    callback_data: kb.OvertimeBulkActionCallback,
    emp_session: AsyncSession,
    state: FSMContext,
    current_employee: Employee,
):
    data = await state.get_data()
    selected_ids = set(data.get("selected_ids", []))

    if callback_data.action == "select_all":
        page_ids = data.get("page_overtime_ids", [])
        if set(page_ids).issubset(selected_ids):
            selected_ids -= set(page_ids)
        else:
            selected_ids.update(page_ids)

        await state.update_data(selected_ids=list(selected_ids))

        await render_overtimes_list(
            message_or_callback=callback,
            emp_session=emp_session,
            state=state,
            current_employee=current_employee,
            start_dt=date.fromisoformat(data["start_date"]),
            end_dt=date.fromisoformat(data["end_date"]),
            period_name=data["period_name"],
            page=callback_data.page,
            current_periods_page=data.get("current_periods_page", 1),
        )

    elif callback_data.action == "submit_description":
        if not selected_ids:
            await callback.answer("Выберите хотя бы одну переработку!", show_alert=True)
            return

        await state.set_state(OvertimeStates.awaiting_description)
        await callback.message.answer(
            f"📝 Введите новое описание для <b>{len(selected_ids)}</b> выбранных переработок.\n\n"
            "Нажмите «❌ Отмена», если передумали.",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()

@router.message(OvertimeStates.awaiting_description)
async def process_bulk_description(
    message: Message,
    state: FSMContext,
    emp_session: AsyncSession,
    current_employee: Employee,
):
    # Кнопка отмены
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Редактирование отменено.", reply_markup=get_main_menu())
        return

    # Не текст (фото, стикер, документ и т.п.) — просим ввести текст
    if message.text is None:
        await message.answer(
            "⚠️ Пожалуйста, отправьте описание текстом.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    note_text = message.text.strip()
    if not note_text:
        await message.answer(
            "⚠️ Описание не может быть пустым. Введите текст или нажмите «❌ Отмена».",
            reply_markup=get_cancel_keyboard(),
        )
        return

    data = await state.get_data()
    selected_ids = data.get("selected_ids", [])

    if not selected_ids:
        await state.clear()
        await message.answer("Ошибка сессии: элементы не найдены.", reply_markup=get_main_menu())
        return

    repo = OvertimeRepository(emp_session)
    try:
        updated = await repo.update_bulk_notes_for_employee(
            overtime_ids=selected_ids,
            employee_id=current_employee.id,   # 👈 защита от правки чужих записей
            note=note_text,
        )
        # update_bulk_notes_for_employee возвращает {"updated_count": len(ids)}.
        # Если поменяете на rowcount — используйте реальное число.
        await message.answer(
            f"✅ Описание успешно обновлено для {len(selected_ids)} переработок!",
            reply_markup=get_main_menu(),
        )
    except Exception:
        logger.exception(
            "Ошибка сохранения группового описания переработок "
            "(employee_id=%s, ids=%s)", current_employee.id, selected_ids
        )
        await emp_session.rollback()
        await message.answer("❌ Произошла ошибка при сохранении данных.", reply_markup=get_main_menu())

    # Обновляем список
    start_dt = date.fromisoformat(data["start_date"])
    end_dt = date.fromisoformat(data["end_date"])
    period_name = data["period_name"]
    page = data["page"]
    current_periods_page = data.get("current_periods_page", 1)

    await state.update_data(selected_ids=[])

    await render_overtimes_list(
        message_or_callback=message,
        emp_session=emp_session,
        state=state,
        current_employee=current_employee,
        start_dt=start_dt,
        end_dt=end_dt,
        period_name=period_name,
        page=page,
        current_periods_page=current_periods_page,
    )

