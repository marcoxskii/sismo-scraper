# sismo-scraper

Extracción **concurrente** de datos desde Reddit sobre el **terremoto de
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
  `terremoto Venezuela muertos`, `Venezuela earthquake`, `Venezuela quake`,
  `terremoto Venezuela rescate`.
- **Orden:** por número de comentarios (los hilos con más discusión, donde se
  concentra el acoso).
- **Filtro de relevancia:** solo se procesan hilos cuyo título menciona el
  sismo (`terremoto`, `sismo`, `temblor`, `magnitud`, `réplica`, `epicentro`,
  `earthquake`…), descartando otros temas de Venezuela.

## 3. Fuente

**Reddit** (`extractors/reddit.py`), vía `old.reddit.com` — renderiza en el
servidor y **no exige iniciar sesión**, lo que hace la extracción estable y
ligera.

## 4. Concurrencia — técnica y justificación

Se usa **`asyncio` + Playwright async**. El orquestador (`main.py`) abre **un
solo navegador Chromium** y lanza varios **frentes de extracción** (grupos de
consultas) **simultáneamente** con `asyncio.gather()`; cada frente trabaja en
su propio `browser_context` aislado.

**¿Por qué asyncio y no hilos/procesos?** La extracción es **I/O-bound**
(esperas de red y de carga de página, no cálculo). La concurrencia cooperativa
da paralelismo real de espera **sin gastar CPU** y con **un único proceso
Chromium**, minimizando la RAM — decisión adecuada para el equipo de desarrollo
(MacBook Pro M3, 8 GB). Hilos o procesos abrirían varios navegadores y
multiplicarían el consumo de memoria sin ganancia, dado que el cuello de
botella es la red.

```
main.py ──►  asyncio.gather(
                frente_espanol,     ┐
                frente_ingles,      ├─ arrancan y corren a la vez
                frente_afectados,   ┘
             )
```

## 5. Precauciones anti-bloqueo

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
Salidas en `data/`: `reddit.json` + `dataset_unificado.json` / `.csv`.

## 7. Instalación (macOS Apple Silicon)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## 8. Ejecución

```bash
# Extracción concurrente (varios frentes con asyncio.gather):
python main.py

# Corrida grande de una sola pasada (sin concurrencia):
python run_reddit.py
```

## 9. Estructura

```
main.py            Orquestador concurrente (asyncio.gather)
run_reddit.py      Corrida grande de una sola pasada
storage.py         Esquema común + guardado JSON/CSV
extractors/
  reddit.py        Extractor de Reddit (Playwright async)
data/              Salidas generadas (base de datos textual)
```

## 10. Resultados de una corrida

- **1842 registros** (58 posts + 1784 comentarios) de 12 subreddits.
- Hilos más comentados: *"Magnitude 7.1 earthquake rocks Venezuela"* (2610),
  *"7.1 Earthquake at the airport"* (704), etc.
- 62 comentarios con score negativo (controversiales / posible acoso).
- Sin bloqueos de IP.

- 

Ejecutado en un entorno macOS
