from typing import Any, Dict
import yaml


class Configurable:
    """Base class for objects that can be configured and serialized to/from YAML.

    Methods:
        to_yaml: Serialize the object to YAML format.
        from_yaml: Deserialize the object from a YAML string.
        from_dict: Create an object from a dictionary.

    """

    def to_yaml(self) -> str:
        """Serialize the object to a YAML-formatted string.

        Returns:
            str: YAML representation of the object.
        """
        cls_name = type(self).__name__
        data = {
            cls_name: {k: v for k, v in vars(self).items() if not k.startswith("__")}
        }
        yml = yaml.safe_dump(data)
        return yml

    @classmethod
    def from_yaml(cls, yml: str) -> Any:
        """Deserialize an object from a YAML-formatted string.

        Args:
            yml (str): YAML-formatted string.

        Returns:
            Any: Deserialized object.
        """
        d = yaml.safe_load(yml).get(cls.__name__)
        return Configurable.from_dict(d)

    @classmethod
    def from_dict(cls, d: Dict[Any, Any]) -> Any:
        """Create an object from a dictionary.

        Args:
            d (Dict[Any, Any]): Dictionary containing attribute values.

        Returns:
            Any: Created parent object.
        """
        c = cls(**d)
        return c
