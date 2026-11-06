# Imagen para ejecutar el scraper igual en cualquier máquina
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir .
COPY data ./data
CMD ["python", "-m", "cromantic_scraper"]
