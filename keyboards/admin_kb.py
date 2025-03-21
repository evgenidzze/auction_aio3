from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.utils import payment_link_generate, GroupTypeSubscription

back_to_admin_btn = InlineKeyboardButton(text='« Назад', callback_data='admin')
back_to_group_manage_btn = InlineKeyboardButton(text="« Назад", callback_data="group_manage")
unblock_user_btn = InlineKeyboardButton(text='🔑 Розблокувати', callback_data='access_{user_id}_unblock')
block_user_btn = InlineKeyboardButton(text='🚫 Заблокувати', callback_data='access_{user_id}_block')
admin_menu_kb = InlineKeyboardBuilder()
back_my_channels_groups = InlineKeyboardButton(text='« Назад', callback_data='my_admin_channels_groups')
back_my_channels_groups_kb = InlineKeyboardMarkup(inline_keyboard=[[back_my_channels_groups]])
black_list_btn = InlineKeyboardButton(text='🚫 Чорний список', callback_data='deny_user_access')
payment_on_btn = InlineKeyboardButton(text='Увімкнути оплату', callback_data='on_payment')
payment_of_btn = InlineKeyboardButton(text='Вимкнути оплату', callback_data='off_payment')
groups_manage_btn = InlineKeyboardButton(text='Керування групами', callback_data='group_manage')
add_group_kb = InlineKeyboardButton(text='🔌 Підключення', callback_data='add_group')
monetization = InlineKeyboardButton(text='💰 Монетизація', callback_data='monetization')
back_to_monetization = InlineKeyboardButton(text='« Назад', callback_data='monetization')

my_channels_groups_btn = InlineKeyboardButton(text='⚙️ Функціонал', callback_data='my_admin_channels_groups')

admin_menu_kb.row(my_channels_groups_btn, add_group_kb).row(monetization, black_list_btn)
back_to_admin_kb = InlineKeyboardMarkup(inline_keyboard=[[back_to_admin_btn]])


async def group_payment_kb(auction_token, ads_token, group_id, free_trial):
    """
    Генерує кнопки для оплати групової підписки
    """
    builder = InlineKeyboardBuilder()
    if auction_token:
        auction_payment_url = await payment_link_generate(auction_token)
        builder.button(text='🔑 Підписка на аукціон (1 місяць)', url=auction_payment_url)
    if ads_token:
        ads_payment_url = await payment_link_generate(ads_token)
        builder.button(text='🔑 Підписка на оголошення (1 місяць)', url=ads_payment_url)
    if free_trial == 0:
        builder.button(text='🔑 Пробний період (14 днів)',
                       callback_data=f'subscription_group:{GroupTypeSubscription.FREE_TRIAL}:14:{group_id}')
    builder.add(back_my_channels_groups)
    builder.adjust(1)

    return builder.as_markup()
