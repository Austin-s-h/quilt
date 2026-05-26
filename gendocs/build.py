#!/usr/bin/env python3

import subprocess
import sys

import yaml


def generate_cli_api_reference_docs():
    # This script relies on relative paths so it should only run if the cwd is gendocs/
    subprocess.check_call(["./gen_cli_api_reference.sh"])


def gen_walkthrough_doc():
    # This script relies on relative paths so it should only run if the cwd is gendocs/
    subprocess.check_call(["./gen_walkthrough.sh"])


def _patch_pydocmd_for_python313():
    """Patch pydocmd for Python 3.12+ compatibility.

    Fixes:
    - classmethod descriptors not directly callable by inspect.signature()
    - dunder attributes (__hash__, __slots__, __firstlineno__, etc.) leaking into docs
    """
    import re

    import pydocmd.__main__ as pydocmd_mod
    import pydocmd.imp as imp
    import pydocmd.loader as loader

    # Skip all dunder attributes — none belong in API docs
    _original_dir_object = imp.dir_object

    def _patched_dir_object(name, sort_order='line', need_docstrings=True):
        result = _original_dir_object(name, sort_order, need_docstrings)
        return [key for key in result if not re.match(r'__\w+__$', key)]

    imp.dir_object = _patched_dir_object
    pydocmd_mod.dir_object = _patched_dir_object

    # Handle classmethod descriptors in signature introspection
    _original_get_function_signature = loader.get_function_signature

    def _patched_get_function_signature(function, owner_class=None):
        if isinstance(function, classmethod):
            function = function.__func__
        return _original_get_function_signature(function, owner_class)

    loader.get_function_signature = _patched_get_function_signature


if __name__ == "__main__":
    # CLI and Walkthrough docs uses custom script to generate documentation markdown, so do that first
    generate_cli_api_reference_docs()
    gen_walkthrough_doc()

    from pydocmd.__main__ import main as pydocmd_main

    # hacky, but we should maintain the same interpreter, and we're dependent on how
    # pydocmd calls mkdocs.
    if sys.argv[-1].endswith('build.py'):
        print("Using standard args for mkdocs.")
        sys.argv.append('build')
    else:
        print("Using custom args for mkdocs.")

    _patch_pydocmd_for_python313()

    print("\nStarting pydocmd_main...")

    pydocmd_main()

    print("...finished pydocmd_main")

    # report where stuff is
    with open('pydocmd.yml', encoding='utf-8') as f:
        pydocmd_config = yaml.safe_load(f)
    print("Generated HTML in {!r}".format(pydocmd_config.get('site_dir')))
    print("Generated markdown in {!r}".format(pydocmd_config.get('gens_dir')))
