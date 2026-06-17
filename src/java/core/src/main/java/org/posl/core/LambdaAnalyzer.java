package org.posl.core;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import com.github.gumtreediff.actions.EditScript;
import com.github.gumtreediff.actions.EditScriptGenerator;
import com.github.gumtreediff.actions.SimplifiedChawatheScriptGenerator;
import com.github.gumtreediff.actions.model.Action;
import com.github.gumtreediff.actions.model.Delete;
import com.github.gumtreediff.actions.model.Insert;
import com.github.gumtreediff.actions.model.Update;
import com.github.gumtreediff.client.Run;
import com.github.gumtreediff.gen.TreeGenerator;
import com.github.gumtreediff.matchers.Matcher;
import com.github.gumtreediff.matchers.Matchers;
import com.github.gumtreediff.matchers.MappingStore;
import com.github.gumtreediff.tree.Tree;

final class LambdaAnalyzer {
    static final int MAX_FILE_SIZE = 1_000_000;

    private LambdaAnalyzer() {
    }

    static ArrayList<String[]> exploreLambda(LanguageConfig language, String srcCode, String dstCode)
            throws IOException {
        MappingContext context = createMappingContext(language, srcCode, dstCode);

        EditScriptGenerator scriptGenerator = new SimplifiedChawatheScriptGenerator();
        EditScript actions = scriptGenerator.computeActions(context.mappings());

        ArrayList<String[]> results = new ArrayList<>();
        for (Action action : actions) {
            if (isInsertedTarget(action, language)) {
                addInsertedLambdaResult(results, language, context.mappings(), action.getNode());
            } else if (isUpdatedToTarget(action, language, context.mappings())) {
                Tree srcNode = action.getNode();
                Tree dstNode = context.mappings().getDstForSrc(srcNode);
                results.add(new String[] {
                        "update",
                        Integer.toString(srcNode.getPos()),
                        Integer.toString(srcNode.getEndPos()),
                        Integer.toString(dstNode.getPos()),
                        Integer.toString(dstNode.getEndPos()),
                        "-1",
                });
            } else if (action instanceof Delete && isTargetNode(language, action.getNode())) {
                results.add(new String[] {
                        "delete",
                        Integer.toString(action.getNode().getPos()),
                        Integer.toString(action.getNode().getEndPos()),
                        "-1",
                        "-1",
                        "-1",
                });
            }
        }
        return results;
    }

    static boolean isMappedTarget(LanguageConfig language, String srcCode, int srcStartPos, int srcEndPos,
            String dstCode, int dstStartPos, int dstEndPos) throws IOException {
        MappingContext context = createMappingContext(language, srcCode, dstCode);
        List<Tree> srcNodes = context.srcTree().getTreesBetweenPositions(srcStartPos, srcEndPos);
        List<Tree> targets = srcNodes.stream()
                .filter(node -> isTargetNode(language, node))
                .toList();

        if (targets.size() != 1) {
            throw new IllegalArgumentException("Expected exactly one target node, but found " + targets.size());
        }

        Tree dstNodeFromSrc = context.mappings().getDstForSrc(targets.get(0));
        return dstNodeFromSrc != null
                && dstNodeFromSrc.getPos() == dstStartPos
                && dstNodeFromSrc.getEndPos() == dstEndPos;
    }

    static void validateFileSize(String srcCode, String dstCode) throws IOException {
        if (srcCode.length() > MAX_FILE_SIZE || dstCode.length() > MAX_FILE_SIZE) {
            throw new IOException("File size too large");
        }
    }

    private static MappingContext createMappingContext(LanguageConfig language, String srcCode, String dstCode)
            throws IOException {
        Run.initGenerators();

        TreeGenerator treeGenerator = language.newTreeGenerator();
        Tree srcTree = treeGenerator.generateFrom().string(srcCode).getRoot();
        Tree dstTree = treeGenerator.generateFrom().string(dstCode).getRoot();

        Matcher matcher = Matchers.getInstance().getMatcher();
        MappingStore mappings = matcher.match(srcTree, dstTree);
        return new MappingContext(srcTree, mappings);
    }

    private static boolean isInsertedTarget(Action action, LanguageConfig language) {
        return action instanceof Insert && isTargetNode(language, action.getNode());
    }

    private static boolean isUpdatedToTarget(Action action, LanguageConfig language, MappingStore mappings) {
        if (!(action instanceof Update) || isTargetNode(language, action.getNode())) {
            return false;
        }
        Tree dstNode = mappings.getDstForSrc(action.getNode());
        return dstNode != null && isTargetNode(language, dstNode);
    }

    private static boolean isTargetNode(LanguageConfig language, Tree node) {
        return language.targetNode().equals(node.getType().name);
    }

    private static void addInsertedLambdaResult(ArrayList<String[]> results, LanguageConfig language,
            MappingStore mappings, Tree insertedNode) {
        Tree parent = findNearestStatementParent(language, insertedNode);
        if (parent == null) {
            throw new IllegalStateException("Inserted node is not within a statement");
        }
        if (mappings.isDstMapped(parent)) {
            Tree srcHierarchy = mappings.getSrcForDst(parent);
            results.add(new String[] {
                    "insert",
                    Integer.toString(srcHierarchy.getPos()),
                    Integer.toString(srcHierarchy.getEndPos()),
                    Integer.toString(parent.getPos()),
                    Integer.toString(parent.getEndPos()),
                    parentHierarchy(language, insertedNode),
            });
        } else {
            results.add(new String[] {
                    "add",
                    "-1",
                    "-1",
                    Integer.toString(parent.getPos()),
                    Integer.toString(parent.getEndPos()),
                    parentHierarchy(language, insertedNode),
            });
        }
    }

    private static Tree findNearestStatementParent(LanguageConfig language, Tree node) {
        Tree parent = node.getParent();

        if (parent != null && parent.getType().name.equals("ERROR")) {
            throw new IllegalStateException(
                    "Inserted node is within an error node, which may indicate a parsing issue");
        }

        while (parent != null && !language.isStatementNode(parent.getType().name)) {
            parent = parent.getParent();
            if (parent != null && parent.getType().name.equals("ERROR")) {
                throw new IllegalStateException(
                        "Inserted node is within an error node, which may indicate a parsing issue");
            }
        }
        return parent;
    }

    private static String parentHierarchy(LanguageConfig language, Tree node) {
        Tree parent = node.getParent();
        List<String> parents = new ArrayList<>();
        while (parent != null) {
            String parentType = parent.getType().name;
            parents.add(parentType);
            if (language.isStatementNode(parentType)) {
                break;
            }
            parent = parent.getParent();
        }
        return String.join(",", parents);
    }

    private record MappingContext(Tree srcTree, MappingStore mappings) {
    }
}
