from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ディレクトリ
DATA_DIR = PROJECT_ROOT / "data"
PICKLE_DIR = DATA_DIR / "pickle"
CSV_DIR = DATA_DIR / "csv"
RESULT_DIR = PROJECT_ROOT / "results"
LOG_DIR = PROJECT_ROOT / "logs"

SAMPLE_SIZE = 500


def repositories_lang_sample_pickle_path(language: str) -> Path:
    return PICKLE_DIR / f"repositories_{language}_sample{SAMPLE_SIZE}.pkl"


# repositories
def repositories_path(language: str, name_with_owner: str) -> Path:
    return DATA_DIR / "repositories" / language / name_with_owner


def project_replacement_path(language: str, name_with_owner: str) -> Path:
    return RESULT_DIR / "lambda_replacement" / language / f"{name_with_owner}.pkl"


def project_delete_matching_path(language: str, name_with_owner: str) -> Path:
    return RESULT_DIR / "lambda_delete_matching" / language / f"{name_with_owner}.csv"


def lambda_replacement_log_path(language: str, name_with_owner: str) -> Path:
    return LOG_DIR / "lambda_replacement" / language / f"{name_with_owner}.log"


def lambda_delete_matching_log_path(language: str, name_with_owner: str) -> Path:
    return LOG_DIR / "lambda_delete_matching" / language / f"{name_with_owner}.log"


def jar_path(language: str) -> Path:
    return (
        PROJECT_ROOT
        / "src"
        / "java"
        / language
        / "target"
        / f"{language}-1.0-SNAPSHOT-jar-with-dependencies.jar"
    )


LANGUAGES = ["java", "javascript", "ruby", "php", "csharp", "cpp"]


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
