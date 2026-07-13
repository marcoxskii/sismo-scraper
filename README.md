# sismo-scraper

Extracción **paralela** de datos desde redes sociales sobre el **terremoto de
Venezuela (magnitud 7.1)**, para construir una base textual que luego se usará
en análisis de sentimientos, detección de **ciberacoso / mensajes de burla** y
visualización.

> Práctica 06 — Computación Paralela.

---

## 1. Problemática

Tras el terremoto en Venezuela surgieron miles de reacciones en redes: apoyo,
testimonios de afectados, pero también **burlas, humor negro y ataques** hacia
la tragedia. Este proyecto **recolecta ese contenido textual** de forma
trazable. La *clasificación* del acoso corresponde al proyecto final; aquí se
genera la **base inicial de datos**.

## 2. Estrategia de búsqueda

- **Palabras clave / consultas:** `Venezuela terremoto`, `sismo Venezuela`,
  `terremoto Venezuela muertos`, `Venezuela earthquake`.
- **Orden:** por número de comentarios (los hilos con más discusión, donde se
  concentra el acoso).
- **Filtro de relevancia:** solo se procesan hilos cuyo título menciona el
  sismo (`terremoto`, `sismo`, `temblor`, `magnitud`, `réplica`, `epicentro`,
  `earthquake`…), descartando otros temas de Venezuela.

## 3. Fuentes (3 redes, extraídas en paralelo)

| Fuente | Estado | Responsable |
|--------|--------|-------------|
| **Reddit**   | Implementada (`extractors/reddit.py`) | este repo |
| **TikTok**   | Integrable (`extractors/tiktok.py`)   | compañero |
| **Instagram**| Integrable (`extractors/instagram.py`)| compañero |

## 4. Paralelismo — técnica y justificación

Se usa **`asyncio` + Playwright async**. El orquestador (`main.py`) abre **un
solo navegador Chromium** y lanza los tres extractores **simultáneamente** con
`asyncio.gather()`; cada uno trabaja en su propio `browser_context` aislado.

**¿Por qué asyncio y no hilos/procesos?** La extracción es **I/O-bound**
(esperas de red y de carga de página, no cálculo). La concurrencia cooperativa
da paralelismo real de espera **sin gastar CPU** y con **un único proceso
Chromium**, minimizando la RAM — decisión adecuada para el equipo de desarrollo
(MacBook Pro M3, 8 GB). Hilos o procesos abrirían varios navegadores y
multiplicarían el consumo de memoria sin ganancia, dado que el cuello de
botella es la red.

```
main.py  ──►  asyncio.gather(
                 reddit.extraer(browser, criterio),      ┐
                 tiktok.extraer(browser, criterio),      ├─ arrancan a la vez
                 instagram.extraer(browser, criterio),   ┘
              )
```

## 5. Precauciones anti-bloqueo (Reddit)

- Navega `old.reddit.com` **sin login** → no hay cuenta que bloquear.
- **Pausas aleatorias** (1.5–4 s) entre páginas e hilos.
- **Límites** configurables de hilos y comentarios.
- **Detección de HTTP 429 / "whoa there"** → *backoff* y parada automática.
- **Aislamiento de errores**: si un hilo falla, se salta (nunca crashea).

## 6. Almacenamiento y trazabilidad

Cada registro (ver `storage.py`) conserva:

```json
{
  "fuente": "reddit",
  "criterio_busqueda": "Venezuela terremoto",
  "contenido": "texto del post o comentario",
  "autor": "usuario",
  "fecha_publicacion": "2026-...T..:..:..+00:00",
  "url": "https://old.reddit.com/r/.../comments/...",
  "metricas": { "tipo": "comentario", "subreddit": "r/worldnews", "score": "-31 puntos", "post_titulo": "..." },
  "extraido_en": "2026-...T..:..:..+00:00"
}
```

Se cumple la trazabilidad exigida: **de qué red** viene (`fuente`), **qué
búsqueda** se usó (`criterio_busqueda`) y **qué texto** se obtuvo (`contenido`).
Salidas en `data/`: un JSON por fuente + `dataset_unificado.json` / `.csv`.

## 7. Instalación (macOS Apple Silicon)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## 8. Ejecución

```bash
# Solo Reddit (corrida grande con filtro de relevancia):
python run_reddit.py

# Sistema paralelo completo (3 fuentes a la vez):
python main.py
```

## 9. Estructura

```
main.py            Orquestador paralelo (asyncio.gather)
run_reddit.py      Corrida grande solo de Reddit
storage.py         Esquema común + guardado JSON/CSV
extractors/
  reddit.py        Extractor de Reddit (Playwright async)
  tiktok.py        Stub para integrar
  instagram.py     Stub para integrar
data/              Salidas generadas (base de datos textual)
```

## 10. Resultados de la última corrida

- **1842 registros** (58 posts + 1784 comentarios) de 12 subreddits.
- Hilos más comentados: *"Magnitude 7.1 earthquake rocks Venezuela"* (2610),
  *"7.1 Earthquake at the airport"* (704), etc.
- 62 comentarios con score negativo (controversiales / posible acoso).
- Sin bloqueos de IP.
