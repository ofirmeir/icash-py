import os
import logging
import configparser
import sys


def setup_logging(config_path: str = "log.cfg"):
    cfg = configparser.ConfigParser()
    level_name = "INFO"
    if os.path.exists(config_path):
        try:
            cfg.read(config_path)
            level_name = cfg.get("logging", "level", fallback=level_name).upper()
        except Exception:
            level_name = "INFO"
    else:
        level_name = os.getenv("LOG_LEVEL", level_name).upper()

    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(level)
    root.info("Logging initialized from %s with level %s", config_path, level_name)

