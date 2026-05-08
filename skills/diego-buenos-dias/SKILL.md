---
name: diego-buenos-dias
description: Informe matutino con noticias, historia y ciencia — generado como audio para Telegram. Usa DeepSeek para investigación web delegando automáticamente.
version: 4.2.0
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

### Manejo de errores por fuente:** Si un delegate falla o devuelve null, usar placeholder: "No se pudo obtener esta información" y continuar. Nunca abortar por una fuente individual.

**Fallback si DeepSeek no está disponible:** Si `delegate_task` falla con error "Could not start Copilot ACP command 'deepseek'" (DeepSeek ACP no instalado), usar `web_extract` y `web_search` directamente para cada fuente:
- onthisday.com → `web_extract` URL directa
- techmeme.com → `web_extract` homepage
- sciencedaily.com → `web_extract` homepage
- bigthink.com → `web_extract` homepage
- AI trends → `web_search` con query "site:x.com AI trending May 2026" o buscar en newsletters de AI (State of AI, The AI Landscape)

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

**Verificar y reparar directorio de output ANTES de llamar a TTS:**

```bash
# 1. Verificar si el symlink existe y apunta a un directorio válido
TARGET=$(readlink -f ~/.hermes/skills/diego-buenos-dias 2>/dev/null)
if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
    # Symlink roto o missing — remover y recrear apuntando al archive
    rm -f ~/.hermes/skills/diego-buenos-dias
    ln -s /root/.hermes/skills/.archive/diego-buenos-dias ~/.hermes/skills/diego-buenos-dias
fi

# 2. Crear output si no existe
mkdir -p ~/.hermes/skills/diego-buenos-dias/output
```

**Fallback si todo falla:** Usar `/tmp/buenos-dias-output/` y crear el directorio ahí.

Usar `text_to_speech` de Hermes:
- Provider: Edge TTS (configurado en `config.yaml:tts.provider`)
- Voz: `es-PE-CamilaNeural` (configurado en `config.yaml:tts.edge.voice`)
- No especificar output path manualmente — el tool usa su propio cache interno

### Verificación obligatoria post-TTS

**INMEDIATAMENTE** después de llamar a `text_to_speech`, verificá que el archivo fue creado usando la ruta que el tool devuelve en `file_path`:

```
1. text_to_speech devuelve file_path (ej: /root/.hermes/audio_cache/tts_20260504_121410.ogg)
2. Verificar que existe: terminal ls -la <file_path>
3. Si NO existe → reintentar con texto más corto (primera mitad)
4. Si sigue sin existir → reportar FALLO explícitamente
5. Usar el file_path real del tool, NO hardcodear "~/.../hoy.ogg"
```

**Regla de oro:** La MEDIA tag solo va en la respuesta SI el archivo físico existe en el disco.

**Manejo de errores TTS:** Si `text_to_speech` falla, intentar una versión más corta del texto. Si sigue fallando, guardar el reporte .md y reportar el error explícitamente — el cron NO debe fallar en silencio.

**Importante:** La voz se configura en `config.yaml` bajo `tts.edge.voice`. No se pasa como parámetro — el tool la lee de la config. Siempre usar el `file_path` que el tool devuelve.

## Paso 4: Enviar a Telegram

El audio se entrega incluyendo la MEDIA tag con la ruta real del `file_path` retornado por `text_to_speech`:

```
MEDIA:<file_path del tool text_to_speech>
```

**Para cron jobs:** Cuando el cron corre en contexto autónomo (sin chat activo), el MEDIA tag se resuelve automáticamente si el cron tiene `deliver: "telegram"` configurado. El agent de Telegram detecta el MEDIA tag y lo entrega como nota de voz al home channel.

**Si el cron falló en silencio (no entregó audio):** Ejecutar manualmente desde esta sesión usando `mcp_cronjob(action='run', job_id='[id]')` y verificar que el MEDIA tag llegue. El skill debe completarse siempre — si el TTS falla, el reporte .md igualmente se guarda y está disponible.

## Estructura de archivos

```
~/.hermes/skills/diego-buenos-dias/output/
  research-YYYY-MM-DD.json   # Investigación cruda (resultados parciales si hay errores)
  YYYY-MM-DD.md              # Reporte sintetizado

# Audio: se guarda en el cache de Hermes — usar el file_path que el tool devuelve
# NO hardcodear ~/.../hoy.ogg
```

**Fallback (si symlink roto):** `/tmp/buenos-dias-output/`

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
- **Bug conocido:** `text_to_speech` guarda en su propio cache interno (`/root/.hermes/audio_cache/tts_TIMESTAMP.ogg`), NO en `~/.hermes/skills/diego-buenos-dias/output/hoy.ogg`. Siempre usar el `file_path` que el tool retorna en su respuesta — nunca hardcodear una ruta de salida.
- **Twitter/X fallback:** X.com requiere autenticación para trending topics. Si el delegate no puede acceder, usar la fuente alternativa "Tech Twitter" (techmeme.com/twitter) como fuente secundaria para trends de IA.
- **Bug conocido 2:** El symlink `~/.hermes/skills/diego-buenos-dias → /root/.hermes/custom-skills/diego-buenos-dias` puede estar roto (el target no existe), causando `FileExistsError` en TTS. Siempre verificar el directorio con `ls` y usar `/tmp/buenos-dias-output/` como fallback si el symlink está roto.
