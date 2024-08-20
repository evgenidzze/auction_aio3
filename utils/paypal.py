import aiohttp
from aiohttp import BasicAuth

from utils.config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET


async def get_access_token():
    url = "https://api-m.paypal.com/v1/oauth2/token"  # Ось тут додано '/v1/oauth2/token'
    data = {
        "grant_type": "client_credentials"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, auth=BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET), headers=headers, data=data) as response:
            data = await response.json()
            access_token = data.get("access_token")
            return access_token


async def create_payment_token(usd):
    access_token = await get_access_token()
    url = "https://api-m.paypal.com/v2/checkout/orders"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    data = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "RUB",
                    f"value": f"{usd}.00"
                }
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
    capture_url = f"https://api-m.paypal.com/v2/checkout/orders/{order_id}/capture"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(capture_url, headers=headers):
            pass


async def get_status(order_id):
    access_token = await get_access_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api-m.paypal.com/v2/checkout/orders/{order_id}", headers=headers) as response:
            response_json = await response.json()
            order_status = response_json.get('status')
            return order_status
