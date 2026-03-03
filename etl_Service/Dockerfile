# Usamos una imagen de Python ligera
FROM python:3.9-slim

# Directorio de trabajo
WORKDIR /app

# Instalamos dependencias del sistema para que Python pueda hablar con Postgres
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiamos el archivo de requisitos e instalamos las librerías
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el script principal
COPY main.py .

# El comando para ejecutar el script al arrancar el contenedor
CMD ["python", "main.py"]