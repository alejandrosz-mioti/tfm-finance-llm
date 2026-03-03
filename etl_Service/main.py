import pandas as pd
from sqlalchemy import create_engine
import os
import time

# 1. Configuración de conexión usando variables de entorno
DB_USER = os.getenv('DB_USER', 'admin')
DB_PASS = os.getenv('DB_PASS', 'admin_password')
DB_NAME = os.getenv('DB_NAME', 'economia_db')
DB_HOST = 'db' # Nombre del servicio en docker-compose

conn_str = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
engine = create_engine(conn_str)

def cargar_datos():
    # Esperar a que la base de datos acepte conexiones (Postgres tarda en arrancar)
    print("Esperando 15 segundos a que la DB esté lista...")
    time.sleep(15) 

    try:
        # --- 1. CARGA DE INFLACIÓN (De formato ancho a largo) ---
        print("Cargando datos de inflación...")
        df_inf = pd.read_csv('data/inflacion.csv')
        
        # Identificamos columnas de años (las que son números)
        columnas_anios = [col for col in df_inf.columns if col.isdigit()]
        
        # Transformación: Pasamos los años de columnas a una sola columna 'anio'
        df_inf_melted = df_inf.melt(
            id_vars=['country_name'], 
            value_vars=columnas_anios,
            var_name='anio', 
            value_name='valor_inflacion'
        )
        
        # Renombrar para SQL: 'country_name' -> 'pais'
        df_inf_melted = df_inf_melted.rename(columns={'country_name': 'pais'})
        
        # Limpieza: quitar nulos y asegurar tipos
        df_inf_melted = df_inf_melted.dropna(subset=['valor_inflacion'])
        df_inf_melted['anio'] = df_inf_melted['anio'].astype(int)
        
        df_inf_melted.to_sql('ext_inflacion', engine, if_exists='append', index=False)
        print(f"✅ Inflación cargada: {len(df_inf_melted)} registros.")


# --- 2. CARGA DE DIVISAS ---
        print("Cargando datos de divisas...")
        df_div = pd.read_csv('data/divisas.csv')
        
        # Seleccionamos solo las columnas necesarias y las renombramos
        # El CSV usa 'Date' para la fecha y 'Price' para el valor del Euro/USD
        df_div = df_div[['Date', 'Price']].copy()
        df_div.columns = ['fecha', 'euro_usd']
        
        # Convertimos la fecha al formato que entiende PostgreSQL (YYYY-MM-DD)
        # Tu CSV viene como '21-02-2025' (día-mes-año)
        df_div['fecha'] = pd.to_datetime(df_div['fecha'], dayfirst=True)
        
        df_div.to_sql('ext_divisas', engine, if_exists='append', index=False)
        print(f"✅ Divisas cargadas: {len(df_div)} registros.")

# --- 3. CARGA DE INE CONSUMO ---
        print("Cargando datos del INE...")
        df_ine = pd.read_csv('data/ine.csv', sep=None, engine='python', encoding='utf-8')

        # Limpiamos nombres de columnas (quitamos espacios extra)
        df_ine.columns = df_ine.columns.str.strip()

        col_quintil = None
        for col in df_ine.columns:
            if 'Quintil' in col:
                col_quintil = col
                break
        
        if col_quintil:
            print(f"   ℹ️ Filtrando columna '{col_quintil}' para quedarnos solo con 'Total'...")
            # Usamos .str.strip() para asegurar que "Total " (con espacio) coincida con "Total"
            df_ine = df_ine[df_ine[col_quintil].astype(str).str.strip() == 'Total']
        else:
            print("   ⚠️ OJO: No encontré columna 'Quintil'. Se cargarán todos los datos sin filtrar.")

        # 2. BUSQUEDA COLUMNA DE NÚMEROS (Total/Dato/Valor)
        col_numeros = None
        for col in df_ine.columns:
            # Evitamos coger la columna Quintil o Periodo como si fuera un número
            if col == col_quintil: continue
            
            if 'Total' in col or 'Dato' in col or 'Valor' in col:
                col_numeros = col
                break
        if not col_numeros:
            col_numeros = df_ine.columns[-1] # Fallback a la última

        # 3. BUSQUEDA COLUMNA DE AÑO (Periodo/Anio/Year)
        col_anio = None
        for col in df_ine.columns:
            if 'Periodo' in col or 'Año' in col or 'Year' in col:
                col_anio = col
                break

        # Validamos que encontramos el año
        if not col_anio:
            print("❌ ERROR: No encuentro la columna de 'Periodo' o 'Año' en el CSV.")
        else:
            # 4. Creamos el dataframe          
            df_final_ine = pd.DataFrame({
                'categoria': df_ine.iloc[:, 2],   
                'anio': df_ine[col_anio],
                'gasto_medio': df_ine[col_numeros]
            })

            # --- LIMPIEZA DE DATOS ---
            
            # Limpieza de Gasto Medio (1.000,50 -> 1000.50)
            # Primero quitamos el punto de los miles y luego cambiamos coma por punto
            df_final_ine['gasto_medio'] = df_final_ine['gasto_medio'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df_final_ine['gasto_medio'] = pd.to_numeric(df_final_ine['gasto_medio'], errors='coerce')
            
            # Limpieza de Año (asegurar que es entero)
            df_final_ine['anio'] = pd.to_numeric(df_final_ine['anio'], errors='coerce')

            # Quitamos filas que no tengan dato o año
            df_final_ine = df_final_ine.dropna(subset=['gasto_medio', 'anio'])

            # Solo cargamos si hay algo
            if not df_final_ine.empty:
                # Importante: if_exists='append'. 
                # RECUERDA vaciar la tabla antes si ya tenías datos sucios.
                df_final_ine.to_sql('ext_ine_consumo', engine, if_exists='append', index=False)
                print(f"✅ Datos INE cargados correctamente (Solo Quintil Total): {len(df_final_ine)} registros.")
            else:
                print("⚠️ El INE se leyó pero quedó vacío tras la limpieza.")

    except Exception as e:
        print(f"❌ ERROR durante la carga: {e}")

if __name__ == "__main__":
    print("--- INICIANDO PROCESO ETL ---")
    cargar_datos()
    print("--- PROCESO FINALIZADO ---")