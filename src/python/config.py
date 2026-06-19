import os

from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ディレクトリ
DATA_DIR = PROJECT_ROOT / "data"
PICKLE_DIR = DATA_DIR / "pickle"
CSV_DIR = DATA_DIR / "csv"
RESULT_DIR = PROJECT_ROOT / "results"
LOG_DIR = PROJECT_ROOT / "logs"
TMP_DIR = PROJECT_ROOT / "tmp"


SAMPLE_SIZE = 500


def repositories_lang_path(language: str, extension: str = "pkl") -> Path:
    match extension:
        case "csv":
            return CSV_DIR / f"repositories_{language}.csv"
        case "pkl":
            return PICKLE_DIR / f"repositories_{language}.pkl"
        case _:
            raise ValueError(f"Unsupported extension: {extension}")


def repositories_lang_sample_path(language: str, extension: str = "pkl") -> Path:
    match extension:
        case "csv":
            return CSV_DIR / f"repositories_{language}_sample.csv"
        case "pkl":
            return PICKLE_DIR / f"repositories_{language}_sample.pkl"
        case _:
            raise ValueError(f"Unsupported extension: {extension}")


def repositories_lang_sample_acc_path(language: str, extension: str = "pkl") -> Path:
    match extension:
        case "csv":
            return CSV_DIR / f"repositories_{language}_sample_acc.csv"
        case "pkl":
            return PICKLE_DIR / f"repositories_{language}_sample_acc.pkl"
        case _:
            raise ValueError(f"Unsupported extension: {extension}")


# repositories
def repositories_path(language: str, name_with_owner: str) -> Path:
    return DATA_DIR / "repositories" / language / name_with_owner


def project_replacement_path(language: str, name_with_owner: str) -> Path:
    return RESULT_DIR / "lambda_replacement" / language / f"{name_with_owner}.csv"


def project_delete_matching_path(language: str, name_with_owner: str) -> Path:
    return RESULT_DIR / "lambda_delete_matching" / language / f"{name_with_owner}.csv"


def lambda_replacement_log_path(language: str, name_with_owner: str) -> Path:
    return LOG_DIR / "lambda_replacement" / language / f"{name_with_owner}.log"


def lambda_delete_matching_log_path(language: str, name_with_owner: str) -> Path:
    return LOG_DIR / "lambda_delete_matching" / language / f"{name_with_owner}.log"


# def jar_path(language: str) -> Path:
#     return (
#         PROJECT_ROOT
#         / "src"
#         / "java"
#         / language
#         / "target"
#         / f"{language}-1.0-SNAPSHOT-jar-with-dependencies.jar"
#     )


JAR_PATH = str(
    PROJECT_ROOT
    / "src"
    / "java"
    / "core"
    / "target"
    / "lambda-replacement-core-1.0-SNAPSHOT-jar-with-dependencies.jar"
)


LANGUAGES = ["csharp", "cpp", "java", "javascript", "php", "ruby"]


def get_repo_url(name_with_owner: str, language: str) -> str:
    return f"lecun-tomoto:/hdd1/tomoto/lambda-replacement/data/repositories/{language}/{name_with_owner}"
    # GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
    # return f"https://{GITHUB_TOKEN}@github.com/{name_with_owner}.git"


def get_extensions(language: str) -> str:
    ext_dict = {
        "java": "java",
        "javascript": "js",
        "ruby": "rb",
        "php": "php",
        "csharp": "cs",
        "cpp": "cpp",
    }
    return ext_dict[language]


def get_introduction_date(language: str) -> str:
    introduction_date_dict = {
        "cpp": "2011-8-12",
        "csharp": "2007-11-19",
        "java": "2014-03-18",
        "javascript": "2015-06-17",
        "php": "2019-11-28",
        "ruby": "2009-01-30",
    }
    return introduction_date_dict[language]


def get_language_title(language: str):
    title_dict = {
        "java": "Java",
        "javascript": "JavaScript",
        "cpp": "C++",
        "csharp": "C#",
        "php": "PHP",
        "ruby": "Ruby",
    }
    return title_dict[language]
