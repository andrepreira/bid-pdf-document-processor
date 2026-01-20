FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV SOURCE_DIR=/app/source/source_files/
ENV DATABASE_URL=postgresql://postgres:postgres@postgres:5432/bid_processor

CMD ["bash", "-lc", "python scripts/run_pipeline.py \"$SOURCE_DIR\" --load-postgres --database-url \"$DATABASE_URL\""]
