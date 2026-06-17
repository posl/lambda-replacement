package org.posl.core;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

final class GitFileLoader {
    private GitFileLoader() {
    }

    static String getGitFileContent(String workingDir, String hexsha, String filePath)
            throws IOException, InterruptedException {
        Process process = new ProcessBuilder("git", "show", hexsha + ":" + filePath)
                .directory(new File(workingDir))
                .redirectErrorStream(true)
                .start();

        byte[] output = process.getInputStream().readAllBytes();
        int exitCode = process.waitFor();
        String content = new String(output, StandardCharsets.UTF_8);
        if (exitCode != 0) {
            throw new IOException("git show failed with exit code " + exitCode + ": " + content.strip());
        }
        return content;
    }

    static String removeNonAscii(String input) {
        return input.replaceAll("[^\\x00-\\x7F]", "");
    }
}
