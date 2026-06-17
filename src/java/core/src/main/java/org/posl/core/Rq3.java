package org.posl.core;

import java.io.IOException;
import java.util.Arrays;

public class Rq3 {
    public static boolean rq3(String language, String srcCode, int srcStartPos, int srcEndPos, String dstCode,
            int dstStartPos, int dstEndPos) throws IOException {
        return LambdaAnalyzer.isMappedTarget(
                LanguageConfig.parse(language),
                srcCode,
                srcStartPos,
                srcEndPos,
                dstCode,
                dstStartPos,
                dstEndPos);
    }

    public static void main(String[] args) throws IOException {
        if (args.length != 10) {
            System.err.println(
                    "Usage: Rq3 <language> <workingDir> <srcHexsha> <srcFilePath> <srcStartPos> <srcEndPos> <dstHexsha> <dstFilePath> <dstStartPos> <dstEndPos>");
            System.err.println("Supported languages: " + LanguageConfig.supportedLanguages());
            System.exit(1);
        }

        LanguageConfig language = LanguageConfig.parse(args[0]);
        String[] rq3Args = Arrays.copyOfRange(args, 1, args.length);
        run(language, rq3Args);
    }

    static void run(LanguageConfig language, String[] args) throws IOException {
        String workingDir = args[0];
        String srcHexsha = args[1];
        String srcFilePath = args[2];
        int srcStartPos = Integer.parseInt(args[3]);
        int srcEndPos = Integer.parseInt(args[4]);
        String dstHexsha = args[5];
        String dstFilePath = args[6];
        int dstStartPos = Integer.parseInt(args[7]);
        int dstEndPos = Integer.parseInt(args[8]);

        try {
            String srcCode = GitFileLoader.removeNonAscii(
                    GitFileLoader.getGitFileContent(workingDir, srcHexsha, srcFilePath));
            String dstCode = GitFileLoader.removeNonAscii(
                    GitFileLoader.getGitFileContent(workingDir, dstHexsha, dstFilePath));

            System.out.println(LambdaAnalyzer.isMappedTarget(
                    language,
                    srcCode,
                    srcStartPos,
                    srcEndPos,
                    dstCode,
                    dstStartPos,
                    dstEndPos));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("Interrupted while reading files from git", e);
        }
    }
}
