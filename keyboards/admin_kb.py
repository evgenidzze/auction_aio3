from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.create_bot import _

reject_to_admin_btn = InlineKeyboardButton(text='❌Відміна', callback_data='admin')
back_to_admin_btn = InlineKeyboardButton(text='« Назад', callback_data='admin')
back_to_group_manage_btn = InlineKeyboardButton(text="« Назад", callback_data="group_manage")
unblock_user_btn = InlineKeyboardButton(text='🔑 Розблокувати', callback_data='access_{user_id}_unblock')
block_user_btn = InlineKeyboardButton(text='🚫 Заблокувати', callback_data='access_{user_id}_block')
admin_menu_kb = InlineKeyboardBuilder()
back_my_channels_groups = InlineKeyboardButton(text='« Назад', callback_data='my_channels_groups')
back_my_channels_groups_kb = InlineKeyboardMarkup(inline_keyboard=[[back_my_channels_groups]])
black_list_btn = InlineKeyboardButton(text='🚫 Чорний список', callback_data='deny_user_access')
payment_on_btn = InlineKeyboardButton(text='Увімкнути оплату', callback_data='on_payment')
payment_of_btn = InlineKeyboardButton(text='Вимкнути оплату', callback_data='off_payment')
groups_manage_btn = InlineKeyboardButton(text='Керування групами', callback_data='group_manage')
add_group = InlineKeyboardButton(text='🔌 Підключити групу', callback_data='add_group')
monetization = InlineKeyboardButton(text='💰 Монетизація', callback_data='monetization')

my_channels_groups = InlineKeyboardButton(text='Мої групи/канали', callback_data='my_channels_groups')

admin_menu_kb.row(my_channels_groups, add_group).row(monetization, black_list_btn)


async def activate_ad_auction_kb(auction_token, ads_token, user_chat_id, back_btn):
    from utils.utils import payment_link_generate
    auction_payment_url = await payment_link_generate(auction_token)
    ads_payment_url = await payment_link_generate(ads_token)
    builder = InlineKeyboardBuilder()
    update_status_btn = InlineKeyboardButton(text=_('🔄 Оновити статус'),
                                             callback_data=f'{user_chat_id}:{auction_token},{ads_token}:sub_update')
    (builder.button(text='Активувати аукціон', url=auction_payment_url).
     button(text='Активувати оголошення', url=ads_payment_url).add(update_status_btn).add(back_btn))
    builder.adjust(2)
    return builder.as_markup()
