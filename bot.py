import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from middlewares.subscribe import SubscribeMiddleware
from handlers import start, camp, admin, ai_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("🚀 تهيئة البوت الأسطوري...")
    await init_db()
    logger.info("✅ قاعدة البيانات SQLite جاهزة")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(SubscribeMiddleware())
    dp.callback_query.middleware(SubscribeMiddleware())

    dp.include_router(start.router)
    dp.include_router(camp.router)
    dp.include_router(admin.router)
    dp.include_router(ai_handler.router)

    logger.info("🤖 البوت شغال ومستني الرسائل...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
