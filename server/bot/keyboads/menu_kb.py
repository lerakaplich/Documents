from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu() -> ReplyKeyboardMarkup:
    """Генерирует главное меню для авторизованного сотрудника"""
    keyboard = [
        [
            KeyboardButton(text="📄 Новый документ"),
            KeyboardButton(text="📸 Распознать по фото")
        ],
        [
            KeyboardButton(text="⏳ Мои переработки"),
            KeyboardButton(text="🆘 Поддержка")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,  # Кнопки будут компактными под размер экрана
        input_field_placeholder="Выберите действие из меню..."
    )

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для отмены текущего действия (FSM-сценария)"""
    keyboard = [
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Для возврата нажмите кнопку..."
    )