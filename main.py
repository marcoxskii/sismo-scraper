"""
main.py  -  Orquestador de extracción CONCURRENTE sobre Reddit.

Requerimiento de la práctica: evidenciar ejecución concurrente. Aquí se
lanzan varios FRENTES de extracción (grupos de consultas) AL MISMO TIEMPO
con asyncio.gather(); cada frente corre en su propio browser_context
aislado, sobre un único navegador Chromium.

Justificación: la extracción es I/O-bound (esperas de red / carga de
página). asyncio con gather() da paralelismo real de espera sin gastar CPU
y con mínimo consumo de RAM (un solo proceso Chromium), decisión adecuada
para un equipo de 8 GB. Frente a hilos o procesos, evita abrir varios
navegadores.
"""

import asyncio
import time

from playwright.async_api import async_playwright

import storage
from extractors import reddit

# Cada frente es un conjunto de consultas ligadas al MISMO evento (el sismo).
# Los tres frentes se ejecutan concurrentemente.
FRENTES = {
    "espanol":   ["sismo Venezuela", "terremoto Venezuela"],
    "ingles":    ["Venezuela earthquake", "Venezuela quake"],
    "afectados": ["terremoto Venezuela muertos", "terremoto Venezuela rescate"],
}


def _dedup(registros):
    """Elimina duplicados por (url, autor, inicio del contenido)."""
    vistos, unicos = set(), []
    for r in registros:
        clave = (r["url"], r["autor"], (r["contenido"] or "")[:60])
        if clave in vistos:
            continue
        vistos.add(clave)
        unicos.append(r)
    return unicos


async def main():
    inicio = time.perf_counter()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # >>> Aquí ocurre la concurrencia: los frentes arrancan a la vez <<<
        tareas = [
            reddit.extraer_multi(
                browser, consultas,
                max_paginas=2, con_comentarios=True,
                max_hilos=5, max_comentarios=80,
                orden="comments", periodo="month",
                filtrar_relevancia=True, rondas_expand=1,
            )
            for consultas in FRENTES.values()
        ]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        await browser.close()

    # Consolidar
    todos = []
    for nombre, res in zip(FRENTES.keys(), resultados):
        if isinstance(res, Exception):
            print(f"[ERROR] frente '{nombre}': {res}")
            continue
        todos.extend(res)

    todos = _dedup(todos)
    storage.guardar_por_fuente("reddit", todos)
    ruta_json, ruta_csv = storage.guardar_unificado(todos)

    dur = time.perf_counter() - inicio
    posts = sum(1 for r in todos if r["metricas"].get("tipo") == "post")
    print("\n===== RESUMEN (concurrente) =====")
    print(f"Registros : {len(todos)} (posts={posts}, comentarios={len(todos)-posts})")
    print(f"Tiempo    : {dur:.2f} s")
    print(f"JSON      : {ruta_json}")
    print(f"CSV       : {ruta_csv}")


if __name__ == "__main__":
    asyncio.run(main())
