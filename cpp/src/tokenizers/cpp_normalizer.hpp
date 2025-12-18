#pragma once

#include "tokenizers/token_normalizer.hpp"
#include <unordered_set>

namespace aegis::similarity {

/**
 * Tokenizer and normalizer for C/C++ source code.
 *
 * Handles:
 * - C++20 keywords
 * - Preprocessor directives (#include, #define, etc.)
 * - Operators and punctuation
 * - String literals (regular, raw, wide)
 * - Character literals
 * - Number literals (int, float, hex, binary, octal, suffixes)
 * - Comments (// and multi-line)
 * - Templates (basic support)
 *
 * Normalization:
 * - Identifiers -> $ID
 * - String/char literals -> $STR
 * - Number literals -> $NUM
 * - Keywords and operators -> preserved
 * - Preprocessor directives -> preserved
 */
class CppNormalizer : public TokenNormalizer {
public:
    CppNormalizer();

    TokenizedFile normalize(std::string_view source) override;

    std::string_view language_name() const override {
        return "C++";
    }

    std::vector<std::string> supported_extensions() const override {
        return {".cpp", ".cxx", ".cc", ".c", ".hpp", ".hxx", ".h", ".hh"};
    }

private:
    // C/C++ keywords
    std::unordered_set<std::string> keywords_;

    // C++11/14/17/20 keywords
    std::unordered_set<std::string> modern_keywords_;

    // Built-in types
    std::unordered_set<std::string> builtin_types_;

    // Preprocessor directives
    std::unordered_set<std::string> preprocessor_;

    /**
     * Internal tokenization state.
     */
    struct TokenizerState {
        std::string_view source;
        size_t pos = 0;
        uint32_t line = 1;
        uint16_t column = 1;
        bool at_line_start = true;

        bool eof() const { return pos >= source.size(); }
        char peek() const { return eof() ? '\0' : source[pos]; }
        char peek_next() const {
            return (pos + 1 >= source.size()) ? '\0' : source[pos + 1];
        }
        char peek_at(size_t offset) const {
            return (pos + offset >= source.size()) ? '\0' : source[pos + offset];
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
                if (c != ' ' && c != '\t') {
                    at_line_start = false;
                }
            }
            return c;
        }
    };

    // Token parsing methods
    static NormalizedToken parse_string(TokenizerState& state);
    static NormalizedToken parse_raw_string(TokenizerState& state);
    static NormalizedToken parse_char(TokenizerState& state);
    NormalizedToken parse_number(TokenizerState& state) const;
    NormalizedToken parse_identifier_or_keyword(TokenizerState& state) const;
    static NormalizedToken parse_operator(TokenizerState& state);
    static void skip_preprocessor(TokenizerState& state);
    static void skip_single_line_comment(TokenizerState& state);
    static void skip_multi_line_comment(TokenizerState& state);

    // Refactoring Helpers
    void handle_line_metrics(TokenizerState& state, uint32_t& current_line,
                             size_t& code_lines, size_t& comment_lines, size_t& blank_lines,
                             bool& line_has_code, bool& line_has_comment) const;
                             
    bool skip_whitespace_and_newline(TokenizerState& state);
    
    bool process_preprocessor(TokenizerState& state, bool& line_has_code, TokenizedFile& result);

    bool process_comment(TokenizerState& state, bool& line_has_comment);
    
    bool process_string_literal(TokenizerState& state, TokenizedFile& result, bool& line_has_code);
    
    bool process_number(TokenizerState& state, TokenizedFile& result, bool& line_has_code) const;
    
    bool process_identifier(TokenizerState& state, TokenizedFile& result, bool& line_has_code) const;
    
    bool process_operator(TokenizerState& state, TokenizedFile& result, bool& line_has_code);

    // Helper methods
    static bool is_identifier_start(char c) ;
    static bool is_identifier_char(char c) ;
    static bool is_digit(char c) ;
    static bool is_hex_digit(char c) ;
    static bool is_operator_char(char c) ;
    static bool is_binary_digit(char c) ;
    static bool is_octal_digit(char c) ;

    // Number parsing helpers (extracted from parse_number to reduce cyclomatic complexity)
    static void consume_digits_with_separator(TokenizerState& state, std::string& value,
                                              bool (*digit_check)(char));
    static bool parse_hex_number(TokenizerState& state, std::string& value);
    static bool parse_binary_number(TokenizerState& state, std::string& value);
    static bool parse_octal_number(TokenizerState& state, std::string& value);
    static void parse_integer_part(TokenizerState& state, std::string& value);
    static bool parse_decimal_part(TokenizerState& state, std::string& value);
    static void parse_exponent_part(TokenizerState& state, std::string& value);
    static void skip_number_suffix(TokenizerState& state);

    // Operator parsing helpers (extracted from parse_operator to reduce cyclomatic complexity)
    static bool try_match_four_char_operator(TokenizerState& state, std::string& value);
    static bool try_match_three_char_operator(TokenizerState& state, std::string& value);
    static bool try_match_two_char_operator(TokenizerState& state, std::string& value);
    static bool is_punctuation(const std::string& op);
};

}  // namespace aegis::similarity
