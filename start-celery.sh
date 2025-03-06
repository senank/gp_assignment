#!/bin/bash
set -e

# Wait until Redis is available
until nc -z redis 6379; do
  echo "Waiting for Redis..."
  sleep 1
done

echo "Redis is up! Starting Celery..."
celery -A app.app_instance.celery worker --loglevel=info --concurrency=9