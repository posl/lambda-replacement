package org.posl.core;

import java.io.IOException;
import java.util.Arrays;
import java.util.Locale;

public class Launcher {
    public static void main(String[] args) throws IOException {
        if (args.length < 2) {
            usage();
            System.exit(1);
        }

        LanguageConfig language = LanguageConfig.parse(args[0]);
        String command = args[1].toUpperCase(Locale.ROOT);
        String[] commandArgs = Arrays.copyOfRange(args, 2, args.length);

        if ("RQ3".equals(command)) {
            if (commandArgs.length != 9) {
                usage();
                System.exit(1);
            }
            Rq3.run(language, commandArgs);
            return;
        }

        String[] treeSitterArgs = Arrays.copyOfRange(args, 1, args.length);
        if (treeSitterArgs.length != 5) {
            usage();
            System.exit(1);
        }
        TreeSitterLambda.run(language, treeSitterArgs);
    }

    private static void usage() {
        System.err.println("Usage:");
        System.err.println("  Launcher <language> <workingDir> <srcHexsha> <dstHexsha> <srcFilePath> <dstFilePath>");
        System.err.println(
                "  Launcher <language> RQ3 <workingDir> <srcHexsha> <srcFilePath> <srcStartPos> <srcEndPos> <dstHexsha> <dstFilePath> <dstStartPos> <dstEndPos>");
        System.err.println("Supported languages: " + LanguageConfig.supportedLanguages());
    }
}
