## Налаштування середовища

Перед запуском проєкту необхідно налаштувати середовище, створивши файли конфігурації з необхідними змінними оточення.

### Підготовка середовища

1. У кореневій директорії проєкту створіть папку `env`:
   ```bash
   mkdir env
2. У папці `env` створіть файл:
   - для Docker
      ```bash
      touch env/.docker.env
   - для локального запуску
       ```bash
      touch env/.local.env
       ```
3. Заповніть файл середовища потрібними змінними:
   ```bash
   DB_HOST=your_db_host
   PORT=3306
   DB_USER=your_db_user
   BOT_TOKEN=your_bot_token
   MYSQL_ROOT_PASSWORD=your_mysql_root_password
   MYSQL_DATABASE=your_database_name
   PAYPAL_CLIENT_ID=your_paypal_client_id
   PAYPAL_CLIENT_SECRET=your_paypal_client_secret
   REDIS_HOST=your_redis_host
   AUCTION_CHANNEL=your_auction_channel_id
   ADVERT_CHANNEL=your_advert_channel_id
   REDIS_PASS=your_redis_password
   GALLERY_CHANNEL=your_gallery_channel_id
   PARTNER_ID=your_paypal_partner_id
   DEV_ID=your_telegram_id

### Запуск проєкту
```bash
docker compose up -d --build
```