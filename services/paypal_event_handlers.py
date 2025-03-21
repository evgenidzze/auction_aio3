import logging
import pprint
import aiohttp
from aiohttp import BasicAuth
from database.services.user_service import UserService
from keyboards.admin_kb import admin_menu_kb
from utils.config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET
from utils.create_bot import bot


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
        async with session.post(capture_link, headers=headers, auth=BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)) as response:
            response_json = await response.json()
            pp = pprint.PrettyPrinter(indent=2)
            purchase_units = response_json.get('purchase_units', [{}])
            captures = purchase_units[0].get('payments', {}).get('captures', [{}])
            user_id = captures[0].get('custom_id')
            print(user_id)
            # await UserGroupService.update_user_group(call.from_user.id, group_id=call.data, advert_subscribe_time=604800 + time.time())


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
