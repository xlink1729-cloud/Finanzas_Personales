import streamlit as st
import pandas as pd
import psycopg2
import bcrypt
import re
from datetime import datetime, date
from zoneinfo import ZoneInfo
import plotly.express as px
import hashlib

# =============================================================================
# ZONA HORARIA LOCAL (MÉXICO)
# =============================================================================
TIMEZONE_MEXICO = ZoneInfo('America/Mexico_City')

def obtener_fecha_local():
    return datetime.now(TIMEZONE_MEXICO).date()

# =============================================================================
# 1. CONFIGURACIÓN DE LA PÁGINA STREAMLIT
# =============================================================================
st.set_page_config(
    page_title="Finanzas Personales - Control Quincenal e Inversiones",
    page_icon="💰",
    layout="wide"
)

# =============================================================================
# 2. CONTROL DE ACCESO Y AUTENTICACIÓN MULTIUSUARIO (BCRYPT)
# =============================================================================
def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

def generar_hash_password(password: str) -> str:
    """Genera un hash seguro para la contraseña."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verificar_password(password: str, hashed_password: str) -> bool:
    """
    Verifica la contraseña ingresada soportando:
    1. Bcrypt ($2a$, $2b$)
    2. SHA-256 (64 caracteres)
    3. Texto plano (Retrocompatibilidad)
    """
    if not hashed_password:
        return False
        
    hashed_password = hashed_password.strip()
    
    # 1. Verificación con Bcrypt
    if hashed_password.startswith("$2a$") or hashed_password.startswith("$2b$"):
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
            
    # 2. Verificación con SHA-256 (Hashes de 64 caracteres de la versión anterior)
    if len(hashed_password) == 64 and not hashed_password.startswith("$"):
        hash_ingresado = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return hash_ingresado.lower() == hashed_password.lower()
            
    # 3. Verificación con Texto Plano
    return password == hashed_password

def validar_usuario_db(username, password):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password_hash FROM usuarios WHERE LOWER(username) = %s",
                (username.lower().strip(),)
            )
            user = cur.fetchone()
            
            if user:
                user_id, user_name, pass_hash = user
                if verificar_password(password, pass_hash):
                    return (user_id, user_name)
            
            return None
                
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"Error en la autenticación: {e}")
        return None
    finally:
        if conn:
            conn.close()
            
def registrar_usuario_db(username, password, nombre):
    """Inserta un nuevo usuario en la base de datos PostgreSQL/Neon."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Verificar si el usuario ya existe
        cur.execute("SELECT id FROM usuarios WHERE LOWER(username) = %s;", (username.lower().strip(),))
        if cur.fetchone():
            return False, "El nombre de usuario ya existe. Intenta con otro."
        
        # Encriptar y guardar incluyendo el campo 'nombre'
        pass_hash = generar_hash_password(password)
        cur.execute(
            "INSERT INTO usuarios (username, nombre, password_hash) VALUES (%s, %s, %s);",
            (username.strip(), nombre.strip(), pass_hash)
        )
        conn.commit()
        cur.close()
        return True, "¡Cuenta creada con éxito! Ahora puedes iniciar sesión."
    
    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Error al registrar usuario: {e}"
    finally:
        if conn:
            conn.close()
            
def mostrar_login():
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #2b3a67 0%, #496a81 35%, #669bbc 70%, #8c7a6b 100%);
        }
        header {visibility: hidden;}

        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
        }

        div[data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.22);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-radius: 25px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.25);
            padding: 25px 30px 35px 30px;
            max-width: 440px;
            margin: auto;
        }

        div[data-testid="stForm"] label,
        div[data-testid="stForm"] label p {
            color: #ffffff !important;
            font-weight: 600 !important;
        }

        div[data-testid="stForm"] input {
            background-color: rgba(43, 67, 99, 0.65) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 8px !important;
        }
        
        div[data-testid="stForm"] input::placeholder {
            color: rgba(255, 255, 255, 0.6) !important;
        }

        div[data-testid="stForm"] button[type="submit"] {
            background: #ffffff !important;
            color: #2b3a67 !important;
            border: none !important;
            border-radius: 20px !important;
            padding: 10px 20px !important;
            font-weight: bold !important;
            width: 100% !important;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2) !important;
            transition: all 0.3s ease !important;
            margin-top: 15px;
        }
        
        div[data-testid="stForm"] button[type="submit"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.3) !important;
        }

        /* Estilo para las pestañas dentro del login */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            justify-content: center;
        }
        .stTabs [data-baseweb="tab"] {
            color: white !important;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
        with col_img2:
            try:
                st.image("static/logo.png", use_container_width=True)
            except Exception:
                pass

        with st.form("form_auth"):
            st.markdown("<h2 style='text-align: center; color: white; margin-bottom: 10px; font-weight: 700;'>FINSMART</h2>", unsafe_allow_html=True)
            
            tab_log, tab_reg = st.tabs(["🔑 Iniciar Sesión", "📝 Crear Cuenta"])
            
            with tab_log:
                usuario_log = st.text_input("👤 Usuario", key="log_user", placeholder="Ingresa tu usuario")
                pass_log = st.text_input("🔒 Contraseña", type="password", key="log_pass", placeholder="Ingresa tu contraseña")
                submit_log = st.form_submit_button("LOGIN", use_container_width=True)
                
                if submit_log:
                    if not usuario_log or not pass_log:
                        st.warning("Completa todos los campos.")
                    else:
                        user_data = validar_usuario_db(usuario_log, pass_log)
                        if user_data:
                            st.session_state["autenticado"] = True
                            st.session_state["user_id"] = user_data[0]
                            st.session_state["username"] = user_data[1]
                            st.rerun()
                        else:
                            st.error("Usuario o contraseña incorrectos.")

            with tab_reg:
                nombre_reg = st.text_input("👤 Tu Nombre", key="reg_nombre", placeholder="Ej. Juan Pérez")
                usuario_reg = st.text_input("👤 Usuario", key="reg_user", placeholder="Crea un nombre de usuario")
                pass_reg1 = st.text_input("🔒 Contraseña", type="password", key="reg_pass1", placeholder="Mínimo 6 caracteres")
                pass_reg2 = st.text_input("🔒 Confirmar Contraseña", type="password", key="reg_pass2", placeholder="Repite tu contraseña")
                submit_reg = st.form_submit_button("CREAR CUENTA", use_container_width=True)
                
                if submit_reg:
                    if not nombre_reg or not usuario_reg or not pass_reg1 or not pass_reg2:
                        st.warning("Por favor completa todos los campos.")
                    elif pass_reg1 != pass_reg2:
                        st.error("Las contraseñas no coinciden.")
                    elif len(pass_reg1) < 6:
                        st.warning("La contraseña debe tener al menos 6 caracteres.")
                    else:
                        exito, msj = registrar_usuario_db(usuario_reg, pass_reg1, nombre_reg)
                        if exito:
                            st.success(msj)
                        else:
                            st.error(msj)

# --- CONTROL DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    mostrar_login()
    st.stop()

USER_ID = st.session_state.get("user_id")

if not USER_ID:
    st.warning("Sesión no válida. Por favor, vuelve a iniciar sesión.")
    st.stop()

# 🔍 DIAGNÓSTICO EN TIEMPO REAL
st.sidebar.error(f"👤 Usuario: {st.session_state.get('username')}")
st.sidebar.error(f"🆔 ID en sesión: {st.session_state.get('user_id')}")

# =============================================================================
# 3. SIDEBAR Y MODO PRIVACIDAD
# =============================================================================
st.sidebar.title(f"👤 Dashboard — {st.session_state.get('username', 'Usuario')}")

ocultar_saldos = st.sidebar.toggle(
    "🙈 Modo Privacidad", 
    value=False, 
    help="Oculta los montos de ingresos, balance y saldos de pantalla."
)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state.pop("user_id", None)
    st.session_state.pop("username", None)
    st.rerun()

def fmt_monto(valor):
    if ocultar_saldos:
        return "$ ••••••"
    return f"${valor:,.2f}"

# =============================================================================
# 4. CAPA DE BASE DE DATOS (POSTGRESQL MULTIUSUARIO)
# =============================================================================
def obtener_movimientos(user_id):
    conn = None
    try:
        conn = get_connection()
        query = """
            SELECT id, fecha, tipo, categoria, monto, descripcion 
            FROM movimientos 
            WHERE user_id = %s 
            ORDER BY fecha DESC, id DESC
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
        return df
    except Exception as e:
        st.error(f"Error al consultar la base de datos: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def guardar_movimiento(tipo, monto, categoria, descripcion, fecha, user_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO movimientos (tipo, monto, categoria, descripcion, fecha, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (tipo, monto, categoria, descripcion.strip(), fecha, user_id)
        )
        conn.commit()
        cur.close()
        st.cache_data.clear()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"Error al guardar en la base de datos: {e}")
        return False
    finally:
        if conn:
            conn.close()

def eliminar_movimiento(id_mov, user_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM movimientos WHERE id = %s AND user_id = %s", (id_mov, user_id))
        conn.commit()
        cur.close()
        st.cache_data.clear()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"Error al eliminar el registro: {e}")
        return False
    finally:
        if conn:
            conn.close()

def actualizar_movimiento(id_movimiento, tipo, monto, categoria, descripcion, fecha, user_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            UPDATE movimientos 
            SET tipo = %s, monto = %s, categoria = %s, descripcion = %s, fecha = %s, user_id = %s
            WHERE id = %s AND user_id = %s
        """
        cur.execute(query, (tipo, monto, categoria, descripcion, fecha, user_id, id_movimiento, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"Error al actualizar: {e}")
        return False
    finally:
        if conn:
            conn.close()

# =============================================================================
# 5. ESTRUCTURA PRINCIPAL DEL DASHBOARD
# =============================================================================
st.title("💰 Control de Finanzas e Inversiones")

tab_flujo, tab_ahorros, tab_presupuesto, tab_efectivo = st.tabs([
    "💵 Flujo Quincenal y Nómina", 
    "📈 Portafolio de Inversiones (CETES, Fintual)",
    "📊 Presupuesto Mensual (Regla 50 / 30 / 20)",
    "👛 Billetera y Efectivo"
])

# =============================================================================
# PESTAÑA 1: FLUJO QUINCENAL Y NÓMINA
# =============================================================================
with tab_flujo:
    
    with st.expander("➕ Registrar Movimiento de Nómina, Gastos o Retiros", expanded=True):
        tipo = st.selectbox(
            "Tipo de Movimiento", 
            ["Egreso", "Ingreso", "Retiro"],
            key="selector_tipo_movimiento"
        )
        
        if tipo == "Ingreso":
            categorias_dinamicas = [
                "Nómina / Sueldo Quincenal", 
                "Retiro de Inversión a Débito", 
                "Ventas / Ingresos Extra", 
                "Otros Ingresos"
            ]
        elif tipo == "Retiro":
            categorias_dinamicas = [
                "Retiro de Cajero (Débito ➔ Efectivo)",
                "Traspaso entre Cuentas"
            ]
        else:
            categorias_dinamicas = [
                "Pago TDC (Tarjeta de Crédito)", 
                "Aportación a Inversión (Enviado a CETES/Fintual)",
                "Alimentación / Súper", 
                "Vivienda / Servicios", 
                "Transporte / Gasolina", 
                "Salud / Gastos Médicos", 
                "Ocio / Entretenimiento", 
                "Suscripciones", 
                "Otros Egresos"
            ]

        with st.form("form_finanzas", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                monto = st.number_input("Monto ($)", min_value=0.01, step=50.0, format="%.2f")
                metodo_pago = st.selectbox("Forma de Pago / Origen", ["💳 Tarjeta de Débito (Nómina)", "💵 Efectivo"])
            
            with col2:
                categoria = st.selectbox("Categoría", categorias_dinamicas)
                fecha = st.date_input("Fecha de Operación", obtener_fecha_local(), key="fecha_flujo")

            with col3:
                descripcion_user = st.text_input(
                    "Descripción / Detalle", 
                    placeholder="Ej. Depósito nómina, Cena, Súper, etc.", 
                    max_chars=120
                )
                submit = st.form_submit_button("💾 Guardar Registro", use_container_width=True)

            if submit:
                desc_final = f"[{metodo_pago}] {descripcion_user}".strip()
                if guardar_movimiento(tipo, monto, categoria, desc_final, fecha, USER_ID):
                    st.success(f"✅ {tipo} ({categoria}) registrado con éxito.")
                    st.rerun()

    st.markdown("---")

    df_raw = obtener_movimientos(USER_ID)

    if not df_raw.empty:
        mask_inversion = df_raw['categoria'].str.contains("inversi", case=False, na=False) | \
                         df_raw['tipo'].str.contains("inversi", case=False, na=False)
        
        df_flujo = df_raw[~mask_inversion].copy()
        
        if not df_flujo.empty:
            df_flujo['fecha'] = pd.to_datetime(df_flujo['fecha'])
            
            fecha_local_actual = obtener_fecha_local()
            hoy_ts = pd.Timestamp(fecha_local_actual)
            hoy_date = fecha_local_actual

            st.markdown("### 📅 Ciclo de Nómina Actual")
            
            # --- REGLA DINÁMICA POR ÚLTIMA NÓMINA REGISTRADA ---
            df_nominas = df_flujo[
                (df_flujo['tipo'] == 'Ingreso') & 
                (df_flujo['categoria'].str.contains("Nómina", case=False, na=False))
            ].sort_values('fecha', ascending=False)

            if not df_nominas.empty:
                # La fecha de inicio es el día que ingresó el último pago de nómina
                ultima_nomina = df_nominas.iloc[0]
                inicio_q = pd.Timestamp(ultima_nomina['fecha'])
                nomina_ingresada_ciclo = float(ultima_nomina['monto'])
                etiqueta_q = f"Ciclo Activo (Nómina del {inicio_q.strftime('%d/%m/%Y')})"
            else:
                # Regla de respaldo si aún no hay nóminas registradas en el sistema
                inicio_q = hoy_ts.replace(day=1)
                nomina_ingresada_ciclo = 0.0
                etiqueta_q = "Ciclo Inicial (Sin registro de nómina)"

            # El ciclo abarca desde el día del último pago registrado hasta hoy
            fin_q = hoy_ts 

            # Filtrar los movimientos que corresponden a este ciclo activo
            df_q_actual = df_flujo[(df_flujo['fecha'] >= inicio_q.normalize()) & (df_flujo['fecha'] <= fin_q.normalize())]
            
            # --- CÁLCULOS ACUMULADOS HISTÓRICOS ---
            mask_debito_global = df_flujo['descripcion'].str.contains("Débito", na=False) | (~df_flujo['descripcion'].str.contains("Efectivo", na=False))
            ingresos_totales_historicos = df_flujo[df_flujo['tipo'] == 'Ingreso']['monto'].sum()
            gastos_debito_historicos = df_flujo[(df_flujo['tipo'] == 'Egreso') & mask_debito_global]['monto'].sum()
            retiros_historicos = df_flujo[df_flujo['tipo'] == 'Retiro']['monto'].sum()
            
            # Saldo disponible real en la cuenta de débito
            nomina_restante = ingresos_totales_historicos - gastos_debito_historicos - retiros_historicos

            # Gastos del ciclo actual
            mask_debito_q = df_q_actual['descripcion'].str.contains("Débito", na=False) | (~df_q_actual['descripcion'].str.contains("Efectivo", na=False))
            gastos_debito_ciclo = df_q_actual[(df_q_actual['tipo'] == 'Egreso') & mask_debito_q]['monto'].sum()
            gastos_efectivo_ciclo = df_q_actual[(df_q_actual['tipo'] == 'Egreso') & df_q_actual['descripcion'].str.contains("Efectivo", na=False)]['monto'].sum()

            st.markdown(f"#### 📊 Resumen: **{etiqueta_q}**")
            col_q1, col_q2, col_q3, col_q4 = st.columns(4)
            
            col_q1.metric("💵 Saldo Real en Débito (Acumulado)", fmt_monto(nomina_restante), help="Sueldo histórico menos gastos en débito y retiros de cajero.")
            col_q2.metric("💳 Gastos con Débito (Ciclo)", fmt_monto(gastos_debito_ciclo), delta_color="inverse")
            col_q3.metric("💵 Gastos en Efectivo (Ciclo)", fmt_monto(gastos_efectivo_ciclo), delta_color="inverse")
            col_q4.metric("🏦 Nómina Recibida", fmt_monto(nomina_ingresada_ciclo))

            # --- PROYECTAR PRÓXIMA META OFICIAL DE CALENDARIO (15 O FIN DE MES) ---
            dia_pago = inicio_q.day

            # Si el pago ingresó a fin de mes/inicios de mes (días 25 a 5), la meta del próximo pago es el 15
            if dia_pago >= 25 or dia_pago <= 5:
                if inicio_q.day >= 25:
                    mes_target = inicio_q.month + 1 if inicio_q.month < 12 else 1
                    anio_target = inicio_q.year if inicio_q.month < 12 else inicio_q.year + 1
                    fecha_estimada_fin = pd.Timestamp(year=anio_target, month=mes_target, day=15)
                else:
                    fecha_estimada_fin = inicio_q.replace(day=15)
            # Si el pago ingresó en quincena (días 6 a 24), la meta es el último día del mes
            else:
                proximo_mes = (inicio_q.replace(day=28) + pd.Timedelta(days=4))
                fecha_estimada_fin = proximo_mes.replace(day=1) - pd.Timedelta(days=1)

            # Días faltantes reales hasta la fecha meta
            dias_restantes = max((fecha_estimada_fin.date() - hoy_date).days + 1, 1)
            gasto_diario_sugerido = nomina_restante / dias_restantes if nomina_restante > 0 else 0.00

            # --- PORCENTAJE SEGURO BASADO EN LA NÓMINA ACTIVA ---
            if nomina_ingresada_ciclo > 0:
                porcentaje_gastado = (gastos_debito_ciclo / nomina_ingresada_ciclo) * 100
            else:
                porcentaje_gastado = 0.0

            st.markdown("---")
            st.markdown("### 🚨 Control de Ritmo de Gasto y Freno de Mano")

            col_f1, col_f2, col_f3 = st.columns(3)

            col_f1.metric("⏳ Días Est. para Próximo Pago", f"{dias_restantes} días", delta=f"Proyectado al {fecha_estimada_fin.strftime('%d/%m')}")
            col_f2.metric("💳 Gasto Diario Máximo Sugerido", fmt_monto(gasto_diario_sugerido), help="Saldo Real en Débito dividido entre días faltantes estimados.")

            if porcentaje_gastado < 70:
                col_f3.success(f"🟢 **Ritmo Saludable**\n\nHas consumido el {porcentaje_gastado:.1f}% de la nómina de esta quincena.")
            elif porcentaje_gastado <= 90:
                col_f3.warning(f"🟡 **Precaución**\n\nHas consumido el {porcentaje_gastado:.1f}% de la nómina de esta quincena.")
            else:
<<<<<<< HEAD
                col_f3.error(f"🔴 **FRENO DE MANO**\n\nHas consumido el {porcentaje_gastado:.1f}% del depósito de esta quincena.")

            # --- MÓDULO: ANÁLISIS DE HÁBITOS E INSIGHTS (PUNTO 4) ---
            st.markdown("---")
            st.markdown("### 📊 Análisis de Hábitos y Fugas de Dinero")

            col_a1, col_a2 = st.columns(2)

            with col_a1:
                st.markdown("#### 🚨 Top 3 Fugas del Ciclo Activo")
                # Filtrar solo egresos del ciclo quincenal actual
                df_egresos_q = df_flujo[(df_flujo['tipo'] == 'Egreso') & 
                                        (df_flujo['fecha'] >= inicio_q.normalize()) & 
                                        (df_flujo['fecha'] <= fin_q.normalize())]

                if not df_egresos_q.empty:
                    top_categorias = df_egresos_q.groupby('categoria')['monto'].sum().reset_index()
                    top_categorias = top_categorias.sort_values(by='monto', ascending=False).head(3)

                    for idx, row in top_categorias.iterrows():
                        pct_cat = (row['monto'] / nomina_ingresada_ciclo * 100) if nomina_ingresada_ciclo > 0 else 0
                        st.write(f"• **{row['categoria']}**: {fmt_monto(row['monto'])} *({pct_cat:.1f}% de la nómina)*")
                else:
                    st.info("Aún no hay egresos registrados en esta quincena.")

            with col_a2:
                st.markdown("#### 🔄 Comparativa vs. Quincena Anterior")
                
                # Buscar en la base de datos para identificar el ciclo anterior
                df_nominas = df_flujo[
                    (df_flujo['tipo'] == 'Ingreso') & 
                    (df_flujo['categoria'].str.contains("Nómina", case=False, na=False))
                ].sort_values('fecha', ascending=False)

                if len(df_nominas) >= 2:
                    nomina_anterior = df_nominas.iloc[1]
                    inicio_q_prev = pd.Timestamp(nomina_anterior['fecha'])
                    fin_q_prev = inicio_q - pd.Timedelta(days=1)

                    df_q_prev = df_flujo[(df_flujo['fecha'] >= inicio_q_prev.normalize()) & (df_flujo['fecha'] <= fin_q_prev.normalize())]
                    gastos_previos = df_q_prev[df_q_prev['tipo'] == 'Egreso']['monto'].sum()

                    diferencia = gastos_debito_ciclo - gastos_previos
                    pct_variacion = ((gastos_debito_ciclo - gastos_previos) / gastos_previos * 100) if gastos_previos > 0 else 0.0

                    if diferencia > 0:
                        st.metric(
                            label="Gasto Acumulado Actual vs. Anterior", 
                            value=fmt_monto(gastos_debito_ciclo), 
                            delta=f"+{fmt_monto(diferencia)} ({pct_variacion:+.1f}%)",
                            delta_color="inverse",
                            help="Estás gastando MÁS que en el mismo punto de la quincena anterior."
                        )
                    else:
                        st.metric(
                            label="Gasto Acumulado Actual vs. Anterior", 
                            value=fmt_monto(gastos_debito_ciclo), 
                            delta=f"{fmt_monto(diferencia)} ({pct_variacion:+.1f}%)",
                            delta_color="inverse",
                            help="Estás gastando MENOS que la quincena anterior."
                        )
                else:
                    st.info("Registra al menos dos pagos de nómina para habilitar la comparativa interquincenal.")

=======
                col_f3.error(f"🔴 **FRENO DE MANO**\n\nHas consumido el {porcentaje_gastado:.1f}% de la nómina de esta quincena.")
                
>>>>>>> 7dd3622f3ff8d6fe137531814e775752d1d28654
            st.markdown("---")

            st.markdown("### 📈 Distribución de Gastos: Fijos vs. Variables vs. Inversión")

            categorias_fijas = [
                "Servicios (Luz, Agua, Gas, Internet)", "Supermercado / Despensa", 
                "Renta / Vivienda", "Transporte / Gasolina", "Pago TDC (Tarjeta de Crédito)", "Salud / Gastos Médicos"
            ]

            categorias_variables = [
                "Restaurantes / Salidas", "Ocio / Entretenimiento", "Compras Personales", 
                "Suscripciones", "Gastos Hormiga / Varios", "Alimentación / Súper", "Otros Egresos"
            ]

            df_gastos_ciclo = df_flujo[(df_flujo['tipo'] == 'Egreso') & 
                                       (df_flujo['fecha'] >= inicio_q.normalize()) & 
                                       (df_flujo['fecha'] <= fin_q.normalize())].copy()

            if not df_gastos_ciclo.empty:
                def clasificar_gasto(cat):
                    if cat in categorias_fijas:
                        return "Necesidades / Fijos 🏠"
                    elif cat in categorias_variables:
                        return "Estilo de Vida / Variables 🎭"
                    elif "Inversión" in cat or "Ahorro" in cat:
                        return "Ahorro / Inversión 🎯"
                    else:
                        return "Otros / Sin Clasificar ❓"

                df_gastos_ciclo['Tipo_Estructura'] = df_gastos_ciclo['categoria'].apply(clasificar_gasto)

                df_resumen_tipo = df_gastos_ciclo.groupby('Tipo_Estructura')['monto'].sum().reset_index()
                total_gastado = df_resumen_tipo['monto'].sum()
                df_resumen_tipo['Porcentaje'] = (df_resumen_tipo['monto'] / total_gastado) * 100

                col_pie1, col_pie2 = st.columns([1, 1])

                with col_pie1:
                    fig = px.pie(
                        df_resumen_tipo, 
                        values='monto', 
                        names='Tipo_Estructura', 
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    fig.update_traces(textinfo='percent+label')
                    fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig, use_container_width=True)

                with col_pie2:
                    st.subheader("Desglose General")
                    for idx, row in df_resumen_tipo.iterrows():
                        st.write(f"**{row['Tipo_Estructura']}:** {fmt_monto(row['monto'])} ({row['Porcentaje']:.1f}%)")

                st.markdown("---")
                st.markdown("### 🗓️ Comportamiento de Gasto por Semana")

                df_gastos_ciclo['semana_num'] = df_gastos_ciclo['fecha'].dt.strftime('%W').astype(int)
                df_gastos_ciclo['semana_lbl'] = "Semana " + df_gastos_ciclo['semana_num'].astype(str)

                gasto_semanal = df_gastos_ciclo.groupby(['semana_num', 'semana_lbl'])['monto'].sum().reset_index().sort_values('semana_num')

                col_graf, col_resumen = st.columns([2, 1])

                with col_graf:
                    st.markdown("**Gasto Acumulado por Semana**")
                    st.bar_chart(gasto_semanal, x='semana_lbl', y='monto', color="#2E7D32")

                with col_resumen:
                    st.markdown("**Resumen Semanal:**")
                    promedio_sem = gasto_semanal['monto'].mean() if not gasto_semanal.empty else 0.0
                    
                    if ocultar_saldos:
                        st.metric("Promedio por Semana", "$ ••••••")
                        df_mostrar_sem = gasto_semanal[['semana_lbl', 'monto']].copy()
                        df_mostrar_sem['monto'] = "$ ••••••"
                        st.dataframe(df_mostrar_sem, column_config={"semana_lbl": "Semana", "monto": "Total Gastado"}, hide_index=True)
                    else:
                        st.metric("Promedio por Semana", fmt_monto(promedio_sem))
                        st.dataframe(
                            gasto_semanal[['semana_lbl', 'monto']],
                            column_config={
                                "semana_lbl": "Semana",
                                "monto": st.column_config.NumberColumn("Total Gastado", format="$%.2f")
                            },
                            hide_index=True
                        )

                with st.expander("🔍 Ver desglose de gastos de una semana específica"):
                    semanas_disponibles = gasto_semanal['semana_lbl'].tolist()
                    
                    if semanas_disponibles:
                        semana_seleccionada = st.selectbox("Selecciona la semana a revisar:", semanas_disponibles)
                        
                        df_desglose_semana = df_gastos_ciclo[df_gastos_ciclo['semana_lbl'] == semana_seleccionada].copy()
                        df_desglose_semana['fecha_str'] = df_desglose_semana['fecha'].dt.strftime('%Y-%m-%d')
                        
                        st.markdown(f"**Movimientos registrados en la {semana_seleccionada}:**")
                        
                        columnas_mostrar = ['fecha_str', 'categoria', 'descripcion', 'monto']
                        
                        if ocultar_saldos:
                            df_desglose_show = df_desglose_semana[columnas_mostrar].copy()
                            df_desglose_show['monto'] = "$ ••••••"
                            st.dataframe(
                                df_desglose_show,
                                column_config={
                                    "fecha_str": "Fecha",
                                    "categoria": "Categoría",
                                    "descripcion": "Descripción / Notas",
                                    "monto": "Monto"
                                },
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.dataframe(
                                df_desglose_semana[columnas_mostrar],
                                column_config={
                                    "fecha_str": "Fecha",
                                    "categoria": "Categoría",
                                    "descripcion": "Descripción / Notas",
                                    "monto": st.column_config.NumberColumn("Monto", format="$%.2f")
                                },
                                use_container_width=True,
                                hide_index=True
                            )
                    else:
                        st.info("No hay registros de gasto para desglosar.")

            else:
                st.info("Aún no hay gastos registrados dentro de este ciclo quincenal para generar desgloses semanales o gráficos de pastel.")

            st.markdown("---")

            st.markdown("### 📋 Historial Completo de Nómina y Gastos")
            df_display = df_flujo.copy()
            df_display['fecha_str'] = df_display['fecha'].dt.strftime('%Y-%m-%d')
            
            config_columnas = {
                "id": st.column_config.NumberColumn("ID", format="%d"),
                "fecha_str": "Fecha",
                "tipo": "Tipo",
                "categoria": "Categoría",
                "monto": st.column_config.NumberColumn("Monto", format="$%.2f"),
                "descripcion": "Descripción"
            }

            if ocultar_saldos:
                df_display_show = df_display.copy()
                df_display_show['monto'] = "••••••"
                st.dataframe(
                    df_display_show[['id', 'fecha_str', 'tipo', 'categoria', 'monto', 'descripcion']],
                    column_config=config_columnas,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.dataframe(
                    df_display[['id', 'fecha_str', 'tipo', 'categoria', 'monto', 'descripcion']],
                    column_config=config_columnas,
                    use_container_width=True,
                    hide_index=True
                )

            st.markdown("---")
            with st.expander("✏️ Editar o Eliminar un Registro de la Lista"):
                opciones_registros = {
                    f"ID {row['id']} | {row['fecha_str']} - {row['descripcion']} (${row['monto']:,.2f})": row['id']
                    for _, row in df_display.iterrows()
                }
                
                if opciones_registros:
                    registro_sel = st.selectbox("Selecciona el registro a modificar:", list(opciones_registros.keys()))
                    id_seleccionado = opciones_registros[registro_sel]
                    
                    datos_reg = df_display[df_display['id'] == id_seleccionado].iloc[0]
                    
                    col_edit1, col_edit2 = st.columns(2)
                    
                    with col_edit1:
                        st.markdown("#### 🔄 Editar Registro")
                        with st.form("form_editar_flujo"):
                            e_fecha = st.date_input("Fecha Correcta", datos_reg['fecha'].date())
                            
                            tipos_op = ["Egreso", "Ingreso", "Retiro", "Inversion"]
                            idx_tipo = tipos_op.index(datos_reg['tipo']) if datos_reg['tipo'] in tipos_op else 0
                            e_tipo = st.selectbox("Tipo", tipos_op, index=idx_tipo)
                            
                            e_monto = st.number_input("Monto Correcto ($)", value=float(datos_reg['monto']), min_value=0.01, step=10.0, format="%.2f")
                            
                            cats_edit = [
                                "Nómina / Sueldo Quincenal", "Retiro de Inversión a Débito", "Ventas / Ingresos Extra", "Otros Ingresos",
                                "Retiro de Cajero (Débito ➔ Efectivo)", "Traspaso entre Cuentas",
                                "Pago TDC (Tarjeta de Crédito)", "Aportación a Inversión (Enviado a CETES/Fintual)",
                                "Alimentación / Súper", "Vivienda / Servicios", "Transporte / Gasolina", 
                                "Salud / Gastos Médicos", "Ocio / Entretenimiento", "Suscripciones", "Otros Egresos"
                            ]
                            idx_cat = cats_edit.index(datos_reg['categoria']) if datos_reg['categoria'] in cats_edit else 0
                            e_cat = st.selectbox("Categoría", cats_edit, index=idx_cat)
                            e_desc = st.text_input("Descripción", value=datos_reg['descripcion'])
                            
                            btn_actualizar = st.form_submit_button("💾 Guardar Cambios")
                            if btn_actualizar:
                                if actualizar_movimiento(id_seleccionado, e_tipo, e_monto, e_cat, e_desc, e_fecha, USER_ID):
                                    st.success("✅ Registro actualizado correctamente.")
                                    st.rerun()

                    with col_edit2:
                        st.markdown("#### 🗑️ Eliminar Registro")
                        st.warning("Esta acción borrará el registro de la base de datos de forma permanente.")
                        if st.button("❌ Borrar Registro Seleccionado", use_container_width=True):
                            if eliminar_movimiento(id_seleccionado, USER_ID):
                                st.success("✅ Registro eliminado.")
                                st.rerun()

        else:
            st.info("Aún no tienes movimientos de nómina o gastos registrados.")
    else:
        st.info("Aún no hay registros en la base de datos.")

# =============================================================================
# PESTAÑA 2: PORTAFOLIO DE INVERSIONES
# =============================================================================
with tab_ahorros:
    st.markdown("### 📈 Portafolio de Inversiones (CETES, Fintual, etc.)")
    st.caption("Esta sección analiza únicamente tus cuentas de inversión y su rendimiento.")

    current_user_id = st.session_state.get("user_id")

    with st.expander("➕ Registrar / Actualizar Saldo de Inversión", expanded=True):
        with st.form("form_inversiones", clear_on_submit=True):
            col_inv1, col_inv2, col_inv3 = st.columns(3)
            
            with col_inv1:
                plataforma = st.selectbox(
                    "Plataforma / Fondo",
                    ["Nu (Cajita)", "CETES Directo", "Finsus", "Fintual", "Mercado Pago / Fondo", "GBM / Acciones", "Fondo de Emergencia", "Otra Plataforma"]
                )
                monto_inv = st.number_input("Saldo Total Actual ($)", min_value=0.01, step=100.0, format="%.2f")
                tasa_anual_inv = st.number_input("Tasa de Rendimiento Anual (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.2f")

            with col_inv2:
                tipo_operacion = st.selectbox(
                    "Tipo de Movimiento", 
                    ["Actualización de Saldo Total", "Aportación Directa", "Retiro Parcial/Total"]
                )
                fecha_inv = st.date_input("Fecha", obtener_fecha_local(), key="fecha_inv")

            with col_inv3:
                notas_inv = st.text_input("Notas / Detalle", placeholder="Ej. Saldo al revisar la app hoy")
                
                ganancia_mensual_prev = (monto_inv * (tasa_anual_inv / 100)) / 12
                st.caption(f"💡 **Rendimiento est.:** +${ganancia_mensual_prev:,.2f} MXN/mes")
                
                submit_inv = st.form_submit_button("💾 Guardar y Actualizar Inversiones", use_container_width=True)

            if submit_inv:
                desc_completa = f"[{plataforma} | Tasa: {tasa_anual_inv:.2f}%] {tipo_operacion}: {notas_inv}".strip()
                categoria_inv = f"Inversión - {plataforma}"
                
                if guardar_movimiento("Inversion", monto_inv, categoria_inv, desc_completa, fecha_inv, current_user_id):
                    st.success(f"✅ Portafolio de {plataforma} actualizado con tasa del {tasa_anual_inv:.2f}%.")
                    st.rerun()

    st.markdown("---")

    df_raw = obtener_movimientos(current_user_id)
    
    if not df_raw.empty:
        plataformas_conocidas = ["fintual", "cetes", "nu", "finsus", "mercado pago", "gbm", "emergencia"]
        mask_inv = (
            df_raw['categoria'].str.contains("inversi", case=False, na=False) |
            df_raw['tipo'].str.contains("inversi", case=False, na=False) |
            df_raw['categoria'].str.lower().str.contains('|'.join(plataformas_conocidas), na=False)
        )
        
        df_inversiones = df_raw[mask_inv].copy()
        
        if not df_inversiones.empty:
            def extraer_datos_inv(row):
                cat = str(row['categoria'])
                desc = str(row['descripcion'])
                
                if "Inversión - " in cat:
                    plat = cat.replace("Inversión - ", "").strip()
                elif "Inversion - " in cat:
                    plat = cat.replace("Inversion - ", "").strip()
                elif desc.startswith("[") and "]" in desc:
                    plat = desc[1:desc.find("]")].split("|")[0].strip()
                else:
                    plat = "General"
                
                tasa = 0.0
                match_tasa = re.search(r"Tasa:\s*([\d\.]+)%", desc)
                if match_tasa:
                    try:
                        tasa = float(match_tasa.group(1))
                    except ValueError:
                        tasa = 0.0
                        
                return pd.Series([plat, tasa], index=['Plataforma', 'Tasa (%)'])

            df_inversiones[['Plataforma', 'Tasa (%)']] = df_inversiones.apply(extraer_datos_inv, axis=1)
            df_inversiones['fecha'] = pd.to_datetime(df_inversiones['fecha'])
            df_inversiones = df_inversiones.sort_values(by=['Plataforma', 'fecha', 'id'])

            resumen_filas = []

            for plat, group in df_inversiones.groupby('Plataforma'):
                ultimos_registros = group.tail(2)
                registro_actual = ultimos_registros.iloc[-1]
                saldo_actual = registro_actual['monto']
                tasa_actual = registro_actual['Tasa (%)']
                
                ganancia_anual = saldo_actual * (tasa_actual / 100)
                ganancia_mensual = ganancia_anual / 12

                if len(ultimos_registros) > 1:
                    saldo_anterior = ultimos_registros.iloc[-2]['monto']
                    variacion = saldo_actual - saldo_anterior
                    porcentaje_var = (variacion / saldo_anterior) * 100 if saldo_anterior > 0 else 0
                else:
                    variacion = 0.0
                    porcentaje_var = 0.0

                resumen_filas.append({
                    "Plataforma": plat,
                    "Saldo Actual": saldo_actual,
                    "Tasa Anual (%)": tasa_actual,
                    "Ganancia Est. / Mes": ganancia_mensual,
                    "Variación ($)": variacion,
                    "Variación (%)": porcentaje_var
                })

            df_resumen_inv = pd.DataFrame(resumen_filas)
            total_inversiones = df_resumen_inv['Saldo Actual'].sum()
            total_variacion = df_resumen_inv['Variación ($)'].sum()
            total_rendimiento_mensual = df_resumen_inv['Ganancia Est. / Mes'].sum()

            METAS_PLATAFORMA = {
                "Fintual": 10000.0,
                "Nu (Cajita)": 10000.0,
                "CETES Directo": 20000.0,
            }

            META_INVERSION_TOTAL = sum(METAS_PLATAFORMA.values())
            faltante_meta = max(0.0, META_INVERSION_TOTAL - total_inversiones)
            progreso_pct = min(100.0, (total_inversiones / META_INVERSION_TOTAL) * 100) if META_INVERSION_TOTAL > 0 else 0

            st.markdown("### 📊 Valor Total del Portafolio de Inversión")
            col_met1, col_met2, col_met3, col_met4 = st.columns(4)
            
            col_met1.metric("Patrimonio Invertido Total", fmt_monto(total_inversiones))
            
            if ocultar_saldos:
                col_met2.metric("Rendimiento Mensual Est.", "$ ••••••")
                col_met3.metric("Última Variación", "$ ••••••")
                col_met4.metric("Faltante p/ Meta Total", "$ ••••••", f"{progreso_pct:.1f}% Alcanzado")
            else:
                col_met2.metric(
                    "Rendimiento Mensual Est.", 
                    f"${total_rendimiento_mensual:,.2f}", 
                    delta=f"+${total_rendimiento_mensual * 12:,.2f}/año",
                    delta_color="normal"
                )
                col_met3.metric(
                    "Última Variación", 
                    f"${total_variacion:,.2f}", 
                    delta=f"${total_variacion:,.2f}",
                    delta_color="normal"
                )
                col_met4.metric("Faltante p/ Meta Total", f"${faltante_meta:,.2f}", f"{progreso_pct:.1f}% Alcanzado")

            st.caption(f"Progreso global hacia la meta de **{fmt_monto(META_INVERSION_TOTAL)}**")
            st.progress(progreso_pct / 100.0)

            st.markdown("#### 🎯 Progreso de Metas Específicas")
            cols_m = st.columns(len(METAS_PLATAFORMA))

            for idx, (plat_nombre, meta_monto) in enumerate(METAS_PLATAFORMA.items()):
                with cols_m[idx]:
                    row_plat = df_resumen_inv[df_resumen_inv['Plataforma'].str.contains(plat_nombre.split()[0], case=False, na=False)]
                    saldo_plat = row_plat['Saldo Actual'].values[0] if not row_plat.empty else 0.0
                    tasa_plat = row_plat['Tasa Anual (%)'].values[0] if not row_plat.empty else 0.0
                    
                    pct_plat = min(100.0, (saldo_plat / meta_monto) * 100) if meta_monto > 0 else 0
                    
                    st.markdown(f"**{plat_nombre}** `{tasa_plat:.2f}%`")
                    if ocultar_saldos:
                        st.caption(f"Meta: {fmt_monto(meta_monto)}")
                        st.progress(pct_plat / 100.0)
                        st.text(f"•••••• ({pct_plat:.1f}%)")
                    else:
                        st.caption(f"{fmt_monto(saldo_plat)} de {fmt_monto(meta_monto)}")
                        st.progress(pct_plat / 100.0)
                        st.text(f"{pct_plat:.1f}% alcanzado")

            st.markdown("---")

            col_ah1, col_ah2 = st.columns(2)

            with col_ah1:
                st.subheader("Distribución de Inversiones")
                st.bar_chart(df_resumen_inv, x='Plataforma', y='Saldo Actual', color="#29B6F6")

            with col_ah2:
                st.subheader("Saldos y Rendimiento por Instrumento")
                df_mostrar_resumen = df_resumen_inv.copy()

                if ocultar_saldos:
                    df_mostrar_resumen['Saldo Actual'] = "$ ••••••"
                    df_mostrar_resumen['Tasa Anual (%)'] = "••• %"
                    df_mostrar_resumen['Ganancia Est. / Mes'] = "$ ••••••"
                    df_mostrar_resumen['Variación ($)'] = "$ ••••••"
                    df_mostrar_resumen['Variación (%)'] = "••• %"
                    st.dataframe(df_mostrar_resumen, use_container_width=True, hide_index=True)
                else:
                    st.dataframe(
                        df_mostrar_resumen,
                        column_config={
                            "Plataforma": "Fondo / Plataforma",
                            "Saldo Actual": st.column_config.NumberColumn("Saldo Actual", format="$%.2f"),
                            "Tasa Anual (%)": st.column_config.NumberColumn("Tasa Anual", format="%.2f%%"),
                            "Ganancia Est. / Mes": st.column_config.NumberColumn("Est. Ganancia/Mes", format="$%.2f"),
                            "Variación ($)": st.column_config.NumberColumn("Ganancia / Pérdida ($)", format="$%.2f"),
                            "Variación (%)": st.column_config.NumberColumn("Cambio (%)", format="%.2f%%")
                        },
                        use_container_width=True,
                        hide_index=True
                    )

            st.markdown("---")

            st.markdown("#### 📋 Historial de Registros de Inversión")
            df_inv_disp = df_inversiones[['id', 'fecha', 'Plataforma', 'Tasa (%)', 'monto', 'descripcion']].sort_values(by='fecha', ascending=False).copy()
            df_inv_disp['fecha_str'] = df_inv_disp['fecha'].dt.strftime('%Y-%m-%d')
            
            config_inv_cols = {
                "id": st.column_config.NumberColumn("ID", format="%d"),
                "fecha_str": "Fecha",
                "Plataforma": "Plataforma",
                "Tasa (%)": st.column_config.NumberColumn("Tasa (%)", format="%.2f%%"),
                "monto": st.column_config.NumberColumn("Saldo Registrado", format="$%.2f"),
                "descripcion": "Notas"
            }

            if ocultar_saldos:
                df_inv_disp_show = df_inv_disp.copy()
                df_inv_disp_show['monto'] = "••••••"
                st.dataframe(df_inv_disp_show[['id', 'fecha_str', 'Plataforma', 'Tasa (%)', 'monto', 'descripcion']], column_config=config_inv_cols, use_container_width=True, hide_index=True)
            else:
                st.dataframe(
                    df_inv_disp[['id', 'fecha_str', 'Plataforma', 'Tasa (%)', 'monto', 'descripcion']],
                    column_config=config_inv_cols,
                    use_container_width=True,
                    hide_index=True
                )

            with st.expander("✏️ Editar o Eliminar un Registro de Inversión"):
                opciones_inv = {
                    f"ID {row['id']} | {row['fecha_str']} - {row['Plataforma']} (${row['monto']:,.2f})": row['id']
                    for _, row in df_inv_disp.iterrows()
                }
                if opciones_inv:
                    reg_inv_sel = st.selectbox("Selecciona registro de inversión:", list(opciones_inv.keys()))
                    id_inv_sel = opciones_inv[reg_inv_sel]
                    
                    datos_inv_reg = df_inv_disp[df_inv_disp['id'] == id_inv_sel].iloc[0]
                    
                    col_einv1, col_einv2 = st.columns(2)
                    
                    with col_einv1:
                        st.markdown("#### 🔄 Editar Inversión")
                        with st.form("form_edit_inv"):
                            ei_fecha = st.date_input("Fecha Correcta", datos_inv_reg['fecha'].date())
                            ei_monto = st.number_input("Saldo Correcto ($)", value=float(datos_inv_reg['monto']), min_value=0.01, step=100.0, format="%.2f")
                            ei_tasa = st.number_input("Tasa Anual Correcta (%)", value=float(datos_inv_reg['Tasa (%)']), min_value=0.0, max_value=100.0, step=0.1, format="%.2f")
                            ei_desc = st.text_input("Notas", value=datos_inv_reg['descripcion'])
                            
                            btn_act_inv = st.form_submit_button("💾 Guardar Cambios en Inversión")
                            if btn_act_inv:
                                desc_editada = f"[{datos_inv_reg['Plataforma']} | Tasa: {ei_tasa:.2f}%] {ei_desc}".strip()
                                if actualizar_movimiento(id_inv_sel, "Inversion", ei_monto, f"Inversión - {datos_inv_reg['Plataforma']}", desc_editada, ei_fecha, current_user_id):
                                    st.success("✅ Registro de inversión actualizado.")
                                    st.rerun()

                    with col_einv2:
                        st.markdown("#### 🗑️ Eliminar Inversión")
                        if st.button("❌ Borrar Registro de Inversión", use_container_width=True):
                            if eliminar_movimiento(id_inv_sel, current_user_id):
                                st.success("✅ Registro eliminado.")
                                st.rerun()

        else:
            st.info("Aún no has registrado cuentas en tu portafolio de inversión.")
    else:
        st.info("No hay datos registrados aún.")

# =============================================================================
# PESTAÑA 3: PRESUPUESTO 50/30/20 & FLUJO QUINCENAL
# =============================================================================
with tab_presupuesto:
    st.markdown("### 📊 Presupuesto Mensual (Regla 50 / 30 / 20)")
    st.caption("Planifica tus finanzas sobre tu ingreso total estimado del mes y monitorea el avance quincenal.")

    current_user_id = st.session_state.get("user_id")
    df_raw = obtener_movimientos(current_user_id)

    with st.expander("⚙️ Configurar Ingreso Mensual Base", expanded=False):
        col_inc1, col_inc2 = st.columns(2)
        with col_inc1:
            ingreso_q1 = st.number_input("Ingreso Neto 1.ª Quincena ($)", min_value=0.0, value=10000.0, step=500.0, format="%.2f")
        with col_inc2:
            ingreso_q2 = st.number_input("Ingreso Neto 2.ª Quincena ($)", min_value=0.0, value=10000.0, step=500.0, format="%.2f")
        
        ingreso_mensual_total = ingreso_q1 + ingreso_q2
        st.info(f"💡 **Ingreso Total Estimado del Mes:** {fmt_monto(ingreso_mensual_total)}")

    limite_necesidades = ingreso_mensual_total * 0.50
    limite_deseos = ingreso_mensual_total * 0.30
    limite_ahorro = ingreso_mensual_total * 0.20

    st.markdown("---")

    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric(
        label="🏠 50% Necesidades / Fijos", 
        value=fmt_monto(limite_necesidades), 
        help="Renta, plan celular, despensa básica y servicios vitales."
    )
    col_p2.metric(
        label="🎉 30% Deseos / Estilo de Vida", 
        value=fmt_monto(limite_deseos), 
        help="Salidas de fin de semana, hobbies, entretenimiento."
    )
    col_p3.metric(
        label="🛡️ 20% Ahorro / Inversión", 
        value=fmt_monto(limite_ahorro), 
        help="Fondo de emergencia, Cajita Nu, Cetes, Finsus."
    )

    st.markdown("---")

    if not df_raw.empty:
        df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
        
        fecha_actual = obtener_fecha_local()
        df_mes = df_raw[(df_raw['fecha'].dt.month == fecha_actual.month) & (df_raw['fecha'].dt.year == fecha_actual.year)].copy()

        mask_gastos = df_mes['tipo'].str.lower().str.contains("gasto|salida|egreso", na=False)
        df_gastos_mes = df_mes[mask_gastos].copy()

        mask_fijos = df_gastos_mes['categoria'].str.lower().str.contains("renta|celular|plan|servicio|luz|agua|despensa", na=False)
        mask_ahorro = df_gastos_mes['tipo'].str.lower().str.contains("inversion|ahorro", na=False) | df_gastos_mes['categoria'].str.lower().str.contains("inversi|ahorro", na=False)
        mask_deseos = ~mask_fijos & ~mask_ahorro

        gasto_fijos_real = df_gastos_mes[mask_fijos]['monto'].sum()
        gasto_ahorro_real = df_gastos_mes[mask_ahorro]['monto'].sum()
        gasto_deseos_real = df_gastos_mes[mask_deseos]['monto'].sum()

    else:
        gasto_fijos_real = 0.0
        gasto_deseos_real = 0.0
        gasto_ahorro_real = 0.0

    st.markdown("#### 📈 Ejecución de tu Presupuesto este Mes")

    col_b1, col_b2, col_b3 = st.columns(3)

    with col_b1:
        st.markdown("**🏠 Gastos Fijos / Necesidades**")
        pct_fijos = min(1.0, gasto_fijos_real / limite_necesidades) if limite_necesidades > 0 else 0
        st.progress(pct_fijos)
        if ocultar_saldos:
            st.caption("•••••• de ••••••")
        else:
            st.caption(f"Gastado: **${gasto_fijos_real:,.2f}** / **${limite_necesidades:,.2f}** ({pct_fijos*100:.1f}%)")

    with col_b2:
        st.markdown("**🎉 Deseos y Salidas (Efectivo / Gustos)**")
        pct_deseos = min(1.0, gasto_deseos_real / limite_deseos) if limite_deseos > 0 else 0
        st.progress(pct_deseos)
        if ocultar_saldos:
            st.caption("•••••• de ••••••")
        else:
            st.caption(f"Gastado: **${gasto_deseos_real:,.2f}** / **${limite_deseos:,.2f}** ({pct_deseos*100:.1f}%)")
            st.info(f"💡 Te quedan **${max(0.0, limite_deseos - gasto_deseos_real):,.2f}** libres para salidas.")

    with col_b3:
        st.markdown("**🛡️ Meta de Ahorro e Inversión (20%)**")
        pct_ahorro = min(1.0, gasto_ahorro_real / limite_ahorro) if limite_ahorro > 0 else 0
        st.progress(pct_ahorro)
        if ocultar_saldos:
            st.caption("•••••• de ••••••")
        else:
            st.caption(f"Aportado: **${gasto_ahorro_real:,.2f}** / **${limite_ahorro:,.2f}** ({pct_ahorro*100:.1f}%)")

    st.markdown("---")

    st.markdown("### 🗓️ Estrategia de Flujo de Caja Quincenal")
    st.caption("Nivelación de compromisos entre la 1.ª y 2.ª Quincena.")

    tab_q1_p, tab_q2_p = st.tabs(["1.ª Quincena (Días 1 - 15)", "2.ª Quincena (Días 16 - Fin de mes)"])

    with tab_q1_p:
        st.markdown("#### 🟢 1.ª Quincena (Ciclo Ligero)")
        col_q1_a, col_q1_b = st.columns(2)
        
        with col_q1_a:
            st.subheader("Compromisos Obligatorios")
            st.markdown("- **Salidas Fines de Semana (2 fines):** ~$3,200.00 MXN *(Efectivo)*")
            st.markdown("- **Reserva 50% de Renta:** Apartar para la 2ª Quincena.")
            st.markdown("- **Págate a ti mismo (10% Ahorro Q1):** Directo a Nu / Cetes.")
        
        with col_q1_b:
            st.warning("💡 **Tip Q1:** Como no pagas Renta en esta quincena, **guarda el 50% de la renta en una Cajita** inmediatamente al cobrar para que no sientas la 2ª quincena pesada.")

    with tab_q2_p:
        st.markdown("#### 🔴 2.ª Quincena (Ciclo Pesado)")
        col_q2_a, col_q2_b = st.columns(2)
        
        with col_q2_a:
            st.subheader("Compromisos Obligatorios")
            st.markdown("- **Renta:** Pago completo (Completado con reserva de la Q1).")
            st.markdown("- **Plan de Celular:** Pago recurrente.")
            st.markdown("- **Salidas Fines de Semana (2 fines):** ~$3,200.00 MXN *(Efectivo)*")
            st.markdown("- **Págate a ti mismo (10% Ahorro Q2):** Directo a Nu / Cetes.")
            
        with col_q2_b:
            st.success("✅ Si apartaste el 50% de la renta durante la Q1, esta quincena fluirá con la misma tranquilidad que la primera.")

# =============================================================================
# PESTAÑA 4: BILLETERA Y EFECTIVO
# =============================================================================
with tab_efectivo:
    st.header("👛 Control de Billetera y Efectivo")
    st.caption("Administra los billetes que retiras del cajero o ajusta tu saldo físico sin alterar tu saldo bancario.")

    col_ef1, col_ef2 = st.columns(2)

    # -------------------------------------------------------------------------
    # 1. ENTRADA DE EFECTIVO / AJUSTE
    # -------------------------------------------------------------------------
    with col_ef1:
        st.subheader("1. 📥 Entrada de Efectivo / Ajuste")
        
        tipo_entrada = st.radio(
            "Origen del Dinero", 
            ["🏦 Retiro de Cajero (Descuenta de Débito)", "💵 Ajuste / Dinero Extra (NO afecta Débito)"],
            help="Usa 'Ajuste' si tenías efectivo guardado previamente o no quieres que reste a tu nómina."
        )

        with st.form("form_retiro_efectivo", clear_on_submit=True):
            monto_retiro = st.number_input("Monto ($)", min_value=1.0, step=10.0, format="%.2f")
            fecha_retiro = st.date_input("Fecha", obtener_fecha_local(), key="fecha_retiro_ef")
            desc_retiro = st.text_input("Detalle / Notas", placeholder="Ej. Cajero Santander / Efectivo que ya tenía")
            
            submit_retiro = st.form_submit_button("💾 Guardar Entrada a Billetera", use_container_width=True)

        if submit_retiro:
            if "Retiro de Cajero" in tipo_entrada:
                tipo_db = "Retiro"
                cat_entrada = "Retiro de Cajero (Débito ➔ Efectivo)"
                desc_ret_final = f"[💳 Tarjeta de Débito (Nómina)] Retiro Cajero: {desc_retiro}".strip()
            else:
                tipo_db = "Ingreso"
                cat_entrada = "Ajuste de Efectivo"
                desc_ret_final = f"[💵 Efectivo] Ajuste de saldo previo en cartera: {desc_retiro}".strip()

            if guardar_movimiento(tipo_db, monto_retiro, cat_entrada, desc_ret_final, fecha_retiro, USER_ID):
                st.success(f"✅ Se agregaron {fmt_monto(monto_retiro)} a tu Billetera.")
                st.rerun()

    # -------------------------------------------------------------------------
    # 2. SALIDA DE EFECTIVO / GASTOS
    # -------------------------------------------------------------------------
    with col_ef2:
        st.subheader("2. 💸 Registrar Gasto Realizado en Efectivo")
        st.info("Esto descuenta directamente del efectivo de tu bolsillo y asigna la categoría de gasto.")
        
        with st.form("form_gasto_efectivo", clear_on_submit=True):
            monto_gasto_e = st.number_input("Monto Gastado ($)", min_value=0.01, step=10.0, format="%.2f")
            cat_gasto_e = st.selectbox("Categoría del Gasto", [
                "Alimentación / Súper", 
                "Transporte / Gasolina", 
                "Ocio / Entretenimiento", 
                "Vivienda / Servicios", 
                "Salud / Gastos Médicos", 
                "Otros Egresos"
            ])
            fecha_gasto_e = st.date_input("Fecha del Gasto", obtener_fecha_local(), key="fecha_gasto_ef")
            desc_gasto_e = st.text_input("Detalle del Gasto", placeholder="Ej. Tacos, Pasaje, Propina, etc.")
            
            submit_gasto_e = st.form_submit_button("💸 Registrar Salida de Billetera", use_container_width=True)

        if submit_gasto_e:
            desc_ge_final = f"[💵 Efectivo] {desc_gasto_e}".strip()
            if guardar_movimiento("Egreso", monto_gasto_e, cat_gasto_e, desc_ge_final, fecha_gasto_e, USER_ID):
                st.success(f"✅ Gasto de {fmt_monto(monto_gasto_e)} en {cat_gasto_e} registrado.")
                st.rerun()

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 3. METRICAS Y TABLA DE HISTORIAL EXCLUSIVO DE EFECTIVO
    # -------------------------------------------------------------------------
    df_raw_efectivo = obtener_movimientos(USER_ID)

    if not df_raw_efectivo.empty:
        mask_entradas_efectivo = (
            (df_raw_efectivo['tipo'] == 'Retiro') | 
            (df_raw_efectivo['categoria'] == 'Ajuste de Efectivo')
        )
        total_retirado = df_raw_efectivo[mask_entradas_efectivo]['monto'].sum()
        
        mask_gastos_efectivo = (
            df_raw_efectivo['descripcion'].str.contains("efectivo", case=False, na=False) & 
            (~mask_entradas_efectivo)
        )
        total_gastado_efectivo = df_raw_efectivo[mask_gastos_efectivo]['monto'].sum()
        saldo_billetera_actual = total_retirado - total_gastado_efectivo

        st.markdown("### 📊 Balance Actual de la Billetera")
        
        c_b1, c_b2, c_b3 = st.columns(3)
        c_b1.metric("📥 Total Entradas / Retiros", fmt_monto(total_retirado))
        c_b2.metric("💸 Total Gastado en Efectivo", fmt_monto(total_gastado_efectivo), delta_color="inverse")
        c_b3.metric("💵 Disponible en Bolsillo / Billetera", fmt_monto(saldo_billetera_actual))

        st.markdown("---")
        st.markdown("### 📋 Historial Exclusivo de Efectivo")
        
        mask_movs_efectivo = mask_entradas_efectivo | mask_gastos_efectivo
        df_hist_efectivo = df_raw_efectivo[mask_movs_efectivo].copy()

        if not df_hist_efectivo.empty:
            df_hist_efectivo['fecha_str'] = pd.to_datetime(df_hist_efectivo['fecha']).dt.strftime('%Y-%m-%d')
            
            config_ef_cols = {
                "id": st.column_config.NumberColumn("ID", format="%d"),
                "fecha_str": "Fecha",
                "tipo": "Operación",
                "categoria": "Categoría",
                "monto": st.column_config.NumberColumn("Monto ($)", format="$%.2f"),
                "descripcion": "Detalle"
            }

            if ocultar_saldos:
                df_hist_show = df_hist_efectivo.copy()
                df_hist_show['monto'] = "••••••"
                st.dataframe(df_hist_show[['id', 'fecha_str', 'tipo', 'categoria', 'monto', 'descripcion']], column_config=config_ef_cols, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_hist_efectivo[['id', 'fecha_str', 'tipo', 'categoria', 'monto', 'descripcion']], column_config=config_ef_cols, use_container_width=True, hide_index=True)

            # -----------------------------------------------------------------
            # 4. EDICIÓN / ELIMINACIÓN CON OPCIÓN DE CANCELAR
            # -----------------------------------------------------------------
            st.markdown("---")
            st.markdown("### 🛠️ Modificar o Eliminar Registro de Efectivo")
            
            lista_ids_efectivo = df_hist_efectivo['id'].tolist()
            id_sel_ef = st.selectbox("Selecciona el ID del registro a gestionar:", lista_ids_efectivo, key="sb_id_efectivo")
            
            # Obtener datos del registro seleccionado
            row_sel_ef = df_hist_efectivo[df_hist_efectivo['id'] == id_sel_ef].iloc[0]
            
            # Inicializar estado para mostrar/ocultar el panel de modificación
            if "mostrar_edit_ef" not in st.session_state:
                st.session_state.mostrar_edit_ef = False

            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("✏️ Editar Registro", use_container_width=True, key="btn_abrir_edit_ef"):
                    st.session_state.mostrar_edit_ef = True

            with col_btn2:
                # Confirmación previa de eliminación para evitar borrados accidentales
                if st.button("🗑️ Eliminar Registro", use_container_width=True, type="secondary", key="btn_del_ef"):
                    st.session_state.confirmar_del_ef = True

            # Diálogo / Alerta de Confirmación de Borrado
            if st.session_state.get("confirmar_del_ef", False):
                st.warning(f"⚠️ ¿Estás seguro de que deseas eliminar el registro ID **{id_sel_ef}** ({row_sel_ef['descripcion']} - {fmt_monto(row_sel_ef['monto'])})?")
                c_del_confirm, c_del_cancel = st.columns(2)
                
                with c_del_confirm:
                    if st.button("🔴 Sí, Eliminar Definitivamente", use_container_width=True, type="primary"):
                        if eliminar_movimiento_db(id_sel_ef, USER_ID):
                            st.session_state.confirmar_del_ef = False
                            st.success("✅ Registro eliminado correctamente.")
                            st.rerun()
                            
                with c_del_cancel:
                    if st.button("❌ Cancelar Eliminación", use_container_width=True):
                        st.session_state.confirmar_del_ef = False
                        st.info("Operación de eliminación cancelada.")
                        st.rerun()

            # Formulario desplegable para Edición con botón de Cancelar
            if st.session_state.mostrar_edit_ef:
                st.info(f"Editando registro ID #{id_sel_ef}")
                with st.form("form_editar_efectivo"):
                    e_monto = st.number_input("Monto ($)", value=float(row_sel_ef['monto']), min_value=0.01, step=10.0, format="%.2f")
                    e_fecha = st.date_input("Fecha", pd.to_datetime(row_sel_ef['fecha']).date())
                    e_categoria = st.text_input("Categoría", value=str(row_sel_ef['categoria']))
                    e_desc = st.text_input("Descripción / Detalle", value=str(row_sel_ef['descripcion']))
                    
                    c_edit_save, c_edit_cancel = st.columns(2)
                    with c_edit_save:
                        submit_edit = st.form_submit_button("💾 Guardar Cambios", use_container_width=True, type="primary")
                    with c_edit_cancel:
                        cancel_edit = st.form_submit_button("❌ Cancelar Modificación", use_container_width=True)

                    if submit_edit:
                        if actualizar_movimiento_db(id_sel_ef, row_sel_ef['tipo'], e_monto, e_categoria, e_desc, e_fecha, USER_ID):
                            st.session_state.mostrar_edit_ef = False
                            st.success("✅ Registro actualizado con éxito.")
                            st.rerun()
                            
                    if cancel_edit:
                        st.session_state.mostrar_edit_ef = False
                        st.info("Modificación cancelada.")
                        st.rerun()

        else:
            st.info("Aún no tienes movimientos registrados en efectivo.")
    else:
        st.info("No hay datos suficientes para calcular el balance de la billetera.")
