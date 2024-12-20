import logging

import aiohttp
from aiohttp import BasicAuth
from fastapi import FastAPI, Request

from database.db_manage import update_user_sql
from keyboards.admin_kb import admin_menu_kb
from utils.config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET
from utils.create_bot import bot

app = FastAPI()


@app.post("/webhook")
async def paypal_webhook(request: Request):
    payload = await request.json()
    event_type = payload.get("event_type")
    resource = payload.get("resource", {})
    if event_type == "MERCHANT.ONBOARDING.COMPLETED":
        merchant_id = resource.get("merchant_id")
        email = resource.get("email")
        user_id = await get_tracking_id_paypal(resource)
        await update_user_sql(telegram_id=user_id, merchant_id=merchant_id)
        try:
            await bot.send_message(chat_id=user_id, text="Вітаю ваш PayPal під'єднано до партнерської програми бота!", reply_markup=admin_menu_kb.as_markup())
        except Exception as err:
            logging.info(err)
        return {"status": "processed"}
    return {"status": "ignored"}


async def get_tracking_id_paypal(resource):
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
