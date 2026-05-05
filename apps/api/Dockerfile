FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps/api ./apps/api
COPY apps/worker ./apps/worker

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api_app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
