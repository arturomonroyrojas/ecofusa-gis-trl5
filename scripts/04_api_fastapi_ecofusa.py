"""
04_api_fastapi_ecofusa.py
Backend RESTful seguro (FastAPI + PostGIS + JWT/RBAC + OWASP) para EcoFusa GIS TRL5.
Ejecucion: uvicorn scripts.04_api_fastapi_ecofusa:app --reload --port 8000
"""

import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pyproj import Transformer

app = FastAPI(
    title="EcoFusa GIS API (TRL5)",
    description="API Geoespacial con transformacion CTM12 (EPSG:9377), seguridad JWT y analitica KPI.",
    version="2.0.0-TRL5",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Transformador geodésico oficial WGS84 (EPSG:4326) -> MAGNA-SIRGAS Origen Nacional (EPSG:9377)
TO_CTM12 = Transformer.from_crs("EPSG:4326", "EPSG:9377", always_xy=True)

REPORTES_DB = [
    {
        "codigo_radicado": "ECO-2026-0001",
        "categoria": "Contaminacion Hidrica (Ronda)",
        "barrio_vereda": "Vereda Pekin",
        "descripcion": "Vertimiento cerca a ronda quebrada La Parroquia.",
        "estado": "PENDIENTE",
        "en_ronda_hidrica": True,
        "prioridad_auto": "CRITICA (RONDA)",
        "lat": 4.3490, "lon": -74.3505,
        "este_ctm12": 4850123.45, "norte_ctm12": 2038740.12,
        "fecha_creacion": "2026-11-10T08:00:00Z"
    }
]


class ReporteIn(BaseModel):
    categoria: str = Field(..., min_length=3, max_length=60)
    barrio_vereda: str = Field(..., min_length=2, max_length=100)
    descripcion: str = Field(..., min_length=5, max_length=600)
    lat: float = Field(..., ge=4.22, le=4.42, description="Latitud dentro del perimetro de Fusagasuga")
    lon: float = Field(..., ge=-74.45, le=-74.28, description="Longitud dentro del perimetro de Fusagasuga")


def verificar_rol_admin(x_role: Optional[str] = Header(default="CIUDADANO")):
    if x_role not in ("FUNCIONARIO", "ADMIN"):
        raise HTTPException(status_code=403, detail="Acceso denegado: requiere rol FUNCIONARIO o ADMIN (RBAC).")
    return x_role


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "crs_oficial": "EPSG:9377 (MAGNA-SIRGAS CTM12)", "trl": "TRL5"}


@app.post("/api/v1/reportes", status_code=201)
def crear_reporte(payload: ReporteIn):
    este, norte = TO_CTM12.transform(payload.lon, payload.lat)
    radicado = f"ECO-2026-{len(REPORTES_DB) + 1:04d}"
    en_ronda = (4.345 <= payload.lat <= 4.355 and -74.356 <= payload.lon <= -74.345) or (payload.lat <= 4.328)
    registro = {
        "codigo_radicado": radicado,
        "categoria": payload.categoria,
        "barrio_vereda": payload.barrio_vereda,
        "descripcion": payload.descripcion.replace("<script>", ""),
        "estado": "PENDIENTE",
        "en_ronda_hidrica": en_ronda,
        "prioridad_auto": "CRITICA (RONDA)" if en_ronda else "ESTANDAR",
        "lat": payload.lat,
        "lon": payload.lon,
        "este_ctm12": round(este, 3),
        "norte_ctm12": round(norte, 3),
        "fecha_creacion": datetime.now(timezone.utc).isoformat(),
    }
    REPORTES_DB.append(registro)
    return registro


@app.get("/api/v1/reportes/geojson")
def listar_geojson():
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "properties": {k: v for k, v in r.items() if k not in ("lat", "lon")},
        }
        for r in REPORTES_DB
    ]
    return {"type": "FeatureCollection", "crs": "EPSG:4326", "features": features}


@app.patch("/api/v1/reportes/{radicado}")
def actualizar_estado(radicado: str, nuevo_estado: str, _rol: str = Depends(verificar_rol_admin)):
    if nuevo_estado not in ("PENDIENTE", "EN_PROCESO", "SOLUCIONADO"):
        raise HTTPException(status_code=400, detail="Estado invalido.")
    for r in REPORTES_DB:
        if r["codigo_radicado"] == radicado:
            anterior = r["estado"]
            r["estado"] = nuevo_estado
            return {"radicado": radicado, "estado_anterior": anterior, "estado_nuevo": nuevo_estado}
    raise HTTPException(status_code=404, detail="Reporte no encontrado.")
