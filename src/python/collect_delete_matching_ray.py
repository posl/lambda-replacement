import argparse
import gc
import subprocess
from logging import INFO, FileHandler, Logger, getLogger
from dataclasses import dataclass, asdict

import pandas as pd
import psutil
import ray
from git_operate import get_repo
from ray.experimental.tqdm_ray import tqdm as rtqdm


from .config import (
    RESULT_DIR,
    JAR_PATH,
    project_replacement_path,
    project_delete_matching_path,
    lambda_delete_matching_log_path,
)


@dataclass
class MatchingResult:
    insert_commit: str
    insert_dst_file: str
    insert_dst_start: int
    insert_dst_end: int
    delete_commit: str
    delete_src_file: str
    delete_src_start: int
    delete_src_end: int


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


def get_name_with_owners(language: str) -> list[str]:
    base_dir = RESULT_DIR / "lambda_replacement" / language

    return sorted(f"{p.parent.name}/{p.stem}" for p in base_dir.glob("*/**/*.pkl"))


@ray.remote
def java_run(
    language: str,
    name_with_owner: str,
    repo_path: str,
    insert_commit: str,
    insert_dst_file: str,
    insert_dst_start: str,
    insert_dst_end: str,
    delete_commit: str,
    delete_src_file: str,
    delete_src_start: str,
    delete_src_end: str,
) -> MatchingResult | None:
    logger = setup_logger(name_with_owner.replace("/", "_"), language)
    try:
        cmd = [
            "java",
            "-jar",
            str(JAR_PATH),
            language,
            "RQ3",
            repo_path,
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
        return None
    except KeyboardInterrupt:
        raise
    except Exception:
        logger.exception(
            f"{insert_commit:} {insert_dst_file:} {delete_commit} {delete_src_file:}"
        )
        return None

    if java_res.stdout.strip() == "true":
        logger.info(f"True: {insert_commit}, {delete_commit}")
        return MatchingResult(
            insert_commit=insert_commit,
            insert_dst_file=insert_dst_file,
            insert_dst_start=insert_dst_start,
            insert_dst_end=insert_dst_end,
            delete_commit=delete_commit,
            delete_src_file=delete_src_file,
            delete_src_start=delete_src_start,
            delete_src_end=delete_src_end,
        )

    return None


def repository_process(name_with_owner: str, language: str):
    logger = setup_logger(name_with_owner.replace("/", "_"), language)
    logger.info("Start!")

    results: list[MatchingResult] = []

    df = pd.read_csv(project_replacement_path(language, name_with_owner, "csv"))

    if df["modifying_type"].nunique() == 1:
        logger.info("Only one status exists.")
        return

    df = df.sort_values("datetime", ascending=False).reset_index(drop=True)

    repo = get_repo(name_with_owner, language)

    df_insert = df[df["modifying_type"] == "insert"]
    df_delete = df[df["modifying_type"] == "delete"]

    delete_groups = {file: g for file, g in df_delete.groupby("src_file")}

    task_ids = []

    for insert in df_insert.itertuples():
        insert_commit = insert.commit
        insert_dst_file = insert.dst_file
        insert_dst_start = insert.dst_start
        insert_dst_end = insert.dst_end
        insert_datetime = insert.datetime

        candidate = delete_groups.get(insert_dst_file)
        if candidate is None:
            continue
        df_delete_after_insert = candidate[(candidate["datetime"] > insert_datetime)]

        for delete in df_delete_after_insert.itertuples():
            delete_datetime = delete.datetime
            assert delete_datetime > insert_datetime, (
                f"{delete_datetime=} {insert_datetime=}"
            )
            delete_commit = f"{delete.commit}^"
            delete_src_file = delete.src_file
            delete_src_start = delete.src_start
            delete_src_end = delete.src_end

            task_ids.append(
                java_run.remote(
                    language,
                    name_with_owner,
                    repo.working_dir,
                    insert_commit,
                    insert_dst_file,
                    insert_dst_start,
                    insert_dst_end,
                    delete_commit,
                    delete_src_file,
                    delete_src_start,
                    delete_src_end,
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

    df = pd.DataFrame(asdict(r) for r in results)

    result_path = project_delete_matching_path(language, name_with_owner)
    result_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(result_path, index=False)


def main(language: str, num_cpus: int):
    ray.init(num_cpus=num_cpus)

    name_with_owners = get_name_with_owners(language)

    for name_with_owner in rtqdm(name_with_owners, desc=language, position=0):
        repository_process(name_with_owner, language)

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

    parse = parser.parse_args()

    language = parse.language
    num_cpus = parse.num_cpus
    main(language, num_cpus)
