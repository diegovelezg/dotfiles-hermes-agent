---
name: buenos-dias
description: Informe matutino con noticias, historia y ciencia — generado como audio para Discord. Usa DeepSeek para investigación web delegando automáticamente.
version: 2.0.0
metadata:
  hermes:
    tags: [morning-briefing, news, audio, Discord, TTS]
    category: productivity
---

# Buenos Días 🌅

## Objetivo

Generar un informe matutino en audio con información de fuentes diversas y entregarlo vía Discord.

## Arquitectura

Este skill usa **dos modelos**:

- **MiniMax** (agente principal): coordina, sintetiza, genera TTS y envía a Discord
- **DeepSeek R1** (delegado): ejecuta toda la investigación web mediante `delegate_task`

El flujo es:
```
MiniMax → delegate_task(DeepSeek R1) → investigación web
       ← resultados ←
MiniMax → sintetiza reporte → TTS → Discord
```

## Paso 1: Investigar con DeepSeek (delegar)

Para cada fuente, ejecutá `delegate_task` con DeepSeek R1. Recopilá TODOS los resultados antes de continuar.

### Fuentes a investigar

**1. Trending AI en Twitter/X**
```
goal: Navega a https://x.com/search?q=AI&src=trend_chart y extrae los 5 trending topics sobre AI/ML del día. Devuelve solo los 5 topics con su texto exacto.
```

**2. Evento histórico (onthisday.com)**
```
goal: Navega a https://onthisday.com/day/{MES}/{DIA} usando la fecha ACTUAL del sistema (mes en inglés en minúsculas, día sin ceros). Ejemplo: si hoy es 6 de abril → https://onthisday.com/day/april/6. Extrae UN evento histórico interesante cuya fecha coincida exactamente con el día de hoy. Devuelve el evento con nombre, año y descripción breve (máx 300 caracteres).
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

### Configuración del delegate

Usar SIEMPRE estos parámetros para cada delegate:
```
acp_command: claude
acp_args: ["--acp", "--stdio", "--model", "deepseek/deepseek-r1"]
```

Ejemplo completo de cada llamada:
```
delegate_task(
  goal="[goal de la fuente según arriba]",
  context="Solo devolvé el contenido investigado, sin opiniones tuyas.",
  acp_command="claude",
  acp_args=["--acp", "--stdio", "--model", "deepseek/deepseek-r1"]
)
```

## Paso 2: Sintetizar el reporte

Con todos los resultados de los delegates, redactá el reporte en CASTELLANO con tono de podcast narrativo (sin bullets/listas).

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
[Titular de Big Thinkplanteado como idea o pregunta]

*¡Que tengas un excelente día!*
```

**Límite:** 2000-2500 caracteres (sin headers) para audio de 2-3 minutos.

Guardar en: `~/.hermes/skills/buenos-dias/output/YYYY-MM-DD.md`

## Paso 3: Generar audio

Usar `text_to_speech` de Hermes:
- Idioma: `es-ES`
- Provider: Edge TTS (gratis, sin API key)
- Output: `~/.hermes/skills/buenos-dias/output/hoy.ogg`

El archivo `hoy.ogg` SIEMPRE se sobrescribe.

## Paso 4: Enviar a Discord

```
send_message(
  action="send",
  channel="discord",
  target="1474242034356326442",
  filePath="~/.hermes/skills/buenos-dias/output/hoy.ogg",
  asVoice=true,
  message="🌅 *Buenos Días!*"
)
```

## Notas

- Investigación web → DeepSeek (delegate), no el agente principal
- Síntesis, TTS y Discord → MiniMax (agente principal)
- Usar herramientas nativas de Hermes (delegate_task, text_to_speech, send_message)
- Para scheduling: `mcp_cronjob` daily a las 8 AM con prompt: "Ejecuta el skill buenos-dias"
