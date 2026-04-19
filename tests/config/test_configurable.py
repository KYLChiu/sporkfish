import pytest

from sporkfish.configurable import Configurable


class DummyConfig(Configurable):
    def __init__(self, foo: int, bar: str = "x") -> None:
        self.foo = foo
        self.bar = bar


class TestConfigurable:
    def test_to_yaml_serializes_public_attributes(self) -> None:
        cfg = DummyConfig(foo=3, bar="abc")

        yml = cfg.to_yaml()

        assert "DummyConfig" in yml
        assert "foo: 3" in yml
        assert "bar: abc" in yml

    def test_from_dict_builds_subclass(self) -> None:
        cfg = DummyConfig.from_dict({"foo": 7, "bar": "z"})

        assert isinstance(cfg, DummyConfig)
        assert cfg.foo == 7
        assert cfg.bar == "z"

    def test_from_yaml_currently_raises_for_subclass(self) -> None:
        # from_yaml delegates to Configurable.from_dict rather than cls.from_dict,
        # so subclass reconstruction currently raises for non-empty payloads.
        with pytest.raises(TypeError):
            DummyConfig.from_yaml("DummyConfig:\n  foo: 1\n  bar: q\n")
