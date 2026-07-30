import streamlit as st
import pandas as pd
import psycopg2
import hashlib
from datetime import datetime, date
import calendar
import plotly.express as px

# =============================================================================
# 1. CONFIGURACIÓN DE LA PÁGINA STREAMLIT
# =============================================================================
st.set_page_config(
    page_title="Finanzas Personales - Control Quincenal e Inversiones",
    page_icon="💰",
    layout="wide"
)

# =============================================================================
# 2. CONTROL DE ACCESO Y AUTENTICACIÓN
# =============================================================================
def verificar_credenciales(usuario, contrasena):
    """
    Compara el usuario e imprime el hash SHA-256 de la contraseña ingresada
    contra las credenciales almacenadas de forma segura en st.secrets.
    """
    hash_ingresado = hashlib.sha256(contrasena.encode()).hexdigest()
    usuario_valido = st.secrets.get("AUTH_USER", "admin")
    hash_valido = st.secrets.get("AUTH_PASSWORD_HASH", "")
    return usuario == usuario_valido and hash_ingresado == hash_valido

def mostrar_login():
    """Muestra el formulario de inicio de sesión si el usuario no está autenticado."""
    st.title("🔒 Acceso Restringido")
    with st.form("form_login"):
        usuario = st.text_input("Usuario")
        contrasena = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Iniciar Sesión", use_container_width=True)
        
        if submit:
            if verificar_credenciales(usuario, contrasena):
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

# Inicializar estado de autenticación en la sesión
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# Detener la ejecución del código si el usuario no ha iniciado sesión
if not st.session_state["autenticado"]:
    mostrar_login()
    st.stop()

# =============================================================================
# 3. SIDEBAR Y MODO PRIVACIDAD
# =============================================================================
st.sidebar.title("👤 Cuenta y Ajustes")

# Toggle para ocultar las cifras monetarias en pantalla (ideal si abres la app en público)
ocultar_saldos = st.sidebar.toggle(
    "🙈 Modo Privacidad", 
    value=False, 
    help="Oculta los montos de ingresos, balance y saldos de pantalla."
)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

def fmt_monto(valor):
    """Formatea valores numéricos a formato moneda o los enmascara si el Modo Privacidad está activo."""
    if ocultar_saldos:
        return "$ ••••••"
    return f"${valor:,.2f}"

# =============================================================================
# 4. CAPA DE BASE DE DATOS (POSTGRESQL)
# =============================================================================
def get_connection():
    """Abre la conexión a la base de datos PostgreSQL utilizando la URL de st.secrets."""
    return psycopg2.connect(st.secrets["DATABASE_URL"])

@st.cache_data(ttl=60)
def obtener_movimientos():
    """
    Obtiene el historial completo de movimientos registrados en la BD.
    Utiliza un caché de 60 segundos para evitar consultas repetitivas a la BD.
    """
    conn = None
    try:
        conn = get_connection()
        query = "SELECT id, fecha, tipo, categoria, monto, descripcion FROM movimientos ORDER BY fecha DESC, id DESC"
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Error al consultar la base de datos: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def guardar_movimiento(tipo, monto, categoria, descripcion, fecha):
    """Inserta un nuevo registro (Ingreso, Egreso o Inversión) en la base de datos."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO movimientos (tipo, monto, categoria, descripcion, fecha)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (tipo, monto, categoria, descripcion.strip(), fecha)
        )
        conn.commit()
        cur.close()
        st.cache_data.clear() # Limpia el caché para refrescar vistas
        return True
    except Exception as e:
        st.error(f"Error al guardar en la base de datos: {e}")
        return False
    finally:
        if conn:
            conn.close()

def eliminar_movimiento(id_mov):
    """Elimina permanentemente un registro de la base de datos según su ID."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM movimientos WHERE id = %s", (id_mov,))
        conn.commit()
        cur.close()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al eliminar el registro: {e}")
        return False
    finally:
        if conn:
            conn.close()

def actualizar_movimiento(id_mov, tipo, monto, categoria, descripcion, fecha):
    """Actualiza los campos de un movimiento existente en la base de datos."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE movimientos 
            SET tipo = %s, monto = %s, categoria = %s, descripcion = %s, fecha = %s
            WHERE id = %s
            """,
            (tipo, monto, categoria, descripcion.strip(), fecha, id_mov)
        )
        conn.commit()
        cur.close()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al actualizar el registro: {e}")
        return False
    finally:
        if conn:
            conn.close()

# =============================================================================
# 5. ESTRUCTURA PRINCIPAL DEL DASHBOARD
# =============================================================================
st.title("💰 Control de Finanzas e Inversiones")

# Pestañas principales
tab_flujo, tab_ahorros = st.tabs([
    "💵 Flujo Quincenal y Nómina", 
    "📈 Portafolio de Inversiones (CETES, Fintual)"
])

# =============================================================================
# PESTAÑA 1: FLUJO QUINCENAL Y NÓMINA
# =============================================================================
with tab_flujo:
    
    # -------------------------------------------------------------------------
    # 5.1 FORMULARIO DE REGISTRO CON SOPORTE PARA RETIROS / TRANSFERENCIAS
    # -------------------------------------------------------------------------
    with st.expander("➕ Registrar Movimiento de Nómina, Gastos o Retiros", expanded=True):
        with st.form("form_finanzas", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                tipo = st.selectbox("Tipo de Movimiento", ["Egreso", "Ingreso", "Transferencia / Retiro"])
                monto = st.number_input("Monto ($)", min_value=0.01, step=50.0, format="%.2f")
                metodo_pago = st.selectbox("Forma de Pago / Origen", ["💳 Tarjeta de Débito (Nómina)", "💵 Efectivo"])
            
            with col2:
                if tipo == "Ingreso":
                    categorias = [
                        "Nómina / Sueldo Quincenal", 
                        "Retiro de Inversión a Débito", 
                        "Ventas / Ingresos Extra", 
                        "Otros Ingresos"
                    ]
                elif tipo == "Transferencia / Retiro":
                    categorias = [
                        "Retiro de Cajero (Débito ➔ Efectivo)",
                        "Traspaso entre Cuentas"
                    ]
                else:
                    categorias = [
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
                    
                categoria = st.selectbox("Categoría", categorias)
                fecha = st.date_input("Fecha de Operación", datetime.now(), key="fecha_flujo")

            with col3:
                descripcion_user = st.text_input(
                    "Descripción / Detalle", 
                    placeholder="Ej. Retiro cajero, Cena, Compras súper, etc.", 
                    max_chars=120
                )
                submit = st.form_submit_button("💾 Guardar Registro", use_container_width=True)

            if submit:
                desc_final = f"[{metodo_pago}] {descripcion_user}".strip()
                if guardar_movimiento(tipo, monto, categoria, desc_final, fecha):
                    st.success(f"✅ {tipo} ({categoria}) registrado con éxito.")
                    st.rerun()

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 5.2 LÓGICA DE DÍAS RESTANTES Y SALDO ACUMULADO REAL
    # -------------------------------------------------------------------------
    df_raw = obtener_movimientos()

    if not df_raw.empty:
        # Filtrar excluyendo movimientos etiquetados como Inversiones
        mask_inversion = df_raw['categoria'].str.contains("Inversión", case=False, na=False) | (df_raw['tipo'] == 'Inversion')
        df_flujo = df_raw[~mask_inversion].copy()
        
        if not df_flujo.empty:
            df_flujo['fecha'] = pd.to_datetime(df_flujo['fecha'])
            hoy_ts = pd.Timestamp.now()
            hoy_date = date.today()

            st.markdown("### 📅 Ciclo de Nómina Actual")
            
            # Determinación automática de la quincena activa (del 15 al 29 o del 30 al 14)
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

            # Filtrar datos de la quincena activa
            df_q_actual = df_flujo[(df_flujo['fecha'] >= inicio_q.normalize()) & (df_flujo['fecha'] <= fin_q.normalize())]
            
            # Cálculo del Saldo Real en Débito (Modelo Acumulativo de Liquidez)
            mask_debito_global = df_flujo['descripcion'].str.contains("Débito", na=False) | (~df_flujo['descripcion'].str.contains("Efectivo", na=False))
            ingresos_totales_historicos = df_flujo[df_flujo['tipo'] == 'Ingreso']['monto'].sum()
            gastos_debito_historicos = df_flujo[(df_flujo['tipo'] == 'Egreso') & mask_debito_global]['monto'].sum()

            retiros_historicos = df_flujo[df_flujo['tipo'] == 'Transferencia / Retiro']['monto'].sum()

            # Saldo disponible real acumulando remanentes de quincenas pasadas
            nomina_restante = ingresos_totales_historicos - gastos_debito_historicos - retiros_historicos

            # Métricas exclusivas del ciclo activo
            nomina_ingresada_ciclo = df_q_actual[df_q_actual['tipo'] == 'Ingreso']['monto'].sum()
            mask_debito_q = df_q_actual['descripcion'].str.contains("Débito", na=False) | (~df_q_actual['descripcion'].str.contains("Efectivo", na=False))
            gastos_debito_ciclo = df_q_actual[(df_q_actual['tipo'] == 'Egreso') & mask_debito_q]['monto'].sum()
            gastos_efectivo_ciclo = df_q_actual[(df_q_actual['tipo'] == 'Egreso') & df_q_actual['descripcion'].str.contains("Efectivo", na=False)]['monto'].sum()

            # Presentación de tarjetas de métricas
            st.markdown(f"#### 📊 Resumen: **{etiqueta_q}**")
            col_q1, col_q2, col_q3, col_q4 = st.columns(4)
            
            col_q1.metric("💵 Saldo Real en Débito (Acumulado)", fmt_monto(nomina_restante), help="Incluye sobrantes de quincenas pasadas.")
            col_q2.metric("💳 Gastos con Débito (Ciclo)", fmt_monto(gastos_debito_ciclo), delta_color="inverse")
            col_q3.metric("💵 Gastos en Efectivo (Ciclo)", fmt_monto(gastos_efectivo_ciclo), delta_color="inverse")
            col_q4.metric("🏦 Depositado este Ciclo", fmt_monto(nomina_ingresada_ciclo))

            # -------------------------------------------------------------------------
            # 5.3 FRENO DE MANO Y RITMO DE GASTO
            # -------------------------------------------------------------------------
            fecha_fin_ciclo = fin_q.date() if hasattr(fin_q, 'date') else fin_q
            fecha_hoy = hoy_date.date() if hasattr(hoy_date, 'date') else hoy_date

            # Cálculo exacto de días restantes sumando el offset (+1) para incluir el día presente
            dias_restantes = (fecha_fin_ciclo - fecha_hoy).days + 1
            dias_para_dividir = max(dias_restantes, 1)

            # Tope diario recomendado dividiendo el Saldo Real entre los días faltantes
            gasto_diario_sugerido = nomina_restante / dias_para_dividir if nomina_restante > 0 else 0.00
            
            # Semáforo de consumo sobre el depósito quincenal
            porcentaje_gastado = (gastos_debito_ciclo / (nomina_ingresada_ciclo if nomina_ingresada_ciclo > 0 else 1)) * 100

            st.markdown("---")
            st.markdown("### 🚨 Control de Ritmo de Gasto y Freno de Mano")

            col_f1, col_f2, col_f3 = st.columns(3)

            col_f1.metric("⏳ Días Restantes del Ciclo", f"{dias_restantes} días", delta=f"Cierra el {fecha_fin_ciclo.strftime('%d/%m')}")
            col_f2.metric("💳 Gasto Diario Máximo Sugerido", fmt_monto(gasto_diario_sugerido), help="Calculado dividiendo tu Saldo Real en Débito entre los días que faltan.")

            if porcentaje_gastado < 70:
                col_f3.success(f"🟢 **Ritmo Saludable**\n\nHas consumido el {porcentaje_gastado:.1f}% del depósito de esta quincena.")
            elif porcentaje_gastado <= 90:
                col_f3.warning(f"🟡 **Precaución**\n\nHas consumido el {porcentaje_gastado:.1f}% del depósito de esta quincena.")
            else:
                col_f3.error(f"🔴 **FRENO DE MANO**\n\nHas consumido el {porcentaje_gastado:.1f}% del depósito de esta quincena.")

            st.markdown("---")

            # -------------------------------------------------------------------------
            # 5.4 VISTAS Y TABLAS DE HISTORIAL
            # -------------------------------------------------------------------------
            st.markdown("### 📊 Desglose de Gastos del Ciclo")
            col_graf1, col_graf2 = st.columns(2)

            with col_graf1:
                st.subheader("Egresos por Categoría")
                df_egresos_q = df_q_actual[df_q_actual['tipo'] == 'Egreso']
                if not df_egresos_q.empty:
                    cat_q = df_egresos_q.groupby('categoria')['monto'].sum().reset_index()
                    st.bar_chart(cat_q, x='categoria', y='monto', color="#FF4B4B")
                else:
                    st.info("No hay gastos registrados dentro de este ciclo de nómina.")

            with col_graf2:
                st.subheader("Pagos a Tarjetas de Crédito (Este Mes)")
                df_mes = df_flujo[(df_flujo['fecha'].dt.month == hoy_ts.month) & (df_flujo['fecha'].dt.year == hoy_ts.year)]
                df_tdc = df_mes[(df_mes['tipo'] == 'Egreso') & (df_mes['categoria'].str.contains("TDC", na=False))].copy()
                
                if not df_tdc.empty:
                    total_tdc = df_tdc['monto'].sum()
                    st.metric("Total Abonado a TDC", fmt_monto(total_tdc))
                    
                    df_tdc_disp = df_tdc[['fecha', 'descripcion', 'monto']].copy()
                    df_tdc_disp['fecha'] = df_tdc_disp['fecha'].dt.strftime('%Y-%m-%d')
                    if ocultar_saldos:
                        df_tdc_disp['monto'] = "••••••"
                    st.dataframe(df_tdc_disp, use_container_width=True, hide_index=True)
                else:
                    st.caption("No se han registrado pagos de TDC este mes.")

            st.markdown("---")

            st.markdown("### 📋 Historial Completo de Nómina y Gastos")
            df_display = df_flujo.copy()
            df_display['fecha_str'] = df_display['fecha'].dt.strftime('%Y-%m-%d')
            
            if ocultar_saldos:
                df_display_show = df_display.copy()
                df_display_show['monto'] = "••••••"
                st.dataframe(
                    df_display_show[['id', 'fecha_str', 'tipo', 'categoria', 'monto', 'descripcion']],
                    column_config={
                        "id": "ID",
                        "fecha_str": "Fecha",
                        "tipo": "Tipo",
                        "categoria": "Categoría",
                        "monto": "Monto ($)",
                        "descripcion": "Descripción"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.dataframe(
                    df_display[['id', 'fecha_str', 'tipo', 'categoria', 'monto', 'descripcion']],
                    column_config={
                        "id": "ID",
                        "fecha_str": "Fecha",
                        "tipo": "Tipo",
                        "categoria": "Categoría",
                        "monto": st.column_config.NumberColumn("Monto", format="$%.2f"),
                        "descripcion": "Descripción"
                    },
                    use_container_width=True,
                    hide_index=True
                )

            st.markdown("---")
            # Módulo para modificar o eliminar un registro por ID
            with st.expander("✏️ Editar o Eliminar un Registro de la Lista"):
                opciones_registros = {
                    f"ID {row['id']} | {row['fecha_str']} - {row['descripcion']} (${row['monto']:,.2f})": row['id']
                    for _, row in df_display.iterrows()
                }
                
                registro_sel = st.selectbox("Selecciona el registro a modificar:", list(opciones_registros.keys()))
                id_seleccionado = opciones_registros[registro_sel]
                
                datos_reg = df_display[df_display['id'] == id_seleccionado].iloc[0]
                
                col_edit1, col_edit2 = st.columns(2)
                
                with col_edit1:
                    st.markdown("#### 🔄 Editar Registro")
                    with st.form("form_editar_flujo"):
                        e_fecha = st.date_input("Fecha Correcta", datos_reg['fecha'].date())
                        e_tipo = st.selectbox("Tipo", ["Egreso", "Ingreso"], index=0 if datos_reg['tipo']=="Egreso" else 1)
                        e_monto = st.number_input("Monto Correcto ($)", value=float(datos_reg['monto']), min_value=0.01, step=10.0, format="%.2f")
                        
                        cats_edit = [
                            "Nómina / Sueldo Quincenal", "Retiro de Inversión a Débito", "Ventas / Ingresos Extra", "Otros Ingresos",
                            "Pago TDC (Tarjeta de Crédito)", "Aportación a Inversión (Enviado a CETES/Fintual)",
                            "Alimentación / Súper", "Vivienda / Servicios", "Transporte / Gasolina", 
                            "Salud / Gastos Médicos", "Ocio / Entretenimiento", "Suscripciones", "Otros Egresos"
                        ]
                        idx_cat = cats_edit.index(datos_reg['categoria']) if datos_reg['categoria'] in cats_edit else 0
                        e_cat = st.selectbox("Categoría", cats_edit, index=idx_cat)
                        e_desc = st.text_input("Descripción", value=datos_reg['descripcion'])
                        
                        btn_actualizar = st.form_submit_button("💾 Guardar Cambios")
                        if btn_actualizar:
                            if actualizar_movimiento(id_seleccionado, e_tipo, e_monto, e_cat, e_desc, e_fecha):
                                st.success("✅ Registro actualizado correctamente.")
                                st.rerun()

                with col_edit2:
                    st.markdown("#### 🗑️ Eliminar Registro")
                    st.warning("Esta acción borrará el registro de la base de datos de forma permanente.")
                    if st.button("❌ Borrar Registro Seleccionado", use_container_width=True):
                        if eliminar_movimiento(id_seleccionado):
                            st.success("✅ Registro eliminado.")
                            st.rerun()

        else:
            st.info("Aún no tienes movimientos de nómina o gastos registrados.")
    else:
        st.info("Aún no hay registros en la base de datos.")

    # -------------------------------------------------------------------------
    # 5.5 ESTRUCTURA 50/30/20 Y LUPA INTERACTIVA
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📈 Distribución de Gastos: Fijos vs. Variables vs. Inversión")

    # Mapeo de categorías a pilares de la regla 50/30/20
    categorias_fijas = [
        "Servicios (Luz, Agua, Gas, Internet)", "Supermercado / Despensa", 
        "Renta / Vivienda", "Transporte / Gasolina", "Pago TDC (Tarjeta de Crédito)", "Salud / Médicos"
    ]

    categorias_variables = [
        "Restaurantes / Salidas", "Ocio / Entretenimiento", "Compras Personales", 
        "Suscripciones", "Gastos Hormiga / Varios"
    ]

    if 'df_flujo' in locals() and not df_flujo.empty:
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

            # Gráfica general de Dona (50/30/20)
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

            # Sección de Inspección Interactiva (Lupa por Bloque)
            st.markdown("#### 🔎 Inspeccionar un Bloque a Detalle")
            
            bloque_seleccionado = st.selectbox(
                "Selecciona la estructura que deseas analizar a fondo:",
                options=df_resumen_tipo['Tipo_Estructura'].unique(),
                index=0
            )

            df_detalle_bloque = df_gastos_ciclo[df_gastos_ciclo['Tipo_Estructura'] == bloque_seleccionado]

            col_det1, col_det2 = st.columns([1, 1])

            with col_det1:
                st.caption(f"**¿En qué categorías se dividió '{bloque_seleccionado}'?**")
                df_cat_summary = df_detalle_bloque.groupby('categoria')['monto'].sum().reset_index().sort_values(by='monto', ascending=True)
                
                fig_bar = px.bar(
                    df_cat_summary, 
                    x='monto', 
                    y='categoria', 
                    orientation='h',
                    text_auto='.2f',
                    color_discrete_sequence=['#FF7F0E' if 'Variables' in bloque_seleccionado else '#1F77B4']
                )
                fig_bar.update_layout(xaxis_title="Monto ($)", yaxis_title="", margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_det2:
                st.caption(f"**Últimos registros en {bloque_seleccionado}:**")
                cols_mostrar = ['fecha', 'categoria', 'descripcion', 'monto']
                df_tabla_show = df_detalle_bloque[cols_mostrar].copy()
                df_tabla_show['fecha'] = df_tabla_show['fecha'].dt.strftime('%d/%m/%Y')
                
                st.dataframe(
                    df_tabla_show,
                    column_config={
                        "fecha": "Fecha",
                        "categoria": "Categoría",
                        "descripcion": "Nota / Concepto",
                        "monto": st.column_config.NumberColumn("Monto", format="$%.2f")
                    },
                    use_container_width=True,
                    hide_index=True
                )

            # -------------------------------------------------------------------------
            # 5.6 MÓDULO DE ANÁLISIS DE GASTOS POR SEMANA (DOMINGO A SÁBADO) + DESGLOSE
            # -------------------------------------------------------------------------
            st.markdown("---")
            st.markdown("### 📅 Comportamiento de Gasto por Semana")

            # Formato de semana alineado al calendario tradicional (Domingo = Inicio de semana)
            df_gastos_ciclo['Semana_Num'] = df_gastos_ciclo['fecha'].dt.strftime('%U').astype(int)
            df_gastos_ciclo['Semana_Label'] = df_gastos_ciclo['fecha'].dt.strftime('Semana %U')

            # Agrupación por número de semana dentro del ciclo
            df_semanal = df_gastos_ciclo.groupby(['Semana_Num', 'Semana_Label'])['monto'].sum().reset_index()
            df_semanal = df_semanal.sort_values('Semana_Num')

            col_sem1, col_sem2 = st.columns([1.2, 1])

            with col_sem1:
                fig_semana = px.bar(
                    df_semanal,
                    x='Semana_Label',
                    y='monto',
                    text_auto='.2f',
                    title="Gasto Acumulado por Semana",
                    labels={'Semana_Label': 'Semana', 'monto': 'Total ($)'},
                    color_discrete_sequence=['#2CA02C']
                )
                fig_semana.update_layout(xaxis_title="", yaxis_title="Monto ($)", margin=dict(t=30, b=10, l=10, r=10))
                st.plotly_chart(fig_semana, use_container_width=True)

            with col_sem2:
                st.caption("**Resumen Semanal:**")
                promedio_semanal = df_semanal['monto'].mean()
                st.metric("Promedio por Semana", fmt_monto(promedio_semanal))

                st.dataframe(
                    df_semanal[['Semana_Label', 'monto']],
                    column_config={
                        "Semana_Label": "Semana",
                        "monto": st.column_config.NumberColumn("Total Gastado", format="$%.2f")
                    },
                    use_container_width=True,
                    hide_index=True
                )

            # =========================================================================
            # 🔎 NUEVO: DESGLOSE DETALLADO DE LO QUE SE GASTÓ EN LA SEMANA SELECCIONADA
            # =========================================================================
            st.markdown("#### 🔍 Ver Gastos a Detalle por Semana")

            semanas_disponibles = df_semanal['Semana_Label'].tolist()
            
            semana_seleccionada = st.selectbox(
                "Selecciona la semana que deseas auditar:",
                options=semanas_disponibles,
                index=len(semanas_disponibles) - 1 # Selecciona automáticamente la semana más reciente
            )

            # Filtrar los gastos únicamente de la semana seleccionada
            df_semana_det = df_gastos_ciclo[df_gastos_ciclo['Semana_Label'] == semana_seleccionada]

            col_sdet1, col_sdet2 = st.columns([1, 1])

            with col_sdet1:
                st.caption(f"**Categorías en las que más gastaste en la {semana_seleccionada}:**")
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

            with col_sdet2:
                st.caption(f"**Lista de compras/pagos en la {semana_seleccionada}:**")
                df_tabla_sem = df_semana_det[['fecha', 'categoria', 'descripcion', 'monto']].copy()
                df_tabla_sem['fecha'] = df_tabla_sem['fecha'].dt.strftime('%d/%m/%Y')
                
                if ocultar_saldos:
                    df_tabla_sem['monto'] = "••••••"
                    st.dataframe(df_tabla_sem, use_container_width=True, hide_index=True)
                else:
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

# =============================================================================
# PESTAÑA 2: PORTAFOLIO DE INVERSIONES
# =============================================================================
with tab_ahorros:
    st.markdown("### 📈 Portafolio de Inversiones (CETES, Fintual, etc.)")
    st.caption("Esta sección analiza únicamente tus cuentas de inversión y su rendimiento. No se mezcla con tu nómina.")

    # Formulario para registrar saldos de portafolios de inversión
    with st.expander("➕ Registrar / Actualizar Saldo de Inversión", expanded=True):
        with st.form("form_inversiones", clear_on_submit=True):
            col_inv1, col_inv2, col_inv3 = st.columns(3)
            
            with col_inv1:
                plataforma = st.selectbox(
                    "Plataforma / Fondo",
                    [
                        "Fintual",
                        "CETES Directo", 
                        "Nu (Cajita)", 
                        "Mercado Pago / Fondo", 
                        "GBM / Acciones", 
                        "Fondo de Emergencia", 
                        "Otra Plataforma"
                    ]
                )
                monto_inv = st.number_input("Saldo Total Actual ($)", min_value=0.01, step=100.0, format="%.2f")

            with col_inv2:
                tipo_operacion = st.selectbox(
                    "Tipo de Movimiento", 
                    ["Actualización de Saldo Total", "Aportación Directa", "Retiro Parcial/Total"]
                )
                fecha_inv = st.date_input("Fecha", datetime.now(), key="fecha_inv")

            with col_inv3:
                notas_inv = st.text_input("Notas / Detalle", placeholder="Ej. Saldo al revisar la app hoy")
                submit_inv = st.form_submit_button("💾 Guardar y Actualizar Inversiones", use_container_width=True)

            if submit_inv:
                desc_completa = f"[{plataforma}] {tipo_operacion}: {notas_inv}".strip()
                categoria_inv = f"Inversión - {plataforma}"
                
                if guardar_movimiento("Inversion", monto_inv, categoria_inv, desc_completa, fecha_inv):
                    st.success(f"✅ Portafolio de {plataforma} actualizado.")
                    st.rerun()

    st.markdown("---")

    # Cálculos y resúmenes de rendimiento de fondos
    df_raw = obtener_movimientos()
    if not df_raw.empty:
        mask_inv = df_raw['categoria'].str.contains("Inversión", case=False, na=False) | (df_raw['tipo'] == 'Inversion')
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

            # Comparativa contra el registro previo para evaluar variaciones ($ y %)
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

            st.markdown("### 📊 Valor Total del Portafolio de Inversión")
            col_met1, col_met2 = st.columns(2)
            
            col_met1.metric(
                "Patrimonio Invertido Total", 
                fmt_monto(total_inversiones)
            )
            
            if ocultar_saldos:
                col_met2.metric("Última Variación Ganancia/Pérdida", "$ ••••••")
            else:
                col_met2.metric(
                    "Última Variación Ganancia/Pérdida", 
                    f"${total_variacion:,.2f}", 
                    delta=f"${total_variacion:,.2f}",
                    delta_color="normal"
                )

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
                    st.markdown("### 🎯 Proyección de Metas de Inversión")

                    metas = {
                        "Fintual": {"meta": 10000.0, "rendimiento_anual": 0.09},
                        "CETES Directo": {"meta": 20000.0, "rendimiento_anual": 0.11},
                        "Nu (Cajita)": {"meta": 10000.0, "rendimiento_anual": 0.135}
                    }

                    col_meta1, col_meta2 = st.columns(2)

                    with col_meta1:
                        st.subheader("Avance de Objetivos")
                        for plat, datos_meta in metas.items():
                            fila_plat = df_resumen_inv[df_resumen_inv['Plataforma'] == plat]
                            saldo_act = fila_plat['Saldo Actual'].values[0] if not fila_plat.empty else 0.0
                            
                            target = datos_meta['meta']
                            porcentaje = min(saldo_act / target, 1.0) if target > 0 else 0.0
                            
                            st.write(f"**{plat}:** {fmt_monto(saldo_act)} / {fmt_monto(target)}")
                            st.progress(porcentaje, text=f"{porcentaje * 100:.1f}% completado")

                    with col_meta2:
                        st.subheader("Proyección a Fin de Año (Rendimientos)")
                        meses_restantes = 12 - hoy_ts.month
                        
                        proyecciones = []
                        for plat, datos_meta in metas.items():
                            fila_plat = df_resumen_inv[df_resumen_inv['Plataforma'] == plat]
                            saldo_act = fila_plat['Saldo Actual'].values[0] if not fila_plat.empty else 0.0
                            
                            tasa_mensual = datos_meta['rendimiento_anual'] / 12
                            saldo_proyectado = saldo_act * ((1 + tasa_mensual) ** meses_restantes)
                            rendimiento_estimado = saldo_proyectado - saldo_act
                            
                            proyecciones.append({
                                "Plataforma": plat,
                                "Saldo Actual": saldo_act,
                                "Rendimiento Est. (Fin de Año)": rendimiento_estimado,
                                "Total Est. Diciembre": saldo_proyectado
                            })
                        
                        df_proyectado = pd.DataFrame(proyecciones)
                        
                        if ocultar_saldos:
                            df_proyectado_show = df_proyectado.copy()
                            df_proyectado_show['Saldo Actual'] = "$ ••••••"
                            df_proyectado_show['Rendimiento Est. (Fin de Año)'] = "$ ••••••"
                            df_proyectado_show['Total Est. Diciembre'] = "$ ••••••"
                            st.dataframe(df_proyectado_show, use_container_width=True, hide_index=True)
                        else:
                            st.dataframe(
                                df_proyectado,
                                column_config={
                                    "Plataforma": "Fondo",
                                    "Saldo Actual": st.column_config.NumberColumn("Actual", format="$%.2f"),
                                    "Rendimiento Est. (Fin de Año)": st.column_config.NumberColumn("Ganancia Est.", format="$%.2f"),
                                    "Total Est. Diciembre": st.column_config.NumberColumn("Proyección Cierre", format="$%.2f")
                                },
                                use_container_width=True,
                                hide_index=True
                            )

            st.markdown("---")

            st.markdown("#### 📋 Historial de Registros de Inversión")
            df_inv_disp = df_inversiones[['id', 'fecha', 'Plataforma', 'monto', 'descripcion']].sort_values(by='fecha', ascending=False).copy()
            df_inv_disp['fecha_str'] = df_inv_disp['fecha'].dt.strftime('%Y-%m-%d')
            
            if ocultar_saldos:
                df_inv_disp_show = df_inv_disp.copy()
                df_inv_disp_show['monto'] = "••••••"
                st.dataframe(df_inv_disp_show[['id', 'fecha_str', 'Plataforma', 'monto', 'descripcion']], use_container_width=True, hide_index=True)
            else:
                st.dataframe(
                    df_inv_disp[['id', 'fecha_str', 'Plataforma', 'monto', 'descripcion']],
                    column_config={
                        "id": "ID",
                        "fecha_str": "Fecha",
                        "Plataforma": "Plataforma",
                        "monto": st.column_config.NumberColumn("Saldo Registrado", format="$%.2f"),
                        "descripcion": "Notas"
                    },
                    use_container_width=True,
                    hide_index=True
                )

            with st.expander("✏️ Editar o Eliminar un Registro de Inversión"):
                opciones_inv = {
                    f"ID {row['id']} | {row['fecha_str']} - {row['Plataforma']} (${row['monto']:,.2f})": row['id']
                    for _, row in df_inv_disp.iterrows()
                }
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
                            if actualizar_movimiento(id_inv_sel, "Inversion", ei_monto, f"Inversión - {datos_inv_reg['Plataforma']}", ei_desc, ei_fecha):
                                st.success("✅ Registro de inversión actualizado.")
                                st.rerun()

                with col_einv2:
                    st.markdown("#### 🗑️ Eliminar Inversión")
                    if st.button("❌ Borrar Registro de Inversión", use_container_width=True):
                        if eliminar_movimiento(id_inv_sel):
                            st.success("✅ Registro eliminado.")
                            st.rerun()

        else:
            st.info("Aún no has registrado cuentas en tu portafolio de inversión.")
    else:
        st.info("No hay datos registrados aún.")