# server/bot/keyboards/tree_kb.py
from typing import Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from server.app.database.employee_models import Department, Employee
from server.bot.states.org_tree_cb import OrgTreeCallback


def build_org_tree_keyboard(
    departments: list[Department],
    employees: list[Employee],
    current_dept: Optional[Department],
    target_role: str,
    selected_ids: list[int] = None,
    disabled_ids: list[int] = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    selected_ids = selected_ids or []

    # 1. Кнопка "Выбрать весь отдел" (если мы находимся внутри конкретного отдела)
    if current_dept:
        builder.button(
            text=f"✅ Выбрать весь отдел «{current_dept.name}»",
            callback_data=OrgTreeCallback(
                action="select_all_dept",
                dept_id=current_dept.id,
                emp_id=None,
                target_role=target_role
            )
        )

    # 2. Дочерние отделы / подотделы
    for dept in departments:
        builder.button(
            text=f"📁 {dept.name}",
            callback_data=OrgTreeCallback(
                action="select_dept",
                dept_id=dept.id,
                emp_id=None,
                target_role=target_role
            )
        )

    # 3. Сотрудники текущего отдела
    for emp in employees:
        if emp.id in disabled_ids:
            # Сотрудник уже занят в другой роли (например, он уже отправитель)
            builder.button(
                text=f"⛔️ {emp.last_name} {emp.first_name} (уже выбран)",
                callback_data="ignore"  # Заглушка, чтобы кнопка не нажималась
            )
        else:
            is_selected = emp.id in selected_ids
            mark = "☑️ " if is_selected else "👤 "
            builder.button(
                text=f"{mark}{emp.last_name} {emp.first_name}",
                callback_data=OrgTreeCallback(
                    action="select_emp",
                    dept_id=current_dept.id if current_dept else None,
                    emp_id=emp.id,
                    target_role=target_role
                )
            )

    # 4. Навигация: Кнопка "⬅️ Наверх" и Кнопка завершения выбора
    if current_dept:
        builder.button(
            text="⬅️ На уровень выше",
            callback_data=OrgTreeCallback(
                action="up",
                dept_id=current_dept.parent_id,
                emp_id=None,
                target_role=target_role
            )
        )

    # Если роль допускает множественный выбор (recipients/executors), добавляем кнопку "Готово"
    if target_role in ("recipients", "executors") and selected_ids:
        builder.button(
            text=f"🏁 Готово (выбрано: {len(selected_ids)})",
            callback_data=OrgTreeCallback(
                action="done",
                dept_id=None,
                emp_id=None,
                target_role=target_role
            )
        )

    builder.button(text="❌ Отмена", callback_data="cancel_doc_creation")
    builder.adjust(1)
    return builder.as_markup()