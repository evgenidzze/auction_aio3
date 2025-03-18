import datetime
from copy import deepcopy
from typing import Union

from aiogram import types, F
from aiogram.enums import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup

import database.models.advertisement
import database.models.lot
import keyboards.client_kb as client_kb
from database.services.base import delete_record_by_id
from database.services.group_channel_service import GroupChannelService
from database.services.lot_service import LotService
from database.services.user_group_service import UserGroupService
from database.services.user_service import UserService
from handlers.client.main_handlers import callback_query, FSMClient, message
from handlers.middleware import require_username, UserNotBlockedFilter, create_user_group
from utils.aiogram_media_group import media_group_handler
from utils.config import DEV_ID
from utils.create_bot import scheduler, _, bot
from utils.utils import create_user_lots_kb, IsMessageType, generate_chats_kb, \
    gather_media_from_messages, is_media_count_allowed, send_post_fsm, send_post, new_bid_caption, lot_ending, \
    create_lot_caption_and_kb


@callback_query(F.data == 'auction')
async def auction_menu(call: types.CallbackQuery, state: FSMContext, **kwargs):
    await call.message.edit_text(text=_('Ви обрали 🏷 Аукціон'), reply_markup=client_kb.auction_kb)
    await state.clear()


@callback_query(F.data == 'my_auctions')
async def my_auctions(call: types.CallbackQuery, state: FSMContext, **kwargs):
    lots = await LotService.get_user_lots(call.from_user.id)
    kb = await create_user_lots_kb(lots)
    kb.inline_keyboard.extend([[client_kb.create_auction_btn], [client_kb.back_to_auction_btn]])
    await state.set_state(FSMClient.change_lot)
    await call.message.edit_text(text=_('Оберіть існуючий аукціон або створіть новий:'),
                                 reply_markup=kb)

@callback_query(F.data == 'create_auction', IsMessageType(message_type=[ContentType.TEXT]))
@require_username
async def lot_group(call: types.CallbackQuery, state: FSMContext, **kwargs):
    chats = await GroupChannelService.get_all_groups()  # замінити на групи користувача
    kb = await generate_chats_kb(chats)
    kb.inline_keyboard.extend([[client_kb.reset_to_auction_menu_btn]])
    await state.set_state(FSMClient.lot_group_id)
    await call.message.edit_text(text=_('У якій групі бажаєте опублікувати лот?'), reply_markup=kb)


@callback_query(FSMClient.lot_group_id)
async def ask_city(call: types.CallbackQuery, state: FSMContext, **kwargs):
    await state.update_data(lot_group_id=call.data)
    user_group = await UserGroupService.get_user_group(call.from_user.id, call.data)
    if user_group and user_group.is_blocked:
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


@message(FSMClient.description, IsMessageType(message_type=[ContentType.TEXT]))
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
async def ready_lot(messages: Union[types.Message, types.CallbackQuery], state: FSMContext, **kwargs):
    state_name = await state.get_state()
    if isinstance(messages[0], types.Message) and 'media' in state_name:
        videos_id, photos_id = await gather_media_from_messages(messages=messages, state=state)
        if await is_media_count_allowed(photos_id, videos_id, messages, client_kb.reset_to_auction_menu_kb):
            await state.update_data(videos_id=videos_id)
            await state.update_data(photos_id=photos_id)
        else:
            return
    fsm_data = await state.get_data()
    kb = deepcopy(client_kb.ready_to_publish_kb)
    kb.inline_keyboard.extend([[client_kb.cancel_btn, client_kb.publish_btn]])
    text = '⬆️ Лот готовий до публікації!\nПеревірте всю інформацію і натисніть <b>✅ Опублікувати</b>, коли будете готові.'
    if isinstance(messages[0], types.Message):
        msg = await send_post_fsm(fsm_data, messages[0].from_user.id)
        await msg.reply(text=_(text), reply_markup=kb)
    elif isinstance(messages[0], types.CallbackQuery):
        if messages[0].data != 'back_to_ready' and await state.get_state() and 'steps' not in await state.get_state():
            await send_post_fsm(fsm_data, messages[0].from_user.id)
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
    await send_post(message.from_user.id, group_data.owner_telegram_id, photo_id, video_id, description,
                    start_price,
                    price_steps, currency=currency, city=city, lot_id=new_lot_id, moder_review=True,
                    videos=fsm_data.get('videos_id'), photos=fsm_data.get('photos_id'))
    await message.message.edit_text(
        text=_("✅ Лот відправлено на модерацію, незабаром він з'явиться у каналі <b><a href='{invite_link}'>"
               "{username}</a></b>.").format(invite_link=group_chat.invite_link, username=group_chat.title),
        reply_markup=client_kb.main_kb)

@callback_query(UserNotBlockedFilter(), F.data.startswith('bid'))
@require_username
@create_user_group
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
        group_id = lot.group_fk

        user = await UserService.get_user(owner_id)
        anti_sniper_time: datetime.time = user.anti_sniper
        if str(message.from_user.id) == lot.owner_telegram_id and str(message.from_user.id) != DEV_ID:
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
            caption = await new_bid_caption(lot_post.caption, message.from_user.first_name, price, currency,
                                            owner_locale=user.language, bid_count=bid_count + 1)
            await bot.edit_message_caption(chat_id=group_id, message_id=lot_post.message_id, caption=caption,
                                           reply_markup=lot_post.reply_markup)
            await bot.send_message(chat_id=owner_id,
                                   text=_("💸 Нова ставка на ваш лот!\n\n"
                                          "<a href='{lot_post}'><b>👉 Перейти до лоту.</b></a>").format(
                                       lot_post=lot_post.get_url()), reply_markup=client_kb.main_kb)
            if last_bidder_id:
                await bot.send_message(chat_id=last_bidder_id,
                                       text=_(
                                           "👋 Вашу ставку на лот <a href='{lot_post}'><b>{lot_name}</b></a> перебили.\n\n"
                                           "<a href='{lot_post}'><b>👉 Перейти до лоту.</b></a>").format(
                                           lot_post=lot_post.get_url(),
                                           lot_name=lot.description),
                                       reply_markup=client_kb.main_kb)
            await message.answer(text=_('✅ Ставку прийнято!'))
        else:
            await message.answer(text=_('Лот ще не опубліковано.'))
    else:
        await message.answer(text=_('❌ Аукціон не активний'))



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
    await send_post(message.from_user.id, message.from_user.id, photo_id, video_id, description,
                    start_price,
                    price_steps, currency=currency, city=city, under_moderation=not lot.approved)
    await state.set_state(None)
    await message.message.answer(text=_('Бажаєте видалити лот?'), reply_markup=client_kb.delete_lot_kb)


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

@callback_query(F.data == 'delete_lot')
async def delete_lot(call: types.CallbackQuery, state: FSMContext, **kwargs):
    fsm_data = await state.get_data()
    lot_id = fsm_data.get('change_lot')
    lot = await LotService.get_lot(lot_id)
    accept_btn = deepcopy(client_kb.accept_lot_deletion_btn)
    accept_btn.callback_data = f'lot_deletion_accept_{lot_id}'
    decline_btn = deepcopy(client_kb.decline_lot_deletion_btn)
    decline_btn.callback_data = f'lot_deletion_decline_{lot_id}'
    kb = InlineKeyboardMarkup(inline_keyboard=[[decline_btn, accept_btn]])
    if lot.lot_link:
        await call.message.edit_text(text=_('✅ Запит на видалення створено.'))
        await bot.send_message(chat_id=lot.group.owner_telegram_id,
                               text=_('<b>⚠️ Користувач {url} хоче видалити лот:\n</b>'
                                      '{lot_link}').format(url=call.from_user.url, lot_link=lot.lot_link),
                               reply_markup=kb)
    else:
        await call.message.edit_text(_('✅ Лот видалено.'), reply_markup=client_kb.main_kb)
        await delete_record_by_id(lot_id, database.models.lot.Lot)

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
        group_id = lot.group_fk
        if not scheduler.get_job(f'lot_{new_lot_id}'):
            msg = await send_post(owner_id, group_id, photo_id, video_id, description, start_price,
                                  price_steps, currency=currency, city=city, lot_id=new_lot_id,
                                  moder_review=None,
                                  photos_link=photos_link)
            await LotService.update_lot_sql(lot_id=new_lot_id, lot_link=msg.get_url(), message_id=msg.message_id,
                                            approved=1)
            scheduler.add_job(lot_ending, trigger='interval', id=f'lot_{new_lot_id}',
                              hours=lot.lot_time_living,
                              kwargs={'job_id': new_lot_id})
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
                await bot.delete_message(chat_id=lot.group_fk, message_id=lot.message_id)
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

@callback_query(F.data.startswith('edit_lot_text'))
async def edit_lot_text(call: types.CallbackQuery, state: FSMContext, **kwargs):
    obj_id = call.data.split(':')[-2]
    action = call.data.split(':')[-1]
    await state.set_state(None)
    if action == 'accept':
        lot = await LotService.get_lot(obj_id)
        if lot.new_text:  # якщо ще не підтверджений
            user = await UserService.get_user(lot.owner_telegram_id)
            caption, kb = await create_lot_caption_and_kb(user_id=user.telegram_id, moder_review=False,
                                                          lot_id=obj_id, description=lot.new_text,
                                                          start_price=lot.start_price, city=lot.city,
                                                          under_moderation=False,
                                                          new_desc=None, photos_link=lot.photos_link,
                                                          change_text=None, photos=None,
                                                          videos=None, price_steps=lot.price_steps,
                                                          currency=lot.currency)

            await LotService.update_lot_sql(obj_id, description=lot.new_text, new_text=None)
            try:
                if lot.bidder_telegram_id:
                    bidder_name = await bot.get_chat(lot.bidder_telegram_id)
                    caption = await new_bid_caption(caption, bidder_name.first_name, lot.last_bid,
                                                    lot.currency, user.language, lot.bid_count)
                await bot.edit_message_caption(chat_id=lot.group_fk, message_id=lot.message_id, caption=caption,
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
    else:
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

