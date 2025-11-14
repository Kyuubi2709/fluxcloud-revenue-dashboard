FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install cron + dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    build-essential \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Ensure cache folder exists
RUN mkdir -p /app/cache && chmod -R 777 /app/cache

# Copy cron schedule
COPY crontab.txt /etc/cron.d/fluxcloud-cron
RUN chmod 0644 /etc/cron.d/fluxcloud-cron && crontab /etc/cron.d/fluxcloud-cron

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080

# Launch cron + Flask
CMD ["/entrypoint.sh"]
