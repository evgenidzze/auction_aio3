import asyncio

from aiogram.methods import DeleteWebhook
from aiogram.types import BotCommand

from database.services.base import on_startup
from utils.create_bot import dp, bot, i18n, scheduler
from handlers import admin, client_handlers
from handlers.middleware import Localization, ChangeLanguageMiddleware
from utils.utils import set_logging
from aiogram import Router


async def main():
    set_logging()

    router = Router()
    router.include_router(admin.router)  # Include admin handlers
    router.include_router(client_handlers.router)  # Include client handlers

    Localization(i18n=i18n).setup(router)
    bot.session.middleware(ChangeLanguageMiddleware())
    dp.startup.register(on_startup)
    await bot(DeleteWebhook(drop_pending_updates=True))
    dp.include_router(router)
    await bot.set_my_commands([BotCommand(command='start', description='Change language/Змінити мову'),
                               BotCommand(command='main_menu', description='Main menu/Головне меню'),
                               BotCommand(command='admin', description='Group owner menu/Меню власника групи'),
                               ])
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
