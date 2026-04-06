"""
Tool schemas for personal-ai-ledger plugin.
Based on Intelligence MCP (UIA Core) API spec.

Docs: https://github.com/diegovelez/personal-ai-mcp
"""

# ─── Ledger (Actions & Intel) ───────────────────────────────────────────────

LEDGER_QUERY_SCHEMA = {
    "name": "ledger_query",
    "description": (
        "Búsqueda híbrida (Lexical + Graph) de ítems en el Ledger. "
        "Usa query natural para búsqueda semántica, o filtros específicos para precisión."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Frase natural o términos clave de búsqueda.",
            },
            "status": {
                "type": "string",
                "description": (
                    "Filtrar por estado. Uno o más separados por coma. "
                    "Ejemplos: 'inbox', 'todo,doing', 'done,archived'."
                ),
                "enum": ["inbox", "todo", "doing", "review", "done", "dismissed", "archived", "permanent"],
            },
            "nature": {
                "type": "string",
                "description": "Filtrar por naturaleza del ítem.",
                "enum": ["action", "intel"],
            },
            "limit": {
                "type": "integer",
                "default": 50,
                "description": "Máximo de resultados a retornar.",
            },
            "include_archived": {
                "type": "boolean",
                "default": False,
                "description": "Incluir ítems archivados en los resultados.",
            },
            "id": {
                "type": "string",
                "description": "UUID del ítem. Si se provee, retorna el detalle completo (incluye content).",
            },
            "pending_ai": {
                "type": "boolean",
                "description": "Filtrar ítems que requieren intervención de IA.",
            },
            "timezone": {
                "type": "string",
                "description": "Zona horaria del usuario (ej: 'America/Lima').",
            },
        },
    },
}

LEDGER_ITEM_CREATE_SCHEMA = {
    "name": "ledger_item_create",
    "description": (
        "Crea un ítem nuevo en el Ledger con validación de consistencia. "
        "Para naturaleza 'intel', el status debe ser 'permanent'. "
        "Para 'action', el default es 'inbox'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Título del ítem.",
            },
            "nature": {
                "type": "string",
                "description": "'action' (tarea/proyecto) o 'intel' (información).",
                "enum": ["action", "intel"],
            },
            "status": {
                "type": "string",
                "description": (
                    "Estado inicial. Default: 'inbox' para action, 'permanent' para intel. "
                    "Ejemplos: inbox, todo, doing, review, done."
                ),
                "enum": ["inbox", "todo", "doing", "review", "done", "dismissed", "archived", "permanent"],
            },
            "content": {
                "type": "string",
                "description": "Descripción detallada del ítem.",
            },
            "subject": {
                "type": "string",
                "description": "Categoría o materia (ej: @proyecto, @persona).",
            },
            "priority": {
                "type": "string",
                "description": "Prioridad. Solo para naturaleza 'action'.",
                "enum": ["low", "medium", "high", "urgent"],
            },
            "resolver": {
                "type": "string",
                "description": "Quién resuelve. Solo para naturaleza 'action'.",
                "enum": ["human", "ai"],
            },
            "due_at": {
                "type": "string",
                "description": "Fecha de vencimiento en formato ISO (ej: '2026-04-15T10:00:00-05:00'). Solo para action.",
            },
            "timezone": {
                "type": "string",
                "description": "Zona horaria para interpretar due_at (ej: 'America/Lima').",
            },
        },
        "required": ["title", "nature"],
    },
}

LEDGER_BULK_ACTION_SCHEMA = {
    "name": "ledger_bulk_action",
    "description": (
        "Modificación masiva de ítems seleccionados en el Ledger. "
        "El campo 'note' es requerido y se guarda en logs como razón técnica del cambio. "
        "No permite asignar estados de tarea a ítems de naturaleza 'intel' (siempre deben ser 'permanent')."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lista de UUIDs de los ítems a modificar.",
            },
            "note": {
                "type": "string",
                "description": "Razón técnica del cambio. Se persiste en logs.",
            },
            "status": {
                "type": "string",
                "description": "Nuevo estado a asignar.",
                "enum": ["inbox", "todo", "doing", "review", "done", "dismissed", "archived", "permanent"],
            },
            "priority": {
                "type": "string",
                "description": "Nueva prioridad.",
                "enum": ["low", "medium", "high", "urgent"],
            },
            "subject": {
                "type": "string",
                "description": "Nueva categoría/materia.",
            },
            "title": {
                "type": "string",
                "description": "Nuevo título.",
            },
            "content": {
                "type": "string",
                "description": "Nuevo contenido.",
            },
            "due_at": {
                "type": "string",
                "description": "Nueva fecha de vencimiento ISO.",
            },
        },
        "required": ["ids", "note"],
    },
}

# ─── Briefing ────────────────────────────────────────────────────────────────

BRIEFING_GENERATE_SCHEMA = {
    "name": "briefing_generate",
    "description": (
        "Genera un resumen ejecutivo del estado del sistema. "
        "Persiste un 'Briefing' legible en la tabla summaries y un 'Rational' semántico en Mem0. "
        "Incluye: bloqueos críticos, compromisos inmediatos, contexto histórico, síntesis y siguiente acción."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Query para filtrar qué ledger items incluir en el briefing.",
            },
            "format": {
                "type": "string",
                "default": "text",
                "description": "Formato de salida.",
                "enum": ["text", "markdown", "html"],
            },
            "max_items": {
                "type": "integer",
                "default": 20,
                "description": "Máximo de ledger items a incluir.",
            },
            "timezone": {
                "type": "string",
                "description": "Zona horaria para格式化 fechas en el briefing.",
            },
        },
        "required": ["query"],
    },
}

# ─── Browser Activity ────────────────────────────────────────────────────────

BROWSER_ACTIVITY_ADD_SCHEMA = {
    "name": "browser_activity_add",
    "description": (
        "Registra una actividad de navegación vectorizada (usado por Chrome Extension). "
        "El summary se usa para generar embeddings semánticos. "
        "Los datos se eliminan automáticamente tras 30 días."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "site": {
                "type": "string",
                "description": "Nombre del sitio (ej: 'GitHub', 'Notion').",
            },
            "summary": {
                "type": "string",
                "description": "Resumen de lo visto. Se genera embedding semántico (requerido para búsqueda).",
            },
            "url": {
                "type": "string",
                "description": "URL completa de la página.",
            },
            "title": {
                "type": "string",
                "description": "Título de la página.",
            },
            "duration": {
                "type": "integer",
                "description": "Duración de la visita en segundos.",
            },
            "action": {
                "type": "string",
                "default": "visit",
                "description": "Tipo de acción.",
                "enum": ["visit", "search", "click", "submit", "scroll"],
            },
        },
        "required": ["site", "summary"],
    },
}

BROWSER_ACTIVITY_QUERY_SCHEMA = {
    "name": "browser_activity_query",
    "description": (
        "Búsqueda semántica en el historial de navegación. "
        "Usa embeddings de los resúmenes para encontrar actividades relacionadas."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Búsqueda semántica sobre los resúmenes de actividad.",
            },
            "site": {
                "type": "string",
                "description": "Filtrar por dominio (ej: 'github.com').",
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Máximo de resultados.",
            },
            "match_threshold": {
                "type": "number",
                "default": 0.5,
                "description": "Umbral de similitud mínima (0 a 1).",
            },
        },
        "required": ["query"],
    },
}

# ─── All schemas for convenience ────────────────────────────────────────────

ALL_SCHEMAS = {
    "ledger_query": LEDGER_QUERY_SCHEMA,
    "ledger_item_create": LEDGER_ITEM_CREATE_SCHEMA,
    "ledger_bulk_action": LEDGER_BULK_ACTION_SCHEMA,
    "briefing_generate": BRIEFING_GENERATE_SCHEMA,
    "browser_activity_add": BROWSER_ACTIVITY_ADD_SCHEMA,
    "browser_activity_query": BROWSER_ACTIVITY_QUERY_SCHEMA,
}
