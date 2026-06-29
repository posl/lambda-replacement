import argparse
import subprocess
from logging import INFO, FileHandler, Logger, getLogger
from dataclasses import dataclass, asdict

import pandas as pd
from tqdm import tqdm


from .config import (
    RESULT_DIR,
    JAR_PATH,
    project_replacement_path,
    project_delete_matching_path,
    lambda_delete_matching_log_path,
)
from .git_operate import get_repo


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

    return sorted(f"{p.parent.name}/{p.stem}" for p in base_dir.glob("*/*.csv"))


def main(language: str):
    name_with_owners = get_name_with_owners(language)

    for name_with_owner in tqdm(name_with_owners, desc=language):
        logger = setup_logger(name_with_owner.replace("/", "_"), language)
        logger.info("Start!")

        results: list[MatchingResult] = []

        df = pd.read_csv(project_replacement_path(language, name_with_owner))

        if df["modifying_type"].nunique() == 1:
            logger.info("Only one status exists.")
            continue

        df = df.sort_values("datetime", ascending=False).reset_index(drop=True)

        repo = get_repo(name_with_owner, language)

        df_insert = df[df["modifying_type"] == "insert"]
        df_delete = df[df["modifying_type"] == "delete"]

        delete_groups = {file: g for file, g in df_delete.groupby("src_file")}

        for insert in tqdm(df_insert.itertuples(), desc=name_with_owner, leave=False):
            insert_commit = insert.commit
            insert_dst_file = insert.dst_file
            insert_dst_start = insert.dst_start
            insert_dst_end = insert.dst_end
            insert_datetime = insert.datetime

            candidate = delete_groups.get(insert_dst_file)
            if candidate is None:
                continue
            df_delete_after_insert = candidate[
                (candidate["datetime"] > insert_datetime)
            ]

            for delete in df_delete_after_insert.itertuples():
                delete_datetime = delete.datetime
                assert delete_datetime > insert_datetime, (
                    f"{delete_datetime=} {insert_datetime=}"
                )

                delete_commit = f"{delete.commit}^"
                delete_src_file = delete.src_file
                delete_src_start = delete.src_start
                delete_src_end = delete.src_end

                try:
                    cmd = [
                        "java",
                        "-jar",
                        str(JAR_PATH),
                        language,
                        "RQ3",
                        repo.working_dir,
                        insert_commit,
                        insert_dst_file,
                        str(insert_dst_start),
                        str(insert_dst_end),
                        delete_commit,
                        delete_src_file,
                        str(delete_src_start),
                        str(delete_src_end),
                    ]
                    java_res = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=60 * 10, check=True
                    )
                except subprocess.CalledProcessError as e:
                    logger.error(
                        f"{insert_commit:} {insert_dst_file:} {delete_commit} {delete_src_file:}\n{e.stderr}"
                    )
                    continue
                except KeyboardInterrupt:
                    raise
                except Exception:
                    logger.exception(
                        f"{insert_commit:} {insert_dst_file:} {delete_commit} {delete_src_file:}"
                    )
                    continue

                if java_res.stdout.strip() == "true":
                    logger.info(f"True: {insert_commit}, {delete_commit}")
                    results.append(
                        MatchingResult(
                            insert_commit=insert_commit,
                            insert_dst_file=insert_dst_file,
                            insert_dst_start_pos=insert_dst_start,
                            insert_dst_end_pos=insert_dst_end,
                            delete_commit=delete_commit,
                            delete_src_file=delete_src_file,
                            delete_src_start_pos=delete_src_start,
                            delete_src_end_pos=delete_src_end,
                        )
                    )
                else:
                    logger.info(f"False: {insert_commit}, {delete_commit}")

        save_results(results, language, name_with_owner)


def save_results(results: list[MatchingResult], language: str, name_with_owner: str):
    if not results:
        return

    df = pd.DataFrame(asdict(r) for r in results)

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
