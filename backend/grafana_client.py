import aiohttp
from grafana_config import GrafanaPanelManager


GRAFANA_HOST = "grafana_tfm" 
GRAFANA_PORT = 3000

manager = GrafanaPanelManager(host=GRAFANA_HOST, port=GRAFANA_PORT)

async def obtener_grafico_grafana(panel_logico_id, user_id):
    """
    Descarga la imagen del gráfico de forma asíncrona.
    Devuelve los bytes de la imagen o None si falla.
    """
    url = manager.get_url(logical_id=panel_logico_id, user_id=user_id, render=True)
    
    if not url:
        print(f"❌ Error: ID lógico {panel_logico_id} no existe en la config.")
        return None

    print(f"🎨 Solicitando gráfico a: {url}")

    async with aiohttp.ClientSession() as session:
        try:
            # A veces Grafana necesita autenticación. Si es pública, esto vale.
            # Si necesita clave, habría que añadir headers={"Authorization": "Bearer TU_CLAVE"}
            async with session.get(url, timeout=60) as response:
                if response.status == 200:
                    datos_imagen = await response.read() 
                    return datos_imagen
                else:
                    print(f"❌ Error Grafana: {response.status}")
                    return None
        except Exception as e:
            print(f"❌ Error de conexión con Grafana: {e}")
            return None