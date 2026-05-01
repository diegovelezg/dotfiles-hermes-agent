---
name: diego-intel
description: Spanish-language research and情报 workflow — morning briefing, read-it-later, and dialectical deep research. All Diego skills consolidated here.
version: 1.0.0
metadata:
  hermes:
    tags: [research, morning-briefing, read-it-later, spanish, intel, Telegram, TTS]
    category: productivity
---

# Diego Intel 🧠

Unified Spanish-language research and情报 workflow. Covers morning briefing, read-it-later article extraction, and dialectical deep research.

## Skills Consolidated Here

- **Buenos Días** — Morning briefing with news, history, science → audio → Telegram
- **Read It Later** — URL extraction → structured report → MCP ledger as permanent intel
- **Research** — Dialectical (Tesis/Antítesis/Síntesis) deep research with verticals

## Architecture Pattern

All Diego skills share the same two-model pattern:
- **MiniMax** (main agent): orchestrates, synthesizes, handles TTS/Telegram/ledger
- **DeepSeek V4 Flash** (delegate): does all web research and content extraction

```
MiniMax → delegate_task(DeepSeek) → web research / extraction
        ← results or fallback ←
MiniMax → synthesize → TTS / Telegram / ledger
```

---

## Buenos Días — Morning Briefing 🌅

Navega a una URL, extrae su contenido y genera un reporte estructurado listo para guardar en el ledger como intel permanente.

### Paso 1: Investigar con DeepSeek (delegar)

Para cada fuente, ejecutá `delegate_task` con DeepSeek V4 Flash. **Si una fuente falla, continuar con las demás** — no abortar todo el proceso. Guardar resultados parciales en `~/.hermes/skills/diego-buenos-dias/output/research-YYYY-MM-DD.json`.

### Fuentes a investigar

**1. Trending AI en Hacker News**
```
goal: Navega a https://news.ycombinator.com/ y extrae los 5 asuntos principales de la página principal que sean sobre AI/ML, LLMs, Python, datos, código abierto o ciencia de datos. Devuelve solo los 5 títulos exactos, TRADUCIDOS AL CASTELLANO. Si no hay 5 sobre esos temas, completa con los que haya y avisa cuántos fueron AI-related.
```

**2. Evento histórico (Wikipedia "On this day")**
```
goal: Navega a https://en.wikipedia.org/wiki/{MES}_{DIA} usando la fecha ACTUAL del sistema (mes en inglés con primera letra mayúscula, día sin ceros). Ejemplo: si hoy es 6 de abril → https://en.wikipedia.org/wiki/April_6. Busca en la sección "On this day" (Eventos) y extrae UN evento histórico interesante cuya fecha coincida exactamente con el día de hoy, PRIORIZANDO eventos de Europa, América Latina, Asia, África u Oceania. RECHAZA eventos de Estados Unidos a menos que no haya ningún otro evento global relevante ese día. Devuelve el evento con nombre, año y descripción breve (máx 300 caracteres).
```

**3. Tecnología (techmeme.com)**
```
goal: Navega a https://techmeme.com y extrae las 3 noticias principales de la sección "Top News". Para cada una devuelve: titular exacto y frase de contexto (máx 200 caracteres).
```

**4. Ciencia (sciencedaily.com)**
```
goal: Navega a https://sciencedaily.com y busca una noticia interesante de la sección "Top Science News". Devuelve: titular exacto y resumen de 2-3 oraciones.
```

**5. Artículo interesante (bigthink.com)**
```
goal: Navega a https://bigthink.com y encuentra un titular del home page que pueda ser interesante. Devuelve el titular y una línea de por qué es relevante.
```

### Paso 2: Sintetizar el reporte

Con los resultados de los delegates (o sus placeholders), redactá el reporte en CASTELLANO con tono de podcast narrativo (sin bullets/listas).

**Estructura obligatoria:**
```
# 🌅 Buenos Días: [Día de la semana], [Día] de [Mes] de [Año]

## Un día como hoy
[Narrativa del evento histórico, máximo 500 caracteres]

## Tecnología
[Un párrafo conectando las 3 noticias de Techmeme]

## AI Trends en Hacker News
[Lista de 5 trending topics sobre AI/ML del día]

## Ciencia
[Resumen narrativo de la noticia científica]

## Podría ser interesante
[Titular de Big Think planteado como idea o pregunta]

*¡Que tengas un excelente día!*
```

**Límite:** 2000-2500 caracteres (sin headers) para audio de 2-3 minutos.

Guardar en: `~/.hermes/skills/diego-intel/output/buenos-dias/YYYY-MM-DD.md`

### Paso 3: Generar audio (OBLIGATORIO)

**El tool `text_to_speech` DEBE ser llamado. No es opcional.**

Usar `text_to_speech` de Hermes:
- Provider: Edge TTS (configurado en `config.yaml:tts.provider`)
- Voz: `es-PE-CamilaNeural` (configurado en `config.yaml:tts.edge.voice`)
- Output: `~/.hermes/skills/diego-intel/output/buenos-dias/hoy.ogg`

### Verificación obligatoria post-TTS

**INMEDIATAMENTE** después de llamar a `text_to_speech`, verificá que el archivo fue creado:

```
1. Llamar a text_to_speech con el texto completo
2. Verificar que ~/.hermes/skills/diego-intel/output/buenos-dias/hoy.ogg existe (ls -la)
3. Si NO existe → reintentar con texto más corto (primera mitad)
4. Si sigue sin existir → reportar FALLO explícitamente en la respuesta
5. Solo incluir la MEDIA tag SI el archivo fue verificado
```

**Regla de oro:** La MEDIA tag solo va en la respuesta SI el archivo físicamente existe en el disco.

### Paso 4: Enviar a Telegram

Incluir el MEDIA tag en la respuesta final:
```
MEDIA:/root/.hermes/skills/diego-intel/output/buenos-dias/hoy.ogg
```

### Cron job recomendado

```
mcp_cronjob(
  action="create",
  prompt="Ejecuta el skill Buenos Días: genera el reporte de hoy con TTS y envía a Telegram.",
  schedule="0 7 * * *",
  name="Buenos Días",
  deliver="telegram",
  skill="diego-intel"
)
```

---

## Read It Later — Article Extraction 📄

Navegar a una URL, extraer su contenido, generar un reporte estructurado en castellano y guardarlo inmediatamente en el ledger de MCP como intel permanente.

### Paso 1: Extraer y sintetizar con DeepSeek (delegar)

```
delegate_task(
  goal="Navega a [URL] y extrae su contenido completo. Luego, redacta un reporte en CASTELLANO con esta estructura exacta:

## Resumen Ejecutivo
[Máximo 500 caracteres. Descripción breve de qué trata el artículo.]

## Resumen Destilado
[Máximo 300 palabras. Principales puntos en narrativa, sin bullets ni listas.]

## Fuente Original
[URL exacta]

Devuelve SOLO el reporte completo, sin comentarios tuyos ni notas adicionales.",
  context="El usuario quiere guardar este artículo para leer después. Extrae todo el contenido relevante y sintetízalo en castellano."
)
```

**Fallback:** Si el delegate falla, usar `web_extract` directamente. Si también falla, buscar con `web_search` y construir el reporte desde ahí.

### Paso 2: Guardar en MCP

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| title   | Título del artículo en CASTELLANO                                   |
| content | El reporte completo (Resumen Ejecutivo + Resumen Destilado + Fuente Original) |
| nature  | "intel"                                                              |
| status  | "permanent"                                                          |

```
ledger_item_create(
  title="[Título en castellano]",
  nature="intel",
  status="permanent",
  content="[Reporte completo]"
)
```

### Estructura de archivos

```
~/.hermes/skills/diego-intel/output/read-it-later/
  YYYY-MM-DD-URL-SLUG.md   # Reporte guardado localmente
```

---

## Research — Dialectical Deep Research 🔬

Investigación estructurada sobre cualquier tema con análisis dialéctico (Tesis/Antítesis/Síntesis) y clasificación por verticales. Genera un reporte completo con oportunidades, riesgos e ideas concretas.

### Modos de investigación

### `--quick` (default)
4 búsquedas:
1. `[tema] definición`
2. `[tema] casos uso`
3. `[tema] ventajas beneficios`
4. `[tema] desventajas limitaciones`

### `--deep`
10 búsquedas (todas las de quick +):
5. `[tema] tendencias futuro`
6. `[tema] empresas líderes`
7. `[tema] tecnología innovación`
8. `[tema] regulación normativa`
9. `[tema] mercado Peru Latinoamerica`
10. `[tema] inversión financiamiento`

### `--interactive`
1. Ejecuta investigación completa (modo deep)
2. Muestra reporte con estadísticas y menú de profundización
3. Espera a que el usuario elija qué aspecto analizar más:
   - `1` → MERCADO (TAM, sizing, competencia)
   - `2` → CLIENTES (pain points, willingness to pay)
   - `3` → PRODUCTO (requisitos técnicos, arquitectura)
   - `4` → MODELO (pricing, unit economics)
   - `5` → COMPETENCIA (análisis de mercado)
   - `6` → TENDENCIAS (tech, regulación)
   - `7` → CASOS (éxitos, failures)
4. Ejecuta 3 búsquedas adicionales sobre el aspecto elegido
5. Genera conclusiones específicas

### Flag `--reuse`
No limpia la base de hechos existente. Agrega sobre lo acumulado.

### Flujo paso a paso

**FASE 1 — Horizon Scanning**
Definir las sub-búsquedas según el modo activo.

**FASE 2 — Búsqueda web**
Para cada sub-búsqueda: `web_search` con limit 10, extraer `title` como claim (max 250 chars).

**FASE 3 — Filtro de Entropía (Jaccard)**
```
tokens(A) = set(A.lower().split())
tokens(B) = set(B.lower().split())
jaccard = len(tokens(A) ∩ tokens(B)) / len(tokens(A) ∪ tokens(B))

Si jaccard > 0.7 → duplicado, descartar
Si jaccard < 0.3 → muy genérico, descartar
```

**FASE 4 — Clasificación por sentimiento**

VENTAJA keywords: ventaja, beneficio, mejor, optimiz, aument, crec, éxito, oportunidad, reduce, ahorra, eficiencia, productividad, rápido, adelante, líder, innov, transform, moderniz, digital, adopta, implement, integra, automatiz, inteligente, potencial, ayuda, aplic, útil, efectivo, resultado, logro

DESVENTAJA keywords: desventaja, problema, difícil, limitacion, reto, desafio, falta, fracaso, riesgo, amenaza, bajo, pérdida, caída, dificult, barrera, obstáculo, resist, confusión, incertidumbre, brecha, retraso, costo, inversión, caro, complejo, lento

**FASE 5 — Clasificación por vertical**

| Vertical | Keywords |
|----------|----------|
| agro | agro, agricultura, campo, cultivo, fruta, exportacion, agri |
| fintech | fintech, banco, pago, crédito, banking, credito |
| retail | retail, tienda, comercio, venta, bodega, supermercado |
| salud | salud, médico, hospital, clínica, doctor, medical |
| educacion | educación, universidad, escuela, curso, formación |
| manufactura | manufactura, fábrica, producción, industrial, factory |
| logistica | logística, transporte, envío, distribución, cadena |
| pymes | pyme, mype, pequeña empresa, mipyme |
| startup | startup, emprendimiento, emprendedor, venture, unicornio |
| gobierno | gobierno, público, estado, municipal, ministerio |

**FASE 6 — Célula Dialéctica (delegate_task, en paralelo)**

**1. Evangelista (Tesis)**
```
goal: Analizá este AtomicFact como Evangelista. Maximizar potencial y viabilidad. Devolvé SOLO JSON.
context: Usá DeepSeek V4 Flash.
```

**2. Inquisidor (Antítesis)**
```
goal: Analizá este AtomicFact como Inquisidor. Encontrar riesgos y limitaciones. Devolvé SOLO JSON.
context: Usá DeepSeek V4 Flash.
```

**3. Mediador (Síntesis)**
```
goal: Integrá los análisis del Evangelista y el Inquisidor para generar síntesis dialéctica. Devolvé SOLO JSON.
context: Usá DeepSeek V4 Flash.
```

**FASE 7 — Síntesis y Reporte**
El agente principal integra todo y genera el reporte.

**FASE 8 — Persistencia**
- Atomic Facts → `~/.hermes/skills/diego-intel/output/research/facts/atomic_facts.jsonl`
- Reporte → `~/.hermes/skills/diego-intel/output/research/output/YYYY-MM-DD-[slug-topic].md`

---

## Estructura de archivos

```
~/.hermes/skills/diego-intel/output/
  buenos-dias/
    research-YYYY-MM-DD.json   # Investigación cruda
    YYYY-MM-DD.md              # Reporte sintetizado
    hoy.ogg                    # Audio del día
  read-it-later/
    YYYY-MM-DD-URL-SLUG.md     # Reporte de artículo
  research/
    facts/atomic_facts.jsonl   # Atomic facts acumulados
    output/YYYY-MM-DD-[topic].md
```

---

## Notas importantes

- **Dos modelos siempre**: MiniMax (orquestación) + DeepSeek V4 Flash (investigación)
- Delegate usa DeepSeek; MiniMax solo orquesta y guarda
- Si una fuente falla, continuar — nunca abortar por una fuente individual
- El cron NUNCA debe fallar en silencio — si el TTS falla, el .md se guarda igual
- **Bug conocido (Buenos Días)**: MiniMax puede "alucinar" el call a `text_to_speech` — escribir la MEDIA tag sin ejecutar el tool. Siempre verificar que el archivo físico existe antes de incluir la MEDIA tag.
