import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Не задан TELEGRAM_BOT_TOKEN в переменных окружения!")

# URL локального или внешнего API Telegram
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError("Не задан JWT_SECRET_KEY в переменных окружения!")

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))


# Шаблоны системных уведомлений для сотрудников МАЗ
MSG_TEMPLATE_NEW_REVISION = (
    "📝 В документе №{reg_number} «{title}» внесены изменения.\n"
    "Пожалуйста, ознакомьтесь с актуальной версией."
)

MSG_TEMPLATE_NEW_DOCUMENT = (
    "📥 Вам направлен новый документ №{reg_number} «{title}» на рассмотрение."
)