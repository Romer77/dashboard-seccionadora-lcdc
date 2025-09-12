# Crear nuevo archivo: database.py
import streamlit as st
import sqlalchemy
from sqlalchemy import create_engine

def get_database_connection():
    """Usar IP directa para evitar DNS issues"""
    
    try:
        # Obtener string original
        original_url = st.secrets["PG_CONN"]
        
        # Reemplazar hostname por IP
        # db.cyjracwepjzzeygfpbxr.supabase.co → IP directa
        ip_url = original_url.replace(
            "db.cyjracwepjzzeygfpbxr.supabase.co",
            "54.220.195.48"  # IP de tu instancia Supabase
        )
        
        st.info(f"🔄 Usando IP directa para evitar DNS issues")
        return ip_url
    except Exception as e:
        st.error(f"Error accediendo a PG_CONN: {e}")
        return None

def create_db_engine():
    """Crea engine de SQLAlchemy"""
    database_url = get_database_connection()
    
    if not database_url:
        st.error("❌ No se pudo obtener DATABASE_URL")
        return None
    
    try:
        engine = create_engine(database_url)
        # Testear conexión
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        st.success("✅ Conexión a base de datos exitosa")
        return engine
    except Exception as e:
        st.error(f"❌ Error conectando a base de datos: {e}")
        return None

# Variables globales
DATABASE_URL = get_database_connection()
ENGINE = create_db_engine() if DATABASE_URL else None