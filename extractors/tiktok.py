"""
extractors/tiktok.py
STUB. Aquí se integra el extractor de TikTok de tu compañero.
Debe respetar la misma firma que reddit.extraer(browser, criterio, ...)
y devolver registros creados con storage.normalizar(...).
"""

import storage

FUENTE = "tiktok"


async def extraer(browser, criterio, max_paginas=3):
    print(f"[{FUENTE}] (stub) pendiente de integrar el código del compañero")
    # Ejemplo de un registro con el esquema común:
    return [storage.normalizar(
        fuente=FUENTE,
        criterio=criterio,
        contenido="(ejemplo) comentario de TikTok sobre el terremoto",
        autor="usuario_demo",
        metricas={"likes": 0},
    )]
