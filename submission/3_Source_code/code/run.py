#!/usr/bin/env python3
"""Task runner. Windows-friendly stand-in for a Makefile.

    python run.py pipeline     run all seven lifecycle stages
    python run.py query        trace the deployed model back to raw data
    python run.py stats        what is currently in the ledger
    python run.py evaluate     the comparative study against the baseline
    python run.py baseline     the control condition, no thread
    python run.py test         the test suite
    python run.py serve        dashboard + API at http://127.0.0.1:8000
    python run.py export       re-render artifacts/thread.html
    python run.py clean        remove generated artifacts
"""

from __future__ import annotations

import shutil
import subprocess
import sys

TASKS = {
    "pipeline": [sys.executable, "-m", "pipeline.flow"],
    "query":    [sys.executable, "-m", "thread.query", "explain-model"],
    "stats":    [sys.executable, "-m", "thread.query", "stats"],
    "export":   [sys.executable, "-m", "thread.query", "export"],
    "evaluate": [sys.executable, "-m", "experiments.evaluate_framework",
                 "--repeats", "5"],
    "baseline": [sys.executable, "-m", "baseline.run_baseline"],
    "test":     [sys.executable, "-m", "pytest", "tests/", "-q"],
    "serve":    [sys.executable, "-m", "uvicorn", "app.main:app",
                 "--reload", "--port", "8000"],
    "install":  [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    task = sys.argv[1]

    if task == "clean":
        for path in ("artifacts", "data/processed"):
            shutil.rmtree(path, ignore_errors=True)
            print(f"removed {path}")
        return 0

    if task not in TASKS:
        print(f"unknown task {task!r}\n")
        print(__doc__)
        return 1

    cmd = TASKS[task] + sys.argv[2:]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
