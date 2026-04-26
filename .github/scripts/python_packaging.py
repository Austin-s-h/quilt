#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]
INTERNAL_DEPENDENCY_NAMES = {
    "quilt3",
    "quilt-shared",
    "t4-lambda-shared",
    "t4-lambda_shared",
    "t4_lambda_shared",
}
CONTAINER_LAMBDAS = {"indexer", "tabular_preview", "thumbnail"}
PILOT_LOCAL_SOURCE_OVERRIDES = {
    "lambdas/indexer": ["lambdas/shared", "py-shared"],
    "lambdas/preview": ["lambdas/shared"],
}
PILOT_COMMITTED_LOCAL_SOURCE_PACKAGES = {
    "lambdas/indexer",
    "lambdas/preview",
}
PILOT_PACKAGE_SET = {
    "py-shared",
    "lambdas/shared",
    "lambdas/indexer",
    "lambdas/preview",
    "gendocs",
}


@dataclass(frozen=True)
class PackageRecord:
    package_path: str
    distribution_name: str
    package_family: str
    python_target: str
    lockfile_path: str
    dependency_groups: list[str]
    default_groups: list[str]
    deploy_release_boundary: str
    internal_source_mode: str
    internal_sources: list[dict[str, Any]]
    direct_numpy_constraints: list[str]
    resolved_numpy_version: str | None
    resolved_numpy_major: int | None
    recent_dependency_churn_examples: list[dict[str, str]]

    def to_json(self) -> dict[str, Any]:
        return {
            "package_path": self.package_path,
            "distribution_name": self.distribution_name,
            "package_family": self.package_family,
            "python_target": self.python_target,
            "lockfile_path": self.lockfile_path,
            "dependency_groups": self.dependency_groups,
            "default_groups": self.default_groups,
            "deploy_release_boundary": self.deploy_release_boundary,
            "internal_source_mode": self.internal_source_mode,
            "internal_sources": self.internal_sources,
            "direct_numpy_constraints": self.direct_numpy_constraints,
            "resolved_numpy_version": self.resolved_numpy_version,
            "resolved_numpy_major": self.resolved_numpy_major,
            "recent_dependency_churn_examples": self.recent_dependency_churn_examples,
        }

    def to_csv(self) -> dict[str, str]:
        return {
            "package_path": self.package_path,
            "distribution_name": self.distribution_name,
            "package_family": self.package_family,
            "python_target": self.python_target,
            "lockfile_path": self.lockfile_path,
            "dependency_groups": "; ".join(self.dependency_groups) or "none",
            "default_groups": "; ".join(self.default_groups) or "none",
            "deploy_release_boundary": self.deploy_release_boundary,
            "internal_source_mode": self.internal_source_mode,
            "direct_numpy_constraint": "; ".join(self.direct_numpy_constraints) or "none",
            "resolved_numpy_version": self.resolved_numpy_version or "none",
            "resolved_numpy_major": str(self.resolved_numpy_major) if self.resolved_numpy_major is not None else "none",
            "recent_dependency_churn_examples": " | ".join(
                f"{entry['sha']} {entry['subject']}" for entry in self.recent_dependency_churn_examples
            )
            or "none",
        }


def normalize_name(name: str) -> str:
    return name.lower().replace("_", "-")


def repo_owned_pyprojects() -> list[Path]:
    pyprojects: list[Path] = []
    for pyproject in REPO_ROOT.glob("**/pyproject.toml"):
        parts = set(pyproject.parts)
        if ".venv" in parts or "site-packages" in parts:
            continue
        pyprojects.append(pyproject)
    return sorted(pyprojects)


def family_for(package_path: str) -> str:
    if package_path == "api/python":
        return "sdk"
    if package_path in {"py-shared", "lambdas/shared"}:
        return "shared"
    if package_path in {"gendocs", "testdocs", "api/python/quilt3-graphql"}:
        return "tooling"
    if package_path.startswith("lambdas/"):
        name = package_path.split("/", 1)[1]
        return "container-lambda" if name in CONTAINER_LAMBDAS else "zip-lambda"
    raise ValueError(f"Unknown package family for {package_path}")


def deploy_boundary_for(package_path: str, family: str) -> str:
    if package_path == "api/python":
        return "PyPI-released SDK and CLI package"
    if package_path == "api/python/quilt3-graphql":
        return "in-repo GraphQL code generation package consumed by api/python"
    if package_path == "gendocs":
        return "in-repo documentation generation tool"
    if package_path == "testdocs":
        return "in-repo documentation codeblock validation tool"
    if package_path == "py-shared":
        return "shared internal Python library consumed by lambdas/services"
    if package_path == "lambdas/shared":
        return "shared internal lambda support library consumed by lambda packages"
    if family == "container-lambda":
        return f"container lambda image built from {package_path}"
    if family == "zip-lambda":
        return f"zip lambda artifact built from {package_path}"
    raise ValueError(f"Unknown deploy boundary for {package_path}")


def load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text())


def source_mode(source: dict[str, Any]) -> str:
    if "path" in source:
        return "path (editable)" if source.get("editable") else "path"
    if source.get("workspace") is True:
        return "workspace"
    if "url" in source:
        if "github.com/quiltdata/quilt/archive/" in source["url"]:
            return "GitHub archive URL"
        return "url"
    if "git" in source:
        return "git"
    if "index" in source:
        return "index"
    return "other"


def dependency_name(raw_dependency: str) -> str:
    base = raw_dependency.split(";", 1)[0].strip()
    if "@" in base:
        base = base.split("@", 1)[0].strip()
    match = re.match(r"^[A-Za-z0-9_.-]+", base)
    return normalize_name(match.group(0) if match else base.strip())


def internal_sources_for(pyproject: dict[str, Any]) -> list[dict[str, Any]]:
    project = pyproject.get("project", {})
    sources = ((pyproject.get("tool") or {}).get("uv") or {}).get("sources") or {}
    rows: list[dict[str, Any]] = []

    for dep_name, source in sorted(sources.items()):
        if normalize_name(dep_name) not in INTERNAL_DEPENDENCY_NAMES:
            continue
        if not isinstance(source, dict):
            continue
        row = {
            "dependency": dep_name,
            "mode": source_mode(source),
        }
        for key in ("path", "url", "git", "subdirectory", "editable", "workspace"):
            if key in source:
                row[key] = source[key]
        rows.append(row)

    for dep in project.get("dependencies", []) or []:
        if "@" not in dep:
            continue
        normalized = dependency_name(dep)
        if normalized not in INTERNAL_DEPENDENCY_NAMES:
            continue
        row = {
            "dependency": dep.split("@", 1)[0].strip(),
            "mode": "GitHub archive URL"
            if "github.com/quiltdata/quilt/archive/" in dep
            else ("path" if "@ file:" in dep or "@ ../" in dep or "@ ./" in dep else "other"),
            "specifier": dep,
        }
        rows.append(row)

    return rows


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


def has_committed_local_sources(package_path: str) -> bool:
    project_dir = REPO_ROOT / package_path
    pyproject = load_toml(project_dir / "pyproject.toml")
    return any(
        source.get("mode", "").startswith("path") or source.get("mode") == "workspace"
        for source in internal_sources_for(pyproject)
    )


def numpy_constraints_for(pyproject: dict[str, Any]) -> list[str]:
    project = pyproject.get("project", {})
    constraints: list[str] = []

    for dep in project.get("dependencies", []) or []:
        if dependency_name(dep) == "numpy":
            constraints.append(f"dependencies: {dep}")

    for extra_name, extra_deps in sorted((project.get("optional-dependencies") or {}).items()):
        for dep in extra_deps or []:
            if dependency_name(dep) == "numpy":
                constraints.append(f"optional:{extra_name}: {dep}")

    for group_name, deps in sorted((pyproject.get("dependency-groups") or {}).items()):
        for dep in deps or []:
            if dependency_name(dep) == "numpy":
                constraints.append(f"group:{group_name}: {dep}")

    return constraints


def resolved_numpy_from_lock(lockfile: Path | None) -> tuple[str | None, int | None]:
    if lockfile is None or not lockfile.exists():
        return None, None
    data = load_toml(lockfile)
    for package in data.get("package", []):
        if package.get("name") == "numpy":
            version = package.get("version")
            if not isinstance(version, str):
                return None, None
            try:
                major = int(version.split(".", 1)[0])
            except ValueError:
                major = None
            return version, major
    return None, None


def recent_dependency_churn(package_path: str) -> list[dict[str, str]]:
    package_dir = REPO_ROOT / package_path
    paths = [str(package_dir / "pyproject.toml")]
    lockfile = package_dir / "uv.lock"
    if lockfile.exists():
        paths.append(str(lockfile))
    cmd = [
        "git",
        "--no-pager",
        "log",
        "--since=2025-01-01",
        "--pretty=format:%H\t%s",
        "--name-only",
        "--",
        *paths,
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in result.stdout.splitlines():
        if "\t" not in line:
            continue
        sha, subject = line.split("\t", 1)
        if sha in seen:
            continue
        seen.add(sha)
        rows.append({"sha": sha[:7], "subject": subject})
        if len(rows) == 3:
            break
    return rows


def render_artifacts() -> tuple[str, str]:
    packages: list[PackageRecord] = []
    family_summary: dict[str, dict[str, Any]] = {}

    for pyproject_path in repo_owned_pyprojects():
        package_dir = pyproject_path.parent
        package_path = package_dir.relative_to(REPO_ROOT).as_posix()
        pyproject = load_toml(pyproject_path)
        project = pyproject.get("project", {})
        family = family_for(package_path)
        lockfile = package_dir / "uv.lock"
        internal_sources = internal_sources_for(pyproject)
        internal_modes = sorted({row["mode"] for row in internal_sources})
        numpy_version, numpy_major = resolved_numpy_from_lock(lockfile if lockfile.exists() else None)
        package = PackageRecord(
            package_path=package_path,
            distribution_name=project.get("name", package_dir.name),
            package_family=family,
            python_target=project.get("requires-python", "unspecified"),
            lockfile_path=(lockfile.relative_to(REPO_ROOT).as_posix() if lockfile.exists() else "none"),
            dependency_groups=sorted((pyproject.get("dependency-groups") or {}).keys()),
            default_groups=sorted(((pyproject.get("tool") or {}).get("uv") or {}).get("default-groups") or []),
            deploy_release_boundary=deploy_boundary_for(package_path, family),
            internal_source_mode=("; ".join(internal_modes) if internal_modes else "none"),
            internal_sources=internal_sources,
            direct_numpy_constraints=numpy_constraints_for(pyproject),
            resolved_numpy_version=numpy_version,
            resolved_numpy_major=numpy_major,
            recent_dependency_churn_examples=recent_dependency_churn(package_path),
        )
        packages.append(package)

    for package in packages:
        summary = family_summary.setdefault(
            package.package_family,
            {
                "package_paths": [],
                "internal_source_modes": set(),
                "resolved_numpy_majors": set(),
                "recent_dependency_churn_examples": [],
            },
        )
        summary["package_paths"].append(package.package_path)
        if package.internal_source_mode != "none":
            summary["internal_source_modes"].update(package.internal_source_mode.split("; "))
        if package.resolved_numpy_major is not None:
            summary["resolved_numpy_majors"].add(package.resolved_numpy_major)
        for entry in package.recent_dependency_churn_examples:
            if entry not in summary["recent_dependency_churn_examples"]:
                summary["recent_dependency_churn_examples"].append(entry)

    json_payload = {
        "packages": [package.to_json() for package in packages],
        "family_summaries": {
            family: {
                "package_paths": sorted(values["package_paths"]),
                "internal_source_modes": sorted(values["internal_source_modes"]),
                "resolved_numpy_majors": sorted(values["resolved_numpy_majors"]),
                "recent_dependency_churn_examples": values["recent_dependency_churn_examples"][:5],
            }
            for family, values in sorted(family_summary.items())
        },
    }
    json_text = json.dumps(json_payload, indent=2, sort_keys=True) + "\n"

    csv_rows = [package.to_csv() for package in packages]
    csv_fieldnames = [
        "package_path",
        "distribution_name",
        "package_family",
        "python_target",
        "lockfile_path",
        "dependency_groups",
        "default_groups",
        "deploy_release_boundary",
        "internal_source_mode",
        "direct_numpy_constraint",
        "resolved_numpy_version",
        "resolved_numpy_major",
        "recent_dependency_churn_examples",
    ]
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=csv_fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(csv_rows)
    csv_text = csv_buffer.getvalue()
    return json_text, csv_text


def write_inventory(json_path: Path, csv_path: Path) -> None:
    json_text, csv_text = render_artifacts()
    json_path.write_text(json_text)
    csv_path.write_text(csv_text)


def check_inventory(json_path: Path, csv_path: Path) -> int:
    expected_json, expected_csv = render_artifacts()
    failures: list[str] = []
    if not json_path.exists() or json_path.read_text() != expected_json:
        failures.append(str(json_path.relative_to(REPO_ROOT)))
    if not csv_path.exists() or csv_path.read_text() != expected_csv:
        failures.append(str(csv_path.relative_to(REPO_ROOT)))
    if failures:
        for failure in failures:
            print(f"Inventory artifact is stale: {failure}", file=sys.stderr)
        return 1
    print("Inventory artifacts are current.")
    return 0


def guardrails() -> int:
    failures: list[str] = []

    expected_py_ci = [
        "uv export --locked --no-emit-project --no-emit-local --no-hashes --directory lambdas/${{ matrix.path }} -o requirements.txt --no-default-groups",
        "uv export --locked --no-emit-project --no-emit-local --no-hashes --directory lambdas/${{ matrix.path }} -o test-requirements.txt --only-group test",
        'python -m pip install -t deps --no-deps -r requirements.txt "${local_targets[@]}" lambdas/${{ matrix.path }}',
        "python -m pip install -r test-requirements.txt",
    ]
    py_ci = (REPO_ROOT / ".github/workflows/py-ci.yml").read_text()
    for needle in expected_py_ci:
        if needle not in py_ci:
            failures.append(f".github/workflows/py-ci.yml is missing expected export contract: {needle}")

    build_zip = (REPO_ROOT / "lambdas/scripts/build_zip.sh").read_text()
    expected_build_zip = 'uv export --locked --no-emit-project --no-emit-local --no-hashes --directory "$FUNCTION_DIR" -o requirements.txt --no-default-groups'
    if expected_build_zip not in build_zip:
        failures.append("lambdas/scripts/build_zip.sh no longer preserves the per-directory export contract")
    expected_build_zip_install = 'uv pip install --no-compile --no-deps --target . -r requirements.txt "${install_targets[@]}"'
    if expected_build_zip_install not in build_zip:
        failures.append("lambdas/scripts/build_zip.sh no longer installs from the exported requirements.txt in the build directory")

    shared_pyproject = load_toml(REPO_ROOT / "lambdas/shared/pyproject.toml")
    shared_target = ((shared_pyproject.get("project") or {}).get("requires-python")) or ""
    if "3.12" not in shared_target:
        failures.append("lambdas/shared must remain compatible with Python 3.12 for the issue #6 pilot set")

    for dockerfile_path in (
        REPO_ROOT / "lambdas/indexer/Dockerfile",
        REPO_ROOT / "lambdas/thumbnail/Dockerfile",
        REPO_ROOT / "lambdas/tabular_preview/Dockerfile",
    ):
        dockerfile = dockerfile_path.read_text()
        if "--group=prod" in dockerfile and "--no-default-groups" not in dockerfile:
            failures.append(
                f"{dockerfile_path.relative_to(REPO_ROOT)} must disable default groups when syncing the prod image environment"
            )

    for pyproject_path in repo_owned_pyprojects():
        package_path = pyproject_path.parent.relative_to(REPO_ROOT).as_posix()
        if not package_path.startswith("lambdas/"):
            continue
        pyproject = load_toml(pyproject_path)
        allow_local_sources = package_path in PILOT_COMMITTED_LOCAL_SOURCE_PACKAGES
        for source in internal_sources_for(pyproject):
            mode = source.get("mode", "")
            dependency = source.get("dependency", "<unknown>")
            if mode.startswith("path") or mode == "workspace":
                if not allow_local_sources:
                    failures.append(f"{package_path} commits a lambda local source for {dependency}: {mode}")
            if source.get("editable") is True:
                if not allow_local_sources:
                    failures.append(f"{package_path} commits an editable lambda source for {dependency}")
            specifier = source.get("specifier", "")
            if "@ file:" in specifier or "@ ../" in specifier or "@ ./" in specifier:
                failures.append(f"{package_path} commits a file/path direct dependency for {dependency}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print("Python packaging guardrails passed.")
    return 0


def venv_python(project_dir: Path) -> Path:
    candidates = [
        project_dir / ".venv/bin/python",
        project_dir / ".venv/Scripts/python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No project virtualenv found in {project_dir}")


def run(cmd: list[str], cwd: Path) -> None:
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def pilot_overrides_for(package_path: str) -> list[tuple[str, str]]:
    if package_path not in PILOT_PACKAGE_SET:
        raise ValueError(
            f"{package_path} is not part of the fixed issue #6 pilot set: {', '.join(sorted(PILOT_PACKAGE_SET))}"
        )
    overrides = []
    for source_path in PILOT_LOCAL_SOURCE_OVERRIDES.get(package_path, []):
        source_pyproject = load_toml(REPO_ROOT / source_path / "pyproject.toml")
        dist_name = ((source_pyproject.get("project") or {}).get("name")) or Path(source_path).name
        overrides.append((dist_name, source_path))
    return overrides


def local_sources_apply(package_path: str) -> int:
    project_dir = REPO_ROOT / package_path
    if not project_dir.exists():
        raise FileNotFoundError(package_path)
    if has_committed_local_sources(package_path):
        print(f"{package_path}: repo defaults already use local internal sources; nothing to apply.")
        return 0
    overrides = pilot_overrides_for(package_path)
    run(["uv", "sync", "--locked"], cwd=project_dir)
    if not overrides:
        print(f"{package_path}: no override sources required; repo defaults are already correct for this pilot package.")
        return 0
    python_path = venv_python(project_dir)
    for _dist_name, source_path in overrides:
        run(
            ["uv", "pip", "install", "--python", str(python_path), "--no-deps", "-e", str(REPO_ROOT / source_path)],
            cwd=project_dir,
        )
    print(f"{package_path}: applied local editable overrides for {', '.join(source for _, source in overrides)}.")
    return 0


def local_sources_restore(package_path: str) -> int:
    project_dir = REPO_ROOT / package_path
    if not project_dir.exists():
        raise FileNotFoundError(package_path)
    if has_committed_local_sources(package_path):
        print(f"{package_path}: repo defaults already use local internal sources; nothing to restore.")
        return 0
    pilot_overrides_for(package_path)
    run(["uv", "sync", "--locked"], cwd=project_dir)
    print(f"{package_path}: restored the locked dependency graph.")
    return 0


def local_sources_status(package_path: str) -> int:
    project_dir = REPO_ROOT / package_path
    if not project_dir.exists():
        raise FileNotFoundError(package_path)
    if has_committed_local_sources(package_path):
        print(f"{package_path}: repo defaults already use local internal sources:")
        for target in path_source_targets_for(project_dir):
            print(target.relative_to(REPO_ROOT))
        return 0
    overrides = pilot_overrides_for(package_path)
    if not overrides:
        print(f"{package_path}: no override sources required.")
        return 0
    python_path = venv_python(project_dir)
    names = [dist_name for dist_name, _ in overrides]
    script = """
import importlib.metadata as md
import json
from pathlib import Path
names = %s
for name in names:
    dist = md.distribution(name)
    direct = None
    for file in dist.files or []:
        if file.name == "direct_url.json":
            direct = Path(dist.locate_file(file)).read_text()
            break
    print(name)
    print(direct or "no direct_url.json")
""" % (
        repr(names),
    )
    run([str(python_path), "-c", script], cwd=project_dir)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Python packaging tooling for the progressive uv packaging rollout.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser("inventory", help="Generate or verify Python packaging inventory artifacts.")
    inventory_subparsers = inventory.add_subparsers(dest="inventory_command", required=True)

    inventory_generate = inventory_subparsers.add_parser("generate", help="Write inventory artifacts.")
    inventory_generate.add_argument("--json", type=Path, required=True)
    inventory_generate.add_argument("--csv", type=Path, required=True)

    inventory_check = inventory_subparsers.add_parser("check", help="Verify inventory artifacts are current.")
    inventory_check.add_argument("--json", type=Path, required=True)
    inventory_check.add_argument("--csv", type=Path, required=True)

    subparsers.add_parser("guardrails", help="Validate packaging guardrails for lambda export/build behavior.")

    local_sources = subparsers.add_parser(
        "local-sources", help="Apply or inspect the issue #6 local override workflow for pilot packages."
    )
    local_subparsers = local_sources.add_subparsers(dest="local_sources_command", required=True)
    for name in ("apply", "restore", "status"):
        command = local_subparsers.add_parser(name)
        command.add_argument("package_path", help="Repo-relative package path (for example: lambdas/preview)")

    install_targets = subparsers.add_parser(
        "install-targets",
        help="Print committed local path source directories for a package, one absolute path per line.",
    )
    install_targets.add_argument("package_path", help="Repo-relative package path (for example: lambdas/preview)")

    args = parser.parse_args()

    if args.command == "inventory":
        json_path = (REPO_ROOT / args.json).resolve() if not args.json.is_absolute() else args.json
        csv_path = (REPO_ROOT / args.csv).resolve() if not args.csv.is_absolute() else args.csv
        if args.inventory_command == "generate":
            write_inventory(json_path, csv_path)
            print(f"Wrote {json_path.relative_to(REPO_ROOT)} and {csv_path.relative_to(REPO_ROOT)}.")
            return 0
        return check_inventory(json_path, csv_path)

    if args.command == "guardrails":
        return guardrails()

    if args.command == "local-sources":
        if args.local_sources_command == "apply":
            return local_sources_apply(args.package_path)
        if args.local_sources_command == "restore":
            return local_sources_restore(args.package_path)
        return local_sources_status(args.package_path)

    if args.command == "install-targets":
        for target in path_source_targets_for(REPO_ROOT / args.package_path):
            print(target)
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
