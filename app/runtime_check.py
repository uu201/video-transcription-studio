"""Checks for runtime combinations that are known to be unsupported."""

from __future__ import annotations

import sys
from importlib import metadata


class UnsupportedRuntimeError(RuntimeError):
    """Raised when the interpreter cannot run the pinned ASR stack reliably."""


def ensure_supported_runtime() -> None:
    """Fail early with an actionable message instead of a broken NumPy import.

    NumPy 1.26.x is intentionally pinned by this project because it is the
    version range validated with FunASR. It has no official CPython 3.13
    Windows wheel, so pip may install an experimental MinGW build instead.
    """
    version = sys.version_info
    major, minor, micro = version[:3]
    if (major, minor) < (3, 10) or (major, minor) >= (3, 13):
        raise UnsupportedRuntimeError(
            "当前项目支持 Python 3.10-3.12；检测到 "
            f"Python {major}.{minor}.{micro}。\n"
            "Python 3.13 会让 NumPy 1.26.x 安装成 Windows MinGW 实验版本，"
            "从而出现 getlimits.py 警告甚至崩溃。\n"
            "请删除并重建虚拟环境：\n"
            "  py -3.11 -m venv .venv\n"
            "  .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt"
        )


def runtime_summary() -> dict[str, str]:
    """Return non-invasive version information for diagnostics."""
    try:
        numpy_version = metadata.version("numpy")
    except metadata.PackageNotFoundError:
        numpy_version = "未安装"
    return {"python": platform_version(), "numpy": numpy_version}


def platform_version() -> str:
    """Return the interpreter version without importing third-party modules."""
    return ".".join(str(part) for part in sys.version_info[:3])
