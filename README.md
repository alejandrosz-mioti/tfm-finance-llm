```
Instrucciones para levantarse el entorno en tu local:

1. Copiar el directorio de github y entrar en el:
    git clone https://github.com/alejandrosz-mioti/tfm-finance-llm.git
    cd tfm-finance-llm

2. Editar el fichero .env en nuestro nuevo directorio añadiendo las apikeys (indicado en entregable):
    TELEGRAM_TOKEN=...
    GROQ_API_KEY=...

3. Editar el fichero "C:\Windows\System32\drivers\etc\hosts" del equipo como administrador, añadiendo las líneas:
    127.0.0.1   dashboard.finance
    127.0.0.1   grafana.finance
    127.0.0.1   bbdd-pg.finance

4. Levantar los contenedores (comando en una terminal desde el directorio que se ha clonado):
    docker compose up -d --build


----- Accesos a los servicios (url navegador):
Streamlit (Interfaz Usuario): http://dashboard.finance/?user_id=[id]
Grafana (Dashboards): http://grafana.finance/ (User: admin / Pass: admin)
pgAdmin (Visor DB): http://bbdd-pg.finance/ (User: admin@tfm.com / Pass: admin)
Base de datos:
 POSTGRES_USER: admin
 POSTGRES_PASSWORD: tfm_password
 POSTGRES_DB: economia_db
```
