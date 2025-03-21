import datetime
import locale
import logging

from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import keyboards.client_kb as client_kb
from database.services.advertisement_service import AdvertisementService
from database.services.group_channel_service import GroupChannelService
from database.services.lot_service import LotService
from database.services.user_group_service import UserGroupService
from database.services.user_service import UserService
from utils.create_bot import scheduler, _, i18n, bot
from utils.utils import IsPrivateChatFilter, send_post, user_sub_time_remain, \
    send_advert, add_user_group_handler, deeplink_handler, UserTypeSubscription

locale.setlocale(locale.LC_ALL, 'uk_UA.utf8')

router = Router()


class FSMClient(StatesGroup):
    my_group = State()
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


@router.message(CommandStart(), IsPrivateChatFilter(), StateFilter("*"))
@router.message(CommandStart(deep_link=True), IsPrivateChatFilter(), StateFilter("*"))
async def start(message: types.Message, state: FSMContext, command: CommandObject, **kwargs):
    """/start"""
    await state.clear()
    for job in scheduler.get_jobs():
        logging.info(f'{job.id}-{job}-{job.kwargs}')
    interrupt_start = await deeplink_handler(main_menu, message, command, state, kwargs)
    if interrupt_start:
        return
    await state.set_state(FSMClient.language)
    text = _('<b>Оберіть мову / Choose a language:</b>')
    if isinstance(message, types.Message):
        await message.answer(text=text,
                             reply_markup=client_kb.language_kb)
    elif isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text=text,
                                        reply_markup=client_kb.language_kb)


@router.message(Command('main_menu'), IsPrivateChatFilter(), StateFilter("*"))
@router.callback_query(FSMClient.language)
@router.callback_query(F.data == 'main_menu')
async def main_menu(call, state: FSMContext, **kwargs):
    """/main_menu"""
    data = await state.get_data()
    group_id = data.get('group_id')
    await state.clear()
    clean_text = "Вітаю, <b>{first_name}!</b><a href='https://telegra.ph/file/3f6168cc5f94f115331ac.png'>⠀</a>\n"
    text = _(clean_text).format(first_name=call.from_user.username)
    geo = getattr(call, 'data', None)
    if geo in ('en', 'uk'):
        await UserService.insert_or_update_user(telegram_id=call.from_user.id, language=call.data)
        text = _(clean_text, locale=call.data).format(first_name=call.from_user.username)
        i18n.current_locale = call.data
    if group_id:
        await add_user_group_handler(call.from_user.id, group_id)
        await bot.send_message(chat_id=call.from_user.id, text=text, reply_markup=client_kb.main_kb)
        return
    if isinstance(call, types.Message):
        await bot.send_message(chat_id=call.from_user.id, text=text, reply_markup=client_kb.main_kb)
    else:
        await call.message.edit_text(text=text, reply_markup=client_kb.main_kb)


@router.callback_query(F.data == 'groups_and_channels')
async def groups_and_channels(call: types.CallbackQuery, **kwargs):
    await call.message.edit_text(text=_('Ви обрали 👥 Групи та канали'), reply_markup=client_kb.group_channels_kb)


@router.callback_query(F.data == 'other_channels_groups')
async def other_channels_groups(call: types.CallbackQuery, **kwargs):
    other_chats = await GroupChannelService.get_all_groups()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=chat.chat_name, url=chat.chat_link)] for chat in
                         other_chats])
    kb.inline_keyboard.extend([[client_kb.back_group_channels_btn]])
    await call.message.edit_text(text=_('Список груп у яких працює бот:'),
                                 reply_markup=kb)


@router.callback_query(F.data == 'my_channels_groups')
async def my_channels_groups(call: types.CallbackQuery, state: FSMContext, **kwargs):
    my_chats = await UserGroupService.get_user_groups(call.from_user.id)
    await state.set_state(FSMClient.my_group)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=chat.group.chat_name, callback_data=chat.group.chat_id)] for
                         chat in
                         my_chats])
    kb.inline_keyboard.extend([[client_kb.back_group_channels_btn]])
    await call.message.edit_text(text=_('Список груп у яких працює бот:'),
                                 reply_markup=kb)


@router.callback_query(FSMClient.my_group)
async def my_group_settings(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await state.update_data(my_group=call.data)
    user_group = await UserGroupService.get_user_group(call.from_user.id, call.data)
    adv_time = await user_sub_time_remain(call.from_user.id, group_id=call.data,
                                          func_type=UserTypeSubscription.ADVERTISEMENT)
    text = _("")
    await call.message.edit_text(text='Показати інфу про групу (статуси, підписки і т д)',
                                 reply_markup=client_kb.client_group_kb.as_markup())


@router.callback_query(F.data == 'del_client_group')
async def del_client_group(call: types.CallbackQuery, state: FSMContext):
    fsm_data = await state.get_data()
    my_group = fsm_data.get('my_group')
    await UserGroupService.delete_record(user_id=call.from_user.id, group_id=my_group)
    await call.message.edit_text(text='✅ Групу видалено зі списку', reply_markup=client_kb.main_kb)


@router.callback_query(F.data == 'help')
async def help_(call: types.CallbackQuery, **kwargs):
    await call.message.edit_text(text=_("По всім запитанням @Oleksandr_Polis\n\n"
                                        "<i>Що таке <a href='https://telegra.ph/Antisnajper-03-31'>"
                                        "<b>⏱ Антиснайпер?</b></a></i>\n"),
                                 reply_markup=client_kb.back_to_main_kb,
                                 disable_web_page_preview=True)


@router.callback_query(F.data == 'change_media')
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


@router.callback_query(F.data == 'change_desc')
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


@router.callback_query(F.data == 'change_city')
async def change_city(call: types.CallbackQuery, state: FSMContext, **kwargs):
    data = await state.get_data()
    await state.set_state(FSMClient.change_city)

    if data.get('is_ad'):
        kb = client_kb.back_to_ready_ad_kb
    else:
        kb = client_kb.back_to_ready_kb
    await call.message.edit_text(text=_('Надішліть нову назву міста:'), reply_markup=kb)


@router.message(FSMClient.change_city)
async def set_new_city(message: types.Message, state: FSMContext, **kwargs):
    await state.update_data(city=message.text)
    data = await state.get_data()
    if data.get('is_ad'):
        from handlers.client.adv_handlers import save_media_ad
        await save_media_ad(message, state)
    else:
        from handlers.client.lot_handlers import ready_lot
        await ready_lot(message, state)


@router.message(FSMClient.change_desc)
async def set_desc(message: types.Message, state: FSMContext, **kwargs):
    await state.update_data(description=message.text)
    data = await state.get_data()
    if data.get('is_ad'):
        from handlers.client.adv_handlers import save_media_ad
        await save_media_ad(message, state)
    else:
        from handlers.client.lot_handlers import ready_lot
        await ready_lot(message, state)


@router.callback_query(F.data.startswith('time_left'))
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


@router.callback_query(F.data.startswith('change_desc_exist'))
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


@router.message(FSMClient.new_desc_exist)
async def request_new_desc(message: types.Message, state: FSMContext, **kwargs):
    fsm_data = await state.get_data()
    object_type = fsm_data.get('object_type')
    await state.set_state(None)
    await message.answer(text=_('✅ Очікуйте підтвердження модератора.'), reply_markup=client_kb.main_kb)
    if object_type == 'ad':
        obj_id = fsm_data.get('change_ad')
        await AdvertisementService.update_adv_sql(obj_id, new_text=message.text)
        ad = await AdvertisementService.get_adv(obj_id)
        await send_advert(user_id=message.from_user.id, send_to_id=ad.group.owner_telegram_id,
                          description=ad.description,
                          city=ad.city,
                          video_id=ad.video_id, photo_id=ad.photo_id,
                          change_text=True, advert_id=obj_id, new_desc=ad.new_text)
    else:
        obj_id = fsm_data.get('change_lot')
        await LotService.update_lot_sql(obj_id, new_text=message.text)
        lot = await LotService.get_lot(obj_id)
        await send_post(message.from_user.id, lot.group.owner_telegram_id, lot.photo_id, lot.video_id,
                        lot.description,
                        lot.start_price,
                        lot.price_steps, currency=lot.currency, city=lot.city, lot_id=obj_id,
                        change_text=True, new_desc=lot.new_text)
