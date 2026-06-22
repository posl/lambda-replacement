import pandas as pd
from tqdm import tqdm

from .config import (
    DATA_DIR,
    LANGUAGES,
    PICKLE_DIR,
    CSV_DIR,
    RESULT_DIR,
    LOG_DIR,
    repositories_lang_path,
    get_introduction_date
)

CHUNK_SIZE = 100_000

LIBRARIES_HEADER = [
    "ID",
    "Host Type",
    "Name with Owner",
    "Description",
    "Fork",
    "Created Timestamp",
    "Updated Timestamp",
    "Last pushed Timestamp",
    "Homepage URL",
    "Size",
    "Stars Count",
    "Language",
    "Issues enabled",
    "Wiki enabled",
    "Pages enabled",
    "Forks Count",
    "Mirror URL",
    "Open Issues Count",
    "Default branch",
    "Watchers Count",
    "UUID",
    "Fork Source Name with Owner",
    "License",
    "Contributors Count",
    "Readme filename",
    "Changelog filename",
    "Contributing guidelines filename",
    "License filename",
    "Code of Conduct filename",
    "Security Threat Model filename",
    "Security Audit filename",
    "Status",
    "Last Synced Timestamp",
    "_1",
    "_2",
    "_3",
    "_4",
    "_5",
    "_6",
    "_7",
]

LIBRARIES_PARAMETERS = [
    "Host Type",
    "Name with Owner",
    "Fork",
    "Created Timestamp",
    # "Homepage URL",
    "Size",
    "Stars Count",
    "Language",
    # "Issues enabled",
    # "Wiki enabled",
    # "Pages enabled",
    "Forks Count",
    "Open Issues Count",
    # "Default branch",
    "Watchers Count",
    "Contributors Count",
    "License",
    "Last Synced Timestamp",
]

LIBRARIES_LICENSES = [
    "AFL-3.0",
    "AGPL-3.0",
    "Apache-2.0",
    "Artistic-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "BSL-1.0",
    "ECL-2.0",
    "EPL-1.0",
    "GPL-2.0",
    "GPL-2.0+",
    "GPL-3.0",
    "GPL-3.0+",
    "ISC",
    "LGPL-2.0",
    "LGPL-2.1",
    "LGPL-2.1+",
    "LGPL-3.0",
    "LGPL-3.0+",
    "LPPL-1.3c",
    "MIT",
    "MPL-2.0",
    "MS-PL",
    "MS-RL",
    "OFL-1.1",
    "OSL-3.0",
    "Unlicense",
    "W3C",
    "Zlib",
]  # OSI に準拠

LIBRARIES_CSV_PATH = (
    DATA_DIR / "libraries-1.6.0-2020-01-12" / "repositories-1.6.0-2020-01-12.csv"
)
LIBRARIES_PICKLE_PATH = PICKLE_DIR / "repositories.pkl"

LIBRARIES_PICKLE_DIR = PICKLE_DIR / "libraries_io"
LIBRARIES_ORIGINAL_PICKLE_DIR = LIBRARIES_PICKLE_DIR / "original"
LIBRARIES_CLEAN_PICKLE_DIR = LIBRARIES_PICKLE_DIR / "clean"


def data_preprocessing():
    """
    libraries.ioのcsv生データをpickleに変換する\n

    必要ないパラメータを除外する\n
    欠損値行を削除する\n
    フォークプロジェクトを削除する\n
    Host Type を GitHub に絞る\n
    created_time > last_synced_time のものを除外\n
    """

    if LIBRARIES_PICKLE_PATH.exists():
        repositories = pd.read_pickle(LIBRARIES_PICKLE_PATH)
    else:
        reader = pd.read_csv(
            LIBRARIES_CSV_PATH,
            skiprows=[0],
            names=LIBRARIES_HEADER,
            chunksize=CHUNK_SIZE,
            index_col="ID",
            encoding="utf-8",
            converters={
                "Mirror URL": str,
                "Security Threat Model filename": str,
                "Security Audit filename": str,
                "UUID": str,
                "Fork Source Name with Owner": str,
                "Status": str,
                "Readme filename": str,
                "Changelog filename": str,
                "Contributing guidelines filename": str,
                "License filename": str,
                "Code of Conduct filename": str,
                "_5": str,
                "_6": str,
                "_7": str,
                "Pages enabled": bool,
            },
        )

        if not LIBRARIES_ORIGINAL_PICKLE_DIR.exists():
            LIBRARIES_ORIGINAL_PICKLE_DIR.mkdir(parents=True, exist_ok=True)

        if not LIBRARIES_CLEAN_PICKLE_DIR.exists():
            LIBRARIES_CLEAN_PICKLE_DIR.mkdir(parents=True, exist_ok=True)

        chunk_dfs = []

        for i, chunk in tqdm(enumerate(reader)):
            chunk.to_pickle(LIBRARIES_ORIGINAL_PICKLE_DIR / f"chunk_{i}.pkl")

            # 必要ないパラメータを除外
            chunk_cleaned = chunk[LIBRARIES_PARAMETERS].copy()

            # 欠損値データを削除
            chunk_cleaned.dropna(subset=LIBRARIES_PARAMETERS, inplace=True)

            #  Forkプロジェクトを除外
            chunk_cleaned = chunk_cleaned[~chunk_cleaned["Fork"]]

            # フォーク数が5以上のものだけを対象
            chunk_cleaned["Forks Count"] = chunk_cleaned["Forks Count"].astype(int)
            chunk_cleaned = chunk_cleaned[chunk_cleaned["Forks Count"] >= 5]

            # ライセンスを絞る
            chunk_cleaned = chunk_cleaned[chunk_cleaned["License"].isin(LIBRARIES_LICENSES)]

            # GitHub のみ
            chunk_cleaned = chunk_cleaned[chunk_cleaned["Host Type"] == "GitHub"]

            # 必要ないので削除
            del chunk_cleaned["Fork"]
            del chunk_cleaned["License"]
            del chunk_cleaned["Host Type"]

            # 時間データをタイムスタンプ型に変換
            chunk_cleaned["Created Timestamp"] = pd.to_datetime(
                chunk_cleaned["Created Timestamp"], format="%Y-%m-%d %H:%M:%S UTC", utc=True
            )
            chunk_cleaned["Last Synced Timestamp"] = pd.to_datetime(
                chunk_cleaned["Last Synced Timestamp"],
                format="%Y-%m-%d %H:%M:%S UTC",
                utc=True,
            )

            #     # created_time > last_synced_time となっているものを除外
            #     chunk_cleaned = chunk_cleaned[~(chunk_cleaned["last_synced_time"] < chunk_cleaned["created_time"])]
            # int 型に変換
            chunk_cleaned["Watchers Count"] = chunk_cleaned["Watchers Count"].astype(int)
            chunk_cleaned["Size"] = chunk_cleaned["Size"].astype(int)
            chunk_cleaned["Stars Count"] = chunk_cleaned["Stars Count"].astype(int)
            chunk_cleaned["Open Issues Count"] = chunk_cleaned["Open Issues Count"].astype(
                int
            )

            chunk_cleaned.to_pickle(LIBRARIES_CLEAN_PICKLE_DIR / f"chunk_{i}_clean.pkl")
            chunk_dfs.append(chunk_cleaned)

        repositories = pd.concat(chunk_dfs, axis=0)

        repositories["Watchers Count"] = repositories["Watchers Count"].astype(int)
        repositories["Size"] = repositories["Size"].astype(int)
        repositories["Stars Count"] = repositories["Stars Count"].astype(int)
        repositories["Open Issues Count"] = repositories["Open Issues Count"].astype(int)

        repositories.set_index("Name with Owner", inplace=True)

        repositories.to_pickle(LIBRARIES_PICKLE_PATH)

    lang_raw = {
        "java": "Java",
        "javascript": "JavaScript",
        "ruby": "Ruby",
        "php": "PHP",
        "csharp": "C#",
        "cpp": "C++",
    }

    for language in LANGUAGES:
        language_df = repositories[repositories["Language"] == lang_raw[language]]

        introduction_date = get_introduction_date(language)

        language_df = language_df[language_df['Created Timestamp'] < introduction_date]

        language_df = language_df.sample(frac=1, random_state=42)
        language_df.set_index("Name with Owner", inplace=True)
        language_df.to_pickle(repositories_lang_path(language, "pkl"))
        language_df.to_csv(repositories_lang_path(language, "csv"))
        print(f"{language} done")


def mkdir():
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    PICKLE_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    mkdir()
    data_preprocessing()
