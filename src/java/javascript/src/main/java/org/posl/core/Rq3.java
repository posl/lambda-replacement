package org.posl.core;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.List;
import java.util.stream.Collectors;

import com.github.gumtreediff.client.Run;
import com.github.gumtreediff.gen.treesitterng.JavaScriptTreeSitterNgTreeGenerator;
import com.github.gumtreediff.matchers.Matcher;
import com.github.gumtreediff.matchers.Matchers;
import com.github.gumtreediff.matchers.MappingStore;
import com.github.gumtreediff.tree.Tree;

public class Rq3 {
    private static final String TARGET_NODE = "arrow_function";

    public static Boolean rq3(String srcCode, int srcStartPos, int srcEndPos, String dstCode,
            int dstStartPos, int dstEndPos) throws IOException, IllegalArgumentException {
        Run.initGenerators();

        JavaScriptTreeSitterNgTreeGenerator treeGenerator = new JavaScriptTreeSitterNgTreeGenerator();
        Tree srcTree = treeGenerator.generateFrom().string(srcCode).getRoot();
        Tree dstTree = treeGenerator.generateFrom().string(dstCode).getRoot();

        Matcher matcher = Matchers.getInstance().getMatcher();
        MappingStore mappings = matcher.match(srcTree, dstTree);

        List<Tree> srcNodes = srcTree.getTreesBetweenPositions(srcStartPos, srcEndPos);
        List<Tree> srcNodes_filtered = srcNodes.stream().filter(n -> TARGET_NODE.equals(n.getType().name))
                .collect(Collectors.toList());
        if (srcNodes_filtered.size() != 1) {
            throw new IllegalArgumentException("条件に合う要素が存在しないか、複数見つかりました");
        }
        Tree srcNode = srcNodes_filtered.get(0);

        Tree dstNodeFromSrc = mappings.getDstForSrc(srcNode);

        if (dstNodeFromSrc != null && dstNodeFromSrc.getPos() == dstStartPos
                && dstNodeFromSrc.getEndPos() == dstEndPos) {
            return true;
        } else {
            return false;
        }

        // List<Tree> dstNodes = dstTree.getTreesBetweenPositions(dstStartPos,
        // dstEndPos);
        // List<Tree> dstNodes_filtered = dstNodes.stream().filter(n ->
        // TARGET_NODE.equals(n.getType().name))
        // .collect(Collectors.toList());
        // if (dstNodes_filtered.size() != 1) {
        // throw new IllegalArgumentException("条件に合う要素が存在しないか、複数見つかりました");
        // }
        // Tree dstNode = dstNodes_filtered.get(0);

        // srcNodes.forEach(n -> System.out.println(n));
        // System.out.println("----");
        // dstNodes.forEach(n -> System.out.println(n));
        // System.out.println("----");

        // System.out.println(srcNode);
        // System.out.println(dstNode);
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
        if (args.length != 9) {
            System.err.println(
                    "Usage: JavaMainTreeSitter <workingDir> <srcHexsha> <srcFilePath> <srcStartPos> <srcEndPos> <dstHexsha> <dstFilePath> <dstStartPos> <dstEndPos>");
            System.exit(1);
        }

        String workingDir = args[0];
        String srcHexsha = args[1];
        String srcFilePath = args[2];
        String srcStartPos = args[3];
        String srcEndPos = args[4];
        String dstHexsha = args[5];
        String dstFilePath = args[6];
        String dstStartPos = args[7];
        String dstEndPos = args[8];

        try {
            String srcCode = getGitFileContent(workingDir, srcHexsha, srcFilePath);
            String dstCode = getGitFileContent(workingDir, dstHexsha, dstFilePath);

            srcCode = removeNonAscii(srcCode);
            dstCode = removeNonAscii(dstCode);

            int srcStartPosInt = Integer.parseInt(srcStartPos);
            int srcEndPosInt = Integer.parseInt(srcEndPos);
            int dstStartPosInt = Integer.parseInt(dstStartPos);
            int dstEndPosInt = Integer.parseInt(dstEndPos);

            Boolean result = rq3(srcCode, srcStartPosInt, srcEndPosInt, dstCode, dstStartPosInt,
                    dstEndPosInt);

            System.out.println(result);

        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        }
    }
}
