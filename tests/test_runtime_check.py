"""运行时兼容性检查测试。"""

import sys

import pytest

from app.runtime_check import UnsupportedRuntimeError, ensure_supported_runtime, platform_version


def test_platform_version_matches_interpreter():
    assert platform_version() == ".".join(str(part) for part in sys.version_info[:3])


def test_python_313_is_rejected(monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 13, 0, "final", 0))
    with pytest.raises(UnsupportedRuntimeError, match="Python 3.13"):
        ensure_supported_runtime()


def test_python_311_is_supported(monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 11, 9, "final", 0))
    ensure_supported_runtime()
