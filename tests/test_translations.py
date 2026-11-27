"""Keep every translation file in step with strings.json."""

import json
from pathlib import Path
import re

import pytest

COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "concept2"
STRINGS = json.loads((COMPONENT_DIR / "strings.json").read_text(encoding="utf-8"))
TRANSLATION_FILES = sorted((COMPONENT_DIR / "translations").glob("*.json"))
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _flatten(node: dict, prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        else:
            flat[path] = value
    return flat


BASE = _flatten(STRINGS)


@pytest.mark.parametrize("path", TRANSLATION_FILES, ids=lambda p: p.name)
def test_translation_matches_strings_keys(path: Path) -> None:
    """A translation has exactly the keys that strings.json has."""
    translated = _flatten(json.loads(path.read_text(encoding="utf-8")))

    assert sorted(BASE.keys() - translated.keys()) == [], "missing keys"
    assert sorted(translated.keys() - BASE.keys()) == [], "extra keys"


@pytest.mark.parametrize("path", TRANSLATION_FILES, ids=lambda p: p.name)
def test_translation_keeps_placeholders(path: Path) -> None:
    """A translated string keeps the same {placeholders} as the source."""
    translated = _flatten(json.loads(path.read_text(encoding="utf-8")))

    for key, source in BASE.items():
        assert set(PLACEHOLDER.findall(translated[key])) == set(
            PLACEHOLDER.findall(source)
        ), key
