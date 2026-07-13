"""
extractors/instagram.py
STUB. Aquí se integra el extractor de Instagram de tu compañero.
Misma firma y mismo esquema (storage.normalizar).
"""

import storage

FUENTE = "instagram"


async def extraer(browser, criterio, max_paginas=3):
    print(f"[{FUENTE}] (stub) pendiente de integrar el código del compañero")
    return [storage.normalizar(
        fuente=FUENTE,
        criterio=criterio,
        contenido="(ejemplo) comentario de Instagram sobre el terremoto",
        autor="usuario_demo",
        metricas={"likes": 0},
    )]
