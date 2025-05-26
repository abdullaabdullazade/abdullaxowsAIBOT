FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libasound2 \
    libx11-xcb1 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libxrandr2 \
    libxdamage1 \
    libgbm1 \
    libu2f-udev \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver


EXPOSE 5100
CMD ["python3", "bot.py"]
