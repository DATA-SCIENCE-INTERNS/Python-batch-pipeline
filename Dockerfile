# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Layer caching: dependencies change rarely, code changes often
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY taxi_pipeline/ taxi_pipeline/

RUN groupadd --system app && useradd --system --gid app --home /app app \
    && chown -R app:app /app

USER app

ENTRYPOINT ["python", "-m", "taxi_pipeline"]
CMD ["--help"]