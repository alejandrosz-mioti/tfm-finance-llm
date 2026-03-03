import yfinance as yf

def consultar_precio(ticker):
    """
    Busca el precio actual y la variación de un activo usando Yahoo Finance.
    """
    try:
        # Descargamos info del ticker
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Yahoo a veces cambia las claves del diccionario, usamos .get para evitar errores
        precio_actual = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('ask')
        moneda = info.get('currency', 'USD')
        nombre = info.get('shortName') or info.get('longName') or ticker
        
        # Intentamos sacar el precio de apertura para calcular variación si no viene directa
        previous_close = info.get('previousClose')
        
        if precio_actual is None:
            return f"⚠️ No pude obtener el precio en tiempo real para **{ticker}**. Quizás el mercado está cerrado o el ticker es incorrecto."

        # Calcular variación porcentual
        variacion_str = ""
        if previous_close:
            variacion = ((precio_actual - previous_close) / previous_close) * 100
            icono = "🟢" if variacion >= 0 else "🔴"
            variacion_str = f"({icono} {variacion:.2f}%)"

        return (
            f"📈 **MERCADO ({ticker})**\n"
            f"🏢 **{nombre}**\n"
            f"💰 Precio: **{precio_actual} {moneda}** {variacion_str}"
        )

    except Exception as e:
        print(f"Error en yfinance: {e}")
        return f"❌ Error consultando el ticker {ticker}. Intenta ser más específico."