from logging import INFO, FileHandler, Logger, getLogger

import pandas as pd
from tqdm import tqdm
from git import GitCommandError

from .git_operate import get_repo
from .config import (
    repositories_lang_path,
    repositories_lang_sample_path,
    CSV_DIR,
    PICKLE_DIR,
    LANGUAGES,
    LOG_DIR,
    get_introduction_date,
)
from .get_repositories import get_repositories

SAMPLE_SIZE = 500

logger = getLogger("get_repositories_acc")
logger.setLevel(INFO)

if not logger.handlers:
    handler = FileHandler(LOG_DIR / "get_repositories_acc.log")
    handler.setLevel(INFO)
    logger.addHandler(handler)


def get_repositories_acc(language: str, sample_size: int = SAMPLE_SIZE) -> pd.DataFrame:
    logger.info(f"Processing language: {language}")

    df = pd.read_pickle(repositories_lang_sample_path(language, "pkl"))

    success_count = 0

    introduction_date = get_introduction_date(language)

    selected_indexes = []

    pbar = tqdm(df.index, total=len(df), desc=f"{language}")

    for name_with_owner in pbar:
        if success_count >= sample_size:
            break

        try:
            clone_date = pd.Timestamp.now()
            repo = get_repo(
                name_with_owner=name_with_owner,
                language=language,
            )
        except GitCommandError as e:
            logger.warning(f"Error occurred while fetching repository: {name_with_owner}", exc_info=e)
            continue
        except Exception as e:
            logger.error(f"Unexpected error occurred: {name_with_owner}", exc_info=e)
            continue

        developers = repo.git.shortlog("HEAD", "-sn")
        developers_count = developers.count("\n") + 1

        if developers_count < 2:
            continue

        df.loc[name_with_owner, "clone_date"] = clone_date
        df.loc[name_with_owner, "developers_count"] = developers_count
        df.loc[name_with_owner, "commit_count_after_introduction"] = repo.git.rev_list(
            "--count",
            f"--since={introduction_date}",
            "HEAD"
        )

        selected_indexes.append(name_with_owner)
        success_count += 1
        pbar.set_postfix(success=success_count)

    logger.info(f"Done sample data processing. Total successful repositories: {success_count}")


    result_df = df.loc[selected_indexes]

    lang_df = pd.read_pickle(repositories_lang_path(language, "pkl"))

    tmp_df = lang_df.loc[lang_df.index.difference(result_df.index)]
    tmp_df = tmp_df.sample(frac=1, random_state=42)

    new_sample = get_repositories(language, sample_size - success_count, df=tmp_df, save_flag=False)

    for name_with_owner in new_sample.index:
        logger.info(f"Adding repository: {name_with_owner}")

    result_df = pd.concat([result_df, new_sample], axis=0)

    assert len(result_df) == sample_size

    result_df["developers_count"] = result_df["developers_count"].astype(int)
    result_df["clone_date"] = pd.to_datetime(result_df["clone_date"])
    result_df["commit_count_after_introduction"] = result_df["commit_count_after_introduction"].astype(int)

    result_df.to_pickle(PICKLE_DIR / f"repositories_{language}_sample_acc.pkl")
    result_df.to_csv(CSV_DIR / f"repositories_{language}_sample_acc.csv")

    return result_df


if __name__ == "__main__":
    for language in LANGUAGES:
        get_repositories_acc(language)
