import argparse
import subprocess
from logging import INFO, FileHandler, Logger, getLogger
from dataclasses import dataclass

import pandas as pd
from git_operate import get_repo
from tqdm import tqdm

from config import (
    RESULT_DIR,
    jar_path,
    project_replacement_path,
    project_delete_matching_path,
    lambda_delete_matching_log_path,
)


@dataclass
class MatchingResult:
    insert_commit: str
    insert_dst_file: str
    insert_dst_start_pos: int
    insert_dst_end_pos: int
    delete_commit: str
    delete_src_file: str
    delete_src_start_pos: int
    delete_src_end_pos: int


def setup_logger(name: str, language: str, level: int = INFO) -> Logger:
    log_file = lambda_delete_matching_log_path(language, name)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = FileHandler(log_file)
        handler.setLevel(level)
        logger.addHandler(handler)

    return logger


def get_name_with_owners(language: str) -> list[str]:
    base_dir = RESULT_DIR / "lambda_replacement" / language

    return sorted(f"{p.parent.name}/{p.stem}" for p in base_dir.glob("*/**/*.pkl"))


def main(language: str):
    jar_path_ = jar_path(language)

    name_with_owners = get_name_with_owners(language)

    for name_with_owner in tqdm(name_with_owners, desc=language):
        logger = setup_logger(name_with_owner.replace("/", "_"), language)

        results: list[MatchingResult] = []

        df = pd.read_pickle(project_replacement_path(language, name_with_owner))

        if len(df["status"].unique()) == 1:
            logger.info("Only one status exists.")
            continue

        df.sort_index(inplace=True, ascending=False)
        df.reset_index(drop=True, inplace=True)

        repo = get_repo(name_with_owner, language)

        df_outer = df[df["status"] == "insert"]

        for i, outer_row in tqdm(
            df_outer.iterrows(), desc=name_with_owner, leave=False, total=len(df_outer)
        ):
            outer_commit = outer_row["commit"]
            outer_srcFile = outer_row["src file"]
            outer_dstFile = outer_row["dst file"]
            outer_srcStartPos = outer_row["src start pos"]
            outer_srcEndPos = outer_row["src end pos"]
            outer_dstStartPos = outer_row["dst start pos"]
            outer_dstEndPos = outer_row["dst end pos"]
            outer_datetime = repo.commit(outer_commit).committed_datetime

            # print(
            #     f"{i=}, {outer_commit=}, {outer_datetime=}, {outer_srcFile=} {outer_dstFile=}, {outer_srcStartPos=}, {outer_srcEndPos=}, {outer_dstStartPos=}, {outer_dstEndPos=}"
            # )

            df_inner = df[i + 1 :]
            df_inner = df_inner[
                (df_inner["status"] == "delete")
                & (df_inner["src file"] == outer_dstFile)
            ]

            for j, inner_row in tqdm(
                df_inner.iterrows(),
                desc=name_with_owner,
                leave=False,
                total=len(df_inner),
            ):
                inner_datetime = repo.commit(inner_row["commit"]).committed_datetime
                if outer_datetime == inner_datetime:
                    continue
                inner_commit = f"{inner_row['commit']}^"
                # inner_datetime = inner_row["datetime"]
                inner_srcFile = inner_row["src file"]
                inner_dstFile = inner_row["dst file"]
                inner_srcStartPos = inner_row["src start pos"]
                inner_srcEndPos = inner_row["src end pos"]
                inner_dstStartPos = inner_row["dst start pos"]
                inner_dstEndPos = inner_row["dst end pos"]

                # print(
                #     f"\t{j=}, {inner_commit=}, {inner_datetime=}, {inner_srcFile=} {inner_dstFile=}, {inner_srcStartPos=}, {inner_srcEndPos=}, {inner_dstStartPos=}, {inner_dstEndPos=}"
                # )

                try:
                    cmd = [
                        "java",
                        "-jar",
                        str(jar_path_),
                        "RQ3",
                        repo.working_dir,
                        outer_commit,
                        outer_dstFile,
                        outer_dstStartPos,
                        outer_dstEndPos,
                        inner_commit,
                        inner_srcFile,
                        inner_srcStartPos,
                        inner_srcEndPos,
                    ]
                    java_res = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60 * 10,
                    )

                    if java_res.returncode != 0:
                        logger.error(
                            f"{outer_commit:} {outer_dstFile:} {inner_commit} {inner_srcFile:} {java_res.stderr:}"
                        )
                        continue
                except KeyboardInterrupt:
                    raise KeyboardInterrupt
                except Exception as e:
                    logger.error(
                        f"{outer_commit:} {outer_dstFile:} {inner_commit} {inner_srcFile:} {e}"
                    )
                    continue

                if java_res.stdout.strip() == "true":
                    logger.info(f"True: {outer_commit}, {inner_commit}")
                    results.append(
                        MatchingResult(
                            insert_commit=outer_commit,
                            insert_dst_file=outer_dstFile,
                            insert_dst_start_pos=outer_dstStartPos,
                            insert_dst_end_pos=outer_dstEndPos,
                            delete_commit=inner_commit,
                            delete_src_file=inner_srcFile,
                            delete_src_start_pos=inner_srcStartPos,
                            delete_src_end_pos=inner_srcEndPos,
                        )
                    )
                else:
                    logger.info(f"False: {outer_commit}, {inner_commit}")

        save_results(results, language, name_with_owner)


def save_results(results: list[MatchingResult], language: str, name_with_owner: str):
    if not results:
        return

    df = pd.DataFrame([r.__dict__ for r in results])

    result_path = project_delete_matching_path(language, name_with_owner)
    result_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(result_path, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-l",
        "--language",
        help="The language to analyze.",
    )
    language = parser.parse_args().language
    main(language)
