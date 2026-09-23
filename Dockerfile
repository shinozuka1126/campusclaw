FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY scripts ./scripts
COPY gunicorn.conf.py .
COPY README.md .
RUN mkdir -p /app/data /app/uploads
EXPOSE 8080
CMD ["sh", "-c", "python scripts/init_db.py && exec gunicorn -c gunicorn.conf.py 'app:create_app()'"]
