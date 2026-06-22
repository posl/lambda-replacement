from logging import INFO, FileHandler, getLogger
from typing import Optional

import pandas as pd
from tqdm import tqdm
from git import GitCommandError

from .git_operate import (
    clone_git_repo,
    get_developers_count,
    get_commit_count_after_introduction,
)
from .config import (
    repositories_lang_path,
    CSV_DIR,
    PICKLE_DIR,
    LOG_DIR,
    LANGUAGES,
    get_introduction_date,
)

SAMPLE_SIZE = 500
DEVELOPERS_COUNT_THRESHOLD = 2
COMMIT_COUNT_AFTER_INTRODUCTION_THRESHOLD = 100

logger = getLogger("get_repositories")
logger.setLevel(INFO)

if not logger.handlers:
    handler = FileHandler(LOG_DIR / "get_repositories.log")
    handler.setLevel(INFO)
    logger.addHandler(handler)


def is_valid_repository(
    developers_count: int,
    commit_count: int,
) -> bool:
    return (
        developers_count >= DEVELOPERS_COUNT_THRESHOLD
        and commit_count >= COMMIT_COUNT_AFTER_INTRODUCTION_THRESHOLD
    )


def get_repositories(
    language: str,
    sample_size: int = SAMPLE_SIZE,
    df: Optional[pd.DataFrame] = None,
    save_flag: bool = True,
) -> pd.DataFrame:
    logger.info(f"Processing language: {language}")

    if df is None:
        update_df_path = PICKLE_DIR / f"repositories_{language}_updated.pkl"

        if update_df_path.exists():
            df = pd.read_pickle(update_df_path)
        else:
            df = pd.read_pickle(repositories_lang_path(language, "pkl"))

            df.loc[:, "available"] = pd.NA
            df.loc[:, "clone_date"] = pd.NaT
            df.loc[:, "developers_count"] = pd.NA
            df.loc[:, "commit_count_after_introduction"] = pd.NA

    success_count = 0

    introduction_date = get_introduction_date(language)

    selected_indexes = []

    pbar = tqdm(df.index, total=len(df), desc=f"{language}")

    updates = []

    for name_with_owner in pbar:
        if success_count >= sample_size:
            break

        if pd.notna(df.at[name_with_owner, "available"]):
            if is_valid_repository(
                df.at[name_with_owner, "developers_count"],
                df.at[name_with_owner, "commit_count_after_introduction"],
            ):
                selected_indexes.append(name_with_owner)
                success_count += 1
                pbar.set_postfix(success=success_count)
            continue

        try:
            repo = clone_git_repo(
                name_with_owner=name_with_owner,
                language=language,
            )
            clone_date = pd.Timestamp.now()
        except GitCommandError as e:
            updates.append(
                {
                    "index": name_with_owner,
                    "available": False,
                }
            )
            logger.warning(
                f"Error occurred while fetching repository: {name_with_owner}",
                exc_info=e,
            )
            continue
        except Exception as e:
            updates.append(
                {
                    "index": name_with_owner,
                    "available": False,
                }
            )
            logger.error(f"Unexpected error occurred: {name_with_owner}", exc_info=e)
            continue

        developers_count = get_developers_count(repo)
        commit_count_after_introduction = get_commit_count_after_introduction(
            repo, introduction_date
        )

        updates.append(
            {
                "index": name_with_owner,
                "available": True,
                "clone_date": clone_date,
                "developers_count": developers_count,
                "commit_count_after_introduction": commit_count_after_introduction,
            }
        )

        if not is_valid_repository(developers_count, commit_count_after_introduction):
            logger.warning(
                f"Repository {name_with_owner} does not meet the validity criteria. {developers_count=}, {commit_count_after_introduction=}."
            )
            continue

        selected_indexes.append(name_with_owner)
        success_count += 1
        pbar.set_postfix(success=success_count)

    update_df = pd.DataFrame(updates).set_index("index")
    for col in update_df.columns:
        df.loc[update_df.index, col] = update_df[col]

    result_df = df.loc[selected_indexes].copy()

    assert len(result_df) == sample_size

    result_df["developers_count"] = result_df["developers_count"].astype(int)
    result_df["clone_date"] = pd.to_datetime(result_df["clone_date"])
    result_df["commit_count_after_introduction"] = result_df[
        "commit_count_after_introduction"
    ].astype(int)

    if save_flag:
        result_df.to_pickle(PICKLE_DIR / f"repositories_{language}_sample.pkl")
        result_df.to_csv(CSV_DIR / f"repositories_{language}_sample.csv")

    df.to_pickle(PICKLE_DIR / f"repositories_{language}_updated.pkl")
    df.to_csv(CSV_DIR / f"repositories_{language}_updated.csv")

    logger.info(
        f"Done sample data processing. Total successful repositories: {success_count}"
    )

    return result_df


if __name__ == "__main__":
    for language in LANGUAGES:
        get_repositories(language)
