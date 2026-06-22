import os
import re
import shutil
from time import sleep
from typing import Generator, Iterator

import git

from .config import repositories_path, get_repo_url

DIFF_PATTERN_COMPILER = re.compile("([ADMCR])[0-9]*\t(.*)")
TWO_FILES_PATTERN_COMPILER = re.compile("(.*)\t(.*)")


def clone_git_repo(name_with_owner: str, language: str) -> git.Repo:
    """
    git リポジトリをクローンする\n
    保存場所は repositories/owner/name\n
    成功時， git.Repo を返し，失敗時 エラー を返す\n
    ここで1秒スリープ
    """
    url = get_repo_url(name_with_owner, language)

    to_path = repositories_path(language, name_with_owner)
    repo = git.Repo.clone_from(url, to_path, no_checkout=True)
    sleep(1)

    # match language:
    #     case "java":
    #         repo.git.sparse_checkout("set", "--no-cone", "*.java", "!*.java/")
    #     case "javascript":
    #         repo.git.sparse_checkout("set", "--no-cone", "*.js", "!*.js/")
    #     case "ruby":
    #         repo.git.sparse_checkout("set", "--no-cone", "*.rb", "!*.rb/")
    #     case "php":
    #         repo.git.sparse_checkout("set", "--no-cone", "*.php", "!*.php/")
    #     case "csharp":
    #         repo.git.sparse_checkout("set", "--no-cone", "*.cs", "!*.cs/")
    #     case "cpp":
    #         repo.git.sparse_checkout("set", "--no-cone", "*.cpp", "!*.cpp/")
    #     case _:
    #         raise ValueError(f"Unsupported language: {language}")

    # repo.git.checkout()

    return repo


def get_repo(name_with_owner: str, language: str) -> git.Repo:
    """
    git リポジトリを取得する\n
    """
    to_path = repositories_path(language, name_with_owner)
    if not to_path.exists():
        raise FileNotFoundError(f"Repository not found: {name_with_owner}")
    else:
        repo = git.Repo(str(to_path))
        return repo


def del_repo(name_with_owner: str, language: str):
    """リポジトリを削除する．\n config.del_repositories_flagが立っていたらオナーのディレクトリから削除．\n 立っていないならプロジェクトのディレクトリのみ削除．"""
    repo_dir = repositories_path(language, name_with_owner)
    top_dir = repo_dir.parent

    if repo_dir.exists():
        shutil.rmtree(repo_dir, ignore_errors=True)

    list_dir = os.listdir(top_dir)
    if list_dir == [] or list_dir == [".DS_Store"]:
        shutil.rmtree(top_dir, ignore_errors=True)


def get_diff(commit: git.Commit, extension: str) -> str:
    diff = commit.repo.git.diff(
        commit.parents[0],
        commit,
        "--name-status",
        "--diff-filter=MRC",
        f"*.{extension}",
    )
    return diff


def get_diff_ray(dir_pth: str, commit_hexsha: str, extension: str) -> str:
    repo = git.Repo(dir_pth)
    commit = repo.commit(commit_hexsha)
    diff = commit.repo.git.diff(
        commit.parents[0],
        commit,
        "--name-status",
        "--diff-filter=MRC",
        f"*.{extension}",
    )
    return diff


def diff_codes_generator(diff: str) -> Generator[tuple[str, str], None, None]:
    change_symbol_and_file_tuples = DIFF_PATTERN_COMPILER.findall(diff)

    for change_symbol, file in change_symbol_and_file_tuples:
        if change_symbol == "M":
            yield file, file
        else:
            # change_symbol == "R" or change_symbol == "C"
            yield TWO_FILES_PATTERN_COMPILER.findall(file)[0]


class DiffCodesGenerator:
    def __init__(self, diff: str):
        self.change_symbol_and_file_tuples = DIFF_PATTERN_COMPILER.findall(diff)

    def __iter__(self) -> Iterator[tuple[str, str]]:
        for change_symbol, file in self.change_symbol_and_file_tuples:
            if change_symbol == "M":
                yield file, file
            else:
                # change_symbol == "R" or change_symbol == "C"
                yield TWO_FILES_PATTERN_COMPILER.findall(file)[0]

    def __len__(self) -> int:
        return len(self.change_symbol_and_file_tuples)


def get_past_contents(commit: git.Commit, file: str) -> str:
    return commit.repo.git.show(f"{commit.hexsha}:{file}")


def get_developers_count(repo: git.Repo) -> int:
    return len(repo.git.shortlog("-sn", "HEAD").splitlines())


def get_commit_count_after_introduction(repo: git.Repo, introduction_date: str) -> int:
    return int(repo.git.rev_list("--count", f"--since={introduction_date}", "HEAD"))
