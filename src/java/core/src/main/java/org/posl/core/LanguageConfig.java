package org.posl.core;

import java.util.Arrays;
import java.util.Locale;
import java.util.Set;
import java.util.function.Supplier;
import java.util.stream.Collectors;

import com.github.gumtreediff.gen.TreeGenerator;
import com.github.gumtreediff.gen.treesitterng.CppTreeSitterNgTreeGenerator;
import com.github.gumtreediff.gen.treesitterng.CSharpTreeSitterNgTreeGenerator;
import com.github.gumtreediff.gen.treesitterng.JavaScriptTreeSitterNgTreeGenerator;
import com.github.gumtreediff.gen.treesitterng.JavaTreeSitterNgTreeGenerator;
import com.github.gumtreediff.gen.treesitterng.PhpTreeSitterNgTreeGenerator;
import com.github.gumtreediff.gen.treesitterng.RubyTreeSitterNgTreeGenerator;

enum LanguageConfig {
    CPP(
            "lambda_expression",
            CppTreeSitterNgTreeGenerator::new,
            Set.of(
                    "statement",
                    "attributed_statement",
                    "break_statement",
                    "case_statement",
                    "co_return_statement",
                    "co_yield_statement",
                    "compound_statement",
                    "continue_statement",
                    "do_statement",
                    "expansion_statement",
                    "expression_statement",
                    "for_statement",
                    "goto_statement",
                    "if_statement",
                    "init_statement",
                    "labeled_statement",
                    "return_statement",
                    "seh_leave_statement",
                    "seh_try_statement",
                    "switch_statement",
                    "throw_statement",
                    "try_statement",
                    "while_statement",
                    "alias_declaration",
                    "attribute_declaration",
                    "consteval_block_declaration",
                    "declaration",
                    "explicit_object_parameter_declaration",
                    "export_declaration",
                    "field_declaration",
                    "friend_declaration",
                    "global_module_fragment_declaration",
                    "import_declaration",
                    "module_declaration",
                    "optional_parameter_declaration",
                    "optional_type_parameter_declaration",
                    "parameter_declaration",
                    "private_module_fragment_declaration",
                    "static_assert_declaration",
                    "template_declaration",
                    "template_template_parameter_declaration",
                    "type_parameter_declaration",
                    "using_declaration",
                    "variadic_parameter_declaration",
                    "variadic_type_parameter_declaration")),
    CSHARP(
            "lambda_expression",
            CSharpTreeSitterNgTreeGenerator::new,
            Set.of(
                    "statement",
                    "break_statement",
                    "checked_statement",
                    "continue_statement",
                    "do_statement",
                    "empty_statement",
                    "expression_statement",
                    "fixed_statement",
                    "for_statement",
                    "foreach_statement",
                    "global_statement",
                    "goto_statement",
                    "if_statement",
                    "labeled_statement",
                    "local_declaration_statement",
                    "local_function_statement",
                    "lock_statement",
                    "return_statement",
                    "switch_statement",
                    "throw_statement",
                    "try_statement",
                    "unsafe_statement",
                    "using_statement",
                    "while_statement",
                    "yield_statement",
                    "declaration",
                    "type_declaration",
                    "accessor_declaration",
                    "catch_declaration",
                    "class_declaration",
                    "constructor_declaration",
                    "conversion_operator_declaration",
                    "delegate_declaration",
                    "destructor_declaration",
                    "enum_declaration",
                    "enum_member_declaration",
                    "event_declaration",
                    "event_field_declaration",
                    "field_declaration",
                    "file_scoped_namespace_declaration",
                    "indexer_declaration",
                    "interface_declaration",
                    "method_declaration",
                    "namespace_declaration",
                    "operator_declaration",
                    "property_declaration",
                    "record_declaration",
                    "struct_declaration",
                    "variable_declaration")),
    JAVA(
            "lambda_expression",
            JavaTreeSitterNgTreeGenerator::new,
            Set.of(
                    "statement",
                    "assert_statement",
                    "break_statement",
                    "continue_statement",
                    "do_statement",
                    "enhanced_for_statement",
                    "expression_statement",
                    "for_statement",
                    "if_statement",
                    "labeled_statement",
                    "return_statement",
                    "synchronized_statement",
                    "throw_statement",
                    "try_statement",
                    "try_with_resources_statement",
                    "while_statement",
                    "yield_statement",
                    "declaration",
                    "annotation_type_declaration",
                    "annotation_type_element_declaration",
                    "class_declaration",
                    "compact_constructor_declaration",
                    "constant_declaration",
                    "constructor_declaration",
                    "enum_declaration",
                    "field_declaration",
                    "import_declaration",
                    "interface_declaration",
                    "local_variable_declaration",
                    "method_declaration",
                    "module_declaration",
                    "package_declaration",
                    "record_declaration")),
    JAVASCRIPT(
            "arrow_function",
            JavaScriptTreeSitterNgTreeGenerator::new,
            Set.of(
                    "statement",
                    "break_statement",
                    "continue_statement",
                    "debugger_statement",
                    "do_statement",
                    "empty_statement",
                    "export_statement",
                    "expression_statement",
                    "for_in_statement",
                    "for_statement",
                    "if_statement",
                    "import_statement",
                    "labeled_statement",
                    "return_statement",
                    "switch_statement",
                    "throw_statement",
                    "try_statement",
                    "while_statement",
                    "with_statement",
                    "declaration",
                    "class_declaration",
                    "function_declaration",
                    "generator_function_declaration",
                    "lexical_declaration",
                    "variable_declaration")),

    PHP(
            "arrow_function",
            PhpTreeSitterNgTreeGenerator::new,
            Set.of(
                    "statement",
                    "break_statement",
                    "case_statement",
                    "compound_statement",
                    "continue_statement",
                    "declare_statement",
                    "default_statement",
                    "do_statement",
                    "echo_statement",
                    "empty_statement",
                    "exit_statement",
                    "expression_statement",
                    "for_statement",
                    "foreach_statement",
                    "goto_statement",
                    "if_statement",
                    "named_label_statement",
                    "return_statement",
                    "switch_statement",
                    "try_statement",
                    "unset_statement",
                    "while_statement",
                    "class_declaration",
                    "const_declaration",
                    "enum_declaration",
                    "function_static_declaration",
                    "global_declaration",
                    "interface_declaration",
                    "method_declaration",
                    "namespace_use_declaration",
                    "property_declaration",
                    "static_variable_declaration",
                    "trait_declaration",
                    "use_declaration")),
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
