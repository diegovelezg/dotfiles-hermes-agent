---
name: diego-buenos-dias
description: Informe matutino con noticias, historia y ciencia — generado como audio para Telegram. Usa DeepSeek para investigación web delegando automáticamente.
version: 4.1.0
metadata:
  hermes:
    tags: [morning-briefing, news, audio, Telegram, TTS]
    category: productivity
---

# Buenos Días 🌅

## Objetivo

Generar un informe matutino en audio con información de fuentes diversas y entregarlo vía Telegram como nota de voz.

## Arquitectura

Este skill usa **dos modelos**:

- **MiniMax** (agente principal): coordina, sintetiza, genera TTS y envía a Telegram
- **DeepSeek V4 Flash** (delegado): ejecuta toda la investigación web mediante `delegate_task`

El flujo es:
```
MiniMax → delegate_task(DeepSeek V4 Flash) → investigación web
       ← resultados (o fallback si falla) ←
MiniMax → sintetiza reporte → TTS → MEDIA tag → Telegram
```

## Paso 1: Investigar con DeepSeek (delegar)

Para cada fuente, ejecutá `delegate_task` con DeepSeek V4 Flash. **Si una fuente falla, continuar con las demás** — no abortar todo el proceso. Guardar resultados parciales en `~/.hermes/skills/diego-buenos-dias/output/research-YYYY-MM-DD.json`.

### Fuentes a investigar

**1. Trending AI en Hacker News**
```
goal: Navega a https://news.ycombinator.com/ y extrae los 5 asuntos principales de la página principal que sean sobre AI/ML, LLMs, Python, datos, código abierto o ciencia de datos. Devuelve solo los 5 títulos exactos, TRADUCIDOS AL CASTELLANO. Si no hay 5 sobre esos temas, completa con los que haya y avisa cuántos fueron AI-related.
```

**2. Evento histórico (Wikipedia "On this day")**
```
goal: Navega a https://en.wikipedia.org/wiki/{MES}_{DIA} usando la fecha ACTUAL del sistema (mes en inglés con primera letra mayúscula, día sin ceros). Ejemplo: si hoy es 6 de abril → https://en.wikipedia.org/wiki/April_6. Busca en la sección "On this day" (Eventos) y extrae UN evento histórico interesante cuya fecha coincida exactamente con el día de hoy, PRIORIZANDO eventos de Europa, América Latina, Asia, África u Oceania. RECHAZA eventos de Estados Unidos (independencia, presidents, wars, Supreme Court, Congress, etc.) a menos que no haya ningún otro evento global relevante ese día. Devuelve el evento con nombre, año y descripción breve (máx 300 caracteres). Si TODOS los eventos del día son USA-céntricos, buscar el más antiguo o el menos conocido de esa lista.
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

### Ejemplo de cada llamada:
```
delegate_task(
  goal="[goal de la fuente según arriba]",
  context="Solo devolvé el contenido investigado, sin opiniones tuyas. Si no podés acceder a la página, devolvé null para esa fuente."
)
```

**Manejo de errores por fuente:** Si un delegate falla o devuelve null, usar placeholder: "No se pudo obtener esta información" y continuar. Nunca abortar por una fuente individual.

## Paso 2: Sintetizar el reporte

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

Guardar en: `~/.hermes/skills/diego-buenos-dias/output/YYYY-MM-DD.md`

## Paso 3: Generar audio (OBLIGATORIO)

**El tool `text_to_speech` DEBE ser llamado. No es opcional. No escribir la MEDIA tag sin generar el audio primero.**

Usar `text_to_speech` de Hermes:
- Provider: Edge TTS (configurado en `config.yaml:tts.provider`)
- Voz: `es-PE-CamilaNeural` (configurado en `config.yaml:tts.edge.voice`)
- Output: `~/.hermes/skills/diego-buenos-dias/output/hoy.ogg`

El archivo `hoy.ogg` SIEMPRE se sobrescribe.

### Verificación obligatoria post-TTS

**INMEDIATAMENTE** después de llamar a `text_to_speech`, verificá que el archivo fue creado:

```
1. Llamar a text_to_speech con el texto completo
2. Verificar que ~/.hermes/skills/diego-buenos-dias/output/hoy.ogg existe (usar terminal: ls -la)
3. Si NO existe → reintentar con texto más corto (primera mitad)
4. Si sigue sin existir → reportar FALLO explícitamente en la respuesta
5. Solo incluir la MEDIA tag SI el archivo fue verificado
```

**Regla de oro:** La MEDIA tag solo va en la respuesta SI el archivo物理icamente existe en el disco. Si el tool no se llamó o falló, no escribir la MEDIA tag.

**Manejo de errores TTS:** Si `text_to_speech` falla, intentar una versión más corta del texto (primera mitad). Si sigue fallando, guardar el reporte .md y reportar el error explícitamente — el cron NO debe fallar en silencio ni inventar la MEDIA tag.

**Importante:** La voz se configura en `~/.hermes/config.yaml` bajo `tts.edge.voice`. No se pasa como parámetro — el tool la lee de la config.

## Paso 4: Enviar a Telegram

El audio se entrega incluyendo el MEDIA tag en la respuesta final del skill:

```
MEDIA:/root/.hermes/skills/diego-buenos-dias/output/hoy.ogg
```

**Para cron jobs:** Cuando el cron corre en contexto autónomo (sin chat activo), el MEDIA tag se resuelve automáticamente si el cron tiene `deliver: "telegram"` configurado. El agent de Telegram detecta el MEDIA tag y lo entrega como nota de voz al home channel.

**Si el cron falló en silencio (no entregó audio):** Ejecutar manualmente desde esta sesión usando `mcp_cronjob(action='run', job_id='[id]')` y verificar que el MEDIA tag llegue. El skill debe completarse siempre — si el TTS falla, el reporte .md igualmente se guarda y está disponible.

## Estructura de archivos

```
~/.hermes/skills/diego-buenos-dias/output/
  research-YYYY-MM-DD.json   # Investigación cruda (resultados parciales si hay errores)
  YYYY-MM-DD.md              # Reporte sintetizado
  hoy.ogg                    # Audio del día (sobrescribe siempre)
```

## Cron job recomendado

```
mcp_cronjob(
  action="create",
  prompt="Ejecuta el skill Buenos Días: genera el reporte de hoy con TTS y envía a Telegram usando el MEDIA tag del audio.",
  schedule="0 7 * * *",
  name="Buenos Días",
  deliver="telegram",
  skill="buenos-dias"
)
```

## Notas

- Investigación web → DeepSeek (delegate), no el agente principal
- Síntesis, TTS y Telegram → MiniMax (agente principal)
- Usar herramientas nativas de Hermes (delegate_task, text_to_speech)
- Si una fuente falla, continuar con las demás — no abortar
- El cron NUNCA debe fallar en silencio — si el TTS falla, el .md se guarda igual
- Para scheduling: `mcp_cronjob` daily a las 7 AM con skill `buenos-dias`
- **Bug conocido:** MiniMax puede "alucinar" el call a text_to_speech — escribe la MEDIA tag sin ejecutar el tool. Para prevenir esto, el Paso 3 incluye verificación obligatoria post-TTS. Si el archivo no existe, reintentar o reportar fallo explícitamente.
