#pragma once

#include "tokenizers/token_normalizer.hpp"
#include <unordered_set>
#include <regex>

namespace aegis::similarity {

/**
 * Tokenizer and normalizer for Python source code.
 *
 * Handles:
 * - Python keywords (def, class, if, for, while, etc.)
 * - Operators and punctuation
 * - String literals (single, double, triple-quoted, f-strings)
 * - Number literals (int, float, hex, binary, octal)
 * - Comments (# style)
 * - Indentation (significant in Python)
 *
 * Normalization:
 * - Identifiers -> $ID (same normalized hash)
 * - String literals -> $STR
 * - Number literals -> $NUM
 * - Keywords and operators -> preserved (original hash)
 */
class PythonNormalizer : public TokenNormalizer {
public:
    PythonNormalizer();

    TokenizedFile normalize(std::string_view source) override;

    std::string_view language_name() const override {
        return "Python";
    }

    std::vector<std::string> supported_extensions() const override {
        return {".py", ".pyw", ".pyi"};
    }

private:
    // Python keywords
    std::unordered_set<std::string> keywords_;

    // Python built-in types (treated specially for Type-2 detection)
    std::unordered_set<std::string> builtin_types_;

    // Operators and punctuation that should be preserved
    std::unordered_set<std::string> operators_;

    /**
     * Line metrics tracking for code analysis.
     */
    struct LineMetrics {
        uint32_t code_lines = 0;
        uint32_t blank_lines = 0;
        uint32_t comment_lines = 0;
        uint32_t current_line = 0;
        bool line_has_code = false;
        bool line_has_comment = false;
    };

    /**
     * Internal tokenization state.
     */
    struct TokenizerState {
        std::string_view source;
        size_t pos = 0;
        uint32_t line = 1;
        uint16_t column = 1;

        // Track indentation for INDENT/DEDENT tokens
        std::vector<size_t> indent_stack = {0};
        bool at_line_start = true;

        bool eof() const { return pos >= source.size(); }
        char peek() const { return eof() ? '\0' : source[pos]; }
        char peek_next() const {
            return (pos + 1 >= source.size()) ? '\0' : source[pos + 1];
        }
        char advance() {
            char c = peek();
            pos++;
            if (c == '\n') {
                line++;
                column = 1;
                at_line_start = true;
            } else {
                column++;
            }
            return c;
        }
        void skip_whitespace_on_line() {
            while (!eof() && (peek() == ' ' || peek() == '\t')) {
                advance();
            }
        }
    };

    // Token parsing methods
    NormalizedToken parse_string(TokenizerState& state);
    NormalizedToken parse_number(TokenizerState& state);
    NormalizedToken parse_identifier_or_keyword(TokenizerState& state);
    NormalizedToken parse_operator(TokenizerState& state);
    void skip_comment(TokenizerState& state);
    void skip_docstring(TokenizerState& state, char quote);
    std::vector<NormalizedToken> handle_indentation(TokenizerState& state, size_t current_indent);

    // Helper methods
    bool is_identifier_start(char c) const;
    bool is_identifier_char(char c) const;
    bool is_digit(char c) const;
    bool is_hex_digit(char c) const;
    bool is_operator_char(char c) const;

    // Number parsing helpers (reduce cyclomatic complexity of parse_number)
    bool parse_hex_number(TokenizerState& state, std::string& value);
    bool parse_binary_number(TokenizerState& state, std::string& value);
    bool parse_octal_number(TokenizerState& state, std::string& value);
    void parse_integer_part(TokenizerState& state, std::string& value);
    void parse_decimal_part(TokenizerState& state, std::string& value);
    void parse_exponent_part(TokenizerState& state, std::string& value);
    void skip_complex_suffix(TokenizerState& state, std::string& value);
    bool is_docstring_context(const std::vector<NormalizedToken>& tokens) const;
    bool is_import_statement(const TokenizerState& state) const;
    void skip_to_end_of_line(TokenizerState& state);

    // Operator parsing helpers (reduce cyclomatic complexity of parse_operator)
    static bool try_match_three_char_operator(TokenizerState& state, std::string& value);
    static bool try_match_two_char_operator(TokenizerState& state, std::string& value);
    static bool is_punctuation(const std::string& op);

    // Refactored processing methods (reduce cyclomatic complexity)
    void update_line_metrics(TokenizerState& state, LineMetrics& metrics);
    bool skip_whitespace(TokenizerState& state, char c);
    bool process_newline(TokenizerState& state, char c, TokenizedFile& result);
    bool process_comment(TokenizerState& state, char c, LineMetrics& metrics);
    bool process_import(TokenizerState& state, LineMetrics& metrics);
    bool process_string_or_docstring(TokenizerState& state, char c, TokenizedFile& result, LineMetrics& metrics);
    bool process_number(TokenizerState& state, char c, TokenizedFile& result, LineMetrics& metrics);
    bool process_identifier(TokenizerState& state, char c, TokenizedFile& result, LineMetrics& metrics);
    bool process_operator(TokenizerState& state, char c, TokenizedFile& result, LineMetrics& metrics);
    void process_indentation(TokenizerState& state, TokenizedFile& result);
    void emit_remaining_dedents(TokenizerState& state, TokenizedFile& result);
    void finalize_metrics(const TokenizerState& state, const LineMetrics& metrics, TokenizedFile& result);
};

}  // namespace aegis::similarity
