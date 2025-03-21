from typing import Union

import aiohttp
from aiohttp import BasicAuth

from utils.config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PARTNER_ID, OWNER_PARTNER_ID, USERNAME_BOT
from utils.core_types import ClientProductCategory, AdminProductCategory

api_domain = 'https://api-m.sandbox.paypal.com'


# api_domain = 'https://api-m.paypal.com'


async def create_order(usd, payer_tg_id, category: Union[ClientProductCategory, AdminProductCategory],
                       merchant_id=None, group_id=None):
    """
    Створення замовлення в PayPal на певну суму
    """
    url = f"{api_domain}/v2/checkout/orders"
    headers = {"Content-Type": "application/json"}
    total_amount = float(usd)
    fee_amount = round(total_amount * 0.2, 2)
    data = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "payee": {
                    "merchant_id": merchant_id
                },
                "amount": {
                    "currency_code": "USD",
                    "value": total_amount,
                    "breakdown": {
                        "item_total": {
                            "currency_code": "USD",
                            "value": total_amount
                        },
                    }
                },
                'custom_id': f'{payer_tg_id}:{category}:{group_id}',
            }

        ],
        "application_context": {
            "brand_name": "Auction",
            "landing_page": "BILLING",
            "user_action": "PAY_NOW",
            "return_url": "https://paypal.com",
            "shipping_preference": "NO_SHIPPING"
        },
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data,
                                auth=BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)) as response:
            data = await response.json()
            token = data.get('id')
            return token


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
                return by_user_id_response.get('merchant_id')
            else:
                return None
