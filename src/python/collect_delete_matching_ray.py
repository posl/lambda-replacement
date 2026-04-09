import argparse
import gc
import subprocess
from logging import INFO, FileHandler, Logger, getLogger
from time import sleep
from dataclasses import dataclass

import pandas as pd
import psutil
import ray
from git_operate import get_repo
from ray.experimental.tqdm_ray import tqdm as rtqdm


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


def garbage_collect(pct=80.0):
    if psutil.virtual_memory().percent >= pct:
        gc.collect()


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


def setup_logger_for_ray(name: str, log_file: str, level=INFO) -> Logger:
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


@ray.remote
def java_run(
    jar_path_: str,
    repo_path: str,
    outer_commit: str,
    outer_dstFile: str,
    outer_dstStartPos: str,
    outer_dstEndPos: str,
    inner_commit: str,
    inner_srcFile: str,
    inner_srcStartPos: str,
    inner_srcEndPos: str,
    name_with_owner: str,
    log_path: str,
) -> MatchingResult | None:
    logger = setup_logger_for_ray(name_with_owner, log_path)
    try:
        cmd = [
            "java",
            "-jar",
            str(jar_path_),
            "RQ3",
            repo_path,
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
            return None
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except Exception as e:
        logger.error(
            f"{outer_commit:} {outer_dstFile:} {inner_commit} {inner_srcFile:} {e}"
        )
        return None

    if java_res.stdout.strip() == "true":
        logger.info(f"True: {outer_commit}, {inner_commit}")
        return MatchingResult(
            insert_commit=outer_commit,
            insert_dst_file=outer_dstFile,
            insert_dst_start_pos=outer_dstStartPos,
            insert_dst_end_pos=outer_dstEndPos,
            delete_commit=inner_commit,
            delete_src_file=inner_srcFile,
            delete_src_start_pos=inner_srcStartPos,
            delete_src_end_pos=inner_srcEndPos,
        )

    else:
        return None


def repository_process(name_with_owner: str, language: str):
    logger = setup_logger(name_with_owner.replace("/", "_"), language)
    logger.info("Start!")

    results: list[MatchingResult] = []

    df = pd.read_pickle(project_replacement_path(language, name_with_owner))

    if len(df["status"].unique()) == 1:
        logger.info("Only one status exists.")
        return

    df.sort_index(inplace=True, ascending=False)
    df.reset_index(drop=True, inplace=True)

    repo = get_repo(name_with_owner, language)

    df_outer = df[df["status"] == "insert"]

    task_ids = []

    log_path_id = ray.put(lambda_delete_matching_log_path(language, name_with_owner))

    jar_path_id = ray.put(jar_path(language))
    repo_path_id = ray.put(repo.working_dir)
    name_with_owner_id = ray.put(name_with_owner)

    for i, outer_row in df_outer.iterrows():
        outer_commit = outer_row["commit"]
        outer_dstFile = outer_row["dst file"]
        outer_dstStartPos = outer_row["dst start pos"]
        outer_dstEndPos = outer_row["dst end pos"]
        outer_datetime = repo.commit(outer_commit).committed_datetime

        df_inner = df[i + 1 :]
        df_inner = df_inner[
            (df_inner["status"] == "delete") & (df_inner["src file"] == outer_dstFile)
        ]

        for j, inner_row in df_inner.iterrows():
            inner_datetime = repo.commit(inner_row["commit"]).committed_datetime
            if outer_datetime == inner_datetime:
                continue
            inner_commit = f"{inner_row['commit']}^"
            # inner_datetime = inner_row["datetime"]
            inner_srcFile = inner_row["src file"]
            inner_srcStartPos = inner_row["src start pos"]
            inner_srcEndPos = inner_row["src end pos"]

            task_ids.append(
                java_run.remote(
                    jar_path_id,
                    repo_path_id,
                    outer_commit,
                    outer_dstFile,
                    outer_dstStartPos,
                    outer_dstEndPos,
                    inner_commit,
                    inner_srcFile,
                    inner_srcStartPos,
                    inner_srcEndPos,
                    name_with_owner_id,
                    log_path_id,
                )
            )

    owner, name = name_with_owner.split("/")
    desc = f"{owner[:5].ljust(7, '.')}/{name[:5].ljust(7, '.')}"

    pbar = rtqdm(total=len(task_ids), desc=desc, position=1)
    pbar.update(0)

    while task_ids:
        done_id, task_ids = ray.wait(task_ids, num_returns=1)
        pbar.update(1)
        java_res = ray.get(done_id[0])
        if java_res:
            results.append(java_res)
        garbage_collect()

    save_results(results, language, name_with_owner)

    logger.info("Done!")


def save_results(results: list[MatchingResult], language: str, name_with_owner: str):
    if not results:
        return

    df = pd.DataFrame([r.__dict__ for r in results])

    result_path = project_delete_matching_path(language, name_with_owner)
    result_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(result_path, index=False)


def main(language: str, num_cpus: int):
    ray.init(num_cpus=num_cpus)
    sleep(1)

    name_with_owners = get_name_with_owners(language)

    for name_with_owner in rtqdm(name_with_owners, desc=language, position=0):
        repository_process(name_with_owner, language, jar_path)

    ray.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-l",
        "--language",
        help="The language to analyze.",
    )
    parser.add_argument(
        "-n",
        "--num_cpus",
        help="The number of cpus.",
        type=int,
        default=10,
    )
    language = parser.parse_args().language
    num_cpus = parser.parse_args().num_cpus
    main(language, num_cpus)
