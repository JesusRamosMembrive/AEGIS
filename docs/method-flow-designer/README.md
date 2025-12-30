# Method Flow Designer - Activity Diagram Integration

**Fecha**: 2025-12-30
**Objetivo**: Unificar diseño UML con pipeline de ejecución

---

## Resumen

El Method Flow Designer permite diseñar el flujo interno de cada método usando Activity Diagrams (UML). Esto completa el "Santo Grial" de la programación asistida:

1. **Estructura** (clases, interfaces, métodos) → UML Editor existente
2. **Comportamiento** (contratos, pre/postcondiciones) → Inspector existente
3. **Flujo interno** (algoritmo del método) → **NUEVO: Activity Diagram**

El resultado es un XML completo que un agente de programación puede usar para implementar código que sigue exactamente la especificación del humano.

---

## Arquitectura

### Interfaz de Usuario

- **Drawer desde abajo**: 60% del viewport, redimensionable
- **UML Editor visible arriba**: Permite ver el contexto mientras se edita el flujo
- **Acceso**: Botón "Design Flow" en el MethodEditor del Inspector

### Flujo de Uso

```
1. Abrir /uml-editor
2. Seleccionar o crear una clase
3. Añadir/seleccionar un método
4. Click en "Design Flow (Activity Diagram)"
5. Se abre el drawer con el canvas de Activity Diagram
6. Añadir nodos desde la toolbar
7. Conectar nodos arrastrando desde los handles
8. Cerrar con ESC o botón X
```

---

## Componentes Implementados

### Estructura de Archivos

```
frontend/src/components/uml-editor/flow-editor/
├── FlowEditorDrawer.tsx      # Drawer contenedor (60% viewport)
├── ActivityCanvas.tsx        # Canvas React Flow
├── FlowEditorToolbar.tsx     # Paleta de nodos
├── nodes/
│   ├── InitialFlowNode.tsx   # Círculo relleno (inicio)
│   ├── FinalFlowNode.tsx     # Bull's eye (fin)
│   ├── ActionFlowNode.tsx    # Rectángulo redondeado
│   ├── DecisionFlowNode.tsx  # Diamante con branches
│   └── MergeFlowNode.tsx     # Diamante para convergencia
└── edges/
    ├── FlowEdge.tsx          # Línea sólida estándar
    └── BranchEdge.tsx        # Con colores true/false
```

### Tipos de Nodos (Activity Diagram UML)

| Nodo | Símbolo | Descripción |
|------|---------|-------------|
| Initial | ● | Punto de inicio (círculo relleno) |
| Final | ◉ | Punto final (bull's eye) |
| Action | ▢ | Paso de acción (rectángulo redondeado) |
| Decision | ◇ | Bifurcación condicional (diamante amarillo) |
| Merge | ◇ | Convergencia de flujos (diamante gris) |

### Tipos de Edges

| Edge | Estilo | Uso |
|------|--------|-----|
| Flow | Línea sólida | Flujo normal |
| Branch | Verde/Rojo | Desde Decision (true/false) |

---

## Modelo de Datos

### Nuevos Tipos en `frontend/src/api/types.ts`

```typescript
// Tipos de nodo Activity Diagram
export type ActivityNodeType =
  | "initial" | "final" | "action" | "decision" | "merge"
  | "fork" | "join" | "loop" | "call"
  | "signal_send" | "signal_receive"
  | "try_block" | "catch_block" | "note";

// Diagrama completo
export interface ActivityDiagram {
  methodId: string;
  nodes: ActivityNode[];
  edges: ActivityEdge[];
  swimlanes?: ActivitySwimlane[];
  detailLevel: "simple" | "detailed" | "pseudocode";
  lastModified?: string;
}
```

### Extensión del Store

En `frontend/src/state/useUmlEditorStore.ts`:

```typescript
// Nuevo estado
isFlowDrawerOpen: boolean;
flowEditorClassId: string | null;
flowEditorMethodId: string | null;
selectedFlowNodeId: string | null;
selectedFlowEdgeId: string | null;

// Nuevas acciones
openFlowEditor(classId, methodId)
closeFlowEditor()
initializeActivityDiagram(classId, methodId)
setActivityDiagram(classId, methodId, diagram)
addActivityNode(classId, methodId, node)
updateActivityNode(classId, methodId, nodeId, updates)
deleteActivityNode(classId, methodId, nodeId)
addActivityEdge(classId, methodId, edge)
// ... y más
```

---

## Funcionalidades

### Implementadas (Phase 1-2)

- [x] Drawer redimensionable (30%-85% viewport)
- [x] Canvas React Flow con zoom, pan, minimap
- [x] Nodos básicos: Initial, Final, Action, Decision, Merge
- [x] Edges: Flow, Branch con colores semánticos
- [x] Toolbar para añadir nodos
- [x] Drag & drop de nodos
- [x] Conexión de nodos arrastrando handles
- [x] Delete con tecla Delete/Backspace
- [x] Auto-inicialización con nodo Initial
- [x] Persistencia en store (se guarda automáticamente)
- [x] Atajos: ESC para cerrar

### Pendientes (Phases 3-7)

- [ ] Phase 3: Loop y Call nodes
- [ ] Phase 4: Fork/Join, Signal, Try/Catch nodes
- [ ] Phase 5: Swimlanes
- [ ] Phase 6: Export XML con `<activity-flow>`
- [ ] Phase 7: Validación de flujos

---

## XML Output (Futuro - Phase 6)

```xml
<method name="processOrder" visibility="public">
  <!-- Secciones existentes -->

  <activity-flow detail-level="detailed">
    <nodes>
      <initial id="n-0" />
      <action id="n-1">
        <text>Validate order</text>
        <pseudocode>for item in order.items: validate(item)</pseudocode>
      </action>
      <decision id="n-2">
        <condition>order.isValid()</condition>
      </decision>
      <final id="n-3"><return>order</return></final>
    </nodes>

    <edges>
      <flow from="n-0" to="n-1" />
      <flow from="n-1" to="n-2" />
      <branch from="n-2" to="n-3" label="true" />
    </edges>
  </activity-flow>
</method>
```

---

## Cómo Acceder

1. Ir a `/uml-editor`
2. Crear o seleccionar una clase
3. En el Inspector (panel derecho), ir a la pestaña de la clase
4. Añadir un método con "+ Add Method"
5. Seleccionar el método haciendo click
6. Scroll hasta ver el botón **"Design Flow (Activity Diagram)"**
7. Click para abrir el drawer

---

## Referencias

- **Plan original**: `.claude/plans/wondrous-sparking-flamingo.md`
- **Estado del proyecto**: `.claude/01-current-phase.md`
- **Store**: `frontend/src/state/useUmlEditorStore.ts`
- **Tipos**: `frontend/src/api/types.ts`
