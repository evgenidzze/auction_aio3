import asyncio
import logging

from aiogram.methods import DeleteWebhook
from aiogram.types import BotCommand

from create_bot import dp, bot, i18n
from database.db_manage import on_startup
from handlers.admin import register_admin_handlers
from handlers.client_handlers import router, register_client_handlers
from handlers.middleware import Localization, ChangeLanguageMiddleware


async def main():
    logging.basicConfig(level=logging.INFO, filename='logs.log')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(console_handler)
    logging.getLogger('apscheduler').setLevel(logging.DEBUG)
    Localization(i18n=i18n).setup(router)
    bot.session.middleware(ChangeLanguageMiddleware())
    register_client_handlers(router)
    register_admin_handlers(router)
    dp.startup.register(on_startup)
    await bot(DeleteWebhook(drop_pending_updates=True))
    dp.include_router(router)
    await bot.set_my_commands([BotCommand(command='start', description='Change language/Змінити мову'),
                               BotCommand(command='main_menu', description='Main menu/Головне меню')])
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
