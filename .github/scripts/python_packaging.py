#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_LOCAL_SOURCE_LAMBDAS = {
    "lambdas/indexer",
}
INTERNAL_DEPENDENCY_NAMES = {
    "quilt3",
    "quilt-shared",
    "t4-lambda-shared",
}
T4_LAMBDA_SHARED_DEPENDENCY = "t4-lambda-shared"
T4_LAMBDA_SHARED_SOURCE_URL = "https://github.com/quiltdata/quilt/archive/d496dffbfb4b7a2ae05f6c1f7f0cb7d5d43bc984.zip"
PROD_DOCKERFILES = (
    REPO_ROOT / "lambdas/indexer/Dockerfile",
    REPO_ROOT / "lambdas/tabular_preview/Dockerfile",
    REPO_ROOT / "lambdas/thumbnail/Dockerfile",
)


def load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text())


def normalize_name(name: str) -> str:
    return name.lower().replace("_", "-")


def dependency_name(raw_dependency: str) -> str:
    base = raw_dependency.split(";", 1)[0].strip()
    if "@" in base:
        base = base.split("@", 1)[0].strip()
    match = re.match(r"^[A-Za-z0-9_.-]+", base)
    return normalize_name(match.group(0) if match else base)


def iter_lambda_pyprojects() -> list[Path]:
    return sorted((REPO_ROOT / "lambdas").glob("*/pyproject.toml"))


def path_source_targets_for(project_dir: Path) -> list[Path]:
    pyproject = load_toml(project_dir / "pyproject.toml")
    sources = ((pyproject.get("tool") or {}).get("uv") or {}).get("sources") or {}
    targets: list[Path] = []
    for source in sources.values():
        if not isinstance(source, dict):
            continue
        path = source.get("path")
        if not isinstance(path, str):
            continue
        target = (project_dir / path).resolve()
        if not target.exists():
            raise FileNotFoundError(f"Local source path does not exist: {target}")
        targets.append(target)
    return targets


def iter_internal_source_entries(pyproject: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    sources = ((pyproject.get("tool") or {}).get("uv") or {}).get("sources") or {}
    rows: list[tuple[str, dict[str, Any]]] = []
    for dependency, source in sorted(sources.items()):
        if normalize_name(dependency) not in INTERNAL_DEPENDENCY_NAMES or not isinstance(source, dict):
            continue
        rows.append((dependency, source))
    return rows


def is_pinned_t4_shared_source(source: dict[str, Any]) -> bool:
    return (
        source.get("url") == T4_LAMBDA_SHARED_SOURCE_URL
        and source.get("subdirectory") == "lambdas/shared"
        and "path" not in source
        and source.get("workspace") is not True
        and source.get("editable") is not True
    )


def iter_dependency_entries(pyproject: dict[str, Any]) -> list[str]:
    project = pyproject.get("project", {})
    entries = list(project.get("dependencies") or [])
    for deps in (project.get("optional-dependencies") or {}).values():
        entries.extend(deps or [])
    for deps in (pyproject.get("dependency-groups") or {}).values():
        entries.extend(deps or [])
    return [entry for entry in entries if isinstance(entry, str)]


def guardrails() -> int:
    failures: list[str] = []

    py_ci = (REPO_ROOT / ".github/workflows/py-ci.yml").read_text()
    for needle in (
        'python .github/scripts/python_packaging.py guardrails',
        'req_dir="$RUNNER_TEMP/lambda-requirements/${{ matrix.path }}"',
        'uv export --locked --no-emit-project --no-emit-local --no-hashes --directory lambdas/${{ matrix.path }} -o "$req_dir/requirements.txt" --no-default-groups',
        'uv export --locked --no-emit-project --no-emit-local --no-hashes --directory lambdas/${{ matrix.path }} -o "$req_dir/test-requirements.txt" --only-group test',
        'mapfile -t local_targets < <(python .github/scripts/python_packaging.py install-targets "lambdas/${{ matrix.path }}")',
        'python -m pip install -t deps --no-deps -r "$req_dir/requirements.txt" "${local_targets[@]}" lambdas/${{ matrix.path }}',
        'python -m pip install -r "$req_dir/test-requirements.txt"',
    ):
        if needle not in py_ci:
            failures.append(f".github/workflows/py-ci.yml is missing expected packaging contract: {needle}")

    build_zip = (REPO_ROOT / "lambdas/scripts/build_zip.sh").read_text()
    if (
        'uv export --locked --no-emit-project --no-emit-local --no-hashes --directory "$FUNCTION_DIR" -o "$requirements_file" --no-default-groups'
        not in build_zip
    ):
        failures.append("lambdas/scripts/build_zip.sh no longer preserves the per-directory export contract")
    if 'uv pip install --no-compile --no-deps --target . -r "$requirements_file" "${install_targets[@]}"' not in build_zip:
        failures.append("lambdas/scripts/build_zip.sh no longer installs from the exported requirements.txt in the build directory")

    shared_target = ((load_toml(REPO_ROOT / "lambdas/shared/pyproject.toml").get("project") or {}).get("requires-python")) or ""
    if "3.12" not in shared_target:
        failures.append("lambdas/shared must remain compatible with Python 3.12 for the local-source pilot")

    for dockerfile_path in PROD_DOCKERFILES:
        dockerfile = dockerfile_path.read_text()
        if "--group=prod" in dockerfile and "--no-default-groups" not in dockerfile:
            failures.append(
                f"{dockerfile_path.relative_to(REPO_ROOT)} must disable default groups when syncing the prod image environment"
            )

    for pyproject_path in iter_lambda_pyprojects():
        package_path = pyproject_path.parent.relative_to(REPO_ROOT).as_posix()
        pyproject = load_toml(pyproject_path)
        allow_local_sources = package_path in ALLOWED_LOCAL_SOURCE_LAMBDAS

        for dependency, source in iter_internal_source_entries(pyproject):
            normalized_dependency = normalize_name(dependency)
            if normalized_dependency == T4_LAMBDA_SHARED_DEPENDENCY:
                if not is_pinned_t4_shared_source(source):
                    failures.append(
                        f"{package_path} must source {dependency} from the pinned quiltdata/quilt archive URL"
                    )
                continue
            if ("path" in source or source.get("workspace") is True) and not allow_local_sources:
                failures.append(f"{package_path} commits a lambda local source for {dependency}")
            if source.get("editable") is True and not allow_local_sources:
                failures.append(f"{package_path} commits an editable lambda source for {dependency}")

        for dependency in iter_dependency_entries(pyproject):
            if dependency_name(dependency) not in INTERNAL_DEPENDENCY_NAMES:
                continue
            if "@ file:" in dependency or "@ ../" in dependency or "@ ./" in dependency:
                failures.append(
                    f"{package_path} commits a file/path direct dependency for {dependency.split('@', 1)[0].strip()}"
                )

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print("Python packaging guardrails passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Python packaging helpers for the local-source pilot.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("guardrails", help="Validate packaging guardrails for lambda export/build behavior.")

    install_targets = subparsers.add_parser(
        "install-targets",
        help="Print committed local path source directories for a package, one absolute path per line.",
    )
    install_targets.add_argument("package_path", help="Repo-relative package path (for example: lambdas/preview)")

    args = parser.parse_args()

    if args.command == "guardrails":
        return guardrails()

    if args.command == "install-targets":
        for target in path_source_targets_for(REPO_ROOT / args.package_path):
            print(target)
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
