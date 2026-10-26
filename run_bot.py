import asyncio
import sys
from server.bot.main import main

if __name__ == "__main__":
    # Настройка для Windows (на всякий случай дублируем здесь)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")