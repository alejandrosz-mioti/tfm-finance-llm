FROM python:3.11-slim

WORKDIR /app

# Instalamos dependencias para que asyncpg y pandas funcionen
RUN apt-get update && apt-get install -y libpq-dev gcc g++ && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ejecutamos el main.py que arranca el bot de Telegram
CMD ["python", "main.py"]