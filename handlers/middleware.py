import logging
from typing import Dict, Any, Callable, Awaitable
from aiogram import types, Bot, BaseMiddleware
from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.dispatcher.event.bases import CancelHandler
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods.base import TelegramType, Response, TelegramMethod
from aiogram.types import InlineKeyboardMarkup, TelegramObject
from aiogram.utils.i18n import gettext as _, I18nMiddleware

from database.services.group_subscription_plan_service import GroupSubscriptionPlanService
from database.services.user_service import UserService
from utils.create_bot import i18n
from utils.utils import translate_kb
from keyboards.client_kb import main_kb


from functools import wraps


# class HiddenUser(BaseMiddleware):
#     async def __call__(
#             self,
#             handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
#             event: TelegramObject,
#             data: Dict[str, Any],
#     ) -> Any:
#         # Можна залишити порожнім або викликати наступний middleware
#         return await handler(event, data)
#
#     async def on_process_message(self, message: types.Message, data):
#         from keyboards.client_kb import main_kb
#
#         if not message.from_user.username:
#             await message.answer(text=_(
#                 "Щоб користуватись ботом потрібно створити або зробити публічним юзернейм у вашому телеграм акаунті."),
#                 reply_markup=main_kb)
#             raise CancelHandler()
#
#     async def on_process_callback_query(self, query: types.CallbackQuery, data):
#         from keyboards.client_kb import main_kb
#         if not query.from_user.username:
#             await query.message.answer(
#                 text=_(
#                     "Щоб користуватись ботом потрібно створити або зробити публічним юзернейм у вашому телеграм акаунті."),
#                 reply_markup=main_kb)
#             raise CancelHandler()


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
        chat = getattr(event, 'from_user', None)
        if chat:
            user_id = chat.id
            user = await UserService.get_user(user_id)
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


# TODO: Накладіть цей декоратор на ваші функції, які вимагають підписки. Приклад використання: @subscription_group_required("auction", "ads")
def subscription_group_required(*subscription_types: List[str]):
    """
    Декоратор для функцій, які вимагають підписку на групу. Перевіряє наявність підписки у групи, з якої було викликано
    функцію. Якщо підписка наявна, викликає функцію.

    :param subscription_types: Список типів підписок, які вимагаються для доступу до функції.
    Доступні значення: "free_trial", "auction", "ads".
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(message: Message, *args, **kwargs):
            chat_subscription = await GroupSubscriptionPlanService.get_subscription(
                message.chat.id)  # Заміна на вашу функцію отримання групи

            if "free_trial" in subscription_types:
                if chat_subscription.free_trial or datetime.utcnow().timestamp() < chat_subscription.free_trial:
                    # Ця функція доступна для груп з активним пробним періодом.
                    return await func(message, *args, **kwargs)

            if "auction" in subscription_types:
                if chat_subscription.auction_paid:
                    # Ця функція доступна для груп з активною підпискою на лоти.
                    return await func(message, *args, **kwargs)

            if "ads" in subscription_types:
                if chat_subscription.ads_paid:
                    # Ця функція доступна для груп з активною підпискою на оголошення.
                    return await func(message, *args, **kwargs)

            return None

        return wrapper

    return decorator


def require_username(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Отримання `message` або `callback_query` з аргументів
        for arg in args:
            if isinstance(arg, Message):
                user = arg.from_user
                if not user.username:
                    await arg.answer(
                        text=_("Щоб користуватись ботом потрібно створити або зробити публічним юзернейм у вашому телеграм акаунті."),
                        reply_markup=main_kb
                    )
                    return None
                break
            elif isinstance(arg, types.CallbackQuery):
                user = arg.from_user
                if not user.username:
                    await arg.answer(
                        text=_("Щоб користуватись ботом потрібно створити або зробити публічним юзернейм у вашому телеграм акаунті."),
                        show_alert=True  # Показує сповіщення в області callback
                    )
                    return None
                break
        # Якщо юзернейм є, виконуємо основну функцію
        return await func(*args, **kwargs)
    return wrapper
