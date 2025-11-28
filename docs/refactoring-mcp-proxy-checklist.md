# Plan de Refactorización: MCP Proxy Tool Approval System

**Fecha**: 2025-11-28
**Estado**: En progreso
**Tiempo estimado total**: ~5 horas

---

## Resumen Ejecutivo

Auditoría completada del sistema MCP Proxy Tool Approval. El código es funcional y seguro, pero tiene problemas de mantenibilidad que deben abordarse para un proyecto Stage 3 (Production-Ready).

---

## Hallazgos Principales

### Problemas Críticos (3)

| # | Problema | Archivos | Impacto |
|---|----------|----------|---------|
| 1 | **Debug prints mezclados con logging** | Todos los archivos MCP + terminal.py | 60+ print() statements en código de producción |
| 2 | **Funciones demasiado largas** | `terminal.py:agent_websocket` (540 líneas), `mcp_proxy_runner.py:run_prompt` (182 líneas), `approval_bridge.py:request_approval` (97 líneas) | Complejidad ciclomática alta, difícil de testear |
| 3 | **Type assertions inseguras (frontend)** | `claudeSessionStore.ts`, `ToolApprovalModal.tsx` | `as unknown as`, `as boolean` bypassing TypeScript safety |

### Problemas Mayores (5)

| # | Problema | Ubicación |
|---|----------|-----------|
| 4 | Store de Zustand demasiado grande | `claudeSessionStore.ts` (1172 líneas) |
| 5 | Código duplicado en approval handlers | 4 funciones casi idénticas en `terminal.py` |
| 6 | Constantes duplicadas (socket path) | 3 archivos definen `DEFAULT_SOCKET_PATH` |
| 7 | Interfaces duplicadas | `PendingToolApproval` vs `PendingMCPApproval` |
| 8 | console.log en producción | 24+ llamadas en frontend |

### Problemas Menores (8)

- Magic numbers sin constantes nombradas
- Imports dentro de funciones (`difflib`, `uuid`)
- Parámetros no usados (`lineNumber` en DiffLine)
- Código deprecado no eliminado
- `LEGACY_SOCKET_PATH` no usado
- `_pending` dict no usado en ToolProxyServer
- Patrón `await_if_coro` repetido 5 veces
- `substr` deprecado (usar `substring`)

---

## Fase 1: Limpieza Inmediata (Debug/Logging)

**Objetivo**: Eliminar debug prints y estandarizar logging
**Esfuerzo estimado**: 30 min
**Impacto**: Alto - código listo para producción

### Backend (Python)

- [x] `code_map/mcp/approval_bridge.py` - 12 prints → logger.debug ✅
- [x] `code_map/mcp/socket_server.py` - 7 prints → logger.debug ✅
- [x] `code_map/mcp/tool_proxy_server.py` - 5 prints → logger.debug ✅
- [x] `code_map/api/terminal.py` - 40+ prints → logger.debug ✅

### Frontend (TypeScript)

- [x] Crear `frontend/src/utils/logger.ts` con helper condicional ✅
- [x] `frontend/src/stores/claudeSessionStore.ts` - 24 console.log → debug() ✅
- [x] `frontend/src/components/ToolApprovalModal.tsx` - 2 console.log → debug() ✅

### Patrón a aplicar (Python)
```python
# Antes
print(f"DEBUG: [MCPSocketServer] Started on {self.socket_path}", flush=True)

# Después
logger.debug(f"[MCPSocketServer] Started on {self.socket_path}")
```

### Patrón a aplicar (TypeScript)
```typescript
// utils/logger.ts
const isDev = import.meta.env.DEV;
export const debug = (msg: string, ...args: unknown[]) => {
  if (isDev) console.log(msg, ...args);
};

// Uso
debug("[ClaudeSession] WebSocket connected");
```

---

## Fase 2: Constantes Compartidas

**Objetivo**: Eliminar duplicación de constantes
**Esfuerzo estimado**: 15 min
**Impacto**: Medio - elimina duplicación

- [ ] Crear `code_map/mcp/constants.py` con:
  ```python
  # Socket paths
  DEFAULT_SOCKET_PATH = "/tmp/atlas_tool_approval.sock"

  # Timeouts (seconds)
  APPROVAL_TIMEOUT = 300.0
  CANCEL_TIMEOUT = 2.0
  COMMAND_TIMEOUT_MS = 120000

  # Preview limits
  PREVIEW_LINE_LIMIT = 50
  PREVIEW_CHAR_LIMIT = 200
  SUMMARY_CHAR_LIMIT = 500
  FILE_LINE_LIMIT = 2000
  ```

- [ ] Actualizar imports en `socket_server.py`
- [ ] Actualizar imports en `tool_proxy_server.py`
- [ ] Actualizar imports en `mcp_proxy_runner.py`
- [ ] Actualizar imports en `terminal.py`

---

## Fase 3: Extraer Handlers de terminal.py

**Objetivo**: Reducir `agent_websocket` de 540 líneas a ~100 líneas
**Esfuerzo estimado**: 2 horas
**Impacto**: Alto - mejora mantenibilidad

### Estructura de archivos

- [ ] Crear directorio `code_map/api/handlers/`
- [ ] Crear `code_map/api/handlers/__init__.py`
- [ ] Crear `code_map/api/handlers/base.py` - BaseAgentHandler ABC
- [ ] Crear `code_map/api/handlers/sdk_handler.py` - SDKModeHandler
- [ ] Crear `code_map/api/handlers/mcp_proxy_handler.py` - MCPProxyModeHandler
- [ ] Crear `code_map/api/handlers/cli_handler.py` - CLIModeHandler
- [ ] Crear `code_map/api/handlers/approval.py` - Shared approval utilities

### Implementación

- [ ] Implementar `BaseAgentHandler` ABC con métodos abstractos
- [ ] Migrar lógica SDK a `SDKModeHandler`
- [ ] Migrar lógica MCP proxy a `MCPProxyModeHandler`
- [ ] Migrar lógica CLI a `CLIModeHandler`
- [ ] Crear función factory `create_handler(mode, websocket, cwd)`
- [ ] Refactorizar `agent_websocket` para usar handlers
- [ ] Unificar código duplicado de approval en `approval.py`

### Estructura base esperada
```python
# handlers/base.py
class BaseAgentHandler(ABC):
    def __init__(self, websocket: WebSocket, cwd: str):
        self.websocket = websocket
        self.cwd = cwd

    @abstractmethod
    async def handle_run(self, message: dict) -> None: ...

    @abstractmethod
    async def handle_cancel(self) -> None: ...
```

---

## Fase 4: Refactorizar Métodos Largos

**Objetivo**: Mejorar testabilidad y legibilidad
**Esfuerzo estimado**: 1 hora
**Impacto**: Medio - mejora testabilidad

### 4.1 `run_prompt` en mcp_proxy_runner.py (182 → ~50 líneas)

- [ ] Extraer `_build_command() -> list[str]`
- [ ] Extraer `_start_process() -> Process`
- [ ] Extraer `_create_output_reader() -> Coroutine`
- [ ] Extraer `_create_error_reader() -> Coroutine`
- [ ] Refactorizar `run_prompt` para usar métodos extraídos

### 4.2 `request_approval` en approval_bridge.py (97 → ~40 líneas)

- [ ] Extraer `_create_approval_request() -> ApprovalRequest`
- [ ] Extraer `_wait_for_response() -> dict`
- [ ] Refactorizar `request_approval` para usar métodos extraídos

---

## Fase 5: Mejoras TypeScript

**Objetivo**: Type safety y eliminación de type assertions inseguras
**Esfuerzo estimado**: 1 hora
**Impacto**: Medio - type safety

### 5.1 Crear tipos seguros para preview data

- [ ] Crear `frontend/src/types/approval.ts`
- [ ] Definir `DiffPreviewData` interface
- [ ] Definir `CommandPreviewData` interface
- [ ] Definir `PreviewData` discriminated union type
- [ ] Definir `BasePendingApproval` interface

### 5.2 Refactorizar componentes

- [ ] Actualizar `ToolApprovalModal.tsx` para usar tipos seguros
- [ ] Eliminar `as unknown as` assertions en `claudeSessionStore.ts`
- [ ] Eliminar `as boolean` assertions inseguras
- [ ] Añadir type guards donde sea necesario

### Tipos esperados
```typescript
// types/approval.ts
interface DiffPreviewData {
  is_new_file: boolean;
  original_lines: number;
  new_lines: number;
}

interface CommandPreviewData {
  command: string;
  description?: string;
  has_sudo: boolean;
  has_rm: boolean;
  has_pipe: boolean;
  has_redirect: boolean;
}

type PreviewData =
  | { type: "diff"; data: DiffPreviewData }
  | { type: "command"; data: CommandPreviewData }
  | { type: "generic"; data: Record<string, unknown> };

interface BasePendingApproval {
  requestId: string;
  toolName: string;
  toolInput: Record<string, unknown>;
  previewType: "diff" | "multi_diff" | "command" | "generic";
  previewData: Record<string, unknown>;
  filePath?: string;
  originalContent?: string;
  newContent?: string;
  diffLines: string[];
  timestamp: Date;
}
```

---

## Fase 6: Limpieza de Código Muerto

**Objetivo**: Housekeeping y eliminación de código no usado
**Esfuerzo estimado**: 15 min
**Impacto**: Bajo - housekeeping

### Eliminar código muerto

- [ ] Eliminar `LEGACY_SOCKET_PATH` en `socket_server.py:27`
- [ ] Eliminar `_pending` dict no usado en `tool_proxy_server.py:67`
- [ ] Evaluar y eliminar código MCP deprecado si no se usa

### Mover imports al top

- [ ] Mover `import difflib` al top en `approval_bridge.py` (líneas 284, 389)
- [ ] Mover `import uuid` al top en `terminal.py`

### Corregir deprecaciones

- [ ] Cambiar `substr` → `substring` en `claude-events.ts:587`

---

## Orden de Ejecución Recomendado

| Prioridad | Fase | Esfuerzo | Impacto | Estado |
|-----------|------|----------|---------|--------|
| 1 | Fase 1: Debug/Logging | 30 min | Alto | [x] Completada ✅ |
| 2 | Fase 2: Constantes | 15 min | Medio | [ ] Pendiente |
| 3 | Fase 6: Limpieza | 15 min | Bajo | [ ] Pendiente |
| 4 | Fase 3: Handlers | 2 horas | Alto | [ ] Pendiente |
| 5 | Fase 4: Métodos largos | 1 hora | Medio | [ ] Pendiente |
| 6 | Fase 5: TypeScript | 1 hora | Medio | [ ] Pendiente |

---

## Notas Importantes

- El sistema es **funcional y seguro** - estas mejoras son de calidad de código
- Las Fases 1-2-6 pueden hacerse juntas en un solo commit
- La Fase 3 es el cambio más grande pero el de mayor impacto
- Considerar dividir `claudeSessionStore.ts` en slices (futuro)
- Ejecutar tests después de cada fase para verificar que no se rompe nada

---

## Registro de Progreso

| Fecha | Fase | Cambios | Commit |
|-------|------|---------|--------|
| 2025-11-28 | Fase 1 | Debug/Logging cleanup - 60+ prints eliminados | Pendiente |

