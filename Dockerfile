# Imagen de la aplicación web. Render la construye a partir de este archivo.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000 \
    DATA_PATH=/app/data/productos_cromantic.csv

WORKDIR /app

# Primero las dependencias: si no cambian, Docker reutiliza esta capa
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .

COPY data ./data

# Usuario sin privilegios de administrador
RUN useradd --create-home appuser
USER appuser

EXPOSE 10000
CMD gunicorn --bind 0.0.0.0:${PORT} --workers 2 --timeout 60 cromantic_scraper.app:app
