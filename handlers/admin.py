import datetime
import time
from typing import Literal, TypeAlias

from aiogram import types, Router, F
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.services.group_channel_service import GroupChannelService
from database.services.group_subscription_plan_service import GroupSubscriptionPlanService
from database.services.user_service import UserService
from utils.create_bot import job_stores, bot, _

from keyboards.admin_kb import reject_to_admin_btn, back_to_admin_btn, \
    unblock_user_btn, block_user_btn, back_my_channels_groups, \
    activate_ad_auction_kb, admin_menu_kb, add_group_kb
from keyboards.client_kb import main_kb
from utils.paypal import create_partner_referral_url_and_token, user_is_merchant_api
from utils.utils import payment_completed, \
    generate_chats_kb, create_monetization_text_and_kb, check_group_subscriptions_db_and_paypal

from utils.create_bot import scheduler
from apscheduler.jobstores.base import JobLookupError

TypeSubscription: TypeAlias = Literal['ads', 'auction', 'free_trial']

router = Router()
message = router.message
callback_query = router.callback_query


class FSMAdmin(StatesGroup):
    monetize_chat = State()
    group_id = State()
    user_id = State()


async def admin(message: types.Message, state):
    await state.clear()
    if isinstance(message, types.Message):
        if message.chat.type == 'private':
            await message.answer(text='Меню адміністратора', reply_markup=admin_menu_kb.as_markup())
    elif isinstance(message, types.CallbackQuery):
        if message.message.chat.type == 'private':
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
    user = await UserService.get_user(user_id)

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
        await UserService.update_user_sql(user_id, is_blocked=1)
    else:
        await UserService.update_user_sql(user_id, is_blocked=0)
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


async def group_id_settings(call: types.CallbackQuery, state: FSMContext, chat_id=None):
    await state.set_state(None)
    if not chat_id:
        chat_id = call.data

    chat = await bot.get_chat(chat_id=chat_id)
    subscription = await GroupSubscriptionPlanService.get_subscription(chat_id)
    text, kb = await create_monetization_text_and_kb(subscription, chat.title, chat_id)
    await call.message.edit_text(text=text, reply_markup=kb)


async def paid_chat_function(call: types.CallbackQuery, state: FSMContext):
    action_to_boolean = {'activate': 1, 'deactivate': 0}
    func_type: Literal['lot', 'ads']
    func_type_to_db_column_name = {'lot': 'auction_paid', 'ads': 'ads_paid'}

    func_type, action, group_id = call.data.split(':')[1:]
    kwargs = {func_type_to_db_column_name[func_type]: action_to_boolean[action]}
    await GroupSubscriptionPlanService.update_group_subscription_sql(chat_id=group_id, **kwargs)
    await group_id_settings(call, state, chat_id=group_id)


async def add_group(call: types.CallbackQuery):
    me = await bot.get_me()
    await call.message.edit_text(text='Додайте бота у свою групу, та надайте йому права адміністратора.\n'
                                      "Ім'я бота: @{bot_name}".format(bot_name=me.username),
                                 reply_markup=InlineKeyboardMarkup(inline_keyboard=[[back_to_admin_btn]]))


async def my_channels_groups(call: types.CallbackQuery, state: FSMContext):
    """Після натискання на кнопку Мої групи/канали"""
    user_chats = await GroupChannelService.get_group_by_owner_telegram_id(call.from_user.id)
    kb = await generate_chats_kb(user_chats)
    kb.inline_keyboard.extend([[add_group_kb], [back_to_admin_btn]])
    await state.set_state(FSMAdmin.group_id)
    await call.message.edit_text(text=_('Ваші групи.\n'
                                        'Щоб активувати функціонал, оберіть потрібну групу:'),
                                 reply_markup=kb)


async def user_chat_menu(call: types.CallbackQuery):
    """Після натискання на кнопку Функціонал груп та вибору групи"""
    await call.message.edit_text(text=_('Перевірка підписки...'))

    group_id = call.data.split(':')[0]
    chat_subscription = await GroupSubscriptionPlanService.get_subscription(group_id)
    if chat_subscription.free_trial > time.time():
        days = (datetime.datetime.fromtimestamp(chat_subscription.free_trial) - datetime.datetime.now()).days
        text = _('Активований пробний період.\n'
                 'До кінця залишилось {days} днів').format(days=days)
        builder = InlineKeyboardBuilder()

        builder.add(back_to_admin_btn)

        kb = builder.as_markup()
    else:
        sub_dates, tokens = await check_group_subscriptions_db_and_paypal(group_id=group_id,
                                                                          chat_subscription=chat_subscription)
        text = (
            f'Оголошення {sub_dates["ads"]}\n'
            f'Аукціон {sub_dates["auction"]}'
        )
        kb = await activate_ad_auction_kb(
            auction_token=tokens['auction'],
            ads_token=tokens['ads'],
            back_btn=back_my_channels_groups,
            group_id=group_id,
            free_trial=chat_subscription.free_trial
        )

    await call.message.edit_text(text=text, reply_markup=kb)


async def update_bot_subscription_status(call, state: FSMContext):
    """Після натискання на кнопку Оновити статус"""
    token = call.data.split('_')[-1]
    user_chat_id = call.data.split(':')[0]
    payment = await payment_completed(token)
    if payment:
        await GroupChannelService.update_chat_sql(user_chat_id, subscription_time=604800 + time.time())
        await call.message.edit_text(text=_('✅ Вітаю! Бота успішно активовано на 30 днів.'),
                                     reply_markup=main_kb)
    else:
        await user_chat_menu(call)
        return


@router.my_chat_member()
async def my_chat_member_handler(my_chat_member: types.ChatMemberUpdated):
    """
    Обробка подій приєднання бота до групи.

    Приєднання зараховується, якщо бот має права адміністратора.
    """
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
            "{title} успішно підключено!"
            #"Для того, щоб бот функціонував у групі {title}, потрібно надати йому права адміністратора."
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

    if new_status == ChatMemberStatus.ADMINISTRATOR or new_status == ChatMemberStatus.MEMBER:

        chat_link = await bot.export_chat_invite_link(chat_id=my_chat_member.chat.id)
        await GroupChannelService.create_group(
            owner_telegram_id=user_id,
            chat_id=my_chat_member.chat.id,
            chat_type=my_chat_member.chat.type,
            chat_name=chat_title,
            chat_link=chat_link,
        )

        check_sub_msg = await bot.send_message(chat_id=user_id, text=_('Перевірка підписки...'))
        await user_chat_menu(types.CallbackQuery(id='generated_callback_query', from_user=my_chat_member.from_user,
                                                 chat_instance=str(my_chat_member.chat.id),
                                                 data=f'{my_chat_member.chat.id}', message=check_sub_msg))


    elif new_status in messages:
        await bot.send_message(chat_id=user_id, text=messages[new_status])


class SubscriptionGroupHandler:

    def __init__(self):
        pass

    @staticmethod
    async def scheduled_job_subscribe_is_ending(owner_id: str, type_subscription: TypeSubscription):
        """Повідомлення за добу до закінчення підписки."""
        message = {
            'ads': _('Ваша підписка на оголошення добігає кінця. Поповніть підписку.'),
            'auction': _('Ваша підписка на аукціон добігає кінця. Поповніть підписку.'),
            'free_trial': _('Ваш пробний період добігає кінця. Поповніть підписку.'),
        }[type_subscription]

        await bot.send_message(chat_id=owner_id, text=message)

    @staticmethod
    def create_task_subscribe_is_ending(owner_chat_id, group_chat_id: str, type_subscription: str,
                                        duration_days: int):
        """Створення задачі на попередження про закінчення підписки."""
        try:
            scheduler.remove_job(f'subscribe:{group_chat_id}')
        except JobLookupError:
            pass

        current_time = time.time()
        scheduler.add_job(
            SubscriptionGroupHandler.scheduled_job_subscribe_is_ending,
            'date',
            run_date=datetime.datetime.fromtimestamp(current_time + duration_days * 86400 - 86400),
            args=[owner_chat_id, type_subscription],
            id=f'subscribe:{group_chat_id}'
        )

    @staticmethod
    async def payment_process(owner_chat_id, group_chat_id: str, type_subscription: str, duration_days: int):
        """Створення платіжного процесу."""
        # TODO: Логіка оплати. Логування і тд.
        pass

    async def listening(self, callback_query: types.CallbackQuery):
        """
        Обробка кнопок підписки на групу.
        startswith("subscription_group")
        """
        owner_chat_id = callback_query.from_user.id
        group_chat_id = callback_query.data.split(':')[-1]
        duration_days = int(callback_query.data.split(':')[-2])
        type_subscribe = callback_query.data.split(':')[-3]  # trial, auction, ads

        current_time = time.time()
        chat_subscription = await GroupSubscriptionPlanService.get_subscription(group_chat_id)

        if type_subscribe == 'free_trial':
            if chat_subscription.free_trial > 0:
                await callback_query.message.edit_text(
                    text=_("Пробний період вже було використано."),
                    reply_markup=admin_menu_kb.as_markup()
                )
                return None

            self.create_task_subscribe_is_ending(owner_chat_id, group_chat_id, 'free_trial', duration_days)
            await GroupSubscriptionPlanService.update_group_subscription_sql(group_chat_id,
                                                                             free_trial=current_time + duration_days * 86400)
            await callback_query.message.edit_text(
                text=_("Пробний період активовано на {days} днів.").format(days=duration_days),
                reply_markup=admin_menu_kb.as_markup()
            )

        elif type_subscribe == 'auction':
            auction_update_duration = max(chat_subscription.auction_sub_time, current_time) + duration_days * 86400

            if await self.payment_process(owner_chat_id, group_chat_id, 'auction', duration_days):
                return None
            self.create_task_subscribe_is_ending(owner_chat_id, group_chat_id, 'auction', duration_days)
            await GroupSubscriptionPlanService.update_group_subscription_sql(group_chat_id,
                                                                             auction_sub_time=auction_update_duration,
                                                                             auction_paid=True)
            await callback_query.message.edit_text(
                text=_("Підписка на аукціон активована на {days} днів.").format(days=duration_days),
                reply_markup=admin_menu_kb.as_markup()
            )

        elif type_subscribe == 'ads':
            ads_update_duration = max(chat_subscription.ads_sub_time, current_time) + duration_days * 86400
            if await self.payment_process(owner_chat_id, group_chat_id, 'ads', duration_days):
                return None
            self.create_task_subscribe_is_ending(owner_chat_id, group_chat_id, 'ads', duration_days)
            await GroupSubscriptionPlanService.update_group_subscription_sql(group_chat_id,
                                                                             ads_sub_time=ads_update_duration,
                                                                             ads_paid=True)
            await callback_query.message.edit_text(
                text=_("Підписка на оголошення активована на {days} днів.").format(days=duration_days),
                reply_markup=admin_menu_kb.as_markup()
            )


async def not_registered_partner(message: types.Message):
    referral_data = await create_partner_referral_url_and_token(message.from_user.id)
    reg_url = referral_data.get('url')
    await message.answer(text='Щоб стати партнером зареєструйтесь в PayPal по посиланню\n'
                              '{reg_url}'.format(reg_url=reg_url),
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[[back_to_admin_btn]]))


async def monetization(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(text=_('Перевірка партнера...'))
    is_partner = await user_is_merchant_api(call.from_user.id)
    if is_partner:
        user_chats = await GroupChannelService.get_group_by_owner_telegram_id(call.from_user.id)
        kb = await generate_chats_kb(user_chats)
        kb.inline_keyboard.extend([[back_to_admin_btn]])
        await call.message.edit_text(text=_('Вітаю, ви партнер!\n'
                                            '💰 Оберіть групу, у якій бажаєте налаштувати монетизацію'),
                                     reply_markup=kb)
        await state.set_state(FSMAdmin.monetize_chat)
    else:
        referral_data = await create_partner_referral_url_and_token(call.from_user.id)
        reg_url = referral_data.get('url')
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Активувати PayPal', url=reg_url)],
            [back_to_admin_btn]
        ])
        await call.message.edit_text(
            text="Щоб стати партнером зареєструйтесь в PayPal по посиланню або під'єднайте існуючий аккаунт.\n"
                 "Після активації ви отримаєте повідомлення.\n"
                 "<b><a href='{reg_url}'>Активувати PayPal</a></b>".format(reg_url=reg_url),
            reply_markup=kb)


def register_admin_handlers(r: Router):
    r.message.register(admin, Command('admin'))
    r.message.register(not_registered_partner, Command('not_registered_partner'))
    r.callback_query.register(admin, F.data == 'admin')  # Меню адміністратора
    r.callback_query.register(change_user_access, F.data.startswith('access'))  # Блокування/Розблокування користувача
    r.callback_query.register(my_channels_groups, F.data == 'my_admin_channels_groups')  # Пункт меню "Мої групи/канали"
    r.callback_query.register(deny_user_access, F.data == 'deny_user_access')  # Чорний список
    r.callback_query.register(payment_tumbler, F.data.endswith('_payment'))  # Вимкнути/Увімкнути оплату
    r.callback_query.register(SubscriptionGroupHandler().listening,
                              F.data.startswith("subscription_group"))  # Підписка на групу
    r.callback_query.register(add_group, F.data == 'add_group')  # Пункт меню "Підключити групу"
    r.callback_query.register(monetization, F.data == 'monetization')  # Монетизація
    r.callback_query.register(user_chat_menu, FSMAdmin.group_id)
    r.callback_query.register(group_id_settings, FSMAdmin.monetize_chat)
    r.callback_query.register(update_bot_subscription_status, F.data.endswith('sub_update'))
    r.message.register(user_access, FSMAdmin.user_id)
    r.callback_query.register(paid_chat_function, F.data.startswith('paid:'))


register_admin_handlers(router)  # TODO: Замість цього навішати декораторів на функції
