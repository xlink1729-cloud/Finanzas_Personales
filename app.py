import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Finanzas Personales",
    page_icon="💰",
    layout="wide"
)

# --- CONEXIÓN A LA BASE DE DATOS (NEON) ---
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])

# --- FUNCIONES PARA LA BASE DE DATOS ---
def guardar_movimiento(tipo, monto, categoria, descripcion, fecha):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO movimientos (tipo, monto, categoria, descripcion, fecha)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (tipo, monto, categoria, descripcion, fecha)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error al guardar en la base de datos: {e}")
        return False

def obtener_movimientos():
    try:
        conn = get_connection()
        query = "SELECT id, fecha, tipo, categoria, monto, descripcion FROM movimientos ORDER BY fecha DESC, id DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error al consultar la base de datos: {e}")
        return pd.DataFrame()

# --- INTERFAZ GRAFICA DE STREAMLIT ---
st.title("💰 Control de Finanzas Personales")
st.caption("Registro diario de ingresos y egresos")

# --- 1. FORMULARIO DE REGISTRO ---
with st.expander("➕ Registrar Nuevo Movimiento", expanded=True):
    with st.form("form_finanzas", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            tipo = st.selectbox("Tipo", ["Egreso", "Ingreso"])
            monto = st.number_input("Monto ($)", min_value=0.01, step=10.0, format="%.2f")
        
        with col2:
            if tipo == "Egreso":
                categorias = ["Alimentación", "Vivienda", "Transporte", "Ocio", "Salud", "Suscripciones", "Otros"]
            else:
                categorias = ["Sueldo / Retiro FISIOSER", "Inversiones", "Ventas Extra", "Otros"]
                
            categoria = st.selectbox("Categoría", categorias)
            fecha = st.date_input("Fecha", datetime.now())

        with col3:
            descripcion = st.text_input("Descripción / Detalle", placeholder="Ej. Súper semanal, Gasolina...")
            submit = st.form_submit_button("💾 Guardar Movimiento", use_container_width=True)

        if submit:
            if guardar_movimiento(tipo, monto, categoria, descripcion, fecha):
                st.success(f"✅ {tipo} de ${monto:.2f} registrado correctamente.")
                st.rerun()

st.markdown("---")

# --- 2. OBTENCIÓN Y MOSTRADO DE DATOS ---
df = obtener_movimientos()

if not df.empty:
    # Formatear la fecha para mejor lectura
    df['fecha'] = pd.to_datetime(df['fecha']).dt.strftime('%Y-%m-%d')
    
    # --- KPIS METRICS ---
    total_ingresos = df[df['tipo'] == 'Ingreso']['monto'].sum()
    total_egresos = df[df['tipo'] == 'Egreso']['monto'].sum()
    balance = total_ingresos - total_egresos

    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("Total Ingresos", f"${total_ingresos:,.2f}")
    col_kpi2.metric("Total Egresos", f"${total_egresos:,.2f}", delta_color="inverse")
    col_kpi3.metric("Balance Neto", f"${balance:,.2f}")

    st.markdown("### 📋 Historial de Movimientos")
    
    # Tabla interactiva
    st.dataframe(
        df,
        column_config={
            "id": None, # Ocultar ID
            "fecha": "Fecha",
            "tipo": "Tipo",
            "categoria": "Categoría",
            "monto": st.column_config.NumberColumn("Monto", format="$%.2f"),
            "descripcion": "Descripción"
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Aún no tienes movimientos registrados. Usa el formulario de arriba para agregar el primero.")