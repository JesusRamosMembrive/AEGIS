# Estado Actual del Proyecto

**Última actualización**: 2025-11-23
**Etapa detectada**: Stage 3 (Production-Ready)
**Proyecto**: ATLAS - Stage-Aware Development Framework + Code Map Backend

---

## 📍 ESTADO ACTUAL

**En progreso:**
- 🔥 **Agent Monitoring Dashboard** - Visión completa (4 semanas)
  - Fase 1 (Semana 1): Foundation - Audit hooks + SSE streaming (50% completado)
  - Terminal en vivo + Timeline visual + Diffs en tiempo real

**Completado recientemente:**
- ✅ Audit hooks system (`code_map/audit/hooks.py`)
- ✅ Linter pipeline integration con audit tracking
- ✅ Sistema de 3 fases (Architect → Implementer → Code-Reviewer)
- ✅ Frontend básico de Audit Sessions (manual)

**Bloqueado/Pendiente:**
- Ninguno actualmente

---

## 🎯 PRÓXIMOS PASOS

1. **Inmediato** (Continuar Fase 1):
   - Modificar git_history para auto-log operations
   - Añadir SSE endpoint para event streaming
   - Crear tests para audit hooks
   - Frontend: useAuditEventStream hook
   - Frontend: Actualizar AuditSessionsView para SSE

2. **Fase 2** (Semana 2):
   - Agent bridge para Claude Code
   - Terminal emulator (xterm.js)
   - Timeline visual (Gantt chart)

3. **Fase 3-4** (Semanas 3-4):
   - Diffs en tiempo real
   - Export system
   - Metrics dashboard

---

## 📝 DECISIONES RECIENTES

### Agent Monitoring Dashboard - Visión Completa (2025-11-23)
**Qué**: Transformar Audit Trail en dashboard completo de monitoreo de agentes en tiempo real
**Por qué**: Control total sobre Claude Code - ver comandos, diffs, timeline de fases, evitar dejarse seducir por potencia del agente
**Alcance**: 4 semanas, 3 features core (terminal vivo, timeline, diffs), enfoque inicial Claude Code
**Impacto**:
- Audit hooks system completo (`code_map/audit/hooks.py`)
- Linter pipeline auto-logging integrado
- SSE streaming para eventos en tiempo real (pendiente)
- Frontend dashboard con 3 columnas (terminal | timeline | diffs)

### Captura Híbrida de Eventos (2025-11-23)
**Qué**: Automática para diffs/git/tests + manual para intents/decisiones
**Por qué**: Balance entre automatización y control humano
**Implementación**:
- `audit_run_command()`: Wrapper de subprocess con auto-logging
- `AuditContext`: Context manager para bloques de trabajo
- `@audit_tracked`: Decorator para funciones
- Environment var `ATLAS_AUDIT_RUN_ID` para integración externa

---

## 🚨 CONTEXTO CRÍTICO

**Restricciones importantes:**
- Stage-aware: No sobre-ingenierizar más allá del stage actual (Stage 3)
- YAGNI enforcement: Solo añadir features cuando hay dolor real 3+ veces
- Separation of concerns: Workflow docs (.claude/doc/) vs Code analysis (frontend)

**Patrones establecidos:**
- Templates en `templates/basic/.claude/` para nuevos proyectos
- Backend FastAPI con async/await en `code_map/`
- Frontend React + TanStack Query en `frontend/src/`
- Agents en `.claude/subagents/` con 3-phase coordination

**No hacer:**
- No modificar templates sin actualizar test_full_flow.sh
- No añadir features al frontend sin evidencia de pain point real
- No saltarse el workflow de 3 fases (Planning → Implementation → Validation)
- No mantener 01-current-phase.md >150 líneas (mover a historial)

---

## 📚 RECURSOS

- **Historial completo**: Ver `.claude/01-session-history.md` (760+ líneas de contexto profundo)
- **Arquitectura 3-phase**: Ver `.claude/doc/README.md` para templates y guías
- **Documentación técnica**: Ver `docs/` para stage criteria, quick start, etc.
- **Templates actualizados**: `templates/basic/.claude/` con sistema compacto

---

## 🔄 ÚLTIMA SESIÓN

### Sesión 8: Fix Terminal Reconnection Bug (2025-11-24)

**Problema inicial identificado:**
- ❌ Terminal funciona en primera conexión, pero falla al recargar página
- ❌ Necesario reiniciar backend para recuperar funcionalidad
- 🔍 Root cause: Event loop reference capturada queda obsoleta tras reload, causando race condition

**Fixes aplicados (Backend):**
- ✅ **code_map/api/terminal.py** (modificado):
  - Validación de `loop.is_running()` antes de encolar output (líneas 61-65)
  - Mejorado orden de cleanup: shell.close() → sleep(0.1) → read_task.cancel() (líneas 142-146)
  - Agregado try-catch en inicialización de WebSocket para capturar errores silenciosos (líneas 32-53)
  - Previene intentos de encolar a event loop cerrado

- ✅ **code_map/terminal/pty_shell.py** (modificado):
  - Agregado `self.read_thread` como atributo de clase (línea 44)
  - Modificado método `read()` para almacenar referencia al thread (líneas 187-188)
  - Agregado `thread.join(timeout=0.5)` en `close()` (líneas 207-214)
  - Asegura terminación limpia de thread antes de liberar recursos

**Fixes aplicados (Frontend):**
- ✅ **frontend/src/main.tsx** (modificado):
  - Deshabilitado React StrictMode temporalmente (líneas 16-22)
  - StrictMode causa double-mount que cierra WebSocket antes de conectarse
  - Solo afecta desarrollo, producción no tiene StrictMode effects

- ✅ **frontend/src/components/RemoteTerminalView.tsx** (simplificado):
  - Código limpio sin protecciones complejas contra React Strict Mode
  - WebSocket se crea y gestiona normalmente
  - Cleanup simple y directo (líneas 189-198)

**Solución final React Strict Mode:**
- ✅ Deshabilitar StrictMode es la solución correcta para componentes con WebSockets
- ✅ WebSockets y StrictMode son incompatibles por diseño (double-mount cierra conexiones)
- ✅ Producción nunca tiene este problema (StrictMode solo en desarrollo)
- ✅ Alternativa más compleja sería useRef con efectos condicionales

- ✅ **tests/test_terminal_reconnect.md** (nuevo):
  - Documentación completa del bug, fix y testing strategy
  - Manual de pruebas para validar reconexiones múltiples
  - Criterios de éxito y monitoreo de logs

**Decisiones técnicas:**
1. **Loop validation**: Prevenir encolado a loops obsoletos
2. **Cleanup order**: Shell → wait → task, evita race conditions
3. **Thread join**: Timeout de 0.5s para terminación explícita
4. **Logging mejorado**: Warnings para debugging de reconexiones

**Resultado esperado:**
- ✅ Recargas de página funcionan sin reiniciar backend
- ✅ Cleanup limpio de recursos (threads, shells, loops)
- ✅ Sin procesos zombie acumulados
- ✅ Sin errores en logs de encolado
- ✅ React Strict Mode no interfiere con conexiones

**Testing requerido ahora:**
- ✅ CRÍTICO: Usuario debe probar recarga de página (F5/Ctrl+R) para confirmar fix funciona
- Manual: Seguir procedimiento en `tests/test_terminal_reconnect.md`
- Validar: Recargas simples, recargas rápidas, múltiples tabs
- Monitorear: Logs de backend y procesos shell (ya no debería haber errores)

**Próxima sesión debe:**
- Si fix funciona: Remover debug print() statements del backend
- Si fix funciona: Continuar con Fase 1 del Agent Monitoring Dashboard
- Si persiste problema: Investigar más a fondo el comportamiento de React Strict Mode

---

**💡 Recordatorio**: Ver `.claude/01-session-history.md` y `docs/audit-trail.md` para contexto completo.