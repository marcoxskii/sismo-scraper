"""
storage.py
Normaliza cada registro a un esquema común (trazabilidad exigida por la
práctica) y lo guarda en JSON y CSV. Se generan:
  - data/dataset_unificado.json / .csv  -> todas las fuentes juntas
  - data/<fuente>.json                  -> una salida por red social
"""

import csv
import json
import os
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Esquema común: cada extractor debe producir registros con estas claves.
CAMPOS = [
    "fuente",             # de qué red proviene   (trazabilidad)
    "criterio_busqueda",  # query / hashtag usado (trazabilidad)
    "contenido",          # texto obtenido        (trazabilidad)
    "autor",
    "fecha_publicacion",
    "url",
    "metricas",           # dict: likes, comentarios, etc.
    "extraido_en",
]


def normalizar(fuente, criterio, contenido, autor=None,
               fecha_publicacion=None, url=None, metricas=None):
    """Devuelve un registro con el esquema común y timestamp de extracción."""
    return {
        "fuente": fuente,
        "criterio_busqueda": criterio,
        "contenido": (contenido or "").strip(),
        "autor": autor,
        "fecha_publicacion": fecha_publicacion,
        "url": url,
        "metricas": metricas or {},
        "extraido_en": datetime.now(timezone.utc).isoformat(),
    }


def _asegurar_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def guardar_por_fuente(fuente, registros):
    """Guarda los registros de una sola fuente en data/<fuente>.json"""
    _asegurar_dir()
    ruta = os.path.join(DATA_DIR, f"{fuente}.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)
    return ruta


def guardar_unificado(registros):
    """Guarda todos los registros juntos en JSON y CSV."""
    _asegurar_dir()

    ruta_json = os.path.join(DATA_DIR, "dataset_unificado.json")
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)

    ruta_csv = os.path.join(DATA_DIR, "dataset_unificado.csv")
    with open(ruta_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        writer.writeheader()
        for r in registros:
            fila = dict(r)
            # las métricas (dict) se serializan como texto JSON para el CSV
            fila["metricas"] = json.dumps(r.get("metricas", {}), ensure_ascii=False)
            writer.writerow(fila)

    return ruta_json, ruta_csv
