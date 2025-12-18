#include "tokenizers/python_normalizer.hpp"
#include "tokenizers/js_normalizer.hpp"
#include "tokenizers/cpp_normalizer.hpp"
#include <cctype>
#include <algorithm>

namespace aegis::similarity {

PythonNormalizer::PythonNormalizer() {
    // Python 3 keywords
    keywords_ = {
        "False", "None", "True", "and", "as", "assert", "async", "await",
        "break", "class", "continue", "def", "del", "elif", "else", "except",
        "finally", "for", "from", "global", "if", "import", "in", "is",
        "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
        "while", "with", "yield"
    };

    // Built-in types (normalized differently for better Type-2 detection)
    builtin_types_ = {
        "int", "float", "str", "bool", "list", "dict", "set", "tuple",
        "bytes", "bytearray", "complex", "frozenset", "object", "type",
        "range", "slice", "memoryview", "property", "classmethod",
        "staticmethod", "super"
    };

    // Operators and punctuation
    operators_ = {
        "+", "-", "*", "/", "//", "%", "**", "@",
        "==", "!=", "<", ">", "<=", ">=",
        "&", "|", "^", "~", "<<", ">>",
        "=", "+=", "-=", "*=", "/=", "//=", "%=", "**=", "@=",
        "&=", "|=", "^=", "<<=", ">>=",
        "(", ")", "[", "]", "{", "}",
        ",", ":", ";", ".", "->", "...",
        "\\",  // Line continuation
    };
}

TokenizedFile PythonNormalizer::normalize(std::string_view source) {
    TokenizedFile result;
    result.path = "";  // Will be set by caller

    TokenizerState state;
    state.source = source;

    LineMetrics metrics{};

    while (!state.eof()) {
        // Track line changes for metrics
        update_line_metrics(state, metrics);

        char c = state.peek();

        // Handle indentation at line start
        if (state.at_line_start && c != '\n' && c != '#') {
            process_indentation(state, result);
            if (state.eof()) break;
            c = state.peek();
        }

        // Process each token type (early return pattern)
        if (skip_whitespace(state, c)) continue;
        if (process_newline(state, c, result)) continue;
        if (process_comment(state, c, metrics)) continue;
        if (process_import(state, metrics)) continue;
        if (process_string_or_docstring(state, c, result, metrics)) continue;
        if (process_number(state, c, result, metrics)) continue;
        if (process_identifier(state, c, result, metrics)) continue;
        if (process_operator(state, c, result, metrics)) continue;

        // Unknown character - skip
        state.advance();
    }

    // Handle final line metrics (force processing of current line even without line change)
    if (metrics.current_line > 0) {
        if (metrics.line_has_code) {
            metrics.code_lines++;
        } else if (metrics.line_has_comment) {
            metrics.comment_lines++;
        } else {
            metrics.blank_lines++;
        }
    }

    // Handle remaining dedents at end of file
    emit_remaining_dedents(state, result);

    // Finalize metrics
    finalize_metrics(state, metrics, result);

    return result;
}

NormalizedToken PythonNormalizer::parse_string(TokenizerState& state) {
    NormalizedToken tok;
    tok.type = TokenType::STRING_LITERAL;
    tok.line = state.line;
    tok.column = state.column;

    char quote = state.advance();
    bool triple = false;

    // Check for triple-quoted string
    if (state.peek() == quote && state.peek_next() == quote) {
        state.advance();
        state.advance();
        triple = true;
    }

    std::string value;
    size_t start_pos = state.pos;

    while (!state.eof()) {
        char c = state.peek();

        if (triple) {
            // Triple-quoted: look for three quotes
            if (c == quote && state.peek_next() == quote) {
                size_t pos = state.pos + 2;
                if (pos < state.source.size() && state.source[pos] == quote) {
                    state.advance();
                    state.advance();
                    state.advance();
                    break;
                }
            }
        } else {
            // Single-quoted: end at matching quote (not escaped)
            if (c == quote) {
                state.advance();
                break;
            }
            if (c == '\n') {
                // Unterminated string
                break;
            }
        }

        // Handle escape sequences
        if (c == '\\' && !state.eof()) {
            state.advance();
            if (!state.eof()) {
                state.advance();
            }
            continue;
        }

        value += c;
        state.advance();
    }

    tok.length = static_cast<uint16_t>(state.pos - start_pos + (triple ? 3 : 1));
    tok.original_hash = hash_string(value);
    tok.normalized_hash = hash_placeholder(TokenType::STRING_LITERAL);

    return tok;
}

// -----------------------------------------------------------------------------
// Number parsing helpers (reduce cyclomatic complexity)
// -----------------------------------------------------------------------------

bool PythonNormalizer::parse_hex_number(TokenizerState& state, std::string& value) {
    if (state.peek() != '0' || state.eof()) return false;
    char next = state.peek_next();
    if (next != 'x' && next != 'X') return false;

    value += state.advance();  // '0'
    value += state.advance();  // 'x' or 'X'
    while (!state.eof() && (is_hex_digit(state.peek()) || state.peek() == '_')) {
        if (state.peek() != '_') value += state.peek();
        state.advance();
    }
    return true;
}

bool PythonNormalizer::parse_binary_number(TokenizerState& state, std::string& value) {
    if (state.peek() != '0' || state.eof()) return false;
    char next = state.peek_next();
    if (next != 'b' && next != 'B') return false;

    value += state.advance();  // '0'
    value += state.advance();  // 'b' or 'B'
    while (!state.eof() && (state.peek() == '0' || state.peek() == '1' || state.peek() == '_')) {
        if (state.peek() != '_') value += state.peek();
        state.advance();
    }
    return true;
}

bool PythonNormalizer::parse_octal_number(TokenizerState& state, std::string& value) {
    if (state.peek() != '0' || state.eof()) return false;
    char next = state.peek_next();
    if (next != 'o' && next != 'O') return false;

    value += state.advance();  // '0'
    value += state.advance();  // 'o' or 'O'
    while (!state.eof() && ((state.peek() >= '0' && state.peek() <= '7') || state.peek() == '_')) {
        if (state.peek() != '_') value += state.peek();
        state.advance();
    }
    return true;
}

void PythonNormalizer::parse_integer_part(TokenizerState& state, std::string& value) {
    // Handle leading zero without special prefix
    if (state.peek() == '0') {
        value += state.advance();
        return;
    }
    // Regular integer digits
    while (!state.eof() && (is_digit(state.peek()) || state.peek() == '_')) {
        if (state.peek() != '_') value += state.peek();
        state.advance();
    }
}

void PythonNormalizer::parse_decimal_part(TokenizerState& state, std::string& value) {
    if (state.peek() != '.' || !is_digit(state.peek_next())) return;

    value += state.advance();  // '.'
    while (!state.eof() && (is_digit(state.peek()) || state.peek() == '_')) {
        if (state.peek() != '_') value += state.peek();
        state.advance();
    }
}

void PythonNormalizer::parse_exponent_part(TokenizerState& state, std::string& value) {
    if (state.peek() != 'e' && state.peek() != 'E') return;

    value += state.advance();  // 'e' or 'E'
    if (state.peek() == '+' || state.peek() == '-') {
        value += state.advance();
    }
    while (!state.eof() && (is_digit(state.peek()) || state.peek() == '_')) {
        if (state.peek() != '_') value += state.peek();
        state.advance();
    }
}

void PythonNormalizer::skip_complex_suffix(TokenizerState& state, std::string& value) {
    if (state.peek() == 'j' || state.peek() == 'J') {
        value += state.advance();
    }
}

// -----------------------------------------------------------------------------
// Main parse_number (refactored to use helpers)
// -----------------------------------------------------------------------------

NormalizedToken PythonNormalizer::parse_number(TokenizerState& state) {
    NormalizedToken tok;
    tok.type = TokenType::NUMBER_LITERAL;
    tok.line = state.line;
    tok.column = state.column;
    std::string value;
    size_t start_pos = state.pos;

    // Try special number formats first (hex, binary, octal)
    bool is_special = parse_hex_number(state, value) ||
                      parse_binary_number(state, value) ||
                      parse_octal_number(state, value);

    // Regular number if no special format matched
    if (!is_special) {
        parse_integer_part(state, value);
    }

    // Decimal and exponent parts (only for regular numbers)
    if (!is_special) {
        parse_decimal_part(state, value);
        parse_exponent_part(state, value);
    }

    // Complex number suffix (j/J)
    skip_complex_suffix(state, value);

    tok.length = static_cast<uint16_t>(state.pos - start_pos);
    tok.original_hash = hash_string(value);
    tok.normalized_hash = hash_placeholder(TokenType::NUMBER_LITERAL);
    return tok;
}

NormalizedToken PythonNormalizer::parse_identifier_or_keyword(TokenizerState& state) {
    NormalizedToken tok;
    tok.line = state.line;
    tok.column = state.column;

    std::string value;
    size_t start_pos = state.pos;

    while (!state.eof() && is_identifier_char(state.peek())) {
        value += state.advance();
    }

    tok.length = static_cast<uint16_t>(state.pos - start_pos);
    tok.original_hash = hash_string(value);

    // Check if it's a keyword
    if (keywords_.count(value)) {
        tok.type = TokenType::KEYWORD;
        tok.normalized_hash = tok.original_hash;  // Keywords keep their hash
    }
    // Check if it's a built-in type
    else if (builtin_types_.count(value)) {
        tok.type = TokenType::TYPE;
        tok.normalized_hash = hash_placeholder(TokenType::TYPE);
    }
    // Regular identifier
    else {
        tok.type = TokenType::IDENTIFIER;
        tok.normalized_hash = hash_placeholder(TokenType::IDENTIFIER);
    }

    return tok;
}

// -----------------------------------------------------------------------------
// Operator parsing helpers (reduce cyclomatic complexity of parse_operator)
// -----------------------------------------------------------------------------

bool PythonNormalizer::try_match_three_char_operator(TokenizerState& state, std::string& value) {
    if (state.pos + 2 >= state.source.size()) return false;

    std::string three(state.source.substr(state.pos, 3));
    if (three == "..." || three == "<<=" || three == ">>=" ||
        three == "**=" || three == "//=") {
        value = three;
        state.advance();
        state.advance();
        state.advance();
        return true;
    }
    return false;
}

bool PythonNormalizer::try_match_two_char_operator(TokenizerState& state, std::string& value) {
    if (state.pos + 1 >= state.source.size()) return false;

    std::string two(state.source.substr(state.pos, 2));
    if (two == "==" || two == "!=" || two == "<=" || two == ">=" ||
        two == "+=" || two == "-=" || two == "*=" || two == "/=" ||
        two == "%=" || two == "&=" || two == "|=" || two == "^=" ||
        two == "**" || two == "//" || two == "<<" || two == ">>" ||
        two == "->" || two == "@=") {
        value = two;
        state.advance();
        state.advance();
        return true;
    }
    return false;
}

bool PythonNormalizer::is_punctuation(const std::string& op) {
    return op == "(" || op == ")" || op == "[" || op == "]" ||
           op == "{" || op == "}" || op == "," || op == ":" ||
           op == ";" || op == ".";
}

// -----------------------------------------------------------------------------
// Main parse_operator (refactored to use helpers)
// -----------------------------------------------------------------------------

NormalizedToken PythonNormalizer::parse_operator(TokenizerState& state) {
    NormalizedToken tok;
    tok.line = state.line;
    tok.column = state.column;
    std::string value;
    size_t start_pos = state.pos;

    // Try to match longest operator first (3-char, then 2-char)
    if (!try_match_three_char_operator(state, value)) {
        if (!try_match_two_char_operator(state, value)) {
            // Single character operator
            value = state.advance();
        }
    }

    tok.length = static_cast<uint16_t>(state.pos - start_pos);
    tok.original_hash = hash_string(value);
    tok.normalized_hash = tok.original_hash;  // Operators keep their hash
    tok.type = is_punctuation(value) ? TokenType::PUNCTUATION : TokenType::OPERATOR;

    return tok;
}

void PythonNormalizer::skip_comment(TokenizerState& state) {
    while (!state.eof() && state.peek() != '\n') {
        state.advance();
    }
}

void PythonNormalizer::skip_docstring(TokenizerState& state, char quote) {
    // Skip the opening triple quotes
    state.advance();  // First quote
    state.advance();  // Second quote
    state.advance();  // Third quote

    // Skip until we find the closing triple quotes
    while (!state.eof()) {
        char c = state.peek();

        // Check for closing triple quotes
        if (c == quote) {
            if (state.pos + 2 < state.source.size() &&
                state.source[state.pos + 1] == quote &&
                state.source[state.pos + 2] == quote) {
                state.advance();  // First closing quote
                state.advance();  // Second closing quote
                state.advance();  // Third closing quote
                return;
            }
        }

        // Handle escape sequences
        if (c == '\\' && !state.eof()) {
            state.advance();
            if (!state.eof()) {
                state.advance();
            }
            continue;
        }

        state.advance();
    }
}

bool PythonNormalizer::is_docstring_context(const std::vector<NormalizedToken>& tokens) const {
    // A docstring appears in these contexts:
    // 1. At the very start of a file (module docstring)
    // 2. Immediately after 'def name(...):' (function docstring)
    // 3. Immediately after 'class name:' or 'class name(...):' (class docstring)

    if (tokens.empty()) {
        // Start of file - this is a module docstring
        return true;
    }

    // Look backwards through tokens, skipping NEWLINE and INDENT
    for (auto it = tokens.rbegin(); it != tokens.rend(); ++it) {
        if (it->type == TokenType::NEWLINE || it->type == TokenType::INDENT) {
            continue;
        }

        // If we find a colon, this could be after def/class
        if (it->type == TokenType::PUNCTUATION) {
            // Check if the original hash matches ':'
            if (it->original_hash == hash_string(":")) {
                return true;  // After a colon = docstring context
            }
        }

        // Any other token means this is not a docstring context
        return false;
    }

    // Only found NEWLINE/INDENT tokens - start of file effectively
    return true;
}

bool PythonNormalizer::is_import_statement(const TokenizerState& state) const {
    // Check if current position starts with "import " or "from "
    // This is called at the start of a logical line (after indentation)

    std::string_view remaining = state.source.substr(state.pos);

    // Check for "import "
    if (remaining.size() >= 7 && remaining.substr(0, 7) == "import ") {
        return true;
    }

    // Check for "from "
    if (remaining.size() >= 5 && remaining.substr(0, 5) == "from ") {
        return true;
    }

    return false;
}

void PythonNormalizer::skip_to_end_of_line(TokenizerState& state) {
    // Skip everything until newline (handles multi-line imports with backslash)
    while (!state.eof()) {
        char c = state.peek();

        if (c == '\n') {
            // Don't consume the newline - let the main loop handle it
            return;
        }

        // Handle line continuation
        if (c == '\\') {
            state.advance();
            if (!state.eof() && state.peek() == '\n') {
                state.advance();  // Skip the newline after backslash
                continue;  // Continue reading the next line
            }
            continue;
        }

        // Handle parentheses for multi-line imports: from x import (a, b, c)
        if (c == '(') {
            state.advance();
            // Skip until closing paren
            int depth = 1;
            while (!state.eof() && depth > 0) {
                char inner = state.peek();
                if (inner == '(') depth++;
                else if (inner == ')') depth--;
                state.advance();
            }
            continue;
        }

        state.advance();
    }
}

std::vector<NormalizedToken> PythonNormalizer::handle_indentation(
    TokenizerState& state,
    size_t current_indent
) {
    std::vector<NormalizedToken> tokens;
    size_t prev_indent = state.indent_stack.back();

    if (current_indent > prev_indent) {
        state.indent_stack.push_back(current_indent);
        NormalizedToken tok;
        tok.type = TokenType::INDENT;
        tok.original_hash = hash_string("INDENT");
        tok.normalized_hash = tok.original_hash;
        tok.line = state.line;
        tok.column = 1;
        tok.length = static_cast<uint16_t>(current_indent);
        tokens.push_back(tok);
    } else if (current_indent < prev_indent) {
        while (!state.indent_stack.empty() &&
               state.indent_stack.back() > current_indent) {
            state.indent_stack.pop_back();
            NormalizedToken tok;
            tok.type = TokenType::DEDENT;
            tok.original_hash = hash_string("DEDENT");
            tok.normalized_hash = tok.original_hash;
            tok.line = state.line;
            tok.column = 1;
            tok.length = 0;
            tokens.push_back(tok);
        }
    }

    return tokens;
}

// ============================================================================
// Refactored processing methods (reduce cyclomatic complexity)
// ============================================================================

void PythonNormalizer::update_line_metrics(TokenizerState& state, LineMetrics& metrics) {
    if (state.line != metrics.current_line) {
        if (metrics.current_line > 0) {
            if (metrics.line_has_code) {
                metrics.code_lines++;
            } else if (metrics.line_has_comment) {
                metrics.comment_lines++;
            } else {
                metrics.blank_lines++;
            }
        }
        metrics.current_line = state.line;
        metrics.line_has_code = false;
        metrics.line_has_comment = false;
    }
}

bool PythonNormalizer::skip_whitespace(TokenizerState& state, char c) {
    if (c == ' ' || c == '\t') {
        state.advance();
        return true;
    }
    return false;
}

bool PythonNormalizer::process_newline(TokenizerState& state, char c, TokenizedFile& result) {
    if (c != '\n') {
        return false;
    }
    // Emit newline token for significant line breaks
    if (!result.tokens.empty() && result.tokens.back().type != TokenType::NEWLINE) {
        NormalizedToken tok;
        tok.type = TokenType::NEWLINE;
        tok.original_hash = hash_string("\n");
        tok.normalized_hash = tok.original_hash;
        tok.line = state.line;
        tok.column = state.column;
        tok.length = 1;
        result.tokens.push_back(tok);
    }
    state.advance();
    return true;
}

bool PythonNormalizer::process_comment(TokenizerState& state, char c, LineMetrics& metrics) {
    if (c != '#') {
        return false;
    }
    metrics.line_has_comment = true;
    skip_comment(state);
    return true;
}

bool PythonNormalizer::process_import(TokenizerState& state, LineMetrics& metrics) {
    if (metrics.line_has_code || !is_import_statement(state)) {
        return false;
    }
    skip_to_end_of_line(state);
    metrics.line_has_code = true;  // Count as code line but don't emit tokens
    return true;
}

bool PythonNormalizer::process_string_or_docstring(TokenizerState& state, char c, TokenizedFile& result, LineMetrics& metrics) {
    // Check for direct string literals
    if (c == '"' || c == '\'') {
        // Check if this is a potential docstring (triple-quoted at start of logical line)
        bool is_triple = (state.peek_next() == c);
        if (is_triple && state.pos + 2 < state.source.size() && state.source[state.pos + 2] == c) {
            // It's a triple-quoted string - check if it's a docstring
            bool is_docstring = !metrics.line_has_code && is_docstring_context(result.tokens);
            if (is_docstring) {
                // Skip the docstring entirely (treat like a comment)
                skip_docstring(state, c);
                metrics.line_has_comment = true;  // Count as comment line
                return true;
            }
        }
        metrics.line_has_code = true;
        result.tokens.push_back(parse_string(state));
        return true;
    }

    // f-strings, r-strings, b-strings (single prefix)
    if ((c == 'f' || c == 'F' || c == 'r' || c == 'R' || c == 'b' || c == 'B') &&
        (state.peek_next() == '"' || state.peek_next() == '\'')) {
        metrics.line_has_code = true;
        state.advance();  // Skip prefix
        result.tokens.push_back(parse_string(state));
        return true;
    }

    // fr"" or rf"" strings (double prefix)
    if ((c == 'f' || c == 'F' || c == 'r' || c == 'R') &&
        (state.peek_next() == 'r' || state.peek_next() == 'R' ||
         state.peek_next() == 'f' || state.peek_next() == 'F')) {
        size_t pos = state.pos + 2;
        if (pos < state.source.size() && (state.source[pos] == '"' || state.source[pos] == '\'')) {
            metrics.line_has_code = true;
            state.advance();  // Skip first prefix
            state.advance();  // Skip second prefix
            result.tokens.push_back(parse_string(state));
            return true;
        }
    }

    return false;
}

bool PythonNormalizer::process_number(TokenizerState& state, char c, TokenizedFile& result, LineMetrics& metrics) {
    if (!is_digit(c) && !(c == '.' && is_digit(state.peek_next()))) {
        return false;
    }
    metrics.line_has_code = true;
    result.tokens.push_back(parse_number(state));
    return true;
}

bool PythonNormalizer::process_identifier(TokenizerState& state, char c, TokenizedFile& result, LineMetrics& metrics) {
    if (!is_identifier_start(c)) {
        return false;
    }
    metrics.line_has_code = true;
    result.tokens.push_back(parse_identifier_or_keyword(state));
    return true;
}

bool PythonNormalizer::process_operator(TokenizerState& state, char c, TokenizedFile& result, LineMetrics& metrics) {
    if (!is_operator_char(c)) {
        return false;
    }
    metrics.line_has_code = true;
    result.tokens.push_back(parse_operator(state));
    return true;
}

void PythonNormalizer::process_indentation(TokenizerState& state, TokenizedFile& result) {
    size_t indent = 0;
    while (!state.eof() && (state.peek() == ' ' || state.peek() == '\t')) {
        if (state.peek() == '\t') {
            indent += 8 - (indent % 8);  // Tab stops at 8
        } else {
            indent++;
        }
        state.advance();
    }

    // Don't emit indent tokens for blank lines or comment-only lines
    if (!state.eof() && state.peek() != '\n' && state.peek() != '#') {
        auto indent_tokens = handle_indentation(state, indent);
        for (auto& tok : indent_tokens) {
            result.tokens.push_back(std::move(tok));
        }
    }
    state.at_line_start = false;
}

void PythonNormalizer::emit_remaining_dedents(TokenizerState& state, TokenizedFile& result) {
    while (state.indent_stack.size() > 1) {
        state.indent_stack.pop_back();
        NormalizedToken tok;
        tok.type = TokenType::DEDENT;
        tok.original_hash = hash_string("DEDENT");
        tok.normalized_hash = tok.original_hash;
        tok.line = state.line;
        tok.column = 1;
        tok.length = 0;
        result.tokens.push_back(tok);
    }
}

void PythonNormalizer::finalize_metrics(const TokenizerState& state, const LineMetrics& metrics, TokenizedFile& result) {
    // Calculate total lines: if file ends with newline, don't count the empty line after it
    // If the source is empty, total_lines is 0
    // If the source has content but no newline, line will be 1
    // If source ends with \n, the line counter has already incremented past the last actual line
    result.total_lines = state.source.empty() ? 0 : (state.column == 1 && state.line > 1 ? state.line - 1 : state.line);
    result.code_lines = metrics.code_lines;
    result.blank_lines = metrics.blank_lines;
    result.comment_lines = metrics.comment_lines;
}

// ============================================================================
// Helper methods
// ============================================================================

bool PythonNormalizer::is_identifier_start(char c) const {
    return std::isalpha(static_cast<unsigned char>(c)) || c == '_';
}

bool PythonNormalizer::is_identifier_char(char c) const {
    return std::isalnum(static_cast<unsigned char>(c)) || c == '_';
}

bool PythonNormalizer::is_digit(char c) const {
    return c >= '0' && c <= '9';
}

bool PythonNormalizer::is_hex_digit(char c) const {
    return is_digit(c) || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
}

bool PythonNormalizer::is_operator_char(char c) const {
    return c == '+' || c == '-' || c == '*' || c == '/' || c == '%' ||
           c == '=' || c == '<' || c == '>' || c == '!' || c == '&' ||
           c == '|' || c == '^' || c == '~' || c == '@' || c == '(' ||
           c == ')' || c == '[' || c == ']' || c == '{' || c == '}' ||
           c == ',' || c == ':' || c == ';' || c == '.';
}

// Factory function implementations
std::unique_ptr<TokenNormalizer> create_normalizer(Language language) {
    switch (language) {
        case Language::PYTHON:
            return std::make_unique<PythonNormalizer>();
        case Language::JAVASCRIPT:
        case Language::TYPESCRIPT:
            return std::make_unique<JavaScriptNormalizer>();
        case Language::CPP:
        case Language::C:
            return std::make_unique<CppNormalizer>();
        default:
            return nullptr;
    }
}

std::unique_ptr<TokenNormalizer> create_normalizer_for_file(std::string_view extension) {
    return create_normalizer(detect_language(extension));
}

}  // namespace aegis::similarity
