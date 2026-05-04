---
name: diego-research
description: Protocolo de Investigación Dialéctica y Fractal — investigación web profunda con tensión dialéctica (Tesis/Antítesis/Síntesis) y análisis por verticales. Solo persiste en archivos locales, no toca el Ledger a menos que el usuario lo pida.
version: 1.0.0
metadata:
  hermes:
    tags: [research, web, dialectic, analysis]
    category: research
---

# diego-research

## Objetivo

Investigación estructurada sobre cualquier tema con análisis dialectico (Tesis/Antítesis/Síntesis) y clasificación por verticales. Genera un reporte completo con oportunidades, riesgos e ideas concretas.

## Arquitectura

```
MiniMax (agente principal)
  ├── Horizon Scanning → define sub-búsquedas
  ├── web_search + web_extract → investigación
  ├── Filtro de entropía (Jaccard) → Atomic Facts
  ├── Clasificación (ventaja/desventaja/neutral) → por vertical
  ├── delegate_task(DeepSeek v4 Flash) → Célula Dialéctica (3 roles)
  └── Síntesis → Reporte en markdown

Persistencia: archivos locales en ~/.hermes/skills/diego-research/
  ├── facts/atomic_facts.jsonl   ← Atomic facts acumulados
  └── output/YYYY-MM-DD-[topic].md ← Reporte del día

NO usa Ledger a menos que el usuario lo pida explícitamente.
```

## Modos de investigación

### --quick (default)
4 búsquedas:
1. `[tema] definición`
2. `[tema] casos uso`
3. `[tema] ventajas beneficios`
4. `[tema] desventajas limitaciones`

### --deep
10 búsquedas (todas las de quick +):
5. `[tema] tendencias futuro`
6. `[tema] empresas líderes`
7. `[tema] tecnología innovación`
8. `[tema] regulación normativa`
9. `[tema] mercado Peru Latinoamerica`
10. `[tema] inversión financiamiento`

### --interactive
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

### Flag --reuse
No limpia la base de hechos existente. Agrega sobre lo acumulado.
Sin este flag, los facts de esta sesión son nuevos nomás.

### Flag --follow-spin-offs
Tras completar la investigación principal (FASE 1-8), si el Mediador detectó spin_offs_pending, el agente ejecuta una segunda ronda de investigación para cada spin-off detectado, aplicando el mismo filtro de entropía y Célula Dialéctica. Los hechos y insights de spin-off se incorporan al reporte final bajo la sección `## 🔄 Spin-off Insights`.

Límites:
- `max_depth = 2` (principal + 1 nivel de spin-offs, no más)
- `max_spin_offs = 3` por nivel (si hay más, priorizar por score de entropía del Mediador)
- Deduplicación por Jaccard: si spin_topic tiene jaccard > 0.6 con uno ya investigado, se omite
- El spin-off es "shallow" (FASE 1-6, sin generar reporte propio) salvo que `--deep` esté activo

Restricción de implementación: `delegate_task` no puede invocar `delegate_task`. Los spin-offs usan `execute_code` (sin timeout de 600s) para ejecutar el mini-research loop internamente.

## Flujo paso a paso

### FASE 1 — Horizon Scanning

Definir las sub-búsquedas según el modo activo. Armar una lista de {q, type}.

### FASE 2 — Búsqueda web (PARALELO)

Ejecutar TODAS las búsquedas web_search EN PARALELO en una sola ronda de llamadas de herramientas.

```
Patrón de llamada paralelo (siguiente response del agente):

web_search(query="[query 1]", limit=10)
web_search(query="[query 2]", limit=10)
web_search(query="[query 3]", limit=10)
... (tantas como sub-búsquedas haya en el modo activo)
```

Reglas:
- Hacer TODAS las llamadas web_search en la MISMA respuesta (parallel tool calls)
- NO procesar resultados entre llamadas — esperar a tener todos los resultados
- Tras ejecutar las llamadas, extraer de CADA resultado:
  - `title` → claim (max 250 chars)
  - `url` → source_url (para citaciones)
- Descartar claims < 10 caracteres
- Recopilar todos los claims en una lista colectiva antes de pasar a FASE 3
- Cada item colectado: {claim, source_url, query}

### FASE 3 — Filtro de Entropía (Jaccard)

Para cada claim nuevo, comparar con todos los facts existentes en `atomic_facts.jsonl`.

```
tokens(A) = set(A.lower().split())
tokens(B) = set(B.lower().split())
jaccard = len(tokens(A) ∩ tokens(B)) / len(tokens(A) ∪ tokens(B))

Si jaccard > 0.7 → duplicado, descartar
Si jaccard < 0.3 → muy genérico, descartar
```

Los facts que pasan el filtro se aceptan como Atomic Facts.

### FASE 4 — Clasificación por sentimiento

Keyword matching sobre el claim:

**VENTAJA** (al menos 1 keyword):
```
ventaja, beneficio, mejor, optimiz, aument, crec, éxito, oportunidad,
reduce, ahorra, eficiencia, productividad, rápido, adelante, líder,
innov, transform, moderniz, digital, adopta, implement, integra,
automatiz, inteligente, potencial, ayuda, aplic, útil, efectivo,
resultado, logro
```

**DESVENTAJA** (al menos 1 keyword):
```
desventaja, problema, difícil, limitacion, reto, desafio, falta,
fracaso, riesgo, amenaza, bajo, pérdida, caída, dificult, barrera,
obstáculo, resist, confusión, incertidumbre, brecha, retraso, costo,
inversión, caro, complejo, lento
```

**NEUTRAL**: resto

### FASE 5 — Clasificación por vertical

Keywords por sector:

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

Si no matchea ninguno → `general`.

### FASE 6 — Célula Dialéctica (delegate_task)

Ejecutar EN PARALELO 3 delegate_task (uno por rol):

**1. Evangelista (Tesis)**
```
goal: """Analizá este AtomicFact como Evangelista en un proceso de investigación dialéctica.

Claim: "[claim]"
Fact ID: [fact_id]

Tu rol: maximizar potencial y viabilidad. Identificar fortalezas, explorar potencial, buscar evidencia favorable, definir condiciones de éxito.

Devolvé SOLO JSON válido:
{
  "role": "evangelista",
  "fact_id": "[fact_id]",
  "analysis": {
    "strengths": ["..."],
    "potential": ["..."],
    "supporting_evidence": ["..."],
    "success_conditions": ["..."]
  },
  "confidence": 0.0-1.0,
  "remaining_questions": ["..."]
}

Sé riguroso pero abierto. No exageres, no subestimes."""
context: "Usá DeepSeek v4 Flash. Responde SOLO JSON, sin texto adicional."
```

**2. Inquisidor (Antítesis)**
```
goal: """Analizá este AtomicFact como Inquisidor en un proceso de investigación dialéctica.

Claim: "[claim]"
Fact ID: [fact_id]

Tu rol: encontrar riesgos, fallos, limitaciones y puntos ciegos. Identificar debilidades, exponer riesgos, buscar contra-evidencia, definir condiciones de fallo.

Devolvé SOLO JSON válido:
{
  "role": "inquisidor",
  "fact_id": "[fact_id]",
  "analysis": {
    "weaknesses": ["..."],
    "risks": ["..."],
    "contradicting_evidence": ["..."],
    "failure_conditions": ["..."]
  },
  "confidence": 0.0-1.0,
  "challenging_questions": ["..."]
}

Sé agresivo pero justo. Cuestiona todo, pero basa tus objeciones en evidencia."""
context: "Usá DeepSeek v4 Flash. Responde SOLO JSON, sin texto adicional."
```

**3. Mediador (Síntesis)**
```
goal: """Integá los análisis del Evangelista y el Inquisidor para generar una síntesis dialéctica.

TESIS: [respuesta JSON del Evangelista]
ANTÍTESIS: [respuesta JSON del Inquisidor]

Tu rol: mediador. Identificar puntos de convergencia, detectar fricciones, generar síntesis, evaluar certidumbre.

Devolvé SOLO JSON válido:
{
  "role": "mediador",
  "fact_id": "[fact_id]",
  "synthesis": {
    "convergence_points": ["..."],
    "friction_zones": ["..."],
    "new_insights": ["..."],
    "certainty_level": "low|medium|high"
  },
  "spin_off_needed": true|false,
  "spin_off_topic": "tema que requiere más investigación si hay fricción",
  "recommended_action": "accept|reject|investigate_more"
}

Sé integrador pero crítico. No busques consenso forzado; abrazá la tensión productiva."""
context: "Usá DeepSeek v4 Flash. Responde SOLO JSON, sin texto adicional."
```

**Aplicar a:**
- Top 3 ventajas (ordenadas por confianza del filtro Jaccard)
- Top 3 desventajas (ordenadas por confianza del filtro Jaccard)
- Máximo 6 facts por ejecución de Célula Dialéctica

**Nota de rendimiento:** 3 facts × 3 roles = 9 delegate_tasks en paralelo. Este es el límite operativo; no exceder para evitar timeout. Si hay más de 6 facts relevantes, priorizar por score de entropía (Jaccard medio = mayor novelty = más valioso para análisis dialéctico).

### FASE 7 — Síntesis y Reporte

El agente principal integra todo y genera el reporte.

### FASE 8 — Persistencia

**Atomic Facts** → `~/.hermes/skills/diego-research/facts/atomic_facts.jsonl`
Cada línea: JSON con {fact_id, claim, source_url, query_type, analysis, verticals, created_at}

**Reporte** → `~/.hermes/skills/diego-research/output/YYYY-MM-DD-[slug-topic].md`

**Estado de investigación** → `~/.hermes/skills/diego-research/facts/research_state.json`
Estado temporal para spin-offs: {research_topic, spin_offs_pending[depth, topic, source_fact], already_researched[], depth}
- `depth=0`: main research
- `depth=1`: spin-off de main research
- `depth=2`: spin-off de spin-off (máximo)

### FASE 9 — Spin-off Loop (solo si --follow-spin-offs)

**Condiciones de entrada:**
- Flag `--follow-spin-offs` activo
- `spin_offs_pending` no vacío tras FASE 7
- `depth < max_depth` (máximo 2 niveles)

**Ejecución:**

1. **Recopilar spin-offs del Mediador** (FASE 7): todos los `spin_off_topic` donde `spin_off_needed: true`, ordenados por score de entropía (mayor novelty primero)

2. **Deduplicar** contra `already_researched[]` usando Jaccard > 0.6 entre topics

3. **Limitar** a `max_spin_offs = 3` por nivel

4. **Para cada spin_topic (ejecutado via execute_code para evitar timeout de delegate_task):**
   ```
   a. Guardar estado en research_state.json (research_topic, depth=1)
   b. Mini-research (FASE 1-6):
      - FASE 1: definir 4 sub-búsquedas para el spin_topic
      - FASE 2: web_search en paralelo
      - FASE 3: filtro Jaccard contra atomic_facts.jsonl existente
      - FASE 4: clasificación sentimiento
      - FASE 5: clasificación vertical
      - FASE 6: Célula Dialéctica sobre top 3+3 facts
   c. Devolver: {spin_facts[], spin_insights[], spin_sources[], sub_spin_offs[]}
   d. Hacer append de spin_facts[] a atomic_facts.jsonl
   e. Marcar spin_topic en already_researched[]
   f. Acumular spin_insights[] + spin_sources[]
   g. Si depth < 2, agregar sub_spin_offs[] a spin_offs_pending para siguiente nivel (depth=2)
   ```

5. **Regenerar reporte** con los insights y fuentes de spin-offs incorporados

**Notas sobre el reporte:**
- La sección `🏷️ Hallazgos por categoría` debe incluir **todos los facts** (main + spin-facts) para dar una visión completa
- El header `Estadísticas` debe reflejar: `X encontrados | Y aceptados | Z filtrados | S spin-facts (de N spin-offs)`
- La sección `🔄 Spin-off Insights` debe listar los claims de los spin-facts con su `source_url` — no resúmenes genéricos
- El campo `depth=N` indica: `1` = spin-off de main research, `2` = spin-off de otro spin-off
- Los insights del spin-off se toman directamente del `synthesis.new_insights` y `synthesis.friction_zones` del Mediador del spin-off, no de inferencia

**Restricción crítica:** Esta fase usa `execute_code` (sin límite de 600s) para ejecutar los mini-research loops. NO intentar implementar esta lógica dentro de `delegate_task` — el modelo no puede invocar `delegate_task` recursivamente.

**Límites operativos:**
- Main research: depth=0
- Spin-off de main research: depth=1
- Spin-off de spin-off: depth=2 (máximo — sin más niveles)
- Máximo 3 spin-offs por nivel para mantener el costo bajo control
- Si `--reuse` también está activo, los facts de spin-off se agregan al archivo existente

### FASE 10 — Métricas de Ejecución

Al finalizar toda la ejecución (incluyendo spin-offs), el agente debe registrar métricas en `facts/research_metrics.jsonl` y en el header del reporte.

**Métricas a collect y persistir:**

```python
metrics = {
    "topic": "[tema de investigación]",
    "mode": "quick|deep|interactive",
    "timestamp_start": "ISO8601",
    "timestamp_end": "ISO8601",
    "duration_seconds": T,
    "main_research": {
        "queries_executed": N,
        "claims_collected": X,
        "facts_accepted": Y,
        "facts_filtered": Z,
        "entropy_filter_rate": "W%",  # Z/(X+Z)*100
        "sentiment_breakdown": {"VENTAJA": V, "DESVENTAJA": D, "NEUTRAL": N},
        "verticals_detected": ["general", "fintech", ...]
    },
    "cell_dialectic": {
        "facts_analyzed": M,  # ventaja + desventaja
        "ventaja_analyzed": V,
        "desventaja_analyzed": D,
        "delegates_invoked": M * 3,  # 3 roles por fact
        "spin_offs_triggered": K
    },
    "spin_offs": {
        "executed": K,
        "spin_facts_generated": S,
        "max_depth_reached": max_depth,
        "dedup_skipped": D,
        "limit_skipped": L
    },
    "tokens_delegation_estimate": "~X.XK"
}
```

**Reglas:**
- `duration_seconds` se mide desde el primer web_search hasta que el reporte está escrito
- `entropy_filter_rate = facts_filtered / (claims_collected + facts_filtered) * 100`
- `tokens_delegation_estimate` se calcula sumando los `tokens.output` de cada delegate_task response
- Las métricas se appendean a `facts/research_metrics.jsonl` (una línea por investigación)

## Estructura del reporte

```
# 🔬 diego-research: [TEMA]

**Modo:** quick | deep | interactive
**Fecha:** YYYY-MM-DD
**Estadísticas:** X encontrados | Y aceptados | Z filtrados (W% entropía) | S spin-facts (de N spin-offs)

**Métricas de ejecución:**
| Métrica | Valor |
|---------|-------|
| Tiempo total | T segundos |
| Búsquedas web | N calls |
| Facts analizados en Célula | M (V+D) |
| Spin-offs ejecutados | K (depth≤2) |
| Tokens delegación | ~X.XK (estimado) |

---

## 📋 Búsquedas realizadas
[Lista de queries ejecutadas con counts]

## 🏷️ Hallazgos por categoría

### ✅ Ventajas (N)
[claim] — [source_url]

### ⚠️ Desventajas (N)
[claim] — [source_url]

### 🔹 Neutral (N)
[claim] — [source_url]

## 🏢 Por Vertical
[N findings por cada vertical detectado]

## ⚖️ Célula Dialéctica

### TESIS (Top 3 ventajas con análisis del Evangelista)
[claim] — [source_url]
[analysis.strengths + analysis.potential]

**Fuente del análisis:** [source_url del AtomicFact analizado]

### ANTÍTESIS (Top 3 desventajas con análisis del Inquisidor)
[claim] — [source_url]
[analysis.weaknesses + analysis.risks]

**Fuente del análisis:** [source_url del AtomicFact analizado]

### 💡 SÍNTESIS (Integración del Mediador)
[Convergence points, friction zones, new insights]

## 💡 Conclusiones

### Oportunidades
[Del análisis]

### Riesgos
[Del análisis Inquisidor]

### Ideas concretas
[Generadas del análisis, NO hardcoded — que surjan de los facts]

### Recomendaciones
[Basadas en el recommended_action del Mediador]

## 🔗 Fuentes
[Lista deduplicada de todas las source_url citadas en el reporte, ordenadas por aparación]

## 🔄 Spin-off Insights
[Solo si --follow-spin-offs y se ejecutaron spin-offs]

Para cada spin-off investigado:
- **Spin-off:** [topic]
- **Depth:** `depth=N` (indica nivel: 1 = spin-off de main research, 2 = spin-off de otro spin-off)
- **Hallazgos:** [facts más relevantes del spin-off — listar los claims con source_url]
- **Insights:** [del Mediador del spin-off]
- **Sub-spin-offs detectados:** [lista o "Ninguno"]

[Lista de todos los spin_offs_pending que NO se investigaron por límites de profundidad o dedup, con razón de omisión]
```

## Ejemplo de uso

```
/diego-research inteligencia artificial Perú
/diego-research empresas diversidad inclusión --deep
/diego-research tendencias tecnológicas 2026 --interactive
/diego-research agroexportación Perú --reuse
/diego-research IA en Latinoamérica --follow-spin-offs
/diego-research IA en Latinoamérica --deep --reuse --follow-spin-offs
```

## Notas

- NO usa Ledger salvo que el usuario lo pida explícitamente
- Delegate usa DeepSeek v4 Flash (modelo dialéctico)
- Agente principal usa MiniMax (síntesis y reporte)
- Búsquedas web paralelas (FASE 2): todas las web_search en la misma ronda de llamadas
- Si una búsqueda no devuelve resultados, continuar con las demás
- Los spin_offs detectados por el Mediador se listan al final del reporte como "Pendientes de investigar"
- Spin-off loop (FASE 9): se ejecuta via `execute_code` (no delegate_task) para evitar restricción de recursión
- Límite spin-offs: max_depth=2, max_spin_offs=3 por nivel, dedup Jaccard > 0.6
- Métricas (FASE 10): se registran en `facts/research_metrics.jsonl` y en el header del reporte
