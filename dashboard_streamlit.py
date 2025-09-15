import streamlit as st

# CONFIGURAR PÁGINA PRIMERO (debe ser lo primero siempre)
st.set_page_config(
    page_title="Dashboard Seccionadora - LCDC",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import con manejo de error
try:
    from database import DATABASE_URL, ENGINE
    
    if ENGINE is None:
        st.error("❌ No se pudo conectar a la base de datos")
        st.info("Verifica la configuración de secrets")
        st.stop()
        
except ImportError as e:
    st.error(f"❌ Error importando database module: {e}")
    st.stop()
except Exception as e:
    st.error(f"❌ Error de configuración: {e}")
    st.stop()

# IMPORTS PARA EL DASHBOARD
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import text
from datetime import datetime, timedelta
import logging
from typing import Optional

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seccionadora_dashboard")

# Paleta de colores unificada - Tonalidades azules
COLORS = {
    'primary': '#2E86AB',      # Azul corporativo principal
    'secondary': '#1B4F72',    # Azul oscuro
    'accent': '#5DADE2',       # Azul claro
    'success': '#3498DB',      # Azul medio
    'info': '#85C1E9',         # Azul muy claro
    'warning': '#2980B9',      # Azul fuerte
    'light': '#AED6F1',        # Azul pastel
    'dark': '#154360',         # Azul muy oscuro
}

# Gradientes para KPI cards - Tonalidades azules unificadas
KPI_GRADIENTS = [
    "linear-gradient(90deg, #1B4F72 0%, #2E86AB 100%)",
    "linear-gradient(90deg, #2E86AB 0%, #5DADE2 100%)", 
    "linear-gradient(90deg, #5DADE2 0%, #85C1E9 100%)",
    "linear-gradient(90deg, #3498DB 0%, #2980B9 100%)",
    "linear-gradient(90deg, #2980B9 0%, #1B4F72 100%)",
    "linear-gradient(90deg, #154360 0%, #1B4F72 100%)",
    "linear-gradient(90deg, #85C1E9 0%, #5DADE2 100%)",
    "linear-gradient(90deg, #2E86AB 0%, #3498DB 100%)",
]

def create_kpi_explanation(kpi_name: str, explanation: str):
    """Crear elemento desplegable explicativo para KPIs"""
    with st.expander(f"ℹ️ ¿Qué significa {kpi_name}?"):
        st.info(explanation)

def format_time_duration(seconds: float) -> str:
    """Formatear duración en formato legible"""
    if pd.isna(seconds) or seconds == 0:
        return "0h 0min"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}min"

def get_connection():
    """Obtener conexión a PostgreSQL usando ENGINE global"""
    return ENGINE

@st.cache_data(ttl=300)  # 5 minutos
def load_data(query: str) -> pd.DataFrame:
    """Cargar datos desde PostgreSQL con manejo de errores robusto"""
    logger.debug(f"Ejecutando consulta: {query[:100]}...")
    
    try:
        engine = get_connection()
        if engine is None:
            return pd.DataFrame()
            
        df = pd.read_sql(query, engine)
        logger.info(f"Consulta exitosa - Filas: {len(df)}")
        return df
        
    except Exception as e:
        logger.error(f"Error ejecutando consulta: {e}")
        st.error(f"❌ Error en consulta de datos: {e}")
        
        # Mostrar información de ayuda según el tipo de error
        if "relation" in str(e).lower():
            st.info("💡 Parece que falta crear las tablas en la base de datos")
        elif "authentication" in str(e).lower():
            st.info("💡 Error de autenticación - verifica usuario y contraseña")
        elif "connection" in str(e).lower():
            st.info("💡 Error de conexión - verifica host y puerto")
            
        return pd.DataFrame()

def main():
    """Función principal de la aplicación"""
    
    # Header con información del sistema
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🏭 Dashboard Seccionadora - LCDC Mendoza")
    with col2:
        st.caption("Entorno: STREAMLIT_CLOUD")
        if st.button("🔄 Limpiar Cache", help="Limpiar cache de datos"):
            st.cache_data.clear()
            st.success("Cache limpiado exitosamente")
            
    st.markdown("---")
    
    # Configuración ya validada al inicio del archivo
    # La conexión ENGINE ya fue testeada en database.py
        
    # Validar conexión a base de datos solo al cargar datos
    # No bloquear la carga inicial de la interfaz
    
    # Sidebar para navegación
    st.sidebar.title("📊 Navegación")
    page = st.sidebar.selectbox(
        "Seleccionar vista:",
        ["📈 Análisis de Producción", "⚡ Análisis por Espesores", "🔧 Análisis por Trabajos"]
    )
    
    if page == "📈 Análisis de Producción":
        show_production_analysis()
    elif page == "⚡ Análisis por Espesores":
        show_thickness_analysis()
    elif page == "🔧 Análisis por Trabajos":
        show_jobs_analysis()

def show_production_analysis():
    st.header("📈 Análisis de Producción")
    
    # Filtro de fechas en sidebar
    with st.sidebar:
        st.markdown("### 📅 Filtros de Fecha")
        fecha_inicio = st.date_input("Fecha inicio", value=datetime(2025, 7, 1), key="production_start")
        fecha_fin = st.date_input("Fecha fin", value=datetime(2025, 8, 13), key="production_end")
    
    # ==================== SECCIÓN 1: KPIs EJECUTIVOS ====================
    st.subheader("📊 Indicadores Ejecutivos del Período")
    
    # KPIs principales corregidos según lógica de negocio LCDC
    col1, col2, col3, col4 = st.columns(4)
    
    # Consultar datos principales corregidos con filtro de fecha
    total_data = load_data(f"""
        SELECT 
            COUNT(*) as total_esquemas,
            SUM(cantidad_placas) as total_placas_procesadas,
            COUNT(DISTINCT job_key) as trabajos_unicos,
            COUNT(DISTINCT fecha_proceso) as dias_activos,
            AVG(duracion_segundos) as duracion_promedio_seg,
            SUM(CASE WHEN espesor_mm = 18 THEN cantidad_placas ELSE 0 END) as placas_blancas_18mm
        FROM cortes_seccionadora
        WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
    """)
    
    # Calcular métricas de tiempo
    tiempo_data = load_data(f"""
        WITH daily_machine_time AS (
            SELECT 
                fecha_proceso,
                MIN(hora_inicio) as primer_inicio,
                MAX(hora_fin) as ultimo_fin,
                EXTRACT(EPOCH FROM (MAX(hora_fin) - MIN(hora_inicio))) as tiempo_total_maquina_seg
            FROM cortes_seccionadora
            WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
            GROUP BY fecha_proceso
        ),
        daily_productive_time AS (
            SELECT 
                fecha_proceso,
                SUM(duracion_segundos) as tiempo_productivo_seg
            FROM cortes_seccionadora
            WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
            GROUP BY fecha_proceso
        )
        SELECT 
            SUM(dt.tiempo_total_maquina_seg) as tiempo_total_maquina_segundos,
            SUM(dp.tiempo_productivo_seg) as tiempo_total_productivo_segundos,
            CASE WHEN SUM(dt.tiempo_total_maquina_seg) > 0 
                 THEN (SUM(dp.tiempo_productivo_seg) / SUM(dt.tiempo_total_maquina_seg)) * 100 
                 ELSE 0 
            END as tasa_tiempo_productivo
        FROM daily_machine_time dt
        JOIN daily_productive_time dp ON dt.fecha_proceso = dp.fecha_proceso
    """)
    
    if not total_data.empty and not tiempo_data.empty:
        data = total_data.iloc[0]
        tiempo = tiempo_data.iloc[0]
        
        with col1:
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #1B4F72 0%, #2E86AB 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">🔧 Total Esquemas</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:,}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Programas ejecutados</p>
                </div>
                """.format(int(data['total_esquemas'])), unsafe_allow_html=True)
            create_kpi_explanation(
                "Total Esquemas",
                "Cada esquema representa un programa de corte específico. Un esquema puede procesar una o varias placas según el diseño."
            )
        
        with col2:
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #2E86AB 0%, #5DADE2 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">📦 Placas Procesadas</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:,}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Unidades procesadas</p>
                </div>
                """.format(int(data['total_placas_procesadas'])), unsafe_allow_html=True)
        
        with col3:
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #5DADE2 0%, #85C1E9 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">⚪ Placas Blancas 18mm</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:,}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Material específico</p>
                </div>
                """.format(int(data['placas_blancas_18mm'])), unsafe_allow_html=True)
        
        
        # Segunda fila de KPIs
        col1, col2, col3 = st.columns(3)
        
        with col1:
            promedio_min_esquema = data['duracion_promedio_seg'] / 60
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #2980B9 0%, #1B4F72 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">⏱️ Min/Esquema</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">min promedio</p>
                </div>
                """.format(promedio_min_esquema), unsafe_allow_html=True)
        
        with col2:
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #1B4F72 0%, #154360 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">🕐 Tiempo total de trabajo</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Solo trabajando</p>
                </div>
                """.format(format_time_duration(tiempo['tiempo_total_productivo_segundos'])), unsafe_allow_html=True)
        
        with col3:
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #85C1E9 0%, #5DADE2 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">📈 Productividad</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}%</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Eficiencia</p>
                </div>
                """.format(tiempo['tasa_tiempo_productivo']), unsafe_allow_html=True)
            create_kpi_explanation(
                "Productividad",
                "La productividad se calcula como: (Tiempo Productivo / Tiempo Total de Máquina) * 100. Tiempo Productivo es la suma de todas las duraciones de esquemas ejecutados. Tiempo Total de Máquina es desde el primer inicio hasta el último fin de cada día."
            )
        
        # Tercera fila de KPIs avanzados
        st.markdown("### 📊 Métricas Avanzadas")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            tasa_improductiva = 100 - tiempo['tasa_tiempo_productivo']
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #154360 0%, #1B4F72 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">📉 Tiempo Improductivo</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}%</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Paradas/Esperas</p>
                </div>
                """.format(tasa_improductiva), unsafe_allow_html=True)
        
        with col2:
            placas_por_hora_efectiva = data['total_placas_procesadas'] / (tiempo['tiempo_total_productivo_segundos'] / 3600) if tiempo['tiempo_total_productivo_segundos'] > 0 else 0
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #2980B9 0%, #5DADE2 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">🚀 Placas/Hora Efectiva</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Ritmo productivo</p>
                </div>
                """.format(placas_por_hora_efectiva), unsafe_allow_html=True)
        
        with col3:
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #3498DB 0%, #2E86AB 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">📅 Días Activos</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Con producción</p>
                </div>
                """.format(int(data['dias_activos'])), unsafe_allow_html=True)
            
        # ==================== SECCIÓN 2: ANÁLISIS POR MATERIAL ====================
        st.markdown("---")
        st.subheader("📏 Análisis por Tipos de Material (Espesores)")
        
        thickness_summary = load_data(f"""
            SELECT 
                espesor_mm,
                COUNT(*) as total_esquemas,
                SUM(cantidad_placas) as total_placas,
                AVG(duracion_segundos) as duracion_promedio_seg
            FROM cortes_seccionadora
            WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
            GROUP BY espesor_mm
            ORDER BY total_placas DESC
        """)
        
        if not thickness_summary.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart de distribución
                fig_pie = px.pie(
                    thickness_summary, 
                    values='total_placas', 
                    names='espesor_mm',
                    title='📊 Distribución de Placas por Espesor',
                    color_discrete_sequence=[COLORS['primary'], COLORS['secondary'], COLORS['accent'], COLORS['success'], COLORS['info'], COLORS['dark']]
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(
                    height=400, 
                    title_font_size=16, 
                    title_x=0.0,
                    title_y=0.95,
                    font=dict(family="Arial, sans-serif", size=12)
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Bar chart de tiempos
                thickness_summary['duracion_min'] = thickness_summary['duracion_promedio_seg'] / 60
                fig_bar = px.bar(
                    thickness_summary, 
                    x='espesor_mm', 
                    y='duracion_min',
                    title='⏱️ Tiempo Promedio por Esquema según Espesor',
                    labels={'espesor_mm': 'Espesor (mm)', 'duracion_min': 'Tiempo Promedio (min)'},
                    color='duracion_min',
                    color_continuous_scale=[[0, COLORS['accent']], [1, COLORS['primary']]]
                )
                fig_bar.update_layout(
                    height=400, 
                    title_font_size=16, 
                    title_x=0.0, 
                    title_y=0.95,
                    coloraxis_showscale=False,
                    font=dict(family="Arial, sans-serif", size=12)
                )
                st.plotly_chart(fig_bar, use_container_width=True)
        
        # ==================== SECCIÓN 3: ANÁLISIS DE RELACIONES ====================
        st.markdown("---")
        st.subheader("🔍 Análisis de Relaciones Entre Indicadores")
        create_kpi_explanation(
            "Gráficos de Dispersión",
            "Estos gráficos muestran relaciones entre variables del proceso productivo. El primer gráfico relaciona las horas productivas diarias con la eficiencia (placas/hora), donde el tamaño de cada punto representa el total de placas procesadas. El segundo gráfico relaciona el número de esquemas ejecutados con las placas totales procesadas, donde el tamaño indica las horas productivas."
        )
        
        # Datos diarios para análisis
        daily_data = load_data(f"""
            WITH daily_analysis AS (
                SELECT 
                    fecha_proceso,
                    COUNT(*) as total_esquemas,
                    SUM(cantidad_placas) as total_placas,
                    AVG(duracion_segundos) as duracion_promedio_seg,
                    SUM(duracion_segundos) / 3600.0 as tiempo_productivo_horas
                FROM cortes_seccionadora
                WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                GROUP BY fecha_proceso
            )
            SELECT 
                *,
                total_placas / tiempo_productivo_horas as placas_por_hora
            FROM daily_analysis
            ORDER BY fecha_proceso
        """)
        
        if not daily_data.empty and len(daily_data) > 1:
            col1, col2 = st.columns(2)
            
            with col1:
                # Scatter plot tiempo vs eficiencia
                fig_scatter1 = px.scatter(
                    daily_data, 
                    x='tiempo_productivo_horas', 
                    y='placas_por_hora',
                    size='total_placas',
                    title='🔄 Tiempo Productivo vs Eficiencia',
                    labels={
                        'tiempo_productivo_horas': 'Horas Productivas', 
                        'placas_por_hora': 'Placas/Hora',
                        'total_placas': 'Total Placas'
                    },
                    color_discrete_sequence=[COLORS['primary']],
                    hover_data=['fecha_proceso', 'total_esquemas']
                )
                fig_scatter1.update_layout(
                    height=400,
                    title_font_size=16,
                    title_x=0.0,
                    title_y=0.95,
                    font=dict(family="Arial, sans-serif", size=12)
                )
                st.plotly_chart(fig_scatter1, use_container_width=True)
            
            with col2:
                # Scatter plot esquemas vs placas
                fig_scatter2 = px.scatter(
                    daily_data,
                    x='total_esquemas',
                    y='total_placas',
                    size='tiempo_productivo_horas',
                    title='📊 Esquemas vs Placas Procesadas',
                    labels={
                        'total_esquemas': 'Total Esquemas',
                        'total_placas': 'Total Placas',
                        'tiempo_productivo_horas': 'Horas Productivas'
                    },
                    color_discrete_sequence=[COLORS['secondary']],
                    hover_data=['fecha_proceso']
                )
                fig_scatter2.update_layout(
                    height=400,
                    title_font_size=16,
                    title_x=0.0,
                    title_y=0.95,
                    font=dict(family="Arial, sans-serif", size=12)
                )
                st.plotly_chart(fig_scatter2, use_container_width=True)
    else:
        st.warning("⚠️ No hay datos para el período seleccionado")

def show_thickness_analysis():
    st.header("⚡ Análisis por Espesores de Material")
    create_kpi_explanation(
        "Análisis por Espesores",
        "Comparación detallada del rendimiento de la máquina según el tipo de material procesado. Cada espesor tiene características diferentes que afectan los tiempos de corte y la eficiencia."
    )
    
    # Filtro de fechas en sidebar
    with st.sidebar:
        st.markdown("### 📅 Filtros de Fecha - Espesores")
        fecha_inicio_esp = st.date_input("Fecha inicio", value=datetime(2025, 7, 1), key="thickness_start")
        fecha_fin_esp = st.date_input("Fecha fin", value=datetime(2025, 8, 13), key="thickness_end")
        
        # Mostrar resumen del período
        dias_periodo = (fecha_fin_esp - fecha_inicio_esp).days + 1
        st.info(f"📊 Período: {dias_periodo} días")
    
    # Datos por espesor con métricas ampliadas y filtro de fecha
    thickness_data = load_data(f"""
        SELECT 
            espesor_mm,
            COUNT(*) as total_cortes,
            SUM(cantidad_placas) as total_placas,
            COUNT(DISTINCT job_key) as trabajos_unicos,
            AVG(duracion_segundos) as duracion_promedio_seg,
            SUM(duracion_segundos) as tiempo_total_seg,
            AVG(largo_mm * ancho_mm) as area_promedio_mm2,
            MIN(duracion_segundos) as duracion_min_seg,
            MAX(duracion_segundos) as duracion_max_seg,
            COUNT(DISTINCT fecha_proceso) as dias_procesados,
            AVG(largo_mm) as largo_promedio_mm,
            AVG(ancho_mm) as ancho_promedio_mm
        FROM cortes_seccionadora 
        WHERE fecha_proceso BETWEEN '{fecha_inicio_esp}' AND '{fecha_fin_esp}'
        GROUP BY espesor_mm 
        ORDER BY espesor_mm
    """)
    
    if not thickness_data.empty:
        # ==================== SECCIÓN 1: KPIs POR ESPESOR ====================
        st.subheader("📊 KPIs por Tipo de Material")
        
        # Primera fila de KPIs
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div style="background: linear-gradient(90deg, #1B4F72 0%, #2E86AB 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">📏 Tipos de Material</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Espesores diferentes</p>
            </div>
            """.format(len(thickness_data)), unsafe_allow_html=True)
        
        with col2:
            most_used = thickness_data.loc[thickness_data['total_placas'].idxmax(), 'espesor_mm']
            most_used_placas = thickness_data.loc[thickness_data['total_placas'].idxmax(), 'total_placas']
            st.markdown("""
            <div style="background: linear-gradient(90deg, #2E86AB 0%, #5DADE2 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">🏆 Material Principal</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{} mm</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">{:,} placas</p>
            </div>
            """.format(int(most_used), int(most_used_placas)), unsafe_allow_html=True)
        
        # ==================== SECCIÓN 2: ANÁLISIS COMPARATIVO ====================
        st.markdown("---")
        st.subheader("📊 Análisis Comparativo por Material")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_volume = px.bar(thickness_data, x='espesor_mm', y='total_placas',
                               title='📊 Total de Placas por Espesor',
                               labels={'espesor_mm': 'Espesor (mm)', 'total_placas': 'Total Placas'},
                               color='total_placas',
                               color_continuous_scale=[[0, COLORS['accent']], [1, COLORS['primary']]])
            fig_volume.update_layout(
                coloraxis_showscale=False,
                title_x=0.0,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12),
                xaxis=dict(tickmode='array', tickvals=thickness_data['espesor_mm'].tolist(), ticktext=[f'{int(x)} mm' for x in thickness_data['espesor_mm']])
            )
            st.plotly_chart(fig_volume, use_container_width=True)
        
        with col2:
            fig_efficiency = px.bar(thickness_data, x='espesor_mm', y='duracion_promedio_seg',
                                   title='⏱️ Duración Promedio por Espesor',
                                   labels={'espesor_mm': 'Espesor (mm)', 'duracion_promedio_seg': 'Segundos'},
                                   color='duracion_promedio_seg',
                                   color_continuous_scale=[[0, COLORS['info']], [1, COLORS['secondary']]])
            fig_efficiency.update_layout(
                coloraxis_showscale=False,
                title_x=0.0,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12),
                xaxis=dict(tickmode='array', tickvals=thickness_data['espesor_mm'].tolist(), ticktext=[f'{int(x)} mm' for x in thickness_data['espesor_mm']])
            )
            st.plotly_chart(fig_efficiency, use_container_width=True)
        
        # ==================== SECCIÓN 3: ANÁLISIS AVANZADO ====================
        st.subheader("🔍 Métricas Avanzadas por Material")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de eficiencia (placas por minuto)
            fig_placas_min = px.bar(thickness_data, x='espesor_mm', y='eficiencia_placas_min',
                                   title='🚀 Eficiencia: Placas por Minuto',
                                   labels={'espesor_mm': 'Espesor (mm)', 'eficiencia_placas_min': 'Placas/min'},
                                   color='eficiencia_placas_min',
                                   color_continuous_scale=[[0, COLORS['info']], [1, COLORS['primary']]])
            fig_placas_min.update_layout(
                coloraxis_showscale=False,
                title_x=0.0,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12),
                xaxis=dict(tickmode='array', tickvals=thickness_data['espesor_mm'].tolist(), ticktext=[f'{int(x)} mm' for x in thickness_data['espesor_mm']])
            )
            st.plotly_chart(fig_placas_min, use_container_width=True)
        
        with col2:
            # Gráfico de aprovechamiento (placas por corte)
            # Calcular métricas para gráficos
            thickness_data['placas_por_esquema'] = thickness_data['total_placas'] / thickness_data['total_cortes']
            
            fig_aprovechamiento = px.bar(thickness_data, x='espesor_mm', y='placas_por_esquema',
                                        title='📈 Aprovechamiento: Placas por Esquema',
                                        labels={'espesor_mm': 'Espesor (mm)', 'placas_por_esquema': 'Placas/Esquema'},
                                        color='placas_por_esquema',
                                        color_continuous_scale=[[0, COLORS['info']], [1, COLORS['primary']]])
            fig_aprovechamiento.update_layout(
                coloraxis_showscale=False,
                title_x=0.0,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12),
                xaxis=dict(tickmode='array', tickvals=thickness_data['espesor_mm'].tolist(), ticktext=[f'{int(x)} mm' for x in thickness_data['espesor_mm']])
            )
            st.plotly_chart(fig_aprovechamiento, use_container_width=True)
        
        # ==================== SECCIÓN 4: TABLA DETALLADA ====================
        st.subheader("📋 Detalle Completo por Material")
        
        # Preparar datos para la tabla
        display_data = thickness_data.copy()
        display_data['Espesor (mm)'] = display_data['espesor_mm'].astype(int)
        display_data['Total Placas'] = display_data['total_placas'].astype(int)
        display_data['Total Esquemas'] = display_data['total_cortes'].astype(int)
        display_data['Trabajos Únicos'] = display_data['trabajos_unicos'].astype(int)
        display_data['Tiempo Total (h)'] = (display_data['tiempo_total_seg'] / 3600).round(1)
        display_data['Duración Promedio (min)'] = (display_data['duracion_promedio_seg'] / 60).round(1)
        display_data['Placas/min'] = display_data['eficiencia_placas_min'].round(2)
        display_data['Placas/Esquema'] = (display_data['total_placas'] / display_data['total_cortes']).round(1)
        
        # Mostrar tabla
        st.dataframe(
            display_data[['Espesor (mm)', 'Total Placas', 'Total Esquemas', 'Trabajos Únicos', 
                         'Tiempo Total (h)', 'Duración Promedio (min)', 'Placas/min', 'Placas/Esquema']],
            use_container_width=True,
            hide_index=True
        )
        
    else:
        st.warning("No hay datos de espesores disponibles")

def show_jobs_analysis():
    st.header("🔧 Análisis por Trabajos")
    create_kpi_explanation(
        "Análisis por Trabajos",
        "Análisis detallado de cada tipo de trabajo procesado en la máquina. Cada 'trabajo' representa un diseño o tipo de corte específico que puede repetirse en múltiples esquemas."
    )
    
    # Filtro de fechas en sidebar
    with st.sidebar:
        st.markdown("### 📅 Filtros de Fecha - Trabajos")
        fecha_inicio_trabajos = st.date_input("Fecha inicio", value=datetime(2025, 7, 1), key="trabajos_start")
        fecha_fin_trabajos = st.date_input("Fecha fin", value=datetime(2025, 8, 13), key="trabajos_end")
        
        # Mostrar resumen del período
        dias_periodo_trabajos = (fecha_fin_trabajos - fecha_inicio_trabajos).days + 1
        st.info(f"📊 Período: {dias_periodo_trabajos} días")
    
    # ==================== SECCIÓN 1: KPIs GLOBALES DE TRABAJOS ====================
    st.subheader("📊 KPIs de Trabajos")
    
    # Consulta para métricas globales de trabajos con filtro de fecha
    global_trabajos_data = load_data(f"""
        WITH trabajo_metrics AS (
            SELECT 
                job_key,
                COUNT(*) as total_cortes,
                SUM(cantidad_placas) as total_placas,
                AVG(duracion_segundos) as duracion_promedio_seg,
                SUM(duracion_segundos) as tiempo_total_seg,
                MIN(fecha_proceso) as primera_fecha,
                MAX(fecha_proceso) as ultima_fecha,
                AVG(largo_mm * ancho_mm) as area_promedio_mm2,
                AVG(espesor_mm) as espesor_promedio
            FROM cortes_seccionadora 
            WHERE fecha_proceso BETWEEN '{fecha_inicio_trabajos}' AND '{fecha_fin_trabajos}'
            GROUP BY job_key
        )
        SELECT 
            COUNT(*) as total_trabajos_unicos,
            SUM(total_placas) as placas_totales,
            AVG(total_placas) as promedio_placas_por_trabajo,
            SUM(tiempo_total_seg) as tiempo_total_segundos,
            AVG(duracion_promedio_seg) as duracion_global_promedio,
            MAX(total_placas) as max_placas_trabajo,
            MIN(total_placas) as min_placas_trabajo,
            COUNT(CASE WHEN total_cortes = 1 THEN 1 END) as trabajos_ejecutados_una_vez,
            COUNT(CASE WHEN total_cortes > 10 THEN 1 END) as trabajos_frecuentes
        FROM trabajo_metrics
    """)
    
    if not global_trabajos_data.empty:
        metrics = global_trabajos_data.iloc[0]
        
        # KPI simplificado
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div style="background: linear-gradient(90deg, #1B4F72 0%, #2E86AB 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">🔧 Total Trabajos Únicos</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:,}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Diseños diferentes</p>
            </div>
            """.format(int(metrics['total_trabajos_unicos'])), unsafe_allow_html=True)
        
        with col2:
            eficiencia_global = metrics['placas_totales'] / (metrics['tiempo_total_segundos'] / 60) if metrics['tiempo_total_segundos'] > 0 else 0
            st.markdown("""
            <div style="background: linear-gradient(90deg, #85C1E9 0%, #5DADE2 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">🚀 Eficiencia Global</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">placas/min total</p>
            </div>
            """.format(eficiencia_global), unsafe_allow_html=True)
    
    # ==================== SECCIÓN 2: FILTROS Y CONFIGURACIÓN ====================
    st.markdown("---")
    st.subheader("🔍 Configuración de Análisis")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        top_n = st.selectbox("Mostrar top:", [10, 20, 50, 100], index=1, key="trabajos_top_n")
    with col2:
        sort_by = st.selectbox("Ordenar por:", 
                              ["Total Placas", "Total Esquemas", "Tiempo Total", "Duración Promedio", "Eficiencia"],
                              index=0, key="trabajos_sort")
    with col3:
        analisis_tipo = st.selectbox("Tipo de análisis:", 
                                   ["Todos los Trabajos", "Trabajos Frecuentes (>5 ejecuciones)", "Trabajos Únicos (1 ejecución)"],
                                   index=0, key="trabajos_filter")
    
    # Construir filtro adicional
    filtro_adicional = ""
    if analisis_tipo == "Trabajos Frecuentes (>5 ejecuciones)":
        filtro_adicional = "HAVING COUNT(*) > 5"
    elif analisis_tipo == "Trabajos Únicos (1 ejecución)":
        filtro_adicional = "HAVING COUNT(*) = 1"
    
    # Mapeo de opciones a columnas
    sort_mapping = {
        "Total Placas": "total_placas",
        "Total Esquemas": "total_cortes", 
        "Tiempo Total": "tiempo_total_seg",
        "Duración Promedio": "duracion_promedio_seg",
        "Eficiencia": "eficiencia_placas_min"
    }
    
    # ==================== SECCIÓN 3: DATOS DETALLADOS POR TRABAJO ====================
    trabajos_data = load_data(f"""
        SELECT 
            job_key,
            COUNT(*) as total_cortes,
            SUM(cantidad_placas) as total_placas,
            AVG(duracion_segundos) as duracion_promedio_seg,
            SUM(duracion_segundos) as tiempo_total_seg,
            MIN(fecha_proceso) as primera_fecha,
            MAX(fecha_proceso) as ultima_fecha,
            AVG(largo_mm) as largo_mm,
            AVG(ancho_mm) as ancho_mm,
            AVG(espesor_mm) as espesor_mm,
            MIN(duracion_segundos) as duracion_min_seg,
            MAX(duracion_segundos) as duracion_max_seg,
            SUM(cantidad_placas) / (SUM(duracion_segundos) / 60.0) as eficiencia_placas_min,
            AVG(largo_mm * ancho_mm * espesor_mm) as volumen_promedio_mm3
        FROM cortes_seccionadora 
        WHERE fecha_proceso BETWEEN '{fecha_inicio_trabajos}' AND '{fecha_fin_trabajos}'
        GROUP BY job_key 
        {filtro_adicional}
        ORDER BY {sort_mapping[sort_by]} DESC 
        LIMIT {top_n}
    """)
    
    if not trabajos_data.empty:
        # ==================== SECCIÓN 4: ANÁLISIS VISUAL ====================
        st.subheader(f"📈 Top {top_n} Trabajos - Análisis Visual")
        
        # Truncar nombres largos para mejor visualización - usar todos los datos obtenidos
        display_trabajos = trabajos_data.copy()
        display_trabajos['trabajo_key_short'] = display_trabajos['job_key'].str[-30:]
        display_trabajos['duracion_min'] = display_trabajos['duracion_promedio_seg'] / 60
        display_trabajos['tiempo_total_min'] = display_trabajos['tiempo_total_seg'] / 60
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Ordenar en orden descendente para gráfico
            display_trabajos_sorted = display_trabajos.sort_values('total_placas', ascending=True)  # ascending=True para que se vea descendente en horizontal
            
            fig_top_trabajos = px.bar(display_trabajos_sorted, 
                                 x='total_placas', 
                                 y='trabajo_key_short',
                                 orientation='h',
                                 title=f'📆 Top Trabajos por Total de Placas',
                                 labels={'total_placas': 'Total Placas', 'trabajo_key_short': 'Trabajo'},
                                 color='total_placas',
                                 color_continuous_scale=[[0, COLORS['accent']], [1, COLORS['primary']]])
            fig_top_trabajos.update_layout(
                height=600, 
                coloraxis_showscale=False,
                title_x=0.0,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12)
            )
            st.plotly_chart(fig_top_trabajos, use_container_width=True)
        
        with col2:
            # Ordenar por duración también
            display_trabajos_dur_sorted = display_trabajos.sort_values('duracion_min', ascending=True)
            
            fig_duration = px.bar(display_trabajos_dur_sorted, 
                                 x='duracion_min', 
                                 y='trabajo_key_short',
                                 orientation='h',
                                 title='⏱️ Duración Promedio por Corte (min)',
                                 labels={'duracion_min': 'Duración Promedio (min)', 'trabajo_key_short': 'Trabajo'},
                                 color='duracion_min',
                                 color_continuous_scale=[[0, COLORS['info']], [1, COLORS['secondary']]])
            fig_duration.update_layout(
                height=600, 
                coloraxis_showscale=False,
                title_x=0.0,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12)
            )
            st.plotly_chart(fig_duration, use_container_width=True)
        
        # ==================== SECCIÓN 5: ANÁLISIS DE EFICIENCIA Y PATRONES ====================
        st.subheader("🔍 Análisis de Eficiencia y Patrones")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de dispersión: total cortes vs eficiencia
            fig_scatter_efficiency = px.scatter(
                display_trabajos,
                x='total_cortes',
                y='eficiencia_placas_min',
                size='total_placas',
                title='🔄 Repeticiones vs Eficiencia',
                labels={
                    'total_cortes': 'Total de Ejecuciones',
                    'eficiencia_placas_min': 'Eficiencia (placas/min)',
                    'total_placas': 'Total Placas'
                },
                color_discrete_sequence=[COLORS['primary']],
                hover_data=['trabajo_key_short', 'duracion_min']
            )
            fig_scatter_efficiency.update_layout(
                height=400,
                title_x=0.0,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12)
            )
            st.plotly_chart(fig_scatter_efficiency, use_container_width=True)
        
        with col2:
            # Gráfico de eficiencia pura
            top_efficiency_trabajos = display_trabajos.nlargest(len(display_trabajos), 'eficiencia_placas_min').sort_values('eficiencia_placas_min', ascending=True)  # Para orden descendente visual
            fig_efficiency = px.bar(
                top_efficiency_trabajos,
                x='eficiencia_placas_min',
                y='trabajo_key_short',
                orientation='h',
                title='🚀 Trabajos Más Eficientes (placas/min)',
                labels={'eficiencia_placas_min': 'Placas por Minuto', 'trabajo_key_short': 'Trabajo'},
                color='eficiencia_placas_min',
                color_continuous_scale=[[0, COLORS['accent']], [1, COLORS['primary']]]
            )
            fig_efficiency.update_layout(
                height=400,
                coloraxis_showscale=False,
                title_x=0.0,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12)
            )
            st.plotly_chart(fig_efficiency, use_container_width=True)
        
        # ==================== SECCIÓN 6: TABLA DETALLADA CON TODAS LAS MÉTRICAS ====================
        st.subheader("📋 Tabla Detallada de Trabajos")
        
        # Preparar datos para la tabla
        table_data = trabajos_data.copy()
        table_data['Trabajo'] = table_data['job_key'].str[-40:]  # Mostrar últimos 40 caracteres
        table_data['Total Placas'] = table_data['total_placas'].astype(int)
        table_data['Ejecuciones'] = table_data['total_cortes'].astype(int)
        table_data['Tiempo Total (h)'] = (table_data['tiempo_total_seg'] / 3600).round(2)
        table_data['Duración Prom (min)'] = (table_data['duracion_promedio_seg'] / 60).round(1)
        table_data['Eficiencia (placas/min)'] = table_data['eficiencia_placas_min'].round(2)
        table_data['Material Prom (mm)'] = table_data['espesor_mm'].round(0).astype(int)
        table_data['Área Prom (cm²)'] = ((table_data['largo_mm'] * table_data['ancho_mm']) / 100).round(0).astype(int)
        table_data['Primera Ejecución'] = pd.to_datetime(table_data['primera_fecha']).dt.strftime('%d/%m/%Y')
        table_data['Última Ejecución'] = pd.to_datetime(table_data['ultima_fecha']).dt.strftime('%d/%m/%Y')
        
        # Mostrar tabla con paginación
        st.dataframe(
            table_data[['Trabajo', 'Total Placas', 'Ejecuciones', 'Tiempo Total (h)', 
                       'Duración Prom (min)', 'Eficiencia (placas/min)', 'Material Prom (mm)', 
                       'Área Prom (cm²)', 'Primera Ejecución', 'Última Ejecución']],
            use_container_width=True,
            hide_index=True
        )
        
        # ==================== SECCIÓN 7: RESUMEN ESTADÍSTICO ====================
        st.subheader("📊 Resumen Estadístico de los Trabajos Seleccionados")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Trabajos Analizados", f"{len(trabajos_data)}")
            st.metric("Placas Totales", f"{trabajos_data['total_placas'].sum():,}")
        
        with col2:
            st.metric("Tiempo Total", f"{(trabajos_data['tiempo_total_seg'].sum() / 3600):.1f}h")
            st.metric("Ejecuciones Totales", f"{trabajos_data['total_cortes'].sum():,}")
        
        with col3:
            st.metric("Duración Prom.", f"{(trabajos_data['duracion_promedio_seg'].mean() / 60):.1f} min")
            st.metric("Eficiencia Prom.", f"{trabajos_data['eficiencia_placas_min'].mean():.2f} placas/min")
        
        with col4:
            st.metric("Trabajo Más Repetido", f"{trabajos_data['total_cortes'].max()} veces")
            st.metric("Rango de Materiales", f"{int(trabajos_data['espesor_mm'].min())}-{int(trabajos_data['espesor_mm'].max())} mm")
    
    else:
        st.warning(f"No hay datos de trabajos disponibles para el filtro '{analisis_tipo}'")

# EJECUTAR EL DASHBOARD
main()