FROM python:3.12.3

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо requirements.txt перед встановленням залежностей
COPY requirements.txt .

# Встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо код вебсервера
COPY . .

# Запускаємо сервер
CMD ["python3", "webserver/app.py"]
