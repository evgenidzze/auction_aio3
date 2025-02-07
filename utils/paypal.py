import json
import time

import aiohttp
from aiohttp import BasicAuth

from utils.config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PARTNER_ID, OWNER_PARTNER_ID, USERNAME_BOT
from utils.create_bot import job_stores

api_domain = 'https://api-m.sandbox.paypal.com'


# api_domain = 'https://api-m.paypal.com'


async def create_order(usd, merchant_id=None):
    """
    Створення замовлення в PayPal на певну суму
    :param merchant_id: id мерчанта(партнера)
    :param usd: сума в доларах
    :return: id замовлення
    """
    url = f"{api_domain}/v2/checkout/orders"
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    f"value": f"{usd}.00"
                },
                "payee": {
                    "merchant_id": merchant_id
                }
            }
        ],
        "application_context": {
            "brand_name": "Auction",
            "landing_page": "BILLING",
            "user_action": "PAY_NOW",
            "return_url": "https://paypal.com"
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data,
                                auth=BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)) as response:
            data = await response.json()
            token = data.get('id')
            return token


async def capture(order_id):
    capture_url = f"{api_domain}/v2/checkout/orders/{order_id}/capture"
    headers = {
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(capture_url, headers=headers, auth=BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)):
            pass


async def get_order_status(order_id):
    headers = {
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{api_domain}/v2/checkout/orders/{order_id}",
                               auth=BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET), headers=headers) as response:
            response_json = await response.json()
            order_status = response_json.get('status')
            return order_status


async def create_partner_referral_url_and_token(user_id) -> dict:
    url = f"{api_domain}/v2/customer/partner-referrals"
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "tracking_id": f"{user_id}",
        "partner_config_override": {
            "return_url": f"https://t.me/{USERNAME_BOT}?start",
            "return_url_description": "Return after onboarding"
        },
        "operations": [{
            "operation": "API_INTEGRATION",
            "api_integration_preference": {
                "rest_api_integration": {
                    "integration_method": "PAYPAL",
                    "integration_type": "THIRD_PARTY",
                    "third_party_details": {
                        "features": ["PAYMENT", "REFUND", "PARTNER_FEE"]
                    }
                }
            }
        }],
        "products": ["EXPRESS_CHECKOUT"],
        "legal_consents": [{"type": "SHARE_DATA_CONSENT", "granted": True}]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, auth=BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
                                json=data) as response:
            res = await response.json()
            links = res.get('links')
            signup_url = links[1].get('href')
            partner_referral_token = signup_url.split('=')[1]
            return {'url': signup_url, 'partner_referral_token': partner_referral_token}


async def user_is_merchant_api(user_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(
                f"{api_domain}/v1/customer/partners/{OWNER_PARTNER_ID}/merchant-integrations?tracking_id={user_id}",
                auth=BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)) as by_user_id_response:
            by_user_id_response = await by_user_id_response.json()
            links = by_user_id_response.get('links')
            if links:
                return True
                # status_by_merchant_id_api_route = links[0].get('href')
                # async with session.get(api_domain + status_by_merchant_id_api_route,
                #                        auth=BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)) as by_merchant_id_response:
                #     by_merchant_id_response = await by_merchant_id_response.json()
                #     for key, val in by_merchant_id_response.items():
                #         print(key, val)
            else:
                return False
