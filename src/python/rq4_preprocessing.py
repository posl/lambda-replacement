import pandas as pd
from retry.api import retry_call
from tqdm.auto import tqdm
import bisect
from git import Repo
from pathlib import Path

from config import (
    RESULT_DIR,
    DATA_DIR,
    get_extensions,
    project_replacement_path,
    LANGUAGES,
)
from git_operate import get_repo

URL_TEMPLATE = "https://github.com/{name_with_owner}/commit/{commit}"


def remove_non_ascii(s):
    return "".join(c for c in s if ord(c) < 128 and c != "\r")


def fetch_file(repo: Repo, rev: str, path: str) -> str:
    return remove_non_ascii(
        retry_call(repo.git.show, fargs=[f"{rev}:{path}"], tries=5, delay=1)
    )


def save_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def build_url(name_with_owner: str, commit: str) -> str:
    return URL_TEMPLATE.format(
        name_with_owner=name_with_owner.replace("_", "/", 1),
        commit=commit,
    )


def calculate_line_offsets(source_code: str) -> list[int]:
    """
    Calculates the start offsets for each line in the source code.

    Args:
        source_code (str): The full source code as a string.

    Returns:
        list[int]: A list of line start offsets.
    """
    offsets = [0]
    current_offset = 0

    for line in source_code.splitlines(keepends=True):
        current_offset += len(line)
        offsets.append(current_offset)

    return offsets


def position_for(offset: int, source_code: str) -> tuple[int, int]:
    """
    Converts an offset into a (line, column) position based on the source code.

    Args:
        offset (int): The offset in the source code string.
        source_code (str): The full source code as a string.

    Returns:
        tuple: (line, column), both starting from 1.
    """
    lines = calculate_line_offsets(source_code)
    line = bisect.bisect_right(lines, offset) - 1
    column = offset - lines[line] + 1

    return line + 1, column


def match_replacement_to_delete(language: str) -> pd.DataFrame:
    all_df = pd.DataFrame()

    base_dir = RESULT_DIR / "lambda_delete_matching" / language
    delete_matching_paths = sorted(base_dir.glob("*/**/*.csv"))

    for delete_matching_path in delete_matching_paths:
        delete_matching_df = pd.read_csv(delete_matching_path)

        name_with_owner = (
            f"{delete_matching_path.parent.name}/{delete_matching_path.stem}"
        )

        lambda_replacement_df = pd.read_pickle(
            project_replacement_path(language, name_with_owner)
        )

        lambda_replacement_df = lambda_replacement_df.astype(
            {
                "src start pos": "int",
                "src end pos": "int",
                "dst start pos": "int",
                "dst end pos": "int",
            }
        )

        lambda_replacement_df.to_pickle(
            project_replacement_path(language, name_with_owner)
        )

        merged_df = (
            delete_matching_df.merge(
                lambda_replacement_df[
                    [
                        "commit",
                        "dst file",
                        "src file",
                        "src start pos",
                        "src end pos",
                        "dst start pos",
                        "dst end pos",
                    ]
                ],
                left_on=[
                    "insert commit",
                    "insert dst file",
                    "insert dst start pos",
                    "insert dst end pos",
                ],
                right_on=["commit", "dst file", "dst start pos", "dst end pos"],
                how="inner",
            )
            .drop(columns=["commit", "dst file", "dst start pos", "dst end pos"])
            .rename(
                columns={
                    "src file": "insert src file",
                    "src start pos": "insert src start pos",
                    "src end pos": "insert src end pos",
                }
            )
        )

        merged_df = (
            merged_df.merge(
                lambda_replacement_df[
                    [
                        "commit",
                        "src file",
                        "src start pos",
                        "src end pos",
                        "dst file",
                    ]
                ],
                left_on=[
                    "delete commit",
                    "delete src file",
                    "delete src start pos",
                    "delete src end pos",
                ],
                right_on=["commit", "src file", "src start pos", "src end pos"],
                how="inner",
            )
            .drop(columns=["commit", "src file", "src start pos", "src end pos"])
            .rename(
                columns={
                    "dst file": "delete dst file",
                }
            )
        )

        merged_df["name_with_owner"] = name_with_owner

        all_df = pd.concat([all_df, merged_df])

    all_df = all_df.reindex(
        columns=[
            "name_with_owner",
            "insert commit",
            "insert src file",
            "insert src start pos",
            "insert src end pos",
            "insert dst file",
            "insert dst start pos",
            "insert dst end pos",
            "delete commit",
            "delete src file",
            "delete src start pos",
            "delete src end pos",
            "delete dst file",
        ],
    )

    all_df = all_df.sample(frac=1, random_state=0)
    all_df.reset_index(inplace=True, drop=True)

    return all_df


def process_row(
    row: pd.Series, repo: Repo, i: int, source_dir: Path, extension: str
) -> dict:
    name_with_owner = row["name_with_owner"]

    insert_commit = row["insert commit"]
    delete_commit = row["delete commit"]

    # --- fetch files ---
    insert_src = fetch_file(repo, f"{insert_commit}^", row["insert src file"])
    insert_dst = fetch_file(repo, insert_commit, row["insert dst file"])
    delete_src = fetch_file(repo, f"{delete_commit}^", row["delete src file"])
    delete_dst = fetch_file(repo, delete_commit, row["delete dst file"])

    # --- save ---
    save_file(source_dir / f"{i}_insert_src.{extension}", insert_src)
    save_file(source_dir / f"{i}_insert_dst.{extension}", insert_dst)
    save_file(source_dir / f"{i}_delete_src.{extension}", delete_src)
    save_file(source_dir / f"{i}_delete_dst.{extension}", delete_dst)

    # --- extract snippets ---
    def slice_(content, start, end):
        return content[start:end]

    result = {
        **row.to_dict(),
        "insert url": build_url(name_with_owner, insert_commit),
        "delete url": build_url(name_with_owner, delete_commit),
        "insert src file content": slice_(
            insert_src, row["insert src start pos"], row["insert src end pos"]
        ),
        "insert dst file content": slice_(
            insert_dst, row["insert dst start pos"], row["insert dst end pos"]
        ),
        "delete src file content": slice_(
            delete_src, row["delete src start pos"], row["delete src end pos"]
        ),
        "insert src start pos": position_for(row["insert src start pos"], insert_src),
        "insert dst start pos": position_for(row["insert dst start pos"], insert_dst),
        "delete src start pos": position_for(row["delete src start pos"], delete_src),
        "replacement_msg": repo.commit(insert_commit).message,
        "delete_msg": repo.commit(delete_commit).message,
    }

    return result


def main(language: str) -> pd.DataFrame:
    extension = get_extensions(language)

    source_dir = DATA_DIR / "rq4" / "source_codes" / language

    source_dir.mkdir(parents=True, exist_ok=True)

    df = match_replacement_to_delete(language)

    results = []

    for i, row in tqdm(df.iterrows(), total=len(df), desc=language):
        repo = get_repo(row["name_with_owner"].replace("_", "/", 1), language)
        results.append(process_row(row, repo, i, source_dir, extension))

    res_df = pd.DataFrame(results)

    res_df["coding"] = None

    res_df = res_df.reindex(
        columns=[
            "name_with_owner",
            "insert url",
            "delete url",
            "replacement_msg",
            "delete_msg",
            "coding",
            "insert commit",
            "insert src file",
            "insert src start pos",
            "insert dst file",
            "insert dst start pos",
            "delete commit",
            "delete src file",
            "delete src start pos",
            "delete dst file",
            "delete dst start pos",
            "insert src file content",
            "insert dst file content",
            "delete src file content",
        ],
    )

    res_df.to_csv(DATA_DIR / "rq4" / f"{language}.csv")

    return res_df


if __name__ == "__main__":
    for language in LANGUAGES:
        main(language)
