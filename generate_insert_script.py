#!/usr/bin/env python3
"""
Generador de script SQL INSERT para migración a Supabase
Extrae datos de la base local y genera un script SQL con inserts
"""

import sys
import os
sys.path.append(os.getcwd())

from config import config
import pandas as pd
from sqlalchemy import create_engine
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_insert_script():
    """Generar script SQL con INSERT statements"""
    try:
        # Conectar a base local usando config.py
        local_url = "postgresql://postgres:margaritadh77@localhost:5432/seccionadora_logs"
        engine = create_engine(local_url)
        
        logger.info("📤 Extrayendo datos de base local...")
        
        # Extraer todos los datos (excluyendo columnas calculadas)
        query = """
        SELECT 
            nombre_optimizacion,
            job_key,
            fecha_proceso,
            hora_inicio,
            hora_fin,
            largo_mm,
            ancho_mm,
            espesor_mm,
            cantidad_placas,
            fecha_carga
        FROM cortes_seccionadora 
        ORDER BY id
        """
        
        df = pd.read_sql_query(query, engine)
        
        if df.empty:
            logger.warning("⚠️ No hay datos para exportar")
            return False
        
        logger.info(f"📊 Encontrados {len(df)} registros para exportar")
        
        # Generar script SQL
        sql_script = []
        sql_script.append("-- Script de migración de datos a Supabase")
        sql_script.append("-- Generado automáticamente")
        sql_script.append("-- Total de registros: {}".format(len(df)))
        sql_script.append("")
        sql_script.append("-- Limpiar tabla existente (opcional)")
        sql_script.append("-- TRUNCATE TABLE cortes_seccionadora RESTART IDENTITY;")
        sql_script.append("")
        sql_script.append("-- Insertar datos")
        
        # Procesar en lotes de 100 registros para evitar queries muy largas
        batch_size = 100
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            sql_script.append(f"-- Lote {i//batch_size + 1}")
            sql_script.append("INSERT INTO cortes_seccionadora (")
            sql_script.append("    nombre_optimizacion, job_key, fecha_proceso, hora_inicio, hora_fin,")
            sql_script.append("    largo_mm, ancho_mm, espesor_mm, cantidad_placas, fecha_carga")
            sql_script.append(") VALUES")
            
            values_list = []
            for _, row in batch.iterrows():
                # Escapar strings y formatear valores
                nombre_opt = row['nombre_optimizacion'].replace("'", "''") if pd.notna(row['nombre_optimizacion']) else ''
                job_key = row['job_key'].replace("'", "''") if pd.notna(row['job_key']) else ''
                
                values = f"('{nombre_opt}', '{job_key}', '{row['fecha_proceso']}', '{row['hora_inicio']}', '{row['hora_fin']}', {row['largo_mm']}, {row['ancho_mm']}, {row['espesor_mm']}, {row['cantidad_placas']}, '{row['fecha_carga']}')"
                values_list.append(values)
            
            sql_script.append(",\n".join(values_list))
            sql_script.append(";")
            sql_script.append("")
        
        # Escribir script a archivo
        script_content = "\n".join(sql_script)
        
        with open('supabase_data_insert.sql', 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        logger.info("✅ Script SQL generado: supabase_data_insert.sql")
        logger.info(f"📏 Tamaño del script: {len(script_content):,} caracteres")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error generando script: {e}")
        return False

def main():
    """Función principal"""
    logger.info("🚀 Generando script SQL de migración...")
    
    if generate_insert_script():
        logger.info("🎉 Script generado exitosamente!")
        logger.info("📝 Próximo paso: Ejecutar 'supabase_data_insert.sql' en Supabase SQL Editor")
    else:
        logger.error("💥 Error generando script")
        sys.exit(1)

if __name__ == "__main__":
    main()