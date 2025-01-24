## Налаштування середовища

Перед запуском проєкту необхідно налаштувати середовище, створивши файли конфігурації з необхідними змінними оточення.

### Підготовка середовища


1. В головній директорії створіть файл:
    - для Docker
       ```bash
       touch .env
    - для локального запуску
        ```bash
       touch .local.env
        ```
2. Заповніть файл середовища потрібними змінними:
   ```bash
   BOT_TOKEN=your_bot_token
   DB_HOST=your_db_host
   DB_PORT=3306
   DB_USER=your_db_user
   MYSQL_ROOT_PASSWORD=your_mysql_root_password
   MYSQL_DATABASE=your_database_name
   PAYPAL_CLIENT_ID=your_paypal_client_id
   PAYPAL_CLIENT_SECRET=your_paypal_client_secret
   REDIS_HOST=your_redis_host
   REDIS_PASS=your_redis_password
   GALLERY_CHANNEL=your_gallery_channel_id
   PARTNER_ID=your_paypal_partner_id
   DEV_ID=your_telegram_id
   USERNAME_BOT=your_bot_username
   ```

### Налаштування PayPal для тестування

1. Зареєструватись на https://developer.paypal.com
2. Створити App (Platform type: Platform) та підставити в env:<br>
<b>PAYPAL_CLIENT_ID=Client ID</b><br>
<b>PAYPAL_CLIENT_SECRET=Secret key 1</b>
3. Знайти Partner аккаунт в https://developer.paypal.com/dashboard/accounts
4. Підставити значення в env:<br>
<b>PARTNER_ID=Account ID</b>
### Запуск проєкту

```bash
docker compose up -d --build
```