"""
test_reddit.py - Prueba SOLO el extractor de Reddit (sin TikTok/Instagram).
Abre un navegador, ejecuta reddit.extraer() y guarda data/reddit.json.
"""

import asyncio
import time

from playwright.async_api import async_playwright

import storage
from extractors import reddit

CRITERIO = "Venezuela terremoto"


async def main():
    inicio = time.perf_counter()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        registros = await reddit.extraer(
            browser, CRITERIO,
            max_paginas=2,          # más posts candidatos
            con_comentarios=True,
            max_hilos=10,           # visita los 10 hilos MÁS comentados
            max_comentarios=50,     # hasta 50 comentarios por hilo
            orden="comments",       # ordena por número de comentarios
            periodo="month",        # último mes (el sismo fue hace 2 semanas)
        )
        await browser.close()

    ruta = storage.guardar_por_fuente("reddit", registros)
    dur = time.perf_counter() - inicio

    posts = [r for r in registros if r["metricas"].get("tipo") == "post"]
    coments = [r for r in registros if r["metricas"].get("tipo") == "comentario"]

    print("\n===== PRUEBA REDDIT =====")
    print(f"Registros : {len(registros)}  (posts={len(posts)}, comentarios={len(coments)})")
    print(f"Tiempo    : {dur:.2f} s")
    print(f"Guardado  : {ruta}")
    print("\n--- Primeros 5 comentarios ---")
    for r in coments[:5]:
        print(f"\n[{r['metricas'].get('subreddit')}] score={r['metricas'].get('score')} autor={r['autor']}")
        print(f"  {r['contenido'][:200]}")


if __name__ == "__main__":
    asyncio.run(main())
