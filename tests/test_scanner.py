"""Scanner 服务单元测试。"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from app.services.scanner import Scanner


@pytest.fixture
def mock_database():
    """模拟数据库。"""
    db = Mock()
    db.fetch_one = Mock(return_value=None)
    db.execute = Mock(return_value=1)
    return db


@pytest.fixture
def scanner(mock_database):
    """创建 Scanner 实例。"""
    return Scanner(mock_database)


def test_scanner_fingerprint_small_file(tmp_path, scanner):
    """测试小文件指纹生成。"""
    # 创建测试文件
    test_file = tmp_path / "small_video.mp4"
    test_file.write_bytes(b"test content" * 100)  # < 1MB

    # 生成指纹
    import os
    stat = os.stat(test_file)
    fingerprint = scanner.fingerprint(test_file, stat)

    # 验证指纹格式
    assert isinstance(fingerprint, str)
    assert len(fingerprint) == 64  # SHA256 hex digest


def test_scanner_fingerprint_large_file(tmp_path, scanner):
    """测试大文件指纹生成（采样模式）。"""
    # 创建大文件
    test_file = tmp_path / "large_video.mp4"
    test_file.write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB

    # 生成指纹
    import os
    stat = os.stat(test_file)
    fingerprint = scanner.fingerprint(test_file, stat)

    # 验证指纹格式
    assert isinstance(fingerprint, str)
    assert len(fingerprint) == 64


def test_scanner_discovers_media_files(tmp_path, scanner, mock_database):
    """测试扫描发现媒体文件。"""
    # 创建测试文件
    (tmp_path / "video.mp4").write_bytes(b"video")
    (tmp_path / "audio.mp3").write_bytes(b"audio")
    (tmp_path / "text.txt").write_bytes(b"text")  # 非媒体文件

    # 执行扫描
    with patch.object(scanner.database, 'fetch_one', return_value=None):
        with patch.object(scanner.database, 'execute', return_value=1):
            result = scanner.scan(source_id=1, root_path=tmp_path, recursive=False)

    # 验证结果
    assert result.discovered >= 2  # 至少发现 2 个媒体文件
    assert result.failed == 0


def test_scanner_skips_duplicate_files(tmp_path, scanner, mock_database):
    """测试跳过重复文件。"""
    # 创建测试文件
    test_file = tmp_path / "video.mp4"
    test_file.write_bytes(b"video content")

    # 模拟文件已存在
    with patch.object(scanner.database, 'fetch_one', return_value={"id": 1}):
        result = scanner.scan(source_id=1, root_path=tmp_path, recursive=False)

    # 验证跳过重复文件
    assert result.skipped >= 1
    assert result.created == 0


def test_scanner_recursive_scan(tmp_path, scanner, mock_database):
    """测试递归扫描子目录。"""
    # 创建子目录和文件
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    (tmp_path / "root.mp4").write_bytes(b"root")
    (sub_dir / "sub.mp4").write_bytes(b"sub")

    # 递归扫描
    with patch.object(scanner.database, 'fetch_one', return_value=None):
        with patch.object(scanner.database, 'execute', return_value=1):
            result = scanner.scan(source_id=1, root_path=tmp_path, recursive=True)

    # 验证发现所有文件
    assert result.discovered >= 2


def test_scanner_non_recursive_scan(tmp_path, scanner, mock_database):
    """测试非递归扫描（仅当前目录）。"""
    # 创建子目录和文件
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    (tmp_path / "root.mp4").write_bytes(b"root")
    (sub_dir / "sub.mp4").write_bytes(b"sub")

    # 非递归扫描
    with patch.object(scanner.database, 'fetch_one', return_value=None):
        with patch.object(scanner.database, 'execute', return_value=1):
            result = scanner.scan(source_id=1, root_path=tmp_path, recursive=False)

    # 验证只发现根目录文件
    assert result.discovered == 1
