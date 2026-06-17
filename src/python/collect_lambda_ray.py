import argparse
import gc
import subprocess
from collections import deque
from logging import INFO, FileHandler, Logger, getLogger
from dataclasses import dataclass
from datetime import datetime


import pandas as pd
import psutil
import ray
from git import Commit, GitCommandError
from ray.experimental.tqdm_ray import tqdm as rtqdm

from .git_operate import DiffCodesGenerator, get_diff, get_repo
from .config import (
    JAR_PATH,
    repositories_lang_sample_acc_path,
    project_replacement_path,
    lambda_replacement_log_path,
    get_extensions,
    get_introduction_date,
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
        self.introduction_date = get_introduction_date(language)
        self.extension = get_extensions(language)

    @staticmethod
    def garbage_collect(pct=80.0):
        if psutil.virtual_memory().percent >= pct:
            gc.collect()

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
            logger.error("GitCommandError", exc_info=e)
            return []

        results: list[LambdaResult] = []

        for src_file, dst_file in DiffCodesGenerator(diff):
            try:
                cmd = [
                    "java",
                    "-jar",
                    JAR_PATH,
                    self.language,
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
                        f"{commit.hexsha:}: {src_file:}, {dst_file:}",
                        exc_info=Exception(res.stderr),
                    )
                    continue
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"{commit.hexsha:}: {src_file:}, {dst_file:}", exc_info=e)
                continue

            for line in res.stdout.splitlines():
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

    def process_repository(self, name_with_owner: str, commit_count: int) -> str:
        repo_logger = self.setup_logger(
            name_with_owner.replace("/", "_"), self.language
        )
        repo_logger.info("Start!")

        try:
            repo = get_repo(name_with_owner, self.language)
        except KeyboardInterrupt:
            raise
        except Exception:
            repo_logger.exception(f"Repository not found: {name_with_owner}")
            return name_with_owner

        results: list[LambdaResult] = []

        owner, name = name_with_owner.split("/")
        desc = f"{owner[:5].ljust(7, '.')}/{name[:5].ljust(7, '.')}"

        for commit in rtqdm(
            repo.iter_commits(since=self.introduction_date),
            desc=desc,
            total=commit_count,
        ):
            if len(commit.parents) != 1:
                continue

            results.extend(
                self.process_commit(
                    commit,
                    repo_logger,
                )
            )

        self.save_results(results, name_with_owner)

        repo_logger.info("Done!")

        return name_with_owner

    def save_results(self, results: list[LambdaResult], name_with_owner: str):
        if not results:
            return

        df = pd.DataFrame([r.__dict__ for r in results])

        result_path = project_replacement_path(self.language, name_with_owner)

        result_path.parent.mkdir(parents=True, exist_ok=True)

        df.to_csv(result_path, index=False)


def collect_lambda_ray(language: str, num_cpus: int = 10):
    if num_cpus < 1:
        raise ValueError("num_cpus must be at least 1")

    lang_logger = WorkerActor.setup_logger(language, language)
    lang_logger.info("Start!")

    try:
        ray.init(
            num_cpus=num_cpus,
            ignore_reinit_error=True,
        )

        workers = [WorkerActor.remote(language) for _ in range(num_cpus)]

        df = pd.read_pickle(repositories_lang_sample_acc_path(language))
        df.sort_values("commit_count_after_introduction", inplace=True, ascending=True)

        pending_repositories = deque(df.index)

        def submit_next(worker):
            if not pending_repositories:
                return None

            name_with_owner = pending_repositories.popleft()
            commit_count = int(
                df.loc[name_with_owner, "commit_count_after_introduction"]
            )
            ref = worker.process_repository.remote(name_with_owner, commit_count)
            return ref, worker, name_with_owner

        running = {}
        for worker in workers:
            submitted = submit_next(worker)
            if submitted is None:
                break

            ref, worker, name_with_owner = submitted
            running[ref] = (worker, name_with_owner)
            lang_logger.info(f"Started repository: {name_with_owner}")

        progress_bar = rtqdm(total=len(df.index), desc=language)
        progress_bar.update(0)

        while running:
            done_refs, _ = ray.wait(list(running), num_returns=1)

            for done_ref in done_refs:
                worker, name_with_owner = running.pop(done_ref)

                try:
                    result = ray.get(done_ref)
                    lang_logger.info(f"Processed repository: {result}")
                except Exception:
                    lang_logger.exception(f"Failed repository: {name_with_owner}")

                progress_bar.update(1)

                submitted = submit_next(worker)
                if submitted is None:
                    continue

                next_ref, worker, next_name_with_owner = submitted
                running[next_ref] = (worker, next_name_with_owner)
                lang_logger.info(f"Started repository: {next_name_with_owner}")

        progress_bar.close()
        lang_logger.info("DONE!")
    finally:
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
        help="The number of CPUs to use.",
        type=int,
        default=10,
    )

    args = parser.parse_args()

    language = args.language
    num_cpus = args.num_cpus

    collect_lambda_ray(language, num_cpus)
