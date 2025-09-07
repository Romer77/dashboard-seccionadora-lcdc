import os
import pandas as pd
import shutil
import requests
import sys
import traceback
import re
from datetime import date, timedelta, datetime
from sqlalchemy import create_engine, text
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from script_seccionadora import procesar_archivo

# Cargar variables de entorno
load_dotenv()
PG_CONN = os.getenv('PG_CONN')

def main():
    """Función principal que orquesta todo el proceso."""
    engine = create_engine(PG_CONN)
    try:
        # 2. PROCESAR ARCHIVOS DE LOG
        ENTRADA_FOLDER = 'archivos_entrada'
        PROCESADOS_FOLDER = 'procesados'
        archivos = [f for f in os.listdir(ENTRADA_FOLDER) if os.path.isfile(os.path.join(ENTRADA_FOLDER, f))]

        if not archivos:
            print("⚠️ No se encontraron nuevos logs para procesar.")
            return

        df_total = pd.concat([procesar_archivo(os.path.join(ENTRADA_FOLDER, f)) for f in archivos], ignore_index=True)

        if df_total.empty:
            print("ℹ️ Los archivos de log no contenían datos válidos.")
            return

        print(f"⚙️  Se han procesado {len(df_total)} registros de los logs.")

        # 3. TRANSFORMAR DATOS PARA POSTGRESQL
        df_total['fecha_proceso'] = pd.to_datetime(df_total['fecha_proceso_str']).dt.date
        df_total['hora_inicio'] = pd.to_datetime(df_total['hora_inicio_str']).dt.time
        df_total['hora_fin'] = pd.to_datetime(df_total['hora_fin_str']).dt.time
        
        # Seleccionar solo las columnas necesarias para la DB
        df_final = df_total[[
            'nombre_optimizacion', 'job_key', 'fecha_proceso', 
            'hora_inicio', 'hora_fin', 'largo_mm', 'ancho_mm', 
            'espesor_mm', 'cantidad_placas'
        ]]

        # 4. CARGAR A POSTGRESQL
        print("📤 Cargando datos a PostgreSQL...")
        rows_inserted = df_final.to_sql(
            'cortes_seccionadora', 
            engine, 
            if_exists='append', 
            index=False,
            method='multi'
        )
        print(f"✅ Se insertaron {rows_inserted} registros en la base de datos.")

        # 5. MOVER ARCHIVOS PROCESADOS
        os.makedirs(PROCESADOS_FOLDER, exist_ok=True)
        for archivo in archivos:
            origen = os.path.join(ENTRADA_FOLDER, archivo)
            destino = os.path.join(PROCESADOS_FOLDER, f"{archivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            shutil.move(origen, destino)
            print(f"📁 Movido: {archivo} -> {destino}")

        print("🎉 ETL completado exitosamente!")

    except Exception as e:
        print(f"❌ Error en el proceso ETL: {str(e)}")
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    main()