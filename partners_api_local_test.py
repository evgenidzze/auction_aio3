import json
import uuid

import requests
from aiohttp import BasicAuth
from requests.auth import HTTPBasicAuth

from utils.config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET
from utils.paypal import api_domain


def get_access_token():
    url = f"{api_domain}/v1/oauth2/token"
    data = {
        "grant_type": "client_credentials",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(url=url, headers=headers,
                             data=data, auth=HTTPBasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET))
    data = response.json()
    access_token = data.get("access_token")
    return access_token


def create_partner_referral():
    url = f"{api_domain}/v2/customer/partner-referrals"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_access_token()}",
    }
    data = {
        "tracking_id": "397875584",
        "partner_config_override": {
            "return_url": "https://t.me/Shopogolic2DayBot?start",
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
        "legal_consents": [{"type": "SHARE_DATA_CONSENT", "granted": True}],
        "scopes": [
            "profile",
            "email",
            "https://uri.paypal.com/services/payments/realtimepayment",
            "https://uri.paypal.com/services/payments/partnerfee",
            "https://uri.paypal.com/services/payments/refund",
            "https://uri.paypal.com/services/payments/payment/authcapture",

        ]
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.json())
    return response.json()



def create_order():
    access_token = get_access_token()
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
                    "value": "13.00"
                },
                "payee": {
                    "merchant_id": "77HX8L3GT2JA2"
                },
                # "partner_fee_details": {
                #     "amount": {
                #         "currency_code": "USD",
                #         "value": "5.00"
                #     }
                # }
            }
        ],
        "application_context": {
            "brand_name": "Your Brand Name",
            "landing_page": "BILLING",
            "user_action": "PAY_NOW",
            "return_url": "https://www.paypal.com",
            "cancel_url": "https://www.paypal.com"
        }
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.json())


def capture(order_id):
    access_token = get_access_token()
    capture_url = f"{api_domain}/v2/checkout/orders/{order_id}/capture"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.post(url=capture_url, headers=headers)
    print(response.json())


def register_webhook(domain):
    url = f"{api_domain}/v1/notifications/webhooks"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_access_token()}",
    }
    data = {
        "url": f"https://{domain}/webhook",  # Змініть на свій реальний URL
        "event_types": [
            {"name": "MERCHANT.ONBOARDING.COMPLETED"},
            {"name": "PAYMENT.SALE.COMPLETED"}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()


# create_order()
# capture('8RL015768U298732X')
# register_webhook('by2x7alhot.loclx.io')
# create_partner_referral()
