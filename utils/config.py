import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
DB_PASS = os.environ.get('DB_PASS')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_HOST = os.environ.get('DB_HOST')
BOT_TOKEN = os.environ.get('BOT_TOKEN')
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET')
PORT = os.environ.get('PORT')
REDIS_HOST = os.environ.get('REDIS_HOST')
ADVERT_CHANNEL = os.environ.get('ADVERT_CHANNEL')
AUCTION_CHANNEL = os.environ.get('AUCTION_CHANNEL')
REDIS_PASS = os.environ.get('REDIS_PASS')
GALLERY_CHANNEL = os.environ.get('GALLERY_CHANNEL')
PARTNER_ID = os.environ.get('PARTNER_ID')
WORKDIR = Path(__file__).parent.parent