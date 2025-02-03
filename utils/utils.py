import datetime
import logging
import time
from typing import List, Literal, Tuple, Union
from aiogram import types
from aiogram.enums import ContentType
from aiogram.filters import BaseFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.media_group import MediaGroupBuilder

import database.models.advertisement
import database.models.lot
from database.models.group_subscription_plan import GroupSubscriptionPlan
from database.services.advertisement_service import AdvertisementService
from database.services.base import delete_record_by_id
from database.services.group_channel_service import GroupChannelService
from database.services.group_subscription_plan_service import GroupSubscriptionPlanService
from database.services.lot_service import LotService
from database.services.user_service import UserService
from utils.create_bot import bot, scheduler, job_stores
from keyboards.client_kb import decline_lot_btn, accept_lot_btn, back_to_main_btn, main_kb
from utils.config import GALLERY_CHANNEL
from utils.paypal import create_order, get_order_status, capture
from utils.create_bot import _

checkout_url = 'https://www.sandbox.paypal.com/checkoutnow?token={token}'


# checkout_url = 'https://api-m.paypal.com/checkoutnow?token={token}'


class IsPrivateChatFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return message.chat.type == "private"


class IsMessageType(BaseFilter):
    def __init__(self, message_type: List[(Literal[ContentType.PHOTO, ContentType.TEXT, ContentType.VIDEO])]):
        self.message_type = message_type

    async def __call__(self, message: types.Message) -> bool:
        if isinstance(message, types.Message):
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
    lot = await LotService.get_lot(job_id)

    scheduler.remove_job(f'lot_{job_id}')
    if lot:
        owner_telegram_id = lot.owner_telegram_id
        owner_tg = await bot.get_chat(owner_telegram_id)
        owner = await UserService.get_user(owner_telegram_id)
        bidder_telegram_id = lot.bidder_telegram_id
        if bidder_telegram_id:
            bidder = await UserService.get_user(bidder_telegram_id)
            winner_tg = await bot.get_chat(bidder_telegram_id)
            await bot.send_message(chat_id=bidder_telegram_id,
                                   text=_('🏆 Вітаю! Ви перемогли у аукціоні <b>{desc}</b>\n'
                                          'Очікуйте повідомлення від продавця.', locale=bidder.language).format(
                                       desc=lot.description[:25]),
                                   reply_markup=main_kb)
            token = await create_order(usd=5)
            await LotService.update_lot_sql(paypal_token=token, lot_id=job_id)
            kb = await contact_payment_kb_generate(bidder_telegram_id, token, job_id, owner_locale=owner.language)
            redis_instance = job_stores.get('default')
            payment_enabled = redis_instance.redis.get(name='payment')
            if payment_enabled and payment_enabled.decode('utf-8') == 'on':
                text = _("🏆 Аукціон <b>{desc}</b> завершено!\n"
                         "Щоб зв'язатись з переможцем, оплатіть комісію.",
                         locale=owner.language).format(desc=lot.description[:25])
                await bot.send_message(owner_telegram_id, text=text, reply_markup=kb, )

            else:
                text = _("🏆 Аукціон <b>{desc}</b> завершено!\n"
                         "Можете зв'язатись з переможцем https://t.me/{username}.").format(username=winner_tg.username,
                                                                                           desc=lot.description[:25])
                await delete_record_by_id(lot.id, database.models.lot.Lot)
                await bot.delete_message(chat_id=lot.group_fk, message_id=lot.message_id)
                await bot.send_message(owner_telegram_id, text=text, )
                text = _(
                    "Вітаю, <b>{first_name}!</b><a href='https://telegra.ph/file/5f63d10b734d545a032cc.jpg'>⠀</a>\n").format(
                    first_name=owner_tg.username)
                await bot.send_message(owner_telegram_id, text=text, reply_markup=main_kb)

        else:
            await bot.send_message(chat_id=owner_telegram_id,
                                   text=_('Ваш лот <b>{desc}...</b> завершився без ставок.',
                                          locale=owner.language).format(
                                       desc=lot.description[:25]),

                                   reply_markup=main_kb)
            await delete_record_by_id(job_id, database.models.lot.Lot)

        """close auction"""
        try:
            await bot.delete_message(chat_id=lot.group_fk, message_id=msg_id)
        except Exception as er:
            print(er)
    else:
        scheduler.remove_job(f'lot_{job_id}')


async def adv_ending(job_id):
    adv = await AdvertisementService.get_adv(job_id)
    scheduler.remove_job(f'adv_{job_id}')
    if adv:
        owner_telegram_id = adv.owner_telegram_id
        owner = await UserService.get_user(owner_telegram_id)
        await delete_record_by_id(job_id, database.models.advertisement.Advertisement)
        await bot.send_message(chat_id=owner_telegram_id,
                               text=_('⚠️ У вашого оголошення <b>{desc}...</b> завершився термін і його було видалено.',
                                      locale=owner.language).format(
                                   desc=adv.description[:25]),

                               reply_markup=main_kb)
        try:
            await bot.delete_message(chat_id=adv.group_fk, message_id=adv.message_id)
        except Exception as er:
            print(er)
    else:
        scheduler.remove_job(f'adv_{job_id}')


async def create_price_step_kb(price_steps, new_lot_id, currency):
    kb = InlineKeyboardBuilder()
    for price in price_steps:
        kb.button(text=f'+{price} {currency}', callback_data=f'bid_{price}_{new_lot_id}')
    return kb


async def create_user_lots_kb(lots):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for lot in lots:
        lot = lot[0]
        kb.inline_keyboard.append([InlineKeyboardButton(text=f'{lot.description[:25]}...', callback_data=f'{lot.id}')])
    return kb


async def create_lot_caption_and_kb(user_id, moder_review, lot_id, description, start_price, city, under_moderation,
                                    new_desc, photos_link, change_text, photos, videos, price_steps, currency):
    caption = ''
    user = await UserService.get_user(user_id=user_id)
    price_steps = price_steps.split(' ')[:3]
    anti_sniper: datetime.time = user.anti_sniper
    kb = await create_price_step_kb(price_steps, lot_id, currency)
    user_tg = await bot.get_chat(user_id)
    if photos is None:
        photos = []
    if videos is None:
        videos = []
    if lot_id and moder_review:
        caption = _('<i>https://t.me/{username} - надіслав лот на модерацію.\n</i>').format(username=user_tg.username)
        kb.button(text='❌ Відхилити', callback_data=f'decline_lot_{lot_id}')
        kb.button(text='✅ Підтвердити', callback_data=f'accept_lot_{lot_id}')
        kb.adjust(len(price_steps), 2)
    elif not moder_review and not change_text:

        kb.row(InlineKeyboardButton(text='⏳', callback_data=f'time_left_lot_{lot_id}'))
        kb.button(text=_('💬 Задати питання автору'), url=f'https://t.me/{user_tg.username}')
        if lot_id:
            lot = await LotService.get_lot(lot_id)
            invite_link = await create_start_link(bot, lot.group.chat_id)
            kb.row(InlineKeyboardButton(text='📝 Створити свою публікацію', url=invite_link))
        if under_moderation:
            caption = _('<i>⚠️ Ваш лот проходить модерацію...\n</i>')
    elif change_text and lot_id:
        caption = _(
            '<i>https://t.me/{username} - хоче змінити опис у лоті з \"{description}\" на \"{new_desc}\".\n</i>').format(
            username=user_tg.username, description=description, new_desc=new_desc)
        kb.button(text='❌ Відхилити', callback_data=f'edit_lot_text:{lot_id}:decline')
        kb.button(text='✅ Підтвердити', callback_data=f'edit_lot_text:{lot_id}:accept')
        kb.adjust(len(price_steps), 2)
    caption += _("<b>{description}</b>\n\n"
                 "🏙 <b>Місто:</b> {city}\n\n"
                 "👇 <b>Ставки учасників:</b>\n\n"
                 "💰 <b>Стартова ціна:</b> {start_price} {currency}\n"
                 "⏱ <b>Антиснайпер</b> {anti_sniper} хв.\n").format(description=description, city=city,
                                                                    start_price=start_price, currency=currency,
                                                                    anti_sniper=anti_sniper.minute)
    caption = await set_addition_media_to_caption(photos, videos, caption, photos_link, lot_id=lot_id)
    return caption, kb.as_markup()


async def send_post(user_id, send_to_id, photo_id, video_id, description, start_price, price_steps, currency, city,
                    lot_id=None, moder_review=None, under_moderation=None, change_text=None, new_desc=None, photos=None,
                    videos=None, photos_link=None):
    """
    moder_review: bool - пост для модератора
    """
    caption, kb = await create_lot_caption_and_kb(user_id=user_id, moder_review=moder_review, lot_id=lot_id,
                                                  description=description, start_price=start_price, city=city,
                                                  under_moderation=under_moderation, new_desc=new_desc,
                                                  photos_link=photos_link, change_text=change_text, photos=photos,
                                                  videos=videos, price_steps=price_steps, currency=currency)
    msg = None
    if photo_id:
        msg = await bot.send_photo(chat_id=send_to_id, photo=photo_id, caption=caption, reply_markup=kb)
    elif video_id:
        msg = await bot.send_video(chat_id=send_to_id, video=video_id, caption=caption, reply_markup=kb)

    if msg:
        return msg


async def set_addition_media_to_caption(photos, videos, caption, photos_link=None, lot_id=None):
    if len(photos) + len(videos) > 1:
        media_group = await build_media_group(photos, videos, caption=None)
        msg = await bot.send_media_group(chat_id=GALLERY_CHANNEL, media=media_group.build())
        await LotService.update_lot_sql(lot_id=lot_id, photos_link=msg[0].get_url())
        caption += _("\n<a href='{photos_link}'><b>👉 Оглянути додаткові фото</b></a>").format(
            photos_link=msg[0].get_url())
    elif photos_link:
        caption += _("\n<a href='{photos_link}'><b>👉 Оглянути додаткові фото</b></a>").format(
            photos_link=photos_link)
    return caption


async def send_advert(user_id, send_to_id, description, city, video_id, photo_id,
                      moder_review=None,
                      advert_id=None, under_moderation=None, change_text=None, new_desc=None, videos=None, photos=None,
                      photos_link=None):
    if photos is None:
        photos = []
    if videos is None:
        videos = []
    user = await UserService.get_user(user_id=user_id)
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
        decline_lot_btn.callback_data = f'edit_ad_text:{advert_id}:decline'
        accept_lot_btn.callback_data = f'edit_ad_text:{advert_id}:accept'
        kb.inline_keyboard.extend([[decline_lot_btn, accept_lot_btn]])

    caption += _("<b>{description}</b>\n\n"
                 "🏙 <b>Місто:</b> {city}\n").format(description=description, city=city)
    caption = await set_addition_media_to_caption(photos, videos, caption, photos_link)
    msg = None
    if video_id:
        msg = await bot.send_video(chat_id=send_to_id, video=video_id, caption=caption,
                                   reply_markup=kb)
    elif photo_id:
        msg = await bot.send_photo(chat_id=send_to_id, photo=photo_id, caption=caption,
                                   reply_markup=kb)
    if msg:
        return msg


async def send_post_fsm(fsm_data, user_id, is_ad=None):
    photo_id = fsm_data.get('photo_id')
    video_id = fsm_data.get('video_id')
    description = fsm_data.get('description')
    start_price = fsm_data.get('price')
    price_steps: str = fsm_data.get('price_steps')
    currency = fsm_data.get('currency')
    city = fsm_data.get('city')
    if is_ad:
        return await send_advert(user_id, user_id, description, city, video_id, photo_id,
                                 videos=fsm_data.get('videos_id'), photos=fsm_data.get('photos_id'))
    else:
        return await send_post(user_id, user_id, photo_id, video_id, description, start_price, price_steps,
                               currency=currency, city=city, videos=fsm_data.get('videos_id'),
                               photos=fsm_data.get('photos_id'))


async def contact_payment_kb_generate(bidder_telegram_id, token, lot_id, owner_locale):
    payment_url = await payment_link_generate(token)
    pay_btn = InlineKeyboardButton(text='5.00 USD', url=str(payment_url))
    get_contact_btn = InlineKeyboardButton(text=_('Отримати контакт', locale=owner_locale),
                                           callback_data=f'get_winner_{bidder_telegram_id}_{lot_id}')
    kb = InlineKeyboardMarkup(inline_keyboard=[[pay_btn], [get_contact_btn]])
    return kb


async def payment_completed(paypal_token):
    if paypal_token:
        await capture(order_id=paypal_token)
        status = await get_order_status(paypal_token)
        return True if status == 'COMPLETED' else False
    else:
        return False


async def payment_link_generate(token):
    logging.info(f'CHECKOUT URL MAY BE TESTING')
    return checkout_url.format(token=token)


async def new_bid_caption(caption, first_name, price, currency, owner_locale, bid_count):
    prev_text = caption.split('\n💰')

    bins = prev_text[0].split('\n')
    if len(bins) > 18:
        prev_text[0] = '\n'.join((bins[:5] + ['\t...'] + bins[-12:]))

    first_part_caption = _("{old_text}    {bid_count} - {first_name} ставить {price}{currency}\n",
                           locale=owner_locale).format(
        old_text=prev_text[0], first_name=first_name, price=price, currency=currency, bid_count=bid_count)

    caption = _("{first_part_caption}\n💰 {old_text}").format(first_part_caption=first_part_caption,
                                                             old_text=prev_text[1].lstrip())

    return caption


async def translate_kb(kb: InlineKeyboardMarkup, locale, owner_id, no_spaces=False):
    if kb:
        for row in kb.inline_keyboard:
            for button in row:
                button.text = _(button.text, locale=locale)
        return kb


async def gather_media_from_messages(messages: List[types.Message], state) -> Tuple[bool, bool] | Tuple[
    List[str], List[str]]:
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


async def adv_sub_time_remain(user_id):
    user = await UserService.get_user(user_id)
    adv_sub_time: int = user.advert_subscribe_time
    time_remain = adv_sub_time - time.time()
    print(time_remain)
    if time_remain > 0:
        return True
    else:
        return False


async def user_have_approved_adv_token(user_id) -> bool:
    user = await UserService.get_user(user_id)
    token = user.user_adv_token
    if token:
        return await payment_completed(token)
    else:
        return False


async def get_token_approval(chat_subscription, type_: Literal['auction', 'ads']) -> bool:
    if type_ == 'auction':
        token_approved = await payment_completed(chat_subscription.auction_token)
    else:
        token_approved = await payment_completed(chat_subscription.ads_token)
    return token_approved


async def payment_kb(token, activate_btn_text, callback_data, back_btn: InlineKeyboardButton = back_to_main_btn):
    update_status_btn = InlineKeyboardButton(text=_('🔄 Оновити статус'), callback_data=callback_data)
    payment_url = await payment_link_generate(token)
    pay_btn = InlineKeyboardButton(text=activate_btn_text, url=payment_url)
    pay_kb = InlineKeyboardMarkup(inline_keyboard=[[pay_btn], [update_status_btn], [back_btn]])
    return pay_kb


async def repost_adv(job_id, username):
    logging.info(f'start repost adv job_id={job_id}')
    ad = await AdvertisementService.get_adv(job_id)
    if not ad:
        logging.info(f"Advertisement with id={job_id} doesn't exist.")
        return

    chat = await bot.get_chat(chat_id=ad.group_fk)
    if not chat:
        logging.info(f"Chat with id={ad.group_fk} doesn't exist.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    kb.inline_keyboard.extend([[InlineKeyboardButton(text='⏳', callback_data=f'time_left_adv_{job_id}')]])
    kb.inline_keyboard.extend([[InlineKeyboardButton(text=_('💬 Задати питання автору'),
                                                     url=f'https://t.me/{username}')]])
    new_message = await bot.copy_message(chat_id=ad.group_fk, from_chat_id=ad.group_fk,
                                         message_id=ad.message_id, reply_markup=kb)
    await bot.delete_message(chat_id=ad.group_fk, message_id=ad.message_id)

    post_link = f"https://t.me/c/{ad.post_link.split('/')[-2]}/{new_message.message_id}"
    await AdvertisementService.update_adv_sql(job_id, message_id=new_message.message_id, post_link=post_link)


async def is_media_count_allowed(photos_id, videos_id, messages, reset_to_auction_menu_kb):
    if len(photos_id) > 5 or len(videos_id) > 1:
        await bot.send_message(chat_id=messages[0].from_user.id, text=_('❌ Максимум 5 фото і 1 відео.\n'
                                                                        'Надішліть ще раз ваші медіафайли:'),
                               reply_markup=reset_to_auction_menu_kb)
        return False
    elif not photos_id and not videos_id:
        await messages[0].answer(text=_('❌ Надішліть фото або відео.'), )
        return False
    return True


def set_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        filename='logs.log')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(console_handler)
    logging.getLogger('apscheduler').setLevel(logging.DEBUG)


async def build_media_group(photos_id, videos_id, caption):
    media_group = MediaGroupBuilder(caption=caption)
    for photo_id in photos_id:
        media_group.add_photo(media=photo_id)
    for video_id in videos_id:
        media_group.add_video(media=video_id)
    return media_group


async def get_token_or_create_new(token, user_chat_id, token_type: str):
    if token:
        status = await get_order_status(token)
        if status in ('CREATED', 'APPROVED'):
            return token
    new_token = await create_order(usd=1)
    await GroupSubscriptionPlanService.update_group_subscription_sql(user_chat_id, **{token_type: new_token})
    return new_token


async def generate_chats_kb(user_chats):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=chat.chat_name, callback_data=chat.chat_id)] for chat in
                         user_chats])


async def create_monetization_text_and_kb(subscription: GroupSubscriptionPlan, chat_title, chat_id):
    from keyboards.admin_kb import my_channels_groups_btn, back_to_monetization
    kb_builder = InlineKeyboardBuilder()
    text = '💰 Налаштування монетизації:\n\n'

    func_types = {
        'lot': {
            'active': subscription.auction_sub_time > time.time(),
            'paid': subscription.auction_paid,
            'name': 'лоти',
            'func_name': 'Аукціон'
        },
        'ads': {
            'active': subscription.ads_sub_time > time.time(),
            'paid': subscription.ads_paid,
            'name': 'оголошення',
            'func_name': 'Оголошення'

        }}
    for type_, values in func_types.items():
        active = values.get('active')
        paid = values.get('paid')
        name = values.get('name')
        func_name = values.get('func_name')
        if active and paid:
            kb_builder.button(text=f'Деактивувати платні {name}',
                              callback_data=f'paid:{type_}:deactivate:{chat_id}')
            text += f'🟢 Платні {name} активовані\n'
        elif active and not paid:
            kb_builder.button(text=f'Активувати платні {name}',
                              callback_data=f'paid:{type_}:activate:{chat_id}')
            text += f'🔴 Платні {name} не активовані\n'

        else:
            if my_channels_groups_btn not in kb_builder.buttons:
                kb_builder.add(my_channels_groups_btn)
            text += (f'🔒 Функція <b>{func_name}</b> не активована. Активувати функцію можна у меню '
                     f'<b>⚙️\u00A0Функціонал</b>\n\n')
    kb_builder.add(back_to_monetization)
    kb_builder.adjust(1)
    return text, kb_builder.as_markup()


async def check_group_subscriptions_db_and_paypal(group_id, chat_subscription):
    """
    Перевіряє чи є підписка у БД.
    Якщо немає - перевірка оплати підписки.
    """
    tokens = {'auction': None, 'ads': None}
    sub_dates = {}
    current_time = time.time()

    for sub_type, sub_time_attr in [('auction', 'auction_sub_time'), ('ads', 'ads_sub_time'), ]:
        sub_time = getattr(chat_subscription, sub_time_attr)
        if sub_time > current_time:  # чи є підписка у БД
            sub_dates[sub_type] = f'активовано до {datetime.datetime.fromtimestamp(sub_time).strftime("%d.%m.%Y")}'
        else:  # запит на перевірку оплати підписки
            token_approved = await get_token_approval(chat_subscription, type_=sub_type)  # type: ignore
            if token_approved:
                sub_dates[sub_type] = f'активовано до {datetime.datetime.fromtimestamp(sub_time).strftime("%d.%m.%Y")}'
                await GroupChannelService.update_chat_sql(group_id, **{sub_time_attr: 604800 + current_time})
            else:
                tokens[sub_type] = await get_token_or_create_new(getattr(chat_subscription, f'{sub_type}_token'),
                                                                 group_id,
                                                                 f'{sub_type}_token')
                sub_dates[sub_type] = 'не активовано'
    return sub_dates, tokens
