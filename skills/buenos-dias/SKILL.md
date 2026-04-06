---
name: buenos-dias
description: Informe matutino con noticias, historia y ciencia — generado como audio y enviado a Telegram. Usa DeepSeek para investigación web delegando automáticamente.
version: 3.0.0
metadata:
  hermes:
    tags: [morning-briefing, news, audio, Telegram, TTS, es-PE-CamilaNeural]
    category: productivity
---

# Buenos Días 🌅

## Objetivo

Generar un informe matutino en audio con información de fuentes diversas y entregarlo como voice message a Telegram.

## Arquitectura

Este skill usa **dos modelos**:

- **MiniMax** (agente principal): coordina, sintetiza, genera TTS y entrega a Telegram
- **DeepSeek R1** (delegado): ejecuta toda la investigación web mediante `delegate_task`

El flujo es:
```
MiniMax → delegate_task(DeepSeek R1) → investigación web
       ← resultados ←
MiniMax → sintetiza reporte → TTS → Telegram (voice message)
```

## Paso 1: Investigar con DeepSeek (delegar)

Para cada fuente, ejecutá `delegate_task` con DeepSeek R1. Recopilá TODOS los resultados antes de continuar.

### Fuentes a investigar

**1. Evento histórico (onthisday.com)**
```
goal: Navega a https://onthisday.com/day/{MES}/{DIA} usando la fecha ACTUAL del sistema (mes en inglés en minúsculas, día sin ceros). Ejemplo: si hoy es 6 de abril → https://onthisday.com/day/april/6. Extrae UN evento histórico interesante cuya fecha coincida exactamente con el día de hoy. Devuelve el evento con nombre, año y descripción breve (máx 300 caracteres).
```

**2. Tecnología (techmeme.com)**
```
goal: Navega a https://techmeme.com y extrae las 3 noticias principales de la sección "Top News". Para cada una devuelve: titular exacto y frase de contexto (máx 200 caracteres).
```

**3. Artículo interesante (bigthink.com)**
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

## Podría ser interesante
[Titular de Big Think planteado como idea o pregunta]

*¡Que tengas un excelente día!*
```

**Límite:** 2000-2500 caracteres (sin headers) para audio de 2-3 minutos.

Guardar en: `~/.hermes/skills/buenos-dias/output/YYYY-MM-DD.md`

## Paso 3: Generar audio

Usar `text_to_speech` de Hermes con la voz configurada:

- Provider: Edge TTS (configurado en `config.yaml:tts.provider`)
- Voz: `es-PE-CamilaNeural` (configurado en `config.yaml:tts.edge.voice`)
- Output: `~/.hermes/skills/buenos-dias/output/hoy.ogg`

**Importante:** La voz se configura en `~/.hermes/config.yaml` bajo `tts.edge.voice`. No se pasa como parámetro — el tool la lee de la config.

El archivo `hoy.ogg` SIEMPRE se sobrescribe.

## Paso 4: Enviar a Telegram

El TTS genera un archivo `.ogg` con `MEDIA:/path/to/hoy.ogg`. Cuando el agent corre dentro del gateway de Telegram, el MEDIA tag se entrega automáticamente como voice message al home channel.

Para scheduling, configurar un cron con `deliver: "telegram"` y skill `buenos-dias`.

## Notas

- Investigación web → DeepSeek (delegate), no el agente principal
- Síntesis, TTS y Telegram → MiniMax (agente principal)
- Usar herramientas nativas de Hermes (delegate_task, text_to_speech)
- Scheduling: cron daily a las 7 AM Lima con `deliver: telegram` y `skill: buenos-dias`
- La voz se configura en `config.yaml`: `tts.edge.voice: es-PE-CamilaNeural`
