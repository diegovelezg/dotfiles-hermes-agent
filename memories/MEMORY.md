SSOT: Hindsight = verdad duradera de Diego; MEMORY local solo guarda reglas activas por turno. Ante contradicción, Hindsight gana y MEMORY se ajusta. Violaciones: parar y avisar.
Reglas activas:
- "procede"/"continua"/"basta"/"continue" → ejecutar sin confirmar.
- Idioma: español. Conciso. Markdown cuando aporta.
- Navegación: browser_* nativas o curl; misma pestaña en sesión autenticada.
- Brave personal intocable. Agente usa SOLO ~/.hermes/browser-data/agent. Detener sesión: `hermes-brave-x stop` exclusivamente. NUNCA pkill contra brave-origin.
- No asumir estructura de proyectos hasta que Diego entregue la lista pendiente.
- Antes de afirmar hechos sobre Diego: verificar fuente. No inventar.
- Memoria 100% MANUAL: agent NUNCA invoca hindsight_retain por iniciativa propia; solo cuando Diego lo pida explícitamente. Si algo merece guardarse, sugerir en chat.
- Diego autoriza al agente a crear skills nuevos por encargo. No esperar confirmación si alcance claro; ejecutar y mostrar.
§
Notas multi-fuente: Diego quiere capturar intel desde (a) texto directo, (b) voice notes (transcribir audio), (c) URLs (delegar a DeepSeek v4-flash para extraer+sintetizar en castellano). Toda nota → ledger MCP (nature="intel", status="permanent") + archivo local ~/.hermes/skills/diego-read-it-later/output/YYYY-MM-DD-SLUG.md.
§
Skills: CREAR sin pedir confirmación si alcance claro (ya existe regla). BORRAR = SIEMPRE pedir confirmación explícita antes; "y el skill X?" no es instrucción de borrado. Convención de nombre: TODOS los skills custom usan prefijo `diego-*` sin excepción.