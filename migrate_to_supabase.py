#!/usr/bin/env python3
"""
Script de migración de datos locales a Supabase
Migra la base de datos PostgreSQL local al proyecto Supabase
"""

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine
import sys
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración de bases de datos
LOCAL_DB_URL = "postgresql://postgres:margaritadh77@localhost:5432/seccionadora_logs"
SUPABASE_DB_URL = "postgresql://postgres:GGElm5EJPSKoyR1B@db.cyjracwepjzzeygfpbxr.supabase.co:5432/postgres"

def create_schema_supabase():
    """Crear el schema en Supabase"""
    try:
        engine = create_engine(SUPABASE_DB_URL)
        
        # Leer el archivo SQL de schema
        with open('init_database.sql', 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Ejecutar el script de schema
        with engine.connect() as conn:
            # Ejecutar línea por línea para evitar problemas con múltiples statements
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement and not statement.startswith('--'):
                    logger.info(f"Ejecutando: {statement[:50]}...")
                    try:
                        conn.execute(sa.text(statement))
                        conn.commit()
                    except Exception as e:
                        logger.warning(f"Error en statement (puede ser normal si ya existe): {e}")
        
        logger.info("✅ Schema creado exitosamente en Supabase")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando schema: {e}")
        return False

def migrate_data():
    """Migrar datos de local a Supabase"""
    try:
        # Conectar a ambas bases de datos
        local_engine = create_engine(LOCAL_DB_URL)
        supabase_engine = create_engine(SUPABASE_DB_URL)
        
        # Extraer datos de la tabla local
        logger.info("📤 Extrayendo datos de base local...")
        df = pd.read_sql_query("SELECT * FROM cortes_seccionadora ORDER BY id", local_engine)
        
        if df.empty:
            logger.warning("⚠️ No hay datos para migrar")
            return True
        
        logger.info(f"📊 Encontrados {len(df)} registros para migrar")
        
        # Limpiar la tabla en Supabase (opcional, para evitar duplicados)
        with supabase_engine.connect() as conn:
            conn.execute(sa.text("TRUNCATE TABLE cortes_seccionadora RESTART IDENTITY CASCADE"))
            conn.commit()
        
        # Insertar datos en Supabase
        logger.info("📥 Insertando datos en Supabase...")
        df.to_sql('cortes_seccionadora', supabase_engine, if_exists='append', index=False, method='multi')
        
        # Verificar la migración
        verification_df = pd.read_sql_query("SELECT COUNT(*) as count FROM cortes_seccionadora", supabase_engine)
        migrated_count = verification_df.iloc[0]['count']
        
        logger.info(f"✅ Migración completada: {migrated_count} registros migrados")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en migración de datos: {e}")
        return False

def test_connection():
    """Probar conexiones a ambas bases"""
    logger.info("🔧 Probando conexiones...")
    
    # Probar conexión local
    try:
        local_engine = create_engine(LOCAL_DB_URL)
        with local_engine.connect() as conn:
            result = conn.execute(sa.text("SELECT 1"))
            logger.info("✅ Conexión local OK")
    except Exception as e:
        logger.error(f"❌ Error conexión local: {e}")
        return False
    
    # Probar conexión Supabase
    try:
        supabase_engine = create_engine(SUPABASE_DB_URL)
        with supabase_engine.connect() as conn:
            result = conn.execute(sa.text("SELECT 1"))
            logger.info("✅ Conexión Supabase OK")
    except Exception as e:
        logger.error(f"❌ Error conexión Supabase: {e}")
        return False
    
    return True

def main():
    """Función principal de migración"""
    logger.info("🚀 Iniciando migración a Supabase...")
    
    # 1. Probar conexiones
    if not test_connection():
        logger.error("💥 Fallo en las conexiones. Abortando migración.")
        sys.exit(1)
    
    # 2. Crear schema en Supabase
    if not create_schema_supabase():
        logger.error("💥 Fallo creando schema. Abortando migración.")
        sys.exit(1)
    
    # 3. Migrar datos
    if not migrate_data():
        logger.error("💥 Fallo en migración de datos.")
        sys.exit(1)
    
    logger.info("🎉 ¡Migración completada exitosamente!")
    logger.info("🔗 Puedes verificar en: https://app.supabase.com/project/cyjracwepjzzeygfpbxr/editor")

if __name__ == "__main__":
    main()