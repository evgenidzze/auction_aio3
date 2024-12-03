import json
import time

import aiohttp
from aiohttp import BasicAuth

from utils.config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET
from utils.create_bot import job_stores

api_domain = 'https://api-m.sandbox.paypal.com'


# api_domain = 'https://api-m.paypal.com'


async def get_access_token():
    redis_obj = job_stores.get('default')
    access_token_expires = redis_obj.redis.get('access_token')
    if access_token_expires:
        access_token_expires = json.loads(access_token_expires)
        expires_in = access_token_expires.get('expires_in', 0)
    else:
        expires_in = 0

    if expires_in <= time.time():
        url = f"{api_domain}/v1/oauth2/token"
        data = {
            "grant_type": "client_credentials"
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, auth=BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET), headers=headers,
                                    data=data) as response:
                data = await response.json()
                expires_in = data.get('expires_in')
                access_token = data.get("access_token")
                redis_obj.redis.set(name='access_token',
                                    value=json.dumps({'token': access_token, 'expires_in': time.time() + expires_in}))
                return access_token
    else:
        access_token = access_token_expires.get('token')
        return access_token


async def create_order(usd):
    access_token = await get_access_token()
    url = f"{api_domain}/v2/checkout/orders"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    data = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    f"value": f"{usd}.00"
                },

            }
        ],
        "application_context": {
            "brand_name": "Your Brand Name",
            "landing_page": "BILLING",
            "user_action": "PAY_NOW",
            "return_url": "https://paypal.com"
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            data = await response.json()
            token = data.get('id')
            return token


async def capture(order_id):
    access_token = await get_access_token()
    capture_url = f"{api_domain}/v2/checkout/orders/{order_id}/capture"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(capture_url, headers=headers):
            pass


async def get_payment_status(order_id):
    access_token = await get_access_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{api_domain}/v2/checkout/orders/{order_id}", headers=headers) as response:
            response_json = await response.json()
            order_status = response_json.get('status')
            return order_status
