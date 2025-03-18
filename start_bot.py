import asyncio
from aiogram.types import BotCommand
from database.services.base import on_startup
from handlers.client import general_handlers, lot_handlers, adv_handlers
from utils.create_bot import dp, bot, i18n, scheduler
from handlers import admin
from handlers.middleware import Localization, ChangeLanguageMiddleware
from utils.utils import set_logging
from aiogram import Router


async def main():
    set_logging()

    router = Router()
    router.include_router(lot_handlers.router)
    router.include_router(admin.router)
    router.include_router(adv_handlers.router)
    router.include_router(general_handlers.router)

    Localization(i18n=i18n).setup(router)
    bot.session.middleware(ChangeLanguageMiddleware())
    dp.startup.register(on_startup)
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([BotCommand(command='start', description='Change language/Змінити мову'),
                               BotCommand(command='main_menu', description='Main menu/Головне меню'),
                               BotCommand(command='admin', description='Group owner menu/Меню власника групи'),
                               ])
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
