# GPL-3.0-or-later
# Test helper: load the addon's bpy-free modules by path, without importing
# the phynodes package itself (whose __init__ imports bpy).

import importlib.util
import pathlib
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, relpath, package_dir=None):
    """Load a module (or, with package_dir, a package) from the addon tree
    under a private name so relative imports inside it still resolve."""
    path = ROOT / relpath
    if package_dir is not None:
        spec = importlib.util.spec_from_file_location(
            name, path,
            submodule_search_locations=[str(ROOT / package_dir)],
        )
    else:
        spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_tests(namespace):
    """Fallback runner so test files also work as plain scripts
    (python tests/test_x.py) when pytest isn't installed."""
    failed = 0
    for name in sorted(namespace):
        fn = namespace[name]
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok:", name)
            except Exception:
                failed += 1
                print("FAIL:", name)
                traceback.print_exc()
    sys.exit(1 if failed else 0)
