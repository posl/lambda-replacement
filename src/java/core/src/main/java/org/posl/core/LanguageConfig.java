package org.posl.core;

import java.util.Arrays;
import java.util.Locale;
import java.util.Set;
import java.util.function.Supplier;
import java.util.stream.Collectors;

import com.github.gumtreediff.gen.TreeGenerator;
import com.github.gumtreediff.gen.srcml.SrcmlCppTreeGenerator;
import com.github.gumtreediff.gen.treesitterng.CSharpTreeSitterNgTreeGenerator;
import com.github.gumtreediff.gen.treesitterng.JavaScriptTreeSitterNgTreeGenerator;
import com.github.gumtreediff.gen.treesitterng.JavaTreeSitterNgTreeGenerator;
import com.github.gumtreediff.gen.treesitterng.PhpTreeSitterNgTreeGenerator;
import com.github.gumtreediff.gen.treesitterng.RubyTreeSitterNgTreeGenerator;

enum LanguageConfig {
    JAVA(
            "lambda_expression",
            JavaTreeSitterNgTreeGenerator::new,
            Set.of(
                    "declaration", "expression_statement", "labeled_statement", "if_statement",
                    "while_statement", "for_statement", "enhanced_for_statement", "block", ";",
                    "assert_statement", "do_statement", "break_statement", "continue_statement",
                    "return_statement", "yield_statement", "switch_expression", "synchronized_statement",
                    "local_variable_declaration", "throw_statement", "try_statement",
                    "try_with_resources_statement", "module_declaration", "package_declaration",
                    "import_declaration", "class_declaration", "record_declaration",
                    "interface_declaration", "annotation_type_declaration", "enum_declaration",
                    "field_declaration", "method_declaration", "compact_constructor_declaration",
                    "static_initializer", "constructor_declaration",
                    "annotation_type_element_declaration", "constant_declaration")),
    CPP(
            "lambda",
            SrcmlCppTreeGenerator::new,
            Set.of(
                    "block", "break", "case", "continue", "default", "do", "empty_stmt",
                    "expr_stmt", "for", "goto", "if_stmt", "label", "return", "switch",
                    "while", "function", "function_decl", "namespace", "typedef", "using",
                    "decl_stmt", "class_decl", "class", "constructor_decl", "destructor_decl",
                    "enum_decl", "enum", "super_list", "private", "protected", "public",
                    "struct_decl", "struct", "union_decl", "union")),
    JAVASCRIPT(
            "arrow_function",
            JavaScriptTreeSitterNgTreeGenerator::new,
            Set.of(
                    "export_statement", "import_statement", "debugger_statement",
                    "expression_statement", "declaration", "statement_bl", "if_statement",
                    "switch_statement", "for_statement", "for_in_statement", "while_statement",
                    "do_statement", "try_statement", "with_statem", "break_statement",
                    "continue_statement", "return_statement", "throw_statement", "empty_statement",
                    "labeled_statement", "function_declaration", "generator_function_declaration",
                    "class_declaration", "lexical_declaration", "variable_declaration")),
    CSHARP(
            "lambda_expression",
            CSharpTreeSitterNgTreeGenerator::new,
            Set.of(
                    "block", "break_statement", "checked_statement", "continue_statement",
                    "do_statement", "empty_statement", "expression_statement", "fixed_statement",
                    "for_each_statement", "for_statement", "goto_statement", "if_statement",
                    "labeled_statement", "local_declaration_statement", "local_function_statement",
                    "lock_statement", "return_statement", "switch_statement", "throw_statement",
                    "try_statement", "unsafe_statement", "using_statement", "while_statement",
                    "yield_statement", "class_declaration", "constructor_declaration",
                    "conversion_operator_declaration", "delegate_declaration",
                    "destructor_declaration", "enum_declaration", "event_declaration",
                    "event_field_declaration", "field_declaration", "indexer_declaration",
                    "interface_declaration", "method_declaration", "namespace_declaration",
                    "operator_declaration", "property_declaration", "record_declaration",
                    "record_struct_declaration", "struct_declaration", "using_directive")),
    PHP(
            "arrow_function",
            PhpTreeSitterNgTreeGenerator::new,
            Set.of(
                    "empty_statement", "compound_statement", "named_label_statement",
                    "expression_statement", "if_statement", "switch_statement", "while_statement",
                    "do_statement", "for_statement", "foreach_statement", "goto_statement",
                    "continue_statement", "break_statement", "return_statement", "try_statement",
                    "declare_statement", "echo_statement", "exit_statement", "unset_statement",
                    "const_declaration", "function_definition", "class_declaration",
                    "interface_declaration", "trait_declaration", "enum_declaration",
                    "namespace_definition", "namespace_use_declaration", "global_declaration",
                    "function_static_declaration")),
    RUBY(
            "lambda",
            RubyTreeSitterNgTreeGenerator::new,
            Set.of(
                    "parenthesized_statements", "_lhs", "call", "subshell", "_literal",
                    "chained_string", "regex", "method", "singleton_method", "class",
                    "singleton_class", "module", "begin", "while", "until", "if", "unless",
                    "for", "case", "case_match", "return", "yield", "break", "next", "redo",
                    "retry", "heredoc_beginning", "assignment", "operator_assignment",
                    "conditional", "range", "binary", "unary", "undef", "alias", "if_modifier",
                    "unless_modifier", "while_modifier", "until_modifier", "rescue_modifier",
                    "begin_block", "end_block", "_expression"));

    private final String targetNode;
    private final Supplier<TreeGenerator> treeGeneratorSupplier;
    private final Set<String> statementNodes;

    LanguageConfig(String targetNode, Supplier<TreeGenerator> treeGeneratorSupplier, Set<String> statementNodes) {
        this.targetNode = targetNode;
        this.treeGeneratorSupplier = treeGeneratorSupplier;
        this.statementNodes = statementNodes;
    }

    String targetNode() {
        return targetNode;
    }

    TreeGenerator newTreeGenerator() {
        return treeGeneratorSupplier.get();
    }

    boolean isStatementNode(String nodeType) {
        return statementNodes.contains(nodeType);
    }

    static LanguageConfig parse(String rawLanguage) {
        String normalized = rawLanguage.toUpperCase(Locale.ROOT)
                .replace("-", "_")
                .replace(".", "")
                .replace("#", "SHARP")
                .replace("++", "PLUSPLUS");
        if ("JS".equals(normalized)) {
            normalized = JAVASCRIPT.name();
        } else if ("CS".equals(normalized) || "C_SHARP".equals(normalized)) {
            normalized = CSHARP.name();
        } else if ("CXX".equals(normalized) || "CPLUSPLUS".equals(normalized)) {
            normalized = CPP.name();
        }

        try {
            return LanguageConfig.valueOf(normalized);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException(
                    "Unsupported language: " + rawLanguage + ". Supported languages: " + supportedLanguages(), e);
        }
    }

    static String supportedLanguages() {
        return Arrays.stream(values())
                .map(language -> language.name().toLowerCase(Locale.ROOT))
                .collect(Collectors.joining(", "));
    }
}
