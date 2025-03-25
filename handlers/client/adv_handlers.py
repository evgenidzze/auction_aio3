import datetime
import logging
import time
from copy import deepcopy
from random import randint
from typing import List

from aiogram import types, F, Router
from aiogram.enums import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database.models.advertisement
import database.models.lot
from database.services.advertisement_service import AdvertisementService
from database.services.base import delete_record_by_id
from database.services.group_channel_service import GroupChannelService
from database.services.group_subscription_plan_service import GroupSubscriptionPlanService
from database.services.user_group_service import UserGroupService
from database.services.user_service import UserService
from utils.aiogram_media_group import media_group_handler
from handlers.client.general_handlers import FSMClient, my_group_settings

from utils.create_bot import scheduler, _, bot
import keyboards.client_kb as client_kb
from handlers.middleware import require_username
from utils.utils import create_user_lots_kb, IsMessageType, generate_chats_kb, \
    gather_media_from_messages, is_media_count_allowed, send_post_fsm, user_sub_time_remain, \
    send_advert, adv_ending, repost_adv, \
    UserTypeSubscription

router = Router()


@router.callback_query(F.data == 'ad_menu')
async def add_menu(call: types.CallbackQuery, **kwargs):
    await call.message.edit_text(text=_('Ви обрали 📣 Оголошення'), reply_markup=client_kb.add_menu_kb)


@router.callback_query(F.data == 'my_ads')
async def my_ads(call: types.CallbackQuery, state: FSMContext, **kwargs):
    ads = await AdvertisementService.get_user_ads(call.from_user.id)
    kb = await create_user_lots_kb(ads)
    kb.inline_keyboard.extend([[client_kb.create_advert_btn], [client_kb.back_to_ad_menu_btn]])
    await state.set_state(FSMClient.change_ad)
    await call.message.edit_text(text=_('Оберіть існуючe оголошення або створіть нове:'),
                                 reply_markup=kb)


@router.callback_query(F.data == 'create_ad')
@require_username
async def group_for_adv(call: types.CallbackQuery, state: FSMContext, **kwargs):
    chats = await UserGroupService.get_user_groups(call.from_user.id)
    kb = await generate_chats_kb(chats)
    if chats:
        text = _('Оберіть групу в якій хочете виставити оголошення:')
    else:
        text = _('🤷‍♂️ У вас немає збережених груп, оберіть групу з загального списку:')
        kb.inline_keyboard.extend([[client_kb.other_channels_groups]])
    kb.inline_keyboard.extend([[client_kb.back_to_ad_menu_btn]])
    await state.set_state(FSMClient.adv_group_id)
    await call.message.edit_text(text=text, reply_markup=kb)


@router.callback_query(FSMClient.adv_group_id)
async def ask_description_ad(call: types.CallbackQuery, state: FSMContext, **kwargs):
    """
    Етап вводу опису для оголошення.
    Cases:
        - В групи немає підписки на оголошення
        - В юзера немає підписки на оголошення
        - В юзера є підписка або в групі free_trial
    """
    await state.update_data(adv_group_id=call.data)
    await call.message.edit_text(text=_('Перевірка підписки...'))
    group_subscription = await GroupSubscriptionPlanService.get_subscription(call.data)
    user_sub_time = await user_sub_time_remain(call.from_user.id,
                                               group_id=call.data,
                                               func_type=UserTypeSubscription.ADVERTISEMENT)

    if user_sub_time > 0 or not group_subscription.ads_paid:  # в юзера є підписка або оголошення безкоштовні
        await call.message.edit_text(text=_('📝 Напишіть опис для оголошення:'),
                                     reply_markup=client_kb.reset_to_ad_menu_kb)
        await state.set_state(FSMClient.description_ad)
    else:
        await my_group_settings(call, state)
        return


@router.message(FSMClient.description_ad, IsMessageType(message_type=[ContentType.TEXT]))
async def ask_city_ad(message: types.Message, state: FSMContext, **kwargs):
    if isinstance(message, types.Message):
        await state.update_data(description=message.text)
        await state.set_state(FSMClient.city_ad)
        await message.answer(text=_('🌆 Вкажіть ваше місто:'),

                             reply_markup=client_kb.reset_to_ad_menu_kb)


@router.message(FSMClient.city_ad, IsMessageType(message_type=[ContentType.TEXT]))
async def ask_media_ad(message: types.Message, state: FSMContext, **kwargs):
    text = _('📸 Надішліть фото і відео:\n'
             '<i>До 5 фото та до 1 відео</i>')
    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text=text, reply_markup=client_kb.reset_to_ad_menu_kb)
    else:
        await state.update_data(city=message.text)
        await message.answer(text=text, reply_markup=client_kb.reset_to_ad_menu_kb)
    await state.set_state(FSMClient.media_ad)


@router.message(FSMClient.media_ad)
@router.message(FSMClient.change_media_ad)
@router.callback_query(F.data == 'back_to_ready_ad')
@media_group_handler
async def save_media_ad(messages: List[types.Message], state: FSMContext, **kwargs):
    await state.update_data(is_ad=True)
    state_name = await state.get_state()
    if isinstance(messages[0], types.Message) and 'media' in state_name:
        videos_id, photos_id = await gather_media_from_messages(messages=messages, state=state)
        if await is_media_count_allowed(photos_id, videos_id, messages, client_kb.reset_to_ad_menu_kb):
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


@router.callback_query(F.data == 'publish_adv')
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
    await send_advert(user_id=message.from_user.id, send_to_id=group_data.owner_telegram_id,
                      description=description, city=city,
                      video_id=video_id, photo_id=photo_id,
                      moder_review=True,
                      advert_id=new_adv_id)
    await message.message.edit_text(
        text=_("✅ Оголошення відправлено не модерацію, незабаром воно з'явиться у каналі <b><a href='{invite_link}'>"
               "{username}</a></b>.").format(invite_link=channel.invite_link, username=channel.title),
        reply_markup=client_kb.main_kb)


@router.callback_query(F.data == 'show_ad')
@router.callback_query(FSMClient.change_ad)
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
    await send_advert(message.from_user.id, message.from_user.id, description, city, video_id, photo_id,
                      under_moderation=not approved)
    await state.set_state(None)
    await message.message.answer(text=_('Бажаєте видалити чи змінити опис оголошення?'),
                                 reply_markup=client_kb.delete_ad_kb)


@router.callback_query(F.data == 'delete_ad')
async def delete_ad(call: types.CallbackQuery, state: FSMContext, **kwargs):
    fsm_data = await state.get_data()
    ad_id = fsm_data.get('change_ad')
    ad = await AdvertisementService.get_adv(ad_id)
    if ad.post_link:
        try:
            await bot.delete_message(chat_id=ad.group_fk, message_id=ad.message_id)
        except:
            pass

    await call.message.edit_text(_('✅ Оголошення видалено.'), reply_markup=client_kb.main_kb)
    await delete_record_by_id(ad_id, database.models.advertisement.Advertisement)

    if scheduler.get_job(f'adv_repost_{ad_id}'):
        scheduler.remove_job(f'adv_repost_{ad_id}')
    if scheduler.get_job(f'adv_{ad_id}'):
        scheduler.remove_job(f'adv_{ad_id}')


@router.callback_query(F.data.startswith('accept_adv'))
async def accept_adv(call: types.CallbackQuery, state: FSMContext, **kwargs):
    accept = call.data.split('_')
    new_adv_id = accept[-1]
    await state.set_state(None)
    adv = await AdvertisementService.get_adv(new_adv_id)
    if adv:
        video_id = adv.video_id
        photo_id = adv.photo_id
        description = adv.description
        city = adv.city
        owner_id = adv.owner_telegram_id
        post_per_day = adv.post_per_day
        photos_link = adv.photos_link
        group_id = adv.group_fk
        owner = await bot.get_chat(owner_id)

        if not scheduler.get_job(f'adv_{new_adv_id}'):
            try:
                msg = await send_advert(user_id=owner_id, send_to_id=group_id, photo_id=photo_id,
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
            scheduler.add_job(adv_ending, trigger='interval', id=f'adv_{new_adv_id}', hours=168,
                              kwargs={'job_id': new_adv_id})
            now = datetime.datetime.now()
            if post_per_day:
                hours_mapping = {
                    1: str(now.hour),
                    2: f'{randint(8, 14)},{randint(17, 23)}',
                    3: f'{randint(8, 14)},{randint(15, 18)},{randint(19, 23)}'}

                scheduler.add_job(repost_adv, trigger='cron', id=f'adv_repost_{new_adv_id}',
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
            await call.message.answer(text=text, reply_markup=client_kb.main_kb)
            await bot.send_message(chat_id=owner_id, text=text, reply_markup=client_kb.main_kb)
        else:
            await call.answer(text=_('Оголошення вже опубліковано.'))
    else:
        await call.answer(text=_('Оголошення вже відхилено.'))


@router.callback_query(F.data.startswith('decline_adv'))
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


@router.callback_query(F.data.startswith('edit_ad_text'))
async def edit_ad_text(call: types.CallbackQuery, state: FSMContext, **kwargs):
    obj_id = call.data.split(':')[-2]
    action = call.data.split(':')[-1]
    if action == 'accept':
        ad = await AdvertisementService.get_adv(obj_id)

        if ad.new_text:
            user = await UserService.get_user(ad.owner_telegram_id)
            user_tg = await bot.get_chat(user.telegram_id)
            kb = InlineKeyboardBuilder()
            kb.button(text='⏳', callback_data=f'time_left_adv_{obj_id}')
            kb.button(text=_('💬 Задати питання автору', locale=user.language),
                                       url=f'https://t.me/{user_tg.username}')
            invite_link = await create_start_link(bot, ad.group.chat_id)
            kb.row(InlineKeyboardButton(text='📝 Створити свою публікацію', url=invite_link))
            await AdvertisementService.update_adv_sql(obj_id, description=ad.new_text, new_text=None)
            caption = _("<b>{description}</b>\n\n"
                        "🏙 <b>Місто:</b> {city}\n", locale=user.language).format(description=ad.new_text,
                                                                                 city=ad.city)
            try:
                await bot.edit_message_caption(chat_id=ad.group_fk, message_id=ad.message_id, caption=caption,
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


@router.callback_query(FSMClient.repost_count_answer)
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


@router.callback_query(FSMClient.repost_count)
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
    await send_post_fsm(fsm_data, call.from_user.id, is_ad=True)
    await bot.send_message(chat_id=call.from_user.id, text=text, reply_markup=kb,
                           reply_to_message_id=last_message_id)
