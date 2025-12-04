# Claude Code Quick Reference

Guía rápida de comandos y conceptos de Claude Code.  
> ¿Trabajas con Codex CLI? Consulta también `docs/CODEX_CLI_REFERENCE.md`.

---

## 📋 Slash Commands Esenciales

### Context Management
- `/add <file>` - Add file to context
- `/add <pattern>` - Add files matching pattern (e.g., `*.py`, `src/**/*.js`)
- `/drop <file>` - Remove specific file from context
- `/drop *` - Remove all files from context
- `/clear` - Clear conversation but keep file context
- `/new` - Start completely fresh (clears conversation AND files, re-reads CLAUDE.md)

### Workflow
- `/debug` - Enable debug mode for verbose output
- `/test` - Run project tests
- `/fix` - Attempt to fix errors in last output
- `/undo` - Undo last tool use
- `/help` - Show help and available commands

### Tasks & Agents
- `/task <description>` - Create a subagent for a specific task
- `/tasks` - List active subagents
- `/cancel` - Cancel current operation

---

## 🤖 Cuándo Usar Subagentes

### ✅ Usa Subagentes Cuando:

1. **Tarea bien definida e independiente**
   - "Implementar función de parse de JSON"
   - "Escribir tests para módulo X"
   - "Refactorizar clase Y según nuevos requerimientos"

2. **Necesitas trabajo en paralelo**
   - Dos features independientes
   - Testing mientras desarrollas
   - Documentación mientras codeas

3. **Contexto diferente requerido**
   - Subagente solo necesita ver 2-3 archivos
   - Tú trabajas en otros archivos
   - Evitas contaminar contexto principal

4. **Tarea repetitiva**
   - Aplicar mismo patrón en múltiples archivos
   - Generar código boilerplate similar

### ❌ NO Uses Subagentes Cuando:

1. **Tarea simple** - Más overhead que valor
2. **Alto acoplamiento** - Requiere mucha coordinación
3. **Requerimientos poco claros** - Iteración es clave
4. **Debugging activo** - Necesitas ver todo el contexto

### 💡 Tips:
```bash
# Crear subagente con contexto específico
/task "Implementar parse_json() en utils.py siguiendo el patrón de parse_xml()"

# Dar instrucciones claras
/task "Escribir unit tests para Calculator class.
Test todas las operaciones: add, subtract, multiply, divide.
Incluir edge cases: división por cero, números negativos.
Usar pytest. Archivo: tests/test_calculator.py"
```

---

## 🔌 Model Context Protocol (MCP)

### ¿Qué es MCP?

Sistema para extender capacidades de Claude con herramientas externas:
- Bases de datos
- APIs
- Herramientas de desarrollo
- Servicios externos

### Cuándo Considerar MCP:

1. **Acceso frecuente a fuentes externas**
   - Consultas a DB específica
   - API de empresa interna
   - Documentación custom

2. **Herramientas especializadas**
   - Linting custom
   - Testing frameworks propios
   - CI/CD internal tools

3. **Integración repetitiva**
   - Mismas acciones en cada proyecto
   - Workflow específico de empresa
   - Standards enforcement

### Cuándo NO Usar MCP:

- ❌ Para una única tarea
- ❌ Cuando Claude ya tiene la capacidad built-in
- ❌ Setup complejo para beneficio marginal

### 💡 MCP Servers Útiles:

- **@context7** - Documentación actualizada de librerías
- **filesystem** - Operaciones de archivos avanzadas
- **git** - Operaciones git complejas
- **database** - Queries a bases de datos

*(Consulta docs oficiales para setup: https://docs.claude.com/en/docs/mcp)*

---

## 🎯 Workflow Óptimo con Claude Code

### Inicio de Sesión:
```bash
# Si es nueva sesión o cambio mayor de contexto:
/new

# Claude lee CLAUDE.md automáticamente
# Luego confirma:
"Leí CLAUDE.md. Estamos en Phase X, Stage Y.
Trabajando en: [descripción].
¿Correcto?"
```

### Durante Desarrollo:
```bash
# Añadir archivos relevantes
/add src/main.py tests/test_main.py

# Si contexto se llena (Claude olvida cosas):
/drop archivos-no-necesarios.py

# Crear subagente para tarea independiente:
/task "Escribir docstrings para todas las funciones en utils.py"
```

### Fin de Sesión:
```bash
# Antes de cerrar:
"Actualiza .claude/01-current-phase.md con el progreso de hoy"

# Claude actualiza tracking automáticamente
```

---

## 📊 Cuándo Usar `/new`

### ✅ Usa `/new` Cuando:

- Nueva feature independiente
- Cambio de phase/stage
- Sesión larga (2+ horas)
- Claude confundido/en loop
- Nuevo día de trabajo
- Contexto corrupto

### ❌ NO Uses `/new` Cuando:

- Iterando sobre mismo código
- Bug fixing reciente
- En medio de implementación
- Decisiones recientes son valiosas

**Regla de oro:** Feature nueva = `/new` | Refinamiento = NO `/new`

---

## 🔍 Debugging Tips

### Claude No Entiende el Contexto:
```bash
# Verificar qué archivos tiene en contexto:
/list

# Asegurar que tiene los archivos correctos:
/drop *
/add .claude/00-project-brief.md
/add .claude/01-current-phase.md
/add .claude/02-stageX-rules.md
/add src/archivo-relevante.py
```

### Claude Propone Soluciones Incorrectas:
```bash
# Resetear y empezar limpio:
/new

# Luego:
"Lee .claude/00-project-brief.md y .claude/02-stageX-rules.md.
Estamos en Stage X, así que [restricciones específicas].
Propón solución siguiendo esas reglas."
```

### Claude Olvida Decisiones Recientes:
```bash
# NO uses /new
# En su lugar, recuérdale:
"Hace 10 minutos decidimos usar X en lugar de Y porque [razón].
Continúa con esa decisión."
```

---

## 💡 Pro Tips

1. **Keep Context Lean**
   - Solo añade archivos que necesitas AHORA
   - Usa `/drop` frecuentemente
   - Menos contexto = respuestas más focused

2. **Use Stage Rules**
   - Siempre referencia el stage actual
   - "Estamos en Stage 1, mantén simple"
   - Ayuda a Claude a auto-corregir

3. **Document Decisions**
   - Update `.claude/01-current-phase.md` regularmente
   - Es tu memoria persistente
   - CLAUDE.md = configuración, 01-current-phase.md = estado

4. **Batch Similar Tasks**
   - Feature A → commit → `/new` → Feature B
   - Límites naturales entre features

5. **When Stuck**
   - Consulta `docs/PROMPT_LIBRARY.md`
   - Hay templates para situaciones comunes
   - Copy-paste y personaliza

---

## 📚 Recursos

- **Claude Code Docs:** https://docs.claude.com/en/docs/claude-code
- **MCP Documentation:** https://docs.claude.com/en/docs/mcp
- **Prompt Library:** `docs/PROMPT_LIBRARY.md` (en este proyecto)
- **Workflow Guide:** `docs/QUICK_START.md` (en este proyecto)

---

*Generated by Claude Prompt Library*
*Keep this file updated as you discover new patterns and workflows*
