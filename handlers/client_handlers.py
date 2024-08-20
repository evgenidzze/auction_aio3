import datetime
import locale
import logging
import time
from copy import deepcopy
from random import randint
from typing import List

from aiogram import Router, types, F
from aiogram.enums import ChatMemberStatus
from aiogram.filters import CommandStart, Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.deep_linking import create_start_link

from utils.aiogram_media_group import media_group_handler

from create_bot import scheduler, _, i18n, bot, job_stores
from database.db_manage import insert_or_update_user, get_user_lots, get_user, create_lot, get_user_ads, \
    update_user_sql, get_question_or_answer, get_question, get_answer, get_lot, delete_answer, create_adv, make_bid_sql, \
    get_adv, delete_lot_sql, delete_adv_sql, update_lot_sql, update_adv_sql, create_question, delete_question_db, \
    create_answer, create_group_channel, get_user_chats, get_all_chats, get_chat_record, update_chat_sql
from keyboards.kb import language_kb, main_kb, back_to_main_kb, auction_kb, create_auction_btn, back_to_main_btn, \
    currency_kb, lot_time_kb, cancel_btn, ready_to_publish_kb, publish_btn, add_menu_kb, create_advert_btn, \
    subscribe_adv_kb, quest_answ_kb, back_to_messages, back_to_questions_kb, back_to_answers_kb, yes_no_kb, \
    delete_lot_kb, delete_ad_kb, back_to_ready_ad_kb, back_to_ready_kb, back_to_ready_btn, accept_lot_deletion_btn, \
    decline_lot_deletion_btn, anti_kb, back_to_answers_btn, back_to_questions, back_show_ad_kb, back_show_lot_kb, \
    repost_count_kb, ready_to_publish_ad_kb, publish_adv_btn, reset_to_auction_menu_kb, reset_to_auction_menu_btn, \
    reset_to_ad_menu_kb, back_to_auction_btn, group_channels_kb, back_group_channels_btn, back_my_channels_groups, \
    back_my_channels_groups_kb, back_to_ad_menu_btn

from utils.config import AUCTION_CHANNEL, ADVERT_CHANNEL
from utils.paypal import get_status, create_payment_token
from utils.utils import create_user_lots_kb, save_sent_media, create_telegraph_link, send_post_fsm, \
    send_post, adv_sub_time_remain, user_have_approved_adv_token, create_question_kb, create_answers_kb, send_advert, \
    new_bid_caption, lot_ending, adv_ending, repost_adv, username_in_text, phone_in_text, payment_kb, \
    payment_approved, create_price_step_kb, photo_video_count_in_messages, restrict_media_count, bot_sub_time_remain, \
    chat_have_approved_token

ADMINS = [397875584, 432530900]
locale.setlocale(locale.LC_ALL, 'uk_UA.utf8')
router = Router()


class FSMClient(StatesGroup):
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


async def start(message: types.Message, state: FSMContext):
    for job in scheduler.get_jobs():
        logging.info(f'{job.id}-{job}-{job.kwargs}')
    await state.set_state(FSMClient.language)
    text = _('<b>Оберіть мову / Choose a language:</b>')
    if isinstance(message, types.Message):
        await message.answer(text=text, parse_mode='html',
                             reply_markup=language_kb)
    elif isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text=text, parse_mode='html',
                                        reply_markup=language_kb)


async def main_menu(call, state: FSMContext):
    clean_text = "Вітаю, <b>{first_name}!</b><a href='https://telegra.ph/file/3f6168cc5f94f115331ac.png'>⠀</a>\n"
    text = _(clean_text).format(first_name=call.from_user.username)
    if isinstance(call, types.CallbackQuery):
        if call.data in ('en', 'uk'):
            await insert_or_update_user(telegram_id=call.from_user.id, language=call.data)
            text = _(clean_text, locale=call.data).format(first_name=call.from_user.username)
            i18n.current_locale = call.data
        await call.message.edit_text(text=text, parse_mode='html',
                                     reply_markup=main_kb)
    else:
        await call.answer(text=text, parse_mode='html', reply_markup=main_kb)
    await state.clear()


async def auction_menu(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(text=_('Ви обрали 🏷 Аукціон'), reply_markup=auction_kb)
    await state.clear()


async def my_auctions(call: types.CallbackQuery, state: FSMContext):
    lots = await get_user_lots(call.from_user.id)
    kb = await create_user_lots_kb(lots)
    kb.inline_keyboard.extend([[create_auction_btn], [back_to_auction_btn]])
    await state.set_state(FSMClient.change_lot)
    await call.message.edit_text(text=_('Оберіть існуючий аукціон або створіть новий:'), parse_mode='html',
                                 reply_markup=kb)


async def ask_city(call: types.CallbackQuery, state: FSMContext):
    user = await get_user(call.from_user.id)
    if user.is_blocked:
        await bot.send_message(chat_id=call.from_user.id, text=_('Вас було заблоковано за порушення правил.'))
        return
    await state.set_state(FSMClient.city)
    await call.message.edit_text(text=_('🌆 Вкажіть ваше місто:'),
                                 parse_mode='html',
                                 reply_markup=reset_to_auction_menu_kb)


async def ask_currency(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(FSMClient.currency)
    await message.answer(text=_('🫰🏼 Оберіть валюту:'),
                         parse_mode='html',
                         reply_markup=currency_kb)


async def ask_description(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(currency=call.data)
    await state.set_state(FSMClient.description)
    await call.message.edit_text(text=_('📝 Напишіть опис для лоту:\n\n'
                                        '<i>Наприклад: Навушники Marshall Major IV Bluetooth Black</i>'),
                                 parse_mode='html',
                                 reply_markup=reset_to_auction_menu_kb)


async def ask_price(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(FSMClient.price)
    data = await state.get_data()
    currency = data.get('currency')
    await message.answer(text=_('💰 Вкажіть стартову ціну в {currency}:').format(currency=currency),
                         reply_markup=reset_to_auction_menu_kb)


async def ask_price_steps(message: types.Message, state: FSMContext):
    if message.text.isdigit() or await state.get_state() == 'FSMClient:price_steps':
        if await state.get_state() != 'FSMClient:price_steps':
            await state.update_data(price=message.text)
        await state.set_state(FSMClient.price_steps)
        await message.answer(text=_('Напишіть крок ставки через пробіл (від 1 до 3 кроків):\n'
                                    'Наприклад: 500 1000 1500'), reply_markup=reset_to_auction_menu_kb)
    else:
        await message.answer(text=_('❌ Потрібно ввести числове значення.'))
        await ask_price(message, state)


async def ask_lot_living(message: types.Message, state: FSMContext):
    if all(step.isdigit() for step in message.text.split(' ')):
        await state.update_data(price_steps=message.text)
        await state.set_state(FSMClient.lot_time_living)
        kb = deepcopy(lot_time_kb)
        kb.inline_keyboard.extend([[reset_to_auction_menu_btn]])
        await message.answer(text=_('🕙 Скільки буде тривати аукціон?'), reply_markup=kb)
    else:
        await message.answer(text=_('❌ Потрібно ввести числові значення.'))
        await ask_price_steps(message, state)


async def ask_media(call: [types.CallbackQuery, types.Message], state: FSMContext):
    text = _('📸 Надішліть фото і відео:\n'
             '<i>До 5 фото та до 1 відео</i>')
    if isinstance(call, types.CallbackQuery):
        await state.update_data(lot_time_living=call.data)
        await call.message.edit_text(text=text, reply_markup=reset_to_auction_menu_kb, parse_mode='html')
    else:
        await call.answer(text=text, reply_markup=reset_to_auction_menu_kb, parse_mode='html')

    await state.set_state(FSMClient.media)


@media_group_handler
async def ready_lot(messages: List[types.Message], state: FSMContext):
    state_name = await state.get_state()
    if isinstance(messages[0], types.Message) and 'media' in state_name:
        videos_id, photos_id = await photo_video_count_in_messages(messages=messages, state=state)
        await restrict_media_count(photos_id, videos_id, messages, reset_to_auction_menu_kb)
        fsm_data = await state.get_data()
        if not videos_id:
            await state.update_data(video_id=None)
        if len(photos_id) <= 1 and not videos_id:
            await state.update_data(photos_link=None)
            fsm_data.pop('photos_link', None)
        elif len(photos_id) > 1:
            html = await save_sent_media(messages, photos_id, videos_id, state)
            await create_telegraph_link(state, html)
    fsm_data = await state.get_data()
    kb = deepcopy(ready_to_publish_kb)
    kb.inline_keyboard.extend([[cancel_btn, publish_btn]])
    if isinstance(messages[0], types.Message):
        msg = await send_post_fsm(fsm_data, messages[0].from_user.id)
        await msg.reply(text=_('⬆️ Лот готовий до публікації!\n'
                               'Перевірте всю інформацію і натисніть <b>✅ Опублікувати</b>, коли будете готові.'),
                        reply_markup=kb, parse_mode='html')
    elif isinstance(messages[0], types.CallbackQuery):
        text = _('Лот готовий!\nОпублікувати?')
        if (messages[0].data != 'back_to_ready' and await state.get_state() and
                'steps' not in await state.get_state()):
            await send_post_fsm(fsm_data, messages[0].from_user.id)
            await messages[0].message.reply_to_message.reply(text=text, reply_markup=kb)
        else:
            await messages[0].message.edit_text(text=_('⬆️ Лот готовий до публікації!\n'
                                                       'Перевірте всю інформацію і натисніть <b>✅ Опублікувати</b>, коли будете готові.'),
                                                reply_markup=kb, parse_mode='html')


async def lot_publish(message: types.CallbackQuery, state: FSMContext):
    fsm_data = await state.get_data()
    video_id = fsm_data.get('video_id')
    photo_id = fsm_data.get('photo_id')
    description = fsm_data.get('description')
    start_price = fsm_data.get('price')
    currency: str = fsm_data.get('currency')
    city: str = fsm_data.get('city')
    price_steps: str = fsm_data.get('price_steps')
    photos_link: str = fsm_data.get('photos_link')
    channel = await bot.get_chat(AUCTION_CHANNEL)
    if channel:
        new_lot_id = await create_lot(fsm_data, message.from_user.id)
        for admin_id in ADMINS:
            await send_post(message.from_user.id, admin_id, photo_id, video_id, description, start_price,
                            price_steps, currency=currency, city=city, lot_id=new_lot_id, moder_review=True,
                            photos_link=photos_link)
        await message.message.edit_text(
            text=_("✅ Лот відправлено на модерацію, незабаром він з'явиться у каналі <b><a href='{invite_link}'>"
                   "{username}</a></b>.").format(invite_link=channel.invite_link, username=channel.username),
            parse_mode='html', reply_markup=main_kb)
    else:
        await message.message.edit_text(
            text=_('Бот не підключений до каналу. Щоб бот функціонував, потрібно надати йому права адміністратора.'))


async def add_menu(call: types.CallbackQuery):
    await call.message.edit_text(text=_('Ви обрали 📣 Оголошення'), reply_markup=add_menu_kb)


async def my_ads(call: types.CallbackQuery, state: FSMContext):
    ads = await get_user_ads(call.from_user.id)
    kb = await create_user_lots_kb(ads)
    kb.inline_keyboard.extend([[create_advert_btn], [back_to_ad_menu_btn]])
    await state.set_state(FSMClient.change_ad)
    await call.message.edit_text(text=_('Оберіть існуючe оголошення або створіть нове:'), parse_mode='html',
                                 reply_markup=kb)


async def ask_description_ad(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(text=_('Перевірка підписки...'))
    is_subscribed = await adv_sub_time_remain(call.from_user.id)
    redis_obj = job_stores.get('default')
    result = redis_obj.redis.get('payment')
    if is_subscribed or (result and result.decode('utf-8') == 'off'):
        await call.message.edit_text(text=_('📝 Напишіть опис для оголошення:'), reply_markup=reset_to_ad_menu_kb)
        await state.set_state(FSMClient.description)
    elif await user_have_approved_adv_token(call.from_user.id):
        await update_user_sql(call.from_user.id, advert_subscribe_time=604800 + time.time())
        await call.message.edit_text(text=_('📝 Напишіть опис для оголошення:'), reply_markup=reset_to_ad_menu_kb)
        await state.set_state(FSMClient.description_ad)
    else:
        await call.message.edit_text(text=_('ℹ️ Щоб виставити оголошення, потрібно оформити підписку.'),
                                     reply_markup=subscribe_adv_kb)
        await state.set_state(FSMClient.adv_sub_seconds)


async def my_chats(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(text=_('👇 Оберіть варіант:'), reply_markup=quest_answ_kb)


async def question_list(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    question_texts_list = await get_question_or_answer(call.from_user.id, model_name='question')
    kb = await create_question_kb(question_texts_list, call.from_user.id)
    kb.inline_keyboard.extend([[back_to_messages]])
    if question_texts_list:
        await state.set_state(FSMClient.choose_question)
        await call.message.edit_text(text=_('👇 Оберіть запитання щоб відповісти або видалити:'), reply_markup=kb)
    else:
        try:
            await call.message.edit_text(text=_('🤷🏻‍♂️ У вас немає повідомлень.'), reply_markup=quest_answ_kb)
        except:
            pass


async def choose_answer(call: types.CallbackQuery, state: FSMContext):
    answer_id = call.data
    await state.update_data(answer_id=answer_id)
    answer_record = await get_answer(answer_id)
    lot = await get_lot(answer_record.lot_id)
    await call.message.edit_text(
        text=_('📦 Лот: <a href="{lot_link}"><b>{lot_desc}</b></a>\n\n'
               'Відповідь: <i>{answer_text}</i>').format(answer_text=answer_record.answer,
                                                         lot_desc=lot.description[:25], lot_link=lot.lot_link),
        parse_mode='html', reply_markup=back_to_answers_kb, disable_web_page_preview=True)
    await state.set_state(FSMClient.delete_answer)


async def del_read_answer(call: types.CallbackQuery, state: FSMContext):
    if call.data == 'read':
        data = await state.get_data()
        answer_id = data.get('answer_id')
        await delete_answer(answer_id)
        await call.message.edit_text(text=_("✅ Повідомлення видалено"))
    await answers_list(call, state)
    return


async def answers_list(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    answer_list = await get_question_or_answer(call.from_user.id, model_name='answer')
    kb = await create_answers_kb(answer_list, recipient_id=call.from_user.id)
    kb.inline_keyboard.extend([[back_to_messages]])
    if answer_list:
        await state.set_state(FSMClient.choose_answer)
        if call.data in ('read', 'delete_question'):
            await call.message.answer(text=_('👇 Оберіть відповідь щоб прочитати:'), reply_markup=kb)
        else:
            await call.message.edit_text(text=_('👇 Оберіть відповідь щоб прочитати:'), reply_markup=kb)
    else:
        try:
            await call.message.edit_text(text=_('🤷🏻‍♂️ У вас немає повідомлень.'), reply_markup=quest_answ_kb)
        except:
            pass


async def ask_city_ad(message: types.Message, state: FSMContext):
    if isinstance(message, types.Message):
        await state.update_data(description=message.text)
        await state.set_state(FSMClient.city_ad)
        await message.answer(text=_('🌆 Вкажіть ваше місто:'),
                             parse_mode='html',
                             reply_markup=reset_to_ad_menu_kb)


async def ask_media_ad(message: types.Message, state: FSMContext):
    text = _('📸 Надішліть фото і відео:\n'
             '<i>До 5 фото та до 1 відео</i>')
    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text=text, reply_markup=reset_to_ad_menu_kb, parse_mode='html')
    else:
        await state.update_data(city=message.text)
        await message.answer(text=text, reply_markup=reset_to_ad_menu_kb, parse_mode='html')
    await state.set_state(FSMClient.media_ad)


@media_group_handler
async def save_media_ad(messages: List[types.Message], state: FSMContext):
    await state.update_data(is_ad=True)
    photos_id, videos_id = [], []
    html = await save_sent_media(messages, photos_id, videos_id, state)
    if html and len(photos_id) > 1:
        await create_telegraph_link(state, html)

    if len(photos_id) > 5 or len(videos_id) > 1:
        await messages[0].answer(text=_('❌ Максимум 5 фото і 1 відео.\n'
                                        'Надішліть ще раз ваші медіафайли:'), reply_markup=reset_to_ad_menu_kb)
        return
    else:
        if len(messages) <= 1:
            await state.update_data(photos_link=None)
    if await state.get_state() in ('FSMClient:change_media_ad', 'FSMClient:change_desc', 'FSMClient:change_city'):
        await save_repost_count(messages[0], state)
        return
    else:
        await messages[0].answer(text=_("✅ Медіа збережені.\n"
                                        "Бажаєте публікувати оголошення щоденно?"), reply_markup=yes_no_kb)
        await state.set_state(FSMClient.repost_count_answer)


async def adv_publish(message, state):
    fsm_data = await state.get_data()
    video_id = fsm_data.get('video_id')
    photo_id = fsm_data.get('photo_id')
    description = fsm_data.get('description')
    city: str = fsm_data.get('city')
    photos_link: str = fsm_data.get('photos_link')
    new_adv_id = await create_adv(message.from_user.id, fsm_data)
    channel = await bot.get_chat(ADVERT_CHANNEL)
    for admin_id in ADMINS:
        await send_advert(user_id=message.from_user.id, send_to_id=admin_id, description=description, city=city,
                          photos_link=photos_link, video_id=video_id, photo_id=photo_id,
                          moder_review=True,
                          advert_id=new_adv_id)
    await message.message.edit_text(
        text=_("✅ Оголошення відправлено не модерацію, незабаром воно з'явиться у каналі <b><a href='{invite_link}'>"
               "{username}</a></b>.").format(invite_link=channel.invite_link, username=channel.username),
        parse_mode='html', reply_markup=main_kb)


async def make_bid(message: types.CallbackQuery):
    bid_data = message.data.split('_')
    lot_id = bid_data[2]
    lot = await get_lot(lot_id)
    if lot:
        last_bid = lot.last_bid
        owner_id = lot.owner_telegram_id
        last_bidder_id = lot.bidder_telegram_id
        bid_count = lot.bid_count
        user = await get_user(owner_id)
        currency = lot.currency
        anti_sniper_time: datetime.time = user.anti_sniper
        if str(message.from_user.id) == lot.owner_telegram_id and message.from_user.id != 397875584:
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
            await make_bid_sql(lot_id, price, bidder_id=message.from_user.id, bid_count=bid_count)
            lot_post = message.message
            caption = await new_bid_caption(lot_post.caption, message.from_user.first_name, price, currency,
                                            owner_locale=user.language, bid_count=bid_count + 1,
                                            photos_link=lot.photos_link)
            await bot.edit_message_caption(chat_id=AUCTION_CHANNEL, message_id=lot_post.message_id, caption=caption,
                                           reply_markup=lot_post.reply_markup, parse_mode='html')
            await bot.send_message(chat_id=owner_id,
                                   text=_(
                                       "💸 Нова ставка на ваш лот!\n\n<a href='{lot_post}'><b>👉 Перейти до лоту.</b></a>").format(
                                       lot_post=lot_post.url),
                                   parse_mode='html',
                                   reply_markup=main_kb)
            if last_bidder_id:
                await bot.send_message(chat_id=last_bidder_id,
                                       text=_(
                                           "👋 Вашу ставку на лот <a href='{lot_post}'><b>{lot_name}</b></a> перебили.\n\n"
                                           "<a href='{lot_post}'><b>👉 Перейти до лоту.</b></a>").format(
                                           lot_post=lot_post.url, lot_name=lot.description), reply_markup=main_kb,
                                       parse_mode='html')
            await message.answer(text=_('✅ Ставку прийнято!'))
        else:
            await message.answer(text=_('Лот ще не опубліковано.'))
    else:
        await message.answer(text=_('❌ Аукціон закінчено'))


async def help_(call: types.CallbackQuery):
    await call.message.edit_text(text=_("По всім запитанням @Oleksandr_Polis\n\n"
                                        "<i>Що таке <a href='https://telegra.ph/Antisnajper-03-31'>"
                                        "<b>⏱ Антиснайпер?</b></a></i>\n"),
                                 reply_markup=back_to_main_kb, parse_mode='html',
                                 disable_web_page_preview=True)


async def show_lot(message: types.CallbackQuery, state: FSMContext):
    lot_id = message.data
    if not (lot_id.isdigit()):
        data = await state.get_data()
        lot_id = data.get('change_lot')
    await state.update_data(change_lot=lot_id)

    lot = await get_lot(lot_id)
    video_id = lot.video_id
    photo_id = lot.photo_id
    description = lot.description
    start_price = lot.start_price
    price_steps = lot.price_steps
    currency = lot.currency
    city = lot.city
    photos_link = lot.photos_link
    await send_post(message.from_user.id, message.from_user.id, photo_id, video_id, description, start_price,
                    price_steps, currency=currency, city=city, under_moderation=not lot.approved,
                    photos_link=photos_link)
    await message.message.answer(text=_('Бажаєте видалити лот?'), reply_markup=delete_lot_kb)


async def show_ad(message: types.CallbackQuery, state: FSMContext):
    ad_id = message.data
    if not (ad_id.isdigit()):
        data = await state.get_data()
        ad_id = data.get('change_ad')
    await state.update_data(change_ad=ad_id)

    ad = await get_adv(ad_id)
    video_id = ad.video_id
    photo_id = ad.photo_id
    description = ad.description
    city = ad.city
    photos_link = ad.photos_link
    approved = ad.approved
    await send_advert(message.from_user.id, message.from_user.id, description, city, photos_link, video_id, photo_id,
                      under_moderation=not approved)
    await message.message.answer(text=_('Бажаєте видалити оголошення?'), reply_markup=delete_ad_kb)


async def change_media(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get('is_ad'):
        await state.set_state(FSMClient.change_media_ad)
        kb = back_to_ready_ad_kb
    else:
        await state.set_state(FSMClient.change_media)
        kb = back_to_ready_kb
    await call.message.edit_text(text=_('📸 Надішліть фото і відео:\n'
                                        '<i>До 5 фото та до 1 відео</i>'), reply_markup=kb,
                                 parse_mode='html')


async def change_desc(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(FSMClient.change_desc)
    data = await state.get_data()
    if data.get('is_ad'):
        kb = back_to_ready_ad_kb
        text = _('📝 Напишіть опис для оголошення:')
    else:
        kb = back_to_ready_kb
        text = _('📝 Напишіть опис для лоту:\n\n'
                 '<i>Наприклад: Навушники Marshall Major IV Bluetooth Black</i>')
    await call.message.edit_text(text=text,
                                 parse_mode='html',
                                 reply_markup=kb)


async def change_start_price(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(FSMClient.change_start_price)
    fsm_data = await state.get_data()
    currency = fsm_data.get('currency')
    text = _('💰 Вкажіть стартову ціну в {currency}:').format(currency=currency)
    if isinstance(call, types.CallbackQuery):
        await call.message.edit_text(text=text, reply_markup=back_to_ready_kb)
    elif isinstance(call, types.Message):
        await call.answer(text=text, reply_markup=back_to_ready_kb)


async def change_lot_time(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(FSMClient.change_lot_time)
    kb = (deepcopy(lot_time_kb))
    kb.inline_keyboard.extend([[back_to_ready_btn]])
    await call.message.edit_text(text=_('🕙 Скільки буде тривати аукціон?'), reply_markup=kb)


async def change_price_steps(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(FSMClient.change_price_steps)
    await call.message.edit_text(text=_('Напишіть крок ставки через пробіл (від 1 до 3 кроків):\n'
                                        'Наприклад: 500 1000 1500'), reply_markup=back_to_ready_kb)


async def change_city(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(FSMClient.change_city)

    if data.get('is_ad'):
        kb = back_to_ready_ad_kb
    else:
        kb = back_to_ready_kb
    await call.message.edit_text(text=_('Надішліть нову назву міста:'), reply_markup=kb)


async def set_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    data = await state.get_data()
    if data.get('is_ad'):
        await save_media_ad(message, state)
    else:
        await ready_lot(message, state)


async def set_start_price(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await state.update_data(price=message.text)
        await ready_lot(message, state)
    else:
        await message.answer(text=_('❌ Потрібно ввести числове значення.'))
        await change_start_price(message, state)


async def set_lot_time(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(lot_time_living=call.data)
    await ready_lot(call, state)


async def set_price_steps(message: types.Message, state: FSMContext):
    await state.update_data(price_steps=message.text)
    if all(step.isdigit() for step in message.text.split(' ')):
        await state.update_data(price_steps=message.text)
        await ready_lot(message, state)
    else:
        await message.answer(text=_('❌ Потрібно ввести числові значення.'))
        await change_start_price(message, state)


async def set_new_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    data = await state.get_data()
    if data.get('is_ad'):
        await save_media_ad(message, state)
    else:
        await ready_lot(message, state)


async def delete_lot(call: types.CallbackQuery, state: FSMContext):
    fsm_data = await state.get_data()
    lot_id = fsm_data.get('change_lot')
    lot = await get_lot(lot_id)
    accept_btn = deepcopy(accept_lot_deletion_btn)
    accept_btn.callback_data = f'lot_deletion_accept_{lot_id}'
    decline_btn = deepcopy(decline_lot_deletion_btn)
    decline_btn.callback_data = f'lot_deletion_decline_{lot_id}'
    kb = InlineKeyboardMarkup(inline_keyboard=[[decline_btn, accept_btn]])
    if lot.lot_link:
        await call.message.edit_text(text=_('✅ Запит на видалення створено.'))
        for admin_id in ADMINS:
            await bot.send_message(chat_id=admin_id,
                                   text=_('<b>⚠️ Користувач {url} хоче видалити лот:\n</b>'
                                          '{lot_link}').format(url=call.from_user.url, lot_link=lot.lot_link),
                                   parse_mode='html', reply_markup=kb)
    else:
        await call.message.edit_text(_('✅ Лот видалено.'), reply_markup=main_kb)
        await delete_lot_sql(lot_id)


async def delete_ad(call: types.CallbackQuery, state: FSMContext):
    fsm_data = await state.get_data()
    ad_id = fsm_data.get('change_ad')
    ad = await get_adv(ad_id)
    if ad.post_link:
        try:
            await bot.delete_message(chat_id=ADVERT_CHANNEL, message_id=ad.message_id)
        except:
            pass

    await call.message.edit_text(_('✅ Оголошення видалено.'), reply_markup=main_kb)
    await delete_adv_sql(ad_id)
    if scheduler.get_job(f'adv_repost_{ad_id}'):
        scheduler.remove_job(f'adv_repost_{ad_id}')
    if scheduler.get_job(f'adv_{ad_id}'):
        scheduler.remove_job(f'adv_{ad_id}')


async def time_left_popup(call: types.CallbackQuery, state: FSMContext):
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


async def accept_lot(call: types.CallbackQuery, state: FSMContext):
    accept = call.data.split('_')
    new_lot_id = accept[-1]
    lot = await get_lot(new_lot_id)
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

        if not scheduler.get_job(f'lot_{new_lot_id}'):
            msg = await send_post(owner_id, AUCTION_CHANNEL, photo_id, video_id, description, start_price,
                                  price_steps, currency=currency, city=city, lot_id=new_lot_id, moder_review=None,
                                  photos_link=photos_link)
            await update_lot_sql(lot_id=new_lot_id, lot_link=msg.url, message_id=msg.message_id, approved=1)
            scheduler.add_job(lot_ending, trigger='interval', id=f'lot_{new_lot_id}', hours=lot.lot_time_living,
                              kwargs={'job_id': new_lot_id, 'msg_id': msg.message_id})
            # scheduler.add_job(lot_ending, trigger='cron', id=new_lot_id, minute='4,3,3',
            #                   kwargs={'job_id': new_lot_id, 'msg_id': msg.message_id})
            channel = await bot.get_chat(chat_id=AUCTION_CHANNEL)
            await call.answer()
            text = _("✅ Готово!\n"
                     "Лот <b><a href='{msg_url}'>{desc}...</a></b> "
                     "опубліковано в каналі <b><a href='{channel_link}'>"
                     "{channel_name}</a></b>").format(msg_url=msg.url,
                                                      desc=description[:15],
                                                      channel_link=channel.invite_link,
                                                      channel_name=channel.username)
            await call.message.edit_caption(caption=text, parse_mode='html', reply_markup=main_kb)
            await bot.send_message(chat_id=owner_id, text=text, parse_mode='html', reply_markup=main_kb)
        else:
            await call.answer(text=_('Лот вже опубліковано.'))
    else:
        await call.answer(text=_('Лот вже відхилено.'))
    await state.reset_state()


async def accept_adv(call: types.CallbackQuery, state: FSMContext):
    accept = call.data.split('_')
    new_adv_id = accept[-1]
    adv = await get_adv(new_adv_id)
    if adv:
        video_id = adv.video_id
        photo_id = adv.photo_id
        description = adv.description
        city = adv.city
        owner_id = adv.owner_telegram_id
        photos_link = adv.photos_link
        post_per_day = adv.post_per_day
        owner = await bot.get_chat(owner_id)

        if not scheduler.get_job(f'adv_{new_adv_id}'):
            msg = await send_advert(user_id=owner_id, send_to_id=ADVERT_CHANNEL, photo_id=photo_id, video_id=video_id,
                                    description=description, city=city, advert_id=new_adv_id, moder_review=None,
                                    photos_link=photos_link)
            await update_adv_sql(adv_id=new_adv_id, post_link=msg.url, message_id=msg.message_id, approved=1)
            scheduler.add_job(adv_ending, trigger='interval', id=f'adv_{new_adv_id}', hours=168,
                              kwargs={'job_id': new_adv_id})
            now = datetime.datetime.now()
            if post_per_day:
                hours_mapping = {
                    1: str(now.hour),
                    2: f'{randint(8, 14)},{randint(17, 23)}',
                    3: f'{randint(8, 14)},{randint(15, 18)},{randint(19, 23)}'}
                # 3: f'18, 18,18'}
                scheduler.add_job(repost_adv, trigger='cron', id=f'adv_repost_{new_adv_id}',
                                  hour=hours_mapping.get(int(post_per_day)),
                                  minute=f'{now.minute}',
                                  kwargs={'job_id': new_adv_id, 'user_tg': owner})
                job = scheduler.get_job(f'adv_repost_{new_adv_id}')
                logging.info(f'name={job.name}; kwargs={job.kwargs}; next_run_time={job.next_run_time}')

            channel = await bot.get_chat(chat_id=ADVERT_CHANNEL)
            await call.answer()
            text = _("✅ Готово!\n"
                     "Оголошення <b><a href='{msg_url}'>{desc}...</a></b> "
                     "опубліковано в каналі <b><a href='{channel_link}'>"
                     "{channel_name}</a></b>").format(msg_url=msg.url,
                                                      desc=description[:15],
                                                      channel_link=channel.invite_link,
                                                      channel_name=channel.username)
            await call.message.edit_caption(caption=text, parse_mode='html', reply_markup=main_kb)
            await bot.send_message(chat_id=owner_id, text=text, parse_mode='html', reply_markup=main_kb)
        else:
            await call.answer(text=_('Оголошення вже опубліковано.'))
    else:
        await call.answer(text=_('Оголошення вже відхилено.'))
    await state.reset_state()


async def decline_lot(call: types.CallbackQuery):
    decline = call.data.split('_')
    new_lot_id = decline[-1]
    lot = await get_lot(new_lot_id)
    if lot:
        if scheduler.get_job(f'lot_{new_lot_id}'):
            await call.answer(text=_('Лот вже опубліковано.'))
        else:
            await call.answer()
            owner_id = lot.owner_telegram_id
            await delete_lot_sql(new_lot_id)
            await call.message.answer(text='✅ Лот успішно відхилено')
            await bot.send_message(chat_id=owner_id,
                                   text=_("❗️Нажаль ваш лот <b>{desc}...</b> не пройшов модерацію.").format(
                                       desc=lot.description[:15]),
                                   parse_mode='html', reply_markup=main_kb)
    else:
        await call.answer(text=_('Лот вже відхилено.'))


async def decline_adv(call: types.CallbackQuery):
    decline = call.data.split('_')
    new_adv_id = decline[-1]
    adv = await get_adv(new_adv_id)
    if adv:
        if scheduler.get_job(f'adv_{new_adv_id}'):
            await call.answer(text=_('Оголошення вже опубліковано.'))
        else:
            await call.answer()
            owner_id = adv.owner_telegram_id
            await delete_adv_sql(new_adv_id)
            await call.message.answer(text='✅ Оголошення успішно відхилено')
            await bot.send_message(chat_id=owner_id,
                                   text=_("❗️Нажаль ваше оголошення <b>{desc}...</b> не пройшло модерацію.").format(
                                       desc=adv.description[:15]),
                                   parse_mode='html', reply_markup=main_kb)
    else:
        await call.answer(text=_('Оголошення вже відхилено.'))


async def lot_deletion(call: types.CallbackQuery):
    data = call.data.split('_')
    action = data[2]
    lot_id = data[-1]
    lot = await get_lot(lot_id)
    text = None
    if lot:
        if action == 'accept':
            text = _('✅ Ваш лот <b>{desc}...</b> видалено').format(desc=lot.description[:15])
            await call.message.edit_text(_('✅ Лот видалено.'), reply_markup=main_kb)
            await delete_lot_sql(lot_id)
            try:
                scheduler.remove_job(f'lot_{lot_id}')
                await bot.delete_message(chat_id=AUCTION_CHANNEL, message_id=lot.message_id)
            except:
                ...
        elif action == 'decline':
            text = _('❌ Ваш лот <b>{desc}...</b> не видалено.\n'
                     f'Запит відхилено.').format(desc=lot.description[:15])
            await call.message.edit_text(_('✅ Видалення відхилено.'), reply_markup=main_kb)
        if text:
            await bot.send_message(chat_id=lot.owner_telegram_id, text=text, parse_mode='html', reply_markup=main_kb)
    else:
        await call.answer(text=_('Запит вже оброблений.'))


async def anti_sniper(call: types.CallbackQuery, state: FSMContext):
    user = await get_user(call.from_user.id)
    await state.set_state(FSMClient.sniper_time)
    await call.message.edit_text(text=_('⏱ Ваш поточний час антиснайпингу - {minute}хв.\n'
                                        'Якщо хочете змінити - оберіть варіант нижче:').format(
        minute=user.anti_sniper.minute), reply_markup=anti_kb)


async def new_sniper_time(call: types.CallbackQuery, state: FSMContext):
    new_time = datetime.time(hour=0, minute=int(call.data), second=0)
    await update_user_sql(telegram_id=call.from_user.id, anti_sniper=new_time)
    await call.message.edit_text(text=_('✅ Час антиснайпингу змінено на {minute}хв').format(minute=new_time.minute),
                                 reply_markup=main_kb)


async def lot_question(message: types.Message, state: FSMContext):
    name_in_text = await username_in_text(message.text, message.from_user.username)
    phone_num_in_text = await phone_in_text(text=message.text)
    if name_in_text or phone_num_in_text:
        await message.answer(text=_('Схоже ви намагались обмінятись контактними даними. Перефразуйте ваше запитання:'),
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[[back_to_answers_btn]]))
        return
    data = await state.get_data()
    lot_id = data.get('lot_id_question')
    lot = await get_lot(lot_id)
    owner_id = data.get('owner_id')
    await create_question(message.text, sender_id=message.from_user.id, lot_id=lot_id, owner_id=owner_id)
    await message.answer(text=_('✅ Власник лоту отримав ваше запитання!\n'
                                'Очікуйте на відповідь.'), reply_markup=main_kb)
    await bot.send_message(chat_id=owner_id,
                           text=_("💬 Ви отримали запитання по лоту <a href='{lot_link}'><b>{lot_desc}</b></a>").format(
                               lot_desc=lot.description[:25], lot_link=lot.lot_link),
                           parse_mode='html', reply_markup=main_kb, disable_web_page_preview=True)
    await state.reset_state(with_data=True)


async def answer_question(call: types.CallbackQuery, state: FSMContext):
    question_id = call.data
    await state.update_data(question_id=question_id)
    question = await get_question(question_id)
    await state.set_state(FSMClient.send_answer)
    await call.message.edit_text(
        text=_('👇 Надішліть відповідь або видаліть запитання:\n'
               '<b>{question_text}</b>').format(question_text=question.question),
        parse_mode='html', reply_markup=back_to_questions_kb)


async def delete_question(call: types.CallbackQuery, state: FSMContext):
    if call.data == 'delete_question':
        data = await state.get_data()
        question_id = data.get('question_id')
        await delete_question_db(question_id)
        await call.message.edit_text(text=_("✅ Повідомлення видалено"))
    await answers_list(call)
    return


async def send_answer(message: types.Message, state: FSMContext):
    answer_text = message.text
    name_in_text = await username_in_text(answer_text, message.from_user.username)
    phone_num_in_text = await phone_in_text(text=answer_text)
    if name_in_text or phone_num_in_text:
        await message.answer(text=_('Схоже ви намагались обмінятись контактними даними. Перефразуйте вашу відповідь:'),
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[[back_to_questions]]))
        return
    data = await state.get_data()
    question_id = data.get('question_id')
    question = await get_question(question_id)
    lot = await get_lot(lot_id=question.lot_id)
    await create_answer(answer=answer_text, sender_id=message.from_user.id, lot_id=question.lot_id,
                        recipient_id=question.sender_id)
    await message.answer(text='Відповідь надіслано.', reply_markup=main_kb)
    await bot.send_message(chat_id=question.sender_id, text=_(
        "Автор лоту <a href='{lot_link}'><b>{lot_desc}</b></a> надіслав вам відповідь.").format(
        lot_desc=lot.description[:20], lot_link=lot.lot_link), parse_mode='html', reply_markup=quest_answ_kb,
                           disable_web_page_preview=True)
    await delete_question_db(question_id)


async def create_adv_sub(call: types.CallbackQuery, state: FSMContext):
    user = await get_user(call.from_user.id)
    if user.user_adv_token:
        status = await get_status(user.user_adv_token)
        if status in ('CREATED', 'APPROVED'):
            token = user.user_adv_token
        else:
            token = await create_payment_token(usd=1)
            await update_user_sql(call.from_user.id, user_adv_token=token)
    else:
        token = await create_payment_token(usd=1)
        await update_user_sql(call.from_user.id, user_adv_token=token)

    kb = await payment_kb(token, activate_btn_text=_('Оплатити 15$'), callback_data=f'update_{token}')
    await call.message.edit_text(text=_('💲 Вартість підписки 15$ на 30 днів.\n\n'
                                        'Оплатіть підписку натиснувши на кнопку нижче 👇'), reply_markup=kb)
    # sub_seconds = call.data + time.time()
    # await update_user_sql(call.from_user.id, advert_subscribe_time=sub_seconds)
    # await call.message.edit_text(text='✅ Підписку успішно ')


async def update_adv_payment_status(call: types.CallbackQuery, state: FSMContext):
    token = call.data.split('_')[1]
    payment = await payment_approved(token)
    if payment:
        await update_user_sql(call.from_user.id, advert_subscribe_time=604800 + time.time())
        await call.message.edit_text(text=_('✅ Вітаю! Підписку на виставлення оголошень успішно оформлено на 30 днів.'),
                                     reply_markup=main_kb)
    else:
        kb = await payment_kb(token, activate_btn_text=_('Оплатити 15$'), callback_data=f'update_{token}')
        try:
            await call.message.edit_text(text=_('⚠️ Оплату не зафіксовано'), reply_markup=kb)
        except:
            pass
        return


async def change_desc_exist(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    object_type = call.data.split('_')[-1]
    await state.update_data(object_type=object_type)
    if data.get('change_ad'):
        kb = back_show_ad_kb
        text = _('📝 Напишіть опис для оголошення:')
    else:
        kb = back_show_lot_kb
        text = _('📝 Напишіть опис для лоту:\n\n'
                 '<i>Наприклад: Навушники Marshall Major IV Bluetooth Black</i>')
    await state.set_state(FSMClient.new_desc_exist)
    await call.message.edit_text(text=text, reply_markup=kb, parse_mode='html')


async def request_new_desc(message: types.Message, state: FSMContext):
    fsm_data = await state.get_data()
    object_type = fsm_data.get('object_type')
    await state.reset_state()
    await message.answer(text=_('✅ Очікуйте підтвердження модератора.'), reply_markup=main_kb)

    for admin_id in ADMINS:
        if object_type == 'adv':
            obj_id = fsm_data.get('change_ad')
            await update_adv_sql(obj_id, new_text=message.text)
            ad = await get_adv(obj_id)
            await send_advert(user_id=message.from_user.id, send_to_id=admin_id, description=ad.description,
                              city=ad.city,
                              photos_link=ad.photos_link, video_id=ad.video_id, photo_id=ad.photo_id,
                              change_text=True, advert_id=obj_id, new_desc=ad.new_text)
        else:
            obj_id = fsm_data.get('change_lot')
            await update_lot_sql(obj_id, new_text=message.text)
            lot = await get_lot(obj_id)
            await send_post(message.from_user.id, admin_id, lot.photo_id, lot.video_id, lot.description,
                            lot.start_price,
                            lot.price_steps, currency=lot.currency, city=lot.city, lot_id=obj_id,
                            photos_link=lot.photos_link, change_text=True, new_desc=lot.new_text)


async def edit_new_text(call: types.CallbackQuery, state: FSMContext):
    obj_type = call.data.split(':')[-1]
    obj_id = call.data.split(':')[-3]
    action = call.data.split(':')[-2]
    if action == 'accept':
        if obj_type == 'lot':
            lot = await get_lot(obj_id)
            if lot.new_text:
                user = await get_user(lot.owner_telegram_id)
                kb = await create_price_step_kb(lot.price_steps, obj_id, lot.currency)
                kb.inline_keyboard.extend([[InlineKeyboardButton(text='⏳', callback_data=f'time_left_lot_{obj_id}')]])
                kb.inline_keyboard.extend(
                    [[InlineKeyboardButton(text=_('💬 Задати питання автору', locale=user.language),
                                           url=await create_start_link(bot=call.bot,
                                                                       payload=f'question_{user.telegram_id}_{obj_id}',
                                                                       encode=True))]])
                await update_lot_sql(obj_id, description=lot.new_text, new_text=None)
                try:
                    caption = _("<b>{description}</b>\n\n"
                                "🏙 <b>Місто:</b> {city}\n\n"
                                "👇 <b>Ставки учасників:</b>\n\n"
                                "💰 <b>Стартова ціна:</b> {start_price} {currency}\n"
                                "⏱ <b>Антиснайпер</b> {anti_sniper} хв.\n")
                    if lot.bidder_telegram_id:
                        bidder_name = await bot.get_chat(lot.bidder_telegram_id)
                        caption = await new_bid_caption(caption, bidder_name.first_name, lot.last_bid,
                                                        lot.currency, user.language, lot.bid_count, lot.photos_link)
                    if lot.photos_link:
                        caption += _("\n<a href='{photos_link}'><b>👉 Оглянути додаткові фото</b></a>",
                                     locale=user.language).format(
                            photos_link=lot.photos_link)
                    await bot.edit_message_caption(chat_id=AUCTION_CHANNEL, message_id=lot.message_id,
                                                   caption=caption.format(
                                                       description=lot.new_text, city=lot.city,
                                                       start_price=lot.start_price, currency=lot.currency,
                                                       anti_sniper=user.anti_sniper.minute, bid_count=lot.bid_count,
                                                       price=lot.last_bid),
                                                   parse_mode='html', reply_markup=kb)
                except Exception:
                    await call.answer(text='Запит вже оброблено.')
                    return
                await bot.send_message(chat_id=user.telegram_id, text=_(
                    "✅ Модератор підтвердив зміну опису лоту.\n\n<a href='{lot_post}'><b>👉 Перейти до лоту.</b></a>",
                    locale=user.language).format(
                    lot_post=lot.lot_link), parse_mode='html', reply_markup=main_kb)
            else:
                await call.answer(text='Запит вже оброблено.')
                return
        elif obj_type == 'adv':
            ad = await get_adv(obj_id)
            if ad.new_text:
                user = await get_user(ad.owner_telegram_id)
                user_tg = await bot.get_chat(user.telegram_id)
                kb = InlineKeyboardMarkup(inline_keyboard=[])
                kb.inline_keyboard.extend([[InlineKeyboardButton(text='⏳', callback_data=f'time_left_adv_{obj_id}')]])
                kb.inline_keyboard.extend(
                    [[InlineKeyboardButton(text=_('💬 Задати питання автору', locale=user.language),
                                           url=f'https://t.me/{user_tg.username}')]])
                await update_adv_sql(obj_id, description=ad.new_text, new_text=None)
                caption = _("<b>{description}</b>\n\n"
                            "🏙 <b>Місто:</b> {city}\n", locale=user.language).format(description=ad.new_text,
                                                                                     city=ad.city)
                if ad.photos_link:
                    caption += _("\n<a href='{photos_link}'><b>👉 Оглянути додаткові фото</b></a>",
                                 locale=user.language).format(
                        photos_link=ad.photos_link)
                try:
                    await bot.edit_message_caption(chat_id=ADVERT_CHANNEL, message_id=ad.message_id, caption=caption,
                                                   parse_mode='html', reply_markup=kb)
                except Exception:
                    await call.answer(text='Запит вже оброблено.')
                    return
                await bot.send_message(chat_id=user.telegram_id, text=_(
                    "✅ Модератор підтвердив зміну опису оголошення.\n\n<a href='{lot_post}'><b>👉 Перейти до оголошення.</b></a>",
                    locale=user.language).format(
                    lot_post=ad.post_link), parse_mode='html', reply_markup=main_kb)
            else:
                await call.answer(text='Запит вже оброблено.')
                return
    else:
        if obj_type == 'lot':
            lot = await get_lot(obj_id)
            user = await get_user(lot.owner_telegram_id)
            if lot.new_text:
                await update_lot_sql(obj_id, new_text=None)
                await bot.send_message(chat_id=lot.owner_telegram_id,
                                       text=_(
                                           '❌ Запит на зміну опису для лоту <a href="{lot_link}"><b>{lot_desc}</b></a> відхилено.',
                                           locale=user.language).format(
                                           lot_link=lot.lot_link, lot_desc=lot.description), reply_markup=main_kb,
                                       parse_mode='html')
                await call.answer(text='✅ Запит на зміну опису відхилено')
            else:
                await call.answer('Запит вже оброблено.')
        elif obj_type == 'adv':
            ad = await get_adv(obj_id)
            user = await get_user(ad.owner_telegram_id)
            if ad.new_text:
                await update_adv_sql(obj_id, new_text=None)
                await bot.send_message(chat_id=ad.owner_telegram_id,
                                       text=_(
                                           '❌ Запит на зміну опису для оголошення <a href="{lot_link}"><b>{lot_desc}</b></a> відхилено.',
                                           locale=user.language).format(
                                           lot_link=ad.post_link, lot_desc=ad.description), reply_markup=main_kb,
                                       parse_mode='html')
                await call.answer(text='✅ Запит на зміну опису відхилено')
            else:
                await call.answer('Запит вже оброблено.')


async def republish_adv(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    answer = call.data
    if answer == 'yes':
        await call.message.edit_text(text=_("Оберіть кількість повторних публікацій на день:"),
                                     reply_markup=repost_count_kb)
        await state.set_state(FSMClient.repost_count)
    else:
        await save_repost_count(call, state)
        return


async def save_repost_count(call: types.CallbackQuery, state: FSMContext):
    if isinstance(call, types.CallbackQuery):
        if call.data in ('1', '2', '3'):
            await state.update_data(repost_count=call.data)
        last_message_id = call.message.message_id
    else:
        last_message_id = call.message_id
    fsm_data = await state.get_data()
    kb = deepcopy(ready_to_publish_ad_kb)
    kb.inline_keyboard.extend([[cancel_btn, publish_adv_btn]])
    text = _('⬆️ Оголошення готове до публікації!\n'
             'Перевірте всю інформацію і натисніть <b>✅ Опублікувати</b>, коли будете готові.')
    await send_post_fsm(fsm_data, call.from_user.id, is_ad=True)
    await bot.send_message(chat_id=call.from_user.id, text=text, reply_markup=kb, parse_mode='html',
                           reply_to_message_id=last_message_id)


@router.my_chat_member()
async def my_chat_member_handler(my_chat_member: types.ChatMemberUpdated):
    if my_chat_member.chat.type in ('channel', 'group', 'supergroup'):
        user_id = my_chat_member.from_user.id
        if my_chat_member.new_chat_member.status is ChatMemberStatus.ADMINISTRATOR:
            chat_link = await bot.export_chat_invite_link(chat_id=my_chat_member.chat.id)
            await bot.send_message(chat_id=user_id,
                                   text=_("{title} успішно підключено!").format(
                                       title=my_chat_member.chat.title), parse_mode='html')
            await create_group_channel(owner_telegram_id=user_id, chat_id=my_chat_member.chat.id,
                                       chat_type=my_chat_member.chat.type, chat_name=my_chat_member.chat.title,
                                       chat_link=chat_link)
        elif my_chat_member.new_chat_member.status is ChatMemberStatus.MEMBER:
            await bot.send_message(chat_id=user_id,
                                   text=_(
                                       "Для того, щоб бот функціонував у каналі {title}, потрібно надати йому права адміністратора.").format(
                                       title=my_chat_member.chat.title), parse_mode='html')


async def groups_and_channels(call: types.CallbackQuery):
    await call.message.edit_text(text=_('Ви обрали 👥 Групи та канали'), reply_markup=group_channels_kb)


async def my_channels_groups(call: types.CallbackQuery, state: FSMContext):
    user_chats = await get_user_chats(call.from_user.id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=chat.chat_name, callback_data=chat.chat_id)] for chat in
                         user_chats])
    kb.inline_keyboard.extend([[back_group_channels_btn]])
    await state.set_state(FSMClient.user_chat_id)
    await call.message.edit_text(text=_('Ваші групи/канали.\n'
                                        'Щоб активувати або перевірити статус бота, оберіть потрібну групу/канал:'),
                                 reply_markup=kb)


async def other_channels_groups(call: types.CallbackQuery):
    other_chats = await get_all_chats()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=chat.chat_name, url=chat.chat_link)] for chat in
                         other_chats])
    kb.inline_keyboard.extend([[back_group_channels_btn]])
    await call.message.edit_text(text=_('Список каналів у яких працює бот:'),
                                 reply_markup=kb)


async def user_chat_menu(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(text=_('Перевірка підписки...'))
    text = _('👌 Ваш бот активований.\n'
             'Підписка діє до {sub_date}')
    # fsm_data = await state.get_data()
    user_chat_id = call.data
    is_subscribed = await bot_sub_time_remain(user_chat_id)
    if is_subscribed:
        chat = await get_chat_record(user_chat_id)
        sub_date = datetime.datetime.fromtimestamp(chat.subscription_time).strftime("%d.%m.%Y")
        await call.message.edit_text(text=text.format(sub_date=sub_date), reply_markup=back_my_channels_groups_kb)
    elif await chat_have_approved_token(user_chat_id):
        chat = await get_chat_record(user_chat_id)
        sub_date = datetime.datetime.fromtimestamp(chat.subscription_time).strftime("%d.%m.%Y")
        await update_chat_sql(user_chat_id, subscription_time=604800 + time.time())
        await call.message.edit_text(text=text.format(sub_date=sub_date), reply_markup=back_my_channels_groups_kb)
    else:
        chat = await get_chat_record(user_chat_id)
        if chat.paypal_token:
            status = await get_status(chat.paypal_token)
            if status in ('CREATED', 'APPROVED'):
                token = chat.paypal_token
            else:
                token = await create_payment_token(usd=1)
                await update_chat_sql(user_chat_id, paypal_token=token)
        else:
            token = await create_payment_token(usd=1)
            await update_chat_sql(user_chat_id, paypal_token=token)
        kb = await payment_kb(token, activate_btn_text=_('🔐 Активувати'),
                              callback_data=f'bot_subscription_update_{user_chat_id}_{token}',
                              back_btn=back_my_channels_groups)
        await call.message.edit_text(text=_('🔴 Статус: не активний.\n'
                                            'Для активації оформіть підписку, натиснувши кнопку «🔐 Активувати» нижче.\n'
                                            'Після активації натисніть 🔄 Оновити статус.'),
                                     reply_markup=kb)


async def update_bot_subscription_status(call, state: FSMContext):
    token = call.data.split('_')[-1]
    user_chat_id = call.data.split('_')[-2]
    payment = await payment_approved(token)
    if payment:
        await update_chat_sql(user_chat_id, subscription_time=604800 + time.time())
        await call.message.edit_text(text=_('✅ Вітаю! Бота успішно активовано на 30 днів.'),
                                     reply_markup=main_kb)
    else:
        await user_chat_menu(call, state)
        return


class IsPrivateChatFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return message.chat.type == "private"


def register_client_handlers(r: Router):
    r.message.register(start, CommandStart(), IsPrivateChatFilter())
    r.callback_query.register(main_menu, FSMClient.language)
    r.callback_query.register(main_menu, F.data == 'main_menu')
    r.message.register(main_menu, Command('main_menu'), IsPrivateChatFilter())
    r.callback_query.register(help_, F.data == 'help')
    r.callback_query.register(auction_menu, F.data == 'auction')
    r.callback_query.register(my_auctions, F.data == 'my_auctions')

    r.callback_query.register(ask_city, F.data == 'create_auction')
    r.message.register(ask_currency, FSMClient.city)
    r.callback_query.register(ask_description, FSMClient.currency)
    r.message.register(ask_price, FSMClient.description)
    r.message.register(ask_price_steps, FSMClient.price)
    r.message.register(ask_lot_living, FSMClient.price_steps)
    r.callback_query.register(ask_media, FSMClient.lot_time_living)
    r.message.register(ready_lot, FSMClient.media)
    r.callback_query.register(ready_lot, F.data == 'back_to_ready')
    r.callback_query.register(lot_publish, F.data == 'publish_lot')

    r.callback_query.register(add_menu, F.data == 'ad_menu')
    r.callback_query.register(my_ads, F.data == 'my_ads')
    r.callback_query.register(ask_description_ad, F.data == 'create_ad')

    r.callback_query.register(my_chats, F.data == 'chats')
    r.callback_query.register(question_list, F.data == 'questions')
    r.callback_query.register(answer_question, FSMClient.choose_question)
    r.callback_query.register(choose_answer, FSMClient.choose_answer)
    r.callback_query.register(del_read_answer, FSMClient.delete_answer)
    r.callback_query.register(answers_list, F.data == 'answers')

    r.callback_query.register(ask_description_ad, F.data == 'create_ad')
    r.message.register(ask_city_ad, FSMClient.description_ad)
    r.message.register(ask_media_ad, FSMClient.city_ad)
    r.message.register(save_media_ad, FSMClient.media_ad)

    r.callback_query.register(save_media_ad, F.data == 'back_to_ready_ad')
    r.callback_query.register(lot_publish, F.data == 'publish_lot')
    r.callback_query.register(adv_publish, F.data == 'publish_adv')

    r.callback_query.register(make_bid, F.data.startswith('bid'))
    r.callback_query.register(show_lot, FSMClient.change_lot)
    r.callback_query.register(show_lot, F.data == 'show_lot')
    r.callback_query.register(show_ad, FSMClient.change_ad)
    r.callback_query.register(show_ad, F.data == 'show_ad')

    r.callback_query.register(change_media, F.data == 'change_media')
    r.callback_query.register(change_desc, F.data == 'change_desc')
    r.callback_query.register(change_start_price, F.data == 'change_start_price')
    r.callback_query.register(change_lot_time, F.data == 'change_lot_time')
    r.callback_query.register(change_price_steps, F.data == 'change_price_steps')
    r.callback_query.register(change_city, F.data == 'change_city')

    r.message.register(ready_lot, FSMClient.change_media)
    r.message.register(save_media_ad, FSMClient.change_media_ad)
    r.message.register(set_desc, FSMClient.change_desc)
    r.message.register(set_start_price, FSMClient.change_start_price)
    r.callback_query.register(set_lot_time, FSMClient.change_lot_time)
    r.message.register(set_price_steps, FSMClient.change_price_steps)
    r.message.register(set_new_city, FSMClient.change_city)

    r.callback_query.register(delete_ad, F.data == 'delete_ad')
    r.callback_query.register(delete_lot, F.data == 'delete_lot')
    r.callback_query.register(time_left_popup, F.data.startswith('time_left'))

    r.callback_query.register(lot_deletion, F.data.startswith('lot_deletion_'))
    r.callback_query.register(accept_lot, F.data.startswith('accept_lot'))
    r.callback_query.register(decline_lot, F.data.startswith('decline_lot'))

    r.callback_query.register(accept_adv, F.data.startswith('accept_adv'))
    r.callback_query.register(decline_adv, F.data.startswith('decline_adv'))

    r.callback_query.register(help_, F.data == 'help')

    r.callback_query.register(anti_sniper, F.data == 'anti_sniper')
    r.callback_query.register(new_sniper_time, FSMClient.sniper_time)

    r.message.register(lot_question, FSMClient.question)
    r.message.register(send_answer, FSMClient.send_answer)

    r.callback_query.register(delete_question, F.data == 'delete_question')
    r.callback_query.register(update_adv_payment_status, F.data.startswith('update_'))
    r.callback_query.register(create_adv_sub, FSMClient.adv_sub_seconds)

    r.callback_query.register(change_desc_exist, F.data.startswith('change_desc_exist'))
    r.callback_query.register(edit_new_text, F.data.startswith('edit_new_text'))
    r.message.register(request_new_desc, FSMClient.new_desc_exist)
    r.callback_query.register(republish_adv, FSMClient.repost_count_answer)
    r.callback_query.register(save_repost_count, FSMClient.repost_count)

    r.callback_query.register(groups_and_channels, F.data == 'groups_and_channels')
    r.callback_query.register(my_channels_groups, F.data == 'my_channels_groups')
    r.callback_query.register(other_channels_groups, F.data == 'other_channels_groups')
    r.callback_query.register(user_chat_menu, FSMClient.user_chat_id)
    r.callback_query.register(update_bot_subscription_status, F.data.startswith('bot_subscription_update'))
