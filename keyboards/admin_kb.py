from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.create_bot import _
from utils.utils import payment_link_generate


def create_subscription_group_buttons_kb(chat_id, is_trial=False):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔑 Пробний період (14 днів)',
                              callback_data=f'subscription_group:free_trial:14:{chat_id}')] if is_trial else [],
        [InlineKeyboardButton(text='🔑 Підписка на аукціон (1 місяць)',
                              callback_data=f'subscription_group:auction:30:{chat_id}')],
        [InlineKeyboardButton(text='🔑 Підписка на оголошення (1 місяць)',
                              callback_data=f'subscription_group:ads:30:{chat_id}')],
    ])


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


async def activate_ad_auction_kb(auction_token, ads_token, group_id, back_btn, free_trial):
    builder = InlineKeyboardBuilder()

    if auction_token or ads_token:
        if auction_token:
            auction_payment_url = await payment_link_generate(auction_token)
            builder.button(text='Активувати аукціон', url=auction_payment_url)
        if ads_token:
            ads_payment_url = await payment_link_generate(ads_token)
            builder.button(text='Активувати оголошення', url=ads_payment_url)
        if free_trial == 0:
            builder.button(text='🔑 Пробний період (14 днів)',
                           callback_data=f'subscription_group:free_trial:14:{group_id}')
        builder.button(text=_('🔄 Оновити статус'),
                       callback_data=f'{group_id}:{auction_token},{ads_token}:sub_update')
    builder.add(back_btn)
    builder.adjust(2)
    return builder.as_markup()
