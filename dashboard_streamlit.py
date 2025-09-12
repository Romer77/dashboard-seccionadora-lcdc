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

# Paleta de colores corporativa LCDC
COLORS = {
    'primary': '#2E86AB',      # Azul corporativo
    'secondary': '#A23B72',    # Magenta corporativo  
    'accent': '#F18F01',       # Naranja vibrante
    'success': '#C73E1D',      # Rojo corporativo
    'info': '#85C1E9',         # Azul claro
    'warning': '#F7B801',      # Amarillo/dorado
    'light': '#F8F9FA',        # Gris muy claro
    'dark': '#2C3E50',         # Gris oscuro
}

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
        ["📈 Análisis de Producción", "⚡ Análisis por Espesores", "🔧 Análisis por Jobs"]
    )
    
    if page == "📈 Análisis de Producción":
        show_production_analysis()
    elif page == "⚡ Análisis por Espesores":
        show_thickness_analysis()
    elif page == "🔧 Análisis por Jobs":
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
            COUNT(DISTINCT job_key) as jobs_unicos,
            COUNT(DISTINCT fecha_proceso) as dias_activos,
            AVG(duracion_segundos) as duracion_promedio_seg,
            SUM(CASE WHEN espesor_mm = 18 THEN cantidad_placas ELSE 0 END) as placas_blancas_18mm
        FROM cortes_seccionadora
        WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
    """)
    
    # Mostrar mensaje si hay datos
    if not total_data.empty:
        st.success("✅ Datos cargados correctamente")
        st.info(f"Período: {fecha_inicio} a {fecha_fin}")
    else:
        st.warning("⚠️ No hay datos para el período seleccionado")

def show_thickness_analysis():
    st.header("⚡ Análisis por Espesores de Material")
    st.info("Función en desarrollo - próximamente disponible")

def show_jobs_analysis():
    st.header("🔧 Análisis por Jobs")
    st.info("Función en desarrollo - próximamente disponible")

# EJECUTAR EL DASHBOARD
main()