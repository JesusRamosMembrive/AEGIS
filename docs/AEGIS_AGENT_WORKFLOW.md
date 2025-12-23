# AEGIS v2 - Flujo de Trabajo con Agentes

Este documento describe cómo usar el UML Editor de AEGIS junto con Claude Code u otros agentes de programación.

## Filosofía

AEGIS separa claramente los roles:
- **Humano (Arquitecto)**: Define la estructura en el editor UML
- **Agente (Implementador)**: Recibe el XML y genera código

El XML exportado es el **contrato** entre arquitecto y agente. No necesitas un agente embebido - la terminal te da máximo control.

## Flujo de Trabajo Recomendado

```
┌─────────────────────────────────────────────────────────────────┐
│  1. DISEÑO (AEGIS UML Editor)                                   │
│     - Crear clases, interfaces, enums                           │
│     - Definir métodos con parámetros, tipos, descripciones      │
│     - Añadir preconditions, postconditions, hints               │
│     - Especificar test cases esperados                          │
│     - Validar (panel de validación muestra errores/warnings)    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. EXPORTAR XML                                                │
│     - Click en "Export" → pestaña "Export"                      │
│     - "Copy to Clipboard" o "Download XML"                      │
│     - El XML contiene toda la especificación semántica          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. TERMINAL CON CLAUDE CODE                                    │
│     - Abrir terminal en tu proyecto                             │
│     - Ejecutar: claude                                          │
│     - Pegar el XML con el prompt template adecuado              │
│     - El agente implementa directamente en tu proyecto          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. VALIDAR E ITERAR                                            │
│     - Revisar código generado                                   │
│     - Ejecutar tests                                            │
│     - Dar feedback al agente si necesita ajustes                │
│     - Repetir hasta satisfacción                                │
└─────────────────────────────────────────────────────────────────┘
```

## Prompt Templates

### Template 1: Implementar Proyecto Completo

```
Implementa el siguiente proyecto UML. El XML contiene la especificación completa
incluyendo clases, métodos, tipos, preconditions, postconditions y test cases.

Instrucciones:
1. Crea los archivos en la estructura apropiada para el lenguaje indicado
2. Implementa cada clase/interface/enum según la especificación
3. Respeta los tipos, visibilidades y firmas exactamente
4. Implementa la lógica siguiendo las preconditions/postconditions
5. Considera los hints y edge cases documentados
6. Genera los tests especificados en cada método

XML del proyecto:
```xml
[PEGAR XML AQUÍ]
```
```

### Template 2: Implementar Una Clase Específica

```
Implementa la clase [NOMBRE_CLASE] del siguiente proyecto UML.
Solo necesito esta clase, no el resto del proyecto.

Contexto: El proyecto usa [LENGUAJE] y la clase debe integrarse con
las otras clases/interfaces definidas en el XML.

XML del proyecto:
```xml
[PEGAR XML AQUÍ]
```

Genera solo el archivo para [NOMBRE_CLASE] con su implementación completa.
```

### Template 3: Generar Solo Tests

```
Genera los tests para el siguiente proyecto UML.
Cada método tiene especificados sus test cases en el XML.

Instrucciones:
1. Usa el framework de testing estándar del lenguaje (pytest, jest, etc.)
2. Implementa cada test case documentado
3. Incluye tests para los edge cases mencionados en hints
4. Organiza los tests por clase/módulo

XML del proyecto:
```xml
[PEGAR XML AQUÍ]
```
```

### Template 4: Implementar Método Específico

```
Implementa el método [NOMBRE_MÉTODO] de la clase [NOMBRE_CLASE].
El XML contiene la especificación completa del método incluyendo:
- Parámetros y tipos
- Preconditions y postconditions
- Hints y edge cases
- Test cases esperados

XML del proyecto:
```xml
[PEGAR XML AQUÍ]
```

Solo necesito la implementación de ese método específico.
```

### Template 5: Refactoring Guiado por UML

```
Tengo código existente que necesita ajustarse a la siguiente especificación UML.
Refactoriza el código para que cumpla exactamente con la estructura definida.

Código actual:
```[LENGUAJE]
[PEGAR CÓDIGO ACTUAL]
```

Nueva especificación UML:
```xml
[PEGAR XML AQUÍ]
```

Ajusta el código para cumplir con la nueva especificación manteniendo
la funcionalidad existente donde sea compatible.
```

### Template 6: Validar Implementación contra UML

```
Verifica que la siguiente implementación cumple con la especificación UML.
Reporta cualquier discrepancia en:
- Firmas de métodos (tipos, parámetros)
- Visibilidades
- Relaciones entre clases
- Lógica vs preconditions/postconditions

Implementación actual:
```[LENGUAJE]
[PEGAR CÓDIGO]
```

Especificación UML:
```xml
[PEGAR XML AQUÍ]
```
```

## Estructura del XML Exportado

El XML de AEGIS está optimizado para LLMs con tags semánticos claros:

```xml
<uml-project name="ProjectName" version="1.0" language="python">
  <module name="main">
    <classes>
      <class name="ClassName" visibility="public">
        <description>Descripción de la clase</description>
        <attributes>
          <attribute name="attr" type="string" visibility="private" />
        </attributes>
        <methods>
          <method name="methodName" visibility="public" static="false">
            <description>Qué hace el método</description>
            <returns type="ReturnType" />
            <parameters>
              <param name="p1" type="Type1" />
            </parameters>
            <preconditions>
              <condition>Condición que debe cumplirse antes</condition>
            </preconditions>
            <postconditions>
              <condition>Estado garantizado después</condition>
            </postconditions>
            <throws>
              <exception type="ErrorType">Cuándo se lanza</exception>
            </throws>
            <hints>
              <edge_case>Caso especial a considerar</edge_case>
              <performance>Consideración de rendimiento</performance>
            </hints>
            <tests>
              <test type="success">should do X when Y</test>
              <test type="error">should throw when Z</test>
            </tests>
          </method>
        </methods>
      </class>
    </classes>
    <interfaces>...</interfaces>
    <enums>...</enums>
    <structs>...</structs>
    <relationships>
      <relationship type="inheritance" from="Child" to="Parent" />
    </relationships>
  </module>
</uml-project>
```

## Tips para Mejores Resultados

### 1. Sé Específico en Descripciones
```xml
<!-- Malo -->
<description>Procesa datos</description>

<!-- Bueno -->
<description>Filtra usuarios activos de los últimos 30 días
y los ordena por fecha de último acceso descendente</description>
```

### 2. Usa Preconditions/Postconditions
```xml
<preconditions>
  <condition>user_id debe existir en la base de datos</condition>
  <condition>user debe tener rol ADMIN o ser el propietario</condition>
</preconditions>
<postconditions>
  <condition>El recurso queda marcado como eliminado (soft delete)</condition>
  <condition>Se emite evento ResourceDeleted</condition>
</postconditions>
```

### 3. Documenta Edge Cases en Hints
```xml
<hints>
  <edge_case>Si la lista está vacía, retornar lista vacía sin error</edge_case>
  <edge_case>Strings numéricos como "123" deben convertirse a número</edge_case>
  <edge_case>None/null se trata como valor ausente, no como error</edge_case>
</hints>
```

### 4. Define Test Cases Concretos
```xml
<tests>
  <test type="success">should return [1,3,5] when input is [1,2,3,4,5]</test>
  <test type="edge">should return [] when input is []</test>
  <test type="edge">should handle mixed types [1,"2",3,"four"]</test>
  <test type="error">should raise TypeError when input is None</test>
</tests>
```

### 5. Usa el Lenguaje Correcto
El `targetLanguage` del proyecto afecta cómo el agente genera código:
- `python`: Usa type hints, pytest, snake_case
- `typescript`: Usa interfaces, jest, camelCase
- `cpp`: Usa headers, catch2, snake_case

## Iteración y Feedback

Cuando el código generado no es exactamente lo que necesitas:

1. **Sé específico**: "El método X debería usar recursión en lugar de iteración"
2. **Referencia el UML**: "Según el postcondition, debería emitir un evento"
3. **Muestra el error**: "El test Y falla con este mensaje: ..."
4. **Pide alternativas**: "Dame 2 formas diferentes de implementar Z"

## Ejemplo Completo

### 1. Diseñas en AEGIS:
- Clase `MathOperations` con métodos `add`, `subtract`, `multiply`, `divide`
- Cada método tiene parámetros tipados y test cases

### 2. Exportas XML (simplificado):
```xml
<uml-project name="Calculator" language="python">
  <module name="main">
    <classes>
      <class name="MathOperations">
        <methods>
          <method name="divide" visibility="public" static="true">
            <returns type="float" />
            <parameters>
              <param name="a" type="float" />
              <param name="b" type="float" />
            </parameters>
            <preconditions>
              <condition>b != 0</condition>
            </preconditions>
            <throws>
              <exception type="ZeroDivisionError">when b is 0</exception>
            </throws>
            <tests>
              <test type="success">divide(10, 2) should return 5.0</test>
              <test type="error">divide(10, 0) should raise ZeroDivisionError</test>
            </tests>
          </method>
        </methods>
      </class>
    </classes>
  </module>
</uml-project>
```

### 3. En terminal con Claude Code:
```
$ claude
> Implementa el siguiente proyecto UML...
[pegar XML]
```

### 4. Claude Code genera:
```python
# math_operations.py
class MathOperations:
    @staticmethod
    def divide(a: float, b: float) -> float:
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return a / b

# test_math_operations.py
import pytest
from math_operations import MathOperations

def test_divide_success():
    assert MathOperations.divide(10, 2) == 5.0

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        MathOperations.divide(10, 0)
```

---

*AEGIS v2 - Model-Driven Development con máximo control*
