import os
import asyncpg
import datetime
from dotenv import load_dotenv

load_dotenv()

async def obtener_conexion():
    return await asyncpg.connect(os.getenv("DATABASE_URL"), ssl=False)

async def asegurar_usuario(user_id, nombre):
    conn = await obtener_conexion()
    try:
        # Usamos ON CONFLICT para que no de error si el usuario ya existe
        await conn.execute(
            """INSERT INTO usuarios(user_id, nombre, fecha_registro) 
               VALUES($1, $2, $3) 
               ON CONFLICT (user_id) DO UPDATE SET nombre = $2""", 
            user_id, nombre, datetime.datetime.now()
        )
        print(f"✅ Usuario {nombre} asegurado en DB.")
    except Exception as e:
        print(f"❌ Error guardando usuario: {e}")
    finally:
        await conn.close()


# --- GESTIÓN DE CUENTAS  ---
async def obtener_nombres_cuentas(user_id):
    """Devuelve una lista con los nombres de todas las cuentas del usuario."""
    conn = await obtener_conexion()
    try:
        rows = await conn.fetch("SELECT nombre_cuenta FROM cuentas WHERE user_id = $1", user_id)
        return [fila['nombre_cuenta'].upper() for fila in rows]
    finally:
        await conn.close()

async def obtener_nombres_cuentas_principales(user_id):
    """Devuelve una lista con los nombres de las cuentas principales del usuario."""
    conn = await obtener_conexion()
    try:
        rows = await conn.fetch("SELECT nombre_cuenta FROM cuentas WHERE user_id = $1 AND tipo='PRINCIPAL'", user_id)
        return [fila['nombre_cuenta'].upper() for fila in rows]
    finally:
        await conn.close()


async def gestionar_cuenta_db(user_id, datos):
    """Crea o Elimina cuentas basándose en la intención de la IA."""
    conn = await obtener_conexion()
    try:
        # Si es borrar 
        if not isinstance(datos, dict):
            nombre_borrar = datos.upper()
            
            # BUSCAR EL ID DE LA CUENTA "PADRE"
            fila = await conn.fetchrow(
                "SELECT id FROM cuentas WHERE user_id = $1 AND nombre_cuenta = $2", 
                user_id, nombre_borrar
            )

            if not fila:
                print(f"⚠️ No se encontró la cuenta {nombre_borrar} para borrar.")
                return

            id_padre = fila['id']

            print(f"🧨 Iniciando borrado en cascada para cuenta ID {id_padre} ({nombre_borrar})...")

            # BORRAR TODAS LAS TRANSACCIONES ASOCIADAS
            # Borramos las que pertenezcan a la cuenta padre O a sus subcuentas (hijas)
            await conn.execute("""
                DELETE FROM transacciones 
                WHERE cuenta_id = $1 
                   OR cuenta_id IN (SELECT id FROM cuentas WHERE parent_id = $1)
            """, id_padre)

            # BORRAR LAS CUENTAS (HIJAS Y PADRE)
            # Al poner "id = $1 OR parent_id = $1" borramos tanto la principal como las subcuentas
            await conn.execute("""
                DELETE FROM cuentas 
                WHERE id = $1 OR parent_id = $1
            """, id_padre)

            print(f"🗑️ Cuenta '{nombre_borrar}', sus subcuentas y todos sus movimientos han sido eliminados.")
            return

        accion = datos.get('accion', 'crear')
        nombre_base = datos.get('nombre_cuenta', '').upper()
        tipo = datos.get('tipo', 'PRINCIPAL')
        
        try:
            saldo = float(datos.get('saldo', 0.0))
        except:
            saldo = 0.0

        parent_id = None
        nombre_final = nombre_base

        # --- LÓGICA DE PADRE E HIJO ---
        if datos.get('es_subcuenta') and datos.get('cuenta_padre'):
            nombre_padre = datos['cuenta_padre'].upper()
            
            # Buscamos el ID del padre
            fila_padre = await conn.fetchrow(
                "SELECT id FROM cuentas WHERE user_id = $1 AND nombre_cuenta = $2",
                user_id, nombre_padre
            )
            
            if fila_padre:
                parent_id = fila_padre['id']
                # Construimos nombre compuesto visual: "SANTANDER - AHORRO"
                nombre_final = f"{nombre_padre} - {nombre_base}"

            else:
                print(f"⚠️ Atención: No se encontró la cuenta padre '{nombre_padre}'. Se creará como principal.")
                tipo = 'PRINCIPAL' # Si no hay padre, la convertimos en principal por seguridad

        # --- INSERTAR O ACTUALIZAR ---
        await conn.execute(
            """INSERT INTO cuentas(user_id, nombre_cuenta, saldo_actual, tipo, parent_id) 
               VALUES($1, $2, $3, $4, $5)
               ON CONFLICT (user_id, nombre_cuenta) 
               DO UPDATE SET saldo_actual = $3""",
            user_id, nombre_final, saldo, tipo, parent_id
        )
        print(f"💾 Cuenta '{nombre_final}' (Padre ID: {parent_id}) guardada.")

        # ACTUALIZAR AL PADRE (SUMAR DINERO)
        if parent_id and saldo != 0 and accion == 'crear':
            
            await conn.execute(
                "UPDATE cuentas SET saldo_actual = saldo_actual + $1 WHERE id = $2",
                saldo, parent_id
            )
            print(f"💰 Se han SUMADO {saldo}€ a la cuenta Padre (ID {parent_id}).")

    except Exception as e:
        print(f"❌ Error DB: {e}")
    finally:
        await conn.close()

async def actualizar_cuenta_db(user_id, datos):
    """Función exclusiva para modificar el saldo o el nombre de una cuenta existente."""
    conn = await obtener_conexion()
    try:
        nombre_actual = datos.get('nombre_cuenta', '').upper()
        nuevo_nombre = datos.get('nuevo_nombre')
        
        saldo_raw = datos.get('saldo') if datos.get('saldo') is not None else datos.get('monto')
        nuevo_saldo = None
        if saldo_raw is not None:
            try:
                if isinstance(saldo_raw, str):
                    saldo_raw = saldo_raw.replace('€', '').replace('$', '').replace(',', '.').strip()
                nuevo_saldo = float(saldo_raw)
            except ValueError:
                print(f"⚠️ Atención: No se pudo convertir '{saldo_raw}' a número.")
                nuevo_saldo = None
        
        # Actualizar el saldo 
        if nuevo_saldo is not None:
            await conn.execute(
                "UPDATE cuentas SET saldo_actual = $1 WHERE user_id = $2 AND UPPER(nombre_cuenta) = $3",
                nuevo_saldo, user_id, nombre_actual
            )
            print(f"🔄 Saldo de '{nombre_actual}' actualizado a {nuevo_saldo}€.")

        # Actualizar el nombre 
        if nuevo_nombre:
            nuevo_nombre = nuevo_nombre.upper()
            # Si es subcuenta, el nuevo nombre también debe llevar el nombre del padre delante
            if " - " in nombre_actual:
                partes = nombre_actual.split(" - ")
                nombre_padre_real = partes[0].strip() 
                
                nuevo_nombre = f"{nombre_padre_real} - {nuevo_nombre}"

            await conn.execute(
                "UPDATE cuentas SET nombre_cuenta = $1 WHERE user_id = $2 AND UPPER(nombre_cuenta) = $3",
                nuevo_nombre, user_id, nombre_actual
            )
            print(f"📝 Nombre actualizado de '{nombre_actual}' a '{nuevo_nombre}'.")

    except Exception as e:
        print(f"❌ Error DB en actualizar_cuenta_db: {e}")
    finally:
        await conn.close()

# --- TRANSACIONES ---
async def registrar_transaccion(user_id, datos):
    conn = await obtener_conexion()
    
    try:
        tipo = datos.get('tipo', 'gasto').lower() 
        try:
            monto = float(datos.get('monto', 0.0))
        except:
            monto = 0.0
            
        concepto = datos.get('concepto', 'Varios')
        categoria = datos.get('categoria', 'Otros')
        nombre_cuenta_usuario = datos.get('cuenta')
        fecha_str = datos.get('fecha') 
        fecha_objeto = None

        if fecha_str:
            try:
                fecha_objeto = datetime.datetime.strptime(fecha_str, "%Y-%m-%d").date()
            except ValueError:
                print(f"⚠️ Formato de fecha extraño ({fecha_str}), usando fecha actual.")
                fecha_objeto = datetime.datetime.now()
        else:
            fecha_objeto = datetime.datetime.now()

        if not nombre_cuenta_usuario:
            print("❌ Error: La IA no detectó el nombre de la cuenta.")
            return False

        fila_cuenta = await conn.fetchrow(
            "SELECT id, parent_id FROM cuentas WHERE user_id = $1 AND nombre_cuenta = $2",
            user_id, nombre_cuenta_usuario.upper()
        )

        if not fila_cuenta:
            print(f"❌ Error: No existe la cuenta '{nombre_cuenta_usuario}'.")
            return False
        
        cuenta_id_real = fila_cuenta['id']
        parent_id = fila_cuenta['parent_id'] 

        # INSERTAR LA TRANSACCIÓN 
        await conn.execute(
            """INSERT INTO transacciones(user_id, cuenta_id, tipo, monto, concepto, categoria, fecha)
               VALUES($1, $2, $3, $4, $5, $6, $7)""",
            user_id, cuenta_id_real, tipo, monto, concepto, categoria, fecha_objeto
        )

        # PREPARAMOS LA LISTA DE CUENTAS A ACTUALIZAR
        # Siempre actualizamos la cuenta elegida
        ids_a_actualizar = [cuenta_id_real]
        
        # Si tiene padre (es subcuenta), añadimos al padre a la lista
        if parent_id is not None:
            ids_a_actualizar.append(parent_id)
            print(f"🔄 Detectada subcuenta. Se actualizará también la cuenta padre ID {parent_id}.")

        # BUCLE DE ACTUALIZACIÓN DE SALDOS
        # Recorremos la lista (puede ser solo 1 cuenta o 2 si es subcuenta)
        for id_cuenta in ids_a_actualizar:
            if tipo == 'ingreso':
                await conn.execute(
                    "UPDATE cuentas SET saldo_actual = saldo_actual + $1 WHERE id = $2", 
                    monto, id_cuenta
                )
            else: # Gasto
                await conn.execute(
                    "UPDATE cuentas SET saldo_actual = saldo_actual - $1 WHERE id = $2", 
                    monto, id_cuenta
                )

        print(f"✅ Saldos actualizados correctamente para: {ids_a_actualizar}")
        return True

    except Exception as e:
        print(f"❌ Error grave en transacciones: {e}")
        return False
    finally:
        await conn.close()


async def realizar_transferencia_db(user_id, datos):
    conn = await obtener_conexion()
    try:
        try: monto = float(datos.get('cantidad', 0.0))
        except: monto = 0.0
        
        origen_raw = (datos.get('cuenta_origen') or "").strip()
        destino_raw = (datos.get('cuenta_destino') or "").strip()

        if monto <= 0: return "❌ La cantidad debe ser positiva."

        # Traemos todo con los nombres de los padres
        sql_full = """
            SELECT c.id, c.nombre_cuenta, c.parent_id, p.nombre_cuenta as nombre_padre
            FROM cuentas c
            LEFT JOIN cuentas p ON c.parent_id = p.id
            WHERE c.user_id = $1
            ORDER BY p.nombre_cuenta NULLS FIRST, c.nombre_cuenta
        """
        todas_las_filas = await conn.fetch(sql_full, user_id)
        
        # Generamos la lista completa de botones
        opciones_menu_completo = [
            f"{r['nombre_cuenta']} ({r['nombre_padre'] or 'Principal'})" 
            for r in todas_las_filas
        ]

        # Solo aceptamos si el nombre es EXACTAMENTE igual al del botón
        fila_origen = next((r for r in todas_las_filas if f"{r['nombre_cuenta']} ({r['nombre_padre'] or 'Principal'})" == origen_raw), None)

        if not fila_origen:
            return {
                "status": "ambiguo", 
                "tipo": "origen", 
                "opciones": opciones_menu_completo 
            }

        fila_destino = next((r for r in todas_las_filas if f"{r['nombre_cuenta']} ({r['nombre_padre'] or 'Principal'})" == destino_raw), None)

        if not fila_destino:
            opciones_destino = [o for o in opciones_menu_completo if o != origen_raw]
            return {
                "status": "ambiguo", 
                "tipo": "destino", 
                "opciones": opciones_destino 
            }

        if fila_origen['id'] == fila_destino['id']: return "❌ Origen y destino son iguales."

        id_origen = fila_origen['id']
        id_destino = fila_destino['id']
        parent_origen = fila_origen['parent_id']
        parent_destino = fila_destino['parent_id']

        es_padre_a_hijo_directo = (parent_destino == id_origen)
        es_hijo_a_padre_directo = (parent_origen == id_destino)

        async with conn.transaction():
            if es_padre_a_hijo_directo:
                await conn.execute("UPDATE cuentas SET saldo_actual = saldo_actual + $1 WHERE id = $2", monto, id_destino)
                mensaje = f"✅ <b>Asignado:</b> {monto}€ al bolsillo {fila_destino['nombre_cuenta']}."
            elif es_hijo_a_padre_directo:
                await conn.execute("UPDATE cuentas SET saldo_actual = saldo_actual - $1 WHERE id = $2", monto, id_origen)
                mensaje = f"✅ <b>Liberado:</b> {monto}€ vuelven al saldo general de {fila_destino['nombre_cuenta']}."
            else:
                await conn.execute("UPDATE cuentas SET saldo_actual = saldo_actual - $1 WHERE id = $2", monto, id_origen)
                await conn.execute("UPDATE cuentas SET saldo_actual = saldo_actual + $1 WHERE id = $2", monto, id_destino)
                if parent_origen:
                    await conn.execute("UPDATE cuentas SET saldo_actual = saldo_actual - $1 WHERE id = $2", monto, parent_origen)
                if parent_destino:
                    await conn.execute("UPDATE cuentas SET saldo_actual = saldo_actual + $1 WHERE id = $2", monto, parent_destino)

                mensaje = f"🔄 <b>Movido:</b> {monto}€ de {fila_origen['nombre_cuenta']} a {fila_destino['nombre_cuenta']}."

            await conn.execute("""
                INSERT INTO transacciones (user_id, cuenta_id, tipo, monto, concepto, fecha) 
                VALUES ($1, $2, 'transferencia', $3, $4, NOW())
            """, user_id, id_destino, abs(monto), f"Desde {fila_origen['nombre_cuenta']}")

        return mensaje

    except Exception as e:
        print(f"Error DB: {e}")
        return f"❌ Error técnico: {e}"
    finally:
        await conn.close()

async def generar_resumen(user_id):
    """
    Genera un reporte visual del estado financiero del usuario.
    CORREGIDO: Conversión de tipos Decimal a float.
    """
    conn = await obtener_conexion()
    try:
        # Traemos todas las cuentas ordenadas por nombre
        filas = await conn.fetch("""
            SELECT id, nombre_cuenta, saldo_actual, parent_id, tipo 
            FROM cuentas 
            WHERE user_id = $1 
            ORDER BY nombre_cuenta ASC
        """, user_id)

        if not filas:
            return "🤷‍♂️ No tienes cuentas registradas todavía."

        principales = []
        subcuentas = {} 

        # Separar Padres e Hijos
        for f in filas:
            if f['parent_id'] is None:
                principales.append(f)
            else:
                p_id = f['parent_id']
                if p_id not in subcuentas:
                    subcuentas[p_id] = []
                subcuentas[p_id].append(f)

        mensaje = "📊 <b>ESTADO FINANCIERO ACTUAL</b>\n\n"
        total_patrimonio = 0.0 

        for p in principales:
            saldo_p = float(p['saldo_actual']) 
            
            total_patrimonio += saldo_p 
            
            icono = "🟢" if saldo_p > 0 else "🔴"
            
            mensaje += f"{icono} <b>{p['nombre_cuenta']}</b>: {saldo_p:,.2f}€\n"

            id_padre = p['id']
            if id_padre in subcuentas:
                for hija in subcuentas[id_padre]:
                    nombre_corto = hija['nombre_cuenta'].split(' - ')[-1] if ' - ' in hija['nombre_cuenta'] else hija['nombre_cuenta']
                    
                    saldo_hija = float(hija['saldo_actual'])
                    
                    mensaje += f"   └  <i>{nombre_corto}</i>: {saldo_hija:,.2f}€\n"
            
            mensaje += "\n" 

        mensaje += "--------------------------------\n"
        mensaje += f"💰 <b>TOTAL PATRIMONIO: {total_patrimonio:,.2f}€</b>"

        return mensaje

    finally:
        await conn.close()

async def consultar_movimientos_db(user_id, datos):
    conn = await obtener_conexion()
    try:
        periodo = datos.get('periodo')
        concepto = datos.get('filtro_concepto') 
        cuenta_nombre_input = datos.get('filtro_cuenta') 
        tipo = datos.get('tipo_movimiento') 
        fecha_str = datos.get('fecha')
        
        cuenta_id_filtro = None
        
        if cuenta_nombre_input:
            cuentas = await conn.fetch("SELECT id, nombre_cuenta, parent_id FROM cuentas WHERE user_id = $1", user_id)
            
            texto_limpio = cuenta_nombre_input.lower().strip() 
            for p in [" de ", " del ", " en ", " la ", " el ", " mi ", " mis "]:
                texto_limpio = texto_limpio.replace(p, " ")
            
            texto_limpio = " ".join(texto_limpio.split())
            palabras_busqueda = texto_limpio.split()

            candidatos = []
            
            for c in cuentas:
                nombre_db = c['nombre_cuenta'].lower()
                if all(palabra in nombre_db for palabra in palabras_busqueda):
                    candidatos.append(c)
            
            if len(candidatos) > 1:
                match_exacto = None
                for c in candidatos:
                    if c['nombre_cuenta'].lower() == texto_limpio:
                        match_exacto = c
                        break
                
                if match_exacto:
                    candidatos = [match_exacto] 

            if len(candidatos) == 0:
                 match_parcial = [c for c in cuentas if any(p in c['nombre_cuenta'].lower() for p in palabras_busqueda)]
                 if match_parcial:
                     return {
                        'status': 'ambiguo',
                        'tipo': 'cuenta',
                        'opciones': [c['nombre_cuenta'] for c in match_parcial]
                    }
                 return f"🤷‍♂️ No encontré ninguna cuenta que coincida con '{cuenta_nombre_input}'."
            
            elif len(candidatos) > 1:
                nombres = [c['nombre_cuenta'] for c in candidatos]
                return {
                    'status': 'ambiguo',
                    'tipo': 'cuenta',
                    'opciones': nombres
                }
            else:
                cuenta_id_filtro = candidatos[0]['id']

        mapa_meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }

        fecha_especifica = None
        if fecha_str:
            try:
                fecha_especifica = datetime.datetime.strptime(fecha_str, "%Y-%m-%d").date()
            except:
                pass

        params = [user_id]
        sql = """
            SELECT t.fecha, t.tipo, t.monto, t.concepto, c.nombre_cuenta 
            FROM transacciones t
            JOIN cuentas c ON t.cuenta_id = c.id
            WHERE t.user_id = $1
        """
        contador = 2 
        

        if cuenta_id_filtro:
            sql += f" AND (t.cuenta_id = ${contador} OR c.parent_id = ${contador})"
            params.append(cuenta_id_filtro)
            contador += 1

        if periodo and str(periodo).lower() in mapa_meses:
            mes_numero = mapa_meses[str(periodo).lower()]
            sql += f" AND EXTRACT(MONTH FROM t.fecha) = ${contador}"
            params.append(mes_numero)
            contador += 1
            sql += " AND EXTRACT(YEAR FROM t.fecha) = EXTRACT(YEAR FROM CURRENT_DATE)"

        elif periodo and str(periodo).isdigit() and 1 <= int(periodo) <= 12:
            sql += f" AND EXTRACT(MONTH FROM t.fecha) = ${contador}"
            params.append(int(periodo))
            contador += 1
            sql += " AND EXTRACT(YEAR FROM t.fecha) = EXTRACT(YEAR FROM CURRENT_DATE)"

        elif periodo in ['mes_actual', 'este mes']:
             sql += f" AND DATE_TRUNC('month', t.fecha) = DATE_TRUNC('month', CURRENT_DATE)"
             
        elif periodo in ['mes_anterior', 'mes pasado']:
             sql += f" AND DATE_TRUNC('month', t.fecha) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')"
             
        elif periodo == 'anio_actual':
             sql += f" AND DATE_TRUNC('year', t.fecha) = DATE_TRUNC('year', CURRENT_DATE)"
        
        elif fecha_especifica:
            sql += f" AND t.fecha::date = ${contador}"
            params.append(fecha_especifica)
            contador += 1
            
        if concepto:
            termino = concepto.strip()
            variantes = [termino]
            if len(termino) > 3 and termino.endswith('s'): variantes.append(termino[:-1])
            if len(termino) > 4 and termino.endswith('es'): variantes.append(termino[:-2])

            filtros_or = []
            for v in variantes:
                filtros_or.append(f"t.concepto ILIKE ${contador}")
                params.append(f"%{v}%")
                contador += 1
            sql += " AND (" + " OR ".join(filtros_or) + ")"

        if tipo and tipo != 'todo':
            if tipo == 'gasto': sql += " AND t.tipo = 'gasto'"
            elif tipo == 'ingreso': sql += " AND t.tipo = 'ingreso'"

        sql += " ORDER BY t.fecha DESC LIMIT 50"

        rows = await conn.fetch(sql, *params)
                
        titulo = "📊 <b>Movimientos"
        if cuenta_nombre_input:
            titulo += f" en {cuenta_nombre_input.upper()}"
        titulo += ":</b>\n\n"

        if not rows:
             return f"🤷‍♂️ No encontré movimientos para esa búsqueda."

        respuesta = titulo
        total = 0.0
        for r in rows:
            f_str = r['fecha'].strftime('%d/%m')
            icono = "🔴" if r['tipo'] == 'gasto' else "🟢"
            nombre_c = f"({r['nombre_cuenta']})" if not cuenta_id_filtro else ""
            
            respuesta += f"{icono} {r['monto']}€ | {r['concepto']}\n └ 📅 {f_str} {nombre_c}\n"
            
            if r['tipo'] == 'gasto': total -= float(r['monto'])
            else: total += float(r['monto'])
            
        respuesta += f"\n💰 <b>Total en esta lista:</b> {total:.2f}€"
        return respuesta

    except Exception as e:
        print(f"Error: {e}")
        return "Error consultando DB"
    finally:
        await conn.close()


async def consultar_datos_macro_db(datos):
    """Consulta las tablas ext_inflacion, ext_ine_consumo y ext_divisas."""
    conn = await obtener_conexion()
    tipo = datos.get('tipo_dato')
    params = datos.get('parametros', {})
    
    try:
        if tipo == 'inflacion':
            anio = params.get('anio')
            pais = params.get('pais', 'Spain')
            
            if not anio:
                sql = "SELECT valor_inflacion, anio FROM ext_inflacion WHERE pais=$1 ORDER BY anio DESC LIMIT 1"
                row = await conn.fetchrow(sql, pais)
            else:
                sql = "SELECT valor_inflacion, anio FROM ext_inflacion WHERE pais=$1 AND anio=$2"
                row = await conn.fetchrow(sql, pais, int(anio))
                
            if row:
                return f"📈 La inflación en **{pais}** en **{row['anio']}** fue del **{row['valor_inflacion']}%**."
            return f"🤷‍♂️ No tengo datos de inflación para {pais} (Año: {anio if anio else 'reciente'})."

        elif tipo == 'consumo_medio':
            categoria_input = params.get('categoria', 'Índice General') 
            anio_usuario = params.get('anio') 

            sql = """
                SELECT categoria, gasto_medio, anio 
                FROM ext_ine_consumo 
                WHERE categoria ILIKE $1 
            """
            
            argumentos = [f"%{categoria_input}%"]

            if anio_usuario:
                sql += " AND anio = $2"
                argumentos.append(int(anio_usuario))
            else:
                sql += " ORDER BY anio DESC LIMIT 1"

            row = await conn.fetchrow(sql, *argumentos)

            if row:
                gasto_fmt = "{:,.2f}".format(row['gasto_medio']).replace(",", "X").replace(".", ",").replace("X", ".")
                
                return f"📊 El gasto medio en España en **{row['categoria']}** (Año {row['anio']}) es de **{gasto_fmt}€**."
            
            return f"🤷‍♂️ No encuentro datos del INE que coincidan con '{categoria_input}'."

        elif tipo == 'divisa_historica':
            fecha = params.get('fecha')
            if not fecha: return "Necesito una fecha específica."
            
            try:
                fecha_obj = datetime.datetime.strptime(fecha, "%Y-%m-%d").date()
            except ValueError:
                return "⚠️ Formato de fecha inválido. Usa YYYY-MM-DD."
            
            row = await conn.fetchrow(
                "SELECT euro_usd FROM ext_divisas WHERE fecha = $1", 
                fecha_obj
            )
            if row:
                return f"💱 El cambio Euro/Dólar el día {fecha} estaba a **{row['euro_usd']}**."
            return f"🤷‍♂️ No tengo el cambio registrado para el {fecha}."

        return "⚠️ Tipo de dato macro no reconocido."

    except Exception as e:
        return f"❌ Error consultando datos externos: {e}"
    finally:
        await conn.close()