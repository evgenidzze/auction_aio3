import datetime
import locale
import logging
import time
from copy import deepcopy
from random import randint
from typing import List
from aiogram import types, Dispatcher, Router
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.deep_linking import decode_payload, get_start_link
from aiogram.utils.exceptions import MessageNotModified

from utils.aiogram_media_group import media_group_handler
from create_bot import bot, scheduler, i18n, _, storage_group, job_stores
from db.db_manage import add_new_user, create_lot, get_lot, make_bid_sql, get_user_lots, delete_lot_sql, \
    get_user, update_user_sql, update_lot_sql, create_question, get_question, \
    create_answer, get_question_or_answer, get_answer, delete_answer, delete_question_db, User, create_adv, get_adv, \
    update_adv_sql, delete_adv_sql, get_user_ads
from handlers.middleware import HiddenUser
from keyboards.kb import language_kb, main_kb, cancel_kb, lot_time_kb, \
    create_auction_btn, back_to_main_btn, cancel_btn, delete_lot_kb, back_to_ready_kb, back_to_ready_btn, currency_kb, \
    decline_lot_deletion_btn, accept_lot_deletion_btn, anti_kb, ready_to_publish_kb, publish_btn, quest_answ_kb, \
    back_to_messages, back_to_questions_kb, back_to_answers_kb, back_to_answers_btn, back_to_questions, \
    ready_to_publish_ad_kb, publish_adv_btn, back_to_ready_ad_kb, subscribe_adv_kb, create_advert_btn, delete_ad_kb, \
    back_show_ad_kb, back_show_lot_kb, yes_no_kb, repost_count_kb
from utils.config import AUCTION_CHANNEL, ADVERT_CHANNEL
from utils.paypal import create_payment_token, get_status
from utils.utils import lot_ending, create_user_lots_kb, send_post, payment_approved, contact_payment_kb_generate, \
    new_bid_caption, send_post_fsm, create_question_kb, create_answers_kb, username_in_text, \
    phone_in_text, create_telegraph_link, send_advert, save_sent_media, adv_ending, adv_sub_time_remain, \
    user_have_approved_adv_token, payment_kb, create_price_step_kb, repost_adv

ADMINS = [397875584, 432530900]
locale.setlocale(locale.LC_ALL, 'uk_UA.utf8')
router = Router()


class FSMClient(StatesGroup):
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
    logging.info('jobs:')
    for job in scheduler.get_jobs():
        logging.info(f'{job.id}-{job}-{job.kwargs}')
    if message.text == '/start':
        await FSMClient.language.set()
        text = _('<b>Оберіть мову / Choose a language:</b>')
        if isinstance(message, types.Message):
            await message.answer(text=text, parse_mode='html',
                                 reply_markup=language_kb)
        elif isinstance(message, types.CallbackQuery):
            await message.message.edit_text(text=text, parse_mode='html',
                                            reply_markup=language_kb)
    else:
        args = decode_payload(message.get_args())
        lot_id = args.split('_')[-1]
        lot = await get_lot(lot_id)
        if lot:
            owner_id = args.split('_')[-2]
            await state.update_data(lot_id_question=lot_id)
            await state.update_data(owner_id=owner_id)
            await FSMClient.question.set()
            await message.answer(text=_('Напишіть ваше запитання:'), reply_markup=cancel_kb)
        else:
            await message.answer(text=_('Оголошення не актуальне'), reply_markup=main_kb)


async def lot_question(message: types.Message, state: FSMContext):
    name_in_text = await username_in_text(message.text, message.from_user.username)
    phone_num_in_text = await phone_in_text(text=message.text)
    if name_in_text or phone_num_in_text:
        await message.answer(text=_('Схоже ви намагались обмінятись контактними даними. Перефразуйте ваше запитання:'),
                             reply_markup=InlineKeyboardMarkup().add(back_to_answers_btn))
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


async def main_menu(call, state: FSMContext):
    clean_text = "Вітаю, <b>{first_name}!</b><a href='https://telegra.ph/file/3f6168cc5f94f115331ac.png'>⠀</a>\n"
    text = _(clean_text).format(first_name=call.from_user.username)
    if isinstance(call, types.CallbackQuery):
        if call.data in ('en', 'uk'):
            await add_new_user(telegram_id=call.from_user.id, language=call.data)
            text = _(clean_text, locale=call.data).format(first_name=call.from_user.username)
        await state.reset_state(with_data=True)
        await call.message.edit_text(text=text, parse_mode='html',
                                     reply_markup=main_kb)
    else:
        await call.answer(text=text, parse_mode='html', reply_markup=main_kb)
    await state.reset_state(with_data=True)


async def my_chats(call: types.CallbackQuery, state: FSMContext):
    await state.reset_state(with_data=True)
    await call.message.edit_text(text=_('👇 Оберіть варіант:'), reply_markup=quest_answ_kb)


async def question_list(call: types.CallbackQuery):
    await call.answer()
    question_texts_list = await get_question_or_answer(call.from_user.id, model_name='question')
    kb = await create_question_kb(question_texts_list, call.from_user.id)
    kb.add(back_to_messages)
    if question_texts_list:
        await FSMClient.choose_question.set()
        await call.message.edit_text(text=_('👇 Оберіть запитання щоб відповісти або видалити:'), reply_markup=kb)
    else:
        try:
            await call.message.edit_text(text=_('🤷🏻‍♂️ У вас немає повідомлень.'), reply_markup=quest_answ_kb)
        except:
            pass


async def answer_question(call: types.CallbackQuery, state: FSMContext):
    question_id = call.data
    await state.update_data(question_id=question_id)
    question = await get_question(question_id)
    await FSMClient.send_answer.set()
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


async def answers_list(call: types.CallbackQuery):
    await call.answer()
    answer_list = await get_question_or_answer(call.from_user.id, model_name='answer')
    kb = await create_answers_kb(answer_list, recipient_id=call.from_user.id)
    kb.add(back_to_messages)
    if answer_list:
        await FSMClient.choose_answer.set()
        if call.data in ('read', 'delete_question'):
            await call.message.answer(text=_('👇 Оберіть відповідь щоб прочитати:'), reply_markup=kb)
        else:
            await call.message.edit_text(text=_('👇 Оберіть відповідь щоб прочитати:'), reply_markup=kb)
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
    await FSMClient.delete_answer.set()


async def del_read_answer(call: types.CallbackQuery, state: FSMContext):
    if call.data == 'read':
        data = await state.get_data()
        answer_id = data.get('answer_id')
        await delete_answer(answer_id)
        await call.message.edit_text(text=_("✅ Повідомлення видалено"))
    await answers_list(call)
    return


async def send_answer(message: types.Message, state: FSMContext):
    answer_text = message.text
    name_in_text = await username_in_text(answer_text, message.from_user.username)
    phone_num_in_text = await phone_in_text(text=answer_text)
    if name_in_text or phone_num_in_text:
        await message.answer(text=_('Схоже ви намагались обмінятись контактними даними. Перефразуйте вашу відповідь:'),
                             reply_markup=InlineKeyboardMarkup().add(back_to_questions))
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


async def my_auctions(call: types.CallbackQuery):
    lots = await get_user_lots(call.from_user.id)
    kb = await create_user_lots_kb(lots)
    kb.add(create_auction_btn, back_to_main_btn)
    await FSMClient.change_lot.set()
    await call.message.edit_text(text=_('Оберіть існуючий аукціон або створіть новий:'), parse_mode='html',
                                 reply_markup=kb)


async def my_ads(call: types.CallbackQuery):
    ads = await get_user_ads(call.from_user.id)
    kb = await create_user_lots_kb(ads)
    kb.add(create_advert_btn, back_to_main_btn)
    await FSMClient.change_ad.set()
    await call.message.edit_text(text=_('Оберіть існуючe оголошення або створіть нове:'), parse_mode='html',
                                 reply_markup=kb)


async def ask_city(call: types.CallbackQuery):
    user = await get_user(call.from_user.id)
    if user.is_blocked:
        await bot.send_message(chat_id=call.from_user.id, text=_('Вас було заблоковано за порушення правил.'))
        return
    await FSMClient.city.set()
    await call.message.edit_text(text=_('🌆 Вкажіть ваше місто:'),
                                 parse_mode='html',
                                 reply_markup=cancel_kb)


async def ask_currency(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await FSMClient.currency.set()
    await message.answer(text=_('🫰🏼 Оберіть валюту:'),
                         parse_mode='html',
                         reply_markup=currency_kb)


async def ask_description(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(currency=call.data)
    await FSMClient.description.set()
    await call.message.edit_text(text=_('📝 Напишіть опис для лоту:\n\n'
                                        '<i>Наприклад: Навушники Marshall Major IV Bluetooth Black</i>'),
                                 parse_mode='html',
                                 reply_markup=cancel_kb)


async def ask_price(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await FSMClient.price.set()
    data = await state.get_data()
    currency = data.get('currency')
    await message.answer(text=_('💰 Вкажіть стартову ціну в {currency}:').format(currency=currency),
                         reply_markup=cancel_kb)


async def ask_price_steps(message: types.Message, state: FSMContext):
    if message.text.isdigit() or await state.get_state() == 'FSMClient:price_steps':
        if await state.get_state() != 'FSMClient:price_steps':
            await state.update_data(price=message.text)
        await FSMClient.price_steps.set()
        await message.answer(text=_('Напишіть крок ставки через пробіл (від 1 до 3 кроків):\n'
                                    'Наприклад: 500 1000 1500'), reply_markup=cancel_kb)
    else:
        await message.answer(text=_('❌ Потрібно ввести числове значення.'))
        await ask_price(message, state)


async def ask_lot_living(message: types.Message, state: FSMContext):
    if all(step.isdigit() for step in message.text.split(' ')):
        await state.update_data(price_steps=message.text)
        await FSMClient.lot_time_living.set()
        kb = deepcopy(lot_time_kb).add(cancel_btn)
        await message.answer(text=_('🕙 Скільки буде тривати аукціон?'), reply_markup=kb)
    else:
        await message.answer(text=_('❌ Потрібно ввести числові значення.'))
        await ask_price_steps(message, state)


async def ask_media(call: [types.CallbackQuery, types.Message], state: FSMContext):
    text = _('📸 Надішліть фото і відео:\n'
             '<i>До 5 фото та до 1 відео</i>')
    if isinstance(call, types.CallbackQuery):
        await state.update_data(lot_time_living=call.data)
        await call.message.edit_text(text=text, reply_markup=cancel_kb, parse_mode='html')
    else:
        await call.answer(text=text, reply_markup=cancel_kb, parse_mode='html')

    await FSMClient.media.set()


@media_group_handler(storage_driver=storage_group)
async def ready_lot(messages: List[types.Message], state: FSMContext):
    photos_id, videos_id = [], []
    html = await save_sent_media(messages, photos_id, videos_id, state)
    if html and len(photos_id) > 1:
        await create_telegraph_link(state, html)
    if len(photos_id) > 5 or len(videos_id) > 1:
        await bot.send_message(chat_id=messages[0].from_user.id, text=_('❌ Максимум 5 фото і 1 відео.\n'
                                                                        'Надішліть ще раз ваші медіафайли:'),
                               reply_markup=cancel_kb)
        return
    else:
        fsm_data = await state.get_data()
        if len(messages) <= 1:
            await state.update_data(photos_link=None)
            fsm_data.pop('photos_link', None)
        kb = deepcopy(ready_to_publish_kb)
        kb.add(cancel_btn, publish_btn)
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
    await state.reset_state(with_data=False)


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
    new_lot_id = await create_lot(fsm_data, message.from_user.id)
    channel = await bot.get_chat(AUCTION_CHANNEL)
    for admin_id in ADMINS:
        await send_post(message.from_user.id, admin_id, photo_id, video_id, description, start_price,
                        price_steps, currency=currency, city=city, lot_id=new_lot_id, moder_review=True,
                        photos_link=photos_link)
    await message.message.edit_text(
        text=_("✅ Лот відправлено на модерацію, незабаром він з'явиться у каналі <b><a href='{invite_link}'>"
               "{username}</a></b>.").format(invite_link=channel.invite_link, username=channel.username),
        parse_mode='html', reply_markup=main_kb)


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


async def show_lot(message: types.CallbackQuery, state: FSMContext):
    lot_id = message.data
    if not (lot_id.isdigit()):
        data = await state.get_data()
        lot_id = data.get('change_lot')
    await state.update_data(change_lot=lot_id)
    await state.reset_state(with_data=False)
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
    await state.reset_state(with_data=False)
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
        await FSMClient.change_media_ad.set()
        kb = back_to_ready_ad_kb
    else:
        await FSMClient.change_media.set()
        kb = back_to_ready_kb
    await call.message.edit_text(text=_('📸 Надішліть фото і відео:\n'
                                        '<i>До 5 фото та до 1 відео</i>'), reply_markup=kb,
                                 parse_mode='html')


async def change_desc(call: types.CallbackQuery, state: FSMContext):
    await FSMClient.change_desc.set()
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
    await FSMClient.change_start_price.set()
    fsm_data = await state.get_data()
    currency = fsm_data.get('currency')
    text = _('💰 Вкажіть стартову ціну в {currency}:').format(currency=currency)
    if isinstance(call, types.CallbackQuery):
        await call.message.edit_text(text=text, reply_markup=back_to_ready_kb)
    elif isinstance(call, types.Message):
        await call.answer(text=text, reply_markup=back_to_ready_kb)


async def change_lot_time(call: types.CallbackQuery):
    await FSMClient.change_lot_time.set()
    kb = deepcopy(lot_time_kb).add(back_to_ready_btn)
    await call.message.edit_text(text=_('🕙 Скільки буде тривати аукціон?'), reply_markup=kb)


async def change_price_steps(call: types.CallbackQuery):
    await FSMClient.change_price_steps.set()
    await call.message.edit_text(text=_('Напишіть крок ставки через пробіл (від 1 до 3 кроків):\n'
                                        'Наприклад: 500 1000 1500'), reply_markup=back_to_ready_kb)


async def change_city(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await FSMClient.change_city.set()
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
    kb = InlineKeyboardMarkup().add(decline_btn, accept_btn)
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


async def anti_sniper(call: types.CallbackQuery):
    user = await get_user(call.from_user.id)
    await FSMClient.sniper_time.set()
    await call.message.edit_text(text=_('⏱ Ваш поточний час антиснайпингу - {minute}хв.\n'
                                        'Якщо хочете змінити - оберіть варіант нижче:').format(
        minute=user.anti_sniper.minute), reply_markup=anti_kb)


async def new_sniper_time(call: types.CallbackQuery, state: FSMContext):
    new_time = datetime.time(hour=0, minute=int(call.data), second=0)
    await update_user_sql(telegram_id=call.from_user.id, anti_sniper=new_time)
    await call.message.edit_text(text=_('✅ Час антиснайпингу змінено на {minute}хв').format(minute=new_time.minute),
                                 reply_markup=main_kb)
    await state.reset_state(with_data=False)


async def help_(call: types.CallbackQuery):
    await call.message.edit_text(text=_("По всім запитанням @Oleksandr_Polis\n\n"
                                        "<i>Що таке <a href='https://telegra.ph/Antisnajper-03-31'>"
                                        "<b>⏱ Антиснайпер?</b></a></i>\n"),
                                 reply_markup=InlineKeyboardMarkup().add(back_to_main_btn), parse_mode='html',
                                 disable_web_page_preview=True)


async def get_contact(call: types.CallbackQuery):
    bidder_id = call.data.split('_')[-2]
    lot_id = call.data.split('_')[-1]
    lot = await get_lot(lot_id)
    token = lot.paypal_token
    winner_tg = await bot.get_chat(bidder_id)
    owner: User = await get_user(call.from_user.id)

    await call.answer()
    if await payment_approved(token):
        await call.message.answer(text=_("<b>📦 Лот {desc}...</b>\n"
                                         "✅Оплата пройшла успішно!\n"
                                         "Можете зв'язатись з переможцем https://t.me/{username}.")
                                  .format(desc=lot.description[:15], username=winner_tg.username),
                                  reply_markup=main_kb)
        await delete_lot_sql(lot_id=lot.id)

    else:
        kb = await contact_payment_kb_generate(bidder_id, token, lot_id, owner_locale=owner.language)
        await call.message.answer(text=_('<b>📦 Лот {desc}...</b>\n'
                                         '❌ Оплату не зафіксовано.\n'
                                         "Щоб зв'язатись з переможцем, оплатіть комісію і натисніть <b>Отримати контакт</b>.").format(
            desc=lot.description[:25]),
            reply_markup=kb, parse_mode='html')


async def ask_description_ad(call: types.CallbackQuery):
    await call.message.edit_text(text=_('Перевірка підписки...'))
    is_subscribed = await adv_sub_time_remain(call.from_user.id)
    redis_obj = job_stores.get('default')
    result = redis_obj.redis.get('payment')
    if is_subscribed or (result and result.decode('utf-8') == 'on'):
        await call.message.edit_text(text=_('📝 Напишіть опис для оголошення:'), reply_markup=cancel_kb)
        await FSMClient.description_ad.set()
    elif await user_have_approved_adv_token(call.from_user.id):
        await update_user_sql(call.from_user.id, advert_subscribe_time=604800 + time.time())
        await call.message.edit_text(text=_('📝 Напишіть опис для оголошення:'), reply_markup=cancel_kb)
        await FSMClient.description_ad.set()
    else:
        await call.message.edit_text(text=_('ℹ️ Щоб виставити оголошення, потрібно оформити підписку.'),
                                     reply_markup=subscribe_adv_kb)
        await FSMClient.adv_sub_seconds.set()


async def ask_city_ad(message: types.Message, state: FSMContext):
    if isinstance(message, types.Message):
        await state.update_data(description=message.text)
        await FSMClient.city_ad.set()
        await message.answer(text=_('🌆 Вкажіть ваше місто:'),
                             parse_mode='html',
                             reply_markup=cancel_kb)


async def ask_media_ad(message: types.Message, state: FSMContext):
    text = _('📸 Надішліть фото і відео:\n'
             '<i>До 5 фото та до 1 відео</i>')
    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text=text, reply_markup=cancel_kb, parse_mode='html')
    else:
        await state.update_data(city=message.text)
        await message.answer(text=text, reply_markup=cancel_kb, parse_mode='html')

    await FSMClient.media_ad.set()


@media_group_handler(storage_driver=storage_group)
async def save_media_ad(messages: List[types.Message], state: FSMContext):
    await state.update_data(is_ad=True)
    photos_id, videos_id = [], []
    html = await save_sent_media(messages, photos_id, videos_id, state)
    if html and len(photos_id) > 1:
        await create_telegraph_link(state, html)

    if len(photos_id) > 5 or len(videos_id) > 1:
        await messages[0].answer(text=_('❌ Максимум 5 фото і 1 відео.\n'
                                        'Надішліть ще раз ваші медіафайли:'), reply_markup=cancel_kb)
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
        await FSMClient.repost_count_answer.set()


async def republish_adv(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    answer = call.data
    if answer == 'yes':
        await call.message.edit_text(text=_("Оберіть кількість повторних публікацій на день:"),
                                     reply_markup=repost_count_kb)
        await FSMClient.repost_count.set()
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
    kb.add(cancel_btn, publish_adv_btn)
    text = _('⬆️ Оголошення готове до публікації!\n'
             'Перевірте всю інформацію і натисніть <b>✅ Опублікувати</b>, коли будете готові.')
    await send_post_fsm(fsm_data, call.from_user.id, is_ad=True)
    await bot.send_message(chat_id=call.from_user.id, text=text, reply_markup=kb, parse_mode='html',
                           reply_to_message_id=last_message_id)
    await state.reset_state(with_data=False)


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
    await FSMClient.new_desc_exist.set()
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
                kb.add(InlineKeyboardButton(text='⏳', callback_data=f'time_left_lot_{obj_id}'))
                kb.add(InlineKeyboardButton(text=_('💬 Задати питання автору', locale=user.language),
                                            url=await get_start_link(f'question_{user.telegram_id}_{obj_id}',
                                                                     encode=True)))
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
                except MessageNotModified:
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
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton(text='⏳', callback_data=f'time_left_adv_{obj_id}'))
                kb.add(InlineKeyboardButton(text=_('💬 Задати питання автору', locale=user.language),
                                            url=f'https://t.me/{user_tg.username}'))
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
                except MessageNotModified:
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


def register_client_handlers(dp: Dispatcher):
    dp.middleware.setup(HiddenUser())
    dp.middleware.setup(i18n)
    dp.register_message_handler(start, commands=['start'], state='*')
    dp.register_callback_query_handler(start, Text(equals='start'), state='*')
    dp.register_callback_query_handler(main_menu, Text(equals='main_menu'), state='*')
    dp.register_message_handler(main_menu, commands=['main_menu'], state='*')
    dp.register_callback_query_handler(get_contact, Text(startswith='get_winner'), state='*')
    dp.register_callback_query_handler(main_menu, state=FSMClient.language)
    dp.register_callback_query_handler(my_auctions, Text(equals='my_auctions'), state='*')
    dp.register_callback_query_handler(my_ads, Text(equals='my_ads'), state='*')
    dp.register_callback_query_handler(my_chats, Text(equals='chats'), state='*')
    dp.register_callback_query_handler(question_list, Text(equals='questions'), state='*')
    dp.register_callback_query_handler(answer_question, state=FSMClient.choose_question)
    dp.register_callback_query_handler(choose_answer, state=FSMClient.choose_answer)
    dp.register_callback_query_handler(del_read_answer, state=FSMClient.delete_answer)
    dp.register_callback_query_handler(answers_list, Text(equals='answers'), state='*')
    dp.register_callback_query_handler(ask_city, Text(equals='create_auction'), state='*')

    dp.register_callback_query_handler(ask_description_ad, Text(equals='create_ad'), state='*')
    dp.register_message_handler(ask_city_ad, state=FSMClient.description_ad)
    dp.register_message_handler(ask_media_ad, state=FSMClient.city_ad)
    dp.register_message_handler(save_media_ad, state=FSMClient.media_ad, content_types=types.ContentType.all())

    dp.register_message_handler(ask_currency, state=FSMClient.city)
    dp.register_callback_query_handler(ask_description, state=FSMClient.currency)
    dp.register_message_handler(ask_price, state=FSMClient.description)
    dp.register_message_handler(ask_price_steps, state=FSMClient.price)
    dp.register_message_handler(ask_lot_living, state=FSMClient.price_steps)
    dp.register_callback_query_handler(ask_media, state=FSMClient.lot_time_living)
    dp.register_message_handler(ready_lot, state=FSMClient.media, content_types=types.ContentType.all())

    dp.register_callback_query_handler(ready_lot, Text(equals='back_to_ready'), state='*')
    dp.register_callback_query_handler(save_media_ad, Text(equals='back_to_ready_ad'), state='*')
    dp.register_callback_query_handler(lot_publish, Text(equals='publish_lot'))
    dp.register_callback_query_handler(adv_publish, Text(equals='publish_adv'))

    dp.register_callback_query_handler(make_bid, Text(startswith='bid'))
    dp.register_callback_query_handler(show_lot, state=FSMClient.change_lot)
    dp.register_callback_query_handler(show_lot, Text(equals='show_lot'), state='*')
    dp.register_callback_query_handler(show_ad, state=FSMClient.change_ad)
    dp.register_callback_query_handler(show_ad, Text(equals='show_ad'), state='*')

    dp.register_callback_query_handler(change_media, Text(equals='change_media'))
    dp.register_callback_query_handler(change_desc, Text(equals='change_desc'))
    dp.register_callback_query_handler(change_start_price, Text(equals='change_start_price'))
    dp.register_callback_query_handler(change_lot_time, Text(equals='change_lot_time'))
    dp.register_callback_query_handler(change_price_steps, Text(equals='change_price_steps'))
    dp.register_callback_query_handler(change_city, Text(equals='change_city'))

    dp.register_message_handler(ready_lot, state=FSMClient.change_media, content_types=types.ContentType.all())
    dp.register_message_handler(save_media_ad, state=FSMClient.change_media_ad, content_types=types.ContentType.all())
    dp.register_message_handler(set_desc, state=FSMClient.change_desc)
    dp.register_message_handler(set_start_price, state=FSMClient.change_start_price)
    dp.register_callback_query_handler(set_lot_time, state=FSMClient.change_lot_time)
    dp.register_message_handler(set_price_steps, state=FSMClient.change_price_steps)
    dp.register_message_handler(set_new_city, state=FSMClient.change_city)

    dp.register_callback_query_handler(delete_ad, Text(equals='delete_ad'))
    dp.register_callback_query_handler(delete_lot, Text(equals='delete_lot'))
    dp.register_callback_query_handler(time_left_popup, Text(startswith='time_left'))

    dp.register_callback_query_handler(lot_deletion, Text(startswith='lot_deletion_'), state='*')
    dp.register_callback_query_handler(accept_lot, Text(startswith='accept_lot'), state='*')
    dp.register_callback_query_handler(decline_lot, Text(startswith='decline_lot'), state='*')

    dp.register_callback_query_handler(accept_adv, Text(startswith='accept_adv'), state='*')
    dp.register_callback_query_handler(decline_adv, Text(startswith='decline_adv'), state='*')

    dp.register_callback_query_handler(help_, Text(equals='help'))

    dp.register_callback_query_handler(anti_sniper, Text(equals='anti_sniper'))
    dp.register_callback_query_handler(new_sniper_time, state=FSMClient.sniper_time)

    dp.register_message_handler(lot_question, state=FSMClient.question)
    dp.register_message_handler(send_answer, state=FSMClient.send_answer)

    dp.register_callback_query_handler(delete_question, Text(equals='delete_question'), state='*')
    dp.register_callback_query_handler(update_adv_payment_status, Text(startswith='update_'), state='*')
    dp.register_callback_query_handler(create_adv_sub, state=FSMClient.adv_sub_seconds)

    dp.register_callback_query_handler(change_desc_exist, Text(startswith='change_desc_exist'))
    dp.register_callback_query_handler(edit_new_text, Text(startswith='edit_new_text'), state='*')
    dp.register_message_handler(request_new_desc, state=FSMClient.new_desc_exist)
    dp.register_callback_query_handler(republish_adv, state=FSMClient.repost_count_answer)
    dp.register_callback_query_handler(save_repost_count, state=FSMClient.repost_count)
