"""Enforces the Clean Architecture dependency rule by scanning imports in each layer."""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"

FRAMEWORKS = {"fastapi", "starlette", "sqlalchemy", "alembic"}
FORBIDDEN: dict[str, set[str]] = {
    "domain": FRAMEWORKS
    | {"pydantic", "pydantic_settings", "app.api", "app.application", "app.infrastructure"},
    "application": FRAMEWORKS | {"app.api", "app.infrastructure"},
    "infrastructure": {"fastapi", "starlette", "app.api"},
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_does_not_depend_on_outer_layers(layer: str) -> None:
    violations = [
        f"{file.relative_to(APP)} imports {name}"
        for file in (APP / layer).rglob("*.py")
        for name in _imports(file)
        if any(name == bad or name.startswith(bad + ".") for bad in FORBIDDEN[layer])
    ]
    assert not violations, "\n".join(violations)
