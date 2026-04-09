package org.posl.core;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Set;
import java.util.stream.Collectors;

import com.github.gumtreediff.actions.EditScript;
import com.github.gumtreediff.actions.EditScriptGenerator;
import com.github.gumtreediff.actions.SimplifiedChawatheScriptGenerator;
import com.github.gumtreediff.actions.model.Action;
import com.github.gumtreediff.actions.model.Delete;
import com.github.gumtreediff.actions.model.Insert;
import com.github.gumtreediff.actions.model.Update;
import com.github.gumtreediff.client.Run;
import com.github.gumtreediff.gen.treesitterng.RubyTreeSitterNgTreeGenerator;
import com.github.gumtreediff.matchers.Matcher;
import com.github.gumtreediff.matchers.Matchers;
import com.github.gumtreediff.matchers.MappingStore;
import com.github.gumtreediff.tree.Tree;

public class TreeSitterLambda {
    private static final String TARGET_NODE = "lambda";
    private static final int MAX_FILE_SIZE = 1_000_000;
    private static final Set<String> STATEMENTS = Set.of(
            "parenthesized_statements",
            "_lhs",
            // alias($._function_identifier_call, $.call),
            "call",
            // "array",
            // "string_array",
            // "symbol_array",
            // "hash",
            "subshell",
            "_literal",
            // "string",
            // "character",
            "chained_string",
            "regex",
            // "lambda",
            "method",
            "singleton_method",
            "class",
            "singleton_class",
            "module",
            "begin",
            "while",
            "until",
            "if",
            "unless",
            "for",
            "case",
            "case_match",
            "return",
            "yield",
            "break",
            "next",
            "redo",
            "retry",
            // alias($.parenthesized_unary, $.unary),

            "heredoc_beginning",
            "assignment",
            "operator_assignment",
            "conditional",
            "range",
            "binary",
            "unary",
            "undef",
            "alias",
            "if_modifier",
            "unless_modifier",
            "while_modifier",
            "until_modifier",
            "rescue_modifier",
            "begin_block",
            "end_block",
            "_expression");

    public static ArrayList<String[]> explore_lambda(String srcCode, String dstCode)
            throws IOException, IllegalArgumentException {
        Run.initGenerators();

        RubyTreeSitterNgTreeGenerator treeGenerator = new RubyTreeSitterNgTreeGenerator();
        Tree srcTree = treeGenerator.generateFrom().string(srcCode).getRoot();
        Tree dstTree = treeGenerator.generateFrom().string(dstCode).getRoot();

        Matcher matcher = Matchers.getInstance().getMatcher();
        MappingStore mappings = matcher.match(srcTree, dstTree);

        EditScriptGenerator scriptGenerator = new SimplifiedChawatheScriptGenerator();
        EditScript actions = scriptGenerator.computeActions(mappings);

        ArrayList<String[]> results = new ArrayList<String[]>();
        for (Action action : actions) {
            if (action instanceof Insert && TARGET_NODE.equals(action.getNode().getType().name)) {
                Tree actionNode = action.getNode();

                Tree parent = actionNode.getParent();
                String parentType = parent.getType().name;
                StringBuilder parents = new StringBuilder();
                parents.append(parentType);

                while (!STATEMENTS.contains(parentType)) {
                    parent = parent.getParent();
                    parentType = parent.getType().name;
                    parents.append(",").append(parentType);
                }

                if (mappings.isDstMapped(parent)) {
                    Tree srcHierarchy = mappings.getSrcForDst(parent);
                    String[] res = {
                            "insert",
                            Integer.toString(srcHierarchy.getPos()),
                            Integer.toString(srcHierarchy.getEndPos()),
                            Integer.toString(parent.getPos()),
                            Integer.toString(parent.getEndPos()),
                            parents.toString(),
                    };
                    results.add(res);
                }
            } else if (action instanceof Update && !TARGET_NODE.equals(action.getNode().getType().name)) { // srcがUPDATEかつTARGET_NODEでない場合
                Tree actionNode = action.getNode();
                Tree dstNode = mappings.getDstForSrc(actionNode);
                if (TARGET_NODE.equals(dstNode.getType().name)) {
                    String[] res = {
                            "update",
                            Integer.toString(actionNode.getPos()),
                            Integer.toString(actionNode.getEndPos()),
                            Integer.toString(dstNode.getPos()),
                            Integer.toString(dstNode.getEndPos()),
                            "-1",
                    };
                    results.add(res);
                }
            } else if (action instanceof Delete && TARGET_NODE.equals(action.getNode().getType().name)) {
                String[] res = {
                        "delete",
                        Integer.toString(action.getNode().getPos()),
                        Integer.toString(action.getNode().getEndPos()),
                        "-1",
                        "-1",
                        "-1",
                };
                results.add(res);
            }
        }
        return results;
    }

    private static String getGitFileContent(String workingDir, String hexsha, String filePath)
            throws IOException, InterruptedException {
        String[] command = { "git", "show", hexsha + ":" + filePath };
        ProcessBuilder processBuilder = new ProcessBuilder(command).directory(new File(workingDir));
        Process process = processBuilder.start();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
            String content = reader.lines().collect(Collectors.joining("\n"));
            process.waitFor();
            return content;
        }
    }

    public static String removeNonAscii(String input) {
        // ASCII範囲外の文字を正規表現で置換
        return input.replaceAll("[^\\x00-\\x7F]", "");
    }

    public static void main(String[] args) throws IOException {
        if (args.length != 5) {
            System.err.println(
                    "Usage: JavaMainTreeSitter <workingDir> <srcHexsha> <dstHexsha> <srcFilePath> <dstFilePath>");
            return;
        }

        String workingDir = args[0];
        String srcHexsha = args[1];
        String dstHexsha = args[2];
        String srcFilePath = args[3];
        String dstFilePath = args[4];

        try {
            String srcCode = getGitFileContent(workingDir, srcHexsha, srcFilePath);
            String dstCode = getGitFileContent(workingDir, dstHexsha, dstFilePath);

            srcCode = removeNonAscii(srcCode);
            dstCode = removeNonAscii(dstCode);

            if (srcCode.length() > MAX_FILE_SIZE || dstCode.length() > MAX_FILE_SIZE) {
                throw new IOException("File size too large");
            }

            ArrayList<String[]> results = explore_lambda(srcCode, dstCode);

            results.stream()
                    .map(array -> String.join("\t", array)) // 配列をフォーマット
                    .forEach(System.out::println); // 出力

        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        }
    }
}
