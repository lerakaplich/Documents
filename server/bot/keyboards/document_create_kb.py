from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from server.app.database.document_models import DocumentType


def get_types_keyboard(types: list[DocumentType]) -> ReplyKeyboardMarkup:
    """Динамическая клавиатура с типами документов из БД + кнопка Отмена"""
    keyboard = []

    row = []
    for doc_type in types:
        row.append(KeyboardButton(text=doc_type.name))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Добавляем стандартную кнопку отмены
    keyboard.append([KeyboardButton(text="❌ Отмена")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите тип документа..."
    )


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_doc_creation")
    return builder.as_markup()


def get_skip_or_cancel_keyboard(step_name: str) -> InlineKeyboardMarkup:
    """Клавиатура для пропуска необязательных шагов"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⏩ Пропустить", callback_data=f"skip_step:{step_name}")
    builder.button(text="❌ Отмена", callback_data="cancel_doc_creation")
    builder.adjust(1)
    return builder.as_markup()


def get_attachments_keyboard(has_files: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для шага отправки вложений."""
    btn_text = "✅ Завершить и продолжить" if has_files else "⏩ Пропустить шаг"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, callback_data="attachments_finish")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_doc_creation")]
        ]
    )