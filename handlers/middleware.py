import logging
from typing import Dict, Any, Optional, List, Type
from aiogram import types, Bot, BaseMiddleware, loggers
from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.dispatcher.event.bases import CancelHandler
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods.base import TelegramType, Response, TelegramMethod
from aiogram.types import InlineKeyboardMarkup, TelegramObject
# from aiogram.utils.i18n import I18nMiddleware
from aiogram.utils.i18n import gettext as _, I18nMiddleware

from utils.create_bot import i18n
from utils.utils import translate_kb


class HiddenUser(BaseMiddleware):
    async def on_process_message(self, message: types.Message, data):
        from keyboards.client_kb import main_kb

        if not message.from_user.username:
            await message.answer(text=_(
                "Щоб користуватись ботом потрібно створити або зробити публічним юзернейм у вашому телеграм акаунті."),
                reply_markup=main_kb)
            raise CancelHandler()

    async def on_process_callback_query(self, query: types.CallbackQuery, data):
        from keyboards.client_kb import main_kb
        if not query.from_user.username:
            await query.message.answer(
                text=_(
                    "Щоб користуватись ботом потрібно створити або зробити публічним юзернейм у вашому телеграм акаунті."),
                reply_markup=main_kb)
            raise CancelHandler()


class ChangeLanguageMiddleware(BaseRequestMiddleware):
    async def __call__(
            self,
            make_request: NextRequestMiddlewareType[TelegramType],
            bot: "Bot",
            method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        kb: InlineKeyboardMarkup = getattr(method, 'reply_markup', None)
        if kb:
            user_id = getattr(method, 'chat_id', None)
            await translate_kb(kb, i18n.current_locale, user_id)
        try:
            return await make_request(bot, method)
        except TelegramBadRequest as err:
            logging.info(err)


class Localization(I18nMiddleware):
    async def get_locale(self, event: TelegramObject, data: Dict[str, Any]) -> str:
        from database.db_manage import get_user
        chat = getattr(event, 'from_user', None)
        if chat:
            user_id = chat.id
            user = await get_user(user_id)
            if not user:
                return 'en'
            locale = user.language
        else:
            locale = 'en'
        return locale



# TODO: Можливо це винести в окремий файл?
import functools
from datetime import datetime
from typing import Callable, List
from aiogram.types import Message
from database.db_manage import get_chat_record


# TODO: Накладіть цей декоратор на ваші функції, які вимагають підписки. Приклад використання: @subscription_group_required("auction", "ads")
def subscription_group_required(*subscription_types: List[str]):
    """
    Декоратор для перевірки наявності необхідної підписки.

    :param subscription_types: Список типів підписок, які необхідно перевірити ("auction", "ads", "free_trial").
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(message: Message, *args, **kwargs):
            chat = await get_chat_record(message.chat.id)  # Заміна на вашу функцію отримання групи

            if "free_trial" in subscription_types:
                if not chat.free_trial or datetime.utcnow().timestamp() > chat.free_trial:
                    # Пробна підписка для цієї групи закінчилася. Оформіть підписку, щоб продовжити.
                    print("Пробна підписка для цієї групи закінчилася. Оформіть підписку, щоб продовжити.") # TODO: delete
                    return

            if "auction" in subscription_types:
                if not chat.auction_paid:
                    # Ця функція доступна лише для груп з активною підпискою на лоти.
                    print("Ця функція доступна лише для груп з активною підпискою на лоти.") # TODO: delete
                    return

            if "ads" in subscription_types:
                if not chat.ads_paid:
                    # Ця функція доступна лише для груп з активною підпискою на оголошення.
                    print("Ця функція доступна лише для груп з активною підпискою на інші функції.") # TODO: delete
                    return

            # Якщо перевірки успішні, виконуємо основну функцію
            return await func(message, *args, **kwargs)

        return wrapper

    return decorator

