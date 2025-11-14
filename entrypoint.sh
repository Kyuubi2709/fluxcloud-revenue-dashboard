#!/bin/bash

echo "Starting cron service..."
service cron start

echo "Cron started."

echo "Launching Flask app..."
exec python /app/app.py
