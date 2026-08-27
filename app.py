import streamlit as st
import pandas as pd
import psycopg2
import hashlib
from datetime import datetime, date
from zoneinfo import ZoneInfo
import plotly.express as px

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
# 2. CONTROL DE ACCESO Y AUTENTICACIÓN MULTIUSUARIO
# =============================================================================
def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

def validar_usuario_db(username, password):
    hash_ingresado = hashlib.sha256(password.encode()).hexdigest()
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username FROM usuarios WHERE username = %s AND password_hash = %s",
                (username, hash_ingresado)
            )
            user = cur.fetchone()
            return user
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"Error en autenticación: {e}")
        return None
    finally:
        if conn:
            conn.close()

def mostrar_login():
    # Estilos CSS con Glassmorphism y margen superior reducido
    st.markdown("""
        <style>
        /* Fondo general con degradado */
        .stApp {
            background: linear-gradient(135deg, #2b3a67 0%, #496a81 35%, #669bbc 70%, #8c7a6b 100%);
        }
        
        /* Ocultar barra superior de Streamlit */
        header {visibility: hidden;}

        /* REDUCIR ESPACIO SUPERIOR DE LA PÁGINA (Sube todo el contenido) */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
        }

        /* 1. Corrección de etiquetas (Usuario / Contraseña en Blanco Brillante) */
        div[data-testid="stForm"] label, 
        div[data-testid="stForm"] label p {
            color: #FFFFFF !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            text-shadow: 0px 1px 3px rgba(0, 0, 0, 0.6);
        }

        /* 2. Color del icono del ojo/revelar contraseña */
        div[data-testid="stForm"] button[aria-label="Show password"] svg,
        div[data-testid="stForm"] button[aria-label="Hide password"] svg {
            fill: #FFFFFF !important;
        }

        /* 3. Borde al hacer clic/focus en las cajas de texto */
        div[data-testid="stForm"] input:focus {
            border-color: #48cae4 !important;
            box-shadow: 0 0 8px rgba(72, 202, 228, 0.5) !important;
        }
        
        div[data-testid="stForm"] input::placeholder {
            color: rgba(255, 255, 255, 0.6) !important;
        }

        /* Botón LOGIN estilo cápsula */
        div[data-testid="stForm"] button[type="submit"] {
            background: linear-gradient(90deg, #48cae4 0%, #0077b6 100%) !important;
            color: white !important;
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
        </style>
    """, unsafe_allow_html=True)

    # Centrado en pantalla usando columnas
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # 1. Logo centrado afuera de la tarjeta
        col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
        with col_img2:
            try:
                st.image("static/logo.png", use_container_width=True)
            except Exception:
                pass

        # 2. Formulario de acceso dentro de la tarjeta
        with st.form("form_login"):
            st.markdown("<h2 style='text-align: center; color: white; margin-bottom: 20px; font-weight: 700;'>LOGIN</h2>", unsafe_allow_html=True)
            
            usuario = st.text_input("👤 Usuario", placeholder="Ingresa tu usuario")
            contrasena = st.text_input("🔒 Contraseña", type="password", placeholder="Ingresa tu contraseña")
            
            submit = st.form_submit_button("LOGIN", use_container_width=True)
            
            if submit:
                user_data = validar_usuario_db(usuario, contrasena)
                if user_data:
                    st.session_state["autenticado"] = True
                    st.session_state["user_id"] = user_data[0]
                    st.session_state["username"] = user_data[1]
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")

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

tab_flujo, tab_ahorros, tab_efectivo = st.tabs([
    "💵 Flujo Quincenal y Nómina", 
    "📈 Portafolio de Inversiones (CETES, Fintual)",
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
            
            if hoy_ts.day >= 15 and hoy_ts.day <= 29:
                inicio_q = hoy_ts.replace(day=15)
                fin_q = hoy_ts.replace(day=29)
                etiqueta_q = f"Ciclo Nómina del 15 (Del {inicio_q.strftime('%d/%m')} al {fin_q.strftime('%d/%m')})"
            elif hoy_ts.day >= 30:
                inicio_q = hoy_ts.replace(day=30)
                proximo_mes = (hoy_ts.replace(day=28) + pd.Timedelta(days=4)).replace(day=14)
                fin_q = proximo_mes
                etiqueta_q = f"Ciclo Nómina del 30 (Del {inicio_q.strftime('%d/%m')} al {fin_q.strftime('%d/%m')})"
            else:
                mes_anterior = (hoy_ts.replace(day=1) - pd.Timedelta(days=1))
                inicio_q = mes_anterior.replace(day=30) if mes_anterior.day >= 30 else mes_anterior.replace(day=28)
                fin_q = hoy_ts.replace(day=14)
                etiqueta_q = f"Ciclo Nómina del 30 anterior (Del {inicio_q.strftime('%d/%m')} al {fin_q.strftime('%d/%m')})"

            df_q_actual = df_flujo[(df_flujo['fecha'] >= inicio_q.normalize()) & (df_flujo['fecha'] <= fin_q.normalize())]
            
            mask_debito_global = df_flujo['descripcion'].str.contains("Débito", na=False) | (~df_flujo['descripcion'].str.contains("Efectivo", na=False))
            ingresos_totales_historicos = df_flujo[df_flujo['tipo'] == 'Ingreso']['monto'].sum()
            gastos_debito_historicos = df_flujo[(df_flujo['tipo'] == 'Egreso') & mask_debito_global]['monto'].sum()
            
            # --- CORRECCIÓN CLAVE AQUÍ ---
            retiros_historicos = df_flujo[df_flujo['tipo'] == 'Retiro']['monto'].sum()
            
            # Resta correctamente los retiros de la nómina
            nomina_restante = ingresos_totales_historicos - gastos_debito_historicos - retiros_historicos

            nomina_ingresada_ciclo = df_q_actual[df_q_actual['tipo'] == 'Ingreso']['monto'].sum()
            mask_debito_q = df_q_actual['descripcion'].str.contains("Débito", na=False) | (~df_q_actual['descripcion'].str.contains("Efectivo", na=False))
            gastos_debito_ciclo = df_q_actual[(df_q_actual['tipo'] == 'Egreso') & mask_debito_q]['monto'].sum()
            gastos_efectivo_ciclo = df_q_actual[(df_q_actual['tipo'] == 'Egreso') & df_q_actual['descripcion'].str.contains("Efectivo", na=False)]['monto'].sum()

            st.markdown(f"#### 📊 Resumen: **{etiqueta_q}**")
            col_q1, col_q2, col_q3, col_q4 = st.columns(4)
            
            col_q1.metric("💵 Saldo Real en Débito (Acumulado)", fmt_monto(nomina_restante), help="Sueldo histórico menos gastos en débito y retiros de cajero.")
            col_q2.metric("💳 Gastos con Débito (Ciclo)", fmt_monto(gastos_debito_ciclo), delta_color="inverse")
            col_q3.metric("💵 Gastos en Efectivo (Ciclo)", fmt_monto(gastos_efectivo_ciclo), delta_color="inverse")
            col_q4.metric("🏦 Depositado este Ciclo", fmt_monto(nomina_ingresada_ciclo))

            fecha_fin_ciclo = fin_q.date() if hasattr(fin_q, 'date') else fin_q
            dias_restantes = (fecha_fin_ciclo - hoy_date).days + 1
            dias_para_dividir = max(dias_restantes, 1)

            gasto_diario_sugerido = nomina_restante / dias_para_dividir if nomina_restante > 0 else 0.00
            porcentaje_gastado = (gastos_debito_ciclo / (nomina_ingresada_ciclo if nomina_ingresada_ciclo > 0 else 1)) * 100

            st.markdown("---")
            st.markdown("### 🚨 Control de Ritmo de Gasto y Freno de Mano")

            col_f1, col_f2, col_f3 = st.columns(3)

            col_f1.metric("⏳ Días Restantes del Ciclo", f"{dias_restantes} días", delta=f"Cierra el {fecha_fin_ciclo.strftime('%d/%m')}")
            col_f2.metric("💳 Gasto Diario Máximo Sugerido", fmt_monto(gasto_diario_sugerido), help="Saldo Real en Débito dividido entre días faltantes.")

            if porcentaje_gastado < 70:
                col_f3.success(f"🟢 **Ritmo Saludable**\n\nHas consumido el {porcentaje_gastado:.1f}% del depósito de esta quincena.")
            elif porcentaje_gastado <= 90:
                col_f3.warning(f"🟡 **Precaución**\n\nHas consumido el {porcentaje_gastado:.1f}% del depósito de esta quincena.")
            else:
                col_f3.error(f"🔴 **FRENO DE MANO**\n\nHas consumido el {porcentaje_gastado:.1f}% del depósito de esta quincena.")

            st.markdown("---")

            # ESTRUCTURA DE GASTOS
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
                    ["Fintual", "CETES Directo", "Nu (Cajita)", "Mercado Pago / Fondo", "GBM / Acciones", "Fondo de Emergencia", "Otra Plataforma"]
                )
                monto_inv = st.number_input("Saldo Total Actual ($)", min_value=0.01, step=100.0, format="%.2f")

            with col_inv2:
                tipo_operacion = st.selectbox(
                    "Tipo de Movimiento", 
                    ["Actualización de Saldo Total", "Aportación Directa", "Retiro Parcial/Total"]
                )
                fecha_inv = st.date_input("Fecha", obtener_fecha_local(), key="fecha_inv")

            with col_inv3:
                notas_inv = st.text_input("Notas / Detalle", placeholder="Ej. Saldo al revisar la app hoy")
                submit_inv = st.form_submit_button("💾 Guardar y Actualizar Inversiones", use_container_width=True)

            if submit_inv:
                desc_completa = f"[{plataforma}] {tipo_operacion}: {notas_inv}".strip()
                categoria_inv = f"Inversión - {plataforma}"
                
                if guardar_movimiento("Inversion", monto_inv, categoria_inv, desc_completa, fecha_inv, current_user_id):
                    st.success(f"✅ Portafolio de {plataforma} actualizado.")
                    st.rerun()

    st.markdown("---")

    df_raw = obtener_movimientos(current_user_id)
    
    if not df_raw.empty:
        plataformas_conocidas = ["fintual", "cetes", "nu", "mercado pago", "gbm", "emergencia"]
        mask_inv = (
            df_raw['categoria'].str.contains("inversi", case=False, na=False) |
            df_raw['tipo'].str.contains("inversi", case=False, na=False) |
            df_raw['categoria'].str.lower().str.contains('|'.join(plataformas_conocidas), na=False)
        )
        
        df_inversiones = df_raw[mask_inv].copy()
        
        if not df_inversiones.empty:
            def extraer_plataforma(row):
                cat = str(row['categoria'])
                if "Inversión - " in cat:
                    return cat.replace("Inversión - ", "").strip()
                elif "Inversion - " in cat:
                    return cat.replace("Inversion - ", "").strip()
                desc = str(row['descripcion'])
                if desc.startswith("[") and "]" in desc:
                    return desc[1:desc.find("]")]
                return "General"

            df_inversiones['Plataforma'] = df_inversiones.apply(extraer_plataforma, axis=1)
            df_inversiones['fecha'] = pd.to_datetime(df_inversiones['fecha'])
            df_inversiones = df_inversiones.sort_values(by=['Plataforma', 'fecha', 'id'])

            resumen_filas = []

            for plat, group in df_inversiones.groupby('Plataforma'):
                ultimos_registros = group.tail(2)
                saldo_actual = ultimos_registros.iloc[-1]['monto']
                
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
                    "Variación ($)": variacion,
                    "Variación (%)": porcentaje_var
                })

            df_resumen_inv = pd.DataFrame(resumen_filas)
            total_inversiones = df_resumen_inv['Saldo Actual'].sum()
            total_variacion = df_resumen_inv['Variación ($)'].sum()

            METAS_PLATAFORMA = {
                "Fintual": 10000.0,
                "Nu (Cajita)": 10000.0,
                "CETES Directo": 20000.0,
            }

            META_INVERSION_TOTAL = sum(METAS_PLATAFORMA.values())
            faltante_meta = max(0.0, META_INVERSION_TOTAL - total_inversiones)
            progreso_pct = min(100.0, (total_inversiones / META_INVERSION_TOTAL) * 100) if META_INVERSION_TOTAL > 0 else 0

            st.markdown("### 📊 Valor Total del Portafolio de Inversión")
            col_met1, col_met2, col_met3 = st.columns(3)
            
            col_met1.metric("Patrimonio Invertido Total", fmt_monto(total_inversiones))
            
            if ocultar_saldos:
                col_met2.metric("Última Variación", "$ ••••••")
                col_met3.metric("Faltante p/ Meta Total", "$ ••••••", f"{progreso_pct:.1f}% Alcanzado")
            else:
                col_met2.metric(
                    "Última Variación", 
                    f"${total_variacion:,.2f}", 
                    delta=f"${total_variacion:,.2f}",
                    delta_color="normal"
                )
                col_met3.metric("Faltante p/ Meta Total", f"${faltante_meta:,.2f}", f"{progreso_pct:.1f}% Alcanzado")

            st.caption(f"Progreso global hacia la meta de **{fmt_monto(META_INVERSION_TOTAL)}**")
            st.progress(progreso_pct / 100.0)

            st.markdown("#### 🎯 Progreso de Metas Específicas")
            cols_m = st.columns(len(METAS_PLATAFORMA))

            for idx, (plat_nombre, meta_monto) in enumerate(METAS_PLATAFORMA.items()):
                with cols_m[idx]:
                    row_plat = df_resumen_inv[df_resumen_inv['Plataforma'].str.contains(plat_nombre.split()[0], case=False, na=False)]
                    saldo_plat = row_plat['Saldo Actual'].values[0] if not row_plat.empty else 0.0
                    
                    pct_plat = min(100.0, (saldo_plat / meta_monto) * 100) if meta_monto > 0 else 0
                    
                    st.markdown(f"**{plat_nombre}**")
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
                st.subheader("Saldos y Variación por Instrumento")
                df_mostrar_resumen = df_resumen_inv.copy()

                if ocultar_saldos:
                    df_mostrar_resumen['Saldo Actual'] = "$ ••••••"
                    df_mostrar_resumen['Variación ($)'] = "$ ••••••"
                    df_mostrar_resumen['Variación (%)'] = "••• %"
                    st.dataframe(df_mostrar_resumen, use_container_width=True, hide_index=True)
                else:
                    st.dataframe(
                        df_mostrar_resumen,
                        column_config={
                            "Plataforma": "Fondo / Plataforma",
                            "Saldo Actual": st.column_config.NumberColumn("Saldo Actual", format="$%.2f"),
                            "Variación ($)": st.column_config.NumberColumn("Ganancia / Pérdida ($)", format="$%.2f"),
                            "Variación (%)": st.column_config.NumberColumn("Cambio (%)", format="%.2f%%")
                        },
                        use_container_width=True,
                        hide_index=True
                    )

            st.markdown("---")

            st.markdown("#### 📋 Historial de Registros de Inversión")
            df_inv_disp = df_inversiones[['id', 'fecha', 'Plataforma', 'monto', 'descripcion']].sort_values(by='fecha', ascending=False).copy()
            df_inv_disp['fecha_str'] = df_inv_disp['fecha'].dt.strftime('%Y-%m-%d')
            
            config_inv_cols = {
                "id": st.column_config.NumberColumn("ID", format="%d"),
                "fecha_str": "Fecha",
                "Plataforma": "Plataforma",
                "monto": st.column_config.NumberColumn("Saldo Registrado", format="$%.2f"),
                "descripcion": "Notas"
            }

            if ocultar_saldos:
                df_inv_disp_show = df_inv_disp.copy()
                df_inv_disp_show['monto'] = "••••••"
                st.dataframe(df_inv_disp_show[['id', 'fecha_str', 'Plataforma', 'monto', 'descripcion']], column_config=config_inv_cols, use_container_width=True, hide_index=True)
            else:
                st.dataframe(
                    df_inv_disp[['id', 'fecha_str', 'Plataforma', 'monto', 'descripcion']],
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
                            ei_desc = st.text_input("Notas", value=datos_inv_reg['descripcion'])
                            
                            btn_act_inv = st.form_submit_button("💾 Guardar Cambios en Inversión")
                            if btn_act_inv:
                                if actualizar_movimiento(id_inv_sel, "Inversion", ei_monto, f"Inversión - {datos_inv_reg['Plataforma']}", ei_desc, ei_fecha, current_user_id):
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
# PESTAÑA 3: BILLETERA Y EFECTIVO
# =============================================================================
with tab_efectivo:
    st.header("👛 Control de Billetera y Efectivo")
    st.caption("Administra los billetes que retiras del cajero sin desajustar tu saldo bancario ni duplicar registros.")

    col_ef1, col_ef2 = st.columns(2)

    with col_ef1:
        st.subheader("1. 🏦 Registrar Retiro de Cajero")
        st.info("Esto descuenta el dinero de tu Débito y lo transfiere a tu Billetera (no cuenta como gasto aún).")
        
        with st.form("form_retiro_efectivo", clear_on_submit=True):
            monto_retiro = st.number_input("Monto Retirado ($)", min_value=10.0, step=50.0, format="%.2f")
            fecha_retiro = st.date_input("Fecha del Retiro", obtener_fecha_local(), key="fecha_retiro_ef")
            desc_retiro = st.text_input("Detalle / Cajero", placeholder="Ej. Cajero Santander, Retiro de emergencia, etc.")
            
            submit_retiro = st.form_submit_button("🏦 Registrar Entrada a Billetera", use_container_width=True)

        if submit_retiro:
            desc_ret_final = f"[💳 Tarjeta de Débito (Nómina)] Retiro Cajero: {desc_retiro}".strip()
            if guardar_movimiento("Retiro", monto_retiro, "Retiro de Cajero (Débito ➔ Efectivo)", desc_ret_final, fecha_retiro, USER_ID):
                st.success(f"✅ Retiro de {fmt_monto(monto_retiro)} ingresado a la Billetera.")
                st.rerun()

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

    df_raw_efectivo = obtener_movimientos(USER_ID)

    if not df_raw_efectivo.empty:
        # 1. Total que ha entrado a la billetera desde el cajero
        total_retirado = df_raw_efectivo[df_raw_efectivo['tipo'] == 'Retiro']['monto'].sum()
        
        # 2. Detecta todos los gastos realizados en efectivo (sin importar mayúsculas/minúsculas)
        mask_gastos_efectivo = (
            df_raw_efectivo['descripcion'].str.contains("efectivo", case=False, na=False) & 
            (df_raw_efectivo['tipo'] != 'Retiro')
        )
        total_gastado_efectivo = df_raw_efectivo[mask_gastos_efectivo]['monto'].sum()

        # 3. Cálculo del disponible (aquí se define la variable que daba error)
        saldo_billetera_actual = total_retirado - total_gastado_efectivo

        st.markdown("### 📊 Balance Actual de la Billetera")
        
        c_b1, c_b2, c_b3 = st.columns(3)
        c_b1.metric("🏦 Total Retirado de Cajeros", fmt_monto(total_retirado))
        c_b2.metric("💸 Total Gastado en Efectivo", fmt_monto(total_gastado_efectivo), delta_color="inverse")
        c_b3.metric("💵 Disponible en Bolsillo / Billetera", fmt_monto(saldo_billetera_actual))

        st.markdown("---")
        st.markdown("### 📋 Historial Exclusivo de Efectivo")
        
        mask_movs_efectivo = (df_raw_efectivo['tipo'] == 'Retiro') | mask_gastos_efectivo
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
        else:
            st.info("Aún no tienes movimientos registrados en efectivo.")
    else:
        st.info("No hay datos suficientes para calcular el balance de la billetera.")
