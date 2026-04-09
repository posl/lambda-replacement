import argparse
import subprocess
from logging import INFO, FileHandler, Logger, getLogger
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from git import Commit, GitCommandError
from git_operate import DiffCodesGenerator, get_diff, get_repo
from tqdm import tqdm

from config import (
    jar_path,
    repositories_lang_sample_pickle_path,
    project_replacement_path,
    lambda_replacement_log_path,
)


@dataclass
class LambdaResult:
    commit: str
    datetime: datetime
    src_file: str
    dst_file: str
    dst_start: int
    dst_end: int
    src_start: int
    src_end: int
    result: str


LIMIT_SIZE = 1_000_000


# Utility Functions
def setup_logger(name: str, language: str, level: int = INFO) -> Logger:
    log_file = lambda_replacement_log_path(language, name)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = FileHandler(log_file)
        handler.setLevel(level)
        logger.addHandler(handler)

    return logger


def get_language_config(language: str) -> tuple[str, str]:
    configs = {
        "java": ("2014-03-17", "java"),
        "javascript": ("2014-06-01", "js"),
        "ruby": ("2009-01-29", "rb"),
        "php": ("2019-11-27", "php"),
        "csharp": ("2007-11-18", "cs"),
        "cpp": ("2010-08-12", "cpp"),
    }
    return configs[language]


# Main Processing Functions
def process_commit(
    commit: Commit,
    language: str,
    extension: str,
    logger: Logger,
) -> list[LambdaResult]:
    try:
        diff = get_diff(commit, extension)
    except KeyboardInterrupt:
        raise
    except GitCommandError as e:
        logger.error(f"GitCommandError: {e}")
        return []

    results: list[LambdaResult] = []

    for src_file, dst_file in DiffCodesGenerator(diff):
        try:
            cmd = [
                "java",
                "-jar",
                str(jar_path(language)),
                commit.repo.working_dir,
                commit.parents[0].hexsha,
                commit.hexsha,
                src_file,
                dst_file,
            ]

            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if res.returncode != 0:
                logger.error(
                    f"{commit.hexsha:}: {src_file:}, {dst_file:}\n{res.stderr}"
                )
                continue
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.error(f"{commit.hexsha:}: {src_file:}, {dst_file:}\n{e}")
            continue

        for line in res.stdout.split("\n"):
            parts = line.split("\t")

            if len(parts) != 5:
                continue

            dst_start, dst_end, src_start, src_end, result = parts

            results.append(
                LambdaResult(
                    commit=commit.hexsha,
                    datetime=commit.committed_datetime,
                    src_file=src_file,
                    dst_file=dst_file,
                    dst_start=int(dst_start),
                    dst_end=int(dst_end),
                    src_start=int(src_start),
                    src_end=int(src_end),
                    result=result,
                )
            )

    return results


def process_repository(
    name_with_owner: str,
    language: str,
    extension: str,
    introduction_date: str,
) -> None:
    """_summary_

    Args:
        repo (Repo): _description_
        extension (str): _description_
        introduction_date (str): _description_
        logger (Logger): _description_
    """
    repo_logger = setup_logger(name_with_owner.replace("/", "_"), language)
    repo_logger.info("Start!")

    try:
        repo = get_repo(name_with_owner, language)
    except KeyboardInterrupt:
        raise
    except Exception:
        repo_logger.error(f"Repository not found: {name_with_owner}")
        return

    results: list[LambdaResult] = []

    for commit in tqdm(
        repo.iter_commits(since=introduction_date),
        desc=name_with_owner,
        # total=repo.commit().count(),
        leave=False,
    ):
        if len(commit.parents) != 1:
            continue

        results.extend(
            process_commit(
                commit,
                language,
                extension,
                repo_logger,
            )
        )

    save_results(results, language, name_with_owner)

    repo_logger.info("Done!")


def save_results(
    results: list[LambdaResult], language: str, name_with_owner: str
) -> None:
    if not results:
        return

    df = pd.DataFrame([r.__dict__ for r in results])

    result_path = project_replacement_path(language, name_with_owner)
    result_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_pickle(result_path)


def collect_lambda(language: str):
    lang_logger = setup_logger(language, language)
    lang_logger.info("Start!")

    introduction_date, extension = get_language_config(language)

    df = pd.read_pickle(repositories_lang_sample_pickle_path(language))
    # df.sort_values("commits", ascending=True, inplace=True)
    # df = df[210:]

    for name_with_owner in tqdm(df["Name with Owner"], desc=language):
        process_repository(
            name_with_owner,
            language,
            extension,
            introduction_date,
        )

    lang_logger.info("Done!")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-l",
        "--language",
        required=True,
        help="Language to analyze",
    )

    args = parser.parse_args()

    collect_lambda(args.language)


if __name__ == "__main__":
    main()
