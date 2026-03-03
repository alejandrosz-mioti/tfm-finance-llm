import os
import asyncio
from aiogram.filters import Command
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove 
from brain import extraer_datos_financieros
from database import asegurar_usuario, registrar_transaccion, obtener_nombres_cuentas, gestionar_cuenta_db, generar_resumen, obtener_nombres_cuentas_principales, realizar_transferencia_db, consultar_movimientos_db, consultar_datos_macro_db, actualizar_cuenta_db
from market import consultar_precio
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from grafana_client import obtener_grafico_grafana


load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))

dp = Dispatcher()

DASHBOARD_BASE_URL = "http://dashboard.finance/"

texto_ayuda = (
        "📖 <b>GUÍA DE USO</b>\n\n"
        "Háblame natural, yo te entiendo. Aquí tienes ejemplos de lo que puedes decir:\n\n"
        
        "🏦 <b>GESTIÓN DE CUENTAS</b>\n"
        "• <i>'Crea una cuenta Ahorro con 1000€'</i>\n"
        "• <i>'Crea una hucha Coche dentro de BBVA'</i>\n"
        "• <i>'Elimina la cuenta de gastos'</i>\n\n"

        "💸 <b>MOVIMIENTOS</b>\n"
        "• <i>'He gastado 15€ en cine con BBVA'</i>\n"
        "• <i>'Ingresa 1500€ de nómina'</i>\n"
        "• <i>'Pasa 200€ de BBVA a Ahorro'</i>\n\n"

        "🔍 <b>CONSULTAS PROPIAS</b>\n"
        "• <i>'¿Cuánto he gastado este mes?'</i>\n"
        "• <i>'Ver gastos de gasolina'</i>\n"
        "• <i>'¿Qué movimientos hice ayer?'</i>\n\n"

        "🌍 <b>DATOS MACRO (INE/Inflación)</b>\n"
        "• <i>'¿Cuál fue la inflación en 2022?'</i>\n"
        "• <i>'Gasto medio en transporte en España'</i>\n"
        "• <i>'Cambio Euro Dólar el 1 de marzo de 2023'</i>\n\n"

        "📈 <b>MERCADOS (Tiempo Real)</b>\n"
        "• <i>'Precio de las acciones de Apple'</i>\n"
        "• <i>'¿A cuánto está el Bitcoin?'</i>\n"
        "• <i>'¿Cómo va el IBEX 35?'</i>\n\n"
        

        "⚙️ <b>Comandos Rápidos:</b>\n"
        "• /start - Inicia el asistente y ve tu estado actual\n"
        "• /resumen - Ver saldos al instante\n"
        "• /cancelar - Detener operación actual\n"
        "• /grafica  - Ver gráfico visual de gastos (Grafana)\n"
        "• /streamlit - Ver panel de control web (Streamlit)\n"
        "• /help - Ver guía completa y más ejemplos\n\n"
    
    )

gastos_pendientes = {}
cola_tareas = {}

# --- MANEJADOR DE COMANDO /START ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    nombre = message.from_user.first_name

    # si el usuario estaba atascado en una operación a medias, lo liberamos
    if user_id in gastos_pendientes:
        del gastos_pendientes[user_id]

    # aseguramos que esté en la base de datos
    await asegurar_usuario(user_id, nombre)

    # generamos su resumen actual para que vea cómo está todo
    resumen = await generar_resumen(user_id)

    texto_bienvenida = (
        f"👋 <b>¡Hola, {nombre}!</b>\n\n"
        "Soy tu <b>Asistente Financiero Personal</b>. 🤖💶\n"
        "Estoy aquí para gestionar tus <b>ingresos, gastos y movimientos entre cuentas</b>, ofrecerte <b>resúmenes detallados</b> y darte información de mercados y economía.\n\n"
        
        "📝 <b>¿Qué puedo hacer por ti?</b>\n"
        "<i>Háblame natural, prueba a decirme cosas como:</i>\n\n"
        
        "💸 <b>Gestión de Cuentas y Huchas:</b>\n"
        "🔹 <i>'Crea una cuenta BBVA con 1000€'</i>\n"
        "🔹 <i>'Crea una hucha Coche dentro de BBVA'</i>\n"
        "🔹 <i>'He gastado 12€ en cine con la Santander'</i>\n"
        "🔹 <i>'Pasa 50€ de BBVA a la hucha Coche'</i>\n"
        "🔹 <i>'¿Cuánto he gastado este mes?'</i>\n\n"

        "📈 <b>Mercados (Tiempo Real):</b>\n"
        "🔹 <i>'¿A cuánto están las acciones de Apple?'</i>\n"
        "🔹 <i>'Precio del Bitcoin hoy'</i>\n"
        "🔹 <i>'¿Cómo va el IBEX 35?'</i>\n\n"

        "🌍 <b>Datos Macro (INE / Histórico):</b>\n"
        "🔹 <i>'¿Cuál fue la inflación en España en 2022?'</i>\n"
        "🔹 <i>'Gasto medio en transporte'</i>\n\n"

        "⚙️ <b>Comandos Rápidos:</b>\n"
        "▪️ /start - Inicia el asistente y ve tu estado actual\n"
        "▪️ /resumen - Ver saldos al instante\n"
        "▪️ /cancelar - Detener operación actual\n"
        "▪️ /grafica  - Ver gráfico visual de gastos (Grafana)\n"
        "▪️ /streamlit - Ver panel de control web (Streamlit)\n"
        "▪️ /help - Ver guía completa y más ejemplos\n\n"
        
        "👇 <b>Aquí tienes tu estado actual:</b>\n"
    )

    await message.answer(
        texto_bienvenida + resumen, 
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove() 
    )

# --- COMANDO /HELP (El Manual de Usuario) ---
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(texto_ayuda, parse_mode="HTML")

# --- COMANDO /RESUMEN (Acceso directo) ---
@dp.message(Command("resumen"))
async def cmd_resumen(message: types.Message):
    user_id = message.from_user.id
    resumen = await generar_resumen(user_id)
    await message.answer(f"📊 <b>Resumen Actualizado:</b>\n{resumen}", parse_mode="HTML")


# --- COMANDO /CANCELAR (Seguridad) ---
@dp.message(Command("cancelar"))
async def cmd_cancelar(message: types.Message):
    user_id = message.from_user.id
    if user_id in gastos_pendientes:
        del gastos_pendientes[user_id]
        await message.answer("✅ Operación cancelada. ¿En qué más puedo ayudarte?", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("🤷‍♂️ No estabas haciendo nada, pero aquí estoy.", reply_markup=ReplyKeyboardRemove())

@dp.message(Command("grafica"))
async def cmd_grafica(message: types.Message):
    teclado = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Saldo Total", callback_data="graf_1"),
         InlineKeyboardButton(text="📉 Últimas Transacciones", callback_data="graf_2")],
        
        [InlineKeyboardButton(text="🍔 Gastos por Categoría", callback_data="graf_3"),
         InlineKeyboardButton(text="🆚 Realidad vs Inflación", callback_data="graf_4")],
        
        [InlineKeyboardButton(text="📅 Gasto Mes Total", callback_data="graf_5"),
         InlineKeyboardButton(text="📈 Evolución", callback_data="graf_6")]
    ])
    
    await message.answer("🎨 **Centro de Visualización**\n¿Qué gráfico quieres consultar?", 
                         reply_markup=teclado, 
                         parse_mode="Markdown")

# --- MANEJADOR DE LOS BOTONES GRAFICA(Callback Query) ---
@dp.callback_query(lambda c: c.data.startswith('graf_'))
async def procesar_grafico(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Sacamos el número del botón (ej: "graf_3" -> 3)
    panel_id = int(callback.data.split("_")[1])
    
    await callback.answer("Generando gráfico... 🎨")
    
    msg_espera = await callback.message.answer("⏳ **Conectando con Grafana...**\nEsto puede tardar unos segundos.")
    
    imagen_bytes = await obtener_grafico_grafana(panel_id, user_id)
    
    await msg_espera.delete()
    
    if imagen_bytes:
        # Convertimos los bytes en un archivo que Telegram entienda
        archivo = BufferedInputFile(imagen_bytes, filename=f"grafico_{panel_id}.png")
        
        titulo_grafico = {
            1: "💰 Saldo Total del Mes",
            2: "📉 Últimas Transacciones",
            3: "🍔 Gastos por Categoría",
            4: "🆚 Realidad vs Inflación",
            5: "📅 Gasto Total Mensual",
            6: "📈 Evolución de Gastos"
        }.get(panel_id, "Gráfico Financiero")

        await callback.message.answer_photo(archivo, caption=f"📊 **{titulo_grafico}**")
    else:
        await callback.message.answer("⚠️ **Error:** No pude conectar con Grafana. Verifica que el servidor esté encendido.")

@dp.message(Command("streamlit"))
async def cmd_streamlit(message: types.Message):
    user_id = message.from_user.id
    
    # Construimos la URL personalizada
    url_personalizada = f"{DASHBOARD_BASE_URL}?user_id={user_id}"
    
    # Creamos el botón
    teclado = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Abrir Dashboard Web", url=url_personalizada)]
    ])
    
    await message.answer(
        "Aquí tienes el acceso a tu panel de control avanzado:",
        reply_markup=teclado
    )

@dp.message()
async def manejador_principal(message: types.Message):
    user_id = message.from_user.id
    nombre = message.from_user.first_name
    texto = message.text
    cuentas_validas = await obtener_nombres_cuentas(user_id)
    cuentas_principales = await obtener_nombres_cuentas_principales(user_id)

    # Insertamos usuario si es nuevo, sino no hace nada
    await asegurar_usuario(user_id, nombre)

    # Usuario eligiendo una cuenta con los botones
    if user_id in gastos_pendientes:
        datos_previos = gastos_pendientes[user_id]

        if datos_previos.get('intencion') == 'transferencia' and datos_previos.get('status') == 'resolviendo_ambiguedad':
            # Detectamos qué campo estamos corrigiendo (origen o destino)
            campo_conflicto = "cuenta_" + datos_previos['tipo_conflicto']
            
            # Guardamos lo que ha pulsado el usuario
            datos_previos[campo_conflicto] = message.text 
            
            # Limpiamos las marcas de error para reintentar
            del datos_previos['status']
            del datos_previos['tipo_conflicto']
            
            # Volvemos a probar la transferencia con el nombre corregido
            respuesta = await realizar_transferencia_db(user_id, datos_previos)
            
            # Sigue habiendo problemas? 
            if isinstance(respuesta, dict) and respuesta.get('status') == 'ambiguo':
                # Guardamos estado de nuevo
                datos_previos['status'] = 'resolviendo_ambiguedad'
                datos_previos['tipo_conflicto'] = respuesta['tipo']
                gastos_pendientes[user_id] = datos_previos 
                
                # Pedimos el siguiente dato
                botones = [[KeyboardButton(text=op)] for op in respuesta['opciones']]
                await message.answer(
                    f"Vale, entendido. Ahora tengo dudas con el <b>{respuesta['tipo']}</b>.\n¿A cuál te refieres?", 
                    reply_markup=ReplyKeyboardMarkup(keyboard=botones, resize_keyboard=True),
                    parse_mode="HTML"
                )
                return

            await message.answer(respuesta, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
            texto_resumen = await generar_resumen(user_id)
            await message.answer(texto_resumen, parse_mode="HTML")
            del gastos_pendientes[user_id]
            return
        
        elif datos_previos.get('intencion') == 'consulta propia' and datos_previos.get('status') == 'resolviendo_consulta':
            
            # Actualizamos el filtro con el nombre exacto del botón que pulsó
            datos_previos['filtro_cuenta'] = message.text 
            
            # Quitamos el estado de "resolviendo"
            del datos_previos['status']
            
            # Volvemos a consultar a la DB, ahora con el nombre exacto
            respuesta = await consultar_movimientos_db(user_id, datos_previos)
            
            # Mostramos resultado y limpiamos memoria
            await message.answer(str(respuesta), parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
            del gastos_pendientes[user_id]
            return
        

        if message.text.upper() in cuentas_validas:
            if datos_previos.get('intencion') == 'gestion_cuenta':
                # Si estamos creando una SUBCUENTA y nos faltaba el padre:
                if datos_previos.get('accion') == 'crear' and datos_previos.get('es_subcuenta'):
                    
                    # El botón NO es el nombre de la cuenta, es el PADRE
                    datos_previos['cuenta_padre'] = message.text.upper() 
                    
                    # Guardamos 
                    await gestionar_cuenta_db(user_id, datos_previos)
                    
                    nombre_nueva = datos_previos['nombre_cuenta']
                    texto_resumen = await generar_resumen(user_id)
                    
                    await message.answer(
                        f"✅ Subcuenta <b>{nombre_nueva}</b> creada dentro de <b>{message.text.upper()}</b>.\n\n{texto_resumen}", 
                        reply_markup=ReplyKeyboardRemove(),
                        parse_mode="HTML"
                    )

                elif datos_previos.get('accion') == 'eliminar':
                    await gestionar_cuenta_db(user_id, message.text)
                    await message.answer(f"🗑️ Cuenta **{message.text}** eliminada.", reply_markup=ReplyKeyboardRemove())
                    texto_resumen = await generar_resumen(user_id)
                    await message.answer(
                        f"✅ Operación realizada.\n\n{texto_resumen}",
                        reply_markup=ReplyKeyboardRemove(),
                        parse_mode="HTML"
                    )

                else:
                    datos_previos['nombre_cuenta'] = message.text
                    await actualizar_cuenta_db(user_id, datos_previos)
                    await message.answer(f"✅ Cuenta **{message.text}** actualizada.", reply_markup=ReplyKeyboardRemove())
                    texto_resumen = await generar_resumen(user_id)
                    await message.answer(
                        f"✅ Operación realizada.\n\n{texto_resumen}",
                        reply_markup=ReplyKeyboardRemove(),
                        parse_mode="HTML"
                    )

           
            # CASO: Estábamos registrando un gasto/ingreso
            else:
                datos_previos['cuenta'] = message.text
                await registrar_transaccion(user_id, datos_previos)
                
                concepto = datos_previos.get('concepto', 'transacción')

                await message.answer(
                    f"✅ Guardado en {message.text}.\n{datos_previos['monto']}€ en {concepto}.",
                    reply_markup=ReplyKeyboardRemove()
                )

                texto_resumen = await generar_resumen(user_id)
                await message.answer(
                    f"✅ Operación realizada.\n\n{texto_resumen}",
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode="HTML"
                )
            
            del gastos_pendientes[user_id]
            return

        else:
            await message.answer("⚠️ Selecciona una cuenta de la lista.")
            return


    # PROCESO NORMAL CON IA
    datos = await extraer_datos_financieros(message.text, nombre, user_id)
    cuentas_reales = await obtener_nombres_cuentas(user_id)

    print('Cuentas activas del usuario: ',cuentas_reales)
    print(datos)

    if datos and datos.get("intencion") == "demasiadas_peticiones":
        await message.answer("⚠️ ¡Whoa, despacio! Me has pedido varias cosas a la vez en el mismo mensaje.\n\nPor favor, **dímelas de una en una** para que pueda procesarlas bien. 🙏")
        return
    elif datos and datos.get('intencion') == 'gestion_cuenta':
        nombre_ia = datos.get('nombre_cuenta')
        accion = datos.get('accion')

        if accion == 'eliminar':
            if nombre_ia.upper() in cuentas_reales:
                await gestionar_cuenta_db(user_id, nombre_ia)
                await message.answer(f"🗑️ Cuenta **{nombre_ia}** eliminada.")
                texto_resumen = await generar_resumen(user_id)
                await message.answer(
                    f"✅ Operación realizada.\n\n{texto_resumen}",
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode="HTML"
                )

            else:
                gastos_pendientes[user_id] = datos
                botones = [[KeyboardButton(text=c)] for c in cuentas_reales]
                await message.answer(f"No encuentro '{nombre_ia}'. ¿Cuál quieres eliminar?",
                                     reply_markup=ReplyKeyboardMarkup(keyboard=botones, resize_keyboard=True))

        elif accion == 'modificar' and nombre_ia.upper() in cuentas_reales:
            await actualizar_cuenta_db(user_id, datos)
            texto_resumen = await generar_resumen(user_id)
            await message.answer(
                f"✅ Operación realizada.\n\n{texto_resumen}",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="HTML"
            )
            

        else:
            if accion == 'crear' and datos.get('es_subcuenta') == True and (datos.get('cuenta_padre') == None or datos.get('cuenta_padre').upper() not in cuentas_reales):
                gastos_pendientes[user_id] = datos
                botones = [[KeyboardButton(text=c)] for c in cuentas_principales]
                await message.answer(f"No has especificado cuenta padre para '{nombre_ia}'. ¿Te refieres a una de estas?",
                                     reply_markup=ReplyKeyboardMarkup(keyboard=botones, resize_keyboard=True))
            elif accion == 'crear':
                await gestionar_cuenta_db(user_id, datos)
                await message.answer(f"✅ Nueva cuenta **{nombre_ia}** creada.")
                texto_resumen = await generar_resumen(user_id)
                await message.answer(
                    f"✅ Operación realizada.\n\n{texto_resumen}",
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode="HTML"
                )

            else:
                gastos_pendientes[user_id] = datos
                botones = [[KeyboardButton(text=c)] for c in cuentas_reales]
                await message.answer(f"No encuentro '{nombre_ia}'. ¿Te refieres a una de estas?",
                                     reply_markup=ReplyKeyboardMarkup(keyboard=botones, resize_keyboard=True))

    elif datos and datos.get('intencion') == 'transaccion':
        if (datos.get('cuenta') or "").upper() not in cuentas_reales:
            gastos_pendientes[user_id] = datos
            botones = [[KeyboardButton(text=c)] for c in cuentas_reales]
            await message.answer(f"¿En qué cuenta registro los {datos['monto']}€?",
                                 reply_markup=ReplyKeyboardMarkup(keyboard=botones, resize_keyboard=True))

        else:
            await registrar_transaccion(user_id, datos)
            nombre_cuenta = (datos.get('cuenta') or "").upper()
            await message.answer(f"✅ Guardado: {datos['monto']}€ en {nombre_cuenta}")
    
            texto_resumen = await generar_resumen(user_id)
            await message.answer(
                f"✅ Operación realizada.\n\n{texto_resumen}",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="HTML"
            )

    elif datos and datos.get('intencion') == 'transferencia':
        
        # Intentamos hacer la transferencia directos. 
        respuesta = await realizar_transferencia_db(user_id, datos)
        
        # La base de datos tiene dudas (AMBIGÜEDAD)
        if isinstance(respuesta, dict) and respuesta.get('status') == 'ambiguo':
            
            # Guardamos en memoria qué estamos intentando resolver
            datos['status'] = 'resolviendo_ambiguedad'
            datos['tipo_conflicto'] = respuesta['tipo'] 
            gastos_pendientes[user_id] = datos
            
            # Creamos los botones con las opciones que nos ha dado la DB
            botones = [[KeyboardButton(text=op)] for op in respuesta['opciones']]
            
            await message.answer(
                f"🤔 Tengo dudas con la cuenta de <b>{respuesta['tipo']}</b>.\n"
                f"He encontrado varias parecidas, ¿a cuál te refieres?",
                reply_markup=ReplyKeyboardMarkup(keyboard=botones, resize_keyboard=True),
                parse_mode="HTML"
            )
            return 

        await message.answer(str(respuesta), parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        
    
        if "❌" not in str(respuesta):
            texto_resumen = await generar_resumen(user_id)
            await message.answer(texto_resumen, parse_mode="HTML")

    elif datos and datos.get('intencion') == 'consulta propia':
        respuesta = await consultar_movimientos_db(user_id, datos)

        # AMBIGÜEDAD EN LA CUENTA
        if isinstance(respuesta, dict) and respuesta.get('status') == 'ambiguo':
            # Guardamos estado para esperar el clic del usuario
            datos['status'] = 'resolviendo_consulta'
            gastos_pendientes[user_id] = datos
            
            botones = [[KeyboardButton(text=op)] for op in respuesta['opciones']]
            await message.answer(
                f"🤔 He encontrado varias cuentas con ese nombre.\n¿Cuál quieres consultar?", 
                reply_markup=ReplyKeyboardMarkup(keyboard=botones, resize_keyboard=True)
            )
            return

        # RESPUESTA
        await message.answer(str(respuesta), parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    
    elif datos and datos.get('intencion') == "mercado":
            ticker = datos.get("ticker")
            if ticker:
                await message.answer(f"Buscando datos...")
                # Llamamos a la función síncrona de market.py
                resultado = consultar_precio(ticker)
                await message.answer(resultado, parse_mode="Markdown")
            else:
                await message.answer(f"No pude deducir el ticker de la empresa")
    
    elif datos and datos.get('intencion') == "resumen_global":
        texto_resumen = await generar_resumen(user_id)
        await message.answer(
            f"📊 <b>Aquí tienes el estado actual de tus cuentas:</b>\n\n{texto_resumen}", 
            parse_mode="HTML"
        )
    
    elif datos and datos.get('intencion') == "consulta_datos_macro":
        respuesta = await consultar_datos_macro_db(datos)
        await message.answer(respuesta, parse_mode="Markdown")

    elif  datos and datos.get('intencion') == "ayuda":
         await message.answer(texto_ayuda, parse_mode="HTML")




async def main():
    print("🚀 BOT en marcha...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import sys
    import asyncio
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot detenido.")