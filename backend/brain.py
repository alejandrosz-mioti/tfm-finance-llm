import os
import json
import re
import datetime
from dotenv import load_dotenv 
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

def limpiar_respuesta_json(texto):
    """
    Limpia la respuesta del modelo para asegurar que solo quede un JSON válido.
    """
    # Eliminar bloques de código markdown si existen
    texto = re.sub(r'```json\s*|```', '', texto)
    # Buscar el primer '{' y el último '}'
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match:
        return match.group(0)
    return texto

async def extraer_datos_financieros(texto_usuario, nombre_usuario, user_id):
    fecha_hoy = datetime.date.today().strftime("%Y-%m-%d") 
    
    print(f"--- FECHA QUE SE ENVÍA AL PROMPT: {fecha_hoy} ---")

    system_prompt = SystemMessage(content=f"""
        ERES UN ANALISTA FINANCIERO QUE RESPONDE ÚNICAMENTE EN FORMATO JSON.
        HOY ES: {fecha_hoy} 
        
        Debes clasificar la intención en: "transaccion", "gestion_cuenta", "transferencia", "consulta propia", "mercado", "resumen_global", "consulta_datos_macro" o "ayuda".

        REGLAS DE FORMATO:
        1. Responde SOLO el objeto JSON.
        2. No añadidas explicaciones ni texto fuera del JSON.
        3. Asegúrate de que todas las propiedades estén separadas por comas.

        --- ESQUEMAS JSON POR INTENCIÓN ---

        TRANSACCION:
        {{"intencion": "transaccion", "tipo": "ingreso/gasto", "monto": float, "concepto": "string", "categoria": "Alimentacion/Educacion/Ocio/Casa/Otros", "cuenta": "string o null", "fecha": "YYYY-MM-DD"}}

        GESTION_CUENTA:
        {{"intencion": "gestion_cuenta", "accion": "crear/modificar/eliminar", "nombre_cuenta": "string", "saldo": float, "tipo": "PRINCIPAL", "es_subcuenta": boolean, "cuenta_padre": "null", "nuevo_nombre":"string"}}

        TRANSFERENCIA:
        {{"intencion": "transferencia", "cantidad": float, "cuenta_origen": "string", "cuenta_destino": "string"}}

        CONSULTA PROPIA:
        {{"intencion": "consulta propia", "periodo": "string", "fecha": "YYYY-MM-DD o null", "tipo_movimiento": "gasto/ingreso/todo", "filtro_concepto": "string o null", "filtro_cuenta": "string o null"}}

        CONSULTA MERCADO:
        {{"intencion": "mercado", "ticker": "SÍMBOLO_YAHOO"}}

        RESUMEN GLOBAL:
        {{"intencion": "resumen_global"}}

        CONSULTA DATOS MACRO:
        {{
          "intencion": "consulta_datos_macro",
          "tipo_dato": "inflacion/consumo_medio/divisa_historica",
          "parametros": {{
             "pais": "Spain",
             "anio": int,
             "categoria": "Elegir de la lista: Índice general, 01 Alimentos, 07 Transporte, etc.",
             "fecha": "YYYY-MM-DD"
          }}
        }}

        AYUDA:
        {{"intencion": "ayuda"}}
    """)
    
    mensaje = HumanMessage(content=texto_usuario)
    
    try:
        print("--- 2. Enviando a Groq... ---")
        response = await llm.ainvoke([system_prompt, mensaje])
        
        contenido = response.content.strip()
        print(f"--- 3. Groq Respondió esto: ---\n{contenido}\n-------------------------------")

        # Limpiar y procesar JSON
        json_str = limpiar_respuesta_json(contenido)
        
        try:
            datos = json.loads(json_str)
            print("--- 4. JSON convertido con éxito ---")
            return datos
        except json.JSONDecodeError as je:
            print(f"❌ Error al decodificar JSON: {je}. Texto recibido: {json_str}")
            # Intentar un último recurso si el modelo envió múltiples líneas o basura
            return None
            
    except Exception as e:
        print(f"❌❌ ERROR FATAL EN BRAIN.PY: {e}")
        return None