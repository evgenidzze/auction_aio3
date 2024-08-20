FROM python:3.10.12-slim

# Install required packages including locales and tzdata
RUN apt-get update && \
    apt-get install -y locales tzdata && \
    apt-get clean

# Set the timezone to Europe/Kyiv
RUN ln -sf /usr/share/zoneinfo/Europe/Kyiv /etc/localtime && \
    echo "Europe/Kyiv" > /etc/timezone

# Generate the locale
RUN echo "uk_UA.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen

# Set the locale environment variables
ENV LANG=uk_UA.UTF-8
ENV LANGUAGE=uk_UA:uk
ENV LC_ALL=uk_UA.UTF-8

WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Copy the rest of the application code
COPY . .

# Ensure that the locale and timezone are correctly set
RUN echo "Locale set to: $(locale)" && \
    echo "Timezone set to: $(cat /etc/timezone)"

# Command to run the application
CMD ["python3", "start_bot.py"]
