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
        from keyboards.kb import main_kb

        if not message.from_user.username:
            await message.answer(text=_(
                "Щоб користуватись ботом потрібно створити або зробити публічним юзернейм у вашому телеграм акаунті."),
                reply_markup=main_kb)
            raise CancelHandler()

    async def on_process_callback_query(self, query: types.CallbackQuery, data):
        from keyboards.kb import main_kb
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
            logging.info(f"Telegram server says - Bad Request: chat {getattr(method, 'chat_id', None)} not found")


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
