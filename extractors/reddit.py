"""
extractors/reddit.py
Extractor de Reddit con Playwright (async). Usa old.reddit.com porque
renderiza en el servidor y NO exige iniciar sesión, lo que hace la
extracción estable y ligera (ideal para 8 GB de RAM).

Recibe un `browser` ya abierto por el orquestador y crea su propio
browser_context aislado -> permite correr las 3 fuentes en paralelo
sobre un solo proceso Chromium.

Dos niveles de extracción:
  1) posts (títulos) desde la búsqueda.
  2) comentarios de cada post (con precauciones anti-bloqueo).

Filtro de relevancia: solo se visitan hilos cuyo título habla del
TERREMOTO (no de otros temas de Venezuela).
"""

import asyncio
import random

from playwright.async_api import TimeoutError as PWTimeout

import storage

FUENTE = "reddit"
BASE = "https://old.reddit.com"

# Términos que confirman que el hilo trata del sismo (es/pt/en).
TERMINOS_SISMO = [
    "terremoto", "sismo", "sismico", "sísmico", "temblor", "seismo", "seísmo",
    "earthquake", "magnitud", "richter", "epicentro", "replica", "réplica",
    "damnificado", "escombros", "derrumbe", "rescate",
]


def _es_relevante(titulo):
    """True si el título menciona el terremoto (evita otros temas de VE)."""
    if not titulo:
        return False
    t = titulo.lower()
    return any(term in t for term in TERMINOS_SISMO)


async def extraer(browser, criterio, **kwargs):
    """
    Envoltura de una sola consulta (la usa el orquestador main.py).
    Acepta str o lista de str en `criterio`.
    """
    criterios = criterio if isinstance(criterio, (list, tuple)) else [criterio]
    return await extraer_multi(browser, criterios, **kwargs)


async def extraer_multi(browser, criterios, max_paginas=3,
                        con_comentarios=True, max_hilos=15, max_comentarios=120,
                        orden="comments", periodo="month",
                        filtrar_relevancia=True, rondas_expand=1):
    """
    Ejecuta varias consultas, deduplica hilos por URL y baja comentarios
    de los hilos MÁS comentados que sean relevantes al terremoto.
    """
    registros = []
    context = await browser.new_context(
        user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"),
        locale="es-ES",
    )
    page = await context.new_page()

    candidatos = {}   # url -> dict del post (deduplicado)
    try:
        # --- Fase 1: posts desde cada consulta ---
        for criterio in criterios:
            url = (f"{BASE}/search?q={criterio.replace(' ', '+')}"
                   f"&sort={orden}&t={periodo}")
            print(f"[{FUENTE}] Buscando: '{criterio}' "
                  f"(orden={orden}, periodo={periodo})")

            for pagina in range(max_paginas):
                resp = await page.goto(url, wait_until="domcontentloaded",
                                       timeout=30000)
                if await _rate_limited(resp, page):
                    print(f"[{FUENTE}] Reddit está limitando; me detengo.")
                    break
                try:
                    await page.wait_for_selector("div.search-result-link",
                                                 timeout=15000)
                except PWTimeout:
                    print(f"[{FUENTE}] Página {pagina + 1}: sin más resultados")
                    break

                resultados = await page.query_selector_all(
                    "div.search-result-link")
                print(f"[{FUENTE}] Página {pagina + 1}: {len(resultados)} posts")

                for res in resultados:
                    titulo = await _texto(res, "a.search-title")
                    if not titulo:
                        continue
                    if filtrar_relevancia and not _es_relevante(titulo):
                        continue  # descarta temas de VE ajenos al sismo

                    enlace_el = await res.query_selector("a.search-title")
                    enlace = await enlace_el.get_attribute("href") \
                        if enlace_el else None
                    if not enlace or enlace in candidatos:
                        continue  # dedup por URL

                    autor = await _texto(res, ".search-author a")
                    subreddit = await _texto(res, ".search-subreddit-link")
                    coment_txt = await _texto(res, ".search-comments")
                    fecha_el = await res.query_selector("time")
                    fecha = await fecha_el.get_attribute("datetime") \
                        if fecha_el else None

                    post = {"titulo": titulo, "autor": autor,
                            "subreddit": subreddit, "url": enlace,
                            "fecha": fecha, "criterio": criterio,
                            "num_comentarios": _parse_num(coment_txt)}
                    candidatos[enlace] = post
                    registros.append(storage.normalizar(
                        fuente=FUENTE, criterio=criterio, contenido=titulo,
                        autor=autor, fecha_publicacion=fecha, url=enlace,
                        metricas={"tipo": "post", "subreddit": subreddit,
                                  "num_comentarios": post["num_comentarios"]},
                    ))

                siguiente = await page.query_selector(
                    "span.nextprev a[rel~='next']")
                if not siguiente:
                    break
                url = await siguiente.get_attribute("href")
                await asyncio.sleep(random.uniform(1.5, 3.0))

        # --- Fase 2: comentarios de los hilos relevantes más comentados ---
        if con_comentarios and candidatos:
            hilos = sorted(candidatos.values(),
                           key=lambda p: p["num_comentarios"],
                           reverse=True)[:max_hilos]
            print(f"[{FUENTE}] {len(candidatos)} hilos relevantes; "
                  f"visito los {len(hilos)} más comentados:")
            for p in hilos:
                print(f"[{FUENTE}]   {p['num_comentarios']:>4} coment. "
                      f"| {p['subreddit']} | {p['titulo'][:60]}")

            for i, post in enumerate(hilos, 1):
                nuevos = await _comentarios_de_hilo(
                    page, post, max_comentarios, rondas_expand)
                if nuevos is None:
                    print(f"[{FUENTE}] Límite detectado, detengo comentarios.")
                    break
                registros.extend(nuevos)
                print(f"[{FUENTE}]  hilo {i}/{len(hilos)}: "
                      f"+{len(nuevos)} comentarios")
                await asyncio.sleep(random.uniform(2.0, 4.0))
    finally:
        await context.close()

    posts_n = sum(1 for r in registros if r["metricas"].get("tipo") == "post")
    coment_n = len(registros) - posts_n
    print(f"[{FUENTE}] Total: {len(registros)} registros "
          f"({posts_n} posts + {coment_n} comentarios)")
    return registros


async def _comentarios_de_hilo(page, post, max_comentarios, rondas_expand):
    """
    Visita un hilo y devuelve registros de sus comentarios.
    Devuelve None si se detecta rate-limit; [] si el hilo falla (se salta).
    """
    registros = []
    try:
        resp = await page.goto(post["url"], wait_until="domcontentloaded",
                               timeout=30000)
        if await _rate_limited(resp, page):
            return None
        try:
            await page.wait_for_selector("div.commentarea", timeout=12000)
        except PWTimeout:
            return []

        await _expandir_comentarios(page, rondas_expand)

        comentarios = await page.query_selector_all(
            "div.commentarea div.comment")
        for c in comentarios[:max_comentarios]:
            texto = await _texto(c, "div.usertext-body")
            if not texto:
                continue
            autor = await _texto(c, "a.author")
            score = await _texto(c, "span.score")
            fecha_el = await c.query_selector("time")
            fecha = await fecha_el.get_attribute("datetime") if fecha_el else None
            registros.append(storage.normalizar(
                fuente=FUENTE, criterio=post["criterio"], contenido=texto,
                autor=autor, fecha_publicacion=fecha, url=post["url"],
                metricas={"tipo": "comentario", "subreddit": post["subreddit"],
                          "score": score, "post_titulo": post["titulo"]},
            ))
    except Exception as e:
        print(f"[{FUENTE}]  (aviso) hilo saltado: {e}")
        return []
    return registros


async def _expandir_comentarios(page, rondas):
    """Hace clic en 'cargar más comentarios' para vaciar hilos grandes."""
    for _ in range(rondas):
        links = await page.query_selector_all("span.morecomments > a")
        if not links:
            break
        for a in links[:8]:            # tope por ronda -> evita rate-limit
            try:
                await a.click()
                await asyncio.sleep(random.uniform(0.4, 0.9))
            except Exception:
                pass
        await asyncio.sleep(1.0)


async def _rate_limited(response, page):
    """Detecta bloqueo/limitación: HTTP 429 o página 'whoa there'."""
    if response is not None and response.status == 429:
        return True
    try:
        titulo = (await page.title()) or ""
        if "whoa there" in titulo.lower():
            return True
    except Exception:
        pass
    return False


def _parse_num(texto):
    """'42 comentarios' -> 42 ; 'comentar' o None -> 0."""
    if not texto:
        return 0
    digitos = "".join(c for c in texto if c.isdigit())
    return int(digitos) if digitos else 0


async def _texto(elemento, selector):
    """Helper: devuelve el texto de un sub-selector o None."""
    el = await elemento.query_selector(selector)
    if not el:
        return None
    txt = await el.inner_text()
    return txt.strip() if txt else None
