#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
import tempfile
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any, TypeAlias, cast

import yaml

ROOT = Path(__file__).resolve().parent
LEGACY_CONFIG_PATH = ROOT / "pydocmd.yml"
GENERATED_DOCS_DIR = (ROOT / "../docs/api-reference").resolve()
RENDERER_SCRATCH_FILES = [ROOT / ".generated-files.txt", ROOT / "mkdocs.yml"]
LegacySpec: TypeAlias = str | list["LegacySpec"] | dict[str, "LegacySpec"]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _resolve_runtime_target(target: str) -> str:
    try:
        module = import_module(target)
    except ImportError:
        pass
    else:
        return module.__name__

    parts = target.split(".")
    obj: Any = import_module(parts[0])
    for part in parts[1:]:
        obj = getattr(obj, part)

    if isinstance(obj, ModuleType):
        return obj.__name__

    module_name = getattr(obj, "__module__", None)
    qualname = getattr(obj, "__qualname__", getattr(obj, "__name__", None))
    if not module_name or not qualname:
        return target
    return f"{module_name}.{qualname}"


def _expand_legacy_object_spec(spec: LegacySpec) -> list[str]:
    if isinstance(spec, str):
        raw_target = spec.rstrip("+")
        expand_depth = len(spec) - len(raw_target)
        target = _resolve_runtime_target(raw_target)
        patterns = [target]
        for depth in range(1, expand_depth + 1):
            patterns.append(target + (".*" * depth))
        return patterns

    if isinstance(spec, list):
        patterns: list[str] = []
        for item in cast(list[LegacySpec], spec):
            patterns.extend(_expand_legacy_object_spec(item))
        return patterns

    patterns: list[str] = []
    for key, value in cast(dict[str, LegacySpec], spec).items():
        patterns.extend(_expand_legacy_object_spec(key))
        patterns.extend(_expand_legacy_object_spec(value))
    return patterns


def _normalize_page_target(page_target: str) -> str:
    return page_target.split("<<", 1)[0].strip()


def _build_generated_pages(legacy_config: dict[str, Any]) -> list[dict[str, Any]]:
    generated_contents: dict[str, list[str]] = {}
    for page_spec in legacy_config.get("generate", []):
        for filename, object_spec in page_spec.items():
            generated_contents[filename] = _dedupe(_expand_legacy_object_spec(object_spec))

    generated_pages: list[dict[str, Any]] = []
    for page_spec in legacy_config.get("pages", []):
        for title, target in page_spec.items():
            filename = _normalize_page_target(target)
            contents = generated_contents.get(filename)
            if not contents:
                continue

            generated_pages.append(
                {
                    "title": title,
                    "name": Path(filename).with_suffix("").as_posix(),
                    "contents": contents,
                }
            )

    return generated_pages


def _build_nav(legacy_config: dict[str, Any]) -> list[dict[str, str]]:
    nav: list[dict[str, str]] = []
    for page_spec in legacy_config.get("pages", []):
        for title, target in page_spec.items():
            nav.append({title: _normalize_page_target(target)})
    return nav


def _shared_mkdocs_options(legacy_config: dict[str, Any]) -> dict[str, Any]:
    options: dict[str, Any] = {
        "site_name": legacy_config.get("site_name"),
        "site_dir": legacy_config.get("site_dir"),
        "theme": legacy_config.get("theme", "readthedocs"),
        "docs_dir": legacy_config.get("gens_dir", "../docs/api-reference"),
    }

    for key in ("markdown_extensions", "repo_url"):
        if key in legacy_config:
            options[key] = legacy_config[key]

    return options


def _build_pydoc_markdown_config(legacy_config: dict[str, Any]) -> dict[str, Any]:
    search_path = ["*"]
    search_path.extend(legacy_config.get("additional_search_paths", []))

    return {
        "loaders": [
            {
                "type": "python",
                "packages": ["quilt3"],
                "search_path": _dedupe(search_path),
            }
        ],
        "processors": [
            {"type": "filter"},
            {"type": "smart"},
            {"type": "crossref"},
        ],
        "renderer": {
            "type": "mkdocs",
            "output_directory": ".",
            "content_directory_name": legacy_config.get("gens_dir", "../docs/api-reference"),
            "pages": _build_generated_pages(legacy_config),
            "markdown": {
                "signature_in_header": True,
                "signature_code_block": False,
                "classdef_code_block": False,
                "descriptive_class_title": False,
                "add_module_prefix": False,
                "add_method_class_prefix": True,
                "render_toc": False,
                "use_fixed_header_levels": True,
                "header_level_by_type": {
                    "Module": 1,
                    "Class": 1,
                    "Method": 2,
                    "Function": 2,
                    "Variable": 2,
                },
            },
            "mkdocs_config": {
                "site_name": legacy_config.get("site_name"),
                "theme": legacy_config.get("theme", "readthedocs"),
            },
        },
    }


def _cleanup_renderer_scratch_files() -> None:
    for path in RENDERER_SCRATCH_FILES:
        path.unlink(missing_ok=True)


def _write_temp_yaml(config: dict[str, Any]) -> Path:
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        prefix="quilt-gendocs-",
        dir=ROOT,
        delete=False,
        encoding="utf-8",
    )
    try:
        yaml.safe_dump(config, temp_file, sort_keys=False)
    finally:
        temp_file.close()
    return Path(temp_file.name)


def _run_pydoc_markdown(config_path: Path) -> None:
    subprocess.check_call(
        [sys.executable, "-m", "pydoc_markdown.main", str(config_path)],
        cwd=ROOT,
    )


def _run_mkdocs(legacy_config: dict[str, Any], mkdocs_args: list[str]) -> None:
    mkdocs_config = _shared_mkdocs_options(legacy_config)
    mkdocs_config["nav"] = _build_nav(legacy_config)

    config_path = _write_temp_yaml(mkdocs_config)
    try:
        subprocess.check_call(
            [sys.executable, "-m", "mkdocs", *mkdocs_args, "--config-file", str(config_path)],
            cwd=ROOT,
        )
    finally:
        config_path.unlink(missing_ok=True)


def generate_api_reference_docs(legacy_config: dict[str, Any]) -> None:
    config_path = _write_temp_yaml(_build_pydoc_markdown_config(legacy_config))
    try:
        _run_pydoc_markdown(config_path)
    finally:
        config_path.unlink(missing_ok=True)
        _cleanup_renderer_scratch_files()


def generate_cli_api_reference_docs() -> None:
    # This script relies on relative paths so it should only run if the cwd is gendocs/
    subprocess.check_call(["./gen_cli_api_reference.sh"])


def gen_walkthrough_doc() -> None:
    # This script relies on relative paths so it should only run if the cwd is gendocs/
    subprocess.check_call(["./gen_walkthrough.sh"])


if __name__ == "__main__":
    with LEGACY_CONFIG_PATH.open(encoding="utf-8") as file_obj:
        legacy_config = yaml.safe_load(file_obj)

    # CLI and Walkthrough docs uses custom script to generate documentation markdown, so do that first
    generate_cli_api_reference_docs()
    gen_walkthrough_doc()

    generate_api_reference_docs(legacy_config)

    mkdocs_args = sys.argv[1:] or ["build"]
    _run_mkdocs(legacy_config, mkdocs_args)

    # report where stuff is
    print("Generated HTML in {!r}".format(legacy_config.get("site_dir")))
    print("Generated markdown in {!r}".format(legacy_config.get("gens_dir")))
