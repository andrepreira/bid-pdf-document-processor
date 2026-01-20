FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir uv \
	&& uv pip install --system -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["bash", "-lc", "python -m alembic upgrade head && python scripts/run_pipeline.py \"$SOURCE_DIR\" --load-postgres --database-url \"$DATABASE_URL\""]
