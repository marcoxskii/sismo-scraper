"""
main.py  -  Orquestador de extracción PARALELA.

Requerimiento de la práctica: iniciar la extracción desde las tres fuentes
AL MISMO TIEMPO. Se usa asyncio + Playwright async:

  - Se abre UN solo navegador Chromium (ahorro de RAM -> 8 GB).
  - Cada extractor crea su propio browser_context aislado.
  - asyncio.gather() lanza los tres extractores simultáneamente.

Justificación: la extracción es I/O-bound (esperas de red/carga de página),
por lo que la concurrencia cooperativa da paralelismo real de espera sin
gastar CPU ni memoria extra. Es la técnica adecuada frente a hilos o
procesos para este equipo.
"""

import asyncio
import time

from playwright.async_api import async_playwright

import storage
from extractors import reddit, tiktok, instagram

# Criterio de búsqueda ligado a la problemática:
# "Reacciones y percepción ciudadana sobre el terremoto en Venezuela"
CRITERIO = "Venezuela terremoto"

# Las tres fuentes de la práctica (tu parte + parte del compañero):
EXTRACTORES = [reddit, tiktok, instagram]


async def main():
    inicio = time.perf_counter()
    todos = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # >>> Aquí ocurre el paralelismo: las 3 tareas arrancan a la vez <<<
        tareas = [ext.extraer(browser, CRITERIO) for ext in EXTRACTORES]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)

        await browser.close()

    # Consolidar resultados y guardar por fuente
    for ext, res in zip(EXTRACTORES, resultados):
        if isinstance(res, Exception):
            print(f"[ERROR] {ext.FUENTE}: {res}")
            continue
        storage.guardar_por_fuente(ext.FUENTE, res)
        todos.extend(res)

    ruta_json, ruta_csv = storage.guardar_unificado(todos)

    dur = time.perf_counter() - inicio
    print("\n===== RESUMEN =====")
    print(f"Registros totales : {len(todos)}")
    print(f"Tiempo (paralelo) : {dur:.2f} s")
    print(f"JSON unificado    : {ruta_json}")
    print(f"CSV unificado     : {ruta_csv}")


if __name__ == "__main__":
    asyncio.run(main())
