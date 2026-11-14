# Jeden obraz: FastAPI serwuje API oraz zbudowany frontend (dokumentacja 3.4).

# ---------- etap 1: budowa frontendu ----------
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ---------- etap 2: backend ----------
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=prod \
    STATIC_DIR=/app/web/dist \
    SEED_DIR=/app/seed

WORKDIR /app/backend
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir .
COPY backend/alembic.ini ./
COPY seed/ /app/seed/
COPY --from=web /web/dist /app/web/dist

RUN useradd --create-home barbellos
USER barbellos

EXPOSE 8000
# Migracje i dane startowe są idempotentne, więc uruchamiają się przy każdym starcie.
# --proxy-headers: za serwerem pośredniczącym hostingu adres klienta i https są w nagłówkach.
CMD ["sh", "-c", "alembic upgrade head && python -m app.tools.seed && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
