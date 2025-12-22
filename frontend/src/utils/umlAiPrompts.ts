/**
 * UML AI Prompts - System prompts for AI-powered UML generation
 *
 * Contains the system prompt that instructs Ollama how to generate
 * valid UML XML from natural language descriptions.
 */

import type { UmlTargetLanguage } from "../api/types";

/**
 * Get the system prompt for UML XML generation
 * @param targetLanguage - The target language for type mapping
 */
export function getUmlGenerationSystemPrompt(targetLanguage: UmlTargetLanguage): string {
  const typeExamples = getTypeExamplesForLanguage(targetLanguage);

  return `You are a UML diagram generator. Given a description, generate ONLY valid XML following this exact format.

<uml-project name="Generated" version="1.0" language="${targetLanguage}">
  <module name="main">
    <classes>
      <class name="ClassName" visibility="public">
        <description>Brief description</description>
        <attributes>
          <attribute name="attrName" type="${typeExamples.string}" visibility="private" />
        </attributes>
        <methods>
          <method name="methodName" visibility="public" static="false">
            <returns type="${typeExamples.number}" />
            <parameters>
              <param name="a" type="${typeExamples.number}" />
            </parameters>
          </method>
        </methods>
      </class>
    </classes>
    <interfaces>
      <interface name="IName">
        <methods>
          <method name="doSomething">
            <returns type="${typeExamples.void}" />
          </method>
        </methods>
      </interface>
    </interfaces>
    <enums>
      <enum name="Status">
        <values>
          <value name="ACTIVE" />
          <value name="INACTIVE" />
        </values>
      </enum>
    </enums>
    <structs>
      <struct name="Point">
        <attributes>
          <attribute name="x" type="${typeExamples.number}" visibility="public" />
          <attribute name="y" type="${typeExamples.number}" visibility="public" />
        </attributes>
      </struct>
    </structs>
    <relationships>
      <relationship type="implementation" from="ClassName" to="IName" />
    </relationships>
  </module>
</uml-project>

IMPORTANT RULES:
1. Output ONLY the XML, no explanations, no markdown code blocks
2. Use appropriate types for ${targetLanguage}: ${typeExamples.examples}
3. Visibility options: public, private, protected
4. Relationship types: association, aggregation, composition, inheritance, implementation, dependency
5. static attribute for methods: "true" or "false"
6. Every class/interface/enum/struct MUST have a name attribute
7. If generating multiple entities, include their relationships
8. Keep descriptions brief (one sentence max)

TYPE REFERENCE FOR ${targetLanguage.toUpperCase()}:
${typeExamples.typeReference}`;
}

/**
 * Get language-specific type examples
 */
function getTypeExamplesForLanguage(language: UmlTargetLanguage): {
  string: string;
  number: string;
  boolean: string;
  void: string;
  examples: string;
  typeReference: string;
} {
  switch (language) {
    case "python":
      return {
        string: "str",
        number: "int",
        boolean: "bool",
        void: "None",
        examples: "str, int, float, bool, list, dict, None",
        typeReference: `- str: text strings
- int: integers
- float: decimal numbers
- bool: True/False
- list: arrays/lists
- dict: dictionaries/maps
- None: no return value
- Optional[T]: nullable type
- List[T]: typed list
- Dict[K, V]: typed dictionary`,
      };

    case "typescript":
      return {
        string: "string",
        number: "number",
        boolean: "boolean",
        void: "void",
        examples: "string, number, boolean, void, Array<T>, object",
        typeReference: `- string: text strings
- number: integers and decimals
- boolean: true/false
- void: no return value
- null: null value
- undefined: undefined value
- Array<T>: typed arrays
- object: generic object
- Record<K, V>: typed maps
- Promise<T>: async return`,
      };

    case "cpp":
      return {
        string: "std::string",
        number: "int",
        boolean: "bool",
        void: "void",
        examples: "int, float, double, bool, std::string, void",
        typeReference: `- int: integers
- float: single precision decimal
- double: double precision decimal
- bool: true/false
- char: single character
- std::string: text strings
- void: no return value
- T*: pointer to T
- T&: reference to T
- std::vector<T>: dynamic array
- std::map<K, V>: key-value map`,
      };

    default:
      return {
        string: "string",
        number: "number",
        boolean: "boolean",
        void: "void",
        examples: "string, number, boolean, void",
        typeReference: "Use standard types for your language",
      };
  }
}

/**
 * Format user prompt for better AI understanding
 */
export function formatUserPrompt(description: string): string {
  return `Generate UML XML for the following description:

${description}

Remember: Output ONLY the XML, nothing else.`;
}
