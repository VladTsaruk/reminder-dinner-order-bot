import asyncio
import logging
from config import bot, dp
from handlers import router
from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)

async def main():
    dp.include_router(router)
    
    # Запуск планувальника завдання
    start_scheduler()
    
    print("Бот успішно запущений з підтримкою MongoDB!")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())