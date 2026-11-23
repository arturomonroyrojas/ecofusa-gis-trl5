"""
03_geoserver_publish_rest.py
Automatizacion de publicacion OGC (WMS / WFS / GeoJSON) en GeoServer 2.25 mediante REST API.
Crea workspace 'ecofusa', conecta el DataStore PostGIS y publica las capas vectoriales CTM12.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

GS_URL = os.getenv("GEOSERVER_URL", "http://localhost:8080/geoserver")
AUTH = (os.getenv("GEOSERVER_USER", "admin"), os.getenv("GEOSERVER_PASSWORD", "geoserver"))
WORKSPACE = os.getenv("GEOSERVER_WORKSPACE", "ecofusa")
STORE = "postgis_fusa"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def crear_workspace():
    r = requests.post(f"{GS_URL}/rest/workspaces", auth=AUTH, headers=HEADERS,
                      json={"workspace": {"name": WORKSPACE}}, timeout=15)
    print(f"[POST] Workspace '{WORKSPACE}' -> HTTP {r.status_code}")


def crear_datastore_postgis():
    payload = {
        "dataStore": {
            "name": STORE,
            "connectionParameters": {
                "entry": [
                    {"@key": "host", "$": "postgis"},
                    {"@key": "port", "$": "5432"},
                    {"@key": "database", "$": os.getenv("POSTGRES_DB", "ecofusa_gis")},
                    {"@key": "user", "$": os.getenv("POSTGRES_USER", "ecofusa_admin")},
                    {"@key": "passwd", "$": os.getenv("POSTGRES_PASSWORD", "EcoFusa_TRL5_Secure2026!")},
                    {"@key": "dbtype", "$": "postgis"},
                    {"@key": "Expose primary keys", "$": "true"},
                ]
            },
        }
    }
    r = requests.post(f"{GS_URL}/rest/workspaces/{WORKSPACE}/datastores",
                      auth=AUTH, headers=HEADERS, json=payload, timeout=15)
    print(f"[POST] DataStore '{STORE}' -> HTTP {r.status_code}")


def publicar_capa(tabla: str, titulo: str, srs: str = "EPSG:9377"):
    payload = {"featureType": {"name": tabla, "nativeName": tabla, "title": titulo, "srs": srs}}
    r = requests.post(
        f"{GS_URL}/rest/workspaces/{WORKSPACE}/datastores/{STORE}/featuretypes",
        auth=AUTH, headers=HEADERS, json=payload, timeout=15,
    )
    print(f"[POST] Capa '{WORKSPACE}:{tabla}' ({srs}) -> HTTP {r.status_code}")


def verificar_ogc():
    wfs = f"{GS_URL}/{WORKSPACE}/ows?service=WFS&version=1.0.0&request=GetCapabilities"
    wms = f"{GS_URL}/{WORKSPACE}/wms?service=WMS&version=1.1.1&request=GetCapabilities"
    for nombre, url in [("WMS", wms), ("WFS", wfs)]:
        r = requests.get(url, timeout=15)
        print(f"[GET] {nombre} GetCapabilities -> HTTP {r.status_code} ({r.elapsed.total_seconds()*1000:.0f} ms)")


if __name__ == "__main__":
    crear_workspace()
    crear_datastore_postgis()
    publicar_capa("rondas_hidricas", "Rondas Hidricas de Proteccion - Fusagasuga")
    publicar_capa("reportes_ambientales", "Reportes Ambientales Ciudadanos - EcoFusa")
    publicar_capa("predios_y_corredores", "Predios Municipales y Corredores Viales POT")
    verificar_ogc()
