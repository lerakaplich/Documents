from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.employee_models import Department, Organization
from server.bot.keyboards.tree_kb import build_org_tree_keyboard
from server.bot.services.bot_repo import BotRepository
from server.bot.states.org_tree_cb import OrgTreeCallback

router = Router()


async def show_org_tree(
        event: Message | CallbackQuery,
        state: FSMContext,
        bot_repo: BotRepository,
        target_role: str,
        org_id: int | None = None,
        dept_id: int | None = None,
        page: int = 1
):
    """Универсальная функция отображения дерева с учетом нового DTO бэкенда."""
    current_org = await bot_repo.emp_session.get(Organization, org_id) if org_id else None
    current_dept = await bot_repo.emp_session.get(Department, dept_id) if dept_id else None

    if current_dept and not current_org:
        current_org = await bot_repo.emp_session.get(Organization, current_dept.organization_id)

    organizations = await bot_repo.get_all_organizations() if not current_org and not current_dept else []
    sub_departments = await bot_repo.get_departments_by_parent(parent_id=dept_id, org_id=org_id)
    employees = await bot_repo.get_employees_by_department(dept_id) if dept_id else []

    data = await state.get_data()

    # Сбор выбранных ID для отображения галочек в клавиатуре
    selected_emp_ids = []
    selected_dept_ids = []
    selected_org_ids = []

    if target_role == "source":
        if data.get("source_employee_id"):
            selected_emp_ids.append(data.get("source_employee_id"))
        if data.get("source_organization_id"):
            selected_org_ids.append(data.get("source_organization_id"))

    elif target_role == "receivers":
        receivers = data.get("receivers", [])
        for r in receivers:
            if r.get("target_organization_id"):
                selected_org_ids.append(r["target_organization_id"])
            if r.get("target_department_id"):
                selected_dept_ids.append(r["target_department_id"])

    elif target_role == "executors":
        selected_emp_ids = list(data.get("executors", []))

    # Запрещаем задействованным сотрудникам повторный выбор
    disabled_emp_ids = set()
    if target_role == "executors":
        source_emp_id = data.get("source_employee_id")
        if source_emp_id:
            disabled_emp_ids.add(source_emp_id)

    kb = build_org_tree_keyboard(
        organizations=organizations,
        departments=sub_departments,
        employees=employees,
        current_org=current_org,
        current_dept=current_dept,
        role=target_role,
        selected_emp_ids=selected_emp_ids,
        selected_dept_ids=selected_dept_ids,
        selected_org_ids=selected_org_ids,
        disabled_emp_ids=list(disabled_emp_ids),
        page=page
    )

    role_titles = {
        "source": "👤 Выбор источника / отправителя на бланке",
        "receivers": "📥 Выбор получателей документа (бланки адресатов)",
        "executors": "👥 Выбор исполнителей (конкретных лиц)"
    }

    title = role_titles.get(target_role, "Выберите участника")
    context_str = "Корень структуры"
    if current_dept:
        context_str = f"Отдел: **{current_dept.name}**"
    elif current_org:
        context_str = f"Организация: **{current_org.name}**"

    text = f"{title}\nКонтекст: {context_str}\n\nВыберите элемент:"

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await event.answer(text, parse_mode="Markdown", reply_markup=kb)


# =========================================================================
# ОБРАБОТКА НАВИГАЦИИ И КЛИКОВ ПО ДЕРЕВУ
# =========================================================================

@router.callback_query(OrgTreeCallback.filter())
async def process_org_tree_navigation(
        callback: CallbackQuery,
        callback_data: OrgTreeCallback,
        state: FSMContext,
        doc_session: AsyncSession,
        emp_session: AsyncSession
):
    from server.bot.handlers.step_navigator import go_to_next_step

    bot_repo = BotRepository(doc_session, emp_session)
    role = callback_data.role
    action = callback_data.act
    page = callback_data.page or 1

    # 1. Навигация и переходы по папкам
    if action in ("page", "open_org", "open_dept", "up"):
        await show_org_tree(
            callback, state, bot_repo, target_role=role,
            org_id=callback_data.org_id, dept_id=callback_data.dept_id, page=page
        )
        await callback.answer()
        return

    # 2. Выбор СОТРУДНИКА (доступен для source и executors)
    if action == "select_emp":
        emp_id = callback_data.emp_id

        if role == "source":
            await state.update_data(source_employee_id=emp_id, source_organization_id=None)
            await callback.answer("Отправитель выбран!")
            await go_to_next_step(callback.message, state, bot_repo)
            return

        elif role == "executors":
            data = await state.get_data()
            executors = list(data.get("executors", []))

            if emp_id in executors:
                executors.remove(emp_id)
                await callback.answer("Исполнитель убран")
            else:
                executors.append(emp_id)
                await callback.answer("Исполнитель добавлен")

            await state.update_data(executors=executors)
            await show_org_tree(
                callback, state, bot_repo, target_role=role,
                org_id=callback_data.org_id, dept_id=callback_data.dept_id, page=page
            )
            return

    # 3. Выбор ОТДЕЛА целиком (доступен только для receivers)
    if action == "select_dept_target":
        dept_id = callback_data.dept_id
        data = await state.get_data()
        receivers = list(data.get("receivers", []))

        existing = next((r for r in receivers if r.get("target_department_id") == dept_id), None)
        if existing:
            receivers.remove(existing)
            await callback.answer("Отдел убран из адресатов")
        else:
            receivers.append({
                "target_department_id": dept_id,
                "target_organization_id": None,
                "target_official_text": None
            })
            await callback.answer("Отдел добавлен в адресаты!")

        await state.update_data(receivers=receivers)
        await show_org_tree(
            callback, state, bot_repo, target_role=role,
            org_id=callback_data.org_id, dept_id=dept_id, page=page
        )
        return

    # 4. Выбор ОРГАНИЗАЦИИ целиком (доступен для source и receivers)
    if action == "select_org_target":
        org_id = callback_data.org_id

        if role == "source":
            await state.update_data(source_organization_id=org_id, source_employee_id=None)
            await callback.answer("Организация-отправитель выбрана!")
            await go_to_next_step(callback.message, state, bot_repo)
            return

        elif role == "receivers":
            data = await state.get_data()
            receivers = list(data.get("receivers", []))

            existing = next((r for r in receivers if r.get("target_organization_id") == org_id), None)
            if existing:
                receivers.remove(existing)
                await callback.answer("Организация убрана из адресатов")
            else:
                receivers.append({
                    "target_organization_id": org_id,
                    "target_department_id": None,
                    "target_official_text": None
                })
                await callback.answer("Организация добавлена в адресаты!")

            await state.update_data(receivers=receivers)
            await show_org_tree(
                callback, state, bot_repo, target_role=role,
                org_id=org_id, dept_id=None, page=page
            )
            return

    # 5. Завершение выбора
    if action == "done":
        await callback.answer()
        await go_to_next_step(callback.message, state, bot_repo)
        return

    if action == "cancel":
        await callback.answer("Выбор отменен")
        await callback.message.delete()
        return


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    await callback.answer("Действие недоступно", show_alert=True)