import logging
from datetime import date
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.employee_models import Employee, Overtime
from server.bot.keyboards import overtime_kb as kb
from server.bot.keyboards.menu_kb import get_main_menu, get_cancel_keyboard
from server.bot.services import messages as msg
from server.bot.services.utils import get_recent_periods

router = Router()
logger = logging.getLogger("bot_overtime")

ITEMS_PER_PAGE = 5  # Выводим по 5 переработок на страницу
PERIODS_PER_PAGE = 4   # По сколько МЕСЯЦЕВ выводить на страницу пагинации

class OvertimeStates(StatesGroup):
    viewing_details = State()  # Состояние просмотра карточки (ждем текст описания)


def paginate_periods(all_periods: list, page: int) -> tuple[list, int]:
    """Вспомогательная функция для пагинации списка месяцев в памяти"""
    total_items = len(all_periods)
    total_pages = (total_items + PERIODS_PER_PAGE - 1) // PERIODS_PER_PAGE

    if page < 1: page = 1
    if page > total_pages: page = total_pages

    start_idx = (page - 1) * PERIODS_PER_PAGE
    end_idx = start_idx + PERIODS_PER_PAGE
    return all_periods[start_idx:end_idx], total_pages

# ==================== 1. Вход в режим просмотра ====================

@router.message(F.chat.type == "private", F.text == "Мои переработки")
async def show_overtime_periods(message: Message, emp_session: AsyncSession):
    """Показывает список доступных периодов для выбора (стартуем с 1 страницы)"""
    result = await emp_session.execute(select(Employee).where(Employee.chat_id == message.from_user.id))
    employee = result.scalar_one_or_none()

    if not employee:
        await message.answer("❌ Вы не зарегистрированы в системе. Обратитесь к администратору.")
        return

    # Загружаем все 12 месяцев (или сколько генерирует утилита)
    all_periods = get_recent_periods(count=12)
    current_page = 1

    periods_page, total_pages = paginate_periods(all_periods, current_page)

    await message.answer(
        text=msg.OVERTIME_CHOOSE_PERIOD,
        reply_markup=kb.get_periods_keyboard(periods_page, page=current_page, total_pages=total_pages).as_markup()
    )


# ==================== 2. Возврат к периодам из инлайна ====================

@router.callback_query(kb.PeriodPageCallback.filter())
async def process_periods_page(callback: CallbackQuery, callback_data: kb.PeriodPageCallback):
    """Переключение страниц самого списка месяцев"""
    all_periods = get_recent_periods(count=12)
    current_page = callback_data.page

    periods_page, total_pages = paginate_periods(all_periods, current_page)

    await callback.message.edit_text(
        text=msg.OVERTIME_CHOOSE_PERIOD,
        reply_markup=kb.get_periods_keyboard(periods_page, page=current_page, total_pages=total_pages).as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ov_back_to_periods:"))
async def back_to_periods_callback(callback: CallbackQuery):
    """Возврат к списку месяцев с сохранением страницы, на которой был пользователь"""
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
async def show_overtimes_list(callback: CallbackQuery, callback_data: kb.PeriodCallback | kb.OvertimeListCallback,
                              emp_session: AsyncSession, state: FSMContext):
    """Отображает постраничный список переработок за период"""
    await state.clear()

    start_dt = date.fromisoformat(callback_data.start_date)
    end_dt = date.fromisoformat(callback_data.end_date)
    period_name = callback_data.name
    page = callback_data.page

    # Извлекаем, на какой странице месяцев мы находились
    current_periods_page = callback_data.current_periods_page

    emp_res = await emp_session.execute(select(Employee).where(Employee.chat_id == callback.from_user.id))
    employee = emp_res.scalar_one_or_none()

    if not employee:
        await callback.answer("Ошибка авторизации.", show_alert=True)
        return

    query = (
        select(Overtime)
        .where(
            Overtime.employee_id == employee.id,
            Overtime.overtime_date.between(start_dt, end_dt)
        )
        .order_by(Overtime.overtime_date.asc())
    )
    res = await emp_session.execute(query)
    all_overtimes = res.scalars().all()

    if not all_overtimes:
        all_periods = get_recent_periods(count=12)
        periods_page, total_periods_pages = paginate_periods(all_periods, current_periods_page)

        await callback.message.edit_text(
            text=msg.OVERTIME_NO_RECORDS.format(period_name=period_name),
            reply_markup=kb.get_periods_keyboard(periods_page, page=current_periods_page,
                                                 total_pages=total_periods_pages).as_markup()
        )
        await callback.answer()
        return

    total_hours = sum(msg.format_overtime_duration(ov.overtime_start, ov.overtime_end) for ov in all_overtimes)
    total_hours = round(total_hours, 1)

    total_items = len(all_overtimes)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    if page < 1: page = 1
    if page > total_pages: page = total_pages

    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    overtimes_page = all_overtimes[start_idx:end_idx]

    text = msg.get_overtime_list_text(
        period_name=period_name,
        start_date=start_dt,
        end_date=end_dt,
        overtimes_page=list(overtimes_page),
        total_hours=total_hours,
        page=page,
        total_pages=total_pages
    )

    # Важно: Сохраняем состояние пагинации месяцев внутри инлайн-структуры
    current_period_info = kb.PeriodCallback(
        start_date=callback_data.start_date,
        end_date=callback_data.end_date,
        name=period_name,
        page=page,
        current_periods_page=current_periods_page
    )

    keyboard = kb.get_overtimes_keyboard(list(overtimes_page), page, total_pages, current_period_info)

    await callback.message.edit_text(text=text, reply_markup=keyboard.as_markup())
    await callback.answer()


# ==================== 4. Карточка конкретной переработки ====================

@router.callback_query(kb.OvertimeDetailCallback.filter())
async def show_overtime_details(callback: CallbackQuery, callback_data: kb.OvertimeDetailCallback, emp_session: AsyncSession,
                                state: FSMContext):
    """Показывает детали переработки и ждет ввода нового описания"""

    # Извлекаем переработку из БД
    ov_res = await emp_session.execute(select(Overtime).where(Overtime.id == callback_data.overtime_id))
    ov = ov_res.scalar_one_or_none()

    if not ov:
        await callback.answer("Переработка не найдена.", show_alert=True)
        return

    # Запоминаем метаданные в FSM, чтобы знать, куда возвращаться и что обновлять
    await state.set_state(OvertimeStates.viewing_details)
    await state.update_data(
        edit_overtime_id=ov.id,
        parent_page=callback_data.parent_page,
        parent_start=callback_data.parent_start,
        parent_end=callback_data.parent_end,
        parent_name=callback_data.parent_name
    )

    text = msg.get_overtime_detail_text(ov)
    keyboard = kb.get_overtime_detail_keyboard(
        parent_page=callback_data.parent_page,
        start=callback_data.parent_start,
        end=callback_data.parent_end,
        name=callback_data.parent_name
    )

    # Меняем клавиатуру нижнего меню на "Отмена", чтобы пользователь мог выйти из ввода
    await callback.message.answer(
        "📝 Вы вошли в режим редактирования описания. Нажмите кнопку «❌ Отмена» на клавиатуре, если передумали.",
        reply_markup=get_cancel_keyboard()
    )

    await callback.message.edit_text(text=text, reply_markup=keyboard.as_markup())
    await callback.answer()


# ==================== 5. Обработка ввода описания ====================

@router.message(OvertimeStates.viewing_details)
async def update_overtime_description(message: Message, state: FSMContext, emp_session: AsyncSession):
    """Перехватывает текст сообщения и записывает его в описание переработки"""

    # 1. Если пользователь нажал глобальную отмену (а мы в состоянии ввода)
    if message.text == "❌ Отмена":
        data = await state.get_data()
        await state.clear()
        await message.answer(
            "Редактирование отменено. Возвращаю вас в главное меню.",
            reply_markup=get_main_menu()
        )
        return

    # Проверяем кнопки главного меню на случай ложного ввода
    if message.text in ["📄 Новый документ", "📸 Распознать по фото", "🆘 Поддержка", "⏳ Мои переработки"]:
        await state.clear()
        return

    # Достаем сохраненные метаданные
    data = await state.get_data()
    ov_id = data.get("edit_overtime_id")

    if not ov_id:
        await state.clear()
        await message.answer("Ошибка сессии. Пожалуйста, попробуйте снова.", reply_markup=get_main_menu())
        return

    try:
        # Обновляем описание в базе данных
        await emp_session.execute(
            update(Overtime)
            .where(Overtime.id == ov_id)
            .values(note_text=message.text)
        )
        await emp_session.commit()

        await message.answer("✅ Описание переработки успешно сохранено!", reply_markup=get_main_menu())

    except Exception as e:
        logger.error(f"Ошибка при обновлении описания переработки {ov_id}: {e}", exc_info=True)
        await emp_session.rollback()
        await message.answer("❌ Не удалось сохранить описание. Попробуйте позже.", reply_markup=get_main_menu())

    # Возвращаем пользователя обратно к списку переработок за этот период!
    # Делаем фиктивный вызов отображения списка с сохраненными ранее параметрами
    all_periods = get_recent_periods()

    # Очищаем состояние
    await state.clear()

    # И отправляем ему свежий список переработок за тот же период
    # (поскольку это текстовое сообщение, мы присылаем его новым сообщением, а не edit_text)
    start_dt = date.fromisoformat(data["parent_start"])
    end_dt = date.fromisoformat(data["parent_end"])
    period_name = data["parent_name"]
    page = data["parent_page"]

    emp_res = await emp_session.execute(select(Employee).where(Employee.chat_id == message.from_user.id))
    employee = emp_res.scalar_one_or_none()

    query = (
        select(Overtime)
        .where(
            Overtime.employee_id == employee.id,
            Overtime.overtime_date.between(start_dt, end_dt)
        )
        .order_by(Overtime.overtime_date.asc())
    )
    res = await emp_session.execute(query)
    all_overtimes = res.scalars().all()

    total_hours = sum(msg.format_overtime_duration(ov.overtime_start, ov.overtime_end) for ov in all_overtimes)
    total_hours = round(total_hours, 1)

    total_items = len(all_overtimes)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    overtimes_page = all_overtimes[start_idx:end_idx]

    text = msg.get_overtime_list_text(
        period_name=period_name,
        start_date=start_dt,
        end_date=end_dt,
        overtimes_page=list(overtimes_page),
        total_hours=total_hours,
        page=page,
        total_pages=total_pages
    )

    current_period_info = kb.PeriodCallback(
        start_date=data["parent_start"],
        end_date=data["parent_end"],
        name=period_name
    )
    keyboard = kb.get_overtimes_keyboard(list(overtimes_page), page, total_pages, current_period_info)

    await message.answer(text=text, reply_markup=keyboard.as_markup())