from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, KeyboardBuilder
from utils.create_bot import _

# from create_bot import _

eng_btn = InlineKeyboardButton(text='🇬🇧 English', callback_data='en')
ua_btn = InlineKeyboardButton(text='🇺🇦 Українська', callback_data='uk')
language_kb = InlineKeyboardMarkup(inline_keyboard=[[ua_btn], [eng_btn]])
back_to_main_btn = InlineKeyboardButton(text='« Назад', callback_data='main_menu')

my_auctions_btn = InlineKeyboardButton(text='🗃 Мої лоти', callback_data='my_auctions')
help_btn = InlineKeyboardButton(text='🆘 Допомога', callback_data='help')
auction_btn = InlineKeyboardButton(text='🏷 Аукціон', callback_data='auction')
create_auction_btn = InlineKeyboardButton(text='➕ Створити аукціон', callback_data='create_auction')
anti_sniper_btn = InlineKeyboardButton(text='⏱ Антиснайпер', callback_data='anti_sniper')
# chats_btn = InlineKeyboardButton(text='💬 Повідомлення', callback_data='chats')
create_advert_btn = InlineKeyboardButton(text='📣 Оголошення', callback_data='ad_menu')
group_channels_btn = InlineKeyboardButton(text='👥 Групи та канали', callback_data='groups_and_channels')
manage_panel_btn = InlineKeyboardButton(text='🔧 Панель керування', callback_data='create_ad')
pro_sub_btn = InlineKeyboardButton(text='💎 Pro-підписка', callback_data='create_ad')
main_kb = InlineKeyboardMarkup(
    inline_keyboard=[[auction_btn, create_advert_btn], [group_channels_btn], [pro_sub_btn],
                     [help_btn]])

my_ads_btn = InlineKeyboardButton(text='📋 Мої оголошення', callback_data='my_ads')
create_advert_btn = InlineKeyboardButton(text='📣 Створити голошення', callback_data='create_ad')
add_menu_kb = InlineKeyboardMarkup(inline_keyboard=[[create_advert_btn], [my_ads_btn], [back_to_main_btn]])

back_to_main_btn = InlineKeyboardButton(text='« Назад', callback_data='main_menu')
# back_to_messages = InlineKeyboardButton(text='« Назад', callback_data='chats')
back_to_auction_btn = InlineKeyboardButton(text='« Назад', callback_data='auction')

auction_kb = InlineKeyboardMarkup(
    inline_keyboard=[[create_auction_btn], [my_auctions_btn], [anti_sniper_btn], [back_to_main_btn]])

back_to_main_kb = InlineKeyboardMarkup(inline_keyboard=[[back_to_main_btn]])

cancel_btn = InlineKeyboardButton(text='❌ Відміна', callback_data='main_menu')
cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[cancel_btn]])

tw_four_btn = InlineKeyboardButton(text='24 години', callback_data='24')
forty_eight_btn = InlineKeyboardButton(text='48 годин', callback_data='48')
seven_days = InlineKeyboardButton(text='7 днів', callback_data='168')
lot_time_kb = InlineKeyboardMarkup(inline_keyboard=[[tw_four_btn, forty_eight_btn, seven_days]])

change_media_btn = InlineKeyboardButton(text='🎞 Змінити медіа', callback_data='change_media')
change_description_btn = InlineKeyboardButton(text='🔤 Змінити опис', callback_data='change_desc')
change_start_price_btn = InlineKeyboardButton(text='💰 Змінити стартову ціну', callback_data='change_start_price')
change_duration_btn = InlineKeyboardButton(text='⏳ Змінити тривалість лоту', callback_data='change_lot_time')
change_steps_btn = InlineKeyboardButton(text='🪙 Змінити кроки ставки', callback_data='change_price_steps')
change_city_btn = InlineKeyboardButton(text='🏙 Змінити місто', callback_data='change_city')
publish_btn = InlineKeyboardButton(text='✅ Опублікувати', callback_data='publish_lot')
publish_adv_btn = InlineKeyboardButton(text='✅ Опублікувати', callback_data='publish_adv')
ready_to_publish_kb = InlineKeyboardMarkup(inline_keyboard=
                                           [[change_media_btn], [change_description_btn], [change_start_price_btn],
                                            [change_duration_btn], [change_steps_btn],
                                            [change_city_btn]])
ready_to_publish_ad_kb = InlineKeyboardMarkup(
    inline_keyboard=[[change_media_btn], [change_description_btn], [change_city_btn]])

change_desc_exist_lot_btn = InlineKeyboardButton(text='🔤 Змінити опис',
                                                 callback_data='change_desc_exist_lot')
delete_lot_btn = InlineKeyboardButton(text='🗑 Видалити лот', callback_data='delete_lot')
delete_lot_kb = InlineKeyboardMarkup(inline_keyboard=[[change_desc_exist_lot_btn], [delete_lot_btn], [
    InlineKeyboardButton(text='« Назад', callback_data='my_auctions')]])

# change_desc_exist_ad_btn = InlineKeyboardButton(text='🔤 Змінити опис', callback_data='change_desc_exist_ad')
delete_ad_btn = InlineKeyboardButton(text='🗑 Видалити оголошення', callback_data='delete_ad')
delete_ad_kb = InlineKeyboardMarkup(inline_keyboard=[[delete_ad_btn], [
    InlineKeyboardButton(text='« Назад', callback_data='my_ads')]])

back_to_ready_btn = InlineKeyboardButton(text='« Назад', callback_data='back_to_ready')
back_to_ready_kb = InlineKeyboardMarkup(inline_keyboard=[[back_to_ready_btn]])

back_to_ready_ad_btn = InlineKeyboardButton(text='« Назад', callback_data='back_to_ready_ad')
back_to_ready_ad_kb = InlineKeyboardMarkup(inline_keyboard=[[back_to_ready_ad_btn]])

gbr_btn = InlineKeyboardButton(text='🇬🇧 GBR', callback_data='GBR')
uah_btn = InlineKeyboardButton(text='🇺🇦 UAH', callback_data='UAH')
usd_btn = InlineKeyboardButton(text='🇺🇸 USD', callback_data='USD')
currency_kb = InlineKeyboardMarkup(inline_keyboard=[[gbr_btn], [uah_btn], [usd_btn], [cancel_btn]])

cancel_to_start_btn = InlineKeyboardButton(text='« Назад', callback_data='start')
cancel_to_start_kb = InlineKeyboardMarkup(inline_keyboard=[[cancel_to_start_btn]])

decline_lot_btn = InlineKeyboardButton(text='❌ Відхилити')
accept_lot_btn = InlineKeyboardButton(text='✅ Підтвердити')

decline_lot_deletion_btn = InlineKeyboardButton(text='❌ Відхилити')
accept_lot_deletion_btn = InlineKeyboardButton(text='✅ Підтвердити')

anti_5_btn = InlineKeyboardButton(text='5хв', callback_data='5')
anti_10_btn = InlineKeyboardButton(text='10хв', callback_data='10')
anti_15_btn = InlineKeyboardButton(text='15хв', callback_data='15')
anti_kb = InlineKeyboardMarkup(inline_keyboard=[[anti_5_btn, anti_10_btn, anti_15_btn], [back_to_auction_btn]])

# questions_btn = InlineKeyboardButton(text='❔ Запитання', callback_data='questions')
# answers_btn = InlineKeyboardButton(text='💬 Відповіді', callback_data='answers')
# quest_answ_kb = InlineKeyboardMarkup(inline_keyboard=[[answers_btn, questions_btn], [back_to_main_btn]])

# delete_answer_btn = InlineKeyboardButton(text='🗑 Видалити', callback_data='read')
# back_to_answers_btn = InlineKeyboardButton(text='« Назад', callback_data='answers')
# back_to_answers_kb = InlineKeyboardMarkup(inline_keyboard=[[delete_answer_btn], [back_to_answers_btn]])
# back_to_questions = InlineKeyboardButton(text='« Назад', callback_data='questions')
# delete_question_btn = InlineKeyboardButton(text='🗑 Видалити', callback_data='delete_question')
# back_to_questions_kb = InlineKeyboardMarkup(inline_keyboard=[[delete_question_btn], [back_to_questions]])

black_list_btn = InlineKeyboardButton(text='🚫 Чорний список', callback_data='deny_user_access')
payment_on_btn = InlineKeyboardButton(text='Увімкнути оплату', callback_data='on_payment')
payment_of_btn = InlineKeyboardButton(text='Вимкнути оплату', callback_data='off_payment')
reject_to_admin_btn = InlineKeyboardButton(text='❌Відміна', callback_data='admin')
back_to_admin_btn = InlineKeyboardButton(text='« Назад', callback_data='admin')
back_to_group_manage_btn = InlineKeyboardButton(text="« Назад", callback_data="group_manage")
groups_manage_btn = InlineKeyboardButton(text='Керування групами', callback_data='group_manage')
add_group = InlineKeyboardButton(text='🔌 Підключити групу', callback_data='add_group')
monetization = InlineKeyboardButton(text='💰 Монетизація', callback_data='monetization')

unblock_user_btn = InlineKeyboardButton(text='🔑 Розблокувати', callback_data='access_{user_id}_unblock')
block_user_btn = InlineKeyboardButton(text='🚫 Заблокувати', callback_data='access_{user_id}_block')
my_channels_groups = InlineKeyboardButton(text='Мої групи/канали', callback_data='my_channels_groups')

admin_menu_kb = InlineKeyboardBuilder()
admin_menu_kb.row(my_channels_groups, add_group).row(monetization, black_list_btn)

adv_30_days = InlineKeyboardButton(text='Оформити на 30 днів', callback_data='2592000')
subscribe_adv_kb = InlineKeyboardMarkup(inline_keyboard=[[adv_30_days], [cancel_btn]])

back_show_lot_btn = InlineKeyboardButton(text='« Назад', callback_data='show_lot')
back_show_lot_kb = InlineKeyboardMarkup(inline_keyboard=[[back_show_lot_btn]])
back_show_ad_btn = InlineKeyboardButton(text='« Назад', callback_data='show_ad')
back_show_ad_kb = InlineKeyboardMarkup(inline_keyboard=[[back_show_ad_btn]])

one_btn = InlineKeyboardButton(text='1', callback_data='1')
two_btn = InlineKeyboardButton(text='2', callback_data='2')
three_btn = InlineKeyboardButton(text='3', callback_data='3')
repost_count_kb = InlineKeyboardMarkup(inline_keyboard=[[one_btn], [two_btn], [three_btn], [cancel_btn]])

yes_btn = InlineKeyboardButton(text='Так', callback_data='yes')
no_btn = InlineKeyboardButton(text='Ні', callback_data='no')
yes_no_kb = InlineKeyboardMarkup(inline_keyboard=[[yes_btn], [no_btn], [cancel_btn]])

reset_to_auction_menu_btn = InlineKeyboardButton(text='❌ Відміна', callback_data='auction')
reset_to_auction_menu_kb = InlineKeyboardMarkup(inline_keyboard=[[reset_to_auction_menu_btn]])

reset_to_ad_menu_btn = InlineKeyboardButton(text='❌ Відміна', callback_data='ad_menu')
back_to_ad_menu_btn = InlineKeyboardButton(text='« Назад', callback_data='ad_menu')
reset_to_ad_menu_kb = InlineKeyboardMarkup(inline_keyboard=[[reset_to_ad_menu_btn]])

other_channels_groups = InlineKeyboardButton(text='Інші групи/канали', callback_data='other_channels_groups')
group_channels_kb = InlineKeyboardMarkup(inline_keyboard=[[other_channels_groups], [back_to_main_btn]])

back_group_channels_btn = InlineKeyboardButton(text='« Назад', callback_data='groups_and_channels')
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
