# Use a minimal Python base image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy ONLY backend folder
COPY backend/ /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8080

CMD ["python", "app.py"]
