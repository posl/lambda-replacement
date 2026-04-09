import argparse
import gc
import subprocess
from logging import INFO, FileHandler, Logger, getLogger
from time import sleep
from dataclasses import dataclass
from datetime import datetime


import pandas as pd
import psutil
import ray
from git import Commit, GitCommandError
from ray.experimental.tqdm_ray import tqdm as rtqdm

from git_operate import DiffCodesGenerator, get_diff, get_repo
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


@ray.remote(num_cpus=1)
class WorkerActor:
    def __init__(self, language: str):
        self.language = language
        self.introduction_date, self.extension = self.get_language_config(language)

    @staticmethod
    def garbage_collect(pct=80.0):
        if psutil.virtual_memory().percent >= pct:
            gc.collect()

    @staticmethod
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

    @staticmethod
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

    def process_commit(
        self,
        commit: Commit,
        logger: Logger,
    ) -> list[LambdaResult]:
        try:
            diff = get_diff(commit, self.extension)
        except KeyboardInterrupt:
            raise
        except GitCommandError as e:
            logger.error(f"GitCommandError: {e}")
            return []

        results: list[LambdaResult] = []

        for src_file, dst_file in DiffCodesGenerator(diff):
            # src_code = get_past_contents(commit.parents[0], src_file)
            # src_code = convert2ascii(src_code)
            # if len(src_code) > LIMIT_SIZE:
            #     logger.error(f"{commit.hexsha:}, {src_file:} src_code is too large")
            #     continue
            # dst_code = get_past_contents(commit, dst_file)
            # dst_code = convert2ascii(dst_code)
            # if len(dst_code) > LIMIT_SIZE:
            #     logger.error(f"{commit.hexsha:}, {dst_file:} src_code is too large")
            #     continue

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
        self,
        name_with_owner: str,
    ):
        repo_logger = self.setup_logger(name_with_owner.replace("/", "_"), language)
        repo_logger.info("Start!")

        try:
            repo = get_repo(name_with_owner, language)
        except KeyboardInterrupt:
            raise
        except Exception:
            repo_logger.error(f"Repository not found: {name_with_owner}")
            return []

        results: list[LambdaResult] = []

        owner, name = name_with_owner.split("/")
        desc = f"{owner[:5].ljust(7, '.')}/{name[:5].ljust(7, '.')}"

        for commit in rtqdm(
            repo.iter_commits(since=self.introduction_date),
            desc=desc,
            # total=repo.commit().count(),
        ):
            if len(commit.parents) != 1:
                continue

            results.extend(
                self.process_commit(
                    commit,
                    repo_logger,
                )
            )

        self.save_results(results, language, name_with_owner)

        repo_logger.info("Done!")

    def save_results(self, results: list[LambdaResult], name_with_owner: str):
        if not results:
            return

        df = pd.DataFrame([r.__dict__ for r in results])

        result_path = project_replacement_path(self.language, name_with_owner)
        result_path.parent.mkdir(parents=True, exist_ok=True)

        df.to_pickle(result_path)


def collect_lambda_ray(language: str, num_cpus: int = 10):
    lang_logger = WorkerActor.setup_logger(language, language)
    lang_logger.info("Start!")

    ray.init(
        num_cpus=num_cpus,
    )
    sleep(1)
    workers = [WorkerActor.remote(language) for _ in range(num_cpus)]

    df = pd.read_pickle(repositories_lang_sample_pickle_path(language))

    tasks = df["Name with Owner"]

    pbar = rtqdm(total=len(tasks), desc=language)
    pbar.update(0)

    res = {}
    pre_tasks, leave_tasks = tasks[:num_cpus], tasks[num_cpus:]

    for task, worker in rtqdm(zip(pre_tasks, workers)):
        res[worker.process_repository.remote(task)] = worker, task

    for task in leave_tasks:
        done_id, _ = ray.wait(list(res), num_returns=1)
        worker, fin_task = res.pop(done_id[0])
        res[worker.process_repository.remote(task)] = worker, task
        lang_logger.info(f"DONE: {fin_task}")
        pbar.update(1)

    for _ in range(len(res)):
        done_id, _ = ray.wait(list(res), num_returns=1)
        worker, fin_task = res.pop(done_id[0])
        lang_logger.info(f"DONE: {fin_task}")
        pbar.update(1)

    pbar.close()

    sleep(1)

    ray.shutdown()

    lang_logger.info("Done!")


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
        help="The number of CPUs to use.",
        type=int,
        default=10,
    )
    language = parser.parse_args().language
    num_cpus = parser.parse_args().num_cpus

    collect_lambda_ray(language, num_cpus)
