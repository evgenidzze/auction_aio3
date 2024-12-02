from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.create_bot import _


pro_sub_btn = InlineKeyboardButton(text='💎 Pro-підписка', callback_data='create_ad')
create_advert_btn = InlineKeyboardButton(text='📣 Оголошення', callback_data='ad_menu')
auction_btn = InlineKeyboardButton(text='🏷 Аукціон', callback_data='auction')
help_btn = InlineKeyboardButton(text='🆘 Допомога', callback_data='help')
group_channels_btn = InlineKeyboardButton(text='👥 Групи та канали', callback_data='groups_and_channels')
back_to_main_btn = InlineKeyboardButton(text='« Назад', callback_data='main_menu')
main_kb = InlineKeyboardMarkup(
    inline_keyboard=[[auction_btn, create_advert_btn], [group_channels_btn], [pro_sub_btn],
                     [help_btn]])
reject_to_admin_btn = InlineKeyboardButton(text='❌Відміна', callback_data='admin')
back_to_admin_btn = InlineKeyboardButton(text='« Назад', callback_data='admin')
back_to_group_manage_btn = InlineKeyboardButton(text="« Назад", callback_data="group_manage")
unblock_user_btn = InlineKeyboardButton(text='🔑 Розблокувати', callback_data='access_{user_id}_unblock')
block_user_btn = InlineKeyboardButton(text='🚫 Заблокувати', callback_data='access_{user_id}_block')
admin_menu_kb = InlineKeyboardBuilder()
back_my_channels_groups = InlineKeyboardButton(text='« Назад', callback_data='my_channels_groups')
back_my_channels_groups_kb = InlineKeyboardMarkup(inline_keyboard=[[back_my_channels_groups]])


async def activate_ad_auction_kb(auction_token, ads_token, user_chat_id, back_btn=back_to_main_btn):
    from utils.utils import payment_link_generate
    auction_payment_url = await payment_link_generate(auction_token)
    ads_payment_url = await payment_link_generate(ads_token)
    builder = InlineKeyboardBuilder()
    update_status_btn = InlineKeyboardButton(text=_('🔄 Оновити статус'),
                                             callback_data=f'{user_chat_id}:{auction_token},{ads_token}:sub_update')
    builder.button(text='Активувати аукціон', url=auction_payment_url).button(
        text='Активувати оголошення', url=ads_payment_url).add(update_status_btn).add(back_btn)
    builder.adjust(2)
    return builder.as_markup()
