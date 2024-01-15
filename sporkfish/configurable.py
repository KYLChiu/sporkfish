from typing import Dict, Any
import yaml


def default_representer(dumper: yaml.Dumper, data: Any) -> yaml.ScalarNode:
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))


yaml.representer.SafeRepresenter.add_representer(None, default_representer)  # type: ignore


class Configurable:
    def to_yaml(self) -> str:
        cls_name = type(self).__name__
        data = {
            cls_name: {k: v for k, v in vars(self).items() if not k.startswith("__")}
        }
        yml = yaml.safe_dump(data)
        return yml

    @classmethod
    def from_yaml(cls, yml: str) -> Any:
        d = yaml.safe_load(yml).get(cls.__name__)
        return Configurable.from_dict(d)

    @classmethod
    def from_dict(cls, d: Dict[Any, Any]) -> Any:
        c = cls(**d)
        return c
