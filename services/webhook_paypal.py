import logging

import requests
from fastapi import FastAPI, Request
from requests.auth import HTTPBasicAuth

from services.paypal_event_handlers import handle_onboarding_completed, handle_payment_completed
from utils.config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET
from utils.paypal import api_domain


def create_webhook(url):
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "url": f"{url}/webhook",
        "event_types": [
            {
                'name': '*'
            }
        ]
    }
    res = requests.post(f"{api_domain}/v1/notifications/webhooks",
                        auth=HTTPBasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET), headers=headers, json=data)
    res_json = res.json()
    print(res_json)


def check_webhook():
    # create_webhook('https://3146-62-80-185-106.ngrok-free.app')
    headers = {
        "Content-Type": "application/json",
    }
    res = requests.get(f"{api_domain}/v1/notifications/webhooks",
                       auth=HTTPBasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET), headers=headers)
    res_json = res.json()
    for w in res_json.get('webhooks'):
        logging.info(w.get('url'))


app = FastAPI(on_startup=check_webhook())

EVENT_HANDLERS = {
    "MERCHANT.ONBOARDING.COMPLETED": handle_onboarding_completed,
    "CHECKOUT.ORDER.APPROVED": handle_payment_completed,
}


@app.post("/webhook")
async def paypal_webhook(request: Request):
    payload = await request.json()
    logging.info(payload)
    event_type = payload.get("event_type")
    resource = payload.get("resource", {})
    handler = EVENT_HANDLERS.get(event_type)
    if handler:
        await handler(resource)
    else:
        return {"status": f"Event `{event_type}` ignored"}
