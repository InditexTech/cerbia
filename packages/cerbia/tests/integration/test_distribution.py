import re
import tomllib
from importlib.metadata import distribution
from pathlib import Path

import pytest

INTERNAL_REQUIREMENT = re.compile(r"cerbia(?:-[A-Za-z0-9_.-]+)?==(?P<version>.+)")

pytestmark = pytest.mark.integration


def test_workspace_packages_share_a_version_and_internal_pins() -> None:
    workspace = Path(__file__).parents[4]
    manifests = sorted(workspace.glob("packages/*/pyproject.toml"))
    documents = [tomllib.loads(manifest.read_text()) for manifest in manifests]
    versions = {document["project"]["version"] for document in documents}

    assert len(versions) == 1

    version = versions.pop()
    internal_pin_version = version.partition(".dev")[0]
    for document in documents:
        project = document["project"]
        requirements = [*project.get("dependencies", [])]
        for optional_requirements in project.get("optional-dependencies", {}).values():
            requirements.extend(optional_requirements)

        for requirement in requirements:
            name = requirement.partition("==")[0]
            match = INTERNAL_REQUIREMENT.fullmatch(requirement)
            if name == "cerbia" or name.startswith("cerbia-"):
                assert match is not None
                assert match["version"] == internal_pin_version


def test_distribution_declares_supported_extras() -> None:
    metadata = distribution("cerbia").metadata

    assert metadata["Name"] == "cerbia"
    assert set(metadata.get_all("Provides-Extra", [])) == {
        "all",
        "cli",
        "ml",
        "presidio",
        "protectai",
    }
