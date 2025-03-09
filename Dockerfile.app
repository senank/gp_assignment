FROM python:3.12-slim

# Install necessary tools to add a user
RUN apt-get update && apt-get install -y --no-install-recommends \
    adduser \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user with home directory
RUN adduser --disabled-password --gecos "" celery_user

WORKDIR /app
COPY requirements_app.txt requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir flake8 \
    && pip install numpy --pre torch torchvision torchaudio --force-reinstall --index-url https://download.pytorch.org/whl/nightly/cpu \
    && pip install sentence-transformers
    

COPY app /app/app
COPY start-celery.sh /app/start-celery.sh
RUN chmod +x /app/start-celery.sh

RUN chown -R celery_user /app
USER celery_user

EXPOSE 5000

CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:5000", "--timeout=300", "app.app_instance:app"]

