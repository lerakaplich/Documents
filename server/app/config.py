import os

# Токен бота (на проде заберем из env, сейчас можно оставить дефолт для тестов)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ")

# URL локального или внешнего API Telegram
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Шаблоны системных уведомлений для сотрудников МАЗ
MSG_TEMPLATE_NEW_REVISION = (
    "📝 В документе №{reg_number} «{title}» внесены изменения.\n"
    "Пожалуйста, ознакомьтесь с актуальной версией."
)

MSG_TEMPLATE_NEW_DOCUMENT = (
    "📥 Вам направлен новый документ №{reg_number} «{title}» на рассмотрение."
)