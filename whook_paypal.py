from fastapi import FastAPI, Request

from database.db_manage import update_user_sql
from utils.create_bot import bot

app = FastAPI()


@app.post("/webhook")
async def paypal_webhook(request: Request):
    payload = await request.json()
    event_type = payload.get("event_type")
    resource = payload.get("resource", {})
    print(payload)
    if event_type == "MERCHANT.ONBOARDING.COMPLETED":
        merchant_id = resource.get("merchant_id")
        email = resource.get("email")
        user_id = resource.get("tracking_id")
        await update_user_sql(telegram_id=user_id, merchant_id=merchant_id)
        await bot.send_message(chat_id=user_id, text="Вітаю ваш PayPal під'єднано до партнерської програми бота!.")
        print(f"Merchant {merchant_id} completed onboarding with email {email}")
        return {"status": "processed"}
    return {"status": "ignored"}

