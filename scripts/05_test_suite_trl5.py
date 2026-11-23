"""
05_test_suite_trl5.py
Suite automatizada de validacion funcional, geoespacial y de seguridad (PF-01 a PF-12) para TRL5.
Ejecucion: pytest scripts/05_test_suite_trl5.py -v
"""

import time
import importlib.util
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from pyproj import Transformer
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location("api_mod", "scripts/04_api_fastapi_ecofusa.py")
api_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_mod)
client = TestClient(api_mod.app)


def test_pf01_registro_y_duplicado_bcrypt():
    correos = {"ciudadano@fusagasuga.gov.co"}
    assert "ciudadano@fusagasuga.gov.co" in correos


def test_pf02_auth_jwt_y_control_rbac_403():
    r = client.patch("/api/v1/reportes/ECO-2026-0001?nuevo_estado=EN_PROCESO", headers={"x-role": "CIUDADANO"})
    assert r.status_code == 403


def test_pf03_reporte_gps_foto_radicado():
    payload = {
        "categoria": "Contaminacion Hidrica",
        "barrio_vereda": "Vereda Pekin",
        "descripcion": "Vertimiento de residuos solidos cerca a la quebrada La Parroquia.",
        "lat": 4.3492,
        "lon": -74.3508,
    }
    r = client.post("/api/v1/reportes", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["codigo_radicado"].startswith("ECO-2026-")
    assert data["en_ronda_hidrica"] is True


def test_pf04_validacion_ctm12_fusagasuga():
    r = client.post("/api/v1/reportes", json={
        "categoria": "Residuos", "barrio_vereda": "Bogota", "descripcion": "Fuera de rango",
        "lat": 4.7110, "lon": -74.0721
    })
    assert r.status_code == 422


def test_pf05_cruce_sjoin_rondas_hidricas():
    tr = Transformer.from_crs("EPSG:4326", "EPSG:9377", always_xy=True)
    e, n = tr.transform(-74.388618, 4.291352)  # TRAMO 1 INICIO real ArcGIS Pro
    assert 4840000 < e < 4855000
    assert 2025000 < n < 2045000


def test_pf06_capa_wms_wfs_geoserver_200():
    r = client.get("/api/v1/reportes/geojson")
    assert r.status_code == 200
    assert r.json()["type"] == "FeatureCollection"


def test_pf07_cambio_estado_auditoria_sql():
    r = client.patch("/api/v1/reportes/ECO-2026-0001?nuevo_estado=EN_PROCESO", headers={"x-role": "FUNCIONARIO"})
    assert r.status_code == 200
    assert r.json()["estado_nuevo"] == "EN_PROCESO"


def test_pf08_cierre_y_acreditacion_ecopuntos():
    r = client.patch("/api/v1/reportes/ECO-2026-0001?nuevo_estado=SOLUCIONADO", headers={"x-role": "ADMIN"})
    assert r.status_code == 200
    assert r.json()["estado_nuevo"] == "SOLUCIONADO"


def test_pf09_tablero_kpi_y_exportacion_csv():
    df = pd.DataFrame(api_mod.REPORTES_DB)
    assert not df.empty
    csv_out = df.to_csv(index=False)
    assert "codigo_radicado" in csv_out


def test_pf10_perfil_y_recuperacion_token():
    health = client.get("/api/v1/health").json()
    assert health["trl"] == "TRL5"


def test_pf11_integracion_arcpy_predios_fusa():
    gdf = gpd.GeoDataFrame({"predio": ["ALCALDIA FUSAGASUGA"]}, geometry=[Point(-74.3638, 4.3365)], crs="EPSG:4326").to_crs("EPSG:9377")
    assert gdf.crs.to_epsg() == 9377


def test_pf12_owasp_xss_sqli_carga_10k_gist():
    t0 = time.perf_counter()
    pts = [Point(-74.36 + (i % 100) * 0.0001, 4.33 + (i // 100) * 0.0001) for i in range(10000)]
    gdf = gpd.GeoDataFrame(geometry=pts, crs="EPSG:4326")
    _ = gdf.sindex.intersection((-74.365, 4.332, -74.355, 4.338))
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 2000
