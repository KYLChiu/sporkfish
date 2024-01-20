import functools
from typing import Dict

import yaml


@functools.lru_cache(1)
def load_config() -> Dict:
    with open("config.yml", "r") as ymlfile:
        d: Dict = yaml.safe_load(ymlfile)
        return d
