import datetime
import time

from aiogram import types, Router, F
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.client_handlers import router
from utils.create_bot import job_stores, bot, _
from database.db_manage import get_user, update_user_sql, get_user_chats, get_chat_record, update_chat_sql, \
    create_group_channel
from keyboards.admin_kb import reject_to_admin_btn, back_to_admin_btn, back_to_group_manage_btn, \
    unblock_user_btn, block_user_btn, back_my_channels_groups, back_my_channels_groups_kb, \
    activate_ad_auction_kb, admin_menu_kb, create_subscription_group_buttons_kb
from keyboards.client_kb import main_kb
from utils.paypal import create_order, create_partner_referral_url_and_token, user_is_partner
from utils.utils import get_token_approval, payment_completed, \
    get_token_or_create_new


from handlers.middleware import subscription_group_required
from database.db_manage import get_chat_record, update_chat_sql


class FSMAdmin(StatesGroup):
    user_chat_id = State()
    group_id_settings = State()
    user_id = State()


async def admin(message: types.Message, state):
    await state.clear()
    if isinstance(message, types.Message):
        await message.answer(text='Меню адміністратора', reply_markup=admin_menu_kb.as_markup())
    elif isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text='Меню адміністратора', reply_markup=admin_menu_kb.as_markup())


async def deny_user_access(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(FSMAdmin.user_id)
    await call.message.edit_text(text='👋🏻 Вітаю!\n'
                                      'Перешліть повідомлення або <b>id</b> користувача для надання або скасування прав:',
                                 reply_markup=InlineKeyboardMarkup(inline_keyboard=[[reject_to_admin_btn]]))


async def user_access(message: types.Message, state: FSMContext):
    if isinstance(message, types.Message):
        if message.forward_from:
            user_id = message.forward_from.id
        else:
            user_id = message.text
        await state.update_data(black_user_id=user_id)
    else:
        fsm_data = await state.get_data()
        user_id = fsm_data.get('black_user_id')
    user = await get_user(user_id)

    if user:
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        if user.is_blocked:
            unblock_user_btn.callback_data = unblock_user_btn.callback_data.format(user_id=user_id)
            kb.inline_keyboard.extend([[unblock_user_btn]])
            text = '🚫 Користувач заблокований.'
        else:
            block_user_btn.callback_data = block_user_btn.callback_data.format(user_id=user_id)
            kb.inline_keyboard.extend([[block_user_btn]])
            text = '✅ Користувач розблокований.'
        kb.inline_keyboard.extend([[back_to_admin_btn]])
        if isinstance(message, types.Message):
            await message.answer(text=text, reply_markup=kb)
        else:
            await message.message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text='❌ Користувача з таким id не існує.\n'
                                  'Спробуйте ще раз:')


async def change_user_access(call: types.CallbackQuery, state: FSMContext):
    user_id, action = call.data.split('_')[1:3]
    if action == 'block':
        await update_user_sql(user_id, is_blocked=1)
    else:
        await update_user_sql(user_id, is_blocked=0)
    await user_access(call, state)
    return


async def payment_tumbler(call: types.CallbackQuery, state: FSMContext):
    redis_obj = job_stores.get('default')
    if call.data == 'off_payment':
        redis_obj.redis.set(name='payment', value='off')
    else:
        redis_obj.redis.set(name='payment', value='on')
    await admin(call, state)
    return


async def group_id_settings(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(group_id_settings=call.data)
    group = await get_chat_record(call.data)
    kb_builder = InlineKeyboardBuilder()
    kb_builder.add(
        InlineKeyboardButton(text='❌ Деактивувати аукціон', callback_data='1'),
        InlineKeyboardButton(text='❌ Деактивувати платні лоти', callback_data='1'),
        InlineKeyboardButton(text='❌ Деактивувати оголошення', callback_data='1'),
        InlineKeyboardButton(text='❌ Деактивувати платні оголошення', callback_data='1'),
    )
    kb_builder.add(back_to_group_manage_btn)
    kb_builder.adjust(1)
    await call.message.edit_text(text='Налаштування групи {group}\n\n'
                                      '🟢 Функція аукціону активована\n'
                                      '🟢 Платні лоти активовані\n\n'
                                      '🟢 Функція оголошень активована\n'
                                      '🟢 Платні оголошення активовані\n'
                                 .format(group=group.chat_name),
                                 reply_markup=kb_builder.as_markup())
    # await call.message.edit_text()


async def add_group(call: types.CallbackQuery):
    me = await bot.get_me()
    await call.message.edit_text(text='Додайте бота у свою групу, та надайте йому права адміністратора.\n'
                                      "Ім'я бота: @{bot_name}".format(bot_name=me.username),
                                 reply_markup=InlineKeyboardMarkup(inline_keyboard=[[back_to_admin_btn]]))


async def my_channels_groups(call: types.CallbackQuery, state: FSMContext):
    user_chats = await get_user_chats(call.from_user.id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=chat.chat_name, callback_data=chat.chat_id)] for chat in
                         user_chats])
    kb.inline_keyboard.extend([[back_to_admin_btn]])
    await state.set_state(FSMAdmin.user_chat_id)
    await call.message.edit_text(text=_('Ваші групи/канали.\n'
                                        'Щоб активувати або перевірити статус бота, оберіть потрібну групу/канал:'),
                                 reply_markup=kb)


async def user_chat_menu(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(text=_('Перевірка підписки...'))
    user_chat_id = call.data.split(':')[0]
    chat = await get_chat_record(user_chat_id)
    adv_subscribe_time_remain, auction_subscribe_time_remain = chat.ads_sub_time, chat.auction_sub_time
    text = ('Оголошення {ads_sub_date}\n'
            'Аукціон {auction_sub_date}')
    auction_token, ads_token = None, None
    if auction_subscribe_time_remain > time.time():
        auction_sub_date = f'активовано до {datetime.datetime.fromtimestamp(chat.auction_sub_time).strftime("%d.%m.%Y")}'
    else:
        auction_token_approved = await get_token_approval(chat, type_='auction')
        if auction_token_approved:
            auction_sub_date = f'активовано до {datetime.datetime.fromtimestamp(chat.auction_sub_time).strftime("%d.%m.%Y")}'
            await update_chat_sql(user_chat_id, auction_sub_time=604800 + time.time())
        else:
            auction_sub_date = 'не активовано'
            auction_token = await get_token_or_create_new(chat.auction_token, user_chat_id, 'auction_token')
    if adv_subscribe_time_remain > time.time():
        ads_sub_date = f'активовано до {datetime.datetime.fromtimestamp(chat.ads_sub_time).strftime("%d.%m.%Y")}'
    else:
        ads_token_approved = await get_token_approval(chat, type_='ads')
        if ads_token_approved:
            ads_sub_date = f'активовано до {datetime.datetime.fromtimestamp(chat.ads_sub_time).strftime("%d.%m.%Y")}'
            await update_chat_sql(user_chat_id, ads_sub_time=604800 + time.time())
        else:
            ads_token = await get_token_or_create_new(chat.ads_token, user_chat_id, 'ads_token')
            ads_sub_date = 'не активовано'
    text = text.format(auction_sub_date=auction_sub_date, ads_sub_date=ads_sub_date)

    kb = await activate_ad_auction_kb(auction_token=auction_token, ads_token=ads_token,
                                      back_btn=back_my_channels_groups, user_chat_id=user_chat_id)
    await bot.send_message(chat_id=call.from_user.id, text=text, reply_markup=kb)


async def update_bot_subscription_status(call, state: FSMContext):
    token = call.data.split('_')[-1]
    user_chat_id = call.data.split(':')[0]
    payment = await payment_completed(token)
    if payment:
        await update_chat_sql(user_chat_id, subscription_time=604800 + time.time())
        await call.message.edit_text(text=_('✅ Вітаю! Бота успішно активовано на 30 днів.'),
                                     reply_markup=main_kb)
    else:
        await user_chat_menu(call, state)
        return


@router.my_chat_member()
async def my_chat_member_handler(my_chat_member: types.ChatMemberUpdated):
    if my_chat_member.chat.type not in {'channel', 'group', 'supergroup'}:
        return

    user_id = my_chat_member.from_user.id
    chat_title = my_chat_member.chat.title
    new_status = my_chat_member.new_chat_member.status

    messages = {
        ChatMemberStatus.ADMINISTRATOR: _(
            "{title} успішно підключено!"
        ).format(title=chat_title),
        ChatMemberStatus.MEMBER: _(
            "Для того, щоб бот функціонував у групі {title}, потрібно надати йому права адміністратора."
        ).format(title=chat_title),
        ChatMemberStatus.RESTRICTED: _(
            "Бот не може функціонувати у групі {title}, оскільки він заблокований."
        ).format(title=chat_title),
        ChatMemberStatus.LEFT: _(
            "Бот видалений з групи {title}."
        ).format(title=chat_title),
        ChatMemberStatus.KICKED: _(
            "Бота відключено з групи {title}."
        ).format(title=chat_title),
    }

    if new_status == ChatMemberStatus.ADMINISTRATOR:
        chat_link = await bot.export_chat_invite_link(chat_id=my_chat_member.chat.id)
        await bot.send_message(chat_id=user_id, text=messages[new_status])
        await create_group_channel(
            owner_telegram_id=user_id,
            chat_id=my_chat_member.chat.id,
            chat_type=my_chat_member.chat.type,
            chat_name=chat_title,
            chat_link=chat_link,
        )
        chat = await get_chat_record(my_chat_member.chat.id)
        is_active_free_trial = datetime.datetime.fromtimestamp(chat.free_trial) > datetime.datetime.now()

        if not is_active_free_trial and not chat.auction_paid and not chat.ads_paid:
            await bot.send_message( # Повідомлення про використаний пробного періоду та відсутність підписок
                chat_id=user_id,
                text=_("Ви не маєте активних підписок. Оформіть підписку для групи, щоб отримати доступ до потрібних функцій."),
                reply_markup=create_subscription_group_buttons_kb(chat.chat_id, is_trial=chat.free_trial == 0)
            )
            return None
        else:
            await bot.send_message( # Повідомлення про активну підписку
                chat_id=user_id,
                text=_("Зараз у вас активна підписка типу *{subscribe}* до *{last_time_subscribe}*").format( # Пробна, аукціон, оголошення
                    subscribe=_('Пробний період') if is_active_free_trial else _('Універсальна') if chat.auction_paid and chat.ads_paid else _('Аукціон') if chat.auction_paid else _('Оголошення'),
                    last_time_subscribe=datetime.datetime.fromtimestamp(
                        chat.free_trial if chat.free_trial else chat.auction_sub_time if chat.auction_paid else chat.ads_sub_time
                    ).strftime("%d.%m.%Y" if chat.free_trial else "%d.%m.%Y"),
                ),
                reply_markup=admin_menu_kb.as_markup()
            )
            return None

    elif new_status in messages:
        await bot.send_message(chat_id=user_id, text=messages[new_status])


async def handle_subscription_group(callback_query: types.CallbackQuery):
    """
    Обробка підписки на групу.
    """
    chat_id = callback_query.from_user.id

    current_time = time.time()

    group_id = callback_query.data.split('_')[-1]
    duration_days = int(callback_query.data.split('_')[-2])
    type_subscribe = callback_query.data.split('_')[-3]

    if type_subscribe == 'trial':
        chat_data = await get_chat_record(group_id)
        print(chat_data)
        if chat_data.free_trial > 0:
            await callback_query.message.edit_text(
                text=_("Пробний період вже було використано."),
                reply_markup=admin_menu_kb.as_markup()
            )
            return None
        await update_chat_sql(group_id, free_trial=duration_days * 86400 + current_time)
        await callback_query.message.edit_text(
            text=_("Пробний період активовано на {days} днів.").format(days=duration_days),
            reply_markup=admin_menu_kb.as_markup()
        )
    elif type_subscribe == 'auction':
        # TODO: Додаткова перевірка на наявність підписки та логіка оплати. А також логування операцій.
        await update_chat_sql(group_id, auction_sub_time=duration_days * 86400 + current_time, auction_paid=True)
        await callback_query.message.edit_text(
            text=_("Підписка на аукціон активована на {days} днів.").format(days=duration_days),
            reply_markup=admin_menu_kb.as_markup()
        )

    elif type_subscribe == 'ads':
        # TODO: Додаткова перевірка на наявність підписки та логіка оплати. А також логування операцій.
        await update_chat_sql(group_id, ads_sub_time=duration_days * 86400 + current_time, ads_paid=True)
        await callback_query.message.edit_text(
            text=_("Підписка на оголошення активована на {days} днів.").format(days=duration_days),
            reply_markup=admin_menu_kb.as_markup()
        )

    elif type_subscribe == 'universal':
        # TODO: Додаткова перевірка на наявність підписки та логіка оплати. А також логування операцій.
        await update_chat_sql(
            group_id,
            auction_sub_time=duration_days * 86400 + current_time,
            ads_sub_time=duration_days * 86400 + current_time,
            ads_paid=True,
            auction_paid=True
        )
        await callback_query.message.edit_text(
            text=_("Універсальна підписка активована на {days} днів.").format(days=duration_days),
            reply_markup=admin_menu_kb.as_markup()
        )


async def not_registered_partner(message: types.Message):
    referral_data = await create_partner_referral_url_and_token(message.from_user.id)
    reg_url = referral_data.get('url')
    await message.answer(text='Щоб стати партнером зареєструйтесь в PayPal по посиланню\n'
                              '{reg_url}'.format(reg_url=reg_url),
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[[back_to_admin_btn]]))


async def monetization(call: types.CallbackQuery):
    is_partner = await user_is_partner(call.from_user.id)
    if is_partner:
        await call.message.edit_text(text='Вітаю, ви партнер!',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[back_to_admin_btn]]))
    else:
        referral_data = await create_partner_referral_url_and_token(call.from_user.id)
        # referral_data = await create_partner_referral_url_and_token('12312312')
        reg_url = referral_data.get('url')
        builder = InlineKeyboardBuilder()
        builder.button(text='Активувати PayPal', url=reg_url)
        builder.add(back_to_admin_btn)
        builder.adjust(1)
        await call.message.edit_text(
            text="Щоб стати партнером зареєструйтесь в PayPal по посиланню або під'єднайте існуючий аккаунт.\n"
                 "Після активації ви отримаєте повідомлення.\n"
                 "<b><a href='{reg_url}'>Активувати PayPal</a></b>".format(reg_url=reg_url),
            reply_markup=builder.as_markup())


def register_admin_handlers(r: Router):
    r.message.register(admin, Command('admin'))
    r.message.register(not_registered_partner, Command('not_registered_partner'))
    r.callback_query.register(admin, F.data == 'admin')  # Меню адміністратора
    r.callback_query.register(change_user_access, F.data.startswith('access'))  # Блокування/Розблокування користувача
    r.callback_query.register(my_channels_groups, F.data == 'my_channels_groups')  # Пункт меню "Мої групи/канали"
    r.callback_query.register(deny_user_access, F.data == 'deny_user_access')  # Чорний список
    r.callback_query.register(payment_tumbler, F.data.endswith('_payment'))  # Вимкнути/Увімкнути оплату
    r.callback_query.register(handle_subscription_group, F.data.startswith("subscription_group"))  # Підписка на групу
    r.callback_query.register(add_group, F.data == 'add_group')  # Пункт меню "Підключити групу"
    r.callback_query.register(monetization, F.data == 'monetization')  # Монетизація
    r.callback_query.register(group_id_settings, FSMAdmin.group_id_settings)  # Налаштування групи
    r.callback_query.register(user_chat_menu, FSMAdmin.user_chat_id)
    r.callback_query.register(update_bot_subscription_status, F.data.endswith('sub_update'))
    r.message.register(user_access, FSMAdmin.user_id)
