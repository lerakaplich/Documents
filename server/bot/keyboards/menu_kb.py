from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from server.bot.keyboards.texts import CANCEL_TEXT, MenuButton


def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MenuButton.NEW_DOCUMENT), KeyboardButton(text=MenuButton.PHOTO_TO_TIFF)],
            [KeyboardButton(text=MenuButton.OVERTIMES), KeyboardButton(text=MenuButton.SUPPORT)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие из меню...",
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_TEXT)]],
        resize_keyboard=True,
        input_field_placeholder="Для возврата нажмите кнопку...",
    )