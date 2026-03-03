class GrafanaPanelManager:
    def __init__(self, host="grafana.finance", port=None):
        """
        host: 'grafana.finance' para Streamlit (Nginx), 
              'grafana_tfm' para comunicación interna entre contenedores Docker,
              'localhost' para pruebas desde tu PC.
        """
        self.base_url = f"http://{host}{f':{port}' if port else ''}"
        
        # MAPEO GLOBAL DE PANELES (ID Lógico -> Configuración de Grafana)
        self.PANELS = {
            1: {"uid": "adfkkqt", "slug": "termometro-financiero", "panel_id": "1"},
            2: {"uid": "adfkkqt", "slug": "termometro-financiero", "panel_id": "4"},
            3: {"uid": "adfkkqt", "slug": "termometro-financiero", "panel_id": "3"},
            4: {"uid": "adqtprv", "slug": "realidad-vs-inflacion", "panel_id": "2"},
            5: {"uid": "adqm8g7", "slug": "arbol-de-cuentas",     "panel_id": "3"},
            6: {"uid": "adqm8g7", "slug": "arbol-de-cuentas",     "panel_id": "2"},
        }

    def get_url(self, logical_id, user_id, render=False, width=1000, height=500):
        config = self.PANELS.get(logical_id)
        if not config:
            return None

        # Endpoint de renderizado o de visualización
        endpoint = "render/d-solo" if render else "d-solo"
        url = f"{self.base_url}/{endpoint}/{config['uid']}/{config['slug']}"
        
        params = [
            f"orgId=1",
            f"panelId={config['panel_id']}",
            f"var-var_user_id={user_id}",
            f"width={width}",
            f"height={height}",
            f"tz=Europe/Madrid",
            "from=now-1M", # Por defecto mostramos el último mes
            "to=now"
        ]
        
        if render:
            params.append("render=1")
            params.append("timeout=60")

        return f"{url}?{'&'.join(params)}"