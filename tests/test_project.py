# ---------------------------------------------------------------------
# Gufo Labs: Project structure tests
# ---------------------------------------------------------------------
# Copyright (C) 2022-24, Gufo Labs
# See LICENSE.md for details
# ---------------------------------------------------------------------

# Python modules
import inspect
import os
import sys
from pathlib import Path
from typing import Tuple, Union

# Third-party modules
import pytest


def _get_root() -> str:
    mod_path = inspect.getfile(sys.modules[__name__])
    rel_root = os.path.dirname(mod_path)
    return os.path.abspath(os.path.join(rel_root, ".."))


def _get_project_info() -> Tuple[str, str]:
    """
    Get project information.

    Returns:
        Tuple of (project path, project module)
    """

    def explore_dir(*args: str) -> str:
        def is_not_rust(path: Path) -> bool:
            if not path.is_dir():
                return True
            return not any(path.rglob("*.rs"))

        root = Path(*args)
        d = [
            f
            for f in os.listdir(os.path.join(*args))
            if not f.startswith(".")
            and not f.startswith("_")
            and not f.endswith(".egg-info")
            and not f.endswith(".rs")
        ]
        if len(d) > 1:
            d = [x for x in d if is_not_rust(root / x)]
        assert len(d) == 1
        return d[0]

    def has_init(*args: str) -> bool:
        return Path(*(*args, "__init__.py")).exists()

    ns = explore_dir(ROOT, "src")
    if ns == "gufo":
        # gufo.* namespace
        pkg = explore_dir(ROOT, "src", ns)
        if has_init("src", ns, pkg):
            return os.path.join("src", ns, pkg), f"{ns}.{pkg}"
        pkg2 = explore_dir(ROOT, "src", ns, pkg)
        return os.path.join("src", ns, pkg, pkg2), f"{ns}.{pkg}.{pkg2}"
    return os.path.join("src", ns), ns


ROOT = _get_root()
PROJECT_SRC, PROJECT_MODULE = _get_project_info()

REQUIRED_FILES = [
    ".devcontainer/devcontainer.json",
    ".github/CODEOWNERS",
    ".github/ISSUE_TEMPLATE/bug-report.yml",
    ".github/ISSUE_TEMPLATE/feature-request.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".gitignore",
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "Dockerfile",
    "LICENSE.md",
    "README.md",
    "SECURITY.md",
    "docs/assets/logo.png",
    "docs/dev/codebase.md",
    "docs/dev/codequality.md",
    "docs/dev/common.md",
    "docs/dev/environment.md",
    "docs/dev/testing.md",
    "docs/faq.md",
    "docs/index.md",
    ("docs/installation.md", "docs/installation/index.md"),
    "mkdocs.yml",
    "pyproject.toml",
    f"{PROJECT_SRC}/__init__.py",
    f"{PROJECT_SRC}/py.typed",
    "tests/test_docs.py",
    "tests/test_project.py",
]


def test_required_is_sorted() -> None:
    def q(name: Union[str, Tuple[str, ...]]) -> Tuple[str, ...]:
        if isinstance(name, str):
            return (name,)
        return name

    normalized = [q(x) for x in REQUIRED_FILES]
    assert sorted(normalized) == normalized, "REQUIRED_FILES must be sorted"


@pytest.mark.parametrize("name", REQUIRED_FILES)
def test_required_files(name: Union[str, Tuple[str, ...]]) -> None:
    if isinstance(name, str):
        full_path = os.path.join(ROOT, name)
        assert os.path.exists(full_path), f"File {name} is missed"
    else:
        full_paths = [os.path.join(ROOT, n) for n in name]
        present = any(os.path.exists(n) for n in full_paths)
        assert present, f"Any of files {', '.join(full_paths)} must be exist"


def test_version() -> None:
    m = __import__(PROJECT_MODULE, {}, {}, "*")
    assert hasattr(m, "__version__"), "__init__.py must contain __version__"
