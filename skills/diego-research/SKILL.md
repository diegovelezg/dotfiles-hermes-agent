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
  ├── delegate_task(DeepSeek R1) → Célula Dialéctica (3 roles)
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

## Flujo paso a paso

### FASE 1 — Horizon Scanning

Definir las sub-búsquedas según el modo activo. Armar una lista de {q, type}.

### FASE 2 — Búsqueda web

Para cada sub-búsqueda:
1. `web_search` con la query (limit 10)
2. De cada resultado, extraer `title` como `claim` (max 250 chars)
3. Descartar claims < 10 caracteres

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
context: "Usá DeepSeek R1. Responde SOLO JSON, sin texto adicional."
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
context: "Usá DeepSeek R1. Responde SOLO JSON, sin texto adicional."
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
context: "Usá DeepSeek R1. Responde SOLO JSON, sin texto adicional."
```

**Aplicar a:**
- Top 5 ventajas
- Top 5 desventajas

### FASE 7 — Síntesis y Reporte

El agente principal integra todo y genera el reporte.

### FASE 8 — Persistencia

**Atomic Facts** → `~/.hermes/skills/diego-research/facts/atomic_facts.jsonl`
Cada línea: JSON con {fact_id, claim, source_url, query_type, analysis, verticals, created_at}

**Reporte** → `~/.hermes/skills/diego-research/output/YYYY-MM-DD-[slug-topic].md`

## Estructura del reporte

```
# 🔬 diego-research: [TEMA]

**Modo:** quick | deep | interactive
**Fecha:** YYYY-MM-DD
**Estadísticas:** X encontrados | Y aceptados | Z filtrados (W% entropía)

---

## 📋 Búsquedas realizadas
[Lista de queries ejecutadas con counts]

## 🏷️ Hallazgos por categoría

### ✅ Ventajas (N)
[claims de ventajas con source y vertical]

### ⚠️ Desventajas (N)
[claims de desventajas con source y vertical]

### 🔹 Neutral (N)
[claims neutrales]

## 🏢 Por Vertical
[N findings por cada vertical detectado]

## ⚖️ Célula Dialéctica

### TESIS (Top 5 ventajas con análisis del Evangelista)
[claim + analysis.strengths + analysis.potential]

### ANTÍTESIS (Top 5 desventajas con análisis del Inquisidor)
[claim + analysis.weaknesses + analysis.risks]

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
```

## Ejemplo de uso

```
/diego-research inteligencia artificial Perú
/diego-research empresas diversidad inclusión --deep
/diego-research tendencias tecnológicas 2026 --interactive
/diego-research agroexportación Perú --reuse
```

## Notas

- NO usa Ledger salvo que el usuario lo pida explícitamente
- Delegate usa DeepSeek R1 (modelo dialectico)
- Agente principal usa MiniMax (síntesis y reporte)
- Si una búsqueda no devuelve resultados, continuar con las demás
- Los spin_offs detectados por el Mediador se listan al final del reporte como "Pendientes de investigar"
