# Backend de RestaurantERP: FastAPI servido con uvicorn
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias primero para aprovechar la caché de Docker
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# El contenedor no corre como root
RUN useradd --create-home --uid 1000 restaurant && chown -R restaurant:restaurant /app
USER restaurant

EXPOSE 8000

# Al arrancar: crea tablas y catálogos si faltan (seed.py no duplica nada) y levanta la API.
# --proxy-headers hace que los logs guarden la IP real que envía nginx, no la del contenedor.
CMD ["sh", "-c", "python seed.py && exec uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
