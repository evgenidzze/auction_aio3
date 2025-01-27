import datetime
import locale
import logging
import time
from copy import deepcopy
from random import randint
from typing import List

from aiogram import Router, types, F
from aiogram.enums import ContentType
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.deep_linking import create_start_link

import database.models.advertisement
import database.models.lot
from database.services.advertisement_service import AdvertisementService
from database.services.base import delete_record_by_id
from database.services.group_channel_service import GroupChannelService
from database.services.lot_service import LotService
from database.services.user_service import UserService
from utils.aiogram_media_group import media_group_handler
from utils.config import DEV_ID

from utils.create_bot import scheduler, _, i18n, bot, job_stores
import keyboards.client_kb as client_kb
from utils.paypal import get_order_status, create_order
import utils.utils

from handlers.middleware import subscription_group_required, require_username

locale.setlocale(locale.LC_ALL, 'uk_UA.utf8')
router = Router()

message = router.message
callback_query = router.callback_query


class FSMClient(StatesGroup):
    lot_group_id = State()
    user_chat_id = State()
    repost_count = State()
    repost_count_answer = State()
    new_desc_exist = State()
    change_ad = State()
    adv_sub_seconds = State()
    change_media_ad = State()
    city_ad = State()
    media_ad = State()
    description_ad = State()
    delete_answer = State()
    choose_answer = State()
    send_answer = State()
    choose_question = State()
    question = State()
    change_city = State()
    sniper_time = State()
    city = State()
    currency = State()
    change_price_steps = State()
    change_media = State()
    change_desc = State()
    change_start_price = State()
    change_lot_time = State()
    change_lot = State()
    price_steps = State()
    media = State()
    lot_time_living = State()
    price = State()
    language = State()
    description = State()
    adv_group_id = State()


########################################################################################################################
#                                              MENU CLIENT COMMANDS                                                    #
########################################################################################################################


@message(CommandStart(), utils.utils.IsPrivateChatFilter())
async def start(message: types.Message, state: FSMContext, **kwargs):
    """/start"""
    for job in scheduler.get_jobs():
        logging.info(f'{job.id}-{job}-{job.kwargs}')
    await state.set_state(FSMClient.language)
    text = _('<b>Оберіть мову / Choose a language:</b>')
    if isinstance(message, types.Message):
        await message.answer(text=text,
                             reply_markup=client_kb.language_kb)
    elif isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text=text,
                                        reply_markup=client_kb.language_kb)


@callback_query(FSMClient.language)
@callback_query(F.data == 'main_menu')
@message(Command('main_menu'), utils.utils.IsPrivateChatFilter())
async def main_menu(call, state: FSMContext, **kwargs):
    """/main_menu"""
    clean_text = "Вітаю, <b>{first_name}!</b><a href='https://telegra.ph/file/3f6168cc5f94f115331ac.png'>⠀</a>\n"
    text = _(clean_text).format(first_name=call.from_user.username)
    if isinstance(call, types.CallbackQuery):
        if call.data in ('en', 'uk'):
            await UserService.insert_or_update_user(telegram_id=call.from_user.id, language=call.data)
            text = _(clean_text, locale=call.data).format(first_name=call.from_user.username)
            i18n.current_locale = call.data
        await call.message.edit_text(text=text,
                                     reply_markup=client_kb.main_kb)
    else:
        await call.answer(text=text, reply_markup=client_kb.main_kb)
    await state.clear()


@callback_query(F.data == 'auction')
async def auction_menu(call: types.CallbackQuery, state: FSMContext, **kwargs):
    await call.message.edit_text(text=_('Ви обрали 🏷 Аукціон'), reply_markup=client_kb.auction_kb)
    await state.clear()


@callback_query(F.data == 'my_auctions')
async def my_auctions(call: types.CallbackQuery, state: FSMContext, **kwargs):
    lots = await LotService.get_user_lots(call.from_user.id)
    kb = await utils.utils.create_user_lots_kb(lots)
    kb.inline_keyboard.extend([[client_kb.create_auction_btn], [client_kb.back_to_auction_btn]])
    await state.set_state(FSMClient.change_lot)
    await call.message.edit_text(text=_('Оберіть існуючий аукціон або створіть новий:'),
                                 reply_markup=kb)


@callback_query(F.data == 'groups_and_channels')
async def groups_and_channels(call: types.CallbackQuery, **kwargs):
    await call.message.edit_text(text=_('Ви обрали 👥 Групи та канали'), reply_markup=client_kb.group_channels_kb)


@callback_query(F.data == 'other_channels_groups')
async def other_channels_groups(call: types.CallbackQuery, **kwargs):
    other_chats = await GroupChannelService.get_all_groups()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=chat.chat_name, url=chat.chat_link)] for chat in
                         other_chats])
    kb.inline_keyboard.extend([[client_kb.back_group_channels_btn]])
    await call.message.edit_text(text=_('Список каналів у яких працює бот:'),
                                 reply_markup=kb)


########################################################################################################################
#                                              AUCTION COMMANDS                                                        #
########################################################################################################################


@callback_query(F.data == 'create_auction', utils.utils.IsMessageType(message_type=[ContentType.TEXT]))
@require_username
async def lot_group(call: types.CallbackQuery, state: FSMContext, **kwargs):
    chats = await GroupChannelService.get_all_groups()  # замінити на групи користувача
    kb = await utils.utils.generate_chats_kb(chats)
    kb.inline_keyboard.extend([[client_kb.reset_to_auction_menu_btn]])
    await state.set_state(FSMClient.lot_group_id)
    await call.message.edit_text(text=_('У якій групі бажаєте опублікувати лот?'), reply_markup=kb)


@callback_query(FSMClient.lot_group_id)
async def ask_city(call: types.CallbackQuery, state: FSMContext, **kwargs):
    await state.update_data(lot_group_id=call.data)
    user = await UserService.get_user(call.from_user.id)
    if user.is_blocked:
        await bot.send_message(chat_id=call.from_user.id, text=_('Вас було заблоковано за порушення правил.'))
        return
    await state.set_state(FSMClient.city)
    await call.message.edit_text(text=_('🌆 Вкажіть ваше місто:'),

                                 reply_markup=client_kb.reset_to_auction_menu_kb)


@message(FSMClient.city)
async def ask_currency(message: types.Message, state: FSMContext, **kwargs):
    await state.update_data(city=message.text)
    await state.set_state(FSMClient.currency)
    await message.answer(text=_('🫰🏼 Оберіть валюту:'),

                         reply_markup=client_kb.currency_kb)


@callback_query(FSMClient.currency)
async def ask_description(call: types.CallbackQuery, state: FSMContext, **kwargs):
    await state.update_data(currency=call.data)
    await state.set_state(FSMClient.description)
    await call.message.edit_text(text=_('📝 Напишіть опис для лоту:\n\n'
                                        '<i>Наприклад: Навушники Marshall Major IV Bluetooth Black</i>'),

                                 reply_markup=client_kb.reset_to_auction_menu_kb)


@message(FSMClient.description, utils.utils.IsMessageType(message_type=[ContentType.TEXT]))
async def ask_price(message: types.Message, state: FSMContext, **kwargs):
    await state.update_data(description=message.text)
    await state.set_state(FSMClient.price)
    data = await state.get_data()
    currency = data.get('currency')
    await message.answer(text=_('💰 Вкажіть стартову ціну в {currency}:').format(currency=currency),
                         reply_markup=client_kb.reset_to_auction_menu_kb)


@message(FSMClient.price)
async def ask_price_steps(message: types.Message, state: FSMContext, **kwargs):
    if message.text.isdigit() or await state.get_state() == 'FSMClient:price_steps':
        if await state.get_state() != 'FSMClient:price_steps':
            await state.update_data(price=message.text)
        await state.set_state(FSMClient.price_steps)
        await message.answer(text=_('Напишіть крок ставки через пробіл (від 1 до 3 кроків):\n'
                                    'Наприклад: 500 1000 1500'), reply_markup=client_kb.reset_to_auction_menu_kb)
    else:
        await message.answer(text=_('❌ Потрібно ввести числове значення.'))
        await ask_price(message, state)


@message(FSMClient.price_steps)
async def ask_lot_living(message: types.Message, state: FSMContext, **kwargs):
    if all(step.isdigit() for step in message.text.split(' ')):
        await state.update_data(price_steps=message.text)
        await state.set_state(FSMClient.lot_time_living)
        kb = deepcopy(client_kb.lot_time_kb)
        kb.inline_keyboard.extend([[client_kb.reset_to_auction_menu_btn]])
        await message.answer(text=_('🕙 Скільки буде тривати аукціон?'), reply_markup=kb)
    else:
        await message.answer(text=_('❌ Потрібно ввести числові значення.'))
        await ask_price_steps(message, state)


@callback_query(FSMClient.lot_time_living)
async def ask_media(call: [types.CallbackQuery, types.Message], state: FSMContext, **kwargs):
    text = _('📸 Надішліть фото і відео:\n'
             '<i>До 5 фото та до 1 відео</i>')
    if isinstance(call, types.CallbackQuery):
        await state.update_data(lot_time_living=call.data)
        await call.message.edit_text(text=text, reply_markup=client_kb.reset_to_auction_menu_kb)
    else:
        await call.answer(text=text, reply_markup=client_kb.reset_to_auction_menu_kb)

    await state.set_state(FSMClient.media)


@message(FSMClient.media)
@message(FSMClient.change_media)
@callback_query(F.data == 'back_to_ready')
@media_group_handler
async def ready_lot(messages: List[types.Message], state: FSMContext, **kwargs):
    state_name = await state.get_state()
    if isinstance(messages[0], types.Message) and 'media' in state_name:
        videos_id, photos_id = await utils.utils.gather_media_from_messages(messages=messages, state=state)
        if await utils.utils.is_media_count_allowed(photos_id, videos_id, messages, client_kb.reset_to_auction_menu_kb):
            await state.update_data(videos_id=videos_id)
            await state.update_data(photos_id=photos_id)
        else:
            return
    fsm_data = await state.get_data()
    kb = deepcopy(client_kb.ready_to_publish_kb)
    kb.inline_keyboard.extend([[client_kb.cancel_btn, client_kb.publish_btn]])
    text = '⬆️ Лот готовий до публікації!\nПеревірте всю інформацію і натисніть <b>✅ Опублікувати</b>, коли будете готові.'
    if isinstance(messages[0], types.Message):
        msg = await utils.utils.send_post_fsm(fsm_data, messages[0].from_user.id)
        await msg.reply(text=_(text), reply_markup=kb)
    elif isinstance(messages[0], types.CallbackQuery):
        if messages[0].data != 'back_to_ready' and await state.get_state() and 'steps' not in await state.get_state():
            await utils.utils.send_post_fsm(fsm_data, messages[0].from_user.id)
            await messages[0].message.reply_to_message.reply(text=text, reply_markup=kb)
        else:
            await messages[0].message.edit_text(text=_(text), reply_markup=kb)


@callback_query(F.data == 'publish_lot')
async def lot_publish(message: types.CallbackQuery, state: FSMContext, **kwargs):
    fsm_data = await state.get_data()
    video_id = fsm_data.get('video_id')
    photo_id = fsm_data.get('photo_id')
    description = fsm_data.get('description')
    start_price = fsm_data.get('price')
    currency: str = fsm_data.get('currency')
    city: str = fsm_data.get('city')
    price_steps: str = fsm_data.get('price_steps')
    group_id = fsm_data.get('lot_group_id')
    group_chat = await bot.get_chat(group_id)
    new_lot_id = await LotService.create_lot(fsm_data, message.from_user.id)
    group_data = await GroupChannelService.get_group_record(group_id)
    await utils.utils.send_post(message.from_user.id, group_data.owner_telegram_id, photo_id, video_id, description,
                                start_price,
                                price_steps, currency=currency, city=city, lot_id=new_lot_id, moder_review=True,
                                videos=fsm_data.get('videos_id'), photos=fsm_data.get('photos_id'))
    await message.message.edit_text(
        text=_("✅ Лот відправлено на модерацію, незабаром він з'явиться у каналі <b><a href='{invite_link}'>"
               "{username}</a></b>.").format(invite_link=group_chat.invite_link, username=group_chat.title),
        reply_markup=client_kb.main_kb)


########################################################################################################################
#                                              ADVERTISEMENT COMMANDS                                                  #
########################################################################################################################

@callback_query(F.data == 'ad_menu')
async def add_menu(call: types.CallbackQuery, **kwargs):
    await call.message.edit_text(text=_('Ви обрали 📣 Оголошення'), reply_markup=client_kb.add_menu_kb)


@callback_query(F.data == 'my_ads')
async def my_ads(call: types.CallbackQuery, state: FSMContext, **kwargs):
    ads = await AdvertisementService.get_user_ads(call.from_user.id)
    kb = await utils.utils.create_user_lots_kb(ads)
    kb.inline_keyboard.extend([[client_kb.create_advert_btn], [client_kb.back_to_ad_menu_btn]])
    await state.set_state(FSMClient.change_ad)
    await call.message.edit_text(text=_('Оберіть існуючe оголошення або створіть нове:'),
                                 reply_markup=kb)


@callback_query(F.data == 'create_ad')
@require_username
async def group_for_adv(call: types.CallbackQuery, state: FSMContext, **kwargs):
    await call.message.edit_text(text=_('Перевірка підписки...'))
    is_subscribed = await utils.utils.adv_sub_time_remain(call.from_user.id)
    redis_obj = job_stores.get('default')
    result = redis_obj.redis.get('payment')
    if is_subscribed or (result and result.decode('utf-8') != 'on'):
        chats = await GroupChannelService.get_all_groups()
        kb = await utils.utils.generate_chats_kb(chats)
        kb.inline_keyboard.extend([[client_kb.back_to_ad_menu_btn]])
        await state.set_state(FSMClient.adv_group_id)
        await call.message.edit_text(text='Оберіть групу в якій хочете виставити оголошення:', reply_markup=kb)
    elif await utils.utils.user_have_approved_adv_token(call.from_user.id):
        await UserService.update_user_sql(call.from_user.id, advert_subscribe_time=604800 + time.time())
    else:
        await call.message.edit_text(text=_('ℹ️ Щоб виставити оголошення, потрібно оформити підписку.'),
                                     reply_markup=client_kb.subscribe_adv_kb)
        await state.set_state(FSMClient.adv_sub_seconds)


# @callback_query(F.data == 'create_ad')
@callback_query(FSMClient.adv_group_id)
async def ask_description_ad(call: types.CallbackQuery, state: FSMContext, **kwargs):
    await state.update_data(adv_group_id=call.data)
    await call.message.edit_text(text=_('📝 Напишіть опис для оголошення:'),
                                 reply_markup=client_kb.reset_to_ad_menu_kb)
    await state.set_state(FSMClient.description_ad)


@message(FSMClient.description_ad, utils.utils.IsMessageType(message_type=[ContentType.TEXT]))
async def ask_city_ad(message: types.Message, state: FSMContext, **kwargs):
    if isinstance(message, types.Message):
        await state.update_data(description=message.text)
        await state.set_state(FSMClient.city_ad)
        await message.answer(text=_('🌆 Вкажіть ваше місто:'),

                             reply_markup=client_kb.reset_to_ad_menu_kb)


@message(FSMClient.city_ad, utils.utils.IsMessageType(message_type=[ContentType.TEXT]))
async def ask_media_ad(message: types.Message, state: FSMContext, **kwargs):
    text = _('📸 Надішліть фото і відео:\n'
             '<i>До 5 фото та до 1 відео</i>')
    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text=text, reply_markup=client_kb.reset_to_ad_menu_kb)
    else:
        await state.update_data(city=message.text)
        await message.answer(text=text, reply_markup=client_kb.reset_to_ad_menu_kb)
    await state.set_state(FSMClient.media_ad)


@message(FSMClient.media_ad)
@message(FSMClient.change_media_ad)
@callback_query(F.data == 'back_to_ready_ad')
@media_group_handler
async def save_media_ad(messages: List[types.Message], state: FSMContext, **kwargs):
    await state.update_data(is_ad=True)
    state_name = await state.get_state()
    if isinstance(messages[0], types.Message) and 'media' in state_name:
        videos_id, photos_id = await utils.utils.gather_media_from_messages(messages=messages, state=state)
        if await utils.utils.is_media_count_allowed(photos_id, videos_id, messages, client_kb.reset_to_auction_menu_kb):
            await state.update_data(videos_id=videos_id)
            await state.update_data(photos_id=photos_id)
            await state.set_state(FSMClient.repost_count_answer)
            if 'change' not in state_name:
                await messages[0].answer(text=_("✅ Медіа збережені.\n"
                                                "Бажаєте публікувати оголошення щоденно?"),
                                         reply_markup=client_kb.yes_no_kb)
            else:
                await save_repost_count(messages[0], state)
        else:
            return
    else:
        await save_repost_count(messages[0], state)
        return


@callback_query(F.data == 'publish_adv')
async def adv_publish(message, state, **kwargs):
    fsm_data = await state.get_data()
    video_id = fsm_data.get('video_id')
    photo_id = fsm_data.get('photo_id')
    description = fsm_data.get('description')
    group_id = fsm_data.get('adv_group_id')
    city: str = fsm_data.get('city')
    new_adv_id = await AdvertisementService.create_adv(message.from_user.id, fsm_data)
    try:
        channel = await bot.get_chat(group_id)
    except Exception as err:
        logging.info(f'{err} {group_id}')
        await bot.send_message(chat_id=message.from_user.id, text=str(err))
        return
    group_data = await GroupChannelService.get_group_record(group_id)
    await utils.utils.send_advert(user_id=message.from_user.id, send_to_id=group_data.owner_telegram_id,
                                  description=description, city=city,
                                  video_id=video_id, photo_id=photo_id,
                                  moder_review=True,
                                  advert_id=new_adv_id)
    await message.message.edit_text(
        text=_("✅ Оголошення відправлено не модерацію, незабаром воно з'явиться у каналі <b><a href='{invite_link}'>"
               "{username}</a></b>.").format(invite_link=channel.invite_link, username=channel.title),
        reply_markup=client_kb.main_kb)


@callback_query(F.data.startswith('bid'))
@require_username
async def make_bid(message: types.CallbackQuery, **kwargs):
    bid_data = message.data.split('_')
    lot_id = bid_data[2]
    lot = await LotService.get_lot(lot_id)
    if lot:
        last_bid = lot.last_bid
        owner_id = lot.owner_telegram_id
        last_bidder_id = lot.bidder_telegram_id
        bid_count = lot.bid_count
        currency = lot.currency
        group_id = lot.group_id

        user = await UserService.get_user(owner_id)
        anti_sniper_time: datetime.time = user.anti_sniper
        if str(message.from_user.id) == lot.owner_telegram_id and message.from_user.id != DEV_ID:
            await message.answer(text=_('❌ На свій лот не можна робити ставку.'))
            return
        job = scheduler.get_job(f'lot_{lot_id}')
        if job:
            cur_time = datetime.datetime.now().replace(tzinfo=None)
            next_run_time = job.next_run_time.replace(tzinfo=None)
            left_job_time: datetime.timedelta = next_run_time - cur_time
            left_minutes = int(left_job_time.total_seconds() // 60)
            if left_minutes <= anti_sniper_time.minute:
                new_next_run_time = cur_time + datetime.timedelta(minutes=anti_sniper_time.minute)
                """continue auction (uncomment)"""
                scheduler.modify_job(f'lot_{lot_id}', next_run_time=new_next_run_time)
            price = int(bid_data[1]) + last_bid
            await LotService.make_bid_sql(lot_id, price, bidder_id=message.from_user.id, bid_count=bid_count)
            lot_post = message.message
            caption = await utils.utils.new_bid_caption(lot_post.caption, message.from_user.first_name, price, currency,
                                                        owner_locale=user.language, bid_count=bid_count + 1)
            await bot.edit_message_caption(chat_id=group_id, message_id=lot_post.message_id, caption=caption,
                                           reply_markup=lot_post.reply_markup)
            await bot.send_message(chat_id=owner_id,
                                   text=_(
                                       "💸 Нова ставка на ваш лот!\n\n<a href='{lot_post}'><b>👉 Перейти до лоту.</b></a>").format(
                                       lot_post=lot_post.get_url()),

                                   reply_markup=client_kb.main_kb)
            if last_bidder_id:
                await bot.send_message(chat_id=last_bidder_id,
                                       text=_(
                                           "👋 Вашу ставку на лот <a href='{lot_post}'><b>{lot_name}</b></a> перебили.\n\n"
                                           "<a href='{lot_post}'><b>👉 Перейти до лоту.</b></a>").format(
                                           lot_post=lot_post.get_url(), lot_name=lot.description),
                                       reply_markup=client_kb.main_kb,
                                       )
            await message.answer(text=_('✅ Ставку прийнято!'))
        else:
            await message.answer(text=_('Лот ще не опубліковано.'))
    else:
        await message.answer(text=_('❌ Аукціон закінчено'))


@callback_query(F.data == 'help')
async def help_(call: types.CallbackQuery, **kwargs):
    await call.message.edit_text(text=_("По всім запитанням @Oleksandr_Polis\n\n"
                                        "<i>Що таке <a href='https://telegra.ph/Antisnajper-03-31'>"
                                        "<b>⏱ Антиснайпер?</b></a></i>\n"),
                                 reply_markup=client_kb.back_to_main_kb,
                                 disable_web_page_preview=True)


@callback_query(F.data == 'show_lot')
@callback_query(FSMClient.change_lot)
async def show_lot(message: types.CallbackQuery, state: FSMContext, **kwargs):
    lot_id = message.data
    if not (lot_id.isdigit()):
        data = await state.get_data()
        lot_id = data.get('change_lot')
    await state.update_data(change_lot=lot_id)

    lot = await LotService.get_lot(lot_id)
    video_id = lot.video_id
    photo_id = lot.photo_id
    description = lot.description
    start_price = lot.start_price
    price_steps = lot.price_steps
    currency = lot.currency
    city = lot.city
    await utils.utils.send_post(message.from_user.id, message.from_user.id, photo_id, video_id, description,
                                start_price,
                                price_steps, currency=currency, city=city, under_moderation=not lot.approved)
    await state.set_state(None)
    await message.message.answer(text=_('Бажаєте видалити лот?'), reply_markup=client_kb.delete_lot_kb)


@callback_query(F.data == 'show_ad')
@callback_query(FSMClient.change_ad)
async def show_ad(message: types.CallbackQuery, state: FSMContext, **kwargs):
    ad_id = message.data
    if not (ad_id.isdigit()):
        data = await state.get_data()
        ad_id = data.get('change_ad')
    await state.update_data(change_ad=ad_id)

    ad = await AdvertisementService.get_adv(ad_id)
    video_id = ad.video_id
    photo_id = ad.photo_id
    description = ad.description
    city = ad.city
    approved = ad.approved
    await utils.utils.send_advert(message.from_user.id, message.from_user.id, description, city, video_id, photo_id,
                                  under_moderation=not approved)
    await state.set_state(None)
    await message.message.answer(text=_('Бажаєте видалити оголошення?'), reply_markup=client_kb.delete_ad_kb)


@callback_query(F.data == 'change_media')
async def change_media(call: types.CallbackQuery, state: FSMContext, **kwargs):
    data = await state.get_data()
    if data.get('is_ad'):
        await state.set_state(FSMClient.change_media_ad)
        kb = client_kb.back_to_ready_ad_kb
    else:
        await state.set_state(FSMClient.change_media)
        kb = client_kb.back_to_ready_kb
    await call.message.edit_text(text=_('📸 Надішліть фото і відео:\n'
                                        '<i>До 5 фото та до 1 відео</i>'), reply_markup=kb,
                                 )


@callback_query(F.data == 'change_desc')
async def change_desc(call: types.CallbackQuery, state: FSMContext, **kwargs):
    await state.set_state(FSMClient.change_desc)
    data = await state.get_data()
    if data.get('is_ad'):
        kb = client_kb.back_to_ready_ad_kb
        text = _('📝 Напишіть опис для оголошення:')
    else:
        kb = client_kb.back_to_ready_kb
        text = _('📝 Напишіть опис для лоту:\n\n'
                 '<i>Наприклад: Навушники Marshall Major IV Bluetooth Black</i>')
    await call.message.edit_text(text=text,

                                 reply_markup=kb)


@callback_query(F.data == 'change_start_price')
async def change_start_price(call: types.CallbackQuery, state: FSMContext, **kwargs):
    await state.set_state(FSMClient.change_start_price)
    fsm_data = await state.get_data()
    currency = fsm_data.get('currency')
    text = _('💰 Вкажіть стартову ціну в {currency}:').format(currency=currency)
    if isinstance(call, types.CallbackQuery):
        await call.message.edit_text(text=text, reply_markup=client_kb.back_to_ready_kb)
    elif isinstance(call, types.Message):
        await call.answer(text=text, reply_markup=client_kb.back_to_ready_kb)


@callback_query(F.data == 'change_lot_time')
async def change_lot_time(call: types.CallbackQuery, state: FSMContext, **kwargs):
    await state.set_state(FSMClient.change_lot_time)
    kb = (deepcopy(client_kb.lot_time_kb))
    kb.inline_keyboard.extend([[client_kb.back_to_ready_btn]])
    await call.message.edit_text(text=_('🕙 Скільки буде тривати аукціон?'), reply_markup=kb)


@callback_query(F.data == 'change_price_steps')
async def change_price_steps(call: types.CallbackQuery, state: FSMContext, **kwargs):
    await state.set_state(FSMClient.change_price_steps)
    await call.message.edit_text(text=_('Напишіть крок ставки через пробіл (від 1 до 3 кроків):\n'
                                        'Наприклад: 500 1000 1500'), reply_markup=client_kb.back_to_ready_kb)


@callback_query(F.data == 'change_city')
async def change_city(call: types.CallbackQuery, state: FSMContext, **kwargs):
    data = await state.get_data()
    await state.set_state(FSMClient.change_city)

    if data.get('is_ad'):
        kb = client_kb.back_to_ready_ad_kb
    else:
        kb = client_kb.back_to_ready_kb
    await call.message.edit_text(text=_('Надішліть нову назву міста:'), reply_markup=kb)


@message(FSMClient.change_desc)
async def set_desc(message: types.Message, state: FSMContext, **kwargs):
    await state.update_data(description=message.text)
    data = await state.get_data()
    if data.get('is_ad'):
        await save_media_ad(message, state)
    else:
        await ready_lot(message, state)


@message(FSMClient.change_start_price)
async def set_start_price(message: types.Message, state: FSMContext, **kwargs):
    if message.text.isdigit():
        await state.update_data(price=message.text)
        await ready_lot(message, state)
    else:
        await message.answer(text=_('❌ Потрібно ввести числове значення.'))
        await change_start_price(message, state)


@message(FSMClient.change_lot_time)
async def set_lot_time(call: types.CallbackQuery, state: FSMContext, **kwargs):
    await state.update_data(lot_time_living=call.data)
    await ready_lot(call, state)


@message(FSMClient.change_price_steps)
async def set_price_steps(message: types.Message, state: FSMContext, **kwargs):
    await state.update_data(price_steps=message.text)
    if all(step.isdigit() for step in message.text.split(' ')):
        await state.update_data(price_steps=message.text)
        await ready_lot(message, state)
    else:
        await message.answer(text=_('❌ Потрібно ввести числові значення.'))
        await change_start_price(message, state)


@message(FSMClient.change_city)
async def set_new_city(message: types.Message, state: FSMContext, **kwargs):
    await state.update_data(city=message.text)
    data = await state.get_data()
    if data.get('is_ad'):
        await save_media_ad(message, state)
    else:
        await ready_lot(message, state)


@callback_query(F.data == 'delete_lot')
async def delete_lot(call: types.CallbackQuery, state: FSMContext, **kwargs):
    fsm_data = await state.get_data()
    lot_id = fsm_data.get('change_lot')
    group_id = fsm_data.get('adv_group_id')
    lot = await LotService.get_lot(lot_id)
    accept_btn = deepcopy(client_kb.accept_lot_deletion_btn)
    accept_btn.callback_data = f'lot_deletion_accept_{lot_id}'
    decline_btn = deepcopy(client_kb.decline_lot_deletion_btn)
    decline_btn.callback_data = f'lot_deletion_decline_{lot_id}'
    kb = InlineKeyboardMarkup(inline_keyboard=[[decline_btn, accept_btn]])
    if lot.lot_link:
        await call.message.edit_text(text=_('✅ Запит на видалення створено.'))
        group_data = await GroupChannelService.get_group_record(group_id)
        await bot.send_message(chat_id=group_data.owner_telegram_id, # TODO: неспрацював запит на видалення.
                               text=_('<b>⚠️ Користувач {url} хоче видалити лот:\n</b>'
                                      '{lot_link}').format(url=call.from_user.url, lot_link=lot.lot_link),
                               reply_markup=kb)
    else:
        await call.message.edit_text(_('✅ Лот видалено.'), reply_markup=client_kb.main_kb)
        await delete_record_by_id(lot_id, database.models.lot.Lot)


@callback_query(F.data == 'delete_ad')
async def delete_ad(call: types.CallbackQuery, state: FSMContext, **kwargs):
    fsm_data = await state.get_data()
    ad_id = fsm_data.get('change_ad')
    ad = await AdvertisementService.get_adv(ad_id)
    if ad.post_link:
        try:
            await bot.delete_message(chat_id=ad.group_id, message_id=ad.message_id)
        except:
            pass

    await call.message.edit_text(_('✅ Оголошення видалено.'), reply_markup=client_kb.main_kb)
    await delete_record_by_id(ad_id, database.models.advertisement.Advertisement)

    if scheduler.get_job(f'adv_repost_{ad_id}'):
        scheduler.remove_job(f'adv_repost_{ad_id}')
    if scheduler.get_job(f'adv_{ad_id}'):
        scheduler.remove_job(f'adv_{ad_id}')


@callback_query(F.data.startswith('time_left'))
async def time_left_popup(call: types.CallbackQuery, state: FSMContext, **kwargs):
    data = call.data.split('_')
    lot_id = data[-1]
    obj_type = data[-2]
    if lot_id == 'None':
        fsm_data = await state.get_data()
        lot_id = fsm_data.get('change_lot')
    if obj_type == 'adv':
        job = scheduler.get_job(f'adv_{lot_id}')
        not_published_text = _('Оголошення не опубліковане.')
    else:
        job = scheduler.get_job(f'lot_{lot_id}')
        not_published_text = _('Лот не опублікований.')

    if job:
        end_lot_time = job.next_run_time.replace(tzinfo=None)
        left_time: datetime.timedelta = end_lot_time - datetime.datetime.now().replace(tzinfo=None)
        hours, rem = divmod(left_time.seconds, 3600)
        minutes = divmod(rem, 60)[0]
        if left_time.days == 0:
            text = _('До завершення {hours}год, {minutes}хв').format(hours=hours, minutes=minutes)
        elif left_time.days == 1:
            text = _('До завершення {days} день, {hours}год, {minutes}хв').format(days=left_time.days, hours=hours,
                                                                                  minutes=minutes)
        else:
            text = _('До завершення {days} дні(-в), {hours}год, {minutes}хв').format(days=left_time.days, hours=hours,
                                                                                     minutes=minutes)
        await call.answer(text=text)
    else:
        await call.answer(text=not_published_text)


@callback_query(F.data.startswith('accept_lot'))
async def accept_lot(call: types.CallbackQuery, state: FSMContext, **kwargs):
    accept = call.data.split('_')
    new_lot_id = accept[-1]
    lot = await LotService.get_lot(new_lot_id)
    if lot:
        video_id = lot.video_id
        photo_id = lot.photo_id
        description = lot.description
        start_price = lot.start_price
        price_steps = lot.price_steps
        city = lot.city
        currency = lot.currency
        owner_id = lot.owner_telegram_id
        photos_link = lot.photos_link
        group_id = lot.group_id
        if not scheduler.get_job(f'lot_{new_lot_id}'):
            msg = await utils.utils.send_post(owner_id, group_id, photo_id, video_id, description, start_price,
                                              price_steps, currency=currency, city=city, lot_id=new_lot_id,
                                              moder_review=None,
                                              photos_link=photos_link)
            await LotService.update_lot_sql(lot_id=new_lot_id, lot_link=msg.get_url(), message_id=msg.message_id,
                                            approved=1)
            scheduler.add_job(utils.utils.lot_ending, trigger='interval', id=f'lot_{new_lot_id}',
                              hours=lot.lot_time_living,
                              kwargs={'job_id': new_lot_id, 'msg_id': msg.message_id})
            channel = await bot.get_chat(chat_id=group_id)
            await call.answer()
            if len(description) > 20:
                description = f'{description[:20]}...'
            text = _("✅ Готово!\n"
                     "Лот <b><a href='{msg_url}'>{desc}...</a></b> "
                     "опубліковано в <b><a href='{channel_link}'>"
                     "{channel_name}</a></b>").format(msg_url=msg.get_url(),
                                                      desc=description,
                                                      channel_link=channel.invite_link,
                                                      channel_name=channel.title)
            await call.message.edit_caption(caption=text, reply_markup=client_kb.main_kb)
            await bot.send_message(chat_id=owner_id, text=text, reply_markup=client_kb.main_kb)
        else:
            await call.answer(text=_('Лот вже опубліковано.'))
    else:
        await call.answer(text=_('Лот вже відхилено.'))


@callback_query(F.data.startswith('accept_adv'))
async def accept_adv(call: types.CallbackQuery, state: FSMContext, **kwargs):
    accept = call.data.split('_')
    new_adv_id = accept[-1]
    adv = await AdvertisementService.get_adv(new_adv_id)
    if adv:
        video_id = adv.video_id
        photo_id = adv.photo_id
        description = adv.description
        city = adv.city
        owner_id = adv.owner_telegram_id
        post_per_day = adv.post_per_day
        photos_link = adv.photos_link
        group_id = adv.group_id
        owner = await bot.get_chat(owner_id)

        if not scheduler.get_job(f'adv_{new_adv_id}'):
            try:
                msg = await utils.utils.send_advert(user_id=owner_id, send_to_id=group_id, photo_id=photo_id,
                                                    video_id=video_id,
                                                    description=description, city=city, advert_id=new_adv_id,
                                                    moder_review=None,
                                                    photos_link=photos_link)
            except Exception as err:
                logging.info(err)
                await bot.send_message(chat_id=call.from_user.id, text=str(err))
                return
            await AdvertisementService.update_adv_sql(adv_id=new_adv_id, post_link=msg.get_url(),
                                                      message_id=msg.message_id,
                                                      approved=1)
            scheduler.add_job(utils.utils.adv_ending, trigger='interval', id=f'adv_{new_adv_id}', hours=168,
                              kwargs={'job_id': new_adv_id})
            now = datetime.datetime.now()
            if post_per_day:
                hours_mapping = {
                    1: str(now.hour),
                    2: f'{randint(8, 14)},{randint(17, 23)}',
                    3: f'{randint(8, 14)},{randint(15, 18)},{randint(19, 23)}'}

                scheduler.add_job(utils.utils.repost_adv, trigger='cron', id=f'adv_repost_{new_adv_id}',
                                  hour=hours_mapping.get(int(post_per_day)),
                                  minute=f'{now.minute}',
                                  kwargs={'job_id': new_adv_id, 'username': owner.username})
                job = scheduler.get_job(f'adv_repost_{new_adv_id}')
                logging.info(f'name={job.name}; kwargs={job.kwargs}; next_run_time={job.next_run_time}')

            channel = await bot.get_chat(chat_id=group_id)
            await call.answer()
            text = _("✅ Готово!\n"
                     "Оголошення <b><a href='{msg_url}'>{desc}...</a></b> "
                     "опубліковано в каналі <b><a href='{channel_link}'>"
                     "{channel_name}</a></b>").format(msg_url=msg.get_url(),
                                                      desc=description[:15],
                                                      channel_link=channel.invite_link,
                                                      channel_name=channel.title)
            await call.message.edit_caption(caption=text, reply_markup=client_kb.main_kb)
            await bot.send_message(chat_id=owner_id, text=text, reply_markup=client_kb.main_kb)
        else:
            await call.answer(text=_('Оголошення вже опубліковано.'))
    else:
        await call.answer(text=_('Оголошення вже відхилено.'))


@callback_query(F.data.startswith('decline_lot'))
async def decline_lot(call: types.CallbackQuery, **kwargs):
    decline = call.data.split('_')
    new_lot_id = decline[-1]
    lot = await LotService.get_lot(new_lot_id)
    if lot:
        if scheduler.get_job(f'lot_{new_lot_id}'):
            await call.answer(text=_('Лот вже опубліковано.'))
        else:
            await call.answer()
            owner_id = lot.owner_telegram_id
            await delete_record_by_id(new_lot_id, database.models.lot.Lot)
            await call.message.answer(text='✅ Лот успішно відхилено')
            await bot.send_message(chat_id=owner_id,
                                   text=_("❗️Нажаль ваш лот <b>{desc}...</b> не пройшов модерацію.").format(
                                       desc=lot.description[:15]),
                                   reply_markup=client_kb.main_kb)
    else:
        await call.answer(text=_('Лот вже відхилено.'))


@callback_query(F.data.startswith('decline_adv'))
async def decline_adv(call: types.CallbackQuery, **kwargs):
    decline = call.data.split('_')
    new_adv_id = decline[-1]
    adv = await AdvertisementService.get_adv(new_adv_id)
    if adv:
        if scheduler.get_job(f'adv_{new_adv_id}'):
            await call.answer(text=_('Оголошення вже опубліковано.'))
        else:
            await call.answer()
            owner_id = adv.owner_telegram_id
            await delete_record_by_id(new_adv_id, database.models.advertisement.Advertisement)
            await call.message.answer(text='✅ Оголошення успішно відхилено')
            await bot.send_message(chat_id=owner_id,
                                   text=_("❗️Нажаль ваше оголошення <b>{desc}...</b> не пройшло модерацію.").format(
                                       desc=adv.description[:15]),
                                   reply_markup=client_kb.main_kb)
    else:
        await call.answer(text=_('Оголошення вже відхилено.'))


@callback_query(F.data.startswith('lot_deletion_'))
async def lot_deletion(call: types.CallbackQuery, **kwargs):
    data = call.data.split('_')
    action = data[2]
    lot_id = data[-1]
    lot = await LotService.get_lot(lot_id)
    text = None
    if lot:
        if action == 'accept':
            text = _('✅ Ваш лот <b>{desc}...</b> видалено').format(desc=lot.description[:15])
            await call.message.edit_text(_('✅ Лот видалено.'), reply_markup=client_kb.main_kb)
            await delete_record_by_id(lot_id, database.models.lot.Lot)
            try:
                scheduler.remove_job(f'lot_{lot_id}')
                await bot.delete_message(chat_id=lot.group_id, message_id=lot.message_id)
            except:
                ...
        elif action == 'decline':
            text = _('❌ Ваш лот <b>{desc}...</b> не видалено.\n'
                     f'Запит відхилено.').format(desc=lot.description[:15])
            await call.message.edit_text(_('✅ Видалення відхилено.'), reply_markup=client_kb.main_kb)
        if text:
            await bot.send_message(chat_id=lot.owner_telegram_id, text=text, reply_markup=client_kb.main_kb)
    else:
        await call.answer(text=_('Запит вже оброблений.'))


@callback_query(F.data == 'anti_sniper')
async def anti_sniper(call: types.CallbackQuery, state: FSMContext, **kwargs):
    user = await UserService.get_user(call.from_user.id)
    await state.set_state(FSMClient.sniper_time)
    await call.message.edit_text(text=_('⏱ Ваш поточний час антиснайпингу - {minute}хв.\n'
                                        'Якщо хочете змінити - оберіть варіант нижче:').format(
        minute=user.anti_sniper.minute), reply_markup=client_kb.anti_kb)


@callback_query(FSMClient.sniper_time)
async def new_sniper_time(call: types.CallbackQuery, state: FSMContext, **kwargs):
    new_time = datetime.time(hour=0, minute=int(call.data), second=0)
    await UserService.update_user_sql(telegram_id=call.from_user.id, anti_sniper=new_time)
    await call.message.edit_text(text=_('✅ Час антиснайпингу змінено на {minute}хв').format(minute=new_time.minute),
                                 reply_markup=client_kb.main_kb)


@callback_query(FSMClient.adv_sub_seconds)
async def create_adv_sub(call: types.CallbackQuery, state: FSMContext, **kwargs):
    fsm_data = await state.get_data()
    user = await UserService.get_user(call.from_user.id)
    if user.user_adv_token:
        status = await get_order_status(user.user_adv_token)
        if status in ('CREATED', 'APPROVED'):
            token = user.user_adv_token
        else:
            token = await create_order(usd=1)
            await UserService.update_user_sql(call.from_user.id, user_adv_token=token)
    else:
        token = await create_order(usd=1)
        await UserService.update_user_sql(call.from_user.id, user_adv_token=token)

    kb = await utils.utils.payment_kb(token, activate_btn_text=_('Оплатити 15$'), callback_data=f'update_{token}')
    await call.message.edit_text(text=_('💲 Вартість підписки 15$ на 30 днів.\n\n'
                                        'Оплатіть підписку натиснувши на кнопку нижче 👇'), reply_markup=kb)


@callback_query(F.data.startswith('update_'))
async def update_adv_payment_status(call: types.CallbackQuery, state: FSMContext, **kwargs):
    token = call.data.split('_')[1]
    payment = await utils.utils.payment_completed(token)
    if payment:
        await UserService.update_user_sql(call.from_user.id, advert_subscribe_time=604800 + time.time())
        await call.message.edit_text(text=_('✅ Вітаю! Підписку на виставлення оголошень успішно оформлено на 30 днів.'),
                                     reply_markup=client_kb.main_kb)
    else:
        kb = await utils.utils.payment_kb(token, activate_btn_text=_('Оплатити 15$'), callback_data=f'update_{token}')
        try:
            await call.message.edit_text(text=_('⚠️ Оплату не зафіксовано'), reply_markup=kb)
        except:
            pass
        return


@callback_query(F.data.startswith('change_desc_exist'))
async def change_desc_exist(call: types.CallbackQuery, state: FSMContext, **kwargs):
    data = await state.get_data()
    object_type = call.data.split('_')[-1]
    await state.update_data(object_type=object_type)
    if data.get('change_ad'):
        kb = client_kb.back_show_ad_kb
        text = _('📝 Напишіть опис для оголошення:')
    else:
        kb = client_kb.back_show_lot_kb
        text = _('📝 Напишіть опис для лоту:\n\n'
                 '<i>Наприклад: Навушники Marshall Major IV Bluetooth Black</i>')
    await state.set_state(FSMClient.new_desc_exist)
    await call.message.edit_text(text=text, reply_markup=kb)


@message(FSMClient.new_desc_exist)
async def request_new_desc(message: types.Message, state: FSMContext, **kwargs):
    fsm_data = await state.get_data()
    object_type = fsm_data.get('object_type')
    group_id = fsm_data.get('adv_group_id')
    await state.set_state(None)
    await message.answer(text=_('✅ Очікуйте підтвердження модератора.'), reply_markup=client_kb.main_kb)

    group_data = await GroupChannelService.get_group_record(group_id)
    if object_type == 'adv':
        obj_id = fsm_data.get('change_ad')
        await AdvertisementService.update_adv_sql(obj_id, new_text=message.text)
        ad = await AdvertisementService.get_adv(obj_id)
        await utils.utils.send_advert(user_id=message.from_user.id, send_to_id=group_data.owner_telegram_id,
                                      description=ad.description,
                                      city=ad.city,
                                      video_id=ad.video_id, photo_id=ad.photo_id,
                                      change_text=True, advert_id=obj_id, new_desc=ad.new_text)
    else:
        obj_id = fsm_data.get('change_lot')
        await LotService.update_lot_sql(obj_id, new_text=message.text)
        lot = await LotService.get_lot(obj_id)
        await utils.utils.send_post(message.from_user.id, group_data.owner_telegram_id, lot.photo_id, lot.video_id,
                                    lot.description,
                                    lot.start_price,
                                    lot.price_steps, currency=lot.currency, city=lot.city, lot_id=obj_id,
                                    change_text=True, new_desc=lot.new_text)


@callback_query(F.data.startswith('edit_new_text'))
async def edit_new_text(call: types.CallbackQuery, state: FSMContext, **kwargs):
    obj_type = call.data.split(':')[-1]
    obj_id = call.data.split(':')[-3]
    action = call.data.split(':')[-2]
    if action == 'accept':
        if obj_type == 'lot':
            lot = await LotService.get_lot(obj_id)
            if lot.new_text:
                user = await UserService.get_user(lot.owner_telegram_id)
                user_tg = await bot.get_chat(user.telegram_id)
                kb = await utils.utils.create_price_step_kb(lot.price_steps, obj_id, lot.currency)
                kb.inline_keyboard.extend([[InlineKeyboardButton(text='⏳', callback_data=f'time_left_lot_{obj_id}')]])
                kb.inline_keyboard.extend(
                    [[InlineKeyboardButton(text=_('💬 Задати питання автору', locale=user.language),
                                           url=f'https://t.me/{user_tg.username}')]])

                await LotService.update_lot_sql(obj_id, description=lot.new_text, new_text=None)
                try:
                    caption = _("<b>{description}</b>\n\n"
                                "🏙 <b>Місто:</b> {city}\n\n"
                                "👇 <b>Ставки учасників:</b>\n\n"
                                "💰 <b>Стартова ціна:</b> {start_price} {currency}\n"
                                "⏱ <b>Антиснайпер</b> {anti_sniper} хв.\n")
                    if lot.bidder_telegram_id:
                        bidder_name = await bot.get_chat(lot.bidder_telegram_id)
                        caption = await utils.utils.new_bid_caption(caption, bidder_name.first_name, lot.last_bid,
                                                                    lot.currency, user.language, lot.bid_count)
                    await bot.edit_message_caption(chat_id=lot.group_id, message_id=lot.message_id,
                                                   caption=caption.format(
                                                       description=lot.new_text, city=lot.city,
                                                       start_price=lot.start_price, currency=lot.currency,
                                                       anti_sniper=user.anti_sniper.minute, bid_count=lot.bid_count,
                                                       price=lot.last_bid),
                                                   reply_markup=kb)
                except Exception:
                    await call.answer(text='Запит вже оброблено.')
                    return
                await bot.send_message(chat_id=user.telegram_id, text=_(
                    "✅ Модератор підтвердив зміну опису лоту.\n\n<a href='{lot_post}'><b>👉 Перейти до лоту.</b></a>",
                    locale=user.language).format(
                    lot_post=lot.lot_link), reply_markup=client_kb.main_kb)
            else:
                await call.answer(text='Запит вже оброблено.')
                return
        elif obj_type == 'adv':
            ad = await AdvertisementService.get_adv(obj_id)

            if ad.new_text:
                user = await UserService.get_user(ad.owner_telegram_id)
                user_tg = await bot.get_chat(user.telegram_id)
                kb = InlineKeyboardMarkup(inline_keyboard=[])
                kb.inline_keyboard.extend([[InlineKeyboardButton(text='⏳', callback_data=f'time_left_adv_{obj_id}')]])
                kb.inline_keyboard.extend(
                    [[InlineKeyboardButton(text=_('💬 Задати питання автору', locale=user.language),
                                           url=f'https://t.me/{user_tg.username}')]])
                await AdvertisementService.update_adv_sql(obj_id, description=ad.new_text, new_text=None)
                caption = _("<b>{description}</b>\n\n"
                            "🏙 <b>Місто:</b> {city}\n", locale=user.language).format(description=ad.new_text,
                                                                                     city=ad.city)
                try:
                    await bot.edit_message_caption(chat_id=ad.group_id, message_id=ad.message_id, caption=caption,
                                                   reply_markup=kb)
                except Exception:
                    await call.answer(text='Запит вже оброблено.')
                    return
                await bot.send_message(chat_id=user.telegram_id, text=_(
                    "✅ Модератор підтвердив зміну опису оголошення.\n\n<a href='{lot_post}'><b>👉 Перейти до оголошення.</b></a>",
                    locale=user.language).format(
                    lot_post=ad.post_link), reply_markup=client_kb.main_kb)
            else:
                await call.answer(text='Запит вже оброблено.')
                return
    else:
        if obj_type == 'lot':
            lot = await LotService.get_lot(obj_id)
            user = await UserService.get_user(lot.owner_telegram_id)
            if lot.new_text:
                await LotService.update_lot_sql(obj_id, new_text=None)
                await bot.send_message(chat_id=lot.owner_telegram_id,
                                       text=_(
                                           '❌ Запит на зміну опису для лоту <a href="{lot_link}"><b>{lot_desc}</b></a> відхилено.',
                                           locale=user.language).format(
                                           lot_link=lot.lot_link, lot_desc=lot.description),
                                       reply_markup=client_kb.main_kb,
                                       )
                await call.answer(text='✅ Запит на зміну опису відхилено')
            else:
                await call.answer('Запит вже оброблено.')
        elif obj_type == 'adv':
            ad = await AdvertisementService.get_adv(obj_id)
            user = await UserService.get_user(ad.owner_telegram_id)
            if ad.new_text:
                await AdvertisementService.update_adv_sql(obj_id, new_text=None)
                await bot.send_message(chat_id=ad.owner_telegram_id,
                                       text=_(
                                           '❌ Запит на зміну опису для оголошення <a href="{lot_link}"><b>{lot_desc}</b></a> відхилено.',
                                           locale=user.language).format(
                                           lot_link=ad.post_link, lot_desc=ad.description),
                                       reply_markup=client_kb.main_kb,
                                       )
                await call.answer(text='✅ Запит на зміну опису відхилено')
            else:
                await call.answer('Запит вже оброблено.')


@callback_query(FSMClient.repost_count_answer)
async def republish_adv(call: types.CallbackQuery, state: FSMContext, **kwargs):
    await call.answer()
    answer = call.data
    if answer == 'yes':
        await call.message.edit_text(text=_("Оберіть кількість повторних публікацій на день:"),
                                     reply_markup=client_kb.repost_count_kb)
        await state.set_state(FSMClient.repost_count)
    else:
        await save_repost_count(call, state)
        return


@callback_query(FSMClient.repost_count)
async def save_repost_count(call: types.CallbackQuery, state: FSMContext, **kwargs):
    if isinstance(call, types.CallbackQuery):
        if call.data in ('1', '2', '3'):
            await state.update_data(repost_count=call.data)
        last_message_id = call.message.message_id
    else:
        last_message_id = call.message_id
    fsm_data = await state.get_data()
    kb = deepcopy(client_kb.ready_to_publish_ad_kb)
    kb.inline_keyboard.extend([[client_kb.cancel_btn, client_kb.publish_adv_btn]])
    text = _('⬆️ Оголошення готове до публікації!\n'
             'Перевірте всю інформацію і натисніть <b>✅ Опублікувати</b>, коли будете готові.')
    await utils.utils.send_post_fsm(fsm_data, call.from_user.id, is_ad=True)
    await bot.send_message(chat_id=call.from_user.id, text=text, reply_markup=kb,
                           reply_to_message_id=last_message_id)

