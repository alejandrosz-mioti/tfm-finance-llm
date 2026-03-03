import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import create_engine
import pandas as pd

# 1. CONFIGURACIÓN INICIAL (DEBE SER LO PRIMERO)
st.set_page_config(
    page_title="Terminal Financiera LLM", 
    layout="wide", 
    page_icon="📈",
    initial_sidebar_state="collapsed" # Fuerza el cierre
)

# 2. CONEXIÓN A LA BASE DE DATOS
# El formato es: postgresql://USUARIO:CONTRASEÑA@HOST:PUERTO/NOMBRE_DB
engine = create_engine("postgresql://admin:tfm_password@db:5432/economia_db")

def get_user_info(uid):
    try:
        # Forzamos que el UID sea tratado como número
        query = f"SELECT nombre, fecha_registro FROM usuarios WHERE user_id = {int(uid)}"
        df = pd.read_sql(query, engine)
        return df.iloc[0] if not df.empty else None
    except Exception as e:
        # Esto te ayudará a ver en la terminal por qué falla
        print(f"Error en la DB: {e}")
        return None

# Capturamos el ID
user_id_url = st.query_params.get("user_id")
user_info = get_user_info(user_id_url) if user_id_url else None

# 3. ESTILO CSS
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11; }
    
    /* ESTO CIERRA Y BLOQUEA EL SIDEBAR DEFINITIVAMENTE */
    [data-testid="collapsedControl"] {
        display: none;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0B0E11;
        border-right: 1px solid #00FF41;
    }
    
    .error-msg {
        color: #FF4B4B;
        font-family: 'Courier New', monospace;
        text-align: center;
        margin-top: 50px;
        border: 2px solid #FF4B4B;
        padding: 20px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 4. LÓGICA DE ACCESO RESTRICTIVO
if user_info is None:
    # Si no hay usuario, bloqueamos toda la app
    st.markdown('<div class="error-msg"><h1>❌ URL NO VÁLIDA</h1><p>DEBES ACCEDER CON LA URL PERSONALIZADA DEL LLM INDICADA PARA TU USUARIO</p></div>', unsafe_allow_html=True)
    # Detenemos la ejecución aquí
    st.stop() 

# --- SI LLEGAMOS AQUÍ, EL USUARIO ES VÁLIDO ---

st.title(f"👾 Bienvenido@, {user_info['nombre']}")
st.caption(f"🛡️ Cuenta activa desde: {user_info['fecha_registro'].strftime('%d/%m/%Y')}")

# --- NAVEGACIÓN ---
menu = st.selectbox(
    "Selecciona la vista de análisis:",
    ["Ver Todo", "Termómetro Financiero", "Árbol de Cuentas", "Realidad vs Inflación"]
)

# --- 5. URLs DINÁMICAS (Revisar sintaxis de variable) ---
uid = user_id_url
#base_g = "http://localhost:3000/d" , sin nginx
base_g = "http://grafana.finance/d"

# IMPORTANTE: Verifica si en Grafana el nombre de la variable es 'var_user_id' o solo 'user_id'
# Si es 'var_user_id', la URL debe ser &var-var_user_id={uid}
url_termometro = f"{base_g}/adfkkqt/termometro-financiero?orgId=1&kiosk&var-var_user_id={uid}"
url_cuentas = f"{base_g}/adqm8g7/arbol-de-cuentas?orgId=1&kiosk&var-var_user_id={uid}"
url_inflacion = f"{base_g}/adqtprv/realidad-vs-inflacion?orgId=1&kiosk&var-var_user_id={uid}"

# --- LÓGICA DE VISUALIZACIÓN ---
if menu == "Termómetro Financiero":
    components.iframe(url_termometro, height=1200, scrolling=True)
elif menu == "Árbol de Cuentas":
    components.iframe(url_cuentas, height=1200, scrolling=True)
elif menu == "Realidad vs Inflación":
    components.iframe(url_inflacion, height=1200, scrolling=True)
else: # Ver Todo
    st.subheader("Estado General y Distribución")
    col1, col2 = st.columns(2)
    with col1:
        components.iframe(url_termometro, height=600, scrolling=True)
    with col2:
        components.iframe(url_cuentas, height=600, scrolling=True)
    st.subheader("Contexto Macroeconómico")
    components.iframe(url_inflacion, height=800, scrolling=True)

# --- SIDEBAR ---
with st.sidebar:    
    st.markdown("**LLM FINANCE**")
    st.success("Alejandro Sánchez / Chantal López")
    st.caption("MIOTI 2026")
