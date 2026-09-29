# server/bot/keyboards/tags_kb.py

import math
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_tags_keyboard(
        tags: list,
        selected_tag_ids: set[int],
        page: int,
        total_count: int,
        per_page: int = 6
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # 1. Кнопки тегов (по 2 в ряд)
    for tag in tags:
        is_selected = tag.id in selected_tag_ids
        icon = "☑️" if is_selected else "🔲"
        btn_text = f"{icon} {tag.name}"
        builder.button(
            text=btn_text,
            callback_data=f"tag_toggle:{tag.id}:{page}"
        )
    builder.adjust(2)  # по 2 тега на строку

    # 2. Навигация пагинации (если страниц > 1)
    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"tags_page:{page - 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="⛔️", callback_data="noop"))

    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))

    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"tags_page:{page + 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="⛔️", callback_data="noop"))

    builder.row(*nav_buttons)

    # 3. Кнопка завершения / пропуска
    confirm_text = f"✅ Готово ({len(selected_tag_ids)})" if selected_tag_ids else "⏩ Пропустить"
    builder.row(
        InlineKeyboardButton(
            text=confirm_text,
            callback_data="tags_confirm"
        )
    )

    return builder.as_markup()