import datetime
import logging
import re
import time
from typing import List, Literal

import aiofiles
import aiohttp
from aiogram import types
from aiogram.enums import ContentType
from aiogram.filters import BaseFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, PhotoSize
from aiogram.utils.deep_linking import create_start_link
from telegraph import Telegraph

from create_bot import bot, scheduler, job_stores
from database.db_manage import get_lot, get_user, delete_lot_sql, update_lot_sql, Question, messages_count, \
    Answer, get_adv, delete_adv_sql, update_adv_sql, get_chat_record
from keyboards.kb import decline_lot_btn, accept_lot_btn, main_kb, back_to_main_btn
from utils.config import ADVERT_CHANNEL
from utils.paypal import create_payment_token, get_status, capture
from create_bot import _


class IsPrivateChatFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return message.chat.type == "private"


class IsMessageType(BaseFilter):
    def __init__(self, message_type: List[(Literal[ContentType.PHOTO, ContentType.TEXT, ContentType.VIDEO])]):
        self.message_type = message_type

    async def __call__(self, message: types.Message) -> bool:
        if isinstance(message, types.Message):
            print(self.message_type)
            if message.content_type in self.message_type:
                return True
            elif self.message_type[0] == ContentType.TEXT:
                await message.answer(text=_('Потрібно надіслати текст:'))
            elif self.message_type[0] in (ContentType.VIDEO, ContentType.PHOTO):
                await message.answer(text=_('Потрібно надіслати медіа:'))
            return False
        else:
            return True


async def lot_ending(job_id, msg_id: types.Message):
    lot = await get_lot(job_id)
    scheduler.remove_job(f'lot_{job_id}')
    if lot:
        owner_telegram_id = lot.owner_telegram_id
        owner_tg = await bot.get_chat(owner_telegram_id)
        owner = await get_user(owner_telegram_id)
        bidder_telegram_id = lot.bidder_telegram_id
        if bidder_telegram_id:
            bidder = await get_user(bidder_telegram_id)
            winner_tg = await bot.get_chat(bidder_telegram_id)
            await bot.send_message(chat_id=bidder_telegram_id,
                                   text=_('🏆 Вітаю! Ви перемогли у аукціоні <b>{desc}</b>\n'
                                          'Очікуйте повідомлення від продавця.', locale=bidder.language).format(
                                       desc=lot.description[:25]),
                                   parse_mode='html', reply_markup=main_kb)
            token = await create_payment_token(usd=5)
            await update_lot_sql(paypal_token=token, lot_id=job_id)
            kb = await contact_payment_kb_generate(bidder_telegram_id, token, job_id, owner_locale=owner.language)
            redis_instance = job_stores.get('default')
            payment_enabled = redis_instance.redis.get(name='payment')
            if payment_enabled and payment_enabled.decode('utf-8') == 'on':
                text = _("🏆 Аукціон <b>{desc}</b> завершено!\n"
                         "Щоб зв'язатись з переможцем, оплатіть комісію.",
                         locale=owner.language).format(desc=lot.description[:25])
                await bot.send_message(owner_telegram_id, text=text, reply_markup=kb, parse_mode='html')

            else:
                from utils.config import AUCTION_CHANNEL
                text = _("🏆 Аукціон <b>{desc}</b> завершено!\n"
                         "Можете зв'язатись з переможцем https://t.me/{username}.").format(username=winner_tg.username,
                                                                                           desc=lot.description[:25])
                await delete_lot_sql(lot_id=lot.id)
                await bot.delete_message(chat_id=AUCTION_CHANNEL, message_id=lot.message_id)
                await bot.send_message(owner_telegram_id, text=text, parse_mode='html')
                text = _(
                    "Вітаю, <b>{first_name}!</b><a href='https://telegra.ph/file/5f63d10b734d545a032cc.jpg'>⠀</a>\n").format(
                    first_name=owner_tg.username)
                await bot.send_message(owner_telegram_id, text=text, parse_mode='html', reply_markup=main_kb)

        else:
            await bot.send_message(chat_id=owner_telegram_id,
                                   text=_('Ваш лот <b>{desc}...</b> завершився без ставок.',
                                          locale=owner.language).format(
                                       desc=lot.description[:25]),
                                   parse_mode='html',
                                   reply_markup=main_kb)
            await delete_lot_sql(job_id)

        """close auction"""
        from utils.config import AUCTION_CHANNEL
        try:
            await bot.delete_message(chat_id=AUCTION_CHANNEL, message_id=msg_id)
        except Exception as er:
            print(er)
    else:
        scheduler.remove_job(f'lot_{job_id}')


async def adv_ending(job_id):
    adv = await get_adv(job_id)
    scheduler.remove_job(f'adv_{job_id}')
    if adv:
        owner_telegram_id = adv.owner_telegram_id
        owner = await get_user(owner_telegram_id)
        await delete_adv_sql(job_id)
        await bot.send_message(chat_id=owner_telegram_id,
                               text=_('⚠️ У вашого оголошення <b>{desc}...</b> завершився термін і його було видалено.',
                                      locale=owner.language).format(
                                   desc=adv.description[:25]),
                               parse_mode='html',
                               reply_markup=main_kb)
        try:
            from utils.config import ADVERT_CHANNEL
            await bot.delete_message(chat_id=ADVERT_CHANNEL, message_id=adv.message_id)
        except Exception as er:
            print(er)
    else:
        scheduler.remove_job(f'adv_{job_id}')


async def create_price_step_kb(price_steps, new_lot_id, currency):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for price in price_steps.split(' ')[:3]:
        btn = InlineKeyboardButton(text=f'+{price} {currency}', callback_data=f'bid_{price}_{new_lot_id}')
        kb.inline_keyboard.extend([[btn]])
    return kb


async def create_user_lots_kb(lots):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for lot in lots:
        lot = lot[0]
        kb.inline_keyboard.append([InlineKeyboardButton(text=f'{lot.description[:25]}...', callback_data=f'{lot.id}')])
    return kb


async def send_post(user_id, send_to_id, photo_id, video_id, description, start_price, price_steps, currency, city,
                    photos_link=None,
                    lot_id=None,
                    moder_review=None, under_moderation=None, change_text=None, new_desc=None):
    user = await get_user(user_id=user_id)
    anti_sniper: datetime.time = user.anti_sniper
    kb = await create_price_step_kb(price_steps, lot_id, currency)
    caption = ''
    user_tg = await bot.get_chat(user.telegram_id)
    if lot_id and moder_review:
        caption = _('<i>https://t.me/{username} - надіслав лот на модерацію.\n</i>').format(username=user_tg.username)
        decline_lot_btn.callback_data = f'decline_lot_{lot_id}'
        accept_lot_btn.callback_data = f'accept_lot_{lot_id}'
        kb.inline_keyboard.extend([[decline_lot_btn, accept_lot_btn]])
    elif not moder_review and not change_text:
        kb.inline_keyboard.extend([[InlineKeyboardButton(text='⏳', callback_data=f'time_left_lot_{lot_id}')]])
        kb.inline_keyboard.extend([[InlineKeyboardButton(text=_('💬 Задати питання автору'),
                                                         url=await create_start_link(bot=bot,
                                                                                     payload=f'question_{user_id}_{lot_id}',
                                                                                     encode=True))]])
        if under_moderation:
            caption = _('<i>⚠️ Ваш лот проходить модерацію...\n</i>')
    elif change_text and lot_id:
        caption = _(
            '<i>https://t.me/{username} - хоче змінити опис у лоті з \"{description}\" на \"{new_desc}\".\n</i>').format(
            username=user_tg.username, description=description, new_desc=new_desc)
        decline_lot_btn.callback_data = f'edit_new_text:{lot_id}:decline:lot'
        accept_lot_btn.callback_data = f'edit_new_text:{lot_id}:accept:lot'
        kb.inline_keyboard.extend([[decline_lot_btn, accept_lot_btn]])
    caption += _("<b>{description}</b>\n\n"
                 "🏙 <b>Місто:</b> {city}\n\n"
                 "👇 <b>Ставки учасників:</b>\n\n"
                 "💰 <b>Стартова ціна:</b> {start_price} {currency}\n"
                 "⏱ <b>Антиснайпер</b> {anti_sniper} хв.\n").format(description=description, city=city,
                                                                    start_price=start_price, currency=currency,
                                                                    anti_sniper=anti_sniper.minute)
    if photos_link:
        caption += _("\n<a href='{photos_link}'><b>👉 Оглянути додаткові фото</b></a>").format(photos_link=photos_link)
    msg = None
    try:
        if video_id:
            msg = await bot.send_video(chat_id=send_to_id, video=video_id, caption=caption, parse_mode='html',
                                       reply_markup=kb)
        elif photo_id:
            msg = await bot.send_photo(chat_id=send_to_id, photo=photo_id, caption=caption, parse_mode='html',
                                       reply_markup=kb)

    except Exception as err:
        logging.info(err)
        msg = await bot.send_message(chat_id=send_to_id, text=caption, parse_mode='html', reply_markup=kb)
    if msg:
        return msg


async def send_advert(user_id, send_to_id, description, city, photos_link, video_id, photo_id,
                      moder_review=None,
                      advert_id=None, under_moderation=None, change_text=None, new_desc=None):
    user = await get_user(user_id=user_id)
    caption = ''
    user_tg = await bot.get_chat(user.telegram_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if advert_id and moder_review:
        caption = _('<i>https://t.me/{username} - надіслав оголошення на модерацію.\n</i>').format(
            username=user_tg.username)
        decline_lot_btn.callback_data = f'decline_advert_{advert_id}'
        accept_lot_btn.callback_data = f'accept_advert_{advert_id}'
        kb.inline_keyboard.extend([[decline_lot_btn, accept_lot_btn]])
    elif not moder_review and not change_text:
        kb.inline_keyboard.extend([[InlineKeyboardButton(text='⏳', callback_data=f'time_left_adv_{advert_id}')]])
        kb.inline_keyboard.extend([[InlineKeyboardButton(text=_('💬 Задати питання автору'),
                                    url=f'https://t.me/{user_tg.username}')]])
        if under_moderation:
            caption = _('<i>⚠️ Ваш лот проходить модерацію...\n</i>')
    elif change_text and advert_id:
        caption = _(
            "<i>https://t.me/{username} - хоче змінити опис у оголошенні з \"{description}\" на \"{new_desc}\".\n</i>").format(
            username=user_tg.username, description=description, new_desc=new_desc)
        decline_lot_btn.callback_data = f'edit_new_text:{advert_id}:decline:ad'
        accept_lot_btn.callback_data = f'edit_new_text:{advert_id}:accept:ad'
        kb.inline_keyboard.extend([[decline_lot_btn, accept_lot_btn]])

    caption += _("<b>{description}</b>\n\n"
                 "🏙 <b>Місто:</b> {city}\n").format(description=description, city=city)
    if photos_link:
        caption += _("\n<a href='{photos_link}'><b>👉 Оглянути додаткові фото</b></a>").format(photos_link=photos_link)
    msg = None
    if video_id:
        msg = await bot.send_video(chat_id=send_to_id, video=video_id, caption=caption, parse_mode='html',
                                   reply_markup=kb)
    elif photo_id:
        msg = await bot.send_photo(chat_id=send_to_id, photo=photo_id, caption=caption, parse_mode='html',
                                   reply_markup=kb)
    if msg:
        return msg


async def send_post_fsm(fsm_data, user_id, is_ad=None):
    photos_link = fsm_data.get('photos_link')
    photo_id = fsm_data.get('photo_id')
    video_id = fsm_data.get('video_id')
    description = fsm_data.get('description')
    start_price = fsm_data.get('price')
    price_steps: str = fsm_data.get('price_steps')
    currency = fsm_data.get('currency')
    city = fsm_data.get('city')
    if is_ad:
        return await send_advert(user_id, user_id, description, city, photos_link, video_id, photo_id)
    else:
        return await send_post(user_id, user_id, photo_id, video_id, description, start_price, price_steps,
                               currency=currency, photos_link=photos_link, city=city)


async def contact_payment_kb_generate(bidder_telegram_id, token, lot_id, owner_locale):
    payment_url = await payment_link_generate(token)
    pay_btn = InlineKeyboardButton(text='5.00 USD', url=str(payment_url))
    get_contact_btn = InlineKeyboardButton(text=_('Отримати контакт', locale=owner_locale),
                                           callback_data=f'get_winner_{bidder_telegram_id}_{lot_id}')
    kb = InlineKeyboardMarkup(inline_keyboard=[[pay_btn], [get_contact_btn]])
    return kb


async def payment_approved(paypal_token):
    await capture(order_id=paypal_token)
    status = await get_status(paypal_token)
    return True if status == 'COMPLETED' else False


async def payment_link_generate(token):
    return f'https://www.paypal.com/checkoutnow?token={token}'


async def new_bid_caption(caption, first_name, price, currency, owner_locale, bid_count, photos_link):
    old_text = caption.split('\n💰')
    old_text[-1] = old_text[-1].replace('👉 Оглянути додаткові фото',
                                        f"<a href='{photos_link}'><b>👉 Оглянути додаткові фото</b></a>")
    first_part_caption = _("{old_text}    {bid_count} - {first_name} ставить {price}{currency}\n",
                           locale=owner_locale).format(
        old_text=old_text[0], first_name=first_name, price=price, currency=currency, bid_count=bid_count)
    caption = _("{first_part_caption}\n💰 {old_text}").format(first_part_caption=first_part_caption,
                                                             old_text=old_text[1].lstrip())
    return caption


async def translate_kb(kb: InlineKeyboardMarkup, locale, owner_id, no_spaces=False):
    if kb:
        for row in kb.inline_keyboard:
            for button in row:
                if any(word in button.text.split() for word in ('Повідомлення', 'Messages')):
                    button.text = _(button.text.split('(')[0].rstrip(), locale=locale)
                else:
                    button.text = _(button.text, locale=locale)
                if any(text in button.text for text in
                       ('💬 Повідомлення', '💬 Messages', '❔ Запитання', "❔ Questions", '💬 Answers', "💬 Відповіді")):
                    if any(text in button.text for text in ('Повідомлення', 'Messages')):
                        questions_count = await messages_count(owner_id, 'question')
                        answers_count = await messages_count(owner_id, 'answer')
                        mes_count = questions_count + answers_count
                    elif any(text in button.text for text in ('Запитання', "Questions")):
                        mes_count = await messages_count(owner_id, 'question')
                    elif any(text in button.text for text in ('Answers', "Відповіді")):
                        mes_count = await messages_count(owner_id, 'answer')
                    split_text = button.text.split(' ')
                    if len(split_text) == 3:
                        split_text[-1] = '({mes_count})'.format(mes_count=mes_count)
                    else:
                        split_text.append('({mes_count})'.format(mes_count=mes_count))
                    button.text = ' '.join(split_text)
        return kb


async def create_photo_album(html, tg):
    response = tg.create_page(
        f'Photos',
        html_content=html)
    return 'http://telegra.ph/{}'.format(response['path'])


async def create_question_kb(questions: List[Question], owner_id):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for q in questions:
        lot = await get_lot(q.lot_id)
        kb.inline_keyboard.extend(
            [[InlineKeyboardButton(text=f'{lot.description[:20]} - {q.question}', callback_data=q.id)]])
    return kb


async def create_answers_kb(answers: List[Answer], recipient_id):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for a in answers:
        lot = await get_lot(a.lot_id)
        kb.inline_keyboard.extend(
            [[InlineKeyboardButton(text=f'{lot.description[:20]} - {a.answer}', callback_data=a.id)]])
    return kb


async def phone_in_text(text):
    text = re.sub(r'[^\w]', ' ', text)
    text = text.replace(' ', '')
    if any(word in text for word in (
            'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'zero', 'один', "два", "три",
            "чотири", "пять", "шість", "сім", "вісім", "девять", "ноль", "нуль")):
        return True
    validate_phone_number_pattern = "^\\+?\\d{1,4}?[-.\\s]?\\(?\\d{1,3}?\\)?[-.\\s]?\\d{1,4}[-.\\s]?\\d{1,4}[-.\\s]?\\d{1,9}$"
    for word in text.split(' '):
        if re.match(validate_phone_number_pattern, word):
            return True
    return False


async def levenshtein_distance(word1, word2):
    dp = [[0] * (len(word2) + 1) for _ in range(len(word1) + 1)]
    for i in range(len(word1) + 1):
        dp[i][0] = i
    for j in range(len(word2) + 1):
        dp[0][j] = j
    for i in range(1, len(word1) + 1):
        for j in range(1, len(word2) + 1):
            cost = 0 if word1[i - 1] == word2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[len(word1)][len(word2)]


async def similarity(word1, word2):
    max_len = max(len(word1), len(word2))
    if max_len == 0:
        return 0
    return (1 - await levenshtein_distance(word1, word2) / max_len) * 100


async def username_in_text(text, username):
    text = re.sub(r'[^\w]', ' ', text)
    merged_text = text.replace(' ', '')
    if username[:5] in merged_text:
        return True
    elif 'http' in merged_text:
        return True
    for word in text.split(' '):
        similarity_percent = await similarity(word, username)
        if similarity_percent > 60:
            return True
    return False


async def create_telegraph_link(state, html):
    telegraph = Telegraph()
    telegraph.create_account(short_name='Shopogolic')
    photos_link = await create_photo_album(tg=telegraph, html=html)
    await state.update_data(photos_link=photos_link)


async def photo_video_count_in_messages(messages: List[types.Message], state) -> tuple[bool, bool] | tuple[
    list[str], list[str]]:
    videos_id, photos_id = [], []
    for message in messages:
        if message.content_type == 'photo':
            photos_id.append(message.photo[-1].file_id)
            await state.update_data(photo_id=message.photo[-1].file_id)
        elif message.content_type == 'video':
            videos_id.append(message.video.file_id)
            await state.update_data(video_id=message.video.file_id)
        else:
            return False, False
    return videos_id, photos_id


async def save_sent_media(messages, photos_id, videos_id, state):
    html = ''
    if isinstance(messages[0], types.Message) and 'media' in await state.get_state():
        async with aiohttp.ClientSession() as session:
            if photos_id:
                for photo_id in photos_id:
                    file = await bot.get_file(photo_id)
                    file_path = file.file_path
                    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"
                    async with session.get(file_url) as response:
                        if response.status != 200:
                            continue
                        temp_filename = f"/tmp/{photo_id}.jpg"
                        async with aiofiles.open(temp_filename, 'wb') as f:
                            await f.write(await response.read())

                    async with aiofiles.open(temp_filename, 'rb') as f:
                        form = aiohttp.FormData()
                        form.add_field('file', f, filename='file', content_type='image/jpeg')
                        async with session.post('https://telegra.ph/upload', data=form) as response:
                            if response.status == 200:
                                telegraph_url = await response.json()
                                if telegraph_url and 'src' in telegraph_url[0]:
                                    full_url = f"https://telegra.ph{telegraph_url[0]['src']}"
                                    print(full_url)
                                    html += f"<img src='{full_url}'/><br>"

                    await state.update_data(photo_id=photo_id)

            if videos_id:
                await state.update_data(video_id=videos_id[0])
            # else:
            #     await messages[0].answer(text=_('❌ Надішліть фото або відео.'), parse_mode='html')
            #     return False
    return html


async def adv_sub_time_remain(user_id):
    user = await get_user(user_id)
    adv_sub_time: int = user.advert_subscribe_time
    time_remain = adv_sub_time - time.time()
    if time_remain > 0:
        return True
    else:
        return False


async def bot_sub_time_remain(chat_id):
    chat = await get_chat_record(chat_id)
    adv_sub_time: int = chat.subscription_time
    print(adv_sub_time)
    print(time.time())
    time_remain = adv_sub_time - time.time()
    print(time_remain)
    if time_remain > 0:
        return True
    else:
        return False


async def user_have_approved_adv_token(user_id) -> bool:
    user = await get_user(user_id)
    token = user.user_adv_token
    if token:
        return await payment_approved(token)
    else:
        return False


async def chat_have_approved_token(chat_id) -> bool:
    chat = await get_chat_record(chat_id)
    token = chat.paypal_token
    if token:
        return await payment_approved(token)
    else:
        return False


async def payment_kb(token, activate_btn_text, callback_data, back_btn: InlineKeyboardButton = back_to_main_btn):
    update_status_btn = InlineKeyboardButton(text=_('🔄 Оновити статус'), callback_data=callback_data)
    payment_url = await payment_link_generate(token)
    pay_btn = InlineKeyboardButton(text=activate_btn_text, url=payment_url)
    pay_kb = InlineKeyboardMarkup(inline_keyboard=[[pay_btn], [update_status_btn], [back_btn]])
    return pay_kb


async def repost_adv(job_id, username):
    logging.info(f'start repost adv job_id={job_id}')
    adv = await get_adv(job_id)
    if adv:
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        kb.inline_keyboard.extend([[InlineKeyboardButton(text='⏳', callback_data=f'time_left_adv_{job_id}')]])
        kb.inline_keyboard.extend([[InlineKeyboardButton(text=_('💬 Задати питання автору'),
                                    url=f'https://t.me/{username}')]])
        new_message = await bot.copy_message(chat_id=ADVERT_CHANNEL, from_chat_id=ADVERT_CHANNEL,
                                             message_id=adv.message_id, reply_markup=kb)
        await bot.delete_message(chat_id=ADVERT_CHANNEL, message_id=adv.message_id)
        chat = await bot.get_chat(chat_id=ADVERT_CHANNEL)
        post_link = f'https://t.me/{chat.username}/{new_message.message_id}'
        await update_adv_sql(job_id, message_id=new_message.message_id, post_link=post_link)
    else:
        logging.info(f'adv where id={job_id} doesnt exist')


async def restrict_media_count(photos_id, videos_id, messages, reset_to_auction_menu_kb):
    if len(photos_id) > 5 or len(videos_id) > 1:
        await bot.send_message(chat_id=messages[0].from_user.id, text=_('❌ Максимум 5 фото і 1 відео.\n'
                                                                        'Надішліть ще раз ваші медіафайли:'),
                               reply_markup=reset_to_auction_menu_kb)
        return
    elif not photos_id and not videos_id:
        await messages[0].answer(text=_('❌ Надішліть фото або відео.'), parse_mode='html')
        return
