# Diagnóstico: Saltos de línea en Terminal PTY

## El Problema

Cuando ejecutas agentes como Claude Code, Gemini CLI o Codex CLI en el terminal embebido, cada carácter que introduces genera un salto de línea. También hay saltos de línea periódicos durante la ejecución.

## Causa Raíz

El PTY (pseudo-terminal) recibe dimensiones incorrectas, típicamente `cols=1`. Cuando el PTY cree que solo tiene 1 columna de ancho, cada carácter que escribes causa un "line wrap" automático.

### ¿Por qué ocurre?

El cálculo de dimensiones en `FitAddon.fit()` es:

```
cols = Math.floor(containerWidth / characterWidth)
rows = Math.floor(containerHeight / lineHeight)
```

Si el contenedor tiene `width=0` o dimensiones muy pequeñas cuando se ejecuta `fit()`:

```
cols = Math.floor(0 / 9) = 0  → se normaliza a 1
```

### La diferencia entre los componentes

| RemoteTerminalView (FUNCIONA) | GeminiTerminalEmbed (PROBLEMA) |
|-------------------------------|--------------------------------|
| `height: 600px` (fijo) | `flex: 1` (dinámico) |
| Página dedicada | Embebido en componente complejo |
| Sin re-renders del padre | ClaudeAgentView tiene mucho estado |
| Contenedor siempre listo | Race condition con layout |

## Las Correcciones Aplicadas

### 1. CSS: Altura Explícita vs Flex

**Antes (problemático):**
```css
.gemini-terminal-content {
  flex: 1;
  min-height: 400px;
}
```

**Después (corregido):**
```css
.gemini-terminal-content {
  height: 400px;
  min-height: 350px;
}
```

### 2. Esperar a que el Contenedor Esté Listo

```typescript
// Nuevo estado para tracking
const [containerReady, setContainerReady] = useState(false);

// Observar hasta que tenga dimensiones válidas
useEffect(() => {
  const container = terminalRef.current;
  
  const checkDimensions = () => {
    const rect = container.getBoundingClientRect();
    if (rect.width >= 100 && rect.height >= 100) {
      setContainerReady(true);
      return true;
    }
    return false;
  };

  if (checkDimensions()) return;

  // ResizeObserver como fallback
  const observer = new ResizeObserver(() => {
    if (checkDimensions()) observer.disconnect();
  });
  observer.observe(container);
}, []);

// Inicializar terminal SOLO cuando containerReady=true
useEffect(() => {
  if (!containerReady || !terminalRef.current) return;
  // ... inicialización
}, [containerReady]);
```

### 3. Validación de Dimensiones Antes de Enviar

```typescript
const MIN_VALID_COLS = 40;
const MIN_VALID_ROWS = 10;
const DEFAULT_COLS = 80;
const DEFAULT_ROWS = 24;

const safeFit = (): { cols: number; rows: number } => {
  const rect = container.getBoundingClientRect();
  
  // Validar contenedor
  if (rect.width < 100 || rect.height < 100) {
    return { cols: DEFAULT_COLS, rows: DEFAULT_ROWS };
  }

  fitAddon.fit();
  
  const { cols, rows } = terminal;
  
  // Validar resultado
  if (cols < MIN_VALID_COLS || rows < MIN_VALID_ROWS) {
    terminal.resize(DEFAULT_COLS, DEFAULT_ROWS);
    return { cols: DEFAULT_COLS, rows: DEFAULT_ROWS };
  }

  return { cols, rows };
};
```

### 4. Envío de Resize Después de Conexión

```typescript
socket.onopen = () => {
  // Esperar a que el DOM esté estable
  requestAnimationFrame(() => {
    const dims = safeFit();
    socket.send(`__RESIZE__:${dims.cols}:${dims.rows}`);
  });
};
```

### 5. Debounce en ResizeObserver

```typescript
let resizeTimeout: ReturnType<typeof setTimeout> | null = null;

disposablesRef.current.observer = new ResizeObserver(() => {
  if (resizeTimeout) clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => {
    sendResize(socket);
  }, 150); // 150ms debounce para evitar spam
});
```

## Solución Alternativa: Backend

También puedes añadir protección en el backend (`pty_shell.py`):

```python
def resize(self, cols: int, rows: int) -> None:
    """
    Resize terminal with validation
    """
    # Validar dimensiones mínimas
    MIN_COLS = 40
    MIN_ROWS = 10
    
    if cols < MIN_COLS:
        logger.warning(f"Invalid cols={cols}, using minimum {MIN_COLS}")
        cols = MIN_COLS
    if rows < MIN_ROWS:
        logger.warning(f"Invalid rows={rows}, using minimum {MIN_ROWS}")
        rows = MIN_ROWS
    
    self.cols = cols
    self.rows = rows
    self._set_winsize(cols, rows)
    logger.debug(f"Terminal resized to {cols}x{rows}")
```

## Los Saltos de Línea Periódicos

Los agentes TUI (Claude Code, etc.) usan "escape sequences" para:
- Limpiar líneas: `\x1b[2K`
- Mover cursor arriba: `\x1b[1A`
- Re-dibujar la interfaz

Si las dimensiones del PTY no coinciden con el terminal visual, estos redraws causan artefactos. La solución es asegurar que las dimensiones sean siempre correctas y sincronizadas.

## Checklist de Debugging

1. **Verificar dimensiones en consola:**
   ```typescript
   console.log(`Terminal: ${terminal.cols}x${terminal.rows}`);
   console.log(`Container: ${rect.width}x${rect.height}`);
   ```

2. **Verificar mensaje __RESIZE__ en backend:**
   ```python
   logger.info(f"Resize received: {cols}x{rows}")
   ```

3. **Asegurar que el CSS del padre tiene dimensiones:**
   ```css
   .parent-container {
     height: 100vh; /* o valor fijo */
     display: flex;
     flex-direction: column;
   }
   ```

4. **Evitar re-renders excesivos:**
   - Usar `React.memo()` para el componente terminal
   - Mover estado no relacionado fuera del componente padre

## Archivos Modificados

- `GeminiTerminalEmbed_fixed.tsx` - Versión corregida completa
- Opcional: `pty_shell.py` - Añadir validación de dimensiones en backend
