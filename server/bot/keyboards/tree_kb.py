# server/bot/keyboards/tree_kb.py
from typing import Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from server.app.database.employee_models import Department, Employee, Organization
from server.bot.states.org_tree_cb import OrgTreeCallback


def build_org_tree_keyboard(
        organizations: list[Organization] = None,
        departments: list[Department] = None,
        employees: list[Employee] = None,
        current_org: Optional[Organization] = None,
        current_dept: Optional[Department] = None,
        role: str = "receivers",  # "source" | "receivers" | "executors"
        selected_org_ids: list[int] = None,
        selected_dept_ids: list[int] = None,
        selected_emp_ids: list[int] = None,
        disabled_emp_ids: list[int] = None,
        page: int = 1,
        page_size: int = 6,  # 6 элементов на страницу, т.к. некоторые строки двойные
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    selected_org_ids = selected_org_ids or []
    selected_dept_ids = selected_dept_ids or []
    selected_emp_ids = selected_emp_ids or []
    disabled_emp_ids = disabled_emp_ids or []

    layout = []

    # ------------------------------------------------------------------
    # УРОВЕНЬ 1: Список организаций
    # ------------------------------------------------------------------
    if not current_org and not current_dept:
        items = organizations or []
        total_pages = max(1, (len(items) + page_size - 1) // page_size)
        current_page_items = items[(page - 1) * page_size: page * page_size]

        for org in current_page_items:
            is_sel = org.id in selected_org_ids
            mark = "✅ " if is_sel else "🏢 "

            # Кнопка 1: Просмотр содержимого организации
            builder.button(
                text=f"{mark}{org.name}",
                callback_data=OrgTreeCallback(act="open_org", org_id=org.id, role=role, page=1)
            )

            # Кнопка 2: Выбор организации целиком (только для source и receivers)
            if role == "source":
                builder.button(
                    text="🎯 Выбрать",
                    callback_data=OrgTreeCallback(act="select_org_target", org_id=org.id, role=role, page=page)
                )
                layout.append(2)
            elif role == "receivers":
                action_text = "✅ Выбрана" if is_sel else "➕ Всю"
                builder.button(
                    text=action_text,
                    callback_data=OrgTreeCallback(act="select_org_target", org_id=org.id, role=role, page=page)
                )
                layout.append(2)
            else:
                # Для executors выбираются только люди, поэтому организация — просто папка
                layout.append(1)

    # ------------------------------------------------------------------
    # УРОВЕНЬ 2 и 3: Отделы / Подотделы / Сотрудники
    # ------------------------------------------------------------------
    else:
        c_org_id = current_org.id if current_org else None
        c_dept_id = current_dept.id if current_dept else None

        # Объединяем подотделы и сотрудников в один список для пагинации
        items = [("dept", d) for d in (departments or [])] + [("emp", e) for e in (employees or [])]
        total_pages = max(1, (len(items) + page_size - 1) // page_size)
        current_page_items = items[(page - 1) * page_size: page * page_size]

        for item_type, item in current_page_items:
            if item_type == "dept":
                is_sel = item.id in selected_dept_ids
                mark = "☑️ " if is_sel else "📁 "

                # Кнопка 1: Просмотр отдела
                builder.button(
                    text=f"{mark}{item.name}",
                    callback_data=OrgTreeCallback(act="open_dept", org_id=c_org_id, dept_id=item.id, role=role, page=1)
                )

                # Кнопка 2: Выбор отдела целиком (только для receivers)
                if role == "receivers":
                    action_text = "✅ Выбран" if is_sel else "➕ Отдел"
                    builder.button(
                        text=action_text,
                        callback_data=OrgTreeCallback(
                            act="select_dept_target", org_id=c_org_id, dept_id=item.id, role=role, page=page
                        )
                    )
                    layout.append(2)
                else:
                    layout.append(1)

            elif item_type == "emp":
                # Сотрудников нельзя выбирать в роли receivers
                if role == "receivers":
                    continue

                if item.id in disabled_emp_ids:
                    builder.button(
                        text=f"⛔️ {item.last_name} {item.first_name[0]}.",
                        callback_data=OrgTreeCallback(act="ignore", role=role, page=page)
                    )
                else:
                    is_sel = item.id in selected_emp_ids
                    mark = "☑️ " if is_sel else "👤 "
                    builder.button(
                        text=f"{mark}{item.last_name} {item.first_name}",
                        callback_data=OrgTreeCallback(
                            act="select_emp", org_id=c_org_id, dept_id=c_dept_id, emp_id=item.id, role=role, page=page
                        )
                    )
                layout.append(1)

    # ------------------------------------------------------------------
    # ПАГИНАЦИЯ (⬅️ 📄 x/y ➡️)
    # ------------------------------------------------------------------
    if total_pages > 1:
        c_org_id = current_org.id if current_org else None
        c_dept_id = current_dept.id if current_dept else None

        if page > 1:
            builder.button(
                text="⬅️",
                callback_data=OrgTreeCallback(act="page", role=role, org_id=c_org_id, dept_id=c_dept_id, page=page - 1)
            )
        else:
            builder.button(text="⏹", callback_data="ignore")

        builder.button(text=f"📄 {page}/{total_pages}", callback_data="ignore")

        if page < total_pages:
            builder.button(
                text="➡️",
                callback_data=OrgTreeCallback(act="page", role=role, org_id=c_org_id, dept_id=c_dept_id, page=page + 1)
            )
        else:
            builder.button(text="⏹", callback_data="ignore")

        layout.append(3)

    # ------------------------------------------------------------------
    # УПРАВЛЕНИЕ И НАВИГАЦИЯ
    # ------------------------------------------------------------------
    nav_buttons_count = 0

    if current_dept:
        builder.button(
            text="🔙 Назад",
            callback_data=OrgTreeCallback(
                act="up",
                org_id=current_org.id if current_org else None,
                dept_id=current_dept.parent_id,
                role=role,
                page=1
            )
        )
        nav_buttons_count += 1
    elif current_org:
        builder.button(
            text="🔙 К организациям",
            callback_data=OrgTreeCallback(act="up", role=role, page=1)
        )
        nav_buttons_count += 1

    # Показываем "Завершить" или "Пропустить"
    total_selected = len(selected_org_ids) + len(selected_dept_ids) + len(selected_emp_ids)

    if role == "receivers" and total_selected > 0:
        builder.button(
            text=f"🏁 Готово ({total_selected})",
            callback_data=OrgTreeCallback(act="done", role=role)
        )
        nav_buttons_count += 1

    elif role == "executors":
        if total_selected > 0:
            builder.button(
                text=f"🏁 Готово ({total_selected})",
                callback_data=OrgTreeCallback(act="done", role=role)
            )
        else:
            builder.button(
                text="⏭ Пропустить (без исполнителей)",
                callback_data=OrgTreeCallback(act="done", role=role)
            )
        nav_buttons_count += 1

    builder.button(text="❌ Отмена", callback_data=OrgTreeCallback(act="cancel", role=role))
    nav_buttons_count += 1

    layout.append(nav_buttons_count)
    builder.adjust(*layout)
    return builder.as_markup()