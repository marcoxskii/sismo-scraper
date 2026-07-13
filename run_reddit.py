"""
run_reddit.py - Corrida grande SOLO de Reddit, con filtro de relevancia
al terremoto de Venezuela. Genera data/reddit.json.
"""

import asyncio
import time

from playwright.async_api import async_playwright

import storage
from extractors import reddit

# Varias consultas para ampliar la cobertura del MISMO evento (el sismo).
CRITERIOS = [
    "Venezuela terremoto",
    "sismo Venezuela",
    "terremoto Venezuela muertos",
    "Venezuela earthquake",
]


async def main():
    inicio = time.perf_counter()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        registros = await reddit.extraer_multi(
            browser, CRITERIOS,
            max_paginas=2,
            con_comentarios=True,
            max_hilos=15,           # 15 hilos más comentados
            max_comentarios=120,    # hasta 120 comentarios por hilo
            orden="comments",
            periodo="month",
            filtrar_relevancia=True,  # SOLO hilos del terremoto
            rondas_expand=1,          # expande 'cargar más comentarios'
        )
        await browser.close()

    ruta = storage.guardar_por_fuente("reddit", registros)
    dur = time.perf_counter() - inicio

    posts = [r for r in registros if r["metricas"].get("tipo") == "post"]
    coments = [r for r in registros if r["metricas"].get("tipo") == "comentario"]
    subs = sorted({r["metricas"].get("subreddit") for r in coments})

    print("\n===== CORRIDA REDDIT =====")
    print(f"Registros : {len(registros)}  (posts={len(posts)}, comentarios={len(coments)})")
    print(f"Subreddits con comentarios: {len(subs)} -> {', '.join(s for s in subs if s)}")
    print(f"Tiempo    : {dur:.2f} s")
    print(f"Guardado  : {ruta}")


if __name__ == "__main__":
    asyncio.run(main())
