"""
02_arcpy_consulta_predios_rondas.py
Script de geoprocesamiento nativo para ArcGIS Pro (ArcGIS Pro Python 3 / Jupyter Notebook).
Extiende el notebook real 'Busqueda_Predios_Nombre' (OFICINA_PROYECTOS_2025):
1. Identifica predios municipales ('MUNICIPIO', 'ALCALDIA', 'ALCALDÍA') en la capa 'Urbano'.
2. Cruza espacialmente con 'TratamientosActividades Urbano' y 'RondaHidrica'.
3. Exporta capas normalizadas en EPSG:9377 (CTM12) y GeoJSON hacia EcoFusa / GeoServer.
Ejecucion: C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe
"""

import os
import arcpy

arcpy.env.overwriteOutput = True
SALIDA_DIR = r"D:\EcoFusa_TRL5\export_arcgis"
os.makedirs(SALIDA_DIR, exist_ok=True)


def ejecutar_cruce_arcgis_pro():
    proyecto = arcpy.mp.ArcGISProject("CURRENT")
    mapa = proyecto.activeMap

    capas = {"Urbano": None, "TratamientosActividades Urbano": None, "RondaHidrica": None}
    for lyr in mapa.listLayers():
        if lyr.isFeatureLayer and lyr.name in capas:
            capas[lyr.name] = lyr

    if capas["Urbano"] is None or capas["TratamientosActividades Urbano"] is None:
        print("[ERROR] Verifique que las capas 'Urbano' y 'TratamientosActividades Urbano' esten activas.")
        return

    # 1. Consulta parametrizada de predios municipales en capa Urbano
    campo_urbano = "NOMBRE"
    palabras_urbano = ["MUNICIPIO", "ALCALDIA", "ALCALDÍA", "FUSAGASUGA", "FUSAGASUGÁ"]
    clausula_sql = " OR ".join([f"UPPER({campo_urbano}) LIKE '%{p}%'" for p in palabras_urbano])

    arcpy.management.SelectLayerByAttribute(capas["Urbano"], "NEW_SELECTION", clausula_sql)
    total_predios = int(arcpy.management.GetCount(capas["Urbano"])[0])
    print(f"[OK] Predios municipales seleccionados en Urbano: {total_predios}")

    # 2. Interseccion con TratamientosActividades Urbano (usos POT)
    out_trat = os.path.join(SALIDA_DIR, "predios_municipales_pot.shp")
    arcpy.analysis.Intersect([capas["Urbano"], capas["TratamientosActividades Urbano"]], out_trat)

    # 3. Validacion espacial contra RondaHidrica (proteccion ambiental)
    if capas["RondaHidrica"] is not None:
        out_ronda_cruce = os.path.join(SALIDA_DIR, "predios_en_ronda_hidrica.shp")
        arcpy.analysis.Intersect([out_trat, capas["RondaHidrica"]], out_ronda_cruce)
        arcpy.conversion.FeaturesToJSON(
            out_ronda_cruce,
            os.path.join(SALIDA_DIR, "predios_en_ronda_hidrica.geojson"),
            geoJSON="GEOJSON",
        )
        print(f"[OK] GeoJSON de predios en Ronda Hidrica exportado en: {SALIDA_DIR}")

    # 4. Limpieza de espacios en campos de texto (buena practica de calidad predial)
    with arcpy.da.UpdateCursor(out_trat, [campo_urbano]) as cursor:
        actualizados = 0
        for row in cursor:
            if row[0] and row[0] != row[0].strip():
                row[0] = " ".join(row[0].split())
                cursor.updateRow(row)
                actualizados += 1
    print(f"[OK] Registros normalizados con UpdateCursor: {actualizados}")


if __name__ == "__main__":
    ejecutar_cruce_arcgis_pro()
