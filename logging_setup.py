# ログ設定モジュール
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_NAME = "DesignSupportTool"


def get_app_base_dir() -> Path:
    """アプリの基準ディレクトリ（開発時=ソース階層、ビルド後=exe のあるフォルダ）"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = get_app_base_dir()
LOG_DIR = BASE_DIR / "log"
LOG_FILE = LOG_DIR / "design_support_tool.log"


def setup_logger(name: str = APP_NAME) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except OSError as e:
        logger.warning(
            "ログファイルを作成できません: path=%s error=%s",
            LOG_FILE,
            e,
        )

    logger.debug(
        "ログ初期化完了: frozen=%s base_dir=%s log_file=%s",
        getattr(sys, "frozen", False),
        BASE_DIR,
        LOG_FILE,
    )
    return logger


logger = setup_logger()
