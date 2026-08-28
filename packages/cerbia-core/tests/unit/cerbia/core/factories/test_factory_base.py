import pytest
from cerbia.core.config import ComponentConfig
from cerbia.core.factories.base import Factory
from cerbia.core.factories.exceptions import FactoryError

pytestmark = pytest.mark.unit


class _FactoryStubConfig(ComponentConfig):
    @property
    def component(self) -> str:
        return f"{__name__}._ComponentStub"


class _NonCompliantFactoryStubConfig(ComponentConfig):
    @property
    def component(self) -> str:
        return "builtins.str"


class _ComponentStub:
    def __init__(self, data: str | None = None) -> None:
        self.data = data


class _FactoryStub(Factory[_FactoryStubConfig, _ComponentStub]):
    """A stub factory for testing purposes that creates instances of _ComponentStub."""

    @classmethod
    def get_output_type(cls) -> type[_ComponentStub]:
        return _ComponentStub


class _NonCompliantFactoryStub(Factory[_NonCompliantFactoryStubConfig, _ComponentStub]):
    """A stub factory for testing purposes that creates instances of _ComponentStub."""

    @classmethod
    def get_output_type(cls) -> type[_ComponentStub]:
        return _ComponentStub


def test_factory_base_import_class_imports_class_when_module_and_class_exist() -> None:
    result = Factory._import_class("builtins.str")

    assert result is str


def test_factory_base_import_class_raises_factory_error_when_module_or_class_missing() -> None:
    with pytest.raises(FactoryError, match="fully qualified dotted path"):
        Factory._import_class("str")


def test_factory_base_import_class_raises_factory_error_when_module_missing() -> None:
    with pytest.raises(FactoryError, match="Cannot import module 'missing_module'"):
        Factory._import_class("missing_module.Component")


def test_factory_base_import_class_raises_factory_error_when_class_missing() -> None:
    with pytest.raises(FactoryError, match="Class 'MissingClass' not found"):
        Factory._import_class("builtins.MissingClass")


def test_factory_base_verify_does_not_raise_when_instance_satisfies_expected_type() -> None:
    instance = "value"

    result = Factory._verify(instance, str, "builtins.str")

    assert result is None


def test_factory_base_verify_raises_factory_error_when_instance_does_not_satisfy_expected_type() -> None:
    with pytest.raises(FactoryError, match="produced str which does not satisfy int"):
        Factory._verify("value", int, "builtins.str")


def test_factory_base_build_returns_instance_when_class_builds_and_satisfies_contract() -> None:
    config = _FactoryStubConfig()
    result = _FactoryStub.build(config)

    assert isinstance(result, _ComponentStub)
    assert result.data is None


def test_factory_base_build_forwards_init_args_to_constructor() -> None:
    config = _FactoryStubConfig(init_args={"data": "value"})
    result = _FactoryStub.build(config)

    assert result.data == "value"


def test_factory_base_build_overrides_config_init_args_when_override_is_supported() -> None:
    config = _FactoryStubConfig(init_args={"data": "configured"})

    result = _FactoryStub.build(config, data="overridden")

    assert result.data == "overridden"
    assert config.init_args == {"data": "configured"}


def test_factory_base_build_ignores_runtime_overrides_when_constructor_does_not_accept_them() -> None:
    config = _FactoryStubConfig(init_args={"data": "configured"})

    result = _FactoryStub.build(config, unsupported="value")

    assert result.data == "configured"


def test_factory_base_build_raises_factory_error_when_class_builds_but_does_not_satisfy_contract() -> None:
    with pytest.raises(FactoryError, match="does not satisfy _ComponentStub"):
        _NonCompliantFactoryStub.build(_NonCompliantFactoryStubConfig())


def test_factory_base_build_raises_type_error_when_class_build_fails_due_to_invalid_init_args() -> None:
    with pytest.raises(TypeError):
        _FactoryStub.build(_FactoryStubConfig(init_args={"invalid_arg": "value"}))
