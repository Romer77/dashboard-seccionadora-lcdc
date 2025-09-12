import streamlit as st
import sqlalchemy
from sqlalchemy import create_engine

def get_database_connection():
    """Obtiene URL de pooler IPv4-compatible"""
    try:
        # Usar pooler en lugar de conexión directa
        base_url = st.secrets["PG_CONN"]
        
        # Asegurar SSL
        if "sslmode" not in base_url:
            return base_url + "?sslmode=require"
        return base_url
        
    except Exception as e:
        st.error(f"Error obteniendo PG_CONN: {e}")
        return None

def create_db_engine():
    """Crea engine optimizado para pooler"""
    database_url = get_database_connection()
    
    if not database_url:
        return None
    
    try:
        engine = create_engine(
            database_url,
            # Configuración para pooler
            pool_pre_ping=True,
            pool_recycle=300,
            pool_timeout=20,
            max_overflow=0,
            pool_size=5,
            connect_args={"sslmode": "require"}
        )
        
        # Test de conexión
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT version()")).fetchone()
            st.success(f"✅ Conexión exitosa via pooler: PostgreSQL detectado")
        
        return engine
        
    except Exception as e:
        st.error(f"❌ Error conectando via pooler: {e}")
        return None

DATABASE_URL = get_database_connection()
ENGINE = create_db_engine() if DATABASE_URL else None