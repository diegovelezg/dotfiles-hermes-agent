---
name: buenos-dias
description: Informe matutino con noticias, historia y ciencia — generado como audio para Discord.
---

# Buenos Días 🌅

## Objetivo

Generar un informe matutino en audio con información de fuentes diversas y entregarlo vía Discord.

## Configuración

Este skill usa:
- **Web search** para investigar las fuentes
- **TTS nativo de Hermes** para generar audio (Edge TTS por defecto, sin API key)
- **Mensajería de Hermes** para enviar a Discord

## Instrucciones para el Agente

### 1. Investigar fuentes

Usa `browser_navigate` y `browser_snapshot` para Twitter/X. Luego `web_search` y `web_extract` para las otras fuentes.

**Trending Topics AI en Twitter/X**:
Navega a `https://x.com/search?q=AI&src=trend_chart` o `https://x.com/search?q=artificial%20intelligence&f=live`
Extrae los 5 trending topics sobre AI/ML del día.

**Evento histórico** (onthisday.com):
Navega a `https://onthisday.com/day/<MES>/<DIA>` con la fecha ACTUAL del sistema (mes y día en inglés, sin ceros). Ejemplo: si hoy es 1 de abril → `https://onthisday.com/day/april/1`. Selecciona UN evento histórico interesante y verifica que la fecha del evento coincida con el día actual.

**Tecnología** (techmeme.com):
Extrae las 3 noticias principales de la sección "Top News".

**Ciencia** (sciencedaily.com):
Busca una noticia interesante de la sección "Top Science News".

**Artículo interesante** (bigthink.com):
Encuentra un titular del home que pueda ser interesante.

### 2. Redactar el reporte

Crea el reporte en CASTELLANO con tono de podcast narrativo (sin bullets/listas).

**Estructura obligatoria:**
```
# 🌅 Buenos Días: [Día de la semana], [Día] de [Mes] de [Año]

## Un día como hoy
[Narrativa del evento histórico, máximo 500 caracteres]

## Tecnología
[Un párrafo conectando las 3 noticias de Techmeme]

## AI Trends en Twitter
[Lista de 5 trending topics sobre AI/ML del día]

## Ciencia
[Resumen narrativo de la noticia científica]

## Podría ser interesante
[Titular de Big Think planteado como idea o pregunta]

*¡Que tengas un excelente día!*
```

**Límite de texto:** 2000-2500 caracteres (sin headers) para audio de 2-3 minutos.

Guarda en: `~/.hermes/skills/buenos-dias/output/YYYY-MM-DD.md`

### 3. Generar audio

Usa la herramienta `text_to_speech` de Hermes:
- Idioma: `es-ES` (Español)
- Provider por defecto: Edge TTS (gratis)
- Output: `~/.hermes/skills/buenos-dias/output/hoy.ogg`

**Importante:** El archivo `hoy.ogg` SIEMPRE se sobrescribe. No acumular audios — solo mantener uno actualizado.

### 4. Enviar a Discord

Usa la herramienta `send_message` de Hermes:
```json
{
  "action": "send",
  "channel": "discord",
  "target": "1474242034356326442",
  "filePath": "~/.hermes/skills/buenos-dias/output/hoy.ogg",
  "asVoice": true,
  "message": "🌅 *Buenos Días!*"
}
```

## Notas

- Usar herramientas nativas de Hermes (web search, browser, TTS, message) — NO exec ni scripts externos.
- El audio se genera con Edge TTS que es gratuito y no requiere API key.
- Para cambiar provider de TTS, editar `config.yaml` → `tts.provider`.
- El skill puede ejecutarse manualmente o como cron job (recomendado: diario a las 8:00 AM).

## Scheduling (opcional)

Para crear un cron job que ejecute este skill diariamente:
```
hermes cron create "0 8 * * *"
```
Usar el prompt:
```
Ejecuta el skill buenos-dias para generar el reporte matutino de hoy.
```
