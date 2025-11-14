FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cron \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

COPY crontab.txt /etc/cron.d/fluxcloud-cron
RUN chmod 0644 /etc/cron.d/fluxcloud-cron && crontab /etc/cron.d/fluxcloud-cron

EXPOSE 8080

CMD service cron start && python app.py
