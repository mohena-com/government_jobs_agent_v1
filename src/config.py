from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "app_config.yaml"


def load_config(path=CONFIG_PATH):
    with Path(path).open(encoding="utf-8") as config_file:
        values = yaml.safe_load(config_file) or {}

    if not isinstance(values, dict):
        raise ValueError(f"Configuration must be a YAML mapping: {path}")

    return values
