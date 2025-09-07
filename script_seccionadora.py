# --- script_seccionadora.py ---
# Esta es nuestra "librería" o "caja de herramientas".
# Su única función es saber leer el log de la máquina.

import pandas as pd

import pandas as pd
import re

def procesar_archivo(filepath):
    """
    Lee un log y lo convierte en un DataFrame, extrayendo el 'job_key_preciso'.
    """
    datos = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            line = line.strip()
            if not line or '=' not in line:
                continue
            try:
                raw_content = line.split('=', 1)[1]
                for trash in ['.\\prg\\', 'C:\\WinCut\\prg\\', '.\\', 'C:WinCut\\prg\\']:
                    if raw_content.startswith(trash):
                        raw_content = raw_content[len(trash):]
                
                parts = raw_content.split(',')
                
                if len(parts) >= 17:
                    nombre_opt = parts[0].strip()
                    
                    # --- ¡NUEVA LÓGICA DE LLAVE PRECISA! ---
                    # Tomamos todo el string hasta el último punto.
                    # Ej: '..._W954ST1418.301' -> '..._W954ST1418'
                    job_key_preciso = nombre_opt.rsplit('.', 1)[0]
                    # --- FIN DE LA LÓGICA NUEVA ---

                    datos.append({
                        'nombre_optimizacion': nombre_opt,
                        'job_key': job_key_preciso, # <-- Usamos la nueva llave precisa
                        'fecha_proceso_str': f"{int(parts[8]):04d}-{int(parts[10]):02d}-{int(parts[9]):02d}",
                        'hora_inicio_str': f"{int(parts[5]):02d}:{int(parts[4]):02d}:{int(parts[7]):02d}",
                        'hora_fin_str': f"{int(parts[12]):02d}:{int(parts[11]):02d}:{int(parts[14]):02d}",
                        'largo_mm': float(parts[1]),
                        'ancho_mm': float(parts[2]),
                        'espesor_mm': float(parts[3]),
                        'cantidad_placas': int(parts[16])
                    })
            except (ValueError, IndexError):
                pass
                
    return pd.DataFrame(datos)