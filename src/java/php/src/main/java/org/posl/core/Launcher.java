package org.posl.core;

import java.io.IOException;
import java.util.Arrays;

public class Launcher {
    public static void main(String[] args) throws IOException {
        if (args.length > 0) {
            String rq = args[0];
            args = Arrays.copyOfRange(args, 1, args.length);
            // 実行したいクラスを切り替える
            if (rq.equals("RQ3")) {
                Rq3.main(args);
            } else {
                TreeSitterLambda.main(args);
            }
        } else {
            System.out.println("Please specify the RQ number.");
            return;
        }
    }
}
