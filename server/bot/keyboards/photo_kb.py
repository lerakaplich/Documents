from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class PhotoCallback(CallbackData, prefix="photo"):
    action: str  # "convert" | "reset" | "cancel"


def get_photo_collect_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Собрать TIFF", callback_data=PhotoCallback(action="convert"))
    builder.button(text="🗑 Сбросить", callback_data=PhotoCallback(action="reset"))
    builder.button(text="❌ Отмена", callback_data=PhotoCallback(action="cancel"))
    builder.adjust(1, 2)
    return builder.as_markup()