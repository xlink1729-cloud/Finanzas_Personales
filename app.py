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
# CONFIGURACIÓN DE ZONA HORARIA LOCAL (MÉXICO)
# =============================================================================
TIMEZONE_MEXICO = ZoneInfo('America/Mexico_City')

def obtener_fecha_local():
    """Obtiene la fecha actual ajustada explícitamente a la zona horaria de Ciudad de México."""
    return datetime.now(TIMEZONE_MEXICO).date()

# =============================================================================
# 1. CONFIGURACIÓN INICIAL DE LA PÁGINA STREAMLIT
# =============================================================================
st.set_page_config(
    page_title="Finanzas Personales - Control Quincenal e Inversiones",
    page_icon="💰",
    layout="wide"
)

# =============================================================================
# 2. CONTROL DE ACCESO, AUTENTICACIÓN Y SEGURIDAD MULTIUSUARIO (BCRYPT)
# =============================================================================
def get_connection():
    """Establece conexión activa a la base de datos PostgreSQL/Neon."""
    return psycopg2.connect(st.secrets["DATABASE_URL"])

def generar_hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verificar_password(password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
        
    hashed_password = hashed_password.strip()
    
    if hashed_password.startswith("$2a$") or hashed_password.startswith("$2b$"):
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
            
    if len(hashed_password) == 64 and not hashed_password.startswith("$"):
        hash_ingresado = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return hash_ingresado.lower() == hashed_password.lower()
            
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
            if user and verificar_password(password, user[2]):
                return (user[0], user[1])
            return None
    except Exception as e:
        if conn: conn.rollback()
        st.error(f"Error en la autenticación: {e}")
        return None
    finally:
        if conn: conn.close()
            
def registrar_usuario_db(username, password, nombre):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM usuarios WHERE LOWER(username) = %s;", (username.lower().strip(),))
        if cur.fetchone():
            return False, "El nombre de usuario ya existe. Intenta con otro."
        
        pass_hash = generar_hash_password(password)
        cur.execute(
            "INSERT INTO usuarios (username, nombre, password_hash) VALUES (%s, %s, %s);",
            (username.strip(), nombre.strip(), pass_hash)
        )
        conn.commit()
        cur.close()
        return True, "¡Cuenta creada con éxito! Ahora puedes iniciar sesión."
    except Exception as e:
        if conn: conn.rollback()
        return False, f"Error al registrar usuario: {e}"
    finally:
        if conn: conn.close()
            
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
            try: st.image("static/logo.png", use_container_width=True)
            except Exception: pass

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
                        if exito: st.success(msj)
                        else: st.error(msj)

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    mostrar_login()
    st.stop()

USER_ID = st.session_state.get("user_id")

if not USER_ID:
    st.warning("Sesión no válida. Por favor, vuelve a iniciar sesión.")
    st.stop()

# =============================================================================
# 3. SIDEBAR Y PRIVACIDAD
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
# 4. CAPA DE BASE DE DATOS
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
        return pd.read_sql_query(query, conn, params=(user_id,))
    except Exception as e:
        st.error(f"Error al consultar la base de datos: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()

def guardar_movimiento(tipo, monto, categoria, descripcion, fecha, user_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO movimientos (tipo, monto, categoria, descripcion, fecha, user_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (tipo, monto, categoria, descripcion.strip(), fecha, user_id)
        )
        conn.commit()
        cur.close()
        st.cache_data.clear()
        return True
    except Exception as e:
        if conn: conn.rollback()
        st.error(f"Error al guardar: {e}")
        return False
    finally:
        if conn: conn.close()

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
        if conn: conn.rollback()
        st.error(f"Error al eliminar: {e}")
        return False
    finally:
        if conn: conn.close()

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
        if conn: conn.rollback()
        st.error(f"Error al actualizar: {e}")
        return False
    finally:
        if conn: conn.close()

# =============================================================================
# 5. ESTRUCTURA PRINCIPAL DEL DASHBOARD
# =============================================================================
st.title("💰 Control de Finanzas e Inversiones")

tab_kpis, tab_flujo, tab_ahorros, tab_presupuesto, tab_efectivo = st.tabs([
    "🎯 Resumen Ejecutivo (KPIs)",
    "💵 Flujo Quincenal y Nómina", 
    "📈 Portafolio de Inversiones",
    "📊 Presupuesto Mensual (50/30/20)",
    "👛 Billetera y Efectivo"
])

# =============================================================================
# PESTAÑA 1: RESUMEN EJECUTIVO (KPIS)
# =============================================================================
with tab_kpis:
    st.markdown("### 🎯 Visión General de Salud Financiera")
    st.caption("Resumen consolidado en tiempo real de tu patrimonio, liquidez y ritmo de gasto.")

    df_raw_kpi = obtener_movimientos(USER_ID)

    if not df_raw_kpi.empty:
        df_raw_kpi['fecha_dt'] = pd.to_datetime(df_raw_kpi['fecha'])
        
        plataformas_conocidas = ["fintual", "cetes", "nu", "finsus", "mercado pago", "gbm", "emergencia"]
        mask_inv = (
            df_raw_kpi['categoria'].str.contains("inversi", case=False, na=False) |
            df_raw_kpi['tipo'].str.contains("inversi", case=False, na=False) |
            df_raw_kpi['categoria'].str.lower().str.contains('|'.join(plataformas_conocidas), na=False)
        )
        
        df_inv = df_raw_kpi[mask_inv].copy()
        
        total_inversiones = 0.0
        rendimiento_mensual_est = 0.0

        if not df_inv.empty:
            def extraer_plat_tasa(row):
                cat, desc = str(row['categoria']), str(row['descripcion'])
                plat = cat.replace("Inversión - ", "").replace("Inversion - ", "").strip() if "Inversión - " in cat or "Inversion - " in cat else "General"
                tasa = 0.0
                m = re.search(r"Tasa:\s*([\d\.]+)%", desc)
                if m:
                    try: tasa = float(m.group(1))
                    except: pass
                return pd.Series([plat, tasa], index=['Plataforma', 'Tasa (%)'])

            df_inv[['Plataforma', 'Tasa (%)']] = df_inv.apply(extraer_plat_tasa, axis=1)
            df_inv = df_inv.sort_values(by=['Plataforma', 'fecha_dt', 'id'])

            for plat, group in df_inv.groupby('Plataforma'):
                reg = group.iloc[-1]
                s = reg['monto']
                t = reg['Tasa (%)']
                total_inversiones += s
                rendimiento_mensual_est += (s * (t / 100)) / 12

        df_flujo_kpi = df_raw_kpi[~mask_inv].copy()

        ingresos_tot = df_flujo_kpi[df_flujo_kpi['tipo'] == 'Ingreso']['monto'].sum()
        mask_debito = df_flujo_kpi['descripcion'].str.contains("Débito", na=False) | (~df_flujo_kpi['descripcion'].str.contains("Efectivo", na=False))
        gastos_debito = df_flujo_kpi[(df_flujo_kpi['tipo'] == 'Egreso') & mask_debito]['monto'].sum()
        retiros_cajero = df_flujo_kpi[df_flujo_kpi['tipo'] == 'Retiro']['monto'].sum()

        saldo_debito = ingresos_tot - gastos_debito - retiros_cajero

        mask_entradas_ef = (df_raw_kpi['tipo'] == 'Retiro') | (df_raw_kpi['categoria'] == 'Ajuste de Efectivo')
        tot_retirado = df_raw_kpi[mask_entradas_ef]['monto'].sum()
        mask_gastos_ef = df_raw_kpi['descripcion'].str.contains("efectivo", case=False, na=False) & (~mask_entradas_ef)
        tot_gastado_ef = df_raw_kpi[mask_gastos_ef]['monto'].sum()
        saldo_efectivo = tot_retirado - tot_gastado_ef

        liquidez_inmediata = saldo_debito + saldo_efectivo
        patrimonio_neto = liquidez_inmediata + total_inversiones

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("🌐 Patrimonio Neto Total", fmt_monto(patrimonio_neto), help="Débito + Efectivo + Inversiones")
        kpi2.metric("💧 Liquidez Inmediata", fmt_monto(liquidez_inmediata), help="Saldo disponible en Banco y Bolsillo")
        kpi3.metric("📈 Capital Invertido", fmt_monto(total_inversiones), help="Suma de CETES, Nu, Fintual, etc.")
        kpi4.metric("💰 Rendimiento Pasivo Est.", fmt_monto(rendimiento_mensual_est), delta=f"+${rendimiento_mensual_est*12:,.2f}/año", delta_color="normal")

        st.markdown("---")

        col_graf_kpi1, col_graf_kpi2 = st.columns([1, 1])

        with col_graf_kpi1:
            st.markdown("#### 📊 Distribución Global de Activos")
            data_distribucion = pd.DataFrame({
                'Activo': ['💳 Tarjeta Débito', '💵 Billetera / Efectivo', '📈 Portafolio Inversión'],
                'Monto': [max(0, saldo_debito), max(0, saldo_efectivo), max(0, total_inversiones)]
            })

            fig_dist = px.pie(
                data_distribucion, values='Monto', names='Activo', hole=0.45,
                color_discrete_sequence=['#496a81', '#669bbc', '#2E7D32']
            )
            fig_dist.update_traces(textinfo='percent+label')
            fig_dist.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_dist, use_container_width=True)

        with col_graf_kpi2:
            st.markdown("#### 🚨 Semáforo de Ritmo Quincenal")
            hoy = pd.Timestamp(obtener_fecha_local())
            df_nominas_kpi = df_flujo_kpi[
                (df_flujo_kpi['tipo'] == 'Ingreso') & 
                (df_flujo_kpi['categoria'].str.contains("Nómina", case=False, na=False))
            ].sort_values('fecha_dt', ascending=False)

            if not df_nominas_kpi.empty:
                ult_nom = df_nominas_kpi.iloc[0]
                ini_q = pd.Timestamp(ult_nom['fecha_dt'])
                monto_nom = float(ult_nom['monto'])
            else:
                ini_q = hoy.replace(day=1)
                monto_nom = 0.0

            gastos_q_actual = df_flujo_kpi[
                (df_flujo_kpi['tipo'] == 'Egreso') & 
                (df_flujo_kpi['fecha_dt'] >= ini_q.normalize())
            ]['monto'].sum()

            pct_gastado = (gastos_q_actual / monto_nom * 100) if monto_nom > 0 else 0.0

            st.write(f"**Nómina registrada:** {fmt_monto(monto_nom)}")
            st.write(f"**Gastado en el ciclo activo:** {fmt_monto(gastos_q_actual)} ({pct_gastado:.1f}%)")
            st.progress(min(1.0, pct_gastado / 100))

            if pct_gastado < 70:
                st.success("🟢 **Saludable:** Mantienes un ritmo de gasto controlado para esta quincena.")
            elif pct_gastado <= 90:
                st.warning("🟡 **Precaución:** Has superado el 70% de consumo de tu nómina.")
            else:
                st.error("🔴 **Freno de Mano:** Cerca o por encima del límite de tu depósito quincenal.")
    else:
        st.info("Aún no hay datos registrados.")

# =============================================================================
# PESTAÑA 2: FLUJO QUINCENAL Y NÓMINA
# =============================================================================
with tab_flujo:
    
    with st.expander("➕ Registrar Movimiento de Nómina, Gastos o Retiros", expanded=False):
        tipo = st.selectbox("Tipo de Movimiento", ["Egreso", "Ingreso", "Retiro"], key="selector_tipo_movimiento")
        
        if tipo == "Ingreso":
            categorias_dinamicas = ["Nómina / Sueldo Quincenal", "Retiro de Inversión a Débito", "Ventas / Ingresos Extra", "Otros Ingresos"]
        elif tipo == "Retiro":
            categorias_dinamicas = ["Retiro de Cajero (Débito ➔ Efectivo)", "Traspaso entre Cuentas"]
        else:
            categorias_dinamicas = [
                "Pago TDC (Tarjeta de Crédito)", "Aportación a Inversión (Enviado a CETES/Fintual)",
                "Alimentación / Súper", "Vivienda / Servicios", "Transporte / Gasolina", 
                "Salud / Gastos Médicos", "Ocio / Entretenimiento", "Suscripciones", "Otros Egresos"
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
                descripcion_user = st.text_input("Descripción / Detalle", placeholder="Ej. Depósito nómina, Súper, etc.", max_chars=120)
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
            
            df_nominas = df_flujo[
                (df_flujo['tipo'] == 'Ingreso') & 
                (df_flujo['categoria'].str.contains("Nómina", case=False, na=False))
            ].sort_values('fecha', ascending=False)

            if not df_nominas.empty:
                ultima_nomina = df_nominas.iloc[0]
                inicio_q = pd.Timestamp(ultima_nomina['fecha'])
                nomina_ingresada_ciclo = float(ultima_nomina['monto'])
                etiqueta_q = f"Ciclo Activo (Nómina del {inicio_q.strftime('%d/%m/%Y')})"
            else:
                inicio_q = hoy_ts.replace(day=1)
                nomina_ingresada_ciclo = 0.0
                etiqueta_q = "Ciclo Inicial (Sin registro de nómina)"

            fin_q = hoy_ts 
            df_q_actual = df_flujo[(df_flujo['fecha'] >= inicio_q.normalize()) & (df_flujo['fecha'] <= fin_q.normalize())]
            
            mask_debito_global = df_flujo['descripcion'].str.contains("Débito", na=False) | (~df_flujo['descripcion'].str.contains("Efectivo", na=False))
            ingresos_totales_historicos = df_flujo[df_flujo['tipo'] == 'Ingreso']['monto'].sum()
            gastos_debito_historicos = df_flujo[(df_flujo['tipo'] == 'Egreso') & mask_debito_global]['monto'].sum()
            retiros_historicos = df_flujo[df_flujo['tipo'] == 'Retiro']['monto'].sum()
            
            nomina_restante = ingresos_totales_historicos - gastos_debito_historicos - retiros_historicos

            mask_debito_q = df_q_actual['descripcion'].str.contains("Débito", na=False) | (~df_q_actual['descripcion'].str.contains("Efectivo", na=False))
            gastos_debito_ciclo = df_q_actual[(df_q_actual['tipo'] == 'Egreso') & mask_debito_q]['monto'].sum()
            gastos_efectivo_ciclo = df_q_actual[(df_q_actual['tipo'] == 'Egreso') & df_q_actual['descripcion'].str.contains("Efectivo", na=False)]['monto'].sum()

            col_q1, col_q2, col_q3, col_q4 = st.columns(4)
            col_q1.metric("💵 Saldo Real en Débito (Acumulado)", fmt_monto(nomina_restante))
            col_q2.metric("💳 Gastos con Débito (Ciclo)", fmt_monto(gastos_debito_ciclo), delta_color="inverse")
            col_q3.metric("💵 Gastos en Efectivo (Ciclo)", fmt_monto(gastos_efectivo_ciclo), delta_color="inverse")
            col_q4.metric("🏦 Nómina Recibida", fmt_monto(nomina_ingresada_ciclo))

            # --- RESTAURACIÓN DE GRÁFICO EN FLUJO QUINCENAL ---
            st.markdown("---")
            col_graf_flujo1, col_graf_flujo2 = st.columns([1, 1])

            with col_graf_flujo1:
                st.markdown("#### 🛒 Desglose de Gastos por Categoría")
                df_egresos = df_flujo[df_flujo['tipo'] == 'Egreso']
                if not df_egresos.empty:
                    gastos_cat = df_egresos.groupby('categoria')['monto'].sum().reset_index()
                    fig_cat = px.bar(
                        gastos_cat, x='monto', y='categoria', orientation='h',
                        color='monto', color_continuous_scale='Reds',
                        text_auto='.2f', labels={'monto': 'Total ($)', 'categoria': 'Categoría'}
                    )
                    fig_cat.update_layout(showlegend=False, coloraxis_showscale=False, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_cat, use_container_width=True)
                else:
                    st.info("No hay egresos registrados para graficar.")

            with col_graf_flujo2:
                st.markdown("#### 🚨 Control y Ritmo de Gasto")
                dia_pago = inicio_q.day
                if dia_pago >= 25 or dia_pago <= 5:
                    if inicio_q.day >= 25:
                        mes_target = inicio_q.month + 1 if inicio_q.month < 12 else 1
                        anio_target = inicio_q.year if inicio_q.month < 12 else inicio_q.year + 1
                        fecha_estimada_fin = pd.Timestamp(year=anio_target, month=mes_target, day=15)
                    else:
                        fecha_estimada_fin = inicio_q.replace(day=15)
                else:
                    proximo_mes = (inicio_q.replace(day=28) + pd.Timedelta(days=4))
                    fecha_estimada_fin = proximo_mes.replace(day=1) - pd.Timedelta(days=1)

                dias_restantes = max((fecha_estimada_fin.date() - hoy_date).days + 1, 1)
                gasto_diario_sugerido = nomina_restante / dias_restantes if nomina_restante > 0 else 0.00

                st.metric("⏳ Días Est. para Próximo Pago", f"{dias_restantes} días", delta=f"Proyectado al {fecha_estimada_fin.strftime('%d/%m')}")
                st.metric("💳 Gasto Diario Máximo Sugerido", fmt_monto(gasto_diario_sugerido))

            st.markdown("---")

            # --- TABLA DE HISTORIAL Y FILTROS EN FLUJO ---
            st.markdown("### 📋 Historial Completo de Nómina y Gastos")
            df_display = df_flujo.copy()
            df_display['fecha_str'] = df_display['fecha'].dt.strftime('%Y-%m-%d')
            
            with st.expander("🔍 Filtros de Búsqueda", expanded=False):
                col_f_flujo1, col_f_flujo2, col_f_flujo3 = st.columns(3)
                with col_f_flujo1:
                    min_fecha_f = df_display['fecha'].min().date()
                    max_fecha_f = df_display['fecha'].max().date()
                    f_rango = st.date_input("Rango de Fechas", [min_fecha_f, max_fecha_f], key="f_rango_flujo")
                with col_f_flujo2:
                    tipos_disponibles = ["Todos"] + list(df_display['tipo'].unique())
                    f_tipo = st.selectbox("Tipo de Movimiento", tipos_disponibles, key="f_tipo_flujo")
                with col_f_flujo3:
                    f_texto = st.text_input("Buscar en Descripción / Categoría", "", key="f_texto_flujo")

            if isinstance(f_rango, (list, tuple)) and len(f_rango) == 2:
                df_display = df_display[(df_display['fecha'].dt.date >= f_rango[0]) & (df_display['fecha'].dt.date <= f_rango[1])]
            if f_tipo != "Todos":
                df_display = df_display[df_display['tipo'] == f_tipo]
            if f_texto:
                df_display = df_display[
                    df_display['descripcion'].str.contains(f_texto, case=False, na=False) |
                    df_display['categoria'].str.contains(f_texto, case=False, na=False)
                ]

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
                st.dataframe(df_display_show[['id', 'fecha_str', 'tipo', 'categoria', 'monto', 'descripcion']], column_config=config_columnas, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_display[['id', 'fecha_str', 'tipo', 'categoria', 'monto', 'descripcion']], column_config=config_columnas, use_container_width=True, hide_index=True)

            with st.expander("✏️ Editar o Eliminar un Registro"):
                opciones_registros = {
                    f"ID {row['id']} | {row['fecha_str']} - {row['descripcion']} (${row['monto']:,.2f})": row['id']
                    for _, row in df_display.iterrows()
                }
                if opciones_registros:
                    registro_sel = st.selectbox("Selecciona registro:", list(opciones_registros.keys()))
                    id_seleccionado = opciones_registros[registro_sel]
                    datos_reg = df_display[df_display['id'] == id_seleccionado].iloc[0]
                    
                    col_edit1, col_edit2 = st.columns(2)
                    with col_edit1:
                        st.markdown("#### 🔄 Editar")
                        with st.form("form_editar_flujo"):
                            e_fecha = st.date_input("Fecha Correcta", datos_reg['fecha'].date())
                            e_tipo = st.selectbox("Tipo", ["Egreso", "Ingreso", "Retiro", "Inversion"], index=0)
                            e_monto = st.number_input("Monto ($)", value=float(datos_reg['monto']), min_value=0.01, step=10.0, format="%.2f")
                            e_cat = st.text_input("Categoría", value=str(datos_reg['categoria']))
                            e_desc = st.text_input("Descripción", value=datos_reg['descripcion'])
                            
                            btn_actualizar = st.form_submit_button("💾 Guardar Cambios")
                            if btn_actualizar:
                                if actualizar_movimiento(id_seleccionado, e_tipo, e_monto, e_cat, e_desc, e_fecha, USER_ID):
                                    st.success("✅ Registro actualizado.")
                                    st.rerun()

                    with col_edit2:
                        st.markdown("#### 🗑️ Eliminar")
                        if st.button("❌ Borrar Registro", use_container_width=True):
                            if eliminar_movimiento(id_seleccionado, USER_ID):
                                st.success("✅ Registro eliminado.")
                                st.rerun()
        else:
            st.info("Aún no tienes movimientos registrados.")
    else:
        st.info("Aún no hay registros en la base de datos.")

# =============================================================================
# PESTAÑA 3: PORTAFOLIO DE INVERSIONES
# =============================================================================
with tab_ahorros:
    st.markdown("### 📈 Portafolio de Inversiones (CETES, Fintual, Nu)")

    current_user_id = st.session_state.get("user_id")

    with st.expander("➕ Registrar / Actualizar Saldo de Inversión", expanded=False):
        with st.form("form_inversiones", clear_on_submit=True):
            col_inv1, col_inv2, col_inv3 = st.columns(3)
            with col_inv1:
                plataforma = st.selectbox("Plataforma / Fondo", ["Nu (Cajita)", "CETES Directo", "Finsus", "Fintual", "Mercado Pago / Fondo", "GBM / Acciones", "Fondo de Emergencia", "Otra Plataforma"])
                monto_inv = st.number_input("Saldo Total Actual ($)", min_value=0.01, step=100.0, format="%.2f")
                tasa_anual_inv = st.number_input("Tasa Anual (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.2f")
            with col_inv2:
                tipo_operacion = st.selectbox("Tipo de Movimiento", ["Actualización de Saldo Total", "Aportación Directa", "Retiro Parcial/Total"])
                fecha_inv = st.date_input("Fecha", obtener_fecha_local(), key="fecha_inv")
            with col_inv3:
                notas_inv = st.text_input("Notas / Detalle", placeholder="Ej. Saldo al revisar la app hoy")
                submit_inv = st.form_submit_button("💾 Guardar Inversión", use_container_width=True)

            if submit_inv:
                desc_completa = f"[{plataforma} | Tasa: {tasa_anual_inv:.2f}%] {tipo_operacion}: {notas_inv}".strip()
                categoria_inv = f"Inversión - {plataforma}"
                
                if guardar_movimiento("Inversion", monto_inv, categoria_inv, desc_completa, fecha_inv, current_user_id):
                    st.success(f"✅ Portafolio de {plataforma} actualizado.")
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
                cat, desc = str(row['categoria']), str(row['descripcion'])
                plat = cat.replace("Inversión - ", "").replace("Inversion - ", "").strip() if "Inversión - " in cat or "Inversion - " in cat else "General"
                tasa = 0.0
                m = re.search(r"Tasa:\s*([\d\.]+)%", desc)
                if m:
                    try: tasa = float(m.group(1))
                    except: pass
                return pd.Series([plat, tasa], index=['Plataforma', 'Tasa (%)'])

            df_inversiones[['Plataforma', 'Tasa (%)']] = df_inversiones.apply(extraer_datos_inv, axis=1)
            df_inversiones['fecha'] = pd.to_datetime(df_inversiones['fecha'])
            df_inversiones = df_inversiones.sort_values(by=['Plataforma', 'fecha', 'id'])

            resumen_filas = []
            for plat, group in df_inversiones.groupby('Plataforma'):
                reg = group.iloc[-1]
                saldo_actual = reg['monto']
                tasa_actual = reg['Tasa (%)']
                ganancia_mensual = (saldo_actual * (tasa_actual / 100)) / 12

                resumen_filas.append({
                    "Plataforma": plat,
                    "Saldo Actual": saldo_actual,
                    "Tasa Anual (%)": tasa_actual,
                    "Ganancia Est. / Mes": ganancia_mensual
                })

            df_resumen_inv = pd.DataFrame(resumen_filas)
            
            st.dataframe(
                df_resumen_inv,
                column_config={
                    "Plataforma": "Fondo / Plataforma",
                    "Saldo Actual": st.column_config.NumberColumn("Saldo Actual", format="$%.2f"),
                    "Tasa Anual (%)": st.column_config.NumberColumn("Tasa Anual", format="%.2f%%"),
                    "Ganancia Est. / Mes": st.column_config.NumberColumn("Est. Ganancia/Mes", format="$%.2f")
                },
                use_container_width=True,
                hide_index=True
            )

            # --- RESTAURACIÓN DE GRÁFICOS EN INVERSIONES ---
            st.markdown("---")
            col_graf_inv1, col_graf_inv2 = st.columns(2)

            with col_graf_inv1:
                st.markdown("#### 🥧 Distribución del Portafolio")
                fig_pie_inv = px.pie(
                    df_resumen_inv, values='Saldo Actual', names='Plataforma', hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_pie_inv.update_traces(textinfo='percent+label')
                fig_pie_inv.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_pie_inv, use_container_width=True)

            with col_graf_inv2:
                st.markdown("#### 💸 Rendimiento Estimado por Fondo ($/Mes)")
                fig_bar_inv = px.bar(
                    df_resumen_inv, x='Plataforma', y='Ganancia Est. / Mes',
                    color='Ganancia Est. / Mes', color_continuous_scale='Greens',
                    text_auto='.2f'
                )
                fig_bar_inv.update_layout(coloraxis_showscale=False, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_bar_inv, use_container_width=True)

# =============================================================================
# PESTAÑA 4: PRESUPUESTO 50/30/20
# =============================================================================
with tab_presupuesto:
    st.markdown("### 📊 Presupuesto Mensual (Regla 50 / 30 / 20)")

    col_inc1, col_inc2 = st.columns(2)
    with col_inc1:
        ingreso_q1 = st.number_input("Ingreso Neto 1.ª Quincena ($)", min_value=0.0, value=10000.0, step=500.0, format="%.2f")
    with col_inc2:
        ingreso_q2 = st.number_input("Ingreso Neto 2.ª Quincena ($)", min_value=0.0, value=10000.0, step=500.0, format="%.2f")
    
    ingreso_mensual_total = ingreso_q1 + ingreso_q2

    limite_necesidades = ingreso_mensual_total * 0.50
    limite_deseos = ingreso_mensual_total * 0.30
    limite_ahorro = ingreso_mensual_total * 0.20

    st.markdown("---")

    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric("🏠 50% Necesidades / Fijos", fmt_monto(limite_necesidades))
    col_p2.metric("🎉 30% Deseos / Estilo de Vida", fmt_monto(limite_deseos))
    col_p3.metric("🛡️ 20% Ahorro / Inversión", fmt_monto(limite_ahorro))

    # --- RESTAURACIÓN DE GRÁFICO EN PRESUPUESTO ---
    st.markdown("---")
    st.markdown("#### 📐 Distribución Teórica de tus Ingresos")
    df_pres_graf = pd.DataFrame({
        'Rubro': ['🏠 Necesidades (50%)', '🎉 Deseos (30%)', '🛡️ Ahorro/Inversión (20%)'],
        'Monto Asignado': [limite_necesidades, limite_deseos, limite_ahorro]
    })
    fig_pres = px.bar(
        df_pres_graf, x='Rubro', y='Monto Asignado', color='Rubro',
        color_discrete_sequence=['#496a81', '#8c7a6b', '#2E7D32'],
        text_auto='.2f'
    )
    fig_pres.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig_pres, use_container_width=True)

# =============================================================================
# PESTAÑA 5: BILLETERA Y EFECTIVO
# =============================================================================
with tab_efectivo:
    st.header("👛 Control de Billetera y Efectivo")

    col_ef1, col_ef2 = st.columns(2)

    with col_ef1:
        st.subheader("1. 📥 Entrada de Efectivo")
        tipo_entrada = st.radio("Origen del Dinero", ["🏦 Retiro de Cajero (Descuenta de Débito)", "💵 Ajuste / Dinero Extra"])

        with st.form("form_retiro_efectivo", clear_on_submit=True):
            monto_retiro = st.number_input("Monto ($)", min_value=1.0, step=10.0, format="%.2f")
            fecha_retiro = st.date_input("Fecha", obtener_fecha_local(), key="fecha_retiro_ef")
            desc_retiro = st.text_input("Notas", placeholder="Ej. Cajero Santander")
            submit_retiro = st.form_submit_button("💾 Guardar Entrada", use_container_width=True)

        if submit_retiro:
            tipo_db = "Retiro" if "Retiro de Cajero" in tipo_entrada else "Ingreso"
            cat_entrada = "Retiro de Cajero (Débito ➔ Efectivo)" if "Retiro de Cajero" in tipo_entrada else "Ajuste de Efectivo"
            desc_ret_final = f"[💵 Efectivo] {desc_retiro}".strip()

            if guardar_movimiento(tipo_db, monto_retiro, cat_entrada, desc_ret_final, fecha_retiro, USER_ID):
                st.success(f"✅ Entrada registrada.")
                st.rerun()

    with col_ef2:
        st.subheader("2. 💸 Gasto en Efectivo")
        with st.form("form_gasto_efectivo", clear_on_submit=True):
            monto_gasto_e = st.number_input("Monto Gastado ($)", min_value=0.01, step=10.0, format="%.2f")
            cat_gasto_e = st.selectbox("Categoría", ["Alimentación / Súper", "Transporte / Gasolina", "Ocio / Entretenimiento", "Vivienda / Servicios", "Otros Egresos"])
            fecha_gasto_e = st.date_input("Fecha del Gasto", obtener_fecha_local(), key="fecha_gasto_ef")
            desc_gasto_e = st.text_input("Detalle", placeholder="Ej. Tacos, Propina")
            submit_gasto_e = st.form_submit_button("💸 Registrar Salida", use_container_width=True)

        if submit_gasto_e:
            desc_ge_final = f"[💵 Efectivo] {desc_gasto_e}".strip()
            if guardar_movimiento("Egreso", monto_gasto_e, cat_gasto_e, desc_ge_final, fecha_gasto_e, USER_ID):
                st.success(f"✅ Gasto en efectivo registrado.")
                st.rerun()