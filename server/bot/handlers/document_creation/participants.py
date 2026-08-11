from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.employee_models import Department
from server.bot.keyboards.tree_kb import build_org_tree_keyboard
from server.bot.services.bot_repo import BotRepository
from server.bot.states.org_tree_cb import OrgTreeCallback

router = Router()

# =========================================================================
# ВНИМАНИЕ: Стартовые функции инициализации шага выбора (вызываются из go_to_next_step)
# =========================================================================

async def show_org_tree(
        event: types.Message | types.CallbackQuery,
        state: FSMContext,
        bot_repo: BotRepository,
        target_role: str,
        dept_id: int | None = None
):
    """Универсальная функция отображения узла дерева"""
    current_dept = await bot_repo.emp_session.get(Department, dept_id) if dept_id else None
    sub_departments = await bot_repo.get_departments_by_parent(dept_id)
    employees = await bot_repo.get_employees_by_department(dept_id) if dept_id else []

    data = await state.get_data()

    # 1. Получаем список выбранных в текущей роли
    selected_ids = data.get(target_role, [])
    if isinstance(selected_ids, int):
        selected_ids = [selected_ids]

    # 2. Собираем ID сотрудников, занятых в ДРУГИХ ролях
    disabled_ids = set()

    # Автор / Отправитель
    sender = data.get("sender")
    if sender and target_role != "sender":
        if isinstance(sender, int):
            disabled_ids.add(sender)
        elif isinstance(sender, dict):
            disabled_ids.add(sender.get("id"))

    # Исполнители
    if target_role != "executors":
        execs = data.get("executors", [])
        if isinstance(execs, list):
            disabled_ids.update(execs)

    # Получатели
    if target_role != "recipients":
        recips = data.get("recipients", [])
        if isinstance(recips, list):
            disabled_ids.update(recips)

    kb = build_org_tree_keyboard(
        departments=sub_departments,
        employees=employees,
        current_dept=current_dept,
        target_role=target_role,
        selected_ids=selected_ids,
        disabled_ids=list(disabled_ids)  # Передаём список запрещённых ID
    )

    role_titles = {
        "sender": "👤 Выбор отправителя",
        "recipients": "📥 Выбор получателей",
        "executors": "👥 Выбор исполнителей"
    }

    title = role_titles.get(target_role, "Выберите участника")
    dept_name = f"\nТекущий отдел: **{current_dept.name}**" if current_dept else "\nКорень структуры"
    text = f"{title}{dept_name}\n\nВыберите отдел для навигации или сотрудника из списка:"

    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await event.answer(text, parse_mode="Markdown", reply_markup=kb)


# =========================================================================
# ОБРАБОТКА НАВИГАЦИИ И КЛИКОВ ПО ДЕРЕВУ
# =========================================================================

@router.callback_query(OrgTreeCallback.filter())
async def process_org_tree_navigation(
    callback: types.CallbackQuery,
    callback_data: OrgTreeCallback,
    state: FSMContext,
    doc_session: AsyncSession,
    emp_session: AsyncSession
):
    from server.bot.handlers.step_navigator import go_to_next_step
    bot_repo = BotRepository(doc_session, emp_session)
    role = callback_data.target_role
    action = callback_data.action

    # 1. Переход по отделу или Вверх
    if action in ("select_dept", "up"):
        await show_org_tree(callback, state, bot_repo, target_role=role, dept_id=callback_data.dept_id)
        await callback.answer()
        return

    # 2. Выбор конкретного сотрудника
    if action == "select_emp":
        emp_id = callback_data.emp_id
        if role == "sender":
            # Для отправителя — один человек, сразу переходим дальше
            await state.update_data(sender_id=emp_id)
            await callback.answer("Отправитель выбран!")
            await go_to_next_step(callback.message, state, bot_repo)
            return
        else:
            # Для recipients / executors — тогл выборка (добавить / удалить)
            data = await state.get_data()
            current_list = list(data.get(role, []))

            if emp_id in current_list:
                current_list.remove(emp_id)
            else:
                current_list.append(emp_id)

            await state.update_data({role: current_list})
            await show_org_tree(callback, state, bot_repo, target_role=role, dept_id=callback_data.dept_id)
            await callback.answer()
            return

    # 3. Выбор ВСЕГО отдела (добавляет всех сотрудников отдела и его подразделений)
    if action == "select_all_dept":
        dept_id = callback_data.dept_id
        all_emp_ids = await bot_repo.get_all_employees_in_department_tree(dept_id)

        if role == "sender":
            await callback.answer("⚠️ Отправителем может быть только один человек, а не весь отдел!", show_alert=True)
            return

        data = await state.get_data()
        current_list = set(data.get(role, []))
        current_list.update(all_emp_ids)  # Объединяем множества

        await state.update_data({role: list(current_list)})
        await callback.answer(f"Добавлено сотрудников: {len(all_emp_ids)}")
        await show_org_tree(callback, state, bot_repo, target_role=role, dept_id=dept_id)
        return

    # 4. Завершение выбора (Кнопка "Готово")
    if action == "done":
        await callback.answer("Выбор сохранен!")
        await go_to_next_step(callback.message, state, bot_repo)

@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    await callback.answer("Этот сотрудник уже выбран в другой роли!", show_alert=True)