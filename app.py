import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import psycopg2
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

# -------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y ZONA HORARIA
# -------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Financiero Personal",
    page_icon="📊",
    layout="wide"
)

TIMEZONE_MEXICO = pytz.timezone('America/Mexico_City')

def obtener_fecha_local():
    return datetime.now(TIMEZONE_MEXICO).date()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------------------------------------------------------------
# 2. CONEXIÓN A BASE DE DATOS NEON
# -------------------------------------------------------------------------
@st.cache_resource
def obtener_conexion():
    return psycopg2.connect(st.secrets["postgres"]["url"])

def verificar_credenciales(username, password):
    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            pass_hash = hash_password(password)
            cur.execute(
                "SELECT id, nombre FROM usuarios WHERE username = %s AND password_hash = %s",
                (username, pass_hash)
            )
            return cur.fetchone()
    except Exception as e:
        st.error(f"Error de conexión con Neon: {e}")
        return None

# -------------------------------------------------------------------------
# 3. CONTROL DE SESIÓN (LOGIN)
# -------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user_id"] = None
    st.session_state["user_name"] = ""

if not st.session_state["authenticated"]:
    col_logo, col_login, col_pad = st.columns([1, 2, 1])
    
    with col_login:
        st.title("🔐 Control Financiero")
        st.caption("Ingresa tus credenciales para acceder a tu panel personal.")
        
        with st.form("form_login"):
            user_input = st.text_input("Usuario")
            pass_input = st.text_input("Contraseña", type="password")
            submit_login = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            
            if submit_login:
                user_data = verificar_credenciales(user_input.strip(), pass_input.strip())
                if user_data:
                    st.session_state["authenticated"] = True
                    st.session_state["user_id"] = user_data[0]
                    st.session_state["user_name"] = user_data[1]
                    st.success(f"¡Bienvenido/a {user_data[1]}!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
    st.stop()

# -------------------------------------------------------------------------
# 4. FUNCIONES CRUD EN NEON (FILTRADAS POR USER_ID)
# -------------------------------------------------------------------------
USER_ID = st.session_state["user_id"]

def cargar_datos_flujo():
    try:
        conn = obtener_conexion()
        query = """
            SELECT id, tipo, monto, categoria, descripcion, fecha 
            FROM flujo_efectivo 
            WHERE user_id = %s 
            ORDER BY fecha DESC, id DESC
        """
        df = pd.read_sql(query, conn, params=(USER_ID,))
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
        return df
    except Exception as e:
        st.error(f"Error al cargar datos desde Neon: {e}")
        return pd.DataFrame(columns=['id', 'tipo', 'monto', 'categoria', 'descripcion', 'fecha'])

def guardar_movimiento(tipo, monto, categoria, descripcion, fecha):
    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            query = """
                INSERT INTO flujo_efectivo (tipo, monto, categoria, descripcion, fecha, user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cur.execute(query, (tipo, monto, categoria, descripcion, fecha, USER_ID))
            conn.commit()
        return True
    except Exception as e:
        st.error(f"Error al guardar movimiento en Neon: {e}")
        return False

def eliminar_movimiento(id_registro):
    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            query = "DELETE FROM flujo_efectivo WHERE id = %s AND user_id = %s"
            cur.execute(query, (id_registro, USER_ID))
            conn.commit()
        return True
    except Exception as e:
        st.error(f"Error al eliminar registro: {e}")
        return False

# -------------------------------------------------------------------------
# 5. SIDEBAR Y CONFIGURACIÓN
# -------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"👤 **Usuario:** {st.session_state['user_name']}")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["user_id"] = None
        st.session_state["user_name"] = ""
        st.rerun()
        
    st.divider()
    ocultar_saldos = st.checkbox("👁️ Ocultar Saldos", value=False)
    
    st.header("⚙️ Configuración del Ciclo")
    fecha_base_q = st.date_input("Inicio del Ciclo Quincenal", value=obtener_fecha_local())

# -------------------------------------------------------------------------
# 6. DASHBOARD PRINCIPAL
# -------------------------------------------------------------------------
st.title(f"📊 Dashboard Financiero — {st.session_state['user_name']}")

df_flujo = cargar_datos_flujo()

# --- 6.1 FORMULARIO DE REGISTRO CON CAMBIO DINÁMICO DE CATEGORÍAS ---
with st.expander("➕ Registrar Movimiento", expanded=True):
    
    tipo = st.selectbox(
        "Tipo de Movimiento", 
        ["Egreso", "Ingreso", "Transferencia / Retiro"],
        key="selector_tipo_movimiento"
    )
    
    if tipo == "Ingreso":
        categorias_dinamicas = [
            "Nómina / Sueldo Quincenal", 
            "Retiro de Inversión a Débito", 
            "Ventas / Ingresos Extra", 
            "Otros Ingresos"
        ]
    elif tipo == "Transferencia / Retiro":
        categorias_dinamicas = [
            "Retiro de Cajero (Débito ➔ Efectivo)",
            "Traspaso entre Cuentas"
        ]
    else: # Egreso
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
            metodo_pago = st.selectbox("Forma de Pago / Origen", ["💳 Tarjeta de Débito (Nómina)", "💵 Efectivo", "💳 Tarjeta de Crédito"])
        
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
            if guardar_movimiento(tipo, monto, categoria, desc_final, fecha):
                st.success(f"✅ {tipo} ({categoria}) registrado con éxito.")
                st.rerun()

st.divider()

# --- 6.2 CÁLCULOS Y MÉTRICAS DE LIQUIDEZ Y FRENO DE MANO ---
inicio_q = pd.to_datetime(fecha_base_q)
fin_q = inicio_q + pd.Timedelta(days=14)

# Filtrar egresos de la quincena actual
df_gastos_ciclo = df_flujo[
    (df_flujo['tipo'] == 'Egreso') & 
    (df_flujo['fecha'] >= inicio_q.normalize()) & 
    (df_flujo['fecha'] <= fin_q.normalize())
].copy() if not df_flujo.empty else pd.DataFrame()

# Balance acumulado contínuo
ingresos_totales = df_flujo[df_flujo['tipo'] == 'Ingreso']['monto'].sum() if not df_flujo.empty else 0.0
egresos_totales = df_flujo[df_flujo['tipo'] == 'Egreso']['monto'].sum() if not df_flujo.empty else 0.0
liquidez_acumulada = ingresos_totales - egresos_totales

col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    val_liq = "••••••" if ocultar_saldos else f"${liquidez_acumulada:,.2f}"
    st.metric("💧 Liquidez Acumulada Real", val_liq)

with col_m2:
    gastos_ciclo_val = df_gastos_ciclo['monto'].sum() if not df_gastos_ciclo.empty else 0.0
    val_gasto = "••••••" if ocultar_saldos else f"${gastos_ciclo_val:,.2f}"
    st.metric("📉 Gastos de la Quincena Actual", val_gasto)

with col_m3:
    if liquidez_acumulada <= 1000:
        st.error("🛑 FRENO DE MANO ACTIVO: Liquidez Crítica")
    elif liquidez_acumulada <= 3000:
        st.warning("⚠️ Precaución: Liquidez Ajustada")
    else:
        st.success("🟢 Estado Financiero Saludable")

st.divider()

# --- 6.3 ANÁLISIS REGLA 50/30/20 ---
st.subheader("📊 Distribución de Gastos (Marco 50/30/20)")

if not df_gastos_ciclo.empty:
    # Clasificación dentro de la regla 50/30/20
    necesidades_cats = ["Alimentación / Súper", "Vivienda / Servicios", "Transporte / Gasolina", "Salud / Gastos Médicos", "Pago TDC (Tarjeta de Crédito)"]
    deseos_cats = ["Ocio / Entretenimiento", "Suscripciones", "Otros Egresos"]
    ahorro_cats = ["Aportación a Inversión (Enviado a CETES/Fintual)"]

    def clasificar_503020(cat):
        if cat in necesidades_cats: return "Necesidades (50%)"
        if cat in deseos_cats: return "Deseos (30%)"
        if cat in ahorro_cats: return "Ahorro / Inversión (20%)"
        return "Otros"

    df_gastos_ciclo['Grupo_503020'] = df_gastos_ciclo['categoria'].apply(clasificar_503020)
    df_resumen_503020 = df_gastos_ciclo.groupby('Grupo_503020')['monto'].sum().reset_index()

    col_g1, col_g2 = st.columns([1, 1])
    with col_g1:
        fig_pie = px.pie(
            df_resumen_503020, 
            values='monto', 
            names='Grupo_503020',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_pie.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_g2:
        st.caption("**Desglose Acumulado por Categoría:**")
        df_cat_total = df_gastos_ciclo.groupby('categoria')['monto'].sum().reset_index().sort_values(by='monto', ascending=False)
        st.dataframe(
            df_cat_total,
            column_config={
                "categoria": "Categoría",
                "monto": st.column_config.NumberColumn("Monto Total", format="$%.2f")
            },
            use_container_width=True,
            hide_index=True
        )

st.divider()

# --- 6.4 COMPORTAMIENTO Y AUDITORÍA SEMANAL ---
st.subheader("📅 Comportamiento de Gasto por Semana")

if not df_gastos_ciclo.empty:
    df_gastos_ciclo['Semana_Num'] = df_gastos_ciclo['fecha'].dt.strftime('%U').astype(int)
    df_gastos_ciclo['Semana_Label'] = df_gastos_ciclo['fecha'].dt.strftime('Semana %U')

    # Gráfica de barras comparativa de semanas
    df_semanal = df_gastos_ciclo.groupby(['Semana_Num', 'Semana_Label'])['monto'].sum().reset_index().sort_values('Semana_Num')
    fig_sem = px.bar(
        df_semanal,
        x='Semana_Label',
        y='monto',
        text_auto='.2f',
        title="Gasto Acumulado por Semana del Ciclo",
        color_discrete_sequence=['#1F77B4']
    )
    st.plotly_chart(fig_sem, use_container_width=True)

    # Selector para auditar semana específica
    semanas_disponibles = df_semanal['Semana_Label'].unique().tolist()
    semana_seleccionada = st.selectbox(
        "Selecciona la semana que deseas auditar:",
        options=semanas_disponibles,
        index=len(semanas_disponibles) - 1
    )

    df_semana_det = df_gastos_ciclo[df_gastos_ciclo['Semana_Label'] == semana_seleccionada]

    col_sdet1, col_sdet2 = st.columns([1, 1])

    with col_sdet1:
        st.caption(f"**Categorías en las que más gastaste en la {semana_seleccionada}:**")
        if not df_semana_det.empty:
            df_cat_sem = df_semana_det.groupby('categoria')['monto'].sum().reset_index().sort_values(by='monto', ascending=True)
            fig_cat_sem = px.bar(
                df_cat_sem,
                x='monto',
                y='categoria',
                orientation='h',
                text_auto='.2f',
                color_discrete_sequence=['#2CA02C']
            )
            fig_cat_sem.update_layout(xaxis_title="Monto ($)", yaxis_title="", margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_cat_sem, use_container_width=True)
        else:
            st.info("No hay registros de gasto para esta semana.")

    with col_sdet2:
        st.caption(f"**Lista de compras/pagos en la {semana_seleccionada}:**")
        df_tabla_sem = df_semana_det[['fecha', 'categoria', 'descripcion', 'monto']].copy()
        df_tabla_sem['fecha'] = df_tabla_sem['fecha'].dt.strftime('%d/%m/%Y')
        st.dataframe(
            df_tabla_sem,
            column_config={
                "fecha": "Fecha",
                "categoria": "Categoría",
                "descripcion": "Descripción",
                "monto": st.column_config.NumberColumn("Monto", format="$%.2f")
            },
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("💡 En cuanto registres tu primer gasto de esta quincena, aquí verás el desglose semanal.")

st.divider()

# --- 6.5 HISTORIAL COMPLETO Y ELIMINACIÓN DE REGISTROS ---
st.subheader("📋 Historial Completo y Gestión de Movimientos")

if not df_flujo.empty:
    df_historial = df_flujo[['id', 'fecha', 'tipo', 'categoria', 'descripcion', 'monto']].copy()
    df_historial['fecha'] = df_historial['fecha'].dt.strftime('%d/%m/%Y')
    
    col_hist, col_del = st.columns([3, 1])
    
    with col_hist:
        st.dataframe(
            df_historial[['fecha', 'tipo', 'categoria', 'descripcion', 'monto']],
            column_config={
                "fecha": "Fecha",
                "tipo": "Tipo",
                "categoria": "Categoría",
                "descripcion": "Descripción",
                "monto": st.column_config.NumberColumn("Monto", format="$%.2f")
            },
            use_container_width=True,
            hide_index=True
        )
        
    with col_del:
        st.caption("🗑️ **Eliminar Registro**")
        id_a_eliminar = st.number_input("ID del registro a borrar:", min_value=1, step=1)
        if st.button("Borrar Registro", type="primary", use_container_width=True):
            if eliminar_movimiento(id_a_eliminar):
                st.success(f"Registro {id_a_eliminar} eliminado.")
                st.rerun()
else:
    st.write("Aún no tienes movimientos registrados.")