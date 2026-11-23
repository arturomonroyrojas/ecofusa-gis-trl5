"""
01_etl_arcgis_geopandas_postgis.py
Pipeline ETL Geoespacial EcoFusa TRL5 (Python + Pandas + GeoPandas + PyProj + PostGIS).
Procesa capas exportadas desde ArcGIS Pro (RondaHidrica, via vertices) y reportes ciudadanos,
reproyecta WGS84 (EPSG:4326) <-> MAGNA-SIRGAS Origen Nacional CTM12 (EPSG:9377),
ejecuta cruce espacial (Spatial Join) y carga resultados a PostgreSQL/PostGIS y GeoJSON.
"""

import os
import time
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
OUT_DIR = Path("web/data")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def cargar_vertices_viales() -> gpd.GeoDataFrame:
    """Vertices reales de control de corredores viales en Fusagasuga (via vertices)."""
    tramos_df = pd.DataFrame([
        {"id": 1, "name": "TRAMO 1", "remarks": "INICIO", "lat": 4.291352, "lon": -74.388618},
        {"id": 2, "name": "TRAMO 1", "remarks": "FIN",    "lat": 4.289290, "lon": -74.386617},
        {"id": 3, "name": "TRAMO 2", "remarks": "INICIO", "lat": 4.288232, "lon": -74.385932},
        {"id": 4, "name": "TRAMO 2", "remarks": "FIN",    "lat": 4.285907, "lon": -74.381692},
        {"id": 5, "name": "TRAMO 3", "remarks": "INICIO", "lat": 4.285760, "lon": -74.381732},
        {"id": 6, "name": "TRAMO 3", "remarks": "FIN",    "lat": 4.280953, "lon": -74.383095},
        {"id": 7, "name": "TRAMO 4", "remarks": "INICIO", "lat": 4.277495, "lon": -74.383658},
        {"id": 8, "name": "TRAMO 4", "remarks": "FIN",    "lat": 4.277375, "lon": -74.383093},
        {"id": 9, "name": "TRAMO 5", "remarks": "INICIO", "lat": 4.277357, "lon": -74.382772},
    ])
    gdf = gpd.GeoDataFrame(
        tramos_df,
        geometry=gpd.points_from_xy(tramos_df["lon"], tramos_df["lat"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:9377")
    gdf["este_ctm12"] = gdf.geometry.x.round(3)
    gdf["norte_ctm12"] = gdf.geometry.y.round(3)
    return gdf


def cargar_rondas_hidricas(ruta_shp: str = "data/RondaHidrica.shp") -> gpd.GeoDataFrame:
    """Carga el shapefile oficial de ArcGIS Pro o genera poligonos de validacion CTM12."""
    if Path(ruta_shp).exists():
        print(f"[INFO] Leyendo capa oficial ArcGIS Pro: {ruta_shp}")
        return gpd.read_file(ruta_shp).to_crs("EPSG:9377")

    print("[INFO] Shapefile local no encontrado; generando capa de validacion TRL5 en EPSG:9377...")
    rondas_ref = [
        ("Ronda Hidrica Quebrada La Parroquia", 4.3485, -74.3510, 4.0945),
        ("Ronda Hidrica Rio Cuja Sector Sur",   4.3248, -74.3692, 9.7554),
        ("Ronda Hidrica Quebrada Sabaneta",     4.3372, -74.3645, 2.9764),
        ("Ronda Hidrica Sector Via Tramo 1-2",  4.2888, -74.3860, 2.5112),
        ("Ronda Hidrica Quebrajacho Norte",     4.3470, -74.3665, 6.5669),
    ]
    pts = gpd.GeoDataFrame(
        [{"Nombre": r[0], "Clasificac": "Suelo Rural", "Categoria1": "Proteccion", "AreaHas": r[3]} for r in rondas_ref],
        geometry=[Point(r[2], r[1]) for r in rondas_ref],
        crs="EPSG:4326",
    ).to_crs("EPSG:9377")
    pts["geometry"] = pts.geometry.buffer(320)
    return pts


def ejecutar_pipeline_etl(cargar_postgis: bool = False):
    t0 = time.perf_counter()
    vertices = cargar_vertices_viales()
    rondas = cargar_rondas_hidricas()

    # Ingesta de reportes ciudadanos de validacion TRL5 (Fusagasuga)
    np.random.seed(2026)
    categorias = ["Residuos Solidos", "Contaminacion Hidrica", "Quema / Humo", "Zonas Verdes", "Escombros"]
    anclas = [(4.3485, -74.3510), (4.3248, -74.3692), (4.3372, -74.3645),
              (4.2888, -74.3860), (4.3470, -74.3665), (4.3315, -74.3550)]
    registros = []
    for idx in range(1, 79):
        lat0, lon0 = anclas[idx % len(anclas)]
        registros.append({
            "codigo_radicado": f"ECO-2026-{idx:04d}",
            "categoria": categorias[idx % len(categorias)],
            "lat": round(lat0 + np.random.normal(0, 0.0024), 6),
            "lon": round(lon0 + np.random.normal(0, 0.0024), 6),
            "estado": np.random.choice(["SOLUCIONADO", "EN_PROCESO", "PENDIENTE"], p=[0.70, 0.19, 0.11]),
        })
    df_rep = pd.DataFrame(registros)
    gdf_rep_ctm12 = gpd.GeoDataFrame(
        df_rep,
        geometry=gpd.points_from_xy(df_rep["lon"], df_rep["lat"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:9377")

    # Cruce espacial (Spatial Join) en coordenadas metricas oficiales CTM12
    cruce = gpd.sjoin(gdf_rep_ctm12, rondas[["Nombre", "Categoria1", "geometry"]], how="left", predicate="intersects")
    cruce["en_ronda_hidrica"] = cruce["Nombre"].notna()
    cruce["prioridad_auto"] = np.where(cruce["en_ronda_hidrica"], "CRITICA (RONDA)", "ESTANDAR")
    cruce["este_ctm12"] = cruce.geometry.x.round(2)
    cruce["norte_ctm12"] = cruce.geometry.y.round(2)

    # Exportar GeoJSON listo para Leaflet / Web GIS (WGS84)
    cruce.to_crs("EPSG:4326").to_file(OUT_DIR / "reportes_ecofusa.geojson", driver="GeoJSON")
    rondas.to_crs("EPSG:4326").to_file(OUT_DIR / "rondas_hidricas.geojson", driver="GeoJSON")
    vertices.to_crs("EPSG:4326").to_file(OUT_DIR / "via_vertices.geojson", driver="GeoJSON")

    # Carga opcional directa a PostGIS cuando Docker esta activo
    if cargar_postgis and os.getenv("POSTGIS_URI"):
        engine = create_engine(os.getenv("POSTGIS_URI"))
        cruce.drop(columns=["index_right"], errors="ignore").to_postgis(
            "reportes_etl_ctm12", engine, if_exists="replace", index=False
        )
        rondas.to_postgis("rondas_hidricas_etl", engine, if_exists="replace", index=False)
        print("[OK] Capas cargadas en PostgreSQL + PostGIS (EPSG:9377)")

    ms = (time.perf_counter() - t0) * 1000
    print(f"[OK] ETL finalizado en {ms:.1f} ms | Reportes: {len(cruce)} | Criticos en Ronda: {int(cruce['en_ronda_hidrica'].sum())}")
    print(cruce.groupby(["categoria", "prioridad_auto"])["codigo_radicado"].count())


if __name__ == "__main__":
    ejecutar_pipeline_etl(cargar_postgis=bool(os.getenv("POSTGIS_URI")))
