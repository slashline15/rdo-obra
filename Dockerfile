# Stage 1: Build frontend
FROM node:22-alpine AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend + static frontend
FROM python:3.13-slim

WORKDIR /app

# Dependências do sistema (weasyprint precisa de libs gráficas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
    libcairo2 libgdk-pixbuf2.0-0 libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY alembic.ini .
COPY migrations ./migrations

# Copiar frontend buildado para static/
COPY --from=frontend-build /frontend/dist ./static

RUN mkdir -p uploads/audio uploads/fotos output

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
