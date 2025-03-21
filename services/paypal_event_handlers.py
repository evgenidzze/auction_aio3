import logging
import pprint
import time

import aiohttp
from aiohttp import BasicAuth

from database.services.group_subscription_plan_service import GroupSubscriptionPlanService
from database.services.user_group_service import UserGroupService
from database.services.user_service import UserService
from handlers.admin import SubscriptionGroupHandler
from keyboards.admin_kb import admin_menu_kb
from utils.config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET
from utils.core_types import GroupTypeSubscription, AdminProductCategory, ClientProductCategory
from utils.create_bot import bot, _


async def handle_onboarding_completed(resource):
    merchant_id = resource.get("merchant_id")
    user_id = await get_tracking_id_paypal(resource)
    await UserService.update_user_sql(telegram_id=user_id, merchant_id=merchant_id)
    try:
        await bot.send_message(chat_id=user_id, text="🤝 Вітаю ваш PayPal під'єднано до партнерської програми бота!",
                               reply_markup=admin_menu_kb.as_markup())
    except Exception as err:
        logging.info(err)
    return {"status": "processed"}


async def handle_payment_completed(resource):
    links = resource.get('links')
    capture_link = links[2].get('href')
    headers = {
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(capture_link, headers=headers,
                                auth=BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)) as response:
            response_json = await response.json()
            pp = pprint.PrettyPrinter(indent=2)
            purchase_units = response_json.get('purchase_units', [{}])
            captures = purchase_units[0].get('payments', {}).get('captures', [{}])
            custom_id = captures[0].get('custom_id').split(':')
            user_id, category, group_id = custom_id[0], custom_id[1], custom_id[2]
            type_subscription = await GroupTypeSubscription.get_by_product_category(category)
            if category in AdminProductCategory.__members__.values():  # якщо оплата за групу
                chat_subscription = await GroupSubscriptionPlanService.get_subscription(group_id)
                current_time = time.time()
                if category == AdminProductCategory.AUCTION:
                    auction_update_duration = max(chat_subscription.auction_sub_time, current_time) + 30 * 86400
                    await GroupSubscriptionPlanService.update_group_subscription_sql(group_id,
                                                                                     auction_sub_time=auction_update_duration,
                                                                                     auction_paid=True)
                    text = _("Підписка на аукціон активована на {days} днів.").format(days=30),
                elif category == AdminProductCategory.ADVERTISEMENT:
                    ads_update_duration = max(chat_subscription.ads_sub_time, current_time) + 30 * 86400
                    await GroupSubscriptionPlanService.update_group_subscription_sql(group_id,
                                                                                     ads_sub_time=ads_update_duration,
                                                                                     ads_paid=True)
                    text = _("Підписка на оголошення активована на {days} днів.").format(days=30),

                await SubscriptionGroupHandler.create_task_subscribe_is_ending(owner_chat_id=user_id,
                                                                               group_chat_id=group_id,
                                                                               type_subscription=type_subscription,
                                                                               duration_days=30)
                await bot.send_message(chat_id=user_id, text=text, reply_markup=admin_menu_kb.as_markup())
            else:
                if category == ClientProductCategory.AUCTION:
                    await UserGroupService.update_user_group(user_id, group_id=group_id,
                                                             auction_subscribe_time=604800 + time.time())
                    text = _("Підписка на аукціон активована на {days} днів.").format(days=30),
                elif category == ClientProductCategory.ADVERTISEMENT:
                    await UserGroupService.update_user_group(user_id, group_id=group_id,
                                                             advert_subscribe_time=604800 + time.time())
                    text = _("Підписка на оголошення активована на {days} днів.").format(days=30),

                await bot.send_message(chat_id=user_id, text=text, reply_markup=admin_menu_kb.as_markup())


async def get_tracking_id_paypal(resource):
    """
    The same as user id.
    """
    links = resource.get('links')
    href = links[0].get('href')
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(href, auth=BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)) as response:
                data = await response.json()
                tracking_id = data.get('tracking_id')
                return tracking_id
        except Exception as err:
            logging.info(err)
