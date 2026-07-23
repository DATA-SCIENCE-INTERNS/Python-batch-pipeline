FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY taxi_pipeline ./taxi_pipeline
COPY sql ./sql

RUN mkdir -p /app/data/bronze/yellow
RUN mkdir -p /app/data/bronze/green
RUN mkdir -p /app/logs

CMD ["python", "-m", "taxi_pipeline.main"]