package org.posl.core;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;

public class TreeSitterLambda {
    public static ArrayList<String[]> exploreLambda(String language, String srcCode, String dstCode)
            throws IOException {
        return LambdaAnalyzer.exploreLambda(LanguageConfig.parse(language), srcCode, dstCode);
    }

    public static void main(String[] args) throws IOException {
        if (args.length != 6) {
            System.err.println(
                    "Usage: TreeSitterLambda <language> <workingDir> <srcHexsha> <dstHexsha> <srcFilePath> <dstFilePath>");
            System.err.println("Supported languages: " + LanguageConfig.supportedLanguages());
            System.exit(1);
        }

        LanguageConfig language = LanguageConfig.parse(args[0]);
        String[] analysisArgs = Arrays.copyOfRange(args, 1, args.length);
        run(language, analysisArgs);
    }

    static void run(LanguageConfig language, String[] args) throws IOException {
        String workingDir = args[0];
        String srcHexsha = args[1];
        String dstHexsha = args[2];
        String srcFilePath = args[3];
        String dstFilePath = args[4];

        try {
            String srcCode = GitFileLoader.removeNonAscii(
                    GitFileLoader.getGitFileContent(workingDir, srcHexsha, srcFilePath));
            String dstCode = GitFileLoader.removeNonAscii(
                    GitFileLoader.getGitFileContent(workingDir, dstHexsha, dstFilePath));

            LambdaAnalyzer.validateFileSize(srcCode, dstCode);
            ArrayList<String[]> results = LambdaAnalyzer.exploreLambda(language, srcCode, dstCode);
            results.stream()
                    .map(array -> String.join("\t", array))
                    .forEach(System.out::println);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("Interrupted while reading files from git", e);
        }
    }
}
