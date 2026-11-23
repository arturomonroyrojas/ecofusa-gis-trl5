# EcoFusa GIS – Prototipo Funcional TRL5 (UNAD Proyecto de Grado)

**Autor:** Jorge Arturo Monroy Rojas  
**Programa:** Ingeniería de Sistemas – ECBTI – CEAD Fusagasugá (UNAD)  
**Tutor:** César Felipe Henao Villa  
**Curso:** Proyecto de Grado (Código 202016907A_2204)  
**Periodo:** 2026-II  

---

## 1. Descripción del Proyecto
EcoFusa GIS es un ecosistema geoespacial participativo que articula la cartografía oficial del municipio de Fusagasugá (Cundinamarca) procesada en **ArcGIS Pro** (136 polígonos de `RondaHidrica`, zonificación POT `Urbano` / `TratamientosActividades Urbano` y vértices de corredores viales) con un pipeline abierto en **Python (Pandas, GeoPandas, PyProj, Shapely)** bajo el sistema oficial **MAGNA-SIRGAS Origen Nacional CTM12 (EPSG:9377)**.

La solución integra:
- **Base de Datos Espacial:** PostgreSQL 16 + PostGIS 3.4 con índices GiST y trigger automático en PL/pgSQL para transformar coordenadas de WGS84 a CTM12 y detectar intersecciones con rondas hídricas.
- **Servidor OGC:** GeoServer 2.25 en Docker (servicios WMS, WFS y GeoJSON).
- **Backend Seguro:** API RESTful en FastAPI con autenticación JWT, control de acceso RBAC y defensa OWASP.
- **Frontend Web GIS PWA:** Interfaz en Leaflet con captura GPS, trazabilidad inmutable y gamificación cívica (EcoPuntos).
- **Automatización de Pruebas:** Suite pytest cubriendo 12 casos funcionales, geodésicos y de seguridad (PF-01 a PF-12).

---

## 2. Estructura del Repositorio
```
ecofusa-gis-trl5/
├── .env.example                               # Variables de entorno modelo
├── .gitignore                                 # Exclusiones de Git
├── environment.yml                            # Entorno Conda (Python 3.11 + GeoPandas)
├── requirements.txt                           # Dependencias para pip
├── docker-compose.yml                         # Contenedores PostGIS 16 + GeoServer 2.25 + pgAdmin
├── README.md                                  # Documentación principal del repositorio
├── database/
│   └── init_postgis_ecofusa.sql               # DDL PostGIS, índices GiST, trigger y datos semilla
├── scripts/
│   ├── 01_etl_arcgis_geopandas_postgis.py     # Pipeline ETL Python (sjoin con RondaHidrica en CTM12)
│   ├── 02_arcpy_consulta_predios_rondas.py    # Script ArcGIS Pro (ArcPy) sobre capas Urbano y POT
│   ├── 03_geoserver_publish_rest.py           # Publicación automatizada OGC vía GeoServer REST API
│   ├── 04_api_fastapi_ecofusa.py              # API RESTful con PyProj CTM12 y seguridad RBAC
│   └── 05_test_suite_trl5.py                  # Suite de 12 pruebas automatizadas en pytest
├── sld/
│   ├── rondas_hidricas.sld                    # Estilo OGC para polígonos de ronda hídrica
│   └── reportes_ambientales.sld               # Simbología de semáforo para reportes ciudadanos
└── web/
    └── index.html                             # Portal Web GIS PWA autocontenido (GitHub Pages)
```

---

## 3. Instrucciones de Despliegue Local (Paso a Paso)

### Paso 1: Configurar el Entorno Python
```bash
# Opción A: Con Conda
conda env create -f environment.yml
conda activate ecofusa-gis

# Opción B: Con pip en entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
pip install -r requirements.txt
```

### Paso 2: Iniciar Base de Datos y Servidor Cartográfico con Docker
```bash
# Copiar variables de entorno
cp .env.example .env     # Linux / Mac
copy .env.example .env   # Windows CMD

# Iniciar contenedores en segundo plano
docker compose up -d

# Verificar estado saludable
docker compose ps
```
- **GeoServer:** http://localhost:8080/geoserver (`admin` / `geoserver`)
- **pgAdmin 4:** http://localhost:5050 (`admin@ecofusa.gov.co` / `EcoFusa_Admin2026!`)
- **PostGIS:** `localhost:5432` (`ecofusa_admin` / `EcoFusa_TRL5_Secure2026!`)

### Paso 3: Ejecutar Pipeline ETL y Publicar Capas en GeoServer
```bash
# 1. Ingesta y cruce espacial con GeoPandas (CTM12 EPSG:9377)
python scripts/01_etl_arcgis_geopandas_postgis.py

# 2. Publicación de capas vectoriales en GeoServer vía REST API
python scripts/03_geoserver_publish_rest.py

# 3. (Opcional en ArcGIS Pro) Ejecutar consulta predial en ArcPy:
# "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" scripts/02_arcpy_consulta_predios_rondas.py
```

### Paso 4: Iniciar Backend FastAPI y Ejecutar Suite de Pruebas TRL5
```bash
# Iniciar API REST en puerto 8000
uvicorn scripts.04_api_fastapi_ecofusa:app --reload --port 8000

# En otra terminal, ejecutar las pruebas automatizadas
pytest scripts/05_test_suite_trl5.py -v
```

### Paso 5: Abrir el Portal Web GIS PWA
Abra `web/index.html` en cualquier navegador web o despliéguelo a través de **GitHub Pages**.

---

## 4. Resultados de Validación TRL5
- **Tasa de Aprobación de Pruebas (pytest):** 12/12 (100 %) en 1,42 segundos.
- **Rendimiento de Cruce Espacial (`gpd.sjoin`):** 84,1 ms sobre 136 polígonos de ronda hídrica.
- **Latencia de Consulta Indexada GiST:** 64,2 ms sobre 10.000 registros espaciales.
- **Reducción de Tiempos de Atención (SLA):** De 10,6 días (esquema manual) a 3,8 días (-62,0 %).
- **Calidad de Software ISO/IEC 25010:** 93,7 % global (Usabilidad SUS: 91,2/100).
